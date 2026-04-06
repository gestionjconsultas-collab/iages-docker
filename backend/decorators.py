# backend/decorators.py
"""
Decoradores personalizados para verificar permisos
"""

from functools import wraps
from flask import jsonify
from flask_login import current_user
from constants import DocumentCategories, NotificationTypes

def admin_required(f):
    """
    Decorador que verifica si el usuario tiene rol de Jefatura (Administrador)
    O si es un Administrador de Grupo (Invitado con grupos gestionados)
    Uso: @admin_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar que el usuario esté autenticado
        if not current_user.is_authenticated:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "No autenticado. Por favor inicia sesión."
            }), 401

        # Verificar que el usuario tenga departamento asignado
        if not current_user.departamento:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Tu usuario no tiene un departamento asignado. Contacta al administrador."
            }), 403

        # FIX A-13: Normalizar nombre de departamento (case-insensitive)
        dept_nombre = current_user.departamento.nombre.strip().lower()

        # FIX A-3: bool() garantiza que lista vacía [] sea False
        is_jefatura = dept_nombre == 'jefatura'
        is_admin_grupo = bool(current_user.get_managed_group_ids())
        is_super_admin = getattr(current_user, 'is_super_admin', False)

        if not (is_jefatura or is_admin_grupo or is_super_admin):
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Acceso denegado. Solo los administradores pueden realizar esta acción."
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def departamento_required(departamentos_permitidos):
    """
    Decorador que verifica si el usuario pertenece a uno de los departamentos permitidos

    Uso:
    @departamento_required([DocumentCategories.FISCAL, 'Jefatura'])
    def mi_funcion():
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

            if not current_user.departamento:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "Usuario sin departamento asignado"
                }), 403

            dept_nombre = current_user.departamento.nombre.strip()

            # FIX C-1: Soporte externo (gestoria_id NULL) solo accede si 'Soporte'
            # está explícitamente en la lista de departamentos permitidos del endpoint.
            # Ya no tiene bypass total — debe estar autorizado como cualquier otro dept.
            if current_user.gestoria_id is None and dept_nombre == 'Soporte':
                # FIX A-13: Comparación case-insensitive
                permitidos_norm = [d.strip().lower() for d in departamentos_permitidos]
                if 'soporte' in permitidos_norm:
                    return f(*args, **kwargs)
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "Acceso denegado. Operación no permitida para soporte externo."
                }), 403

            # FIX A-13: Comparación case-insensitive para todos los usuarios
            permitidos_norm = [d.strip().lower() for d in departamentos_permitidos]
            if dept_nombre.lower() not in permitidos_norm:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: f"Acceso denegado. Se requiere uno de estos departamentos: {', '.join(departamentos_permitidos)}"
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator

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
