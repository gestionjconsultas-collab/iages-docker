# backend/services/billing_service.py
"""
Servicio de facturación con cumplimiento legal español
"""
import logging
from models_billing import Plan, Suscripcion, Factura, UsoMensual, Cupon, HistorialCambiosPlan, EmpresaEmisora
from models import Gestoria, User
from extensions import db
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

class BillingService:
    
    @staticmethod
    def crear_suscripcion_trial(gestoria_id, plan_codigo='basico', dias_trial=30):
        """
        Crea una suscripción con período de prueba
        
        Args:
            gestoria_id: ID de la gestoría
            plan_codigo: Código del plan (basico, profesional, enterprise)
            dias_trial: Días de prueba gratuita
        
        Returns:
            Suscripcion creada
        """
        plan = Plan.query.filter_by(codigo=plan_codigo, activo=True).first()
        if not plan:
            raise ValueError(f"Plan '{plan_codigo}' no encontrado")
        
        # Verificar que no exista suscripción
        suscripcion_existente = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        if suscripcion_existente:
            raise ValueError("La gestoría ya tiene una suscripción")
        
        # Crear suscripción con trial
        suscripcion = Suscripcion(
            gestoria_id=gestoria_id,
            plan_id=plan.id,
            estado='trial',
            fecha_inicio=datetime.utcnow(),
            trial_hasta=datetime.utcnow() + timedelta(days=dias_trial),
            fecha_proximo_pago=datetime.utcnow() + timedelta(days=dias_trial),
            ciclo='mensual',
            precio_actual=plan.precio_mensual
        )
        
        db.session.add(suscripcion)
        db.session.commit()
        
        return suscripcion
    
    @staticmethod
    def cambiar_plan(gestoria_id, nuevo_plan_codigo, ciclo='mensual', cupon_codigo=None, usuario_id=None):
        """
        Cambia el plan de una gestoría con prorrateado

        Args:
            gestoria_id: ID de la gestoría
            nuevo_plan_codigo: Código del nuevo plan
            ciclo: 'mensual' o 'anual'
            cupon_codigo: Código de cupón opcional
            usuario_id: ID del usuario que realiza el cambio

        Returns:
            dict con suscripcion actualizada y detalles del cambio
        """
        # FIX C-7: Validar que el usuario solo puede cambiar el plan de su propia gestoría.
        # Esta verificación se hace aquí en el servicio como segunda capa de defensa
        # (el endpoint también debe validarlo), para cubrir llamadas internas directas.
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            if not current_user.is_super_admin and current_user.gestoria_id != gestoria_id:
                raise PermissionError(
                    f"No autorizado: el usuario no puede cambiar el plan de la gestoría {gestoria_id}"
                )

        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        if not suscripcion:
            raise ValueError("La gestoría no tiene suscripción")
        
        from sqlalchemy import func
        nuevo_plan = Plan.query.filter(func.lower(Plan.nombre) == nuevo_plan_codigo.lower(), Plan.activo == True).first()
        if not nuevo_plan:
            # Reintentar por código si existe como columna (fallback) o simplemente fallar si no existe
            raise ValueError(f"Plan '{nuevo_plan_codigo}' no encontrado en bases de datos")
        
        plan_anterior = suscripcion.plan
        precio_anterior = suscripcion.precio_actual
        
        # Calcular nuevo precio
        if ciclo == 'anual':
            nuevo_precio = nuevo_plan.precio_anual or (nuevo_plan.precio_mensual * 10)
        else:
            nuevo_precio = nuevo_plan.precio_mensual
        
        # Aplicar cupón si existe
        descuento = Decimal(0)
        if cupon_codigo:
            cupon = Cupon.query.filter_by(codigo=cupon_codigo).first()
            if cupon and cupon.esta_vigente:
                # FIX A-7: Validar usos_maximos antes de aplicar el cupón
                if cupon.usos_maximos is not None and cupon.usos_actuales >= cupon.usos_maximos:
                    raise ValueError(f"El cupón '{cupon_codigo}' ha alcanzado su límite de usos")
                descuento = Decimal(cupon.calcular_descuento(nuevo_precio))
                nuevo_precio -= descuento
                # Incrementar uso del cupón
                cupon.usos_actuales += 1
        
        # Calcular prorrateado (simplificado)
        dias_restantes = 0
        credito_generado = Decimal(0)
        cargo_adicional = Decimal(0)
        
        if suscripcion.fecha_proximo_pago:
            dias_restantes = (suscripcion.fecha_proximo_pago - datetime.utcnow()).days
            if dias_restantes > 0:
                # Crédito proporcional del plan anterior
                credito_generado = (precio_anterior / 30) * dias_restantes
                # Cargo proporcional del nuevo plan
                cargo_adicional = (nuevo_precio / 30) * dias_restantes
        
        # Determinar motivo
        if nuevo_plan.precio_mensual > plan_anterior.precio_mensual:
            motivo = 'upgrade'
        elif nuevo_plan.precio_mensual < plan_anterior.precio_mensual:
            motivo = 'downgrade'
        else:
            motivo = 'cambio_ciclo'
        
        # Registrar cambio en historial
        historial = HistorialCambiosPlan(
            gestoria_id=gestoria_id,
            suscripcion_id=suscripcion.id,
            plan_anterior_id=plan_anterior.id,
            plan_nuevo_id=nuevo_plan.id,
            motivo=motivo,
            precio_anterior=precio_anterior,
            precio_nuevo=nuevo_precio,
            credito_generado=credito_generado,
            cargo_adicional=cargo_adicional,
            usuario_id=usuario_id
        )
        
        # Actualizar suscripción
        suscripcion.plan_id = nuevo_plan.id
        suscripcion.ciclo = ciclo
        suscripcion.precio_actual = nuevo_precio
        suscripcion.cupon_codigo = cupon_codigo
        suscripcion.cupon_descuento = descuento
        suscripcion.estado = 'activa'
        suscripcion.trial_hasta = None
        
        # 🔄 SINCRONIZACIÓN: Actualizar modelo Gestoria
        gestoria = Gestoria.query.get(gestoria_id)
        if gestoria:
            gestoria.plan = nuevo_plan.codigo
            # Actualizar límites físicos (solo campos que existen en PlanGestoria)
            gestoria.max_usuarios = nuevo_plan.usuarios_max
            gestoria.max_empresas = nuevo_plan.empresas_max
            gestoria.max_storage_gb = nuevo_plan.almacenamiento_gb
            gestoria.max_tokens_mes = nuevo_plan.tokens_ia_mes
        
        # 🔄 SINCRONIZACIÓN: Actualizar modelo GestoriaPlan (usado en SuperAdmin)
        from models import GestoriaPlan
        gp = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
        if gp:
            gp.plan_id = nuevo_plan.id
            gp.fecha_inicio = datetime.utcnow()
        else:
            gp = GestoriaPlan(
                gestoria_id=gestoria_id,
                plan_id=nuevo_plan.id,
                fecha_inicio=datetime.utcnow()
            )
            db.session.add(gp)
        
        db.session.add(historial)
        db.session.commit()
        
        # 📣 NOTIFICACIÓN: Emitir evento WebSocket para actualizar la UI en tiempo real
        try:
            from flask import current_app
            socketio = current_app.extensions.get('socketio')
            if socketio:
                socketio.emit('plan_changed', {
                    'gestoria_id': gestoria_id,
                    'new_plan': nuevo_plan.nombre,
                    'plan_id': nuevo_plan.id,
                    'new_price': float(nuevo_precio),
                    'mensaje': f'Tu plan ha sido actualizado a {nuevo_plan.nombre}'
                }, room=f'gestoria_{gestoria_id}')
                logger.debug("Evento plan_changed emitido para gestoría %s", gestoria_id)
        except Exception as ws_error:
            # No fallar el cambio de plan si falla la notificación
            logger.warning("Error emitiendo WebSocket plan_changed: %s", ws_error)
        
        return {
            'suscripcion': suscripcion.to_dict(),
            'cambio': historial.to_dict(),
            'credito_generado': float(credito_generado),
            'cargo_adicional': float(cargo_adicional),
            'cargo_neto': float(cargo_adicional - credito_generado)
        }
    
    @staticmethod
    def generar_factura_mensual(suscripcion_id):
        """
        Genera factura mensual para una suscripción
        
        Args:
            suscripcion_id: ID de la suscripción
        
        Returns:
            Factura generada
        """
        suscripcion = Suscripcion.query.get(suscripcion_id)
        if not suscripcion:
            raise ValueError("Suscripción no encontrada")
        
        if suscripcion.estado not in ['activa', 'trial']:
            raise ValueError(f"Suscripción en estado '{suscripcion.estado}', no se puede facturar")
        
        # No facturar si está en trial
        if suscripcion.esta_en_trial:
            return None
        
        # Calcular período
        hoy = datetime.utcnow()
        if suscripcion.ciclo == 'anual':
            periodo_inicio = hoy
            periodo_fin = hoy + relativedelta(years=1)
        else:
            periodo_inicio = hoy
            periodo_fin = hoy + relativedelta(months=1)
        
        # Calcular importes
        subtotal = suscripcion.precio_actual
        iva_porcentaje = Decimal('21.00')
        iva_importe = subtotal * (iva_porcentaje / 100)
        total = subtotal + iva_importe
        
        # Concepto
        plan_nombre = suscripcion.plan.nombre
        ciclo_texto = 'mensual' if suscripcion.ciclo == 'mensual' else 'anual'
        concepto = f"Suscripción {plan_nombre} ({ciclo_texto}) - {periodo_inicio.strftime('%B %Y')}"
        
        # Generar número de factura secuencial con protección ante concurrencia
        # Usamos WITH FOR UPDATE para serializar la asignación en PostgreSQL;
        # si la BD no lo soporta o hay colisión, el UNIQUE de numero_factura
        # rechazará el duplicado y se reintenta hasta MAX_RETRIES veces.
        anio_actual = hoy.year
        serie = 'FAC'
        MAX_RETRIES = 5
        factura = None
        for intento in range(MAX_RETRIES):
            ultima_factura = (
                Factura.query
                .filter(db.func.extract('year', Factura.fecha_emision) == anio_actual)
                .order_by(Factura.numero_secuencial.desc())
                .with_for_update()
                .first()
            )
            numero_secuencial = (ultima_factura.numero_secuencial + 1) if (ultima_factura and ultima_factura.numero_secuencial) else 1
            numero_factura = f"{serie}-{anio_actual}-{numero_secuencial:04d}"

            factura = Factura(
                gestoria_id=suscripcion.gestoria_id,
                suscripcion_id=suscripcion.id,
                numero_factura=numero_factura,
                serie=serie,
                numero_secuencial=numero_secuencial,
                fecha_emision=hoy,
                fecha_vencimiento=hoy + timedelta(days=15),
                subtotal=subtotal,
                iva_porcentaje=iva_porcentaje,
                iva_importe=iva_importe,
                total=total,
                concepto=concepto,
                periodo_inicio=periodo_inicio.date(),
                periodo_fin=periodo_fin.date(),
                lineas=[{
                    'descripcion': f'Suscripción {plan_nombre}',
                    'cantidad': 1,
                    'precio_unitario': float(subtotal),
                    'subtotal': float(subtotal)
                }],
                estado='pendiente'
            )
            # Actualizar fecha próximo pago
            suscripcion.fecha_proximo_pago = periodo_fin
            db.session.add(factura)
            try:
                db.session.commit()
                break  # Éxito — salir del loop de reintentos
            except Exception:
                db.session.rollback()
                if intento == MAX_RETRIES - 1:
                    raise
                logger.warning("Colisión en numero_secuencial factura, reintentando (%d/%d)...", intento + 1, MAX_RETRIES)

        return factura
    
    @staticmethod
    def marcar_factura_pagada(factura_id, metodo_pago='stripe', stripe_payment_intent_id=None):
        """
        Marca una factura como pagada
        
        Args:
            factura_id: ID de la factura
            metodo_pago: Método de pago utilizado
            stripe_payment_intent_id: ID del payment intent de Stripe
        
        Returns:
            Factura actualizada
        """
        factura = Factura.query.get(factura_id)
        if not factura:
            raise ValueError("Factura no encontrada")
        
        if factura.estado == 'pagada':
            raise ValueError("La factura ya está pagada")
        
        factura.estado = 'pagada'
        factura.fecha_pago = datetime.utcnow()
        factura.metodo_pago = metodo_pago
        factura.stripe_payment_intent_id = stripe_payment_intent_id

        # ── Reactivar gestoría si fue inactivada por impago ──────────────────
        # Solo reactivar si ya no quedan facturas vencidas pendientes de pago
        facturas_vencidas_restantes = Factura.query.filter(
            Factura.gestoria_id == factura.gestoria_id,
            Factura.estado == 'vencida'
        ).count()

        if facturas_vencidas_restantes == 0:
            gestoria = Gestoria.query.get(factura.gestoria_id)
            if gestoria and not gestoria.activa:
                gestoria.activa = True

            # Reactivar suscripción si estaba suspendida
            suscripcion = Suscripcion.query.filter_by(
                gestoria_id=factura.gestoria_id
            ).first()
            if suscripcion and suscripcion.estado == 'suspendida':
                suscripcion.estado = 'activa'

        db.session.commit()

        return factura
    
    @staticmethod
    def verificar_limites(gestoria_id, recurso):
        """
        Verifica si una gestoría ha alcanzado el límite de un recurso
        
        Args:
            gestoria_id: ID de la gestoría
            recurso: Nombre del recurso ('usuarios', 'empresas', 'storage', 'tokens', 'requests')
        
        Returns:
            dict con {
                'permitido': bool,
                'uso_actual': int,
                'limite': int,
                'porcentaje': float
            }
        """
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        if not suscripcion or suscripcion.estado not in ['activa', 'trial']:
            return {'permitido': False, 'mensaje': 'Suscripción inactiva'}
        
        plan = suscripcion.plan
        gestoria = Gestoria.query.get(gestoria_id)
        
        # Obtener uso mensual actual
        hoy = datetime.utcnow()
        uso_mensual = UsoMensual.query.filter_by(
            gestoria_id=gestoria_id,
            mes=hoy.month,
            anio=hoy.year
        ).first()
        
        storage_usado = uso_mensual.storage_usado_gb if uso_mensual else 0

        # Mapeo de recursos — usa los nombres reales de PlanGestoria
        limites = {
            'usuarios': (len(gestoria.usuarios), plan.usuarios_max),
            'empresas': (len(gestoria.empresas), plan.empresas_max),
            'storage':  (storage_usado, plan.almacenamiento_gb),
            'tokens':   (0, plan.tokens_ia_mes),  # TODO: obtener de uso_mensual
        }

        if recurso not in limites:
            raise ValueError(f"Recurso '{recurso}' no válido. Opciones: {list(limites.keys())}")
        
        uso_actual, limite = limites[recurso]
        
        # NULL = ilimitado
        if limite is None:
            return {
                'permitido': True,
                'uso_actual': uso_actual,
                'limite': None,
                'porcentaje': 0
            }
        
        permitido = uso_actual < limite
        porcentaje = (uso_actual / limite * 100) if limite > 0 else 0
        
        return {
            'permitido': permitido,
            'uso_actual': uso_actual,
            'limite': limite,
            'porcentaje': round(porcentaje, 2)
        }
    
    @staticmethod
    def calcular_uso_mensual(gestoria_id, mes=None, anio=None):
        """
        Calcula y guarda el uso mensual de una gestoría
        
        Args:
            gestoria_id: ID de la gestoría
            mes: Mes (1-12), por defecto mes actual
            anio: Año, por defecto año actual
        
        Returns:
            UsoMensual actualizado
        """
        hoy = datetime.utcnow()
        mes = mes or hoy.month
        anio = anio or hoy.year
        
        gestoria = Gestoria.query.get(gestoria_id)
        if not gestoria:
            raise ValueError("Gestoría no encontrada")
        
        # Obtener o crear registro de uso
        uso = UsoMensual.query.filter_by(
            gestoria_id=gestoria_id,
            mes=mes,
            anio=anio
        ).first()
        
        if not uso:
            uso = UsoMensual(
                gestoria_id=gestoria_id,
                mes=mes,
                anio=anio
            )
        
        # Calcular métricas
        # gestoria.usuarios es una InstrumentedList, no una query
        uso.usuarios_activos = len([u for u in gestoria.usuarios if u.activo])
        uso.empresas_totales = len(gestoria.empresas)
        
        # Calcular almacenamiento usado
        import os
        from models import Documento
        
        total_bytes = 0
        documentos = Documento.query.filter_by(gestoria_id=gestoria_id).all()
        
        for doc in documentos:
            if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                try:
                    total_bytes += os.path.getsize(doc.ruta_archivo)
                except OSError:
                    # Archivo no accesible, continuar
                    pass
        
        # Convertir a GB
        uso.storage_usado_gb = round(total_bytes / (1024 ** 3), 2)
        
        # TODO: Calcular tokens, requests, documentos, emails
        
        db.session.add(uso)
        db.session.commit()
        
        return uso
    
    @staticmethod
    def cancelar_suscripcion(gestoria_id, motivo='cancelacion', usuario_id=None):
        """
        Cancela una suscripción
        
        Args:
            gestoria_id: ID de la gestoría
            motivo: Motivo de la cancelación
            usuario_id: ID del usuario que cancela
        
        Returns:
            Suscripcion cancelada
        """
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        if not suscripcion:
            raise ValueError("La gestoría no tiene suscripción")
        
        # Registrar en historial
        historial = HistorialCambiosPlan(
            gestoria_id=gestoria_id,
            suscripcion_id=suscripcion.id,
            plan_anterior_id=suscripcion.plan_id,
            plan_nuevo_id=None,
            motivo=motivo,
            precio_anterior=suscripcion.precio_actual,
            precio_nuevo=Decimal(0),
            usuario_id=usuario_id
        )
        
        # Cancelar suscripción (mantener hasta fin de período pagado)
        suscripcion.estado = 'cancelada'
        suscripcion.fecha_fin = suscripcion.fecha_proximo_pago or datetime.utcnow()
        
        db.session.add(historial)
        db.session.commit()
        
        return suscripcion
    
    @staticmethod
    def validar_cupon(codigo, plan_id=None, ciclo=None):
        """
        Valida un cupón de descuento
        
        Args:
            codigo: Código del cupón
            plan_id: ID del plan (opcional)
            ciclo: Ciclo de facturación (opcional)
        
        Returns:
            dict con información del cupón y descuento aplicable
        """
        cupon = Cupon.query.filter_by(codigo=codigo.upper()).first()
        
        if not cupon:
            return {'valido': False, 'mensaje': 'Cupón no encontrado'}
        
        if not cupon.esta_vigente:
            return {'valido': False, 'mensaje': 'Cupón expirado o inactivo'}
        
        # Verificar aplicabilidad al plan
        if cupon.plan_id and plan_id and cupon.plan_id != plan_id:
            return {'valido': False, 'mensaje': 'Cupón no válido para este plan'}
        
        # Verificar aplicabilidad al ciclo
        if cupon.ciclo and ciclo and cupon.ciclo != ciclo:
            return {'valido': False, 'mensaje': f'Cupón solo válido para ciclo {cupon.ciclo}'}
        
        return {
            'valido': True,
            'cupon': cupon.to_dict(),
            'mensaje': f'Cupón válido: {cupon.descripcion}'
        }
