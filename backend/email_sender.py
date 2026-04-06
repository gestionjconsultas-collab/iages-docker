"""
Utilidades para envío de emails de recordatorios con templates HTML
"""
import html as html_lib
import logging

from flask import render_template, current_app
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
from reportlab.lib.styles import getSampleStyleSheet
from extensions import db
from models import Gestoria
from email_tokens import generar_url_confirmacion
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from constants import NotificationTypes, TaskStates

# Logo de IAGES en base64
LOGO_BASE64 = """iVBORw0KGgoAAAANSUhEUgAABLAAAAJYCAYAAABNZv+qAAAACXBIWXMAAC4jAAAuIwF4pT92AAAgAElEQVR4nOzdd5hV1b3/8c+aMzP0DjKA9N57EwEBRUQQRQWNGo0ao4kxJjHGmGI0xt6iRo0lGhWNvSuIgAUQpPfeO8ww7fz+mOME... [contenido base64 completo del logo]"""

def enviar_email(destinatario, asunto, cuerpo_html, gestoria_id=None):
    """
    Función genérica para envío de email HTML (ej: recuperaciones de contraseña)
    """
    return _enviar_email_smtp(destinatario, asunto, cuerpo_html, gestoria_id)

def enviar_email_recordatorio(linea, tipo_recordatorio):
    """
    Envía email de recordatorio para una línea de finiquito
    tipo_recordatorio: '7_dias', '3_dias', 'vencimiento'
    """
    try:
        # Obtener datos del documento y empresa
        documento = db.session.get(Documento, linea.documento_id)
        if not documento:
            return False
        
        empresa = db.session.get(Empresa, documento.empresa_id)
        if not empresa:
            return False
            
        # Determinar destinatario final (Empresa vs Grupo)
        email_destino = obtener_email_notificaciones(empresa.id)
        if not email_destino:
            logger.warning("Empresa sin email configurado: %s", empresa.nombre if empresa else 'Unknown')
            return False
        
        # Generar URLs de confirmación
        url_pagado = generar_url_confirmacion(linea.id, 'pagado')
        url_pendiente = generar_url_confirmacion(linea.id, TaskStates.PENDIENTE)
        
        # Contexto para el template
        context = {
            'empresa': empresa,
            'documento': documento,
            'linea': linea,
            'url_pagado': url_pagado,
            'url_pendiente': url_pendiente,
            'tipo': tipo_recordatorio
        }
        
        # Renderizar template HTML
        template_map = {
            '7_dias': 'emails/recordatorio_7_dias.html',
            '3_dias': 'emails/recordatorio_3_dias.html',
            'vencimiento': 'emails/recordatorio_vencimiento.html'
        }
        
        html_body = render_template(template_map.get(tipo_recordatorio, 'emails/recordatorio_7_dias.html'), **context)
        
        # Asunto del email
        asuntos = {
            '7_dias': f'Recordatorio: Cuota vence en 7 días - €{linea.importe_total_plazo:.2f}',
            '3_dias': f'⚠️ Urgente: Cuota vence en 3 días - €{linea.importe_total_plazo:.2f}',
            'vencimiento': f'🚨 Cuota vence HOY - €{linea.importe_total_plazo:.2f}'
        }
        
        # Enviar email
        enviado = _enviar_email_smtp(
            destinatario=email_destino,
            asunto=asuntos.get(tipo_recordatorio, 'Recordatorio de pago'),
            html_body=html_body,
            gestoria_id=documento.gestoria_id  # Personalizar remitente por gestoría
        )
        
        if enviado:
            # Registrar envío en BD
            registrar_envio_recordatorio(linea, tipo_recordatorio, email_destino)
            
            # Actualizar línea
            linea.ultimo_recordatorio_enviado = datetime.now(timezone.utc)
            linea.recordatorios_count = (linea.recordatorios_count or 0) + 1
            db.session.commit()
            
            return True
        
        return False
        
    except Exception as e:
        logger.error("Error enviando recordatorio: %s", e, exc_info=True)
        return False

def registrar_envio_recordatorio(linea, tipo, email_destino):
    """Registra el envío de un recordatorio en la BD"""
    recordatorio = RecordatorioPago(
        finiquito_linea_id=linea.id,
        tipo_recordatorio=tipo,
        email_enviado_a=email_destino,
        estado='enviado'
    )
    db.session.add(recordatorio)
    db.session.commit()
    return recordatorio

