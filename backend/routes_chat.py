#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Chat Routes - Endpoints for chat functionality
To be imported in app.py
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from models import Conversacion, MensajeChat
from extensions import db
from ai_chat import construir_contexto_sistema, generar_contexto_adicional
from auditoria import auditar
from rate_limiter import rate_limit  # Sistema de rate limiting
from chat_cache import obtener_respuesta_cache, guardar_respuesta_cache  # Sistema de caché
from chat_commands import detectar_comando, ejecutar_comando  # Comandos rápidos
import google.generativeai as genai
import time
from datetime import datetime
from constants import NotificationTypes


def register_chat_routes(app):
    """
    Register all chat-related routes
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/api/chat/preguntar', methods=['POST'])
    @rate_limit(limite=20, ventana_horas=1)  # Límite: 20 preguntas por hora
    @login_required
    def chat_preguntar():
        """
        Endpoint para hacer preguntas al asistente de IA
        
        Body:
            pregunta (str): Pregunta del usuario
            conversacion_id (int, optional): ID de conversación existente
        
        Returns:
            JSON con respuesta de Gemini
        """
        data = request.json
        pregunta = data.get('pregunta', '').strip()
        conversacion_id = data.get('conversacion_id')
        
        if not pregunta:
            return jsonify({NotificationTypes.ERROR: 'Pregunta vacía'}), 400
        
        try:
            # 🆕 DETECTAR INTENCIÓN DE CREAR TAREA (antes de comandos)
            from chat_actions import (
                detectar_intencion_crear_tarea,
                extraer_parametros_tarea_con_gemini,
                ejecutar_accion_crear_tarea
            )
            from tenant_utils import get_current_gestoria_id
            
            if detectar_intencion_crear_tarea(pregunta):
                print("✅ Detectada intención de crear tarea")
                print(f"📝 Pregunta: {pregunta}")
                
                # Extraer parámetros usando Gemini
                params = extraer_parametros_tarea_con_gemini(pregunta, get_current_gestoria_id())
                print(f"📋 Parámetros extraídos: {params}")
                
                # Ejecutar acción
                resultado = ejecutar_accion_crear_tarea(
                    params,
                    current_user.id,
                    get_current_gestoria_id()
                )
                
                print(f"✨ Resultado: {resultado}")
                
                if resultado[NotificationTypes.SUCCESS]:
                    return jsonify({
                        NotificationTypes.SUCCESS: True,
                        'respuesta': resultado['mensaje'],
                        'accion_ejecutada': 'crear_tarea',
                        'tarea': resultado['tarea'],
                        'conversacion_id': conversacion_id or 0,
                        'tokens_usados': 0,
                        'tiempo_respuesta': 0
                    })
                else:
                    return jsonify({
                        NotificationTypes.SUCCESS: False,
                        'respuesta': resultado['mensaje'],
                        'conversacion_id': conversacion_id or 0
                    }), 400
            
            # Detectar si es un comando rápido
            es_comando, comando, argumentos = detectar_comando(pregunta)
            
            if es_comando:
                print(f"⚡ Ejecutando comando: {comando} {argumentos or ''}")
                resultado = ejecutar_comando(comando, argumentos, current_user.id)
                
                return jsonify({
                    NotificationTypes.SUCCESS: resultado[NotificationTypes.SUCCESS],
                    'respuesta': resultado['respuesta'],
                    'es_comando': True,
                    'comando': comando,
                    'conversacion_id': conversacion_id or 0,
                    'tokens_usados': 0,
                    'tiempo_respuesta': 0
                })
            
            # Detectar si es una consulta analítica (antes del caché)
            from chat_analytics import detectar_consulta_analitica, ejecutar_consulta_analitica
            
            analisis = detectar_consulta_analitica(pregunta)
            if analisis:
                print(f"📊 Ejecutando consulta analítica: {analisis['tipo']}")
                resultado_analitico = ejecutar_consulta_analitica(analisis['tipo'], analisis)
                
                if resultado_analitico:
                    return jsonify({
                        NotificationTypes.SUCCESS: True,
                        'respuesta': resultado_analitico,
                        'es_analitica': True,
                        'conversacion_id': conversacion_id or 0,
                        'tokens_usados': 0,
                        'tiempo_respuesta': 0
                    })
            
            # Generar contexto adicional
            contexto_adicional = generar_contexto_adicional(pregunta)
            
            # Buscar en cache primero
            cache_result = obtener_respuesta_cache(pregunta, contexto_adicional)
            
            if cache_result:
                # Obtener o crear conversación incluso para respuestas cacheadas
                if conversacion_id:
                    conversacion = Conversacion.query.get(conversacion_id)
                    if not conversacion or conversacion.usuario_id != current_user.id:
                        conversacion = None
                else:
                    conversacion = None
                
                if not conversacion:
                    # Nueva conversación
                    conversacion = Conversacion(
                        usuario_id=current_user.id,
                        titulo=pregunta[:100]
                    )
                    db.session.add(conversacion)
                    db.session.flush()
                    conversacion_id = conversacion.id
                
                # Registrar en auditoría con conversacion_id correcto
                from auditoria import registrar_auditoria
                registrar_auditoria(
                    accion='chat_pregunta',
                    entidad_tipo='conversacion',
                    entidad_id=conversacion.id,
                    descripcion=f"{current_user.nombre} realizó acción: chat_pregunta (cacheada)",
                    detalles={'pregunta': pregunta, 'cacheada': True}
                )
                
                # Guardar mensajes en historial del chat
                mensaje_usuario = MensajeChat(
                    conversacion_id=conversacion.id,
                    rol='user',
                    contenido=pregunta
                )
                mensaje_asistente = MensajeChat(
                    conversacion_id=conversacion.id,
                    rol='assistant',
                    contenido=cache_result['respuesta']
                )
                db.session.add(mensaje_usuario)
                db.session.add(mensaje_asistente)
                
                db.session.commit()
                
                # Respuesta encontrada en cache
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'respuesta': cache_result['respuesta'],
                    'cacheado': True,
                    'hits': cache_result['hits'],
                    'conversacion_id': conversacion.id,
                    'tokens_usados': 0,
                    'tiempo_respuesta': 0
                })
            
            # Si no está en cache, continuar con flujo normal
            # Obtener o crear conversación
            if conversacion_id:
                conversacion = Conversacion.query.get(conversacion_id)
                if not conversacion or conversacion.usuario_id != current_user.id:
                    return jsonify({NotificationTypes.ERROR: 'Conversación no encontrada'}), 404
            else:
                # Nueva conversación
                conversacion = Conversacion(
                    usuario_id=current_user.id,
                    titulo=pregunta[:100]  # Primeras 100 chars como título
                )
                db.session.add(conversacion)
                db.session.flush()
            
            # Construir contexto del sistema
            contexto_sistema = construir_contexto_sistema(current_user)
            
            # Generar contexto adicional basado en la pregunta
            contexto_adicional = generar_contexto_adicional(pregunta)
            
            # Historial de conversación (últimos 10 mensajes)
            mensajes_anteriores = conversacion.mensajes.order_by(
                MensajeChat.fecha_creacion
            ).limit(10).all()
            
            # Construir historial para Gemini
            historial = []
            for msg in mensajes_anteriores:
                # Gemini usa 'model' en lugar de 'assistant'
                role_gemini = 'model' if msg.rol == 'assistant' else msg.rol
                historial.append({
                    'role': role_gemini,
                    'parts': [msg.contenido]
                })
            
            # Configurar Gemini con sistema de fallback de múltiples keys
            # Intentar con cada key disponible hasta encontrar una que funcione
            import os
            gemini_keys = [
                os.getenv('GEMINI_API_KEY'),      # Key principal
                os.getenv('GEMINI_API_KEY_2'),    # Respaldo 1
                os.getenv('GEMINI_API_KEY_3'),    # Respaldo 2
            ]
            
            # Filtrar keys vacías
            gemini_keys = [key for key in gemini_keys if key]
            
            print(f"🔑 Keys disponibles para fallback: {len(gemini_keys)}")
            
            if not gemini_keys:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'No hay API keys de Gemini configuradas'
                }), 500
            
            # Modelo a usar
            modelo_usar = 'gemini-2.5-flash'
            
            response = None
            key_usada = None
            error_final = None
            
            # Intentar con cada key hasta que una funcione
            for i, api_key in enumerate(gemini_keys, 1):
                try:
                    print(f"🔑 Intentando con API Key #{i}...")
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(modelo_usar)
                    
                    # Construir prompt completo
                    prompt_completo = f"""{contexto_sistema}

