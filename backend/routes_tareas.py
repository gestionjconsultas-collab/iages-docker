#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Routes para gestión y estadísticas de tareas
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import Tarea, User, db
from tenant_utils import get_current_gestoria_id
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from constants import NotificationTypes, TaskStates

tareas_bp = Blueprint('tareas', __name__)


@tareas_bp.route('/api/tareas/calendario', methods=['GET'])
@login_required
def get_tareas_calendario():
    """
    Retorna todas las tareas del usuario actual para el calendario
    
    Returns:
        JSON con lista de tareas
    """
    try:
        from flask_login import current_user
        
        gestoria_id = get_current_gestoria_id()
        usuario_id = current_user.id
        
        print(f"📅 Calendario - Gestoría ID: {gestoria_id}, Usuario ID: {usuario_id}")
        
        # Obtener tareas asignadas al usuario O sin asignar (jefatura)
        # Esto permite ver:
        # 1. Tareas propias (asignadas al usuario)
        # 2. Tareas de jefatura (sin asignar aún)
        from sqlalchemy import or_
        from sqlalchemy.orm import joinedload
        
        tareas = Tarea.query.options(
            joinedload(Tarea.documento),
            joinedload(Tarea.empresa),
            joinedload(Tarea.asignado_a)  # ✅ Eager loading para evitar N+1
        ).filter(
            Tarea.gestoria_id == gestoria_id,
            or_(
                Tarea.asignado_a_id == usuario_id,
                Tarea.asignado_a_id == None
            )
        ).order_by(Tarea.fecha_creacion.desc()).all()
        
        print(f"📅 Total tareas (propias + jefatura) para usuario {usuario_id}: {len(tareas)}")
        
        
        eventos = []
        tareas_sin_fecha = 0
        
        from datetime import datetime
        hoy = datetime.now().date()
        
        for tarea in tareas:
            # Si no tiene fecha_vencimiento, usar fecha_creacion
            if not tarea.fecha_vencimiento:
                tareas_sin_fecha += 1
                print(f"  ⚠️ Tarea sin fecha_vencimiento: {tarea.titulo}")
                fecha = tarea.fecha_creacion
            else:
                fecha = tarea.fecha_vencimiento
            
            # Determinar color según estado y fecha
            if tarea.estado == TaskStates.COMPLETADA:
                backgroundColor = '#10b981'  # Verde
                borderColor = '#059669'
                print(f"  ✅ Tarea completada: {tarea.titulo}")
            else:
                # Calcular días hasta vencimiento
                if tarea.fecha_vencimiento:
                    vencimiento_date = tarea.fecha_vencimiento.date() if hasattr(tarea.fecha_vencimiento, 'date') else tarea.fecha_vencimiento
                    dias_hasta_vencimiento = (vencimiento_date - hoy).days
                    
                    print(f"  📅 Tarea: {tarea.titulo}")
                    print(f"     Estado: {tarea.estado}")
                    print(f"     Vence: {vencimiento_date}")
                    print(f"     Días hasta vencimiento: {dias_hasta_vencimiento}")
                    
                    # Rojo: Vencida o próxima a vencer (≤3 días)
                    if dias_hasta_vencimiento < 0 or dias_hasta_vencimiento <= 3:
                        backgroundColor = '#ef4444'  # Rojo (vencida o crítica)
                        borderColor = '#dc2626'
                        print(f"     🔴 COLOR: ROJO (vencida o crítica)")
                    # Amarillo: Advertencia (4-7 días)
                    elif dias_hasta_vencimiento <= 7:
                        backgroundColor = '#f59e0b'  # Amarillo (advertencia)
                        borderColor = '#d97706'
                        print(f"     🟡 COLOR: AMARILLO (advertencia)")
                    # Azul: Futuras (>7 días)
                    else:
                        backgroundColor = '#3b82f6'  # Azul (futura)
                        borderColor = '#2563eb'
                        print(f"     🔵 COLOR: AZUL (futura)")
                else:
                    backgroundColor = '#3b82f6'  # Azul por defecto
                    borderColor = '#2563eb'
                    print(f"  ⚠️ Tarea sin fecha de vencimiento: {tarea.titulo}")
            
            eventos.append({
                'title': tarea.titulo,
                'start': fecha.isoformat() if fecha else None,
                'end': fecha.isoformat() if fecha else None,
                'allDay': True,
                'backgroundColor': backgroundColor,
                'borderColor': borderColor,
                'textColor': '#ffffff',
                'data': tarea.to_dict()
            })
        
        print(f"📅 Tareas con fecha: {len(tareas) - tareas_sin_fecha}")
        print(f"📅 Tareas SIN fecha_vencimiento: {tareas_sin_fecha}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'eventos': eventos,
            'tareas_sin_fecha': tareas_sin_fecha
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo tareas para calendario: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@tareas_bp.route('/api/tareas/estadisticas', methods=['GET'])
@login_required
def get_estadisticas_tareas():
    """
    Retorna estadísticas de productividad de tareas
    
    Query params:
        - usuario_id: (opcional) filtrar por usuario específico
        - fecha_inicio: (opcional) desde cuándo (YYYY-MM-DD)
        - fecha_fin: (opcional) hasta cuándo (YYYY-MM-DD)
    
    Returns:
        JSON con estadísticas generales y por usuario
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # Parámetros opcionales
        usuario_id = request.args.get('usuario_id', type=int)
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        
        # Construir query base
        query = Tarea.query.filter(Tarea.gestoria_id == gestoria_id)
        
        # Filtros opcionales
        if usuario_id:
            query = query.filter(Tarea.asignado_a_id == usuario_id)
        
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
            query = query.filter(Tarea.fecha_creacion >= fecha_inicio)
        
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
            query = query.filter(Tarea.fecha_creacion <= fecha_fin)
        
        # Obtener todas las tareas
        tareas = query.all()
        
        # Calcular estadísticas generales
        total_tareas = len(tareas)
        completadas = len([t for t in tareas if t.estado == TaskStates.COMPLETADA])
        pendientes = len([t for t in tareas if t.estado in [TaskStates.PENDIENTE, TaskStates.EN_PROGRESO]])
        
        # Tareas vencidas (fecha_vencimiento < hoy y no completadas)
        hoy = datetime.now()
        vencidas = len([t for t in tareas 
                       if t.fecha_vencimiento and t.fecha_vencimiento < hoy 
                       and t.estado != TaskStates.COMPLETADA])
        
        # Tasa de completitud
        tasa_completitud = (completadas / total_tareas * 100) if total_tareas > 0 else 0
        
        # Promedio de días para completar
        tareas_completadas_con_fecha = [t for t in tareas 
                                        if t.estado == TaskStates.COMPLETADA 
                                        and t.fecha_completada 
                                        and t.fecha_creacion]
        
        if tareas_completadas_con_fecha:
            dias_totales = sum([(t.fecha_completada - t.fecha_creacion).days 
                               for t in tareas_completadas_con_fecha])
            promedio_dias = dias_totales / len(tareas_completadas_con_fecha)
        else:
            promedio_dias = 0
        
        # Estadísticas por usuario
        usuarios_stats = {}
        for tarea in tareas:
            if not tarea.asignado_a_id:
                continue
            
            if tarea.asignado_a_id not in usuarios_stats:
                usuarios_stats[tarea.asignado_a_id] = {
                    'usuario_id': tarea.asignado_a_id,
                    'nombre': tarea.asignado_a.nombre if tarea.asignado_a else 'Sin asignar',
                    'total': 0,
                    'completadas': 0,
                    'pendientes': 0,
                    'vencidas': 0
                }
            
            usuarios_stats[tarea.asignado_a_id]['total'] += 1
            
            if tarea.estado == TaskStates.COMPLETADA:
                usuarios_stats[tarea.asignado_a_id]['completadas'] += 1
            elif tarea.estado in [TaskStates.PENDIENTE, TaskStates.EN_PROGRESO]:
                usuarios_stats[tarea.asignado_a_id]['pendientes'] += 1
                
                if tarea.fecha_vencimiento and tarea.fecha_vencimiento < hoy:
                    usuarios_stats[tarea.asignado_a_id]['vencidas'] += 1
        
        # Calcular tasa de completitud por usuario
        por_usuario = []
        for user_id, stats in usuarios_stats.items():
            stats['tasa_completitud'] = (stats['completadas'] / stats['total'] * 100) if stats['total'] > 0 else 0
            por_usuario.append(stats)
        
        # Ordenar por tasa de completitud (menor a mayor para identificar problemas)
        por_usuario.sort(key=lambda x: x['tasa_completitud'])
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'estadisticas': {
                'total_tareas': total_tareas,
                'completadas': completadas,
                'pendientes': pendientes,
                'vencidas': vencidas,
                'tasa_completitud': round(tasa_completitud, 1),
                'promedio_dias_completar': round(promedio_dias, 1),
                'por_usuario': por_usuario
            }
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@tareas_bp.route('/api/tareas/vencidas', methods=['GET'])
@login_required
def get_tareas_vencidas():
    """
    Retorna tareas vencidas (fecha_vencimiento < hoy y estado != completada)
    
    Query params:
        - usuario_id: (opcional) filtrar por usuario
    
    Returns:
        JSON con lista de tareas vencidas
    """
    try:
        gestoria_id = get_current_gestoria_id()
        usuario_id = request.args.get('usuario_id', type=int)
        
        hoy = datetime.now()
        
        # Query base
        query = Tarea.query.filter(
            Tarea.gestoria_id == gestoria_id,
            Tarea.fecha_vencimiento < hoy,
            Tarea.estado.in_([TaskStates.PENDIENTE, TaskStates.EN_PROGRESO])
        )
        
        if usuario_id:
            query = query.filter(Tarea.asignado_a_id == usuario_id)
        
        tareas_vencidas = query.order_by(Tarea.fecha_vencimiento.asc()).all()
        
        # Formatear respuesta
        tareas_list = []
        for tarea in tareas_vencidas:
            dias_vencida = (hoy.date() - tarea.fecha_vencimiento.date()).days
            
            tareas_list.append({
                'id': tarea.id,
                'titulo': tarea.titulo,
                'descripcion': tarea.descripcion,
                'asignado_a': tarea.asignado_a.nombre if tarea.asignado_a else 'Sin asignar',
                'asignado_a_id': tarea.asignado_a_id,
                'fecha_vencimiento': tarea.fecha_vencimiento.isoformat(),
                'dias_vencida': dias_vencida,
                'prioridad': tarea.prioridad,
                'estado': tarea.estado,
                'empresa': tarea.empresa.nombre if tarea.empresa else None
            })
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'tareas_vencidas': tareas_list,
            'total': len(tareas_list)
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo tareas vencidas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@tareas_bp.route('/api/tareas/reporte/<int:usuario_id>', methods=['GET'])
@login_required
def get_reporte_usuario(usuario_id):
    """
    Reporte detallado de productividad de un usuario
    
    Returns:
        JSON con estadísticas detalladas del usuario
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # Verificar que el usuario pertenece a la gestoría
        usuario = User.query.filter_by(id=usuario_id, gestoria_id=gestoria_id).first()
        if not usuario:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Usuario no encontrado'}), 404
        
        hoy = datetime.now()
        hace_30_dias = hoy - timedelta(days=30)
        
        # Tareas de los últimos 30 días
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        tareas_30_dias = Tarea.query.filter(
            Tarea.gestoria_id == gestoria_id,
            Tarea.asignado_a_id == usuario_id,
            Tarea.fecha_creacion >= hace_30_dias
        ).all()
        
        total_30 = len(tareas_30_dias)
        completadas_30 = len([t for t in tareas_30_dias if t.estado == TaskStates.COMPLETADA])
        vencidas_30 = len([t for t in tareas_30_dias 
                          if t.fecha_vencimiento and t.fecha_vencimiento < hoy 
                          and t.estado != TaskStates.COMPLETADA])
        
        tasa_30 = (completadas_30 / total_30 * 100) if total_30 > 0 else 0
        
        # Tareas vencidas actuales
        tareas_vencidas_actuales = Tarea.query.filter(
            Tarea.gestoria_id == gestoria_id,
            Tarea.asignado_a_id == usuario_id,
            Tarea.fecha_vencimiento < hoy,
            Tarea.estado.in_([TaskStates.PENDIENTE, TaskStates.EN_PROGRESO])
        ).all()
        
        vencidas_list = [{
            'id': t.id,
            'titulo': t.titulo,
            'fecha_vencimiento': t.fecha_vencimiento.isoformat(),
            'dias_vencida': (hoy.date() - t.fecha_vencimiento.date()).days,
            'prioridad': t.prioridad
        } for t in tareas_vencidas_actuales]
        
        # Estadísticas por mes (últimos 6 meses)
        por_mes = []
        for i in range(6):
            mes_inicio = (hoy - timedelta(days=30 * i)).replace(day=1)
            mes_fin = (mes_inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            tareas_mes = Tarea.query.filter(
                Tarea.gestoria_id == gestoria_id,
                Tarea.asignado_a_id == usuario_id,
                Tarea.fecha_creacion >= mes_inicio,
                Tarea.fecha_creacion <= mes_fin
            ).all()
            
            completadas_mes = len([t for t in tareas_mes if t.estado == TaskStates.COMPLETADA])
            vencidas_mes = len([t for t in tareas_mes 
                               if t.fecha_vencimiento and t.fecha_vencimiento < hoy 
                               and t.estado != TaskStates.COMPLETADA])
            
            por_mes.append({
                'mes': mes_inicio.strftime('%Y-%m'),
                'total': len(tareas_mes),
                'completadas': completadas_mes,
                'vencidas': vencidas_mes
            })
        
        por_mes.reverse()  # Orden cronológico
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.email
            },
            'ultimos_30_dias': {
                'total': total_30,
                'completadas': completadas_30,
                'vencidas': vencidas_30,
                'tasa_completitud': round(tasa_30, 1)
            },
            'por_mes': por_mes,
            'tareas_vencidas_actuales': vencidas_list
        })
        
    except Exception as e:
        print(f"❌ Error generando reporte: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@tareas_bp.route('/api/tareas/<int:tarea_id>', methods=['PUT'])
@login_required
def actualizar_tarea(tarea_id):
    """
    Actualiza una tarea (principalmente para marcar como completada)
    
    Body:
        - estado: nuevo estado de la tarea
        - fecha_completada: (opcional) fecha de completación
    
    Returns:
        JSON con resultado de la operación
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # Buscar tarea y verificar pertenencia a gestoría
        tarea = Tarea.query.filter_by(
            id=tarea_id,
            gestoria_id=gestoria_id
        ).first()
        
        if not tarea:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Tarea no encontrada'}), 404
        
        data = request.get_json()
        
        # Actualizar estado
        if 'estado' in data:
            tarea.estado = data['estado']
        
        # Si se marca como completada, registrar fecha
        if data.get('estado') == TaskStates.COMPLETADA and 'fecha_completada' in data:
            tarea.fecha_completada = datetime.fromisoformat(data['fecha_completada'].replace('Z', '+00:00'))
        elif data.get('estado') == TaskStates.COMPLETADA:
            tarea.fecha_completada = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': 'Tarea actualizada exitosamente',
            'tarea': tarea.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error actualizando tarea: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500
