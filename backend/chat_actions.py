#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chat Actions - Detección y ejecución de acciones desde el chat IA
"""

import re
import json
from datetime import datetime
from models import Tarea, Documento, Empresa, db
from tenant_utils import get_current_gestoria_id
from gemini_utils import obtener_gemini_con_fallback
from constants import DocumentCategories, NotificationTypes, TaskStates


def detectar_intencion_crear_tarea(pregunta):
    """
    Detecta si el usuario quiere crear una tarea
    
    Args:
        pregunta: str - Pregunta del usuario
    
    Returns:
        bool: True si detecta intención EXPLÍCITA de crear tarea
    """
    # Palabras que indican pregunta informativa (NO crear tarea)
    palabras_pregunta = ['hay', 'cuántos', 'cuántas', 'qué', 'cuál', 'dónde', 'cuándo', 'cómo', 'existe', 'tengo', 'tienes']
    pregunta_lower = pregunta.lower().strip()
    
    # Si empieza con palabra de pregunta, NO es creación de tarea
    if any(pregunta_lower.startswith(p) for p in palabras_pregunta):
        return False
    
    # Si tiene signos de interrogación, probablemente es pregunta informativa
    if '?' in pregunta:
        return False
    
    # Palabras clave EXPLÍCITAS para crear tarea
    palabras_clave_explicitas = [
        'crea una tarea', 'crear tarea', 'crea tarea', 'nueva tarea',
        'añadir tarea', 'agregar tarea', 'añade una tarea', 'agrega una tarea',
        'recordatorio para', 'recuérdame', 'recordarme',
        'agendar', 'programar tarea', 'programa tarea', 'hacer seguimiento de',
        'asignar tarea', 'asígnate', 'asígname',
        'programa alerta', 'programa reunion', 'programa una',
        'revisar', 'llamar a', 'hacer seguimiento'
    ]
    
    es_tarea = any(kw in pregunta_lower for kw in palabras_clave_explicitas)
    
    # Debug logging
    print(f"\n{'='*60}")
    print(f"🔍 DETECTAR_INTENCION_CREAR_TAREA")
    print(f"Pregunta: '{pregunta}'")
    print(f"Pregunta lower: '{pregunta_lower}'")
    print(f"¿Es tarea?: {es_tarea}")
    if es_tarea:
        matched = [kw for kw in palabras_clave_explicitas if kw in pregunta_lower]
        print(f"✅ Palabras clave detectadas: {matched}")
    print(f"{'='*60}\n")
    
    return es_tarea


def parsear_fecha_relativa(fecha_str):
    """
    Convierte palabras clave o fechas ISO a objetos datetime
    
    Args:
        fecha_str: str - Palabra clave o fecha ISO
    
    Returns:
        datetime or None
    """
    from datetime import datetime, timedelta
    import re
    
    if not fecha_str:
        print("⚠️ parsear_fecha_relativa: fecha_str es None o vacío")
        return None
    
    print(f"🔍 Parseando fecha: '{fecha_str}' (tipo: {type(fecha_str)})")
    
    hoy = datetime.utcnow().replace(hour=23, minute=59, second=59)
    fecha_lower = str(fecha_str).lower().strip()
    
    # Palabras clave (con y sin tilde)
    if fecha_lower in ['hoy', 'today']:
        print(f"✅ Detectado 'hoy' → {hoy}")
        return hoy
    elif fecha_lower in ['mañana', 'manana', 'tomorrow']:
        resultado = hoy + timedelta(days=1)
        print(f"✅ Detectado 'mañana' → {resultado}")
        return resultado
    elif fecha_lower in ['pasado_mañana', 'pasado_manana', 'pasado mañana', 'pasado manana']:
        resultado = hoy + timedelta(days=2)
        print(f"✅ Detectado 'pasado mañana' → {resultado}")
        return resultado
    elif fecha_lower in ['proxima_semana', 'próxima_semana', 'proxima semana', 'próxima semana']:
        resultado = hoy + timedelta(days=7)
        print(f"✅ Detectado 'próxima semana' → {resultado}")
        return resultado
    
    # Patrón "en_X_dias" o "en X dias"
    match = re.match(r'en[_\s]?(\d+)[_\s]?dias?', fecha_lower)
    if match:
        dias = int(match.group(1))
        resultado = hoy + timedelta(days=dias)
        print(f"✅ Detectado 'en {dias} días' → {resultado}")
        return resultado
    
    # Fecha ISO (YYYY-MM-DD)
    try:
        resultado = datetime.strptime(fecha_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        print(f"✅ Fecha ISO parseada → {resultado}")
        return resultado
    except:
        pass
    
    print(f"⚠️ No se pudo parsear la fecha: '{fecha_str}'")
    return None


def extraer_parametros_tarea_con_gemini(pregunta, gestoria_id):
    """
    Usa Gemini para extraer parámetros de la tarea
    
    Args:
        pregunta: str - Pregunta del usuario
        gestoria_id: int - ID de la gestoría (para obtener usuarios)
    
    Returns:
        dict: Parámetros de la tarea
    """
    from datetime import datetime
    from models import User
    
    fecha_actual = datetime.utcnow().strftime('%Y-%m-%d')
    
    # Obtener lista de usuarios de la gestoría
    usuarios = User.query.filter_by(gestoria_id=gestoria_id).all()
    usuarios_str = ", ".join([f'"{u.nombre}"' for u in usuarios])
    
    fecha_actual = datetime.utcnow().strftime('%Y-%m-%d')
    
    prompt = f"""Extrae la información de esta solicitud de tarea y devuelve SOLO un JSON válido sin markdown:

