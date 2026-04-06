"""
Utilidades para verificar límites de gestorías
Integración simplificada con el sistema existente
"""
from models import db, GestoriaPlan, UsoGestoria, User, Empresa
from datetime import datetime
from flask import current_app

def validate_gestoria_limit(gestoria_id, tipo_recurso):
    """
    Valida si una gestoría puede crear un nuevo recurso
    
    Args:
        gestoria_id: ID de la gestoría
        tipo_recurso: 'usuarios' o 'empresas'
    
    Returns:
        tuple: (puede_crear: bool, mensaje_error: str)
    """
    try:
        # Obtener plan de la gestoría
        plan = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
        
        if not plan:
            # Si no tiene plan, permitir (para compatibilidad)
            current_app.logger.warning(f"Gestoría {gestoria_id} sin plan asignado")
            return (True, None)
        
        if tipo_recurso == 'usuarios':
            # Contar usuarios actuales
            usuarios_count = User.query.filter_by(gestoria_id=gestoria_id).count()
            limite = plan.plan.usuarios_max
            
            if usuarios_count >= limite:
                return (False, f"Límite de usuarios alcanzado ({limite}). Actualice su plan para agregar más usuarios.")
            
            return (True, None)
            
        elif tipo_recurso == 'empresas':
            # Contar empresas actuales
            empresas_count = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
            limite = plan.plan.empresas_max
            
            if empresas_count >= limite:
                return (False, f"Límite de empresas alcanzado ({limite}). Actualice su plan para agregar más empresas.")
            
            return (True, None)
        
        else:
            return (True, None)
            
    except Exception as e:
        current_app.logger.error(f"Error validando límite: {e}")
        # En caso de error, permitir (para no bloquear operaciones)
        return (True, None)


def check_tokens_ia_disponibles(gestoria_id, tokens_a_usar):
    """
    Verifica si hay tokens de IA disponibles
    
    Returns:
        tuple: (tiene_disponibles: bool, mensaje_error: str)
    """
    try:
        plan = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
        
        if not plan:
            return (True, None)
        
        # Obtener uso del mes actual
        periodo = datetime.now().strftime('%Y-%m')
        uso = UsoGestoria.query.filter_by(
            gestoria_id=gestoria_id,
            periodo=periodo
        ).first()
        
        if not uso:
            # Crear registro de uso
            uso = UsoGestoria(
                gestoria_id=gestoria_id,
                periodo=periodo,
                tokens_ia_usados=0
            )
            db.session.add(uso)
            db.session.commit()
        
        tokens_usados = uso.tokens_ia_usados
        limite = plan.plan.tokens_ia_mes
        
        if tokens_usados + tokens_a_usar > limite:
            return (False, f"Límite de tokens IA alcanzado ({limite}/mes). Actualice su plan o espere al próximo mes.")
        
        return (True, None)
        
    except Exception as e:
        current_app.logger.error(f"Error verificando tokens IA: {e}")
        return (True, None)


def registrar_tokens_ia_usados(gestoria_id, tokens_usados):
    """
    Registra el uso de tokens de IA
    """
    try:
        periodo = datetime.now().strftime('%Y-%m')
        uso = UsoGestoria.query.filter_by(
            gestoria_id=gestoria_id,
            periodo=periodo
        ).first()
        
        if not uso:
            uso = UsoGestoria(
                gestoria_id=gestoria_id,
                periodo=periodo,
                tokens_ia_usados=tokens_usados
            )
            db.session.add(uso)
        else:
            uso.tokens_ia_usados += tokens_usados
            uso.fecha_actualizacion = datetime.utcnow()
        
        db.session.commit()
        current_app.logger.info(f"Registrados {tokens_usados} tokens IA para gestoría {gestoria_id}")
        
    except Exception as e:
        current_app.logger.error(f"Error registrando tokens IA: {e}")
        db.session.rollback()
