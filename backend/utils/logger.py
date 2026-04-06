"""
Logger Utility - Sistema de logging profesional para Flask

Uso:
    from utils.logger import logger
    
    logger.debug("Mensaje de debug")
    logger.info("Información general")
    logger.warning("Advertencia")
    logger.error("Error")
    logger.critical("Error crítico")
"""

import logging
import os
from datetime import datetime

# Configuración desde variables de entorno
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG' if DEBUG else 'WARNING')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'False').lower() == 'true'
LOG_FILE = os.getenv('LOG_FILE', 'logs/app.log')

# Crear logger
logger = logging.getLogger('iages')

# Configurar nivel
level = getattr(logging, LOG_LEVEL.upper(), logging.WARNING)
logger.setLevel(level)

# Evitar duplicación de handlers
if not logger.handlers:
    # Formato de logs
    if DEBUG:
        # Formato detallado para desarrollo
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Formato simple para producción
        formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )

    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para archivo (opcional)
    if LOG_TO_FILE:
        # Crear directorio de logs si no existe
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

# Funciones helper para mantener compatibilidad con prints existentes
def log_success(message):
    """Log de éxito (con emoji)"""
    logger.info(f"✅ {message}")

def log_error(message):
    """Log de error (con emoji)"""
    logger.error(f"❌ {message}")

def log_warning(message):
    """Log de advertencia (con emoji)"""
    logger.warning(f"⚠️ {message}")

def log_info(message):
    """Log de información (con emoji)"""
    logger.info(f"ℹ️ {message}")

def log_debug(message):
    """Log de debug (con emoji)"""
    logger.debug(f"🔧 {message}")

# Log inicial
if DEBUG:
    logger.info("=" * 50)
    logger.info("🚀 IAGES Dashboard - Modo Desarrollo")
    logger.info(f"📊 Nivel de log: {LOG_LEVEL}")
    logger.info(f"📁 Log a archivo: {LOG_TO_FILE}")
    logger.info("=" * 50)
