# backend/celery_tasks_billing.py
"""
Tareas programadas de Celery para facturación
"""
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Añadir el directorio actual al path
basedir = os.path.abspath(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from celery_worker import celery, get_flask_app  # ✅ Importar get_flask_app
from extensions import db
from models_billing import Suscripcion, Factura, UsoMensual
from services.billing_service import BillingService
from datetime import datetime, timedelta
from email_sender import enviar_email_con_adjuntos


@celery.task(
    name='generar_facturas_mensuales',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3}
)
def generar_facturas_mensuales():
    """
    Genera facturas mensuales para todas las suscripciones activas
    Se ejecuta el día 1 de cada mes a las 00:00
    """
    app = get_flask_app()  # ✅ Usar get_flask_app() en lugar de 'from app import app'
    
    with app.app_context():
        logger.info(f"Generando facturas mensuales - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
        
        # Obtener suscripciones activas que necesitan facturación
        hoy = datetime.utcnow()
        suscripciones = Suscripcion.query.filter(
            Suscripcion.estado == 'activa',
            Suscripcion.fecha_proximo_pago <= hoy
        ).all()
        
        facturas_generadas = 0
        errores = 0
        
        for suscripcion in suscripciones:
            try:
                # Generar factura
                factura = BillingService.generar_factura_mensual(suscripcion.id)
                
                if factura:
                    facturas_generadas += 1
                    
                    # Enviar factura por email
                    enviar_factura_email.delay(factura.id)
                    
                    logger.info(f"Factura generada: {factura.numero_factura} - Gestoría ID {suscripcion.gestoria_id}")
                
            except Exception as e:
                errores += 1
                logger.error(f"Error generando factura para suscripción {suscripcion.id}: {e}")
        
        logger.info(f"Resumen: {facturas_generadas} facturas generadas, {errores} errores")
        
        return {
            'facturas_generadas': facturas_generadas,
            'errores': errores,
            'fecha': hoy.isoformat()
        }


@celery.task(
    name='enviar_factura_email',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3}
)
def enviar_factura_email(factura_id):
    """
    Envía una factura por email a la gestoría
    """
    from models import Gestoria
    from utils.pdf_invoice_generator import generar_pdf_factura
    
    app = get_flask_app()
    with app.app_context():
        factura = Factura.query.get(factura_id)
        if not factura:
            logger.error(f"Factura {factura_id} no encontrada")
            return
        
        gestoria = Gestoria.query.get(factura.gestoria_id)
        if not gestoria or not gestoria.email:
            logger.error(f"Gestoría {factura.gestoria_id} sin email")
            return
        
        try:
            # Generar PDF si no existe
            if not factura.pdf_generado or not factura.pdf_path:
                pdf_path = generar_pdf_factura(factura.id)
                factura.pdf_path = pdf_path
                factura.pdf_generado = True
                db.session.commit()

            # Fix 7: Obtener IBAN real desde EmpresaEmisora en lugar de placeholder
            from models_billing import EmpresaEmisora
            empresa_emisora = EmpresaEmisora.get_datos_iages()
            iban_texto = empresa_emisora.iban_decrypted if empresa_emisora else '(Contacte con soporte)'

            # Enviar email con factura adjunta
            asunto = f"Nueva factura {factura.numero_factura} - IAGES"
            cuerpo = f"""
Estimado/a {gestoria.nombre},

Adjuntamos la factura {factura.numero_factura} correspondiente a su suscripción.

Detalles de la factura:
- Número: {factura.numero_factura}
- Fecha de emisión: {factura.fecha_emision.strftime('%d/%m/%Y')}
- Fecha de vencimiento: {factura.fecha_vencimiento.strftime('%d/%m/%Y')}
- Importe total: {factura.total}€

Para realizar el pago, por favor haga una transferencia bancaria a:
- IBAN: {iban_texto}
- Concepto: {factura.numero_factura}

Si ya ha realizado el pago, por favor ignore este mensaje.

Saludos cordiales,
Equipo IAGES
            """

            resultado = enviar_email_con_adjuntos(
                destinatarios=[gestoria.email],
                asunto=asunto,
                cuerpo=cuerpo,
                adjuntos=[{
                    'ruta': factura.pdf_path,
                    'nombre': f"{factura.numero_factura}.pdf"
                }],
                usar_html=True,
                empresa_nombre=gestoria.nombre,
                gestoria_id=gestoria.id
            )

            if resultado.get('success'):
                logger.info("Factura %s enviada a %s", factura.numero_factura, gestoria.email)
            else:
                logger.error("Error enviando factura %s: %s", factura.numero_factura, resultado.get('error'))

        except Exception as e:
            logger.error("Error enviando factura %s: %s", factura.numero_factura, e, exc_info=True)


