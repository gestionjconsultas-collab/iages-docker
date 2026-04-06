# backend/routes_soporte.py
"""
Rutas API para el sistema de soporte al cliente
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, TicketSoporte, MensajeSoporte, Empresa, User
from datetime import datetime
import traceback
from tenant_utils import get_current_gestoria_id
from constants import NotificationTypes

soporte_bp = Blueprint('soporte', __name__, url_prefix='/api/soporte')


# Helper function para verificar permisos de admin/soporte
def es_admin_o_soporte(user):
    """Verifica si el usuario es admin, super-admin o del equipo de soporte"""
    # Super-admin siempre tiene acceso
    if getattr(user, 'is_super_admin', False):
        return True
    
    # Soporte externo (gestoria_id NULL) tiene acceso
    if user.departamento and user.departamento.nombre == 'Soporte' and user.gestoria_id is None:
        return True
    
    # Jefatura y Soporte normal
    if not user.departamento:
        return False
    return user.departamento.nombre in ['Jefatura', 'Soporte']


# ============================================
# ENDPOINTS DE TICKETS
# ============================================

@soporte_bp.route('/tickets', methods=['GET'])
@login_required
def listar_tickets():
    """
    Lista tickets según el rol del usuario
    - Cliente: Solo sus tickets
    - Soporte/Admin: Todos los tickets
    
    Query params:
        - estado: Filtrar por estado
        - categoria: Filtrar por categoría
        - asignado_a: Filtrar por agente asignado
    """
    try:
        query = TicketSoporte.query
        
        # Verificar si es super-admin
        es_super_admin = getattr(current_user, 'is_super_admin', False)
        
        # Verificar si es del departamento de Soporte (NO Jefatura)
        es_soporte = current_user.departamento and current_user.departamento.nombre == 'Soporte'
        
        # Solo super-admin y Soporte ven TODOS los tickets
        if es_super_admin or es_soporte:
            # Ver todos los tickets de todas las gestorías
            pass
        else:
            # Todos los demás (incluyendo Jefatura) solo ven tickets de SU gestoría
            gestoria_id = get_current_gestoria_id()
            query = query.filter_by(gestoria_id=gestoria_id)
            
            # Si NO es Jefatura, solo ve sus propios tickets
            if not (current_user.departamento and current_user.departamento.nombre == 'Jefatura'):
                query = query.filter_by(usuario_creador_id=current_user.id)
        
        # Filtros opcionales
        estado = request.args.get('estado')
        if estado:
            query = query.filter_by(estado=estado)
        
        categoria = request.args.get('categoria')
        if categoria:
            query = query.filter_by(categoria=categoria)
        
        asignado_a = request.args.get('asignado_a', type=int)
        if asignado_a:
            query = query.filter_by(asignado_a_id=asignado_a)
        
        # Ordenar por fecha (más recientes primero)
        tickets = query.order_by(TicketSoporte.fecha_creacion.desc()).all()
        
        # Convertir a dict y calcular mensajes_sin_leer para el usuario actual
        tickets_data = []
        for t in tickets:
            ticket_dict = t.to_dict()
            # Recalcular mensajes_sin_leer para el usuario actual
            ticket_dict['mensajes_sin_leer'] = sum(
                1 for m in t.mensajes 
                if not m.leido and m.usuario_id != current_user.id
            )
            tickets_data.append(ticket_dict)
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'tickets': tickets_data
        })
    
    except Exception as e:
        print(f"❌ Error listando tickets: {str(e)}")
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/tickets', methods=['POST'])
@login_required
def crear_ticket():
    """
    Crea un nuevo ticket de soporte
    
    Body:
        - asunto: string (requerido)
        - descripcion: string
        - categoria: string
    """
    try:
        data = request.get_json()
        
        # Validaciones
        if not data.get('asunto'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Asunto es requerido'}), 400
        
        # Generar número de ticket
        numero_ticket = TicketSoporte.generar_numero_ticket()
        
        # Obtener gestoria_id del usuario creador (puede ser None para soporte externo)
        gestoria_id = current_user.gestoria_id or get_current_gestoria_id()
        
        # Crear ticket
        ticket = TicketSoporte(
            numero_ticket=numero_ticket,
            empresa_id=data.get('empresa_id'),  # Opcional
            gestoria_id=gestoria_id,  # De la gestoría del usuario creador
            usuario_creador_id=current_user.id,
            asunto=data['asunto'],
            descripcion=data.get('descripcion', ''),
            categoria=data.get('categoria', 'Consulta'),
            prioridad=data.get('prioridad', 'Media'),
            estado='Abierto'
        )
        
        db.session.add(ticket)
        db.session.flush()  # Para obtener el ID del ticket
        
        # ✅ Crear primer mensaje con la descripción si existe
        if data.get('descripcion'):
            from models import MensajeSoporte
            primer_mensaje = MensajeSoporte(
                ticket_id=ticket.id,
                usuario_id=current_user.id,
                mensaje=data['descripcion'],
                es_interno=False
            )
            db.session.add(primer_mensaje)
        
        db.session.commit()
        
        print(f"✅ Ticket creado: {numero_ticket} - {ticket.asunto}")
        
        # TODO: Enviar email a equipo de soporte
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'ticket': ticket.to_dict(),
            'message': f'Ticket {numero_ticket} creado exitosamente'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creando ticket: {str(e)}")
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def obtener_ticket(ticket_id):
    """Obtiene detalles de un ticket específico"""
    try:
        ticket = TicketSoporte.query.get_or_404(ticket_id)
        
        # Verificar permisos
        if not es_admin_o_soporte(current_user):
            if ticket.usuario_creador_id != current_user.id:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'ticket': ticket.to_dict()
        })
    
    except Exception as e:
        print(f"❌ Error obteniendo ticket: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/tickets/<int:ticket_id>', methods=['PUT'])
@login_required
def actualizar_ticket(ticket_id):
    """Actualiza un ticket (solo equipo de soporte)"""
    try:
        # Solo soporte/admin pueden actualizar
        if not es_admin_o_soporte(current_user):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
        
        ticket = TicketSoporte.query.get_or_404(ticket_id)
        data = request.get_json()
        
        # Actualizar campos permitidos
        if 'estado' in data:
            ticket.estado = data['estado']
            if data['estado'] == 'Resuelto' and not ticket.fecha_resolucion:
                ticket.fecha_resolucion = datetime.utcnow()
        
        if 'prioridad' in data:
            ticket.prioridad = data['prioridad']
        
        if 'asignado_a_id' in data:
            ticket.asignado_a_id = data['asignado_a_id']
        
        if 'valoracion' in data:
            ticket.valoracion = data['valoracion']
        
        if 'comentario_cierre' in data:
            ticket.comentario_cierre = data['comentario_cierre']
        
        ticket.fecha_actualizacion = datetime.utcnow()
        db.session.commit()
        
        print(f"✅ Ticket actualizado: {ticket.numero_ticket}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'ticket': ticket.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error actualizando ticket: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/tickets/<int:ticket_id>', methods=['DELETE'])
@login_required
def eliminar_ticket(ticket_id):
    """Elimina un ticket (solo admin)"""
    try:
        if not es_admin_o_soporte(current_user):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
        
        ticket = TicketSoporte.query.get_or_404(ticket_id)
        numero = ticket.numero_ticket
        
        db.session.delete(ticket)
        db.session.commit()
        
        print(f"🗑️ Ticket eliminado: {numero}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': f'Ticket {numero} eliminado'
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error eliminando ticket: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================
# ENDPOINTS DE MENSAJES
# ============================================

@soporte_bp.route('/tickets/<int:ticket_id>/mensajes', methods=['GET'])
@login_required
def listar_mensajes(ticket_id):
    """Lista mensajes de un ticket"""
    try:
        ticket = TicketSoporte.query.get_or_404(ticket_id)
        
        # Verificar permisos
        es_admin = es_admin_o_soporte(current_user)
        if not es_admin:
            if ticket.usuario_creador_id != current_user.id:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
        
        # Filtrar mensajes internos si es cliente
        mensajes = ticket.mensajes
        if not es_admin:
            mensajes = [m for m in mensajes if not m.es_interno]
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensajes': [m.to_dict() for m in mensajes]
        })
    
    except Exception as e:
        print(f"❌ Error listando mensajes: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500

# ⚠️ ENDPOINT DESHABILITADO - Ahora se usa el de routes_soporte_chat.py con WebSocket
# @soporte_bp.route('/tickets/<int:ticket_id>/mensajes', methods=['POST'])
# @login_required
# def enviar_mensaje(ticket_id):
#     """Envía un mensaje en un ticket"""
#     try:
#         ticket = TicketSoporte.query.get_or_404(ticket_id)
#         data = request.get_json()
#         
#         # Verificar permisos
#         es_admin = es_admin_o_soporte(current_user)
#         if not es_admin:
#             if ticket.usuario_creador_id != current_user.id:
#                 return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
#         
#         # Validar mensaje
#         if not data.get('mensaje'):
#             return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Mensaje es requerido'}), 400
#         
#         # Crear mensaje
#         mensaje = MensajeSoporte(
#             ticket_id=ticket_id,
#             usuario_id=current_user.id,
#             mensaje=data['mensaje'],
#             es_interno=data.get('es_interno', False) and es_admin
#         )
#         
#         db.session.add(mensaje)
#         
#         # Actualizar fecha de actualización del ticket
#         ticket.fecha_actualizacion = datetime.utcnow()
#         
#         # Si el ticket estaba cerrado, reabrirlo
#         if ticket.estado == 'Cerrado':
#             ticket.estado = 'Abierto'
#         
#         db.session.commit()
#         
#         print(f"💬 Mensaje enviado en ticket {ticket.numero_ticket}")
#         
#         # TODO: Enviar email de notificación
#         
#         return jsonify({
#             NotificationTypes.SUCCESS: True,
#             'mensaje': mensaje.to_dict()
#         })
#     
#     except Exception as e:
        db.session.rollback()
        print(f"❌ Error enviando mensaje: {str(e)}")
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/mensajes/<int:mensaje_id>/leer', methods=['PUT'])
@login_required
def marcar_leido(mensaje_id):
    """Marca un mensaje como leído"""
    try:
        mensaje = MensajeSoporte.query.get_or_404(mensaje_id)
        mensaje.leido = True
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True})
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error marcando mensaje como leído: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================
# ENDPOINTS DE MÉTRICAS
# ============================================

@soporte_bp.route('/metricas', methods=['GET'])
@login_required
def obtener_metricas():
    """Obtiene métricas del sistema de soporte (solo soporte/admin)"""
    try:
        if not es_admin_o_soporte(current_user):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No autorizado'}), 403
        
        # Contar tickets por estado
        total_tickets = TicketSoporte.query.count()
        abiertos = TicketSoporte.query.filter_by(estado='Abierto').count()
        en_proceso = TicketSoporte.query.filter_by(estado='En Proceso').count()
        resueltos = TicketSoporte.query.filter_by(estado='Resuelto').count()
        cerrados = TicketSoporte.query.filter_by(estado='Cerrado').count()
        
        # Tickets asignados al usuario actual
        mis_tickets = TicketSoporte.query.filter_by(asignado_a_id=current_user.id).count()
        
        # Tickets por categoría
        bugs = TicketSoporte.query.filter_by(categoria='Bug').count()
        consultas = TicketSoporte.query.filter_by(categoria='Consulta').count()
        mejoras = TicketSoporte.query.filter_by(categoria='Mejora').count()
        urgentes = TicketSoporte.query.filter_by(categoria='Urgente').count()
        
        # Valoración promedio
        tickets_valorados = TicketSoporte.query.filter(TicketSoporte.valoracion.isnot(None)).all()
        valoracion_promedio = sum(t.valoracion for t in tickets_valorados) / len(tickets_valorados) if tickets_valorados else 0
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'metricas': {
                'total_tickets': total_tickets,
                'por_estado': {
                    'abiertos': abiertos,
                    'en_proceso': en_proceso,
                    'resueltos': resueltos,
                    'cerrados': cerrados
                },
                'mis_tickets': mis_tickets,
                'por_categoria': {
                    'bugs': bugs,
                    'consultas': consultas,
                    'mejoras': mejoras,
                    'urgentes': urgentes
                },
                'valoracion_promedio': round(valoracion_promedio, 2)
            }
        })
    
    except Exception as e:
        print(f"❌ Error obteniendo métricas: {str(e)}")
        traceback.print_exc()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@soporte_bp.route('/notificaciones', methods=['GET'])
@login_required
def obtener_notificaciones():
    """Obtiene notificaciones de mensajes sin leer"""
    try:
        # Obtener tickets del usuario
        if es_admin_o_soporte(current_user):
            # Soporte ve todos los tickets asignados
            tickets = TicketSoporte.query.filter_by(asignado_a_id=current_user.id).all()
        else:
            # Cliente ve solo sus tickets
            tickets = TicketSoporte.query.filter_by(usuario_creador_id=current_user.id).all()
        
        # Contar mensajes sin leer
        mensajes_sin_leer = 0
        for ticket in tickets:
            for mensaje in ticket.mensajes:
                # No contar mensajes propios
                if mensaje.usuario_id != current_user.id and not mensaje.leido:
                    mensajes_sin_leer += 1
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensajes_sin_leer': mensajes_sin_leer
        })
    
    except Exception as e:
        print(f"❌ Error obteniendo notificaciones: {str(e)}")
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500
