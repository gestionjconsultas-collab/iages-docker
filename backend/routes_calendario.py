# backend/routes_calendario.py
"""
Routes para el calendario tributario de la AEAT
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from models import FechaTributaria
from datetime import datetime, timedelta, date
from constants import NotificationTypes
import logging

logger = logging.getLogger(__name__)

calendario_bp = Blueprint('calendario', __name__)


@calendario_bp.route('/api/calendario/tributario', methods=['GET'])
@login_required
def get_fechas_tributarias():
    """
    Retorna fechas tributarias para el calendario
    
    Query params:
        - fecha_inicio: (opcional) YYYY-MM-DD
        - fecha_fin: (opcional) YYYY-MM-DD
        - tipo_impuesto: (opcional) filtrar por tipo
        - modelo: (opcional) filtrar por modelo
    
    Returns:
        JSON con eventos formateados para FullCalendar
    """
    try:
        # Parámetros
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        tipo_impuesto = request.args.get('tipo_impuesto')
        modelo = request.args.get('modelo')
        
        # Por defecto: próximos 6 meses
        if not fecha_inicio_str:
            fecha_inicio = date.today()
        else:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
        
        if not fecha_fin_str:
            fecha_fin = fecha_inicio + timedelta(days=180)
        else:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        
        # Query
        query = FechaTributaria.query.filter(
            FechaTributaria.fecha >= fecha_inicio,
            FechaTributaria.fecha <= fecha_fin,
            FechaTributaria.activo == True
        )
        
        if tipo_impuesto:
            query = query.filter(FechaTributaria.tipo_impuesto == tipo_impuesto)
        
        if modelo:
            query = query.filter(FechaTributaria.modelo == modelo)
        
        fechas = query.order_by(FechaTributaria.fecha.asc()).all()
        
        logger.info(f"Obtenidas {len(fechas)} fechas tributarias entre {fecha_inicio} y {fecha_fin}")
        
        # Formatear para FullCalendar
        eventos = []
        for fecha in fechas:
            # Determinar color según urgencia
            dias_restantes = (fecha.fecha - date.today()).days
            
            if dias_restantes < 0:
                # Ya pasó
                backgroundColor = '#6b7280'  # Gris
                borderColor = '#4b5563'
            elif dias_restantes <= 7:
                # Muy próximo
                backgroundColor = '#dc2626'  # Rojo
                borderColor = '#991b1b'
            elif dias_restantes <= 15:
                # Próximo
                backgroundColor = '#f59e0b'  # Naranja
                borderColor = '#d97706'
            else:
                # Futuro
                backgroundColor = '#8b5cf6'  # Morado
                borderColor = '#7c3aed'
            
            # Icono según tipo
            icono = '📋'
            if fecha.tipo_impuesto == 'IVA':
                icono = '💶'
            elif fecha.tipo_impuesto == 'IRPF':
                icono = '👤'
            elif fecha.tipo_impuesto == 'Sociedades':
                icono = '🏢'
            elif fecha.tipo_impuesto == 'Seguridad Social':
                icono = '🏥'
            
            titulo = f'{icono} {fecha.titulo}'
            if fecha.modelo:
                titulo = f'{icono} Modelo {fecha.modelo}'
            
            eventos.append({
                'id': f'aeat-{fecha.id}',
                'title': titulo,
                'start': fecha.fecha.isoformat(),
                'backgroundColor': backgroundColor,
                'borderColor': borderColor,
                'textColor': '#ffffff',
                'allDay': True,
                'extendedProps': {
                    'tipo': 'tributaria',
                    'data': fecha.to_dict()
                }
            })
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'eventos': eventos,
            'total': len(eventos)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo fechas tributarias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: str(e)
        }), 500


@calendario_bp.route('/api/calendario/tributario/tipos', methods=['GET'])
@login_required
def get_tipos_impuesto():
    """
    Retorna la lista de tipos de impuesto disponibles
    
    Returns:
        JSON con lista de tipos
    """
    try:
        from sqlalchemy import distinct
        
        tipos = FechaTributaria.query.with_entities(
            distinct(FechaTributaria.tipo_impuesto)
        ).filter(
            FechaTributaria.tipo_impuesto.isnot(None),
            FechaTributaria.activo == True
        ).all()
        
        tipos_list = [t[0] for t in tipos if t[0]]
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'tipos': sorted(tipos_list)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo tipos de impuesto: {e}")
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: str(e)
        }), 500


@calendario_bp.route('/api/calendario/tributario/modelos', methods=['GET'])
@login_required
def get_modelos():
    """
    Retorna la lista de modelos disponibles
    
    Returns:
        JSON con lista de modelos
    """
    try:
        from sqlalchemy import distinct
        
        modelos = FechaTributaria.query.with_entities(
            distinct(FechaTributaria.modelo)
        ).filter(
            FechaTributaria.modelo.isnot(None),
            FechaTributaria.activo == True
        ).all()
        
        modelos_list = [m[0] for m in modelos if m[0]]
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'modelos': sorted(modelos_list)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo modelos: {e}")
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: str(e)
        }), 500


@calendario_bp.route('/api/calendario/tributario/sincronizar', methods=['POST'])
@login_required
def sincronizar_calendario():
    """
    Inicia manualmente la sincronización del calendario AEAT
    
    Body:
        - year: (opcional) Año a sincronizar
    
    Returns:
        JSON con task_id de la tarea Celery
    """
    try:
        from celery_worker import sincronizar_calendario_aeat
        
        data = request.get_json() or {}
        year = data.get('year')
        
        # Iniciar tarea asíncrona
        task = sincronizar_calendario_aeat.apply_async(args=[year])
        
        logger.info(f"Sincronización manual del calendario AEAT iniciada: task_id={task.id}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'task_id': task.id,
            'message': 'Sincronización iniciada'
        })
        
    except Exception as e:
        logger.error(f"Error iniciando sincronización: {e}")
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: str(e)
        }), 500