{contexto_adicional}

PREGUNTA DEL USUARIO:
{pregunta}
"""
                    
                    # Llamar a Gemini
                    start_time = time.time()
                    
                    if historial:
                        # Conversación existente - usar historial
                        chat = model.start_chat(history=historial)
                        response = chat.send_message(prompt_completo)
                    else:
                        # Primera pregunta - sin historial
                        response = model.generate_content(prompt_completo)
                    
                    tiempo_respuesta = time.time() - start_time
                    key_usada = i
                    
                    # Si llegamos aquí, la llamada fue exitosa
                    print(f"✅ Respuesta generada con API Key #{i} ({modelo_usar})")
                    
                    # Registrar uso exitoso de la API key
                    try:
                        from gemini_utils import registrar_uso_api_key
                        tokens_usados = 0
                        if hasattr(response, 'usage_metadata') and hasattr(response.usage_metadata, 'total_token_count'):
                            tokens_usados = response.usage_metadata.total_token_count
                        registrar_uso_api_key(i, success=True, tokens=tokens_usados)
                    except Exception as track_error:
                        print(f"⚠️ Error registrando tracking: {track_error}")
                    
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    
                    # Si es error de cuota (429), intentar siguiente key
                    if '429' in error_msg or 'quota' in error_msg.lower() or 'ResourceExhausted' in error_msg:
                        print(f"⚠️ API Key #{i} agotó su cuota, intentando con siguiente key...")
                        error_final = f"Cuota agotada en key #{i}"
                        
                        # Registrar error de cuota
                        try:
                            from gemini_utils import registrar_uso_api_key
                            registrar_uso_api_key(i, success=False)
                        except Exception as track_error:
                            print(f"⚠️ Error registrando tracking: {track_error}")
                        
                        continue
                    else:
                        # Otro tipo de error, no continuar
                        print(f"❌ Error en API Key #{i}: {error_msg}")
                        error_final = error_msg
                        raise e
            
            # Si ninguna key funcionó
            if response is None:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: f'Todas las API keys de Gemini agotaron su cuota. {error_final}',
                    'mensaje': 'El servicio de IA ha alcanzado su límite de uso. Por favor, intenta más tarde o contacta al administrador.'
                }), 429
            
            respuesta_texto = response.text
            
            # Obtener tokens usados (si está disponible)
            tokens_usados = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens_usados = response.usage_metadata.total_token_count
            
            # Guardar mensaje del usuario
            mensaje_usuario = MensajeChat(
                conversacion_id=conversacion.id,
                rol='user',
                contenido=pregunta,
                tokens_usados=None,
                tiempo_respuesta=None
            )
            db.session.add(mensaje_usuario)
            
            # Guardar respuesta del asistente
            mensaje_asistente = MensajeChat(
                conversacion_id=conversacion.id,
                rol='assistant',
                contenido=respuesta_texto,
                tokens_usados=tokens_usados,
                tiempo_respuesta=tiempo_respuesta,
                metadata={
                    'modelo': modelo_usar,
                    'api_key_usada': key_usada,  # Guardar qué key se usó
                    'contexto_generado': bool(contexto_adicional)
                }
            )
            db.session.add(mensaje_asistente)
            
            # Actualizar fecha de conversación
            conversacion.fecha_actualizacion = datetime.utcnow()
            
            db.session.commit()
            
            # Guardar respuesta en cache
            guardar_respuesta_cache(pregunta, respuesta_texto, contexto_adicional)
            
            # Registrar en auditoría con la pregunta
            from auditoria import registrar_auditoria
            registrar_auditoria(
                accion='chat_pregunta',
                entidad_tipo='conversacion',
                entidad_id=conversacion.id,
                descripcion=f"{current_user.nombre} realizó acción: chat_pregunta",
                detalles={'pregunta': pregunta}
            )
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'respuesta': respuesta_texto,
                'conversacion_id': conversacion.id,
                'tiempo_respuesta': round(tiempo_respuesta, 2),
                'tokens_usados': tokens_usados,
                'cacheado': False
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en chat: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/conversaciones', methods=['GET'])
    @login_required
    def get_conversaciones():
        """Lista de conversaciones del usuario"""
        try:
            conversaciones = Conversacion.query.filter_by(
                usuario_id=current_user.id
            ).order_by(Conversacion.fecha_actualizacion.desc()).all()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'conversaciones': [c.to_dict() for c in conversaciones]
            })
        except Exception as e:
            print(f"❌ Error obteniendo conversaciones: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/conversacion/<int:id>', methods=['GET'])
    @login_required
    def get_conversacion(id):
        """Obtener mensajes de una conversación"""
        try:
            conversacion = Conversacion.query.get(id)
            
            if not conversacion or conversacion.usuario_id != current_user.id:
                return jsonify({NotificationTypes.ERROR: 'Conversación no encontrada'}), 404
            
            mensajes = conversacion.mensajes.order_by(MensajeChat.fecha_creacion).all()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'conversacion': {
                    'id': conversacion.id,
                    'titulo': conversacion.titulo,
                    'fecha_creacion': conversacion.fecha_creacion.isoformat() if conversacion.fecha_creacion else None,
                    'mensajes': [m.to_dict() for m in mensajes]
                }
            })
        except Exception as e:
            print(f"❌ Error obteniendo conversación: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/conversacion/<int:id>', methods=['DELETE'])
    @login_required
    @auditar('chat_conversacion_eliminada', 'conversacion')
    def delete_conversacion(id):
        """Eliminar conversación"""
        try:
            conversacion = Conversacion.query.get(id)
            
            if not conversacion or conversacion.usuario_id != current_user.id:
                return jsonify({NotificationTypes.ERROR: 'Conversación no encontrada'}), 404
            
            db.session.delete(conversacion)
            db.session.commit()
            
            return jsonify({NotificationTypes.SUCCESS: True, 'message': 'Conversación eliminada'})
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error eliminando conversación: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/estadisticas', methods=['GET'])
    @login_required
    def get_estadisticas_chat():
        """Estadísticas de uso del chat"""
        try:
            # Total de conversaciones del usuario
            total_conversaciones = Conversacion.query.filter_by(
                usuario_id=current_user.id
            ).count()
            
            # Total de mensajes
            total_mensajes = db.session.query(MensajeChat).join(Conversacion).filter(
                Conversacion.usuario_id == current_user.id
            ).count()
            
            # Tokens totales usados
            tokens_totales = db.session.query(
                db.func.sum(MensajeChat.tokens_usados)
            ).join(Conversacion).filter(
                Conversacion.usuario_id == current_user.id,
                MensajeChat.tokens_usados != None
            ).scalar() or 0
            
            # Tiempo promedio de respuesta
            tiempo_promedio = db.session.query(
                db.func.avg(MensajeChat.tiempo_respuesta)
            ).join(Conversacion).filter(
                Conversacion.usuario_id == current_user.id,
                MensajeChat.tiempo_respuesta != None
            ).scalar() or 0
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'estadisticas': {
                    'total_conversaciones': total_conversaciones,
                    'total_mensajes': total_mensajes,
                    'tokens_totales': int(tokens_totales),
                    'tiempo_promedio_respuesta': round(float(tiempo_promedio), 2)
                }
            })
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/rate-limit/status', methods=['GET'])
    @login_required
    def rate_limit_status():
        """
        Obtener estado actual del rate limit del usuario
        
        Returns:
            JSON con información de rate limit:
                - limite: número máximo de requests
                - usado: requests usados en la ventana actual
                - restante: requests restantes
                - reset_en: segundos hasta el reset
        """
        from rate_limiter import RateLimiter
        
        try:
            resultado = RateLimiter.check_limit(
                current_user.id,
                limite=20,
                ventana_horas=1
            )
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'rate_limit': resultado
            })
        except Exception as e:
            print(f"❌ Error obteniendo rate limit status: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/cache/stats', methods=['GET'])
    @login_required
    def cache_stats():
        """
        Obtiene estadísticas del cache de respuestas
        
        Returns:
            JSON con estadísticas del cache
        """
        from chat_cache import obtener_estadisticas_cache
        
        try:
            stats = obtener_estadisticas_cache()
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'cache': stats
            })
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas de cache: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/cache/clear', methods=['DELETE'])
    @login_required
    def clear_cache():
        """
        Limpia todo el cache de respuestas
        
        Returns:
            JSON con número de entradas eliminadas
        """
        from chat_cache import limpiar_cache_completo
        
        try:
            count = limpiar_cache_completo()
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': f'{count} entradas eliminadas',
                'count': count
            })
        except Exception as e:
            print(f"❌ Error limpiando cache: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/chat/cache/clear/expired', methods=['DELETE'])
    @login_required
    def clear_expired_cache():
        """
        Limpia solo las entradas expiradas del cache
        
        Returns:
            JSON con número de entradas eliminadas
        """
        from chat_cache import limpiar_cache_expirado
        
        try:
            count = limpiar_cache_expirado()
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': f'{count} entradas expiradas eliminadas',
                'count': count
            })
        except Exception as e:
            print(f"❌ Error limpiando cache expirado: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # Mensaje de confirmación
    print("✅ Rutas de Chat IA registradas")
