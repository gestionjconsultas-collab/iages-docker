# backend/celery_tasks_notifications.py
"""
Tareas Celery para notificaciones programadas de documentos
"""
import os
import sys
import logging
from datetime import datetime, timedelta

# Añadir el directorio actual al path
basedir = os.path.abspath(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from celery_worker import celery, get_flask_app
from extensions import db
from models import ScheduledNotification, Documento, User
from services.push_notification_service import notify_deadline_reminder

logger = logging.getLogger(__name__)


@celery.task(
    bind=True,
    name='send_scheduled_notifications',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def send_scheduled_notifications(self):
    """
    Enviar notificaciones programadas pendientes
    Se ejecuta cada 30 minutos via Celery Beat
    """
    app = get_flask_app()
    
    with app.app_context():
        try:
            # Buscar notificaciones pendientes cuya fecha ya pasó
            now = datetime.utcnow()
            
            pending_notifications = ScheduledNotification.query.filter(
                ScheduledNotification.sent == False,
                ScheduledNotification.scheduled_date <= now
            ).all()
            
            logger.info(f"📬 Encontradas {len(pending_notifications)} notificaciones pendientes")
            
            sent_count = 0
            error_count = 0
            
            for notification in pending_notifications:
                try:
                    # Obtener documento
                    documento = Documento.query.get(notification.document_id)
                    if not documento:
                        logger.warning(f"Documento {notification.document_id} no encontrado, marcando notificación como enviada")
                        notification.sent = True
                        notification.sent_at = now
                        continue
                    
                    # Calcular días restantes hasta el vencimiento
                    # Extraer el número de días del notification_type (ej: 'deadline_7days' -> 7)
                    try:
                        days_before = int(notification.notification_type.split('_')[1].replace('days', ''))
                    except:
                        days_before = 0
                    
                    # Enviar notificación
                    sent = notify_deadline_reminder(
                        user_id=notification.user_id,
                        document_name=documento.nombre_archivo,
                        days_remaining=days_before,
                        document_id=documento.id
                    )
                    
                    if sent > 0:
                        # Marcar como enviada
                        notification.sent = True
                        notification.sent_at = now
                        sent_count += 1
                        logger.info(f"✅ Notificación {notification.id} enviada a usuario {notification.user_id}")
                    else:
                        error_count += 1
                        logger.warning(f"⚠️ No se pudo enviar notificación {notification.id}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Error enviando notificación {notification.id}: {str(e)}")
                    continue
            
            # Commit cambios
            db.session.commit()
            
            logger.info(f"📤 Proceso completado: {sent_count} enviadas, {error_count} errores")
            
            return {
                'success': True,
                'sent': sent_count,
                'errors': error_count,
                'total': len(pending_notifications)
            }
            
        except Exception as e:
            logger.error(f"❌ Error en send_scheduled_notifications: {str(e)}")
            db.session.rollback()
            raise


@celery.task(
    bind=True,
    name='schedule_document_deadline_reminders',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 2}
)
def schedule_document_deadline_reminders(self, document_id, deadline_date_iso, reminder_days=None):
    """
    Programar recordatorios automáticos para un documento con fecha de vencimiento
    
    Args:
        document_id: ID del documento
        deadline_date_iso: Fecha de vencimiento en formato ISO
        reminder_days: Lista de días antes del vencimiento para enviar recordatorios (default: [7, 1])
    """
    app = get_flask_app()
    
    with app.app_context():
        try:
            # Obtener documento
            documento = Documento.query.get(document_id)
            if not documento:
                return {'success': False, 'error': 'Documento no encontrado'}
            
            # Parsear fecha de vencimiento
            try:
                deadline_date = datetime.fromisoformat(deadline_date_iso.replace('Z', '+00:00'))
            except:
                return {'success': False, 'error': 'Formato de fecha inválido'}
            
            # Días por defecto
            if reminder_days is None:
                reminder_days = [7, 1]
            
            # Obtener usuarios de la empresa
            from models import Empresa, EmpresaAcceso, GrupoAcceso
            empresa = Empresa.query.get(documento.empresa_id)
            if not empresa:
                return {'success': False, 'error': 'Empresa no encontrada'}
            
            # ✅ CORRECCIÓN: Obtener TODOS los usuarios con acceso a esta empresa
            # Incluye usuarios con empresa_id directo Y usuarios invitados con acceso
            usuarios_con_acceso = set()
            
            # 1. Usuarios con empresa_id directo (empleados de la gestoría)
            usuarios_directos = User.query.filter_by(
                empresa_id=empresa.id,
                activo=True
            ).all()
            for u in usuarios_directos:
                usuarios_con_acceso.add(u)
            
            # 2. Usuarios invitados con acceso directo a esta empresa
            accesos_directos = EmpresaAcceso.query.filter_by(empresa_id=empresa.id).all()
            for acceso in accesos_directos:
                if acceso.user and acceso.user.activo:
                    usuarios_con_acceso.add(acceso.user)
            
            # 3. Usuarios invitados con acceso vía grupo (si la empresa pertenece a un grupo)
            if empresa.grupo_id:
                accesos_grupo = GrupoAcceso.query.filter_by(grupo_id=empresa.grupo_id).all()
                for acceso in accesos_grupo:
                    if acceso.user and acceso.user.activo:
                        usuarios_con_acceso.add(acceso.user)
            
            usuarios_empresa = list(usuarios_con_acceso)
            
            if not usuarios_empresa:
                logger.warning(f"⚠️ No hay usuarios con acceso a la empresa {empresa.id}")
                return {'success': False, 'error': 'No hay usuarios activos con acceso a la empresa'}
            
            logger.info(f"👥 Encontrados {len(usuarios_empresa)} usuarios con acceso a empresa {empresa.nombre}")
            
            # Crear notificaciones programadas
            notifications_created = 0
            for days_before in reminder_days:
                scheduled_date = deadline_date - timedelta(days=days_before)
                
                # Solo crear si la fecha programada es futura
                if scheduled_date > datetime.utcnow():
                    for usuario in usuarios_empresa:
                        notification = ScheduledNotification(
                            document_id=documento.id,
                            user_id=usuario.id,
                            notification_type=f'deadline_{days_before}days',
                            scheduled_date=scheduled_date,
                            sent=False
                        )
                        db.session.add(notification)
                        notifications_created += 1
                        logger.debug(f"📅 Programado recordatorio para {usuario.nombre} ({usuario.id})")
            
            db.session.commit()
            
            logger.info(f"✅ Programados {notifications_created} recordatorios para documento {document_id}")
            
            return {
                'success': True,
                'notifications_created': notifications_created
            }
            
        except Exception as e:
            logger.error(f"❌ Error programando recordatorios: {str(e)}")
            db.session.rollback()
            raise
