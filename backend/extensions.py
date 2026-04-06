# backend/extensions.py
"""
Inicialización de extensiones Flask
"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from prometheus_flask_exporter import PrometheusMetrics
from constants import NotificationTypes
from flask_socketio import SocketIO
socketio = SocketIO()

# Base de datos
db = SQLAlchemy()

# Autenticación
bcrypt = Bcrypt()
login_manager = LoginManager()

# Rate Limiting - CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5000 per day", "2000 per hour", "100 per minute"],  # ⚠️ SEGURIDAD: Límites aumentados para evitar 429 falsos positivos
    storage_uri="redis://localhost:6379/0",
    strategy="fixed-window",
    swallow_errors=True  # No romper la app si Redis falla
)

# Caché
cache = Cache()

# Métricas
metrics = PrometheusMetrics.for_app_factory()


def init_extensions(app):
    """Inicializa todas las extensiones con la app Flask"""
    
    # Base de datos
    db.init_app(app)
    
    # Autenticación
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    
    # Rate Limiting
    limiter.init_app(app)
    
    # Caché
    cache.init_app(app)
    
    # Configurar login manager
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return db.session.get(User, int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify
        return jsonify({
            NotificationTypes.SUCCESS: False, 
            NotificationTypes.ERROR: "No hay sesión activa."
        }), 401
    
    return app