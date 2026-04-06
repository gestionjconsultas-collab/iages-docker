"""
Módulo centralizado para emitir eventos de notificaciones en tiempo real via SocketIO.
"""
from flask_socketio import emit
from datetime import datetime


def _get_jefatura_room():
    """
    Obtiene el nombre de la room del departamento Jefatura consultando la BD.
    Evita hardcodear 'departamento_Jefatura' por si el nombre cambia.
    Devuelve None si no existe el departamento.
    """
    try:
        from models import Departamento
        dep = Departamento.query.filter_by(nombre='Jefatura').first()
        if dep:
            return f'departamento_{dep.nombre}'
        return None
    except Exception:
        return None

def notify_documento_procesado(socketio, documento_id, user_id, nombre_archivo, categoria):
    """
    Notifica cuando un documento ha sido procesado por IA.
    
    Args:
        socketio: Instancia de SocketIO
        documento_id: ID del documento
        user_id: ID del usuario que subió el documento
        nombre_archivo: Nombre del archivo procesado
        categoria: Categoría asignada
    """
    socketio.emit('documento_procesado', {
        'documento_id': documento_id,
        'nombre_archivo': nombre_archivo,
        'categoria': categoria,
        'mensaje': f'✅ Documento procesado: {nombre_archivo}'
    }, room=f'user_{user_id}')
    
    # También notificar a Jefatura (room obtenida de BD para evitar hardcoding)
    jefatura_room = _get_jefatura_room()
    if jefatura_room:
        socketio.emit('documento_procesado', {
            'documento_id': documento_id,
            'nombre_archivo': nombre_archivo,
            'categoria': categoria,
            'mensaje': f'📄 Nuevo documento procesado: {nombre_archivo}'
        }, room=jefatura_room)


def notify_tarea_asignada(socketio, documento_id, user_id, nombre_archivo, asignado_por_nombre):
    """
    Notifica cuando se asigna una tarea a un usuario.
    
    Args:
        socketio: Instancia de SocketIO
        documento_id: ID del documento
        user_id: ID del usuario asignado
        nombre_archivo: Nombre del archivo
        asignado_por_nombre: Nombre de quien asignó
    """
    socketio.emit('tarea_asignada', {
        'documento_id': documento_id,
        'nombre_archivo': nombre_archivo,
        'asignado_por': asignado_por_nombre,
        'mensaje': f'📋 Nueva tarea asignada: {nombre_archivo}'
    }, room=f'user_{user_id}')


def notify_recordatorio(socketio, user_id, documento_id, nombre_archivo, tipo, horas_restantes):
    """
    Notifica recordatorio de vencimiento próximo.
    
    Args:
        socketio: Instancia de SocketIO
        user_id: ID del usuario
        documento_id: ID del documento
        nombre_archivo: Nombre del archivo
        tipo: Tipo de recordatorio ('vencimiento', 'plazo')
        horas_restantes: Horas hasta el vencimiento
    """
    if horas_restantes <= 24:
        emoji = '🚨'
        urgencia = 'URGENTE'
    elif horas_restantes <= 48:
        emoji = '⚠️'
        urgencia = 'Próximo'
    else:
        emoji = '⏰'
        urgencia = 'Recordatorio'
    
    socketio.emit('recordatorio_vencimiento', {
        'documento_id': documento_id,
        'nombre_archivo': nombre_archivo,
        'tipo': tipo,
        'horas_restantes': horas_restantes,
        'mensaje': f'{emoji} {urgencia}: {nombre_archivo} vence en {int(horas_restantes)}h'
    }, room=f'user_{user_id}')


def notify_saltra_nueva(socketio, notificacion_id, tipo, nif_titular, tiene_empresa):
    """
    Notifica nueva notificación de SALTRA detectada.
    
    Args:
        socketio: Instancia de SocketIO
        notificacion_id: ID de la notificación SALTRA
        tipo: Tipo de notificación
        nif_titular: NIF del titular
        tiene_empresa: Boolean si ya está asociada a empresa
    """
    mensaje = f'📨 Nueva notificación SALTRA: {tipo}'
    if not tiene_empresa:
        mensaje += ' (sin empresa asignada)'
    
    # Solo notificar a Jefatura (room obtenida de BD para evitar hardcoding)
    jefatura_room = _get_jefatura_room()
    if jefatura_room:
        socketio.emit('notificacion_saltra', {
            'notificacion_id': notificacion_id,
            'tipo': tipo,
            'nif_titular': nif_titular,
            'tiene_empresa': tiene_empresa,
            'mensaje': mensaje
        }, room=jefatura_room)


