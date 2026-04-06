# backend/routes_monitoring.py
"""
Dashboard de Monitoreo para Super-Admin
Visualización de métricas de Prometheus y configuración de alertas
"""

from flask import jsonify, request, render_template_string
from flask_login import login_required, current_user
from decorators import super_admin_required
import requests
from datetime import datetime, timedelta
from models import db, AuditoriaLog, Documento, User
from sqlalchemy import func, desc, text
import logging

logger = logging.getLogger(__name__)


def register_monitoring_routes(app):
    """Registrar rutas de monitoreo para super-admin"""
    
    @app.route('/api/admin/monitoring/metrics', methods=['GET'])
    @login_required
    @super_admin_required
    def get_prometheus_metrics():
        """
        Obtener métricas de Prometheus parseadas
        Solo accesible por super-admin
        """
        try:
            # Obtener métricas raw de Prometheus
            response = requests.get('http://localhost:5000/metrics', timeout=5)
            
            if response.status_code != 200:
                return jsonify({'error': 'No se pudieron obtener métricas'}), 500
            
            # Parsear métricas relevantes
            metrics_text = response.text
            metrics = parse_prometheus_metrics(metrics_text)
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/admin/monitoring/dashboard', methods=['GET'])
    @login_required
    @super_admin_required
    def get_monitoring_dashboard():
        """
        Dashboard completo de monitoreo
        Incluye métricas, estadísticas y alertas
        """
        try:
            # 1. Estadísticas de sistema
            total_users = User.query.count()
            total_docs = Documento.query.count()
            
            # Documentos procesados hoy
            hoy = datetime.utcnow().date()
            docs_hoy = db.session.query(func.count(Documento.id)).filter(
                Documento.fecha_procesado != None,
                func.date(Documento.fecha_procesado) == hoy
            ).scalar() or 0           
            # Actividad de auditoría (últimas 24h)
            hace_24h = datetime.utcnow() - timedelta(hours=24)
            actividad_24h = AuditoriaLog.query.filter(
                AuditoriaLog.fecha_creacion >= hace_24h
            ).count()
            
            # 2. Top usuarios más activos (última semana)
            hace_7_dias = datetime.utcnow() - timedelta(days=7)
            top_usuarios = db.session.query(
                AuditoriaLog.user_nombre,
                func.count(AuditoriaLog.id).label('acciones')
            ).filter(
                AuditoriaLog.fecha_creacion >= hace_7_dias
            ).group_by(
                AuditoriaLog.user_nombre
            ).order_by(desc('acciones')).limit(5).all()
            
            # 3. Errores recientes (últimas 24h)
            errores_recientes = AuditoriaLog.query.filter(
                AuditoriaLog.fecha_creacion >= hace_24h,
                AuditoriaLog.accion.like('%ERROR%')
            ).order_by(desc(AuditoriaLog.fecha_creacion)).limit(10).all()
            
            # 4. Estado del sistema
            system_status = {
                'database': 'healthy',
                'redis': 'healthy',  # TODO: Verificar Redis
                'celery': 'healthy',  # TODO: Verificar Celery
                'sentry': 'active' if app.config.get('SENTRY_DSN') else 'inactive'
            }
            
            return jsonify({
                'success': True,
                'dashboard': {
                    'statistics': {
                        'total_users': total_users,
                        'total_documents': total_docs,
                        'documents_today': docs_hoy,
                        'activity_24h': actividad_24h
                    },
                    'top_users': [
                        {'nombre': u, 'acciones': a} for u, a in top_usuarios
                    ],
                    'recent_errors': [
                        {
                            'id': e.id,
                            'accion': e.accion,
                            'descripcion': e.descripcion,
                            'fecha': e.fecha_creacion.isoformat(),
                            'user': e.user_nombre
                        } for e in errores_recientes
                    ],
                    'system_status': system_status
                }
            })
            
        except Exception as e:
            logger.error(f"Error en dashboard de monitoreo: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/admin/monitoring/alerts', methods=['GET'])
    @login_required
    @super_admin_required
    def get_alerts():
        """
        Obtener alertas activas del sistema
        """
        try:
            alerts = []
            
            # Alerta 1: Documentos sin procesar (>100)
            docs_pendientes = Documento.query.filter_by(
                categoria='Por Procesar'
            ).count()
            
            if docs_pendientes > 100:
                alerts.append({
                    'level': 'warning',
                    'title': 'Documentos pendientes',
                    'message': f'{docs_pendientes} documentos sin procesar',
                    'action': 'Revisar cola de procesamiento'
                })
            
            # Alerta 2: Errores recientes (>10 en última hora)
            hace_1h = datetime.utcnow() - timedelta(hours=1)
            errores_1h = AuditoriaLog.query.filter(
                AuditoriaLog.fecha_creacion >= hace_1h,
                AuditoriaLog.accion.like('%ERROR%')
            ).count()
            
            if errores_1h > 10:
                alerts.append({
                    'level': 'error',
                    'title': 'Alto nivel de errores',
                    'message': f'{errores_1h} errores en la última hora',
                    'action': 'Revisar logs de Sentry'
                })
            
            # Alerta de usuarios inactivos - DESACTIVADA (User no tiene ultimo_login)
            # hace_30_dias = datetime.now() - timedelta(days=30)
            # usuarios_inactivos = db.session.query(func.count(User.id)).filter(
            #     User.ultimo_login < hace_30_dias
            # ).scalar() or 0
            # 
            # if usuarios_inactivos > 5:
            #     alerts.append({
            #         'level': 'info',
            #         'title': 'Usuarios inactivos',
            #         'message': f'{usuarios_inactivos} usuarios sin login en 30+ días',
            #         'action': 'Considerar desactivar cuentas inactivas'
            #     })
            
            return jsonify({
                'success': True,
                'alerts': alerts,
                'count': len(alerts)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    @app.route('/api/admin/monitoring/health', methods=['GET'])
    @login_required
    @super_admin_required
    def admin_health_check():
        """
        Health check profundo del sistema para admin
        """
        try:
            health = {
                'status': 'healthy',
                'checks': {}
            }
            
            # Check 1: Database
            try:
                db.session.execute(text('SELECT 1'))
                health['checks']['database'] = {
                    'status': 'healthy',
                    'message': 'Conexión exitosa'
                }
            except Exception as e:
                health['checks']['database'] = {
                    'status': 'unhealthy',
                    'message': str(e)
                }
                health['status'] = 'degraded'
            
            # Check 2: Prometheus (solo si está habilitado)
            try:
                response = requests.get('http://localhost:5000/metrics', timeout=1)
                if response.status_code == 200:
                    health['checks']['prometheus'] = {
                        'status': 'healthy',
                        'message': f'Status: {response.status_code}'
                    }
                else:
                    health['checks']['prometheus'] = {
                        'status': 'unhealthy',
                        'message': f'Status: {response.status_code}'
                    }
            except requests.exceptions.Timeout:
                health['checks']['prometheus'] = {
                    'status': 'inactive',
                    'message': 'Timeout - Prometheus desactivado o no disponible'
                }
            except Exception as e:
                health['checks']['prometheus'] = {
                    'status': 'inactive',
                    'message': 'No disponible'
                }
            
            # Check 3: Sentry
            health['checks']['sentry'] = {
                'status': 'active' if app.config.get('SENTRY_DSN') else 'inactive',
                'message': 'Configurado' if app.config.get('SENTRY_DSN') else 'No configurado'
            }
            
            return jsonify({
                'success': True,
                'health': health,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error en health check: {e}")
            return jsonify({'error': str(e)}), 500
    
    
    logger.info("✅ Rutas de Monitoreo registradas")


def parse_prometheus_metrics(metrics_text):
    """
    Parsear métricas de Prometheus a formato JSON
    """
    metrics = {
        'http_requests': {},
        'system': {},
        'custom': {}
    }
    
    lines = metrics_text.split('\n')
    
    for line in lines:
        if line.startswith('#') or not line.strip():
            continue
        
        # Parsear líneas de métricas
        if 'flask_http_request_total' in line:
            metrics['http_requests']['total'] = extract_value(line)
        elif 'flask_http_request_duration_seconds' in line:
            metrics['http_requests']['duration'] = extract_value(line)
        elif 'python_info' in line:
            metrics['system']['python_version'] = extract_label(line, 'version')
        elif 'flask_exporter_info' in line:
            metrics['system']['exporter_version'] = extract_label(line, 'version')
    
    return metrics


def extract_value(line):
    """Extraer valor numérico de línea de métrica"""
    try:
        return float(line.split()[-1])
    except:
        return 0.0


def extract_label(line, label_name):
    """Extraer valor de label de métrica"""
    try:
        import re
        match = re.search(f'{label_name}="([^"]+)"', line)
        return match.group(1) if match else 'unknown'
    except:
        return 'unknown'
