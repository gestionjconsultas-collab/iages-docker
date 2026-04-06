"""
Sistema de Notificaciones para Cambios de Planes
Notifica a las gestorías cuando su plan cambia
"""
from models import db, GestoriaPlan, Gestoria, User, Notificacion
from datetime import datetime

def notificar_cambio_plan(plan_id, campo_modificado, valor_anterior, valor_nuevo):
    """
    Notifica a todas las gestorías que tienen un plan cuando este cambia
    
    Args:
        plan_id: ID del plan modificado
        campo_modificado: Campo que cambió (ej: 'precio_mensual')
        valor_anterior: Valor antes del cambio
        valor_nuevo: Valor después del cambio
    """
    try:
        # Obtener gestorías con este plan
        gestorias_plan = GestoriaPlan.query.filter_by(plan_id=plan_id).all()
        
        if not gestorias_plan:
            print(f"ℹ️ No hay gestorías con el plan {plan_id}")
            return 0
        
        # Preparar mensaje según el campo
        mensaje = generar_mensaje_cambio(campo_modificado, valor_anterior, valor_nuevo)
        titulo = f"Cambio en tu plan"
        
        notificaciones_creadas = 0
        
        for gp in gestorias_plan:
            gestoria = gp.gestoria
            
            # Obtener administradores de la gestoría
            admins = User.query.filter_by(
                gestoria_id=gestoria.id,
                departamento_id=5  # Jefatura
            ).all()
            
            # Crear notificación para cada admin
            for admin in admins:
                notificacion = Notificacion(
                    user_id=admin.id,
                    titulo=titulo,
                    mensaje=mensaje,
                    tipo='info',
                    link=None,
                    leida=False,
                    fecha_creacion=datetime.utcnow()
                )
                db.session.add(notificacion)
                notificaciones_creadas += 1
        
        db.session.commit()
        print(f"✅ {notificaciones_creadas} notificaciones enviadas")
        return notificaciones_creadas
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error notificando cambio de plan: {e}")
        return 0


def generar_mensaje_cambio(campo, valor_anterior, valor_nuevo):
    """Genera un mensaje amigable según el campo modificado"""
    
    mensajes = {
        'precio_mensual': f"El precio de tu plan ha cambiado de €{valor_anterior}/mes a €{valor_nuevo}/mes. Este cambio se reflejará en tu próxima factura.",
        
        'usuarios_max': f"El límite de usuarios de tu plan ha cambiado de {valor_anterior} a {valor_nuevo} usuarios.",
        
        'empresas_max': f"El límite de empresas de tu plan ha cambiado de {valor_anterior} a {valor_nuevo} empresas.",
        
        'almacenamiento_gb': f"El almacenamiento de tu plan ha cambiado de {valor_anterior} GB a {valor_nuevo} GB.",
        
        'tokens_ia_mes': f"Los tokens de IA mensuales de tu plan han cambiado de {valor_anterior} a {valor_nuevo} tokens.",
        
        'soporte_nivel': f"El nivel de soporte de tu plan ha cambiado de '{valor_anterior}' a '{valor_nuevo}'.",
        
        'permite_branding': f"El branding personalizado ahora está {'habilitado' if valor_nuevo == 'true' else 'deshabilitado'} en tu plan."
    }
    
    return mensajes.get(campo, f"Se ha actualizado {campo} de tu plan de {valor_anterior} a {valor_nuevo}.")


def notificar_cambio_precio_masivo(cambios):
    """
    Notifica cambios de precio a múltiples planes
    
    Args:
        cambios: Lista de diccionarios con {plan_id, precio_anterior, precio_nuevo}
    """
    total_notificaciones = 0
    
    for cambio in cambios:
        n = notificar_cambio_plan(
            cambio['plan_id'],
            'precio_mensual',
            cambio['precio_anterior'],
            cambio['precio_nuevo']
        )
        total_notificaciones += n
    
    return total_notificaciones


def enviar_email_cambio_plan(gestoria_id, plan_nombre, cambios):
    """
    Envía email a la gestoría sobre cambios en su plan
    (Implementar cuando esté configurado el sistema de emails)
    """
    # TODO: Implementar envío de email
    pass
