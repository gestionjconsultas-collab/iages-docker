# backend/routes_emails_pendientes.py
"""
Endpoints para gestión de correos pendientes de envío.
Lista documentos con email preparado pero no enviado,
y permite envío individual o masivo.
MULTI-TENANT: filtrado por gestoria_id.
"""

import os
import ssl
import smtplib
from datetime import datetime, timezone
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import db
from models import Documento, Empresa, Gestoria
from tenant_utils import get_current_gestoria_id

emails_pendientes_bp = Blueprint('emails_pendientes', __name__)

basedir = os.path.abspath(os.path.dirname(__file__))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_email_msg(doc: Documento, emp: Empresa, dests: list, subject: str, body: str):
    """Construye el objeto MIMEMultipart listo para enviar."""
    msg = MIMEMultipart('related')
    msg["From"] = f"IAGES <{current_app.config['SMTP_USER']}>"
    msg["To"] = ", ".join(dests)
    msg["Subject"] = Header(subject, 'utf-8')

    msg_alt = MIMEMultipart('alternative')
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(body, "plain", "utf-8"))

    # Firma dinámica desde la gestoría
    gestoria = db.session.get(Gestoria, doc.gestoria_id)
    firma_nombre = gestoria.nombre if gestoria else 'Su Gestoría'
    firma_tel_html = f"<br>Tel {gestoria.telefono}" if gestoria and gestoria.telefono else ''

    html = (
        f"<html><head><style>"
        "body{font-family:'Segoe UI',sans-serif;background:#f3f4f6;padding:20px}"
        ".container{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;"
        "overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,0.1)}"
        ".header{background:linear-gradient(90deg,#f97316 0%,#ef4444 100%);padding:15px;text-align:center}"
        ".content{padding:30px 25px;color:#374151;font-size:15px;line-height:1.5}"
        ".attachment-box{background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;"
        "padding:12px;margin-top:20px;display:flex;align-items:center;font-size:13px}"
        ".footer{background:#f9fafb;padding:15px;text-align:center;font-size:11px;"
        "color:#9ca3af;border-top:1px solid #e5e7eb}"
        "</style></head><body><div class='container'>"
        "<div class='header'><img src='cid:logo_iages' style='height:60px;width:auto;display:block;margin:0 auto'></div>"
        f"<div class='content'>{body.replace(chr(10), '<br>')}"
        f"<div class='attachment-box'>📄 <strong>Adjunto:</strong> &nbsp; {doc.nombre_archivo}</div>"
        "</div>"
        f"<div class='footer'><p><strong>{firma_nombre}</strong>{firma_tel_html}</p>"
        "<p>© 2025 IAGES</p></div></div></body></html>"
    )
    msg_alt.attach(MIMEText(html, "html", "utf-8"))

    logo = os.path.join(basedir, 'assets', 'logo-iages.png')
    if os.path.exists(logo):
        with open(logo, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', '<logo_iages>')
            msg.attach(img)

    if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
        with open(doc.ruta_archivo, "rb") as f:
            p = MIMEBase("application", "octet-stream")
            p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header(
                "Content-Disposition", "attachment",
                filename=Header(doc.nombre_archivo, 'utf-8').encode()
            )
            msg.attach(p)

    return msg


def _send_email(doc: Documento, dests: list, subject: str, body: str) -> None:
    """Envía el email y actualiza el documento. Lanza excepción en caso de error."""
    emp = db.session.get(Empresa, doc.empresa_id)
    msg = _build_email_msg(doc, emp, dests, subject, body)

    ctx = ssl.create_default_context()
    port = int(current_app.config['SMTP_PORT'])
    if port == 465:
        with smtplib.SMTP_SSL(
            current_app.config['SMTP_SERVER'],
            port,
            context=ctx
        ) as s:
            s.login(current_app.config['SMTP_USER'], current_app.config['SMTP_PASS'])
            s.sendmail(current_app.config['SMTP_USER'], dests, msg.as_string())
    else:
        with smtplib.SMTP(
            current_app.config['SMTP_SERVER'],
            port
        ) as s:
            s.starttls(context=ctx)
            s.login(current_app.config['SMTP_USER'], current_app.config['SMTP_PASS'])
            s.sendmail(current_app.config['SMTP_USER'], dests, msg.as_string())

    doc.email_enviado = True
    doc.guardado = False
    doc.fecha_envio = datetime.now(timezone.utc)
    doc.estado_tarea = None


def _generar_texto_email(doc: Documento):
    """Genera subject y body usando todos los campos OCR y la firma de la gestoría."""
    datos = doc.datos_extraidos or {}

    # Firma dinámica desde la gestoría
    gestoria = db.session.get(Gestoria, doc.gestoria_id)
    firma_nombre = gestoria.nombre if gestoria else 'Su Gestoría'
    firma_tel = f"\nTel {gestoria.telefono}" if gestoria and gestoria.telefono else ''

    # Asunto: tipo_documento extraído o fallback al nombre del archivo
    tipo = datos.get('tipo_documento') or 'Notificación'
    subject = f"{tipo}: {doc.nombre_archivo}"

    # Campos OCR que se muestran si tienen valor
    CAMPOS = [
        ('organismo_emisor',    'Organismo'),
        ('referencia',          'Referencia'),
        ('expediente',          'Expediente'),
        ('nif_destinatario',    'NIF Destinatario'),
        ('nombre_destinatario', 'Destinatario'),
        ('asunto',              'Asunto'),
        ('concepto',            'Concepto'),
        ('descripcion',         'Descripción'),
        ('importe_total_deuda', 'Importe deuda'),
        ('importe_embargado',   'Importe embargado'),
        ('importe_pagar',       'Importe a pagar'),
        ('fecha_notificacion',  'Fecha notificación'),
        ('fecha_limite',        'Fecha límite'),
        ('fecha_plazo',         'Fecha plazo'),
        ('resumen',             'Resumen'),
    ]
    lineas = [
        f"{etiqueta}: {datos[campo]}"
        for campo, etiqueta in CAMPOS
        if datos.get(campo) and str(datos[campo]).strip()
    ]

    cuerpo_datos = '\n'.join(lineas) if lineas else f"Documento: {doc.nombre_archivo}"
    return subject, f"Se adjunta la siguiente notificación:\n\n{cuerpo_datos}\n\n{firma_nombre}{firma_tel}"


def _doc_to_dict(doc: Documento, emp: Empresa) -> dict:
    """Convierte un documento pendiente a dict para la API."""
    email_prep = (doc.datos_extraidos or {}).get('email_preparado', {})
    return {
        'id': doc.id,
        'nombre_archivo': doc.nombre_archivo,
        'empresa_id': doc.empresa_id,
        'empresa_nombre': emp.nombre if emp else '—',
        'empresa_nif': emp.nif if emp else None,
        'destinatarios': email_prep.get('destinatarios', []),
        'fecha_preparacion': email_prep.get('fecha_preparacion'),
        'estado_tarea': doc.estado_tarea,
        'asunto': email_prep.get('asunto') or f"Notificación Procesada: {doc.nombre_archivo}",
        'cuerpo': email_prep.get('cuerpo') or _generar_texto_email(doc)[1],
    }


# ---------------------------------------------------------------------------
# GET /api/emails-pendientes
# ---------------------------------------------------------------------------

@emails_pendientes_bp.route('/api/emails-pendientes', methods=['GET'])
@login_required
def listar_emails_pendientes():
    """
    Devuelve todos los documentos con email preparado y no enviado,
    filtrados por gestoria_id del usuario actual.

    Query params opcionales:
      empresa_id  (int)  — filtrar por empresa
      page        (int)  — paginación (default 1)
      per_page    (int)  — resultados por página (default 50)
    """
    gestoria_id = get_current_gestoria_id()
    empresa_id = request.args.get('empresa_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)

    # Filtramos a nivel SQL solo por email_enviado + gestoria_id (campos indexados).
    # El filtro por listo_para_enviar se hace en Python para evitar problemas con
    # el operador JSON anidado en distintas versiones de SQLAlchemy/PostgreSQL.
    q = (
        db.session.query(Documento, Empresa)
        .join(Empresa, Documento.empresa_id == Empresa.id)
        .filter(
            Documento.gestoria_id == gestoria_id,
            Documento.email_enviado == False,
            Documento.datos_extraidos.isnot(None),
        )
    )

    if empresa_id:
        q = q.filter(Documento.empresa_id == empresa_id)

    # Filtrado Python: solo docs con email_preparado.listo_para_enviar = True
    all_rows = q.order_by(Documento.id.desc()).all()
    rows = [
        (doc, emp) for doc, emp in all_rows
        if (doc.datos_extraidos or {}).get('email_preparado', {}).get('listo_para_enviar')
    ]

    total = len(rows)
    # Paginación manual sobre la lista filtrada
    start = (page - 1) * per_page
    rows_page = rows[start:start + per_page]

    items = [_doc_to_dict(doc, emp) for doc, emp in rows_page]

    return jsonify({
        'success': True,
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    })


# ---------------------------------------------------------------------------
# POST /api/emails-pendientes/<doc_id>/enviar
# Individual send
# ---------------------------------------------------------------------------

@emails_pendientes_bp.route('/api/emails-pendientes/<int:doc_id>/enviar', methods=['POST'])
@login_required
def enviar_email_pendiente(doc_id):
    """
    Envía el email para un documento específico.
    Body JSON opcional:
      destinatarios  (list[str]) — sobreescribe los guardados
      asunto         (str)       — sobreescribe el asunto generado
      cuerpo         (str)       — sobreescribe el cuerpo generado
    """
    gestoria_id = get_current_gestoria_id()

    doc = db.session.get(Documento, doc_id)
    if not doc:
        return jsonify({'error': 'Documento no encontrado'}), 404
    if doc.gestoria_id != gestoria_id:
        return jsonify({'error': 'Acceso denegado'}), 403
    if doc.email_enviado:
        return jsonify({'error': 'El email ya fue enviado'}), 400

    data = request.get_json(silent=True) or {}
    email_prep = (doc.datos_extraidos or {}).get('email_preparado', {})

    # Destinatarios: cuerpo JSON > guardados > email empresa
    dests = data.get('destinatarios') or email_prep.get('destinatarios', [])
    if not dests:
        emp = db.session.get(Empresa, doc.empresa_id)
        if emp and emp.email:
            dests = [emp.email]

    if not dests:
        return jsonify({'error': 'No hay destinatarios configurados'}), 400

    subject = data.get('asunto') or email_prep.get('asunto') or _generar_texto_email(doc)[0]
    body = data.get('cuerpo') or email_prep.get('cuerpo') or _generar_texto_email(doc)[1]

    try:
        _send_email(doc, dests, subject, body)
        db.session.commit()
        return jsonify({'success': True, 'doc_id': doc_id, 'destinatarios': dests})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/emails-pendientes/enviar-masivo
# Bulk send
# ---------------------------------------------------------------------------

@emails_pendientes_bp.route('/api/emails-pendientes/enviar-masivo', methods=['POST'])
@login_required
def enviar_emails_masivo():
    """
    Envía emails para múltiples documentos.
    Body JSON:
      doc_ids  (list[int])  — IDs a enviar. Si está vacío, envía TODOS los pendientes.

    Devuelve un resumen con éxitos y errores por documento.
    """
    gestoria_id = get_current_gestoria_id()
    data = request.get_json(silent=True) or {}
    doc_ids = data.get('doc_ids', [])

    # Query base: pendientes de esta gestoría (filtro JSON en Python, más seguro)
    q = db.session.query(Documento).filter(
        Documento.gestoria_id == gestoria_id,
        Documento.email_enviado == False,
        Documento.datos_extraidos.isnot(None),
    )

    if doc_ids:
        q = q.filter(Documento.id.in_(doc_ids))

    candidatos = q.all()
    docs = [
        d for d in candidatos
        if (d.datos_extraidos or {}).get('email_preparado', {}).get('listo_para_enviar')
    ]

    if not docs:
        return jsonify({'success': True, 'enviados': 0, 'errores': [], 'total': 0})

    enviados = 0
    errores = []

    for doc in docs:
        try:
            email_prep = (doc.datos_extraidos or {}).get('email_preparado', {})
            dests = email_prep.get('destinatarios', [])

            if not dests:
                emp = db.session.get(Empresa, doc.empresa_id)
                if emp and emp.email:
                    dests = [emp.email]

            if not dests:
                errores.append({
                    'doc_id': doc.id,
                    'nombre': doc.nombre_archivo,
                    'error': 'Sin destinatarios',
                })
                continue

            subject = email_prep.get('asunto') or _generar_texto_email(doc)[0]
            body = email_prep.get('cuerpo') or _generar_texto_email(doc)[1]

            _send_email(doc, dests, subject, body)
            enviados += 1

        except Exception as e:
            errores.append({
                'doc_id': doc.id,
                'nombre': doc.nombre_archivo,
                'error': str(e),
            })

    # Commit todos los éxitos juntos
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error al guardar cambios: {str(e)}'}), 500

    return jsonify({
        'success': True,
        'total': len(docs),
        'enviados': enviados,
        'errores': errores,
    })
