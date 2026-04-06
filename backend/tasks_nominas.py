"""
Tareas Celery para procesamiento asíncrono de nóminas
"""
import os
import sys
import logging

# ✅ FIX: Asegurar que el directorio actual está en el path para evitar ModuleNotFoundError
basedir = os.path.abspath(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from celery_worker import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True)
def procesar_nominas_async(self, pdf_path, output_dir, storage_dir, user_id, gestoria_id, periodo_override=None):
    """
    Procesa archivo de nóminas de forma asíncrona con reporte de progreso

    Args:
        pdf_path: Ruta al archivo PDF
        output_dir: Directorio temporal para PDFs divididos
        storage_dir: Directorio de storage final
        user_id: ID del usuario que inició el procesamiento
        gestoria_id: ID de la gestoría (para multi-tenant)
        periodo_override: Periodo manual (opcional)
    """
    def progress_callback(current, total, nif=None, status=None):
        """Callback para reportar progreso vía Celery state y Socket.IO"""
        percentage = (current / total) * 100 if total > 0 else 0
        status_msg = status or f'Procesando página {current} de {total}...'

        logger.debug("Progreso: %d/%d - %s", current, total, status_msg)

        # Actualizar estado de la tarea en Celery
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percentage': round(percentage, 1),
                'empresa_nif': nif,
                'status': status_msg
            }
        )

        # Emitir progreso en tiempo real vía Redis pub/sub (cada 10 páginas o si hay un cambio de etapa)
        if current % 10 == 0 or status is not None or current == total:
            try:
                from redis_notifications import publish_nomina_progress
                publish_nomina_progress(
                    task_id=self.request.id,
                    current=current,
                    total=total,
                    user_id=user_id,
                    nif=nif,
                    status=status_msg
                )
            except Exception as e:
                logger.warning("Error publicando progreso: %s", e)

    try:
        # ✅ Crear contexto de aplicación Flask
        from app import create_app
        app = create_app()

        with app.app_context():
            # ✅ LAZY IMPORT para evitar importación circular
            from procesar_nominas import procesar_nominas, asociar_con_empresas_bd, guardar_en_carpetas_empresas, registrar_en_bd

            # ✅ VERIFICACIÓN DE SEGURIDAD (Especialmente para Windows)
            # Esperar hasta 2 segundos a que el archivo esté disponible en disco
            import time
            max_retries = 10
            found = False
            for i in range(max_retries):
                if os.path.exists(pdf_path):
                    found = True
                    logger.debug("Archivo encontrado en el intento %d", i + 1)
                    break
                logger.debug("Esperando archivo... (intento %d/10)", i + 1)
                time.sleep(0.2)

            if not found:
                raise FileNotFoundError(f"No se encontró el archivo después de esperar: {pdf_path}")

            # ✅ PROCESAMIENTO PARALELO ACTIVADO (CORREGIDO)
            # Usar procesamiento paralelo automático (usa paralelo si PDF >100 páginas)
            from procesar_nominas_parallel import procesar_nominas_auto

            logger.info("Procesando nóminas con detección automática de paralelización...")

            resultados = procesar_nominas_auto(
                pdf_path=pdf_path,
                output_dir=storage_dir,
                periodo_override=periodo_override,
                progress_callback=progress_callback
            )

            # Asociar con empresas BD (con gestoria_id para multi-tenant)
            progress_callback(100, 100, status="Asociando con empresas en base de datos...")
            asociar_con_empresas_bd(resultados, gestoria_id=gestoria_id)

            # Guardar en carpetas de empresas
            progress_callback(100, 100, status="Guardando archivos en carpetas de empresa...")
            guardar_en_carpetas_empresas(resultados, storage_dir)

            # Registrar en BD (con gestoria_id para multi-tenant)
            progress_callback(100, 100, status="Registrando documentos finales...")
            registrar_en_bd(resultados)

            progress_callback(100, 100, status="¡Procesamiento finalizado!")

            # Preparar resultado final
            empresas_asociadas = sum(1 for r in resultados if r.get('empresa_id'))
            total_trabajadores = sum(r.get('num_trabajadores', 0) for r in resultados)
            periodo = resultados[0].get('periodo') if resultados else None

            # Emitir notificación vía Redis pub/sub
            try:
                from redis_notifications import publish_nomina_completed
                publish_nomina_completed(
                    task_id=self.request.id,
                    user_id=user_id,
                    total_empresas=len(resultados),
                    total_trabajadores=total_trabajadores,
                    periodo=periodo,
                    empresas_clasificadas=empresas_asociadas,
                    detalles=resultados
                )
                logger.info("Notificación publicada para user_%s", user_id)
            except Exception as e:
                logger.warning("Error enviando notificación: %s", e)

            # Actualizar historial
            try:
                from models import db
                from datetime import datetime, timezone

                # Importar modelo aquí para evitar circular import
                try:
                    from models import TareaNomina
                except ImportError:
                    # Si no existe el modelo, continuar sin error
                    TareaNomina = None

                if TareaNomina:
                    tarea = TareaNomina.query.filter_by(task_id=self.request.id).first()
                    if tarea:
                        tarea.status = 'SUCCESS'
                        tarea.completed_at = datetime.now(timezone.utc)
                        tarea.total_empresas = len(resultados)
                        tarea.total_trabajadores = total_trabajadores
                        tarea.periodo = periodo
                        db.session.commit()
                        logger.info("Historial actualizado para task %s", self.request.id)
            except Exception as e:
                logger.warning("Error actualizando historial: %s", e)

            return {
                'success': True,
                'async': False,  # Marcar como completado
                'total_empresas': len(resultados),
                'empresas_clasificadas': empresas_asociadas,
                'empresas_no_encontradas': len(resultados) - empresas_asociadas,
                'total_trabajadores': total_trabajadores,
                'periodo': periodo,
                'detalles': resultados  # Agregar detalles completos
            }

    except Exception as e:
        logger.error("Error procesando nóminas: %s", e)
        raise

    finally:
        # Limpiar archivo temporal
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except OSError as e:
                logger.warning("No se pudo eliminar temporal %s: %s", pdf_path, e)
