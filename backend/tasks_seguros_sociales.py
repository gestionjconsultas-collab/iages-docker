"""
Tareas Celery para procesamiento asíncrono de seguros sociales
"""
from celery_worker import celery
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@celery.task(bind=True)
def procesar_seguros_async(self, rlc_path, rnt_path, user_id, gestoria_id, periodo_override=None):
    """
    Procesa archivos RLC/RNT de forma asíncrona
    """
    try:
        # ✅ LAZY IMPORT para evitar importación circular
        from procesar_seguros_sociales import procesar_seguros_sociales

        # ✅ VERIFICACIÓN DE SEGURIDAD (Especialmente para Windows)
        import time
        for path in [rlc_path, rnt_path]:
            if not path: continue
            max_retries = 10
            found = False
            for i in range(max_retries):
                if os.path.exists(path):
                    found = True
                    break
                logger.debug("Esperando archivo %s... (%d/10)", os.path.basename(path), i + 1)
                time.sleep(0.2)
            if not found:
                raise FileNotFoundError(f"No se encontró el archivo: {path}")

        # Callback para reportar progreso vía Celery state y Socket.IO
        def progress_callback(current, total, tipo_doc='', status=None):
            """Callback para reportar progreso durante procesamiento"""
            percentage = (current / total) * 100 if total > 0 else 0
            status_msg = status or f'Procesando {tipo_doc}: {current}/{total} documentos...'

            logger.debug("Progreso: %d/%d (%s) - %s", current, total, tipo_doc, status_msg)

            # Actualizar estado de la tarea en Celery
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'percentage': round(percentage, 1),
                    'tipo_documento': tipo_doc,
                    'status': status_msg
                }
            )

            # Emitir progreso en tiempo real vía Redis pub/sub (cada 10 páginas o cambio de estado)
            if current % 10 == 0 or status is not None:
                try:
                    from redis_notifications import publish_seguro_progress
                    publish_seguro_progress(
                        task_id=self.request.id,
                        current=current,
                        total=total,
                        user_id=user_id,
                        empresa=tipo_doc,
                        status=status_msg
                    )
                except Exception as e:
                    logger.warning("Error publicando progreso: %s", e)

        # Procesar seguros sociales con callback de progreso y gestoria_id
        resultados = procesar_seguros_sociales(
            rlc_path,
            rnt_path,
            gestoria_id=gestoria_id,
            periodo_override=periodo_override,
            progress_callback=progress_callback
        )

        # Preparar resultado
        total_empresas = len(resultados) if resultados else 0
        total_trabajadores = sum(r.get('num_trabajadores', 0) for r in resultados) if resultados else 0
        periodo = resultados[0].get('periodo') if resultados else None

        # Normalizar detalles para el frontend ANTES de emitir notificación
        # (Socket.IO envía estos datos, la tabla los necesita en formato {nombre_trabajador, empresa, estado, mensaje})
        detalles_normalizados = []
        for r in resultados:
            nombre_archivo = os.path.basename(r.get('pdf_path_final') or r.get('pdf_path') or '')
            tipo = r.get('tipo', '')
            razon = r.get('razon_social') or r.get('nif') or r.get('ccc') or 'Desconocido'
            empresa_nombre = r.get('empresa_nombre') or razon
            es_inbox = r.get('es_inbox', False)
            estado = 'advertencia' if es_inbox else 'exito'
            mensaje = r.get('metodo_deteccion') or ('Sin clasificar - enviado a Inbox' if es_inbox else 'Clasificado correctamente')
            detalles_normalizados.append({
                'estado': estado,
                'nombre_trabajador': f"{tipo}: {nombre_archivo}" if nombre_archivo else f"{tipo}: {razon}",
                'empresa': empresa_nombre,
                'mensaje': mensaje
            })

        # Emitir notificación vía Redis pub/sub (con detalles ya normalizados)
        try:
            rlc_procesados = sum(1 for r in resultados if r.get('tipo') == 'RLC')
            rnt_procesados = sum(1 for r in resultados if r.get('tipo') == 'RNT')
            # Contar empresas ÚNICAS (no documentos)
            empresas_asociadas = len(set(r.get('empresa_id') for r in resultados if r.get('empresa_id')))

            from redis_notifications import publish_seguro_completed
            publish_seguro_completed(
                task_id=self.request.id,
                user_id=user_id,
                total_empresas=total_empresas,
                total_trabajadores=total_trabajadores,
                periodo=periodo,
                rlc_procesados=rlc_procesados,
                rnt_procesados=rnt_procesados,
                empresas_asociadas=empresas_asociadas,
                detalles=detalles_normalizados  # ✅ normalizados, no raw
            )
            logger.info("Notificación publicada para user_%s", user_id)
        except Exception as e:
            logger.warning("Error enviando notificación: %s", e)

        # Actualizar historial
        try:
            from app import create_app
            from models import db, TareaSeguros
            app = create_app()
            with app.app_context():
                tarea = TareaSeguros.query.filter_by(task_id=self.request.id).first()
                if tarea:
                    tarea.status = 'SUCCESS'
                    tarea.completed_at = datetime.now(timezone.utc)
                    tarea.total_empresas = total_empresas
                    tarea.total_trabajadores = total_trabajadores
                    tarea.periodo = periodo
                    db.session.commit()
                    logger.info("Historial actualizado para task %s", self.request.id)
        except Exception as e:
            logger.warning("Error actualizando historial: %s", e)

        return {
            'success': True,
            'total_empresas': total_empresas,
            'total_trabajadores': total_trabajadores,
            'periodo': periodo,
            'detalles': detalles_normalizados
        }

    except Exception as e:
        logger.error("Error procesando seguros: %s", e)

        # Marcar como fallida en historial
        try:
            from app import create_app
            from models import db, TareaSeguros
            app = create_app()
            with app.app_context():
                tarea = TareaSeguros.query.filter_by(task_id=self.request.id).first()
                if tarea:
                    tarea.status = 'FAILURE'
                    tarea.error_message = str(e)
                    tarea.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
        except Exception as inner_e:
            logger.warning("No se pudo actualizar historial de tarea: %s", inner_e)

        raise

    finally:
        # Limpiar archivos temporales
        try:
            if rlc_path and os.path.exists(rlc_path):
                os.remove(rlc_path)
            if rnt_path and os.path.exists(rnt_path):
                os.remove(rnt_path)
        except OSError as e:
            logger.warning("No se pudieron eliminar temporales: %s", e)