Solicitud: "{pregunta}"
Fecha actual: {fecha_actual}
Usuarios disponibles: {usuarios_str}

Devuelve JSON con estos campos:
- titulo: título corto y descriptivo (máximo 100 caracteres)
- descripcion: descripción detallada de la tarea
- prioridad: "alta", "media" o "baja" (por defecto "media")
- asignado_a: nombre del usuario si se menciona a quién asignar (ej: "para Jose", "asignar a Maria"). Si NO se menciona → usa null
- fecha_vencimiento: detecta si menciona cuándo debe hacerse:
  * Si dice "mañana" → usa "mañana"
  * Si dice "pasado mañana" → usa "pasado_mañana"
  * Si dice "en 3 días" o "dentro de 3 días" → usa "en_3_dias"
  * Si dice "próxima semana" → usa "proxima_semana"
  * Si dice "hoy" → usa "hoy"
  * Si NO menciona cuándo → usa null

Ejemplo 1: "programa alerta de revisión para mañana"
{{"titulo": "Alerta de revisión", "descripcion": "Revisar documentos pendientes", "prioridad": "media", "asignado_a": null, "fecha_vencimiento": "mañana"}}

Ejemplo 2: "crear tarea urgente de seguimiento para Jose"
{{"titulo": "Tarea de seguimiento", "descripcion": "Realizar seguimiento urgente", "prioridad": "alta", "asignado_a": "Jose", "fecha_vencimiento": null}}

Ejemplo 3: "asignar a Maria revisar nóminas pasado mañana"
{{"titulo": "Revisar nóminas", "descripcion": "Revisar nóminas pendientes", "prioridad": "media", "asignado_a": "Maria", "fecha_vencimiento": "pasado_mañana"}}

