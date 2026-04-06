# backend/tenant_utils.py
"""
Utilidades para manejo de multi-tenancy (gestorías)
Proporciona funciones para obtener y gestionar el contexto de gestoría actual
"""

from flask import g
from flask_login import current_user


def get_current_gestoria_id():
    """
    Obtiene el gestoria_id del usuario actual de forma segura.

    Orden de prioridad:
    0. Sesión de impersonación activa (soporte/super_admin viendo otra gestoría)
    1. Flask.g.gestoria_id (si está explícitamente establecido)
    2. current_user.gestoria_id (usuario autenticado)
    3. Fallback a 1 (para procesos sin usuario como Celery)

    Returns:
        int: ID de la gestoría actual

    Usage:
        gestoria_id = get_current_gestoria_id()
        empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
    """
    # 0. Impersonación activa: usar la gestoría impersonada
    try:
        from flask import session
        imp_id = session.get('impersonando_gestoria_id')
        if imp_id:
            return imp_id
    except Exception:
        pass

    # 1. Verificar si ya está en el contexto de Flask
    if hasattr(g, 'gestoria_id'):
        return g.gestoria_id
    
    # 2. Obtener del usuario autenticado (verificar que existe primero)
    if current_user and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        if hasattr(current_user, 'gestoria_id'):
            # Cachear en g para evitar múltiples accesos
            g.gestoria_id = current_user.gestoria_id
            return g.gestoria_id
    
    # 3. Sin contexto válido: en producción lanzar excepción; en desarrollo
    #    hacer fallback a gestoria 1 para no romper scripts locales.
    import logging
    import os
    logger = logging.getLogger(__name__)

    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError(
            "get_current_gestoria_id() llamada sin contexto de usuario ni g.gestoria_id. "
            "En tareas Celery usa set_gestoria_context(gestoria_id) antes de operar."
        )

    logger.warning(
        "get_current_gestoria_id() sin contexto — fallback a gestoria 1 (solo desarrollo). "
        "En Celery usa set_gestoria_context(gestoria_id)."
    )
    return 1


def set_gestoria_context(gestoria_id):
    """
    Establece explícitamente el contexto de gestoría.
    Útil para tareas de Celery o scripts que no tienen current_user.
    
    Args:
        gestoria_id (int): ID de la gestoría a establecer
    
    Usage:
        # En una tarea de Celery
        set_gestoria_context(gestoria_id)
        # Ahora get_current_gestoria_id() devolverá este valor
    """
    g.gestoria_id = gestoria_id


def clear_gestoria_context():
    """
    Limpia el contexto de gestoría.
    Útil para testing o cuando se necesita resetear el contexto.
    """
    if hasattr(g, 'gestoria_id'):
        delattr(g, 'gestoria_id')


def require_gestoria_ownership(model_instance):
    """
    Verifica que el modelo pertenezca a la gestoría del usuario actual.
    Lanza excepción si no coincide.
    
    Args:
        model_instance: Instancia de modelo con gestoria_id
    
    Raises:
        PermissionError: Si el modelo no pertenece a la gestoría actual
    
    Usage:
        empresa = Empresa.query.get(empresa_id)
        require_gestoria_ownership(empresa)  # Lanza error si no es de la gestoría
    """
    if not hasattr(model_instance, 'gestoria_id'):
        raise ValueError(f"El modelo {type(model_instance).__name__} no tiene gestoria_id")
    
    current_gestoria = get_current_gestoria_id()
    
    if model_instance.gestoria_id != current_gestoria:
        raise PermissionError(
            f"Acceso denegado: {type(model_instance).__name__} pertenece a otra gestoría"
        )


def filter_by_gestoria(query):
    """
    Agrega filtro de gestoría a una query de SQLAlchemy.
    
    Args:
        query: Query de SQLAlchemy
    
    Returns:
        Query filtrada por gestoria_id
    
    Usage:
        # En lugar de:
        empresas = Empresa.query.all()
        
        # Usar:
        empresas = filter_by_gestoria(Empresa.query).all()
    """
    gestoria_id = get_current_gestoria_id()
    return query.filter_by(gestoria_id=gestoria_id)


def safe_query(model_class):
    """
    Retorna una query pre-filtrada por la gestoría actual.
    Sintaxis más limpia que filter_by_gestoria().
    
    Args:
        model_class: Clase del modelo (ej: Empresa, Documento, Tarea)
    
    Returns:
        Query filtrada por gestoria_id de la gestoría actual
    
    Usage:
        # En lugar de:
        tareas = Tarea.query.filter(Tarea.estado == 'Pendiente').all()
        
        # Usar:
        from tenant_utils import safe_query
        tareas = safe_query(Tarea).filter(Tarea.estado == 'Pendiente').all()
        
    Example:
        # Listar empresas de la gestoría actual
        empresas = safe_query(Empresa).all()
        
        # Buscar con filtros adicionales
        tareas_pendientes = safe_query(Tarea).filter(
            Tarea.estado == 'Pendiente',
            Tarea.prioridad == 'Alta'
        ).all()
    """
    gestoria_id = get_current_gestoria_id()
    return model_class.query.filter(model_class.gestoria_id == gestoria_id)


# Decorator para rutas que requieren aislamiento de gestoría
def tenant_isolated(f):
    """
    Decorator para asegurar que una ruta está aislada por gestoría.
    Agrega el gestoria_id al contexto de Flask.
    
    Usage:
        @app.route('/api/empresas')
        @login_required
        @tenant_isolated
        def listar_empresas():
            # get_current_gestoria_id() funcionará correctamente
            empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).all()
            return jsonify([e.to_dict() for e in empresas])
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Asegurar que el contexto de gestoría está establecido
        if not hasattr(g, 'gestoria_id'):
            get_current_gestoria_id()  # Esto lo establecerá en g
        
        return f(*args, **kwargs)
    
    return decorated_function
