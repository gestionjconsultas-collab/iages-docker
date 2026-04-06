"""
Sistema de Alertas Automáticas para Multi-Gestoría
Verifica límites y genera alertas automáticamente
"""
from models import db, GestoriaPlan, UsoGestoria, AlertaSistema, User, Empresa
from datetime import datetime
from sqlalchemy import func

def verificar_limites_y_generar_alertas():
    """
    Verifica los límites de todas las gestorías y genera alertas automáticas
    Esta función debe ejecutarse periódicamente (ej: cada hora con Celery)
    """
    print("🔍 Verificando límites de gestorías...")
    
    alertas_generadas = 0
    
    # Obtener todas las gestorías con plan
    planes_gestorias = GestoriaPlan.query.all()
    
    for gp in planes_gestorias:
        gestoria_id = gp.gestoria_id
        plan = gp.plan
        
        # 1. Verificar límite de usuarios
        usuarios_count = User.query.filter_by(gestoria_id=gestoria_id).count()
        porcentaje_usuarios = (usuarios_count / plan.usuarios_max) * 100 if plan.usuarios_max > 0 else 0
        
        if porcentaje_usuarios >= 90 and porcentaje_usuarios < 100:
            crear_alerta_si_no_existe(
                gestoria_id=gestoria_id,
                tipo='limite_usuarios',
                nivel='warning',
                titulo='Límite de usuarios próximo',
                mensaje=f'Has usado {usuarios_count} de {plan.usuarios_max} usuarios ({porcentaje_usuarios:.1f}%). Considera actualizar tu plan.'
            )
            alertas_generadas += 1
        elif porcentaje_usuarios >= 100:
            crear_alerta_si_no_existe(
                gestoria_id=gestoria_id,
                tipo='limite_usuarios',
                nivel='critical',
                titulo='Límite de usuarios alcanzado',
                mensaje=f'Has alcanzado el límite de {plan.usuarios_max} usuarios. No podrás crear más usuarios hasta actualizar tu plan.'
            )
            alertas_generadas += 1
        
        # 2. Verificar límite de empresas
        empresas_count = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
        porcentaje_empresas = (empresas_count / plan.empresas_max) * 100 if plan.empresas_max > 0 else 0
        
        if porcentaje_empresas >= 90 and porcentaje_empresas < 100:
            crear_alerta_si_no_existe(
                gestoria_id=gestoria_id,
                tipo='limite_empresas',
                nivel='warning',
                titulo='Límite de empresas próximo',
                mensaje=f'Has usado {empresas_count} de {plan.empresas_max} empresas ({porcentaje_empresas:.1f}%). Considera actualizar tu plan.'
            )
            alertas_generadas += 1
        elif porcentaje_empresas >= 100:
            crear_alerta_si_no_existe(
                gestoria_id=gestoria_id,
                tipo='limite_empresas',
                nivel='critical',
                titulo='Límite de empresas alcanzado',
                mensaje=f'Has alcanzado el límite de {plan.empresas_max} empresas. No podrás crear más empresas hasta actualizar tu plan.'
            )
            alertas_generadas += 1
        
        # 3. Verificar límite de tokens IA
        periodo_actual = datetime.now().strftime('%Y-%m')
        uso = UsoGestoria.query.filter_by(
            gestoria_id=gestoria_id,
            periodo=periodo_actual
        ).first()
        
        if uso:
            tokens_usados = uso.tokens_ia_usados
            limite_tokens = plan.tokens_ia_mes
            porcentaje_tokens = (tokens_usados / limite_tokens) * 100 if limite_tokens > 0 else 0
            
            if porcentaje_tokens >= 80 and porcentaje_tokens < 90:
                crear_alerta_si_no_existe(
                    gestoria_id=gestoria_id,
                    tipo='limite_tokens_ia',
                    nivel='info',
                    titulo='Uso de tokens IA elevado',
                    mensaje=f'Has usado {tokens_usados:,} de {limite_tokens:,} tokens IA este mes ({porcentaje_tokens:.1f}%).'
                )
                alertas_generadas += 1
            elif porcentaje_tokens >= 90 and porcentaje_tokens < 100:
                crear_alerta_si_no_existe(
                    gestoria_id=gestoria_id,
                    tipo='limite_tokens_ia',
                    nivel='warning',
                    titulo='Límite de tokens IA próximo',
                    mensaje=f'Has usado {tokens_usados:,} de {limite_tokens:,} tokens IA este mes ({porcentaje_tokens:.1f}%). El servicio se detendrá al alcanzar el límite.'
                )
                alertas_generadas += 1
            elif porcentaje_tokens >= 100:
                crear_alerta_si_no_existe(
                    gestoria_id=gestoria_id,
                    tipo='limite_tokens_ia',
                    nivel='critical',
                    titulo='Límite de tokens IA alcanzado',
                    mensaje=f'Has alcanzado el límite de {limite_tokens:,} tokens IA. El servicio de IA está deshabilitado hasta el próximo mes o hasta que actualices tu plan.'
                )
                alertas_generadas += 1
    
    print(f"✅ Verificación completada. {alertas_generadas} alertas generadas.")
    return alertas_generadas


def crear_alerta_si_no_existe(gestoria_id, tipo, nivel, titulo, mensaje):
    """
    Crea una alerta solo si no existe una similar reciente (últimas 24 horas)
    """
    from datetime import timedelta
    
    # Verificar si ya existe una alerta similar en las últimas 24 horas
    hace_24h = datetime.utcnow() - timedelta(hours=24)
    
    alerta_existente = AlertaSistema.query.filter(
        AlertaSistema.gestoria_id == gestoria_id,
        AlertaSistema.tipo == tipo,
        AlertaSistema.fecha_creacion >= hace_24h,
        AlertaSistema.leida == False
    ).first()
    
    if not alerta_existente:
        nueva_alerta = AlertaSistema(
            gestoria_id=gestoria_id,
            tipo=tipo,
            nivel=nivel,
            titulo=titulo,
            mensaje=mensaje,
            leida=False,
            fecha_creacion=datetime.utcnow()
        )
        db.session.add(nueva_alerta)
        db.session.commit()
        print(f"  📢 Alerta creada: {titulo} (Gestoría {gestoria_id})")
        return True
    
    return False


def limpiar_alertas_antiguas(dias=30):
    """
    Elimina alertas leídas más antiguas que X días
    """
    from datetime import timedelta
    
    fecha_limite = datetime.utcnow() - timedelta(days=dias)
    
    alertas_eliminadas = AlertaSistema.query.filter(
        AlertaSistema.leida == True,
        AlertaSistema.fecha_creacion < fecha_limite
    ).delete()
    
    db.session.commit()
    print(f"🗑️ {alertas_eliminadas} alertas antiguas eliminadas.")
    return alertas_eliminadas


# Endpoint para ejecutar manualmente (para testing)
def endpoint_verificar_alertas():
    """
    Endpoint para ejecutar la verificación manualmente
    """
    try:
        alertas = verificar_limites_y_generar_alertas()
        return {
            'success': True,
            'alertas_generadas': alertas,
            'mensaje': f'Verificación completada. {alertas} alertas generadas.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