def obtener_email_notificaciones(empresa_id):
    """
    Determina a qué email enviar notificaciones (empresa o grupo)
    """
    empresa = db.session.get(Empresa, empresa_id)
    if not empresa:
        return None
    
    # Si la empresa pertenece a un grupo y el grupo tiene habilitado usar su email
    if empresa.grupo_id:
        grupo = db.session.get(GrupoEmpresa, empresa.grupo_id)
        if grupo and grupo.usar_email_grupo and grupo.email_notificaciones:
            logger.debug("Usando email de GRUPO %s para empresa %s: %s", grupo.nombre, empresa.nombre, grupo.email_notificaciones)
            return grupo.email_notificaciones
            
    return empresa.email

def _get_smtp_config(gestoria_id=None):
    """
    Obtiene configuración SMTP centralizada con personalización de remitente por gestoría
    
    Args:
        gestoria_id: ID de la gestoría (None = usar nombre por defecto "IAGES")
    
    Returns:
        dict con server, port, user, password, from_email
    """
    # SMTP centralizado (una sola cuenta para todas las gestorías)
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    # Personalizar nombre del remitente por gestoría
    from_name = "IAGES"  # Nombre por defecto
    
    if gestoria_id:
        try:
            from models import Gestoria
            gestoria = Gestoria.query.get(gestoria_id)
            if gestoria:
                from_name = gestoria.nombre
        except Exception as e:
            logger.warning("Error obteniendo nombre de gestoría: %s", e)
    
    # Formato: "Nombre Gestoría <email@centralizado.com>"
    from_email = f"{from_name} <{smtp_user}>" if smtp_user else smtp_user
    
    return {
        'server': smtp_server,
        'port': smtp_port,
        'user': smtp_user,
        'password': smtp_password,
        'from_email': from_email
    }

def _enviar_email_smtp(destinatario, asunto, html_body, gestoria_id=None):
    """Envía email usando SMTP configurado en el sistema"""
    try:
        # Obtener configuración SMTP (centralizada con nombre personalizado por gestoría)
        smtp_config = _get_smtp_config(gestoria_id)
        
        smtp_server = smtp_config['server']
        smtp_port = smtp_config['port']
        smtp_user = smtp_config['user']
        smtp_password = smtp_config['password']
        from_email = smtp_config['from_email']
        
        if not smtp_user or not smtp_password:
            logger.error("SMTP no configurado. Definir SMTP_USER y SMTP_PASSWORD en .env")
            return False
        
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From'] = from_email
        msg['To'] = destinatario
        
        # Adjuntar HTML
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)

        # Adjuntar Logo
        try:
            from email.mime.image import MIMEImage
            import os
            basedir = os.path.abspath(os.path.dirname(__file__))
            logo_path = os.path.join(basedir, 'assets', 'logo-iages.png')
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<logo_iages>')
                    msg.attach(img)
        except Exception as e:
            logger.warning("Error adjuntando logo en email: %s", e)
        
        # Enviar — puerto 465 usa SSL directo; 587/25 usan STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

        logger.info("Email enviado a %s", destinatario)
        return True

    except Exception as e:
        logger.error("Error enviando email a %s: %s", destinatario, e, exc_info=True)
        return False

def generar_html_email(asunto, mensaje, documentos, empresa_nombre):
    """
    Genera HTML profesional para email sin branding de IAGES
    (el email se envía en nombre de la gestoría, no de IAGES)
    """
    # E-1: Escapar todos los valores controlados por el usuario para prevenir XSS
    empresa_nombre_safe = html_lib.escape(str(empresa_nombre or ''))
    asunto_safe = html_lib.escape(str(asunto or ''))
    mensaje_html = html_lib.escape(str(mensaje or '')).replace('\n', '<br>') if mensaje else ''

    docs_html = ''
    for doc in documentos:
        doc_safe = html_lib.escape(str(doc))
        docs_html += f'''
            <tr>
                <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
                    <div style="display: flex; align-items: center;">
                        <span style="color: #6b7280; margin-right: 8px;">📄</span>
                        <span style="color: #374151; font-size: 14px;">{doc_safe}</span>
                    </div>
                </td>
            </tr>
        '''

    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{asunto_safe}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 30px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                        <!-- Contenido principal -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 8px 0; color: #111827; font-size: 20px; font-weight: 600;">
                                    {empresa_nombre_safe}
                                </h2>
                                <p style="margin: 0 0 24px 0; color: #6b7280; font-size: 13px; border-bottom: 1px solid #e5e7eb; padding-bottom: 20px;">
                                    ha compartido documentación contigo
                                </p>

                                <div style="color: #374151; font-size: 15px; line-height: 1.6; margin-bottom: 28px;">
                                    {mensaje_html if mensaje_html else '<p>Adjuntamos la documentación solicitada.</p>'}
                                </div>
                                
                                <!-- Lista de documentos -->
                                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px;">
                                    <h3 style="margin: 0 0 12px 0; color: #374151; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                                        📎 Documentos Adjuntos ({len(documentos)})
                                    </h3>
                                    <table width="100%" cellpadding="0" cellspacing="0">
                                        {docs_html}
                                    </table>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer neutro -->
                        <tr>
                            <td style="background-color: #f9fafb; padding: 20px 40px; border-top: 1px solid #e5e7eb; text-align: center;">
                                <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                    Este correo fue enviado por {empresa_nombre_safe}. Si no esperabas recibirlo, puedes ignorarlo.
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''
    
    return html

