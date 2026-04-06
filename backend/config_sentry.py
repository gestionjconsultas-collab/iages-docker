# backend/config_sentry.py
"""
Configuración de Sentry para monitoreo de errores
"""

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration
import os


def init_sentry(app):
    """
    Inicializa Sentry para captura de errores
    
    Para activar:
    1. Crear cuenta en sentry.io
    2. Crear proyecto Flask
    3. Copiar DSN
    4. Agregar a .env: SENTRY_DSN=https://...
    
    Args:
        app: Instancia de Flask
    """
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        app.logger.warning("⚠️ SENTRY_DSN no configurado - Sentry deshabilitado")
        return None
    
    environment = os.getenv('FLASK_ENV', 'production')
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        
        # Tasa de muestreo de errores (1.0 = 100%)
        traces_sample_rate=1.0 if environment == 'development' else 0.1,
        
        # Tasa de muestreo de performance (0.1 = 10%)
        profiles_sample_rate=0.1,
        
        # Entorno
        environment=environment,
        
        # Versión de la app
        release=os.getenv('APP_VERSION', '1.0.0'),
        
        # Enviar PII (Personally Identifiable Information)
        send_default_pii=False,
        
        # Capturar errores de SQL
        _experiments={
            "profiles_sample_rate": 0.1,
        },
    )
    
    app.logger.info(f"✅ Sentry inicializado - Entorno: {environment}")
    return sentry_sdk


def capture_exception(error, context=None):
    """
    Captura una excepción manualmente en Sentry
    
    Args:
        error: Excepción a capturar
        context: Contexto adicional (dict)
    
    Example:
        try:
            # código
        except Exception as e:
            capture_exception(e, {'user_id': user.id})
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(error)
    else:
        sentry_sdk.capture_exception(error)


def capture_message(message, level='info', context=None):
    """
    Captura un mensaje en Sentry
    
    Args:
        message: Mensaje a capturar
        level: Nivel ('info', 'warning', 'error')
        context: Contexto adicional
    
    Example:
        capture_message('Usuario intentó acceso no autorizado', 'warning', {
            'user_id': user.id,
            'ip': request.remote_addr
        })
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)
