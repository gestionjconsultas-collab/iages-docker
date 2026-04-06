# backend/middleware/billing_middleware.py
"""
Middleware para verificar límites de suscripción
"""
from flask import request, jsonify, g
from flask_login import current_user
from functools import wraps
from models_billing import Suscripcion
from services.billing_service import BillingService
from constants import NotificationTypes

def verificar_suscripcion_activa():
    """
    Middleware que verifica si la gestoría tiene suscripción activa
    Se ejecuta antes de cada request
    """
    # Rutas públicas que no requieren suscripción
    rutas_publicas = [
        '/api/login',
        '/api/logout',
        '/api/register',
        '/api/planes',
        '/api/suscripcion',
        '/api/suscripcion/cambiar-plan',
        '/api/datos-bancarios',
        '/api/facturas',
        '/static',
        '/uploads'
    ]
    
    # Si la ruta es pública, permitir
    for ruta in rutas_publicas:
        if request.path.startswith(ruta):
            return None
    
    # Si no hay usuario autenticado, permitir (el login_required se encargará)
    if not current_user.is_authenticated:
        return None
    
    # Verificar suscripción
    if not hasattr(current_user, 'gestoria_id') or not current_user.gestoria_id:
        return None
    
    suscripcion = Suscripcion.query.filter_by(gestoria_id=current_user.gestoria_id).first()
    
    # Si no hay suscripción o está suspendida/cancelada
    if not suscripcion or suscripcion.estado in ['suspendida', 'cancelada', 'vencida']:
        return jsonify({
            NotificationTypes.ERROR: 'Suscripción inactiva. Por favor, actualice su plan de pago.',
            'codigo': 'SUSCRIPCION_INACTIVA',
            'redirect': '/billing'
        }), 402  # Payment Required
    
    # Guardar suscripción en g para uso posterior
    g.suscripcion = suscripcion
    
    return None


def require_plan(*planes_requeridos):
    """
    Decorador que requiere un plan específico para acceder a un endpoint
    
    Uso:
        @require_plan('profesional', 'enterprise')
        def endpoint_premium():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({NotificationTypes.ERROR: 'No autenticado'}), 401
            
            if not hasattr(current_user, 'gestoria_id') or not current_user.gestoria_id:
                return jsonify({NotificationTypes.ERROR: 'Sin gestoría asignada'}), 403
            
            suscripcion = Suscripcion.query.filter_by(gestoria_id=current_user.gestoria_id).first()
            
            if not suscripcion or suscripcion.estado not in ['activa', 'trial']:
                return jsonify({
                    NotificationTypes.ERROR: 'Suscripción inactiva',
                    'codigo': 'SUSCRIPCION_INACTIVA'
                }), 402
            
            # Verificar si el plan actual está en la lista de planes requeridos
            plan_codigo = suscripcion.plan.codigo
            
            if plan_codigo not in planes_requeridos:
                return jsonify({
                    NotificationTypes.ERROR: f'Esta función requiere plan {" o ".join(planes_requeridos)}',
                    'codigo': 'PLAN_INSUFICIENTE',
                    'plan_actual': plan_codigo,
                    'planes_requeridos': list(planes_requeridos)
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def verificar_limite_recurso(recurso):
    """
    Decorador que verifica si se ha alcanzado el límite de un recurso
    
    Uso:
        @verificar_limite_recurso('empresas')
        def crear_empresa():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({NotificationTypes.ERROR: 'No autenticado'}), 401
            
            if not hasattr(current_user, 'gestoria_id') or not current_user.gestoria_id:
                return jsonify({NotificationTypes.ERROR: 'Sin gestoría asignada'}), 403
            
            # Verificar límite
            resultado = BillingService.verificar_limites(
                gestoria_id=current_user.gestoria_id,
                recurso=recurso
            )
            
            if not resultado.get('permitido'):
                return jsonify({
                    NotificationTypes.ERROR: f'Límite de {recurso} alcanzado',
                    'codigo': 'LIMITE_ALCANZADO',
                    'recurso': recurso,
                    'uso_actual': resultado.get('uso_actual'),
                    'limite': resultado.get('limite'),
                    'mensaje': f'Ha alcanzado el límite de {resultado.get("limite")} {recurso}. Actualice su plan para continuar.'
                }), 403
            
            # Advertencia si está cerca del límite (>80%)
            if resultado.get('porcentaje', 0) > 80:
                g.advertencia_limite = {
                    'recurso': recurso,
                    'porcentaje': resultado.get('porcentaje'),
                    'mensaje': f'Está usando el {resultado.get("porcentaje"):.0f}% de su límite de {recurso}'
                }
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_admin(f):
    """
    Decorador que requiere permisos de administrador
    
    Uso:
        @require_admin
        def endpoint_admin():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({NotificationTypes.ERROR: 'No autenticado'}), 401
        
        if not getattr(current_user, 'es_admin', False):
            return jsonify({
                NotificationTypes.ERROR: 'Permisos insuficientes',
                'codigo': 'NO_ADMIN'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
