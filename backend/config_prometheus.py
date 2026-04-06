# backend/config_prometheus.py
"""
Configuración de métricas Prometheus para Grafana
"""

from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge
import time
import os


def protect_metrics_endpoint(app):
    """Restringe /metrics a localhost o un Bearer token (METRICS_BEARER_TOKEN)."""
    metrics_token = os.environ.get('METRICS_BEARER_TOKEN')

    @app.before_request
    def _check_metrics_auth():
        from flask import request, abort
        if request.path != '/metrics':
            return
        # Localhost siempre permitido
        if request.remote_addr in ('127.0.0.1', '::1'):
            return
        # Bearer token si está configurado
        if metrics_token:
            auth = request.headers.get('Authorization', '')
            if auth == f'Bearer {metrics_token}':
                return
        abort(403)


def init_prometheus(app):
    """
    Inicializa Prometheus metrics para monitoreo
    
    Métricas disponibles en: /metrics
    
    Args:
        app: Instancia de Flask
    
    Returns:
        PrometheusMetrics instance or None if in Celery worker
    """
    try:
        # ✅ FIX: No inicializar Prometheus en workers de Celery
        import os
        if os.environ.get('CELERY_WORKER_RUNNING'):
            app.logger.info("⏭️ Saltando inicialización de Prometheus (Celery worker)")
            return None
            
        # ✅ GUARDIA: Verificar si ya existe el endpoint para evitar errores de duplicado
        for rule in app.url_map.iter_rules():
            if rule.endpoint == 'prometheus_metrics':
                app.logger.info("⏭️ Prometheus ya está inicializado, saltando...")
                return app.config.get('METRICS_OBJECT')
        
        # Configuración simple que funciona
        metrics = PrometheusMetrics.for_app_factory()
        metrics.init_app(app)
        
        # Información de la aplicación — wrapped to handle duplicate on worker restart
        try:
            metrics.info('app_info', 'IAGES Application', version='1.0.0')
        except Exception:
            pass  # Ya registrada por un worker anterior — es seguro ignorar
        
        def _safe_counter(name, description, labels=[]):
            try:
                return Counter(name, description, labels)
            except Exception:
                from prometheus_client import REGISTRY
                return REGISTRY._names_to_collectors.get(name)

        def _safe_histogram(name, description, labels=[]):
            try:
                return Histogram(name, description, labels)
            except Exception:
                from prometheus_client import REGISTRY
                return REGISTRY._names_to_collectors.get(name)

        def _safe_gauge(name, description, labels=[]):
            try:
                return Gauge(name, description, labels)
            except Exception:
                from prometheus_client import REGISTRY
                return REGISTRY._names_to_collectors.get(name)

        # Métricas personalizadas
        documentos_procesados = _safe_counter('documentos_procesados_total', 'Total de documentos procesados', ['gestoria_id', 'categoria'])
        gemini_errors = _safe_counter('gemini_errors_total', 'Total de errores de Gemini', ['error_type'])
        processing_time = _safe_histogram('documento_processing_seconds', 'Tiempo de procesamiento de documentos', ['tipo_documento'])
        documentos_pendientes = _safe_gauge('documentos_pendientes', 'Documentos pendientes de procesar', ['gestoria_id'])
        saltra_downloads = _safe_counter('saltra_downloads_total', 'Total de descargas de Saltra', ['gestoria_id', 'estado'])
        saltra_response_time = _safe_histogram('saltra_api_response_seconds', 'Tiempo de respuesta de Saltra API', ['endpoint'])
        usuarios_activos = _safe_gauge('usuarios_activos', 'Usuarios activos en el sistema', ['gestoria_id'])
        logins = _safe_counter('logins_total', 'Total de logins', ['gestoria_id', 'success'])
        storage_usage = _safe_gauge('storage_usage_gb', 'Uso de almacenamiento en GB', ['gestoria_id'])
        
        # Guardar métricas en app.config para acceso global
        app.config['METRICS'] = {
            'documentos_procesados': documentos_procesados,
            'gemini_errors': gemini_errors,
            'processing_time': processing_time,
            'documentos_pendientes': documentos_pendientes,
            'saltra_downloads': saltra_downloads,
            'saltra_response_time': saltra_response_time,
            'usuarios_activos': usuarios_activos,
            'logins': logins,
            'storage_usage': storage_usage,
        }
        
        app.logger.info("✅ Prometheus metrics inicializadas en /metrics")
        app.config['METRICS_OBJECT'] = metrics

        # Proteger /metrics tras inicializar las rutas
        protect_metrics_endpoint(app)

        return metrics
        
    except Exception as e:
        app.logger.error(f"❌ Error inicializando Prometheus: {e}")
        # No lanzar excepción, solo loguear para no romper la app
        return None


# ==========================================
# HELPERS PARA USAR MÉTRICAS
# ==========================================

def track_documento_procesado(gestoria_id, categoria):
    """Incrementa contador de documentos procesados"""
    from flask import current_app
    metrics = current_app.config.get('METRICS', {})
    if 'documentos_procesados' in metrics:
        metrics['documentos_procesados'].labels(
            gestoria_id=gestoria_id,
            categoria=categoria
        ).inc()


def track_gemini_error(error_type):
    """Incrementa contador de errores de Gemini"""
    from flask import current_app
    metrics = current_app.config.get('METRICS', {})
    if 'gemini_errors' in metrics:
        metrics['gemini_errors'].labels(error_type=error_type).inc()


def track_processing_time(tipo_documento):
    """Context manager para medir tiempo de procesamiento"""
    from flask import current_app
    
    class ProcessingTimer:
        def __enter__(self):
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            duration = time.time() - self.start
            metrics = current_app.config.get('METRICS', {})
            if 'processing_time' in metrics:
                metrics['processing_time'].labels(
                    tipo_documento=tipo_documento
                ).observe(duration)
    
    return ProcessingTimer()


def update_documentos_pendientes(gestoria_id, count):
    """Actualiza gauge de documentos pendientes"""
    from flask import current_app
    metrics = current_app.config.get('METRICS', {})
    if 'documentos_pendientes' in metrics:
        metrics['documentos_pendientes'].labels(
            gestoria_id=gestoria_id
        ).set(count)


def track_saltra_download(gestoria_id, estado):
    """Incrementa contador de descargas de Saltra"""
    from flask import current_app
    metrics = current_app.config.get('METRICS', {})
    if 'saltra_downloads' in metrics:
        metrics['saltra_downloads'].labels(
            gestoria_id=gestoria_id,
            estado=estado
        ).inc()


def track_login(gestoria_id, success):
    """Incrementa contador de logins"""
    from flask import current_app
    metrics = current_app.config.get('METRICS', {})
    if 'logins' in metrics:
        metrics['logins'].labels(
            gestoria_id=gestoria_id,
            success='true' if success else 'false'
        ).inc()
