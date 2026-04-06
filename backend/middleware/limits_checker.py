"""
Middleware para verificación de límites de gestorías
"""
from flask import jsonify, request
from functools import wraps
from models import db, GestoriaPlan, UsoGestoria, User, Empresa, AuditoriaAccesoGestoria
from datetime import datetime

class LimitExceededError(Exception):
    """Excepción cuando se excede un límite"""
    pass

def get_uso_actual(gestoria_id):
    """Obtiene el uso actual del mes para una gestoría"""
    periodo = datetime.now().strftime('%Y-%m')
    uso = UsoGestoria.query.filter_by(
        gestoria_id=gestoria_id,
        periodo=periodo
    ).first()
    
    if not uso:
        # Crear registro de uso para este mes
        uso = UsoGestoria(
            gestoria_id=gestoria_id,
            periodo=periodo
        )
        db.session.add(uso)
        db.session.commit()
    
    return uso

def check_limite_usuarios(gestoria_id):
    """Verifica si se puede crear un nuevo usuario"""
    plan = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
    if not plan:
        raise LimitExceededError("Gestoría sin plan asignado")
    
    usuarios_count = User.query.filter_by(gestoria_id=gestoria_id).count()
    
    if usuarios_count >= plan.plan.usuarios_max:
        raise LimitExceededError(
            f"Límite de usuarios alcanzado ({plan.plan.usuarios_max}). "
            f"Actualice su plan para agregar más usuarios."
        )
    
    return True

def check_limite_empresas(gestoria_id):
    """Verifica si se puede crear una nueva empresa"""
    plan = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
    if not plan:
        raise LimitExceededError("Gestoría sin plan asignado")
    
    empresas_count = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
    
    if empresas_count >= plan.plan.empresas_max:
        raise LimitExceededError(
            f"Límite de empresas alcanzado ({plan.plan.empresas_max}). "
            f"Actualice su plan para agregar más empresas."
        )
    
    return True

def check_limite_tokens_ia(gestoria_id, tokens_a_usar):
    """Verifica si hay tokens de IA disponibles"""
    plan = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
    if not plan:
        raise LimitExceededError("Gestoría sin plan asignado")
    
    uso = get_uso_actual(gestoria_id)
    
    if uso.tokens_ia_usados + tokens_a_usar > plan.plan.tokens_ia_mes:
        raise LimitExceededError(
            f"Límite de tokens IA alcanzado ({plan.plan.tokens_ia_mes}/mes). "
            f"Actualice su plan o espere al próximo mes."
        )
    
    return True

def registrar_uso_tokens_ia(gestoria_id, tokens_usados):
    """Registra el uso de tokens de IA"""
    uso = get_uso_actual(gestoria_id)
    uso.tokens_ia_usados += tokens_usados
    uso.fecha_actualizacion = datetime.utcnow()
    db.session.commit()

def auditar_acceso(usuario_id, gestoria_destino, recurso_tipo, recurso_id, accion, permitido):
    """Registra un intento de acceso en la auditoría"""
    from flask_login import current_user
    
    auditoria = AuditoriaAccesoGestoria(
        usuario_id=usuario_id,
        gestoria_origen=current_user.gestoria_id if current_user.is_authenticated else None,
        gestoria_destino=gestoria_destino,
        recurso_tipo=recurso_tipo,
        recurso_id=recurso_id,
        accion=accion,
        permitido=permitido,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    db.session.add(auditoria)
    db.session.commit()

def require_gestoria_access(f):
    """Decorator que valida acceso a recursos de gestoría"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        # Obtener gestoria_id del request
        gestoria_id = kwargs.get('gestoria_id') or (request.json.get('gestoria_id') if request.json else None)
        
        # Super-admin puede acceder a todo
        if current_user.is_super_admin:
            return f(*args, **kwargs)
        
        # Validar que el usuario pertenece a la gestoría
        if gestoria_id and current_user.gestoria_id != gestoria_id:
            # Registrar intento no autorizado
            auditar_acceso(
                current_user.id,
                gestoria_id,
                'unknown',
                None,
                request.method,
                False
            )
            return jsonify({'error': 'Acceso denegado a recursos de otra gestoría'}), 403
        
        return f(*args, **kwargs)
    return decorated_function
