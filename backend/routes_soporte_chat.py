# backend/routes_soporte_chat.py
"""
Rutas para el sistema de chat interactivo de soporte
Incluye asignación de tickets, mensajería en tiempo real, y sistema de valoración
Mejoras v2: paginación, notas internas, read receipts RT, transferir, adjuntos, email offline, agente online
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, TicketSoporte, MensajeSoporte, User, Departamento
from datetime import datetime
from sqlalchemy import or_
import os

soporte_chat_bp = Blueprint('soporte_chat', __name__)

# ---------------------------------------------------------------------------
# Helpers de permisos (reutilizables)
# ---------------------------------------------------------------------------

def _get_permisos(ticket):
    """Devuelve un dict con los flags de permiso del current_user para este ticket."""
    es_soporte = bool(current_user.departamento and
                      current_user.departamento.nombre.strip() == 'Soporte')
    es_soporte_externo = es_soporte and current_user.gestoria_id is None
    es_superadmin = current_user.is_super_admin
    es_admin = bool(current_user.departamento and
                    current_user.departamento.nombre.strip() == 'Jefatura')
    return {
        'es_creador':        ticket.usuario_creador_id == current_user.id,
        'es_asignado':       ticket.asignado_a_id == current_user.id,
        'es_soporte':        es_soporte,
        'es_soporte_externo': es_soporte_externo,
        'es_superadmin':     es_superadmin,
        'es_admin':          es_admin,
        'es_agente':         es_soporte or es_soporte_externo or es_superadmin or es_admin,
    }


def _verificar_acceso_ticket(ticket, perms):
    """Devuelve (ok, error_response). Comprueba gestoría y permisos básicos."""
    if not perms['es_soporte_externo'] and not perms['es_superadmin']:
        ticket_gestoria = getattr(ticket, 'gestoria_id', None)
        if ticket_gestoria and ticket_gestoria != current_user.gestoria_id:
            return False, (jsonify({'error': 'No autorizado'}), 403)
    if not any([perms['es_creador'], perms['es_asignado'], perms['es_agente']]):
        return False, (jsonify({'error': 'No autorizado'}), 403)
    return True, None


# ---------------------------------------------------------------------------
# GET mensajes (con paginación + filtro notas internas)
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/mensajes', methods=['GET'])
@login_required
def get_mensajes_ticket(ticket_id):
    """Obtiene mensajes de un ticket con paginación."""
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    perms = _get_permisos(ticket)
    ok, err = _verificar_acceso_ticket(ticket, perms)
    if not ok:
        return err

    # Paginación: ?page=1&per_page=50 (por defecto carga los últimos 50)
    page     = request.args.get('page',     1,  type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = MensajeSoporte.query.filter_by(ticket_id=ticket_id)

    # Ocultar notas internas a usuarios no-agentes
    if not perms['es_agente']:
        query = query.filter_by(es_interno=False)

    total = query.count()
    # Carga en orden inverso para paginar y luego revertir (scroll infinito)
    mensajes_paginados = (
        query
        .order_by(MensajeSoporte.fecha_creacion.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    mensajes = list(reversed(mensajes_paginados.items))

    # Marcar como leídos los mensajes ajenos
    try:
        marcados = 0
        for m in mensajes:
            if m.usuario_id != current_user.id and not m.leido:
                m.leido = True
                marcados += 1
        if marcados:
            db.session.commit()
            # Emitir read receipt en tiempo real al emisor de cada mensaje
            sio = current_app.extensions.get('socketio')
            sio.emit('mensajes_leidos', {
                'ticket_id': ticket_id,
                'leido_por': current_user.id
            }, room=f'ticket_{ticket_id}')
    except Exception as e:
        db.session.rollback()

    return jsonify({
        'success':   True,
        'mensajes':  [m.to_dict() for m in mensajes],
        'total':     total,
        'page':      page,
        'per_page':  per_page,
        'has_prev':  mensajes_paginados.has_prev,
        'has_next':  mensajes_paginados.has_next,
    })


# ---------------------------------------------------------------------------
# POST mensaje (con email offline + soporte notas internas)
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/mensajes', methods=['POST'])
@login_required
def enviar_mensaje_ticket(ticket_id):
    """Envía un mensaje en un ticket."""
    data   = request.json
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    perms  = _get_permisos(ticket)
    ok, err = _verificar_acceso_ticket(ticket, perms)
    if not ok:
        return err

    es_interno = bool(data.get('es_interno', False)) and perms['es_agente']

    mensaje = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje=data.get('mensaje'),
        es_interno=es_interno,
        es_respuesta_soporte=perms['es_agente'],
        es_mensaje_sistema=False
    )

    db.session.add(mensaje)
    ticket.fecha_actualizacion = datetime.utcnow()
    db.session.commit()

    sio       = current_app.extensions.get('socketio')
    room_name = f'ticket_{ticket_id}'

    event_data = {
        'ticket_id': ticket_id,
        'mensaje':   mensaje.to_dict()
    }

    # Emitir al room del ticket
    sio.emit('nuevo_mensaje_soporte', event_data, room=room_name)

    # Notificación email si el destinatario no está conectado al room
    _notificar_offline_si_necesario(ticket, mensaje, sio, room_name)

    return jsonify({'success': True, 'mensaje': mensaje.to_dict()})


def _notificar_offline_si_necesario(ticket, mensaje, sio, room_name):
    """Envía email al destinatario si no está en el room del ticket."""
    try:
        # Determinar destinatario: si el emisor es agente → notificar al creador, y viceversa
        if mensaje.es_respuesta_soporte:
            destinatario_user = ticket.usuario_creador
        else:
            destinatario_user = ticket.asignado_a

        if not destinatario_user or not destinatario_user.email:
            return

        # Comprobar si el destinatario está en el room
        try:
            participantes = list(sio.server.manager.get_participants('/', room_name))
            sids_en_room  = [sid for sid, _ in participantes]
        except Exception:
            sids_en_room = []

        # Si hay participantes en el room asumimos que el destinatario está online
        # (no podemos mapear SID→user_id sin overhead, así que solo enviamos si el room está vacío)
        if sids_en_room:
            return

        # Room vacío → enviar email
        from email_sender import enviar_email
        asunto  = f'Nuevo mensaje en ticket {ticket.numero_ticket}: {ticket.asunto}'
        cuerpo  = f"""
        <p>Has recibido un nuevo mensaje de <strong>{mensaje.usuario.nombre if mensaje.usuario else 'Usuario'}</strong>
        en el ticket <strong>{ticket.numero_ticket}</strong>.</p>
        <blockquote style="border-left:3px solid #3b82f6;padding-left:12px;color:#374151;">
            {mensaje.mensaje[:500]}
        </blockquote>
        <p>Accede al sistema para responder.</p>
        """
        enviar_email(destinatario_user.email, asunto, cuerpo,
                     gestoria_id=ticket.gestoria_id)
    except Exception as e:
        print(f"⚠️ Error enviando email offline: {e}")


# ---------------------------------------------------------------------------
# Marcar mensajes como leídos (con socket event)
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/marcar-leido', methods=['POST'])
@login_required
def marcar_mensajes_leidos(ticket_id):
    """Marca todos los mensajes ajenos como leídos y emite read receipt."""
    try:
        mensajes_no_leidos = MensajeSoporte.query.filter(
            MensajeSoporte.ticket_id == ticket_id,
            MensajeSoporte.usuario_id != current_user.id,
            MensajeSoporte.leido == False
        ).all()

        for m in mensajes_no_leidos:
            m.leido = True

        db.session.commit()

        # Emitir read receipt en tiempo real
        sio = current_app.extensions.get('socketio')
        sio.emit('mensajes_leidos', {
            'ticket_id': ticket_id,
            'leido_por': current_user.id,
            'cantidad':  len(mensajes_no_leidos)
        }, room=f'ticket_{ticket_id}')

        return jsonify({'success': True, 'mensajes_marcados': len(mensajes_no_leidos)})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Adjuntos
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/adjuntos', methods=['POST'])
@login_required
def subir_adjunto(ticket_id):
    """Sube un archivo adjunto al ticket y crea un mensaje con él."""
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    perms  = _get_permisos(ticket)
    ok, err = _verificar_acceso_ticket(ticket, perms)
    if not ok:
        return err

    archivo = request.files.get('archivo')
    if not archivo:
        return jsonify({'error': 'No se envió ningún archivo'}), 400

    # Solo imágenes permitidas (PDFs y docs rechazados por seguridad)
    EXTENSIONES_PERMITIDAS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = archivo.filename.rsplit('.', 1)[-1].lower() if '.' in archivo.filename else ''
    if ext not in EXTENSIONES_PERMITIDAS:
        return jsonify({'error': 'Solo se permiten imágenes (PNG, JPG, JPEG, GIF, WEBP)'}), 400

    MAX_SIZE = 10 * 1024 * 1024  # 10 MB
    archivo.seek(0, 2)
    size = archivo.tell()
    archivo.seek(0)
    if size > MAX_SIZE:
        return jsonify({'error': 'Archivo demasiado grande (máx 10 MB)'}), 400

    # Guardar en disco
    from werkzeug.utils import secure_filename
    import uuid
    nombre_seguro = secure_filename(archivo.filename)
    nombre_unico  = f"{uuid.uuid4().hex}_{nombre_seguro}"

    directorio = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'storage', 'soporte', str(ticket_id)
    )
    os.makedirs(directorio, exist_ok=True)
    ruta = os.path.join(directorio, nombre_unico)
    archivo.save(ruta)

    # Crear mensaje con adjunto
    mensaje = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje=f'📎 {nombre_seguro}',
        es_respuesta_soporte=perms['es_agente'],
        adjuntos=[{'nombre': nombre_seguro, 'ruta': ruta, 'nombre_disco': nombre_unico}]
    )
    db.session.add(mensaje)
    ticket.fecha_actualizacion = datetime.utcnow()
    db.session.commit()

    sio = current_app.extensions.get('socketio')
    sio.emit('nuevo_mensaje_soporte', {
        'ticket_id': ticket_id,
        'mensaje':   mensaje.to_dict()
    }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True, 'mensaje': mensaje.to_dict()})


@soporte_chat_bp.route('/api/soporte/adjuntos/<int:ticket_id>/<nombre_disco>', methods=['GET'])
@login_required
def descargar_adjunto(ticket_id, nombre_disco):
    """Descarga un archivo adjunto de un ticket."""
    from flask import send_file
    from werkzeug.utils import secure_filename
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    perms  = _get_permisos(ticket)
    ok, err = _verificar_acceso_ticket(ticket, perms)
    if not ok:
        return err

    nombre_seguro = secure_filename(nombre_disco)
    ruta = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'storage', 'soporte', str(ticket_id), nombre_seguro
    )
    if not os.path.exists(ruta):
        return jsonify({'error': 'Archivo no encontrado'}), 404

    return send_file(ruta, as_attachment=True)


# ---------------------------------------------------------------------------
# Transferir ticket
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/transferir', methods=['POST'])
@login_required
def transferir_ticket(ticket_id):
    """Transfiere el ticket a otro agente de soporte."""
    ticket = TicketSoporte.query.get_or_404(ticket_id)
    perms  = _get_permisos(ticket)

    # Solo agentes pueden transferir
    if not perms['es_agente']:
        return jsonify({'error': 'No autorizado'}), 403

    data           = request.json
    nuevo_agente_id = data.get('agente_id')
    if not nuevo_agente_id:
        return jsonify({'error': 'agente_id requerido'}), 400

    nuevo_agente = User.query.get(nuevo_agente_id)
    if not nuevo_agente:
        return jsonify({'error': 'Agente no encontrado'}), 404

    agente_anterior_nombre = ticket.asignado_a.nombre if ticket.asignado_a else 'Sin asignar'
    ticket.asignado_a_id    = nuevo_agente_id
    ticket.fecha_actualizacion = datetime.utcnow()

    # Mensaje automático de transferencia
    msg_transfer = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje=f'Ticket transferido de {agente_anterior_nombre} a {nuevo_agente.nombre}.',
        es_mensaje_sistema=True
    )
    db.session.add(msg_transfer)
    db.session.commit()

    sio = current_app.extensions.get('socketio')
    sio.emit('ticket_transferido', {
        'ticket_id':      ticket_id,
        'nuevo_agente':   nuevo_agente.nombre,
        'nuevo_agente_id': nuevo_agente_id,
        'mensaje':        msg_transfer.to_dict()
    }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True, 'ticket': ticket.to_dict()})


# ---------------------------------------------------------------------------
# Agentes disponibles para transferencia
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/agentes', methods=['GET'])
@login_required
def listar_agentes_soporte():
    """Lista agentes de soporte disponibles para transferir tickets."""
    es_soporte   = current_user.departamento and current_user.departamento.nombre == 'Soporte'
    es_superadmin = current_user.is_super_admin

    if not (es_soporte or es_superadmin):
        return jsonify({'error': 'No autorizado'}), 403

    agentes = User.query.join(Departamento).filter(
        Departamento.nombre == 'Soporte',
        User.activo == True
    ).all()

    return jsonify({
        'success': True,
        'agentes': [{'id': a.id, 'nombre': a.nombre, 'email': a.email} for a in agentes]
    })


# ---------------------------------------------------------------------------
# Agente online (basado en presencia en room user_X)
# ---------------------------------------------------------------------------

@soporte_chat_bp.route('/api/soporte/agente-online/<int:user_id>', methods=['GET'])
@login_required
def agente_online(user_id):
    """Comprueba si un usuario está conectado al socket."""
    try:
        from extensions import socketio as sio_ext
        room   = f'user_{user_id}'
        partic = list(sio_ext.server.manager.get_participants('/', room))
        online = len(partic) > 0
    except Exception:
        online = False
    return jsonify({'online': online, 'user_id': user_id})


# ============================================================================
# Asignación de tickets
# ============================================================================

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/tomar', methods=['POST'])
@login_required
def tomar_ticket(ticket_id):
    """Agente de soporte toma un ticket sin asignar."""
    es_soporte    = current_user.departamento and current_user.departamento.nombre == 'Soporte'
    es_superadmin = current_user.is_super_admin

    if not (es_soporte or es_superadmin):
        return jsonify({'error': 'Solo soporte o superadmin pueden tomar tickets'}), 403

    ticket = TicketSoporte.query.get_or_404(ticket_id)

    if ticket.asignado_a_id:
        return jsonify({'error': 'Ticket ya asignado'}), 400

    ticket.asignado_a_id    = current_user.id
    ticket.fecha_asignacion  = datetime.utcnow()
    ticket.estado            = 'En Proceso'

    mensaje_bienvenida = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje=f"Hola buen día, soy {current_user.nombre} de soporte. ¿En qué le podemos ayudar?",
        es_respuesta_soporte=True,
        es_mensaje_sistema=False
    )
    db.session.add(mensaje_bienvenida)
    db.session.commit()

    sio = current_app.extensions.get('socketio')
    sio.emit('ticket_asignado', {
        'ticket_id': ticket_id,
        'agente':    current_user.nombre,
        'mensaje':   mensaje_bienvenida.to_dict()
    }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True, 'ticket': ticket.to_dict(), 'mensaje': mensaje_bienvenida.to_dict()})


# ============================================================================
# Cierre y valoración
# ============================================================================

@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/finalizar', methods=['POST'])
@login_required
def finalizar_ticket(ticket_id):
    """Agente finaliza el ticket y solicita valoración."""
    ticket = TicketSoporte.query.get_or_404(ticket_id)

    es_jefatura = bool(current_user.departamento and
                       current_user.departamento.nombre.strip() == 'Jefatura')
    if ticket.asignado_a_id != current_user.id and not es_jefatura and not current_user.is_super_admin:
        return jsonify({'error': 'No autorizado'}), 403

    ticket.estado           = 'Resuelto'
    ticket.fecha_resolucion = datetime.utcnow()

    mensaje_cierre = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje="Su ticket ha sido cerrado. ¿Podría ayudarnos a valorar cómo le atendimos?",
        es_respuesta_soporte=True,
        es_mensaje_sistema=True
    )
    db.session.add(mensaje_cierre)
    db.session.commit()

    sio = current_app.extensions.get('socketio')
    sio.emit('ticket_finalizado', {
        'ticket_id': ticket_id,
        'mensaje':   mensaje_cierre.to_dict()
    }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True, 'mensaje': mensaje_cierre.to_dict()})


@soporte_chat_bp.route('/api/soporte/tickets/<int:ticket_id>/valorar', methods=['POST'])
@login_required
def valorar_ticket(ticket_id):
    """Usuario valora el servicio de soporte."""
    data   = request.json
    ticket = TicketSoporte.query.get_or_404(ticket_id)

    if ticket.usuario_creador_id != current_user.id:
        return jsonify({'error': 'No autorizado'}), 403

    valoracion = data.get('valoracion')
    if not valoracion or valoracion < 1 or valoracion > 5:
        return jsonify({'error': 'Valoración debe ser entre 1 y 5'}), 400

    ticket.valoracion        = valoracion
    ticket.comentario_cierre = data.get('comentario', '')
    ticket.estado            = 'Cerrado'

    mensaje_gracias = MensajeSoporte(
        ticket_id=ticket_id,
        usuario_id=current_user.id,
        mensaje=f"¡Gracias por su valoración de {ticket.valoracion} estrellas! Su opinión nos ayuda a mejorar.",
        es_mensaje_sistema=True
    )
    db.session.add(mensaje_gracias)
    db.session.commit()

    sio = current_app.extensions.get('socketio')
    sio.emit('ticket_valorado', {
        'ticket_id': ticket_id,
        'valoracion': ticket.valoracion,
        'mensaje':    mensaje_gracias.to_dict()
    }, room=f'ticket_{ticket_id}')

    return jsonify({'success': True, 'mensaje': mensaje_gracias.to_dict()})


# ============================================================================
# Métricas
# ============================================================================

@soporte_chat_bp.route('/api/soporte/metricas', methods=['GET'])
@login_required
def get_metricas_soporte():
    """Métricas de performance de agentes de soporte."""
    es_soporte = current_user.departamento and current_user.departamento.nombre == 'Soporte'

    if not (current_user.is_super_admin or es_soporte):
        return jsonify({'error': 'No autorizado'}), 403

    gestoria_id = current_user.gestoria_id

    agentes = User.query.join(Departamento).filter(
        Departamento.nombre == 'Soporte',
        User.gestoria_id == gestoria_id,
        User.activo == True
    ).all()

    metricas = []
    for agente in agentes:
        tickets_resueltos = TicketSoporte.query.filter_by(
            asignado_a_id=agente.id
        ).filter(TicketSoporte.estado.in_(['Resuelto', 'Cerrado'])).all()

        valoraciones   = [t.valoracion for t in tickets_resueltos if t.valoracion]
        promedio_rating = sum(valoraciones) / len(valoraciones) if valoraciones else 0

        tiempos = []
        for t in tickets_resueltos:
            if t.fecha_asignacion and t.fecha_resolucion:
                tiempos.append((t.fecha_resolucion - t.fecha_asignacion).total_seconds() / 3600)

        metricas.append({
            'agente_id':            agente.id,
            'agente_nombre':        agente.nombre,
            'tickets_resueltos':    len(tickets_resueltos),
            'promedio_rating':      round(promedio_rating, 2),
            'total_valoraciones':   len(valoraciones),
            'tiempo_promedio_horas': round(sum(tiempos) / len(tiempos), 1) if tiempos else 0
        })

    metricas.sort(key=lambda x: x['promedio_rating'], reverse=True)
    return jsonify({'success': True, 'metricas': metricas})
