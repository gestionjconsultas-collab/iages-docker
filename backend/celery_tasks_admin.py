# backend/celery_tasks_admin.py
"""
Tareas Celery para operaciones administrativas masivas (reprocesamiento, etc.)
"""
import os
import sys
import logging
import shutil
from datetime import datetime

# Añadir el directorio actual al path
basedir = os.path.abspath(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from celery_worker import celery, get_flask_app
from extensions import db
from models import Documento, Empresa, AuditoriaLog

logger = logging.getLogger(__name__)

@celery.task(
    bind=True,
    name='reprocesar_categoria_global_task',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 1}
)
def reprocesar_categoria_global_task(self, gestoria_id, categoria, user_id):
    """
    Tarea masiva para reprocesar todos los documentos de una categoría 
    en TODAS las empresas de una gestoría.
    """
    app = get_flask_app()
    
    with app.app_context():
        try:
            logger.info(f"🚀 Iniciando reprocesamiento GLOBAL: gestoria={gestoria_id}, categoria={categoria}")
            
            # 1. Obtener todas las empresas de la gestoría
            empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
            empresa_ids = [e.id for e in empresas]
            
            if not empresa_ids:
                logger.warning(f"⚠️ No hay empresas para la gestoria {gestoria_id}")
                return {'success': True, 'procesados': 0, 'errores': 0, 'message': 'No hay empresas'}

            # 2. Buscar todos los documentos de esa categoría en esas empresas
            docs = Documento.query.filter(
                Documento.empresa_id.in_(empresa_ids),
                Documento.categoria == categoria,
                Documento.gestoria_id == gestoria_id
            ).all()
            
            total_docs = len(docs)
            logger.info(f"📊 Encontrados {total_docs} documentos para reprocesar")
            
            if not docs:
                return {'success': True, 'procesados': 0, 'errores': 0, 'message': 'No hay documentos'}

            # 3. Importar servicios on-demand
            from services.procesar_impuestos import procesar_impuestos
            from services.procesar_altas import procesar_altas
            from services.procesar_finiquitos import procesar_finiquitos
            from services.procesar_contratos import procesar_contratos
            from services.procesar_modelo_190 import procesar_certificados_190
            from services.procesar_modelo_180 import procesar_certificados_180
            
            # Directorio temporal
            temp_output = os.path.join(app.config.get('UPLOAD_FOLDER', 'temp'), 'reprocess_global', str(datetime.now().timestamp()))
            os.makedirs(temp_output, exist_ok=True)
            
            procesados = 0
            errores = 0
            
            try:
                for idx, doc in enumerate(docs):
                    # Actualizar progreso en Celery si es necesario (opcional)
                    self.update_state(state='PROGRESS', meta={'current': idx, 'total': total_docs, 'categoria': categoria})
                    
                    if not doc.ruta_archivo or not os.path.exists(doc.ruta_archivo):
                        logger.warning(f"⚠️ Archivo no encontrado para doc {doc.id}: {doc.ruta_archivo}")
                        continue
                        
                    res_ocr = []
                    try:
                        if categoria == 'Impuestos':
                            res_ocr = procesar_impuestos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        elif categoria in ['Altas de Trabajadores', 'Bajas de Trabajadores']:
                            res_ocr = procesar_altas(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        elif categoria == 'Finiquitos':
                            res_ocr = procesar_finiquitos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        elif categoria == 'Contratos':
                            res_ocr = procesar_contratos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        elif categoria == 'Certificados de Retenciones 190':
                            res_ocr = procesar_certificados_190(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        elif categoria == 'Certificados de Retenciones 180':
                            res_ocr = procesar_certificados_180(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=app.app_context())
                        
                        if res_ocr:
                            item = res_ocr[0]
                            doc.datos_extraidos = item
                            doc.procesado = True
                            doc.fecha_procesado = datetime.utcnow()
                            doc.periodo = item.get('ejercicio') or item.get('periodo')
                            procesados += 1
                            
                            # Commit parcial cada 10 docs para no perder todo si falla
                            if procesados % 10 == 0:
                                db.session.commit()
                                
                    except Exception as e:
                        logger.error(f"❌ Error reprocesando doc {doc.id}: {e}")
                        errores += 1
                        
                db.session.commit()
                
                # 4. Registrar en auditoría final
                log = AuditoriaLog(
                    user_id=user_id,
                    accion="REPROCESAR_CATEGORIA_GLOBAL",
                    entidad_tipo="Documento",
                    descripcion=f"Reprocesamiento GLOBAL de {categoria} para TODAS las empresas",
                    detalles={'categoria': categoria, 'procesados': procesados, 'errores': errores, 'total': total_docs},
                    gestoria_id=gestoria_id
                )
                db.session.add(log)
                db.session.commit()
                
            finally:
                try: shutil.rmtree(temp_output)
                except: pass
                
            logger.info(f"✅ Reprocesamiento GLOBAL completado: {procesados} exitosos, {errores} fallidos")
            
            return {
                'success': True,
                'procesados': procesados,
                'errores': errores,
                'total': total_docs
            }
            
        except Exception as e:
            logger.error(f"❌ Error crítico en reprocesar_categoria_global_task: {str(e)}")
            db.session.rollback()
            raise
