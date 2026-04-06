"""
Push Notifications Service para IAGES
Maneja suscripciones y envío de notificaciones push
"""

from flask import current_app
from pywebpush import webpush, WebPushException
import json
import logging

logger = logging.getLogger(__name__)


class PushNotificationService:
    """
    Servicio para enviar notificaciones push a usuarios suscritos
    """
    
    @staticmethod
    def send_notification(subscription_info, notification_data):
        """
        Envía una notificación push a un usuario
        
        Args:
            subscription_info: Dict con endpoint, keys (p256dh, auth)
            notification_data: Dict con title, body, icon, badge, data
            
        Returns:
            bool: True si se envió correctamente
        """
        try:
            # Obtener claves VAPID del config
            vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
            vapid_claims = {
                "sub": f"mailto:{current_app.config.get('VAPID_CLAIM_EMAIL', 'admin@iages.com')}"
            }
            
            # Preparar payload
            payload = json.dumps(notification_data)
            
            # Enviar notificación
            response = webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
                headers={
                    "Urgency": "high",
                    "TTL": "43200"  # 12 horas
                }
            )
            
            logger.info(f"✅ Notificación push enviada: {notification_data.get('title')}")
            return True
            
        except WebPushException as e:
            logger.error(f"❌ Error enviando push: {e}")
            
            # Si la suscripción expiró (410 Gone) o no se encuentra (404), eliminarla
            if e.response is not None and e.response.status_code in (404, 410):
                logger.warning(f"Suscripción expirada ({e.response.status_code}), eliminando de BD")
                try:
                    from models import PushSubscription
                    from app import db
                    endpoint = subscription_info.get('endpoint')
                    if endpoint:
                        PushSubscription.query.filter_by(endpoint=endpoint).delete()
                        db.session.commit()
                        logger.info("Suscripción eliminada con éxito")
                except Exception as db_err:
                    logger.error(f"Error al eliminar suscripción: {db_err}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return False
    
    @staticmethod
    def send_to_user(user_id, notification_data):
        """
        Envía notificación a todas las suscripciones de un usuario
        
        Args:
            user_id: ID del usuario
            notification_data: Dict con datos de la notificación
            
        Returns:
            int: Número de notificaciones enviadas exitosamente
        """
        from models import PushSubscription
        
        # Obtener todas las suscripciones del usuario
        subscriptions = PushSubscription.query.filter_by(
            user_id=user_id,
            active=True
        ).all()
        
        sent_count = 0
        for sub in subscriptions:
            subscription_info = {
                'endpoint': sub.endpoint,
                'keys': {
                    'p256dh': sub.p256dh,
                    'auth': sub.auth
                }
            }
            
            if PushNotificationService.send_notification(subscription_info, notification_data):
                sent_count += 1
        
        logger.info(f"📤 Enviadas {sent_count}/{len(subscriptions)} notificaciones a usuario {user_id}")
        return sent_count
    
    @staticmethod
    def send_segmented_push(gestoria_id, alcance, filtro_id, notification_data, exclude_user_id=None):
        """
        Envía notificación push segmentada basándose en el alcance del comunicado
        """
        from models import User
        
        # Obtener usuarios activos de la gestoría
        query = User.query.filter_by(gestoria_id=gestoria_id, activo=True)
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        
        users = query.all()
        total_notified = 0
        
        for user in users:
            should_notify = False
            
            # Jefatura / Admin ven todos los alcances
            if not user.is_invitado() or user.is_super_admin:
                should_notify = True
            else:
                # Usuarios "Invitado" (Clientes) tienen segmentación
                if alcance == 'global':
                    should_notify = True
                elif alcance == 'grupo' and filtro_id:
                    # Verificar si tiene acceso al grupo
                    should_notify = any(ga.grupo_id == int(filtro_id) for ga in user.grupo_accesos)
                elif alcance == 'empresa' and filtro_id:
                    # Verificar si tiene acceso a la empresa
                    should_notify = user.has_access_to_company(int(filtro_id))
            
            if should_notify:
                sent_count = PushNotificationService.send_to_user(user.id, notification_data)
                if sent_count > 0:
                    total_notified += 1
                    
        logger.info(f"📤 Push segmentado ({alcance}) enviado a {total_notified} usuarios")
        return total_notified


# Funciones helper para tipos comunes de notificaciones

def notify_new_document(user_id, document_name, empresa_name):
    """Notificar nuevo documento"""
    notification = {
        'title': 'Nuevo documento',
        'body': f'{document_name} de {empresa_name}',
        'icon': '/logo-light.png',
        'badge': '/notification-badge.png',
        'data': {
            'url': '/mesa-trabajo',
            'type': 'new_document'
        }
    }
    return PushNotificationService.send_to_user(user_id, notification)


def notify_task_assigned(user_id, task_description):
    """Notificar tarea asignada"""
    notification = {
        'title': 'Nueva tarea asignada',
        'body': task_description,
        'icon': '/logo-light.png',
        'badge': '/notification-badge.png',
        'data': {
            'url': '/tareas',
            'type': 'task_assigned'
        }
    }
    return PushNotificationService.send_to_user(user_id, notification)


def notify_document_processed(user_id, document_name):
    """Notificar documento procesado"""
    notification = {
        'title': 'Documento procesado',
        'body': f'{document_name} ha sido procesado',
        'icon': '/logo-light.png',
        'badge': '/notification-badge.png',
        'data': {
            'url': '/documentos',
            'type': 'document_processed'
        }
    }
    return PushNotificationService.send_to_user(user_id, notification)


def notify_document_available(user_id, document_type, document_name, company_name, document_id):
    """Notificar documento disponible (contextual)"""
    # Iconos por tipo de documento
    DOCUMENT_ICONS = {
        'nomina': '💰',
        'impuestos': '📊',
        'seguro_social': '🏥',
        'contrato': '📄',
        'factura': '🧾',
        'default': '📁'
    }
    
    icon_emoji = DOCUMENT_ICONS.get(document_type.lower(), DOCUMENT_ICONS['default'])
    
    notification = {
        'title': f'{icon_emoji} {document_type.title()} disponible',
        'body': f'{document_name} de {company_name}',
        'icon': '/logo-light.png',
        'badge': '/notification-badge.png',
        'data': {
            'url': f'/mesa-trabajo?doc={document_id}',
            'type': 'document_notification',
            'document_id': document_id
        }
    }
    return PushNotificationService.send_to_user(user_id, notification)


def notify_deadline_reminder(user_id, document_name, days_remaining, document_id=None):
    """Notificar recordatorio de vencimiento"""
    if days_remaining == 0:
        title = '🚨 Vencimiento HOY'
        body = f'{document_name} vence hoy'
    elif days_remaining == 1:
        title = '⚠️ Vence mañana'
        body = f'{document_name} vence mañana'
    else:
        title = '⏰ Recordatorio de vencimiento'
        body = f'{document_name} vence en {days_remaining} días'
    
    notification = {
        'title': title,
        'body': body,
        'icon': '/logo-light.png',
        'badge': '/notification-badge.png',
        'data': {
            'url': f'/mesa-trabajo?doc={document_id}' if document_id else '/mesa-trabajo',
            'type': 'deadline_reminder',
            'document_id': document_id
        }
    }
    return PushNotificationService.send_to_user(user_id, notification)