def notify_custom(socketio, user_id, tipo, mensaje, datos=None, gestoria_id=None):
    """
    Notificación personalizada genérica.

    Args:
        socketio: Instancia de SocketIO
        user_id: ID del usuario (o None para emitir a toda una gestoría)
        tipo: Tipo de notificación ('info', 'success', 'warning', 'error')
        mensaje: Mensaje a mostrar
        datos: Datos adicionales (opcional)
        gestoria_id: ID de la gestoría para emitir (requerido si user_id es None)
    """
    payload = {
        'tipo': tipo,
        'mensaje': mensaje,
        'datos': datos or {}
    }

    if user_id:
        socketio.emit('notificacion_custom', payload, room=f'user_{user_id}')
    elif gestoria_id:
        # ✅ Emitir solo a la gestoría específica, no broadcast total
        socketio.emit('notificacion_custom', payload, room=f'gestoria_{gestoria_id}')
    else:
        # ⚠️ Broadcast total — solo usar si realmente se quiere notificar a TODOS los usuarios
        import logging
        logging.getLogger(__name__).warning('notify_custom: broadcast total sin user_id ni gestoria_id — considera usar gestoria_id')
        socketio.emit('notificacion_custom', payload, broadcast=True)


def notify_tarea_chat_ia(socketio, tarea_id, user_id, titulo, fecha_vencimiento=None):
    """
    Notifica cuando el Chat IA crea una nueva tarea.
    
    Args:
        socketio: Instancia de SocketIO
        tarea_id: ID de la tarea creada
        user_id: ID del usuario que creó la tarea
        titulo: Título de la tarea
        fecha_vencimiento: Fecha de vencimiento (opcional)
    """
    mensaje = f'🤖 Chat IA creó una tarea: {titulo}'
    if fecha_vencimiento:
        from datetime import datetime
        fecha_str = datetime.fromisoformat(str(fecha_vencimiento)).strftime('%d/%m/%Y')
        mensaje += f' (vence: {fecha_str})'
    
    socketio.emit('tarea_chat_ia', {
        'tarea_id': tarea_id,
        'titulo': titulo,
        'fecha_vencimiento': fecha_vencimiento.isoformat() if fecha_vencimiento else None,
        'mensaje': mensaje
    }, room=f'user_{user_id}')
    
    # También emitir evento genérico para refrescar stats
    socketio.emit('stats_updated', {
        'tipo': 'tarea_nueva',
        'tarea_id': tarea_id
    }, room=f'user_{user_id}')


def notify_stats_updated(socketio, tipo, gestoria_id=None, user_id=None):
    """
    Notifica que las estadísticas han cambiado y deben refrescarse.
    
    Args:
        socketio: Instancia de SocketIO
        tipo: Tipo de cambio ('tarea_nueva', 'tarea_completada', 'documento_nuevo', etc.)
        gestoria_id: ID de gestoría (para broadcast a toda la gestoría)
        user_id: ID de usuario específico (opcional)
    """
    payload = {
        'tipo': tipo,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    if user_id:
        socketio.emit('stats_updated', payload, room=f'user_{user_id}')
    elif gestoria_id:
        socketio.emit('stats_updated', payload, room=f'gestoria_{gestoria_id}')
    else:
        socketio.emit('stats_updated', payload, broadcast=True)

def notify_permissions_updated(socketio, user_id):
    """
    Notifica a un usuario que sus permisos/accesos han cambiado
    y debe refrescar su estado de sesión.
    """
    socketio.emit('permissions_updated', {
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
        'mensaje': 'Sus permisos de acceso han sido actualizados.'
    }, room=f'user_{user_id}')
def notify_guests_of_document(socketio, documento, notificacion_payload):
    """
    Notifica tanto a los staff de la gestoría como a los invitados autorizados.
    
    Args:
        socketio: Instancia de SocketIO
        documento: Instancia del modelo Documento
        notificacion_payload: Diccionario con los datos de la notificación (to_dict())
    """
    from models import User
    
    try:
        # 0. Notificar al usuario que realizó la acción (Staff o Cliente)
        # Esto asegura que el autor siempre vea su propia confirmación en verde
        _subido_por = getattr(documento, 'subido_por_id', None)
        if _subido_por:
            socketio.emit('nueva_notificacion', notificacion_payload, room=f'user_{_subido_por}')

        # 1. Notificar al Staff (Jefatura y otros)
        # Emitimos solo a la sala de staff para evitar duplicados en invitados
        gestoria_id = documento.gestoria_id
        if gestoria_id:
            socketio.emit('nueva_notificacion', notificacion_payload, room=f'gestoria_staff_{gestoria_id}')

        # 2. Notificar a los Invitados (Clientes) autorizados de esta gestoría
        # Filtramos por gestoria_id para no cargar invitados de otras gestorías
        invitados = User.query.filter(
            User.departamento.has(nombre='Invitado'),
            User.gestoria_id == gestoria_id
        ).all()
        for inv in invitados:
            if inv.has_access_to_company(documento.empresa_id) and inv.id != _subido_por:
                socketio.emit('nueva_notificacion', notificacion_payload, room=f'user_{inv.id}')
                
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error en notify_guests_of_document: {e}")
