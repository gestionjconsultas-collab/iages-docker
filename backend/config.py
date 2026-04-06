# backend/config.py
import os
import redis
from datetime import timedelta

# 1. Detectar rutas dinámicas (MAGIA AQUÍ)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
DEFAULT_INBOX = os.path.join(STORAGE_DIR, '__INBOX_NO_CLASIFICADOS')

class Config:
    """Configuración base"""
    
    # Seguridad
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in environment variables")
    
    # Base de datos
    # Si no hay DB configurada, usa un archivo local gestion.db
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', f'sqlite:///{os.path.join(BASE_DIR, "gestion.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # connect_args solo aplica a PostgreSQL (SQLite no lo soporta)
    _db_uri = os.getenv('DATABASE_URI', '')
    _connect_args = {'connect_timeout': 10} if _db_uri.startswith('postgresql') else {}

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,      # Verificar conexión antes de usar
        'pool_recycle': 300,        # Reciclar conexiones cada 5 min
        'pool_size': 10,            # Máximo 10 conexiones por worker
        'max_overflow': 20,         # 20 conexiones extras en picos
        'pool_timeout': 30,         # Timeout 30s para obtener conexión
        'echo': False,              # No loguear SQL (rendimiento)
        'connect_args': _connect_args,
    }
    
    # APIs externas
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # 2FA / TOTP
    TOTP_ENCRYPTION_KEY = os.getenv('TOTP_ENCRYPTION_KEY')
    if not TOTP_ENCRYPTION_KEY:
        raise ValueError("TOTP_ENCRYPTION_KEY must be set in environment variables")
    TOTP_ENCRYPTION_KEY = TOTP_ENCRYPTION_KEY.encode()
    
    # --- RUTAS DEL SISTEMA (CORREGIDO) ---
    # Usa la variable de entorno SI EXISTE, si no, usa la carpeta 'storage' local
    RUTA_RAIZ_NOTIFICACIONES = os.getenv('RUTA_RAIZ_NOTIFICACIONES') or STORAGE_DIR
    RUTA_INBOX = os.getenv('RUTA_INBOX') or DEFAULT_INBOX
    # -------------------------------------
    
    # Configuración de archivos
    MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
    MAX_CONTENT_LENGTH = 150 * 1024 * 1024  # 150MB - Flask enforcement
    ALLOWED_EXTENSIONS = {'pdf'}
    UPLOAD_FOLDER = RUTA_INBOX
    
    # Configuración de Email/SMTP
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASS = os.getenv('SMTP_PASS')

    # Push Notifications
    VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY')
    VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY')
    VAPID_CLAIM_EMAIL = os.getenv('VAPID_CLAIM_EMAIL', 'admin@iages.com')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Session configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'iag:'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # ⚠️ IMPORTANTE: Configuración de cookies para CORS
    # Permite que las cookies funcionen entre frontend (3000) y backend (5000)
    SESSION_COOKIE_NAME = 'iag_sid'
    SESSION_COOKIE_HTTPONLY = True
    # FIX A-11: Secure=True por defecto — DevelopmentConfig lo sobreescribe a False para HTTP local
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Permite cookies cross-origin
    SESSION_COOKIE_DOMAIN = None  # None permite localhost:3000 y localhost:5000
    
    # Flask-Login
    REMEMBER_COOKIE_NAME = 'auth_t'
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True  # Sobreescrito a False en DevelopmentConfig
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = "1000 per day;200 per hour;30 per minute"  # ⚠️ SEGURIDAD: Sincronizado con extensions.py
    RATELIMIT_HEADERS_ENABLED = True
    RATELIMIT_SWALLOW_ERRORS = True
    
    # Caché
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'gestion_'
    
    # Celery
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    
    SESSION_REDIS = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    
    # En desarrollo no exigimos HTTPS, pero sí las demás protecciones
    SESSION_COOKIE_SECURE = False         # False para HTTP (localhost)
    SESSION_COOKIE_HTTPONLY = False       # False para permitir acceso desde JavaScript (necesario para SPA)
    SESSION_COOKIE_SAMESITE = 'Lax'       # Lax funciona mejor que None en localhost
    SESSION_COOKIE_DOMAIN = None          # None permite cookies en localhost
    REMEMBER_COOKIE_SECURE = False        # False para HTTP (localhost)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # ✅ NUEVO: Configuración de seguridad de sesiones
    SESSION_COOKIE_SECURE = True          # Solo transmitir por HTTPS
    SESSION_COOKIE_HTTPONLY = True        # No accesible desde JavaScript
    SESSION_COOKIE_SAMESITE = 'Lax'       # Protección CSRF
    REMEMBER_COOKIE_SECURE = True         # Cookies de "recuérdame" seguras
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Sesión de 24 horas


class TestingConfig(Config):
    """Configuración para tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}