Responde SOLO con el JSON, sin texto adicional."""

    try:
        response, _ = obtener_gemini_con_fallback(prompt, modelo='gemini-2.5-flash')
        
        # Limpiar respuesta (remover markdown si existe)
        texto = response.text.strip()
        if '```json' in texto:
            texto = texto.split('```json')[1].split('```')[0].strip()
        elif '```' in texto:
            texto = texto.split('```')[1].split('```')[0].strip()
        
        params = json.loads(texto)
        
        # Validar campos
        if 'titulo' not in params:
            params['titulo'] = 'Tarea creada desde chat IA'
        if 'descripcion' not in params:
            params['descripcion'] = pregunta
        if 'prioridad' not in params or params['prioridad'] not in ['alta', 'media', 'baja']:
            params['prioridad'] = 'media'
        
        # Parsear fecha_vencimiento si existe
        if 'fecha_vencimiento' in params and params['fecha_vencimiento']:
            fecha_parseada = parsear_fecha_relativa(params['fecha_vencimiento'])
            params['fecha_vencimiento'] = fecha_parseada
        else:
            params['fecha_vencimiento'] = None
        
        # Buscar usuario por nombre si se especificó
        if params.get('asignado_a'):
            usuario_nombre = params['asignado_a'].strip()
            
            # Buscar por coincidencia parcial (case-insensitive)
            usuario = User.query.filter(
                User.gestoria_id == gestoria_id,
                User.nombre.ilike(f'%{usuario_nombre}%')
            ).first()
            
            if usuario:
                params['asignado_a_id'] = usuario.id
                params['asignado_a_nombre'] = usuario.nombre
                print(f"✅ Usuario encontrado: {usuario.nombre} (ID: {usuario.id})")
            else:
                # No se encontró el usuario
                params['asignado_a_id'] = None
                params['asignado_a_nombre'] = None
                params['usuario_no_encontrado'] = usuario_nombre
                print(f"⚠️ Usuario no encontrado: '{usuario_nombre}'")
                
                # Listar usuarios disponibles para debug
                usuarios_disponibles = User.query.filter_by(gestoria_id=gestoria_id).all()
                print(f"📋 Usuarios disponibles: {[u.nombre for u in usuarios_disponibles]}")
        else:
            params['asignado_a_id'] = None
            params['asignado_a_nombre'] = None
        
        return params
        
    except Exception as e:
        print(f"⚠️ Error extrayendo parámetros con Gemini: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: parámetros básicos
        return {
            'titulo': pregunta[:100] if len(pregunta) <= 100 else pregunta[:97] + '...',
            'descripcion': pregunta,
            'prioridad': 'media',
            'fecha_vencimiento': None,
            'asignado_a_id': None,
            'asignado_a_nombre': None
        }


def ejecutar_accion_crear_tarea(params, usuario_id, gestoria_id):
    """
    Crea una tarea en el sistema
    
    Args:
        params: dict - Parámetros de la tarea
        usuario_id: int - ID del usuario que crea la tarea
        gestoria_id: int - ID de la gestoría
    
    Returns:
        dict: Resultado de la operación
    """
    try:
        # Determinar a quién se asigna la tarea
        asignado_a_id = params.get('asignado_a_id') or usuario_id
        
        tarea = Tarea(
            titulo=params.get('titulo', 'Tarea creada desde chat IA'),
            descripcion=params.get('descripcion'),
            asignado_a_id=asignado_a_id,  # ⭐ Puede ser otro usuario
            prioridad=params.get('prioridad', 'media'),
            estado=TaskStates.PENDIENTE,
            fecha_creacion=datetime.utcnow(),
            fecha_vencimiento=params.get('fecha_vencimiento'),  # ← NUEVO
            # Tracking fields
            origen='chat_ia',  # ⭐ Marcar como creada desde Chat IA
            creado_por_id=usuario_id,  # ⭐ Usuario que la creó
            gestoria_id=gestoria_id,  # ⭐ Gestoría para multi-tenant
            tags=params.get('tags', [])  # ⭐ Tags si se proporcionan
        )
        
        # Si se menciona un documento o empresa, intentar asociarlo
        if params.get('documento_id'):
            tarea.documento_id = params['documento_id']
        if params.get('empresa_id'):
            tarea.empresa_id = params['empresa_id']
        
        db.session.add(tarea)
        db.session.commit()
        
        # ⭐ Crear notificación en BD (para que aparezca en dropdown)
        notificacion = None
        if asignado_a_id:  # Notificar al usuario asignado
            try:
                from models import Notificacion
                from tenant_utils import get_current_gestoria_id
                
                # Mensaje con fecha si existe
                mensaje_notif = f"🤖 Chat IA creó una tarea: {tarea.titulo[:80]}"
                if tarea.fecha_vencimiento:
                    fecha_str = tarea.fecha_vencimiento.strftime('%d/%m/%Y')
                    mensaje_notif += f" (vence: {fecha_str})"
                
                notificacion = Notificacion(
                    titulo="Tarea creada por Chat IA",
                    mensaje=mensaje_notif,
                    gestoria_id=get_current_gestoria_id(),
                    user_id=asignado_a_id,  # ⭐ Notificar al asignado
                    link="/calendario",
                    tipo='success'
                )
                db.session.add(notificacion)
                db.session.commit()
                print(f"✅ Notificación creada en BD (ID: {notificacion.id}) para user_{asignado_a_id}")
            except Exception as e:
                print(f"⚠️ Error creando notificación en BD: {e}")
                import traceback
                traceback.print_exc()
        
        # ⭐ Emitir WebSocket (toast + notificación push)
        try:
            from flask import current_app
            socketio = current_app.extensions.get('socketio')
            if socketio and asignado_a_id:  # ⭐ Emitir al asignado
                # 1. Toast tarea_chat_ia
                from socketio_events import notify_tarea_chat_ia
                notify_tarea_chat_ia(
                    socketio,
                    tarea_id=tarea.id,
                    user_id=asignado_a_id,  # ⭐ Toast al asignado
                    titulo=tarea.titulo,
                    fecha_vencimiento=tarea.fecha_vencimiento
                )
                
                # 2. Notificación push (para contador)
                if notificacion:
                    socketio.emit('nueva_notificacion', notificacion.to_dict(), 
                                room=f'user_{asignado_a_id}')  # ⭐ Push al asignado
                    print(f"📬 Emitiendo nueva_notificacion a user_{asignado_a_id}")
        except Exception as e:
            print(f"⚠️ Error emitiendo notificación WebSocket: {e}")
        
        # Mensaje con fecha si existe
        mensaje_fecha = ""
        if tarea.fecha_vencimiento:
            fecha_str = tarea.fecha_vencimiento.strftime('%d/%m/%Y')
            mensaje_fecha = f" para el {fecha_str}"
        
        # Mensaje con usuario asignado si es diferente
        mensaje_asignado = ""
        if params.get('asignado_a_nombre'):
            mensaje_asignado = f" (asignada a {params['asignado_a_nombre']})"
        elif params.get('usuario_no_encontrado'):
            mensaje_asignado = f" ⚠️ Nota: No se encontró al usuario '{params['usuario_no_encontrado']}', la tarea se asignó a ti"
        
        return {
            NotificationTypes.SUCCESS: True,
            'tarea_id': tarea.id,
            'mensaje': f'✅ Tarea creada exitosamente{mensaje_fecha}{mensaje_asignado}: "{tarea.titulo}"',
            'tarea': {
                'id': tarea.id,
                'titulo': tarea.titulo,
                'prioridad': tarea.prioridad,
                'estado': tarea.estado,
                'fecha_vencimiento': tarea.fecha_vencimiento.isoformat() if tarea.fecha_vencimiento else None
            }
        }
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando tarea: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            NotificationTypes.SUCCESS: False,
            'mensaje': f'❌ Error al crear la tarea: {str(e)}'
        }


def detectar_intencion_analizar_importes(pregunta):
    """
    Detecta si el usuario quiere analizar importes
    
    Args:
        pregunta: str - Pregunta del usuario
    
    Returns:
        bool: True si detecta intención de analizar importes
    """
    palabras_clave = [
        'cuánto', 'importe', 'pagar', 'total', 'suma',
        'costo', 'precio', 'monto', 'cantidad', 'cuanto',
        'calcular', 'sumar'
    ]
    
    pregunta_lower = pregunta.lower()
    return any(kw in pregunta_lower for kw in palabras_clave)


def analizar_importes_documentos(pregunta, gestoria_id):
    """
    Analiza y suma importes de documentos según la pregunta
    
    Args:
        pregunta: str - Pregunta del usuario
        gestoria_id: int - ID de la gestoría
    
    Returns:
        dict: Análisis de importes
    """
    from datetime import date, timedelta
    
    pregunta_lower = pregunta.lower()
    
    # Detectar categoría
    categoria = detectar_categoria_en_pregunta(pregunta)
    
    # Detectar empresa
    empresa = detectar_empresa_en_pregunta(pregunta, gestoria_id)
    
    # Detectar período
    hoy = date.today()
    inicio_periodo = None
    fin_periodo = hoy
    
    if 'mes' in pregunta_lower or 'mensual' in pregunta_lower:
        inicio_periodo = hoy.replace(day=1)
    elif 'semana' in pregunta_lower or 'semanal' in pregunta_lower:
        inicio_periodo = hoy - timedelta(days=hoy.weekday())
    elif 'año' in pregunta_lower or 'anual' in pregunta_lower:
        inicio_periodo = hoy.replace(month=1, day=1)
    
    # Construir query
    query = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == gestoria_id,
        Documento.importe_pagar.isnot(None)
    )
    
    if categoria:
        query = query.filter(Documento.categoria == categoria)
    
    if empresa:
        query = query.filter(Documento.empresa_id == empresa.id)
    
    if inicio_periodo:
        query = query.filter(Documento.fecha_creacion >= inicio_periodo)
    
    documentos = query.all()
    
    if not documentos:
        return {
            'total': 0,
            'count': 0,
            'documentos': [],
            'categoria': categoria,
            'empresa': empresa.nombre if empresa else None,
            'mensaje': 'No se encontraron documentos con importes para los criterios especificados.'
        }
    
    total = sum(float(d.importe_pagar) for d in documentos)
    
    return {
        'total': total,
        'count': len(documentos),
        'documentos': documentos[:20],  # Limitar a 20 para no sobrecargar
        'categoria': categoria,
        'empresa': empresa.nombre if empresa else None,
        'periodo': {
            'inicio': inicio_periodo.isoformat() if inicio_periodo else None,
            'fin': fin_periodo.isoformat()
        }
    }


def detectar_empresa_en_pregunta(pregunta, gestoria_id):
    """
    Detecta si se menciona una empresa en la pregunta
    
    Args:
        pregunta: str - Pregunta del usuario
        gestoria_id: int - ID de la gestoría
    
    Returns:
        Empresa o None
    """
    # Buscar NIFs
    nifs = re.findall(r'\b[A-Z]\d{8}\b', pregunta.upper())
    if nifs:
        for nif in nifs:
            empresa = Empresa.query.filter_by(nif=nif, gestoria_id=gestoria_id).first()
            if empresa:
                return empresa
    
    # Buscar por nombre
    empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
    pregunta_lower = pregunta.lower()
    
    for empresa in empresas:
        if empresa.nombre.lower() in pregunta_lower:
            return empresa
    
    return None


def detectar_categoria_en_pregunta(pregunta):
    """
    Detecta la categoría de documento mencionada
    
    Args:
        pregunta: str - Pregunta del usuario
    
    Returns:
        str o None: Categoría detectada
    """
    categorias_map = {
        DocumentCategories.SEGUROS_SOCIALES: ['seguro', 'seguros', 'social', 'sociales', 'ss'],
        DocumentCategories.NOMINAS: ['nomina', 'nómina', 'nominas', 'nóminas'],
        DocumentCategories.NOTIFICACIONES: ['notificacion', 'notificación'],
        'Finiquitos': ['finiquito'],
        'Documentos Fiscales': ['fiscal', 'hacienda', 'aeat']
    }
    
    pregunta_lower = pregunta.lower()
    
    for categoria, keywords in categorias_map.items():
        if any(kw in pregunta_lower for kw in keywords):
            return categoria
    
    return None