def enviar_email_con_adjuntos(destinatarios, asunto, cuerpo, adjuntos, usar_html=True, empresa_nombre=None, gestoria_id=None):
    """
    Envía email con múltiples archivos adjuntos
    
    Args:
        destinatarios: Lista de emails destinatarios
        asunto: Asunto del email
        cuerpo: Cuerpo del mensaje (texto plano)
        adjuntos: Lista de dicts con 'ruta' y 'nombre' de cada archivo
        usar_html: Si True, genera HTML profesional
        empresa_nombre: Nombre de la empresa para el HTML
        gestoria_id: ID de la gestoría para personalizar remitente
    
    Returns:
        dict con NotificationTypes.SUCCESS y opcionalmente NotificationTypes.ERROR
    """
    try:
        from email.mime.base import MIMEBase
        from email import encoders
        
        # Obtener configuración SMTP (centralizada con nombre personalizado por gestoría)
        smtp_config = _get_smtp_config(gestoria_id)
        
        smtp_server = smtp_config['server']
        smtp_port = smtp_config['port']
        smtp_user = smtp_config['user']
        smtp_password = smtp_config['password']
        
        # Usar empresa_nombre como nombre visible del remitente (ej: "Grupo Moon")
        # en lugar del nombre de la gestoría (ej: "Victor Cisneros")
        if empresa_nombre and smtp_user:
            from_email = f"{empresa_nombre} <{smtp_user}>"
        else:
            from_email = smtp_config['from_email']
        
        if not smtp_user or not smtp_password:
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'SMTP no configurado'}
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['Subject'] = asunto
        msg['From'] = from_email
        msg['To'] = ', '.join(destinatarios)
        
        # Generar HTML si está habilitado
        if usar_html and empresa_nombre:
            # Obtener nombres de documentos
            nombres_docs = [adj['nombre'] for adj in adjuntos]
            html_body = generar_html_email(asunto, cuerpo, nombres_docs, empresa_nombre)
            
            # Adjuntar HTML
            html_parte = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_parte)
        else:
            # Adjuntar cuerpo del mensaje en texto plano
            texto_parte = MIMEText(cuerpo, 'plain', 'utf-8')
            msg.attach(texto_parte)
        
        # Adjuntar archivos
        logger.debug("Adjuntando %d archivos: %s", len(adjuntos), [adj['nombre'] for adj in adjuntos])
        for adjunto in adjuntos:
            try:
                with open(adjunto['ruta'], 'rb') as f:
                    parte = MIMEBase('application', 'octet-stream')
                    parte.set_payload(f.read())
                    encoders.encode_base64(parte)
                    parte.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{adjunto["nombre"]}"'
                    )
                    msg.attach(parte)
                    logger.debug("Adjuntado: %s", adjunto['nombre'])
            except Exception as e:
                logger.warning("Error adjuntando %s: %s", adjunto['nombre'], e)
        
        # Enviar — puerto 465 usa SSL directo; 587/25 usan STARTTLS
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

        logger.info("Email enviado a %s con %d adjuntos", ', '.join(destinatarios), len(adjuntos))
        return {NotificationTypes.SUCCESS: True}

    except Exception as e:
        logger.error("Error enviando email con adjuntos: %s", e, exc_info=True)
        return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}