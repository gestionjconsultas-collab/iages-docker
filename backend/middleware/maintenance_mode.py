# middleware/maintenance_mode.py
"""
Middleware para modo de mantenimiento
Bloquea el acceso al sistema excepto para super-admins
"""

from functools import wraps
from flask import jsonify, request, g
from flask_login import current_user

def check_maintenance_mode():
    """
    Middleware que verifica el modo de mantenimiento antes de cada request
    Permite bypass para super-admins y endpoints públicos necesarios
    """
    # Importar aquí para evitar import circular
    from models import SystemConfig
    
    # Verificar si está en modo mantenimiento
    if not SystemConfig.is_maintenance_mode():
        return None  # Continuar normalmente
    
    # Permitir acceso a super-admins
    if current_user.is_authenticated and current_user.is_super_admin:
        # Agregar flag para mostrar banner en frontend
        g.maintenance_mode = True
        g.is_super_admin_bypass = True
        return None
    
    # Lista de endpoints públicos permitidos durante mantenimiento
    allowed_endpoints = [
        '/api/auth/login',
        '/api/auth/logout',
        '/api/maintenance/status',
        '/maintenance',  # Permitir acceso a la página de mantenimiento
        '/static/',
        '/favicon.ico',
        '/_debug_toolbar/',  # Para desarrollo
    ]
    
    # Permitir acceso a endpoints públicos
    if any(request.path.startswith(endpoint) for endpoint in allowed_endpoints):
        return None
    
    # Bloquear acceso - retornar error 503
    message = SystemConfig.get_maintenance_message()
    
    return jsonify({
        'error': 'Sistema en mantenimiento',
        'message': message,
        'maintenance': True,
        'status': 503
    }), 503


def maintenance_mode_decorator(f):
    """
    Decorador para aplicar check de mantenimiento a rutas específicas
    Uso: @maintenance_mode_decorator
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Importar aquí para evitar import circular
        from models import SystemConfig
        
        # Verificar modo mantenimiento
        if SystemConfig.is_maintenance_mode():
            # Permitir super-admins
            if not (current_user.is_authenticated and current_user.is_super_admin):
                message = SystemConfig.get_maintenance_message()
                return jsonify({
                    'error': 'Sistema en mantenimiento',
                    'message': message,
                    'maintenance': True
                }), 503
        
        return f(*args, **kwargs)
    
    return decorated_function