@celery.task(name='calcular_uso_mensual_todas')
def calcular_uso_mensual_todas():
    """
    Calcula el uso mensual para todas las gestorías
    Se ejecuta diariamente
    """
    from models import Gestoria
    
    app = get_flask_app()
    with app.app_context():
        logger.info(f"Calculando uso mensual - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

        
        gestorias = Gestoria.query.filter_by(activa=True).all()
        
        actualizadas = 0
        errores = 0
        
        for gestoria in gestorias:
            try:
                BillingService.calcular_uso_mensual(gestoria.id)
                actualizadas += 1
            except Exception as e:
                errores += 1
                logger.error(f"Error calculando uso para gestoría {gestoria.id}: {e}")
        
        logger.info(f"Resumen: {actualizadas} gestorías actualizadas, {errores} errores")
        
        return {
            'gestorias_actualizadas': actualizadas,
            'errores': errores
        }


@celery.task(
    name='verificar_facturas_vencidas',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3}
)
def verificar_facturas_vencidas():
    """
    Verifica facturas vencidas y suspende suscripciones si es necesario
    Se ejecuta diariamente
    """
    app = get_flask_app()
    
    with app.app_context():
        logger.info(f"Verificando facturas vencidas - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
        
        hoy = datetime.utcnow()
        
        # Buscar facturas pendientes vencidas
        facturas_vencidas = Factura.query.filter(
            Factura.estado == 'pendiente',
            Factura.fecha_vencimiento < hoy
        ).all()
        
        facturas_marcadas = 0
        suscripciones_suspendidas = 0
        
        from models import Gestoria

        for factura in facturas_vencidas:
            # Marcar factura como vencida
            factura.estado = 'vencida'
            facturas_marcadas += 1

            gestoria = Gestoria.query.get(factura.gestoria_id)
            if not gestoria:
                continue

            # ─── Suspender suscripción ───────────────────────────────────────
            suscripcion = Suscripcion.query.filter_by(
                gestoria_id=factura.gestoria_id
            ).first()
            if suscripcion and suscripcion.estado == 'activa':
                suscripcion.estado = 'suspendida'
                suscripciones_suspendidas += 1
                logger.warning(f"Suscripción suspendida - Gestoría ID {factura.gestoria_id} ({gestoria.nombre})")

            # ─── Inactivar gestoría si sigue activa ─────────────────────────
            if gestoria.activa:
                gestoria.activa = False
                logger.warning(
                    f"Gestoría INACTIVADA por impago - ID {gestoria.id} ({gestoria.nombre}) "
                    f"Factura: {factura.numero_factura} vencida el {factura.fecha_vencimiento.strftime('%d/%m/%Y')}"
                )

                # Notificar al gestor por email (si tiene email configurado)
                try:
                    from models import User
                    admin_gestoria = User.query.filter_by(
                        gestoria_id=gestoria.id
                    ).join(User.departamento).filter(
                        db.text("departamentos.nombre = 'Jefatura'")
                    ).first()

                    if admin_gestoria and admin_gestoria.email:
                        enviar_email_con_adjuntos(
                            destinatarios=[admin_gestoria.email],
                            asunto="⚠️ Cuenta suspendida por impago",
                            cuerpo_html=f"""
                            <h2>Cuenta suspendida por impago</h2>
                            <p>Estimado/a {admin_gestoria.nombre},</p>
                            <p>Su cuenta en <strong>IAGES</strong> ha sido <strong>suspendida temporalmente</strong>
                               porque la factura <strong>{factura.numero_factura}</strong>
                               (€{factura.total:.2f}) venció el {factura.fecha_vencimiento.strftime('%d/%m/%Y')}
                               sin haber sido abonada.</p>
                            <p>Para reactivar el acceso, realice la transferencia bancaria indicada
                               en su panel de facturación y contacte con nuestro equipo de soporte.</p>
                            <p>Gracias,<br>Equipo IAGES</p>
                            """
                        )
                        logger.info(f"Email de suspensión enviado a {admin_gestoria.email}")
                except Exception as mail_err:
                    logger.error(f"Error enviando email de suspensión: {mail_err}")

        db.session.commit()
        
        logger.info(f"Resumen: {facturas_marcadas} facturas vencidas, {suscripciones_suspendidas} suscripciones suspendidas")
        
        return {
            'facturas_vencidas': facturas_marcadas,
            'suscripciones_suspendidas': suscripciones_suspendidas
        }


@celery.task(name='recordatorio_facturas_proximas_vencer')
def recordatorio_facturas_proximas_vencer():
    """
    Envía recordatorios de facturas que vencen en 3 días
    Se ejecuta diariamente
    """
    from models import Gestoria
    
    app = get_flask_app()
    with app.app_context():
        logger.info(f"Enviando recordatorios de facturas - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
        
        # Facturas que vencen en 3 días
        fecha_limite = datetime.utcnow() + timedelta(days=3)
        
        facturas = Factura.query.filter(
            Factura.estado == 'pendiente',
            Factura.fecha_vencimiento <= fecha_limite,
            Factura.fecha_vencimiento > datetime.utcnow()
        ).all()
        
        recordatorios_enviados = 0
        
        for factura in facturas:
            try:
                gestoria = Gestoria.query.get(factura.gestoria_id)
                if not gestoria or not gestoria.email:
                    continue
                
                dias_restantes = (factura.fecha_vencimiento - datetime.utcnow()).days
                
                asunto = f"⚠️ Recordatorio: Factura {factura.numero_factura} vence en {dias_restantes} días"
                cuerpo = f"""
Estimado/a {gestoria.nombre},

Le recordamos que la factura {factura.numero_factura} vence en {dias_restantes} días.

Detalles:
- Importe: {factura.total}€
- Fecha de vencimiento: {factura.fecha_vencimiento.strftime('%d/%m/%Y')}

Por favor, realice el pago a la brevedad para evitar la suspensión del servicio.

Saludos,
Equipo IAGES
                """
                
                resultado = enviar_email_con_adjuntos(
                    destinatarios=[gestoria.email],
                    asunto=asunto,
                    cuerpo=cuerpo,
                    adjuntos=[],
                    usar_html=False,
                    gestoria_id=gestoria.id
                )
                
                if resultado.get('success'):
                    recordatorios_enviados += 1
                    
            except Exception as e:
                logger.error(f"Error enviando recordatorio para factura {factura.id}: {e}")
        
        logger.info(f"Recordatorios enviados: {recordatorios_enviados}")
        
        return {
            'recordatorios_enviados': recordatorios_enviados
        }
