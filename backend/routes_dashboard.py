"""
Routes para Dashboard con Gráficos
Endpoints para usuarios normales y superadmin
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func, case, and_, or_
from datetime import datetime, timedelta
from models import Documento, Tarea, Empresa, Gestoria, User, db
from tenant_utils import get_current_gestoria_id
from constants import DocumentCategories, TaskStates, NotificationTypes
from decorators_rbac import super_admin_required

dashboard_bp = Blueprint('dashboard', __name__)


# ============================================
# ENDPOINTS PARA USUARIOS NORMALES
# ============================================

@dashboard_bp.route('/api/dashboard/stats-graficos', methods=['GET'])
@login_required
def get_stats_graficos():
    """
    Stats para gráficos del dashboard
    Filtrado por gestoría del usuario actual
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # 1. Documentos por categoría (Pie Chart)
        docs_por_categoria = db.session.query(
            Documento.categoria,
            func.count(Documento.id).label('total')
        ).filter(
            Documento.gestoria_id == gestoria_id
        ).group_by(Documento.categoria).all()
        
        # 2. Documentos procesados por mes (Line Chart - últimos 6 meses)
        seis_meses_atras = datetime.now() - timedelta(days=180)
        docs_por_mes = db.session.query(
            func.to_char(Documento.fecha_procesado, 'YYYY-MM').label('mes'),
            func.count(Documento.id).label('total')
        ).filter(
            Documento.gestoria_id == gestoria_id,
            Documento.fecha_procesado >= seis_meses_atras,
            Documento.fecha_procesado.isnot(None)
        ).group_by(
            func.to_char(Documento.fecha_procesado, 'YYYY-MM')
        ).order_by('mes').all()
        
        # 3. Tareas por estado (Bar Chart)
        tareas_por_estado = db.session.query(
            Tarea.estado,
            func.count(Tarea.id).label('total')
        ).join(Empresa).filter(
            Empresa.gestoria_id == gestoria_id
        ).group_by(Tarea.estado).all()
        
        # 4. Documentos procesados hoy vs pendientes
        hoy_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        procesados_hoy = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            Documento.fecha_procesado >= hoy_inicio,
            Documento.fecha_procesado.isnot(None)
        ).count()
        
        pendientes = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            Documento.categoria == DocumentCategories.POR_PROCESAR
        ).count()
        
        # 5. Top 5 empresas con más documentos
        top_empresas = db.session.query(
            Empresa.nombre,
            func.count(Documento.id).label('total')
        ).join(Documento).filter(
            Empresa.gestoria_id == gestoria_id
        ).group_by(Empresa.id).order_by(
            func.count(Documento.id).desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'data': {
                'por_categoria': [
                    {'categoria': cat, 'total': total}
                    for cat, total in docs_por_categoria
                ],
                'por_mes': [
                    {'mes': mes, 'total': total}
                    for mes, total in docs_por_mes
                ],
                'tareas_por_estado': [
                    {'estado': estado, 'total': total}
                    for estado, total in tareas_por_estado
                ],
                'resumen': {
                    'procesados_hoy': procesados_hoy,
                    'pendientes': pendientes
                },
                'top_empresas': [
                    {'nombre': nombre, 'total': total}
                    for nombre, total in top_empresas
                ]
            }
        })
        
    except Exception as e:
        print(f"Error en stats-graficos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/tendencias', methods=['GET'])
@login_required
def get_tendencias():
    """
    Tendencias y comparativas
    Filtrado por gestoría del usuario actual
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # Comparar mes actual vs mes anterior
        hoy = datetime.now()
        inicio_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_mes_anterior = (inicio_mes_actual - timedelta(days=1)).replace(day=1)
        
        docs_mes_actual = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            Documento.fecha_procesado >= inicio_mes_actual,
            Documento.fecha_procesado.isnot(None)
        ).count()
        
        docs_mes_anterior = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            Documento.fecha_procesado >= inicio_mes_anterior,
            Documento.fecha_procesado < inicio_mes_actual,
            Documento.fecha_procesado.isnot(None)
        ).count()
        
        # Calcular porcentaje de cambio
        if docs_mes_anterior > 0:
            cambio_porcentaje = ((docs_mes_actual - docs_mes_anterior) / docs_mes_anterior) * 100
        else:
            cambio_porcentaje = 100 if docs_mes_actual > 0 else 0
        
        return jsonify({
            'success': True,
            'data': {
                'mes_actual': docs_mes_actual,
                'mes_anterior': docs_mes_anterior,
                'cambio_porcentaje': round(cambio_porcentaje, 1),
                'tendencia': 'subida' if cambio_porcentaje > 0 else 'bajada' if cambio_porcentaje < 0 else 'estable'
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/dashboard/tareas-por-origen', methods=['GET'])
@login_required
def get_tareas_por_origen():
    """
    Distribución de tareas por origen (manual, chat_ia, etc.)
    Filtrado por gestoría del usuario actual
    """
    try:
        gestoria_id = get_current_gestoria_id()
        
        # Contar tareas por origen
        tareas_por_origen = db.session.query(
            Tarea.origen,
            func.count(Tarea.id).label('total')
        ).filter(
            Tarea.gestoria_id == gestoria_id
        ).group_by(Tarea.origen).all()
        
        return jsonify([
            {'origen': origen or 'manual', 'total': total}
            for origen, total in tareas_por_origen
        ])
        
    except Exception as e:
        print(f"Error en tareas-por-origen: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# ENDPOINTS PARA SUPERADMIN
# ============================================

@dashboard_bp.route('/api/admin/dashboard/global', methods=['GET'])
@login_required
@super_admin_required
def get_stats_global():
    """
    Stats globales de todas las gestorías
    Solo para superadmin
    """
    try:
        # 1. Stats por gestoría
        stats_por_gestoria = db.session.query(
            Gestoria.nombre,
            func.count(Documento.id).label('total_docs'),
            func.count(case((Documento.fecha_procesado.isnot(None), 1))).label('procesados'),
            func.count(case((Documento.categoria == DocumentCategories.POR_PROCESAR, 1))).label('pendientes')
        ).outerjoin(Empresa, Gestoria.id == Empresa.gestoria_id
        ).outerjoin(Documento, Empresa.id == Documento.empresa_id
        ).group_by(Gestoria.id).all()
        
        # 2. Total de usuarios por gestoría
        usuarios_por_gestoria = db.session.query(
            Gestoria.nombre,
            func.count(User.id).label('total_usuarios')
        ).outerjoin(User, Gestoria.id == User.gestoria_id
        ).group_by(Gestoria.id).all()
        
        # 3. Documentos procesados por mes (todas las gestorías)
        seis_meses_atras = datetime.now() - timedelta(days=180)
        docs_globales_por_mes = db.session.query(
            func.to_char(Documento.fecha_procesado, 'YYYY-MM').label('mes'),
            func.count(Documento.id).label('total')
        ).filter(
            Documento.fecha_procesado >= seis_meses_atras,
            Documento.fecha_procesado.isnot(None)
        ).group_by(
            func.to_char(Documento.fecha_procesado, 'YYYY-MM')
        ).order_by('mes').all()
        
        # 4. Top gestorías por actividad
        top_gestorias = db.session.query(
            Gestoria.nombre,
            func.count(Documento.id).label('total')
        ).outerjoin(Empresa, Gestoria.id == Empresa.gestoria_id
        ).outerjoin(Documento, Empresa.id == Documento.empresa_id
        ).group_by(Gestoria.id).order_by(
            func.count(Documento.id).desc()
        ).limit(10).all()
        
        # 5. Resumen global
        total_gestorias = Gestoria.query.count()
        total_usuarios = User.query.count()
        total_empresas = Empresa.query.count()
        total_documentos = Documento.query.count()
        
        return jsonify({
            'success': True,
            'data': {
                'stats_por_gestoria': [
                    {
                        'nombre': nombre,
                        'total_docs': total_docs,
                        'procesados': procesados,
                        'pendientes': pendientes
                    }
                    for nombre, total_docs, procesados, pendientes in stats_por_gestoria
                ],
                'usuarios_por_gestoria': [
                    {'nombre': nombre, 'total': total}
                    for nombre, total in usuarios_por_gestoria
                ],
                'docs_globales_por_mes': [
                    {'mes': mes, 'total': total}
                    for mes, total in docs_globales_por_mes
                ],
                'top_gestorias': [
                    {'nombre': nombre, 'total': total}
                    for nombre, total in top_gestorias
                ],
                'resumen': {
                    'total_gestorias': total_gestorias,
                    'total_usuarios': total_usuarios,
                    'total_empresas': total_empresas,
                    'total_documentos': total_documentos
                }
            }
        })
        
    except Exception as e:
        print(f"Error en stats-global: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/api/admin/dashboard/comparativa', methods=['GET'])
@login_required
@super_admin_required
def get_comparativa_gestorias():
    """
    Comparativa entre gestorías
    Solo para superadmin
    """
    try:
        # Obtener todas las gestorías con sus métricas
        gestorias = db.session.query(
            Gestoria.id,
            Gestoria.nombre,
            func.count(func.distinct(Empresa.id)).label('total_empresas'),
            func.count(func.distinct(User.id)).label('total_usuarios'),
            func.count(Documento.id).label('total_documentos')
        ).outerjoin(Empresa, Gestoria.id == Empresa.gestoria_id
        ).outerjoin(User, Gestoria.id == User.gestoria_id
        ).outerjoin(Documento, Empresa.id == Documento.empresa_id
        ).group_by(Gestoria.id).all()
        
        return jsonify({
            'success': True,
            'data': [
                {
                    'id': id,
                    'nombre': nombre,
                    'empresas': empresas,
                    'usuarios': usuarios,
                    'documentos': documentos,
                    'docs_por_empresa': round(documentos / empresas, 1) if empresas > 0 else 0
                }
                for id, nombre, empresas, usuarios, documentos in gestorias
            ]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
