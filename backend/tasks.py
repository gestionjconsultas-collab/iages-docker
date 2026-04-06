"""
Tareas de Celery para IAGES
Tareas programadas y en background
"""
from celery_config import celery
from models import db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery.task(name='tasks.verificar_limites_gestorias')
def verificar_limites_gestorias():
    """
    Verifica los límites de todas las gestorías y genera alertas
    Se ejecuta cada hora
    """
    try:
        from services.alertas_automaticas import verificar_limites_y_generar_alertas
        from app import app

        with app.app_context():
            alertas_generadas = verificar_limites_y_generar_alertas()
            logger.info("[Celery] Verificación completada. %d alertas generadas.", alertas_generadas)
            return {
                'success': True,
                'alertas_generadas': alertas_generadas,
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("[Celery] Error en verificar_limites_gestorias: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery.task(name='tasks.limpiar_alertas_antiguas')
def limpiar_alertas_antiguas(dias=30):
    """
    Limpia alertas leídas más antiguas que X días
    Se ejecuta diariamente a las 3 AM
    """
    try:
        from services.alertas_automaticas import limpiar_alertas_antiguas as limpiar
        from app import app

        with app.app_context():
            alertas_eliminadas = limpiar(dias)
            logger.info("[Celery] %d alertas antiguas eliminadas.", alertas_eliminadas)
            return {
                'success': True,
                'alertas_eliminadas': alertas_eliminadas,
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("[Celery] Error en limpiar_alertas_antiguas: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery.task(name='tasks.generar_reporte_uso_mensual')
def generar_reporte_uso_mensual():
    """
    Genera reporte de uso mensual para todas las gestorías
    Se ejecuta el primer día de cada mes a las 6 AM
    """
    try:
        from models import Gestoria, UsoGestoria, GestoriaPlan
        from app import app

        with app.app_context():
            # Obtener mes anterior
            hoy = datetime.utcnow()
            primer_dia_mes_actual = hoy.replace(day=1)
            ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
            periodo = ultimo_dia_mes_anterior.strftime('%Y-%m')

            # Obtener todas las gestorías
            gestorias = Gestoria.query.filter_by(activa=True).all()

            reportes = []
            for g in gestorias:
                uso = UsoGestoria.query.filter_by(
                    gestoria_id=g.id,
                    periodo=periodo
                ).first()

                plan = GestoriaPlan.query.filter_by(gestoria_id=g.id).first()

                if uso:
                    reportes.append({
                        'gestoria_id': g.id,
                        'gestoria_nombre': g.nombre,
                        'plan': plan.plan.nombre if plan else None,
                        'periodo': periodo,
                        'usuarios_activos': uso.usuarios_activos,
                        'empresas_count': uso.empresas_count,
                        'documentos_procesados': uso.documentos_procesados,
                        'tokens_ia_usados': uso.tokens_ia_usados,
                        'almacenamiento_usado_gb': float(uso.almacenamiento_usado_gb)
                    })

            logger.info("[Celery] Reporte mensual generado para %d gestorías.", len(reportes))

            # TODO: Enviar reporte por email a super-admins

            return {
                'success': True,
                'periodo': periodo,
                'gestorias_procesadas': len(reportes),
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("[Celery] Error en generar_reporte_uso_mensual: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery.task(name='tasks.actualizar_metricas_uso')
def actualizar_metricas_uso():
    """
    Actualiza las métricas de uso actuales para todas las gestorías
    Se ejecuta cada 15 minutos
    """
    try:
        from models import Gestoria, User, Empresa, Documento, UsoGestoria
        from app import app
        from sqlalchemy import func

        with app.app_context():
            periodo_actual = datetime.utcnow().strftime('%Y-%m')
            gestorias = Gestoria.query.filter_by(activa=True).all()

            actualizadas = 0
            for g in gestorias:
                # Contar recursos actuales
                usuarios_count = User.query.filter_by(gestoria_id=g.id).count()
                empresas_count = Empresa.query.filter_by(gestoria_id=g.id).count()

                # Documentos del mes actual
                inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
                documentos_mes = Documento.query.filter(
                    Documento.gestoria_id == g.id,
                    Documento.fecha_creacion >= inicio_mes
                ).count()

                # Obtener o crear registro de uso
                uso = UsoGestoria.query.filter_by(
                    gestoria_id=g.id,
                    periodo=periodo_actual
                ).first()

                if not uso:
                    uso = UsoGestoria(
                        gestoria_id=g.id,
                        periodo=periodo_actual
                    )
                    db.session.add(uso)

                # Actualizar valores
                uso.usuarios_activos = usuarios_count
                uso.empresas_count = empresas_count
                uso.documentos_procesados = documentos_mes
                uso.fecha_actualizacion = datetime.utcnow()

                actualizadas += 1

            db.session.commit()
            logger.info("[Celery] Métricas actualizadas para %d gestorías.", actualizadas)

            return {
                'success': True,
                'gestorias_actualizadas': actualizadas,
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        db.session.rollback()
        logger.error("[Celery] Error en actualizar_metricas_uso: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


# Tarea manual para testing
@celery.task(name='tasks.test_task')
def test_task():
    """Tarea de prueba para verificar que Celery funciona"""
    logger.info("[Celery] Test task ejecutada correctamente!")
    return {
        'success': True,
        'message': 'Celery está funcionando correctamente',
        'timestamp': datetime.utcnow().isoformat()
    }


@celery.task(name='tasks.activate_scheduled_maintenance')
def activate_scheduled_maintenance(user_id, scheduled_token=None):
    """
    Activa el modo de mantenimiento de forma programada
    """
    try:
        from models import SystemConfig
        from app import app

        with app.app_context():
            # Forzar lectura fresca desde BD (evita caché de sesión SQLAlchemy)
            from extensions import db
            db.session.expire_all()

            # Verificar si la programación sigue siendo válida
            current_token = SystemConfig.get_value('maintenance_scheduled_token')

            # Cancelar si el token fue limpiado (admin desactivó) o no coincide
            token_limpio   = not current_token  # '' o None → admin canceló
            token_distinto = bool(scheduled_token and current_token != scheduled_token)

            if token_limpio or token_distinto:
                logger.warning(
                    "[Celery] Cancelando activación: token_limpio=%s token_distinto=%s "
                    "(scheduled=%r != current=%r)",
                    token_limpio, token_distinto, scheduled_token, current_token
                )
                return {'success': False, 'reason': 'cancelled'}

            # Activar mantenimiento
            SystemConfig.set_value('maintenance_mode', 'true', user_id)
            SystemConfig.set_value('maintenance_scheduled_token', '', user_id)

            # Emitir evento WebSocket
            try:
                socketio = app.config.get('SOCKETIO')
                if socketio:
                    socketio.emit('maintenance_activated', {
                        'message': SystemConfig.get_value('maintenance_message', 'Sistema en mantenimiento')
                    })
            except Exception as e:
                logger.warning("[Celery] Error emitiendo WebSocket: %s", e)

            logger.info("[Celery] Modo de mantenimiento activado automáticamente")

            return {
                'success': True,
                'message': 'Mantenimiento activado',
                'timestamp': datetime.utcnow().isoformat()
            }
    except Exception as e:
        logger.error("[Celery] Error activando mantenimiento: %s", e, exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
