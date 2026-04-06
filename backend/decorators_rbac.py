from functools import wraps
from flask import jsonify
from flask_login import current_user
from constants import NotificationTypes

def super_admin_required(f):
    """
    Decorador que verifica si el usuario es super-admin
    Uso: @super_admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "No autenticado"
            }), 401
        
        if not current_user.is_super_admin:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Acceso denegado. Solo super-administradores pueden realizar esta acción."
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def permiso_required(codigo_permiso):
    """
    Decorador que verifica si el usuario tiene un permiso específico
    
    Uso:
    @permiso_required('users.edit')
    def editar_usuario():
        ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "No autenticado"
                }), 401
            
            # Super-admin siempre tiene acceso
            if current_user.is_super_admin:
                return f(*args, **kwargs)
            
            # Verificar permiso específico
            if not current_user.tiene_permiso(codigo_permiso):
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: f"Acceso denegado. Se requiere el permiso: {codigo_permiso}"
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
