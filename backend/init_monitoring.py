# backend/init_monitoring.py
"""
Inicialización de todas las funcionalidades de monitoreo y documentación
"""

def init_monitoring_features(app):
    """
    Inicializa todas las funcionalidades de monitoreo:
    - Compresión HTTP
    - Sentry (si está configurado)
    - Swagger API docs
    - Prometheus metrics

    Args:
        app: Instancia de Flask
    """
    # 1. Compresión HTTP - PROBANDO
    try:
        from config_compress import init_compress
        compress = init_compress(app)
        app.logger.info("✅ Compresión HTTP activada")
    except Exception as e:
        app.logger.warning(f"⚠️ No se pudo activar compresión: {e}")

    # 2. Sentry (opcional - solo si SENTRY_DSN está configurado)
    try:
        from config_sentry import init_sentry
        sentry = init_sentry(app)
        if sentry:
            app.logger.info("✅ Sentry activado")
    except Exception as e:
        app.logger.warning(f"⚠️ Sentry no disponible: {e}")

    # 3. Swagger API Documentation - ⚠️ DESACTIVADO: Interfiere con sesiones de login
    # try:
    #     from config_swagger import init_swagger
    #     api = init_swagger(app)
    #     app.logger.info("✅ Swagger UI disponible en /api/docs")
    # except Exception as e:
    #     app.logger.warning(f"⚠️ Swagger no disponible: {e}")

    # 4. Prometheus Metrics
    try:
        from config_prometheus import init_prometheus
        metrics = init_prometheus(app)
        app.logger.info("✅ Prometheus metrics disponibles en /metrics")
    except Exception as e:
        app.logger.warning(f"⚠️ Prometheus no disponible: {e}")

    app.logger.info("🎉 Funcionalidades de monitoreo inicializadas")
