# backend/celery_worker.py
import os
import sys
import re
import time
import logging
import shutil

# ✅ FIX: Añadir el directorio actual al path para evitar ModuleNotFoundError
basedir = os.path.abspath(os.path.dirname(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from celery import Celery
from dotenv import load_dotenv
from extensions import db
from datetime import datetime, timezone, timedelta, date
from models import Documento, FiniquitoLinea, RecordatorioPago
from models_saltra import NotificacionSaltra, SaltraSyncLog  # ✅ Import al nivel superior
from socketio_events import notify_documento_procesado
from services.saltra_service import SaltraService
from tenant_utils import get_current_gestoria_id

# ============================================
# CONFIGURACIÓN DE LOGGING
# ============================================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Cargar variables
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Configuración Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery = Celery('gestion_tasks', broker=redis_url, backend=redis_url)

celery.conf.update(
    result_expires=3600,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Madrid',
    enable_utc=True,
    worker_concurrency=4,  # ✅ OPTIMIZADO: 2 → 4 (permite 4 tareas simultáneas)
    broker_connection_retry_on_startup=True,
    task_acks_late=True,  # ✅ NUEVO: Fair scheduling - no tomar tareas hasta terminar actual
    worker_prefetch_multiplier=1,  # ✅ NUEVO: Tomar solo 1 tarea a la vez
)

# ============================================
# COLAS DEDICADAS Y LÍMITES DE MEMORIA
# ============================================

# Rutas de tareas a colas específicas
celery.conf.task_routes = {
    'tasks_nominas.procesar_nominas_async': {'queue': 'nominas'},
    'tasks_seguros_sociales.procesar_seguros_async': {'queue': 'seguros'},
}

# ✅ OPTIMIZADO: Límites de concurrencia y timeouts por tarea
celery.conf.task_annotations = {
    'tasks_nominas.procesar_nominas_async': {
        'rate_limit': '10/m',     # ✅ OPTIMIZADO: 2/m → 10/m (más permisivo)
        'time_limit': 1800,       # Timeout 30 minutos (para PDFs de 2000+ páginas)
        'soft_time_limit': 1680,  # Warning a los 28 minutos
    },
    'tasks_seguros_sociales.procesar_seguros_async': {
        'rate_limit': '5/m',      # ✅ OPTIMIZADO: 1/m → 5/m (más permisivo)
        'time_limit': 2700,       # Timeout 45 minutos (para PDFs muy grandes)
        'soft_time_limit': 2520,  # Warning a los 42 minutos
    },
}

# ============================================
# TAREAS PROGRAMADAS (CELERY BEAT)
# ============================================
from celery.schedules import crontab

celery.conf.beat_schedule = {
    # Sincronización SALTRA cada 15 minutos
    'sincronizar-saltra-15m': {
        'task': 'sincronizar_saltra',
        'schedule': 900.0,
    },
    
    # ==========================================
    # TAREAS DE MANTENIMIENTO
    # ==========================================
    
    # Limpieza de archivos temporales (cada hora)
    'cleanup-temp-files-hourly': {
        'task': 'cleanup_temp_files',
        'schedule': 3600.0,  # Cada hora
    },
    
    # ==========================================
    # TAREAS DE FACTURACIÓN
    # ==========================================
    
    # Generar facturas mensuales (día 1 a las 00:00)
    'generar-facturas-mensuales': {
        'task': 'generar_facturas_mensuales',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),
    },
    
    # Calcular uso mensual (diario a las 2 AM)
    'calcular-uso-mensual': {
        'task': 'calcular_uso_mensual_todas',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Verificar facturas vencidas (diario a las 3 AM)
    'verificar-facturas-vencidas': {
        'task': 'verificar_facturas_vencidas',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Recordatorios de facturas (diario a las 10 AM)
    'recordatorios-facturas': {
        'task': 'recordatorio_facturas_proximas_vencer',
        'schedule': crontab(hour=10, minute=0),
    },
    
    # ==========================================
    # CALENDARIO TRIBUTARIO AEAT
    # ==========================================
    
    # Sincronizar calendario AEAT (primer día de cada mes a la 1 AM)
    'sincronizar-calendario-aeat': {
        'task': 'sincronizar_calendario_aeat',
        'schedule': crontab(day_of_month=1, hour=1, minute=0),
    },
    
    # ==========================================
    # NOTIFICACIONES PROGRAMADAS DE DOCUMENTOS
    # ==========================================
    
    # Enviar notificaciones programadas (cada 30 minutos)
    'send-scheduled-notifications': {
        'task': 'send_scheduled_notifications',
        'schedule': crontab(minute='*/30'),  # Cada 30 minutos
    },
}


def get_flask_app():
    from flask import Flask
    from extensions import db
    from config import config
    app = Flask(__name__)
    env = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[env])
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    db.init_app(app)
    return app

# ============================================
# IMPORTAR MÓDULOS DE TAREAS PARA REGISTRO
# ============================================
# CRÍTICO: Estos imports deben estar DESPUÉS de la definición de celery
# para que las tareas se registren correctamente en el worker

try:
    # Tareas de notificaciones programadas
    import celery_tasks_notifications
    logger.info("✅ Módulo celery_tasks_notifications importado correctamente")
except Exception as e:
    logger.error(f"❌ Error importando celery_tasks_notifications: {e}")

try:
    # Tareas de facturación
    import celery_tasks_billing
    logger.info("✅ Módulo celery_tasks_billing importado correctamente")
except Exception as e:
    logger.error(f"❌ Error importando celery_tasks_billing: {e}")

try:
    # Tareas administrativas masivas
    import celery_tasks_admin
    logger.info("✅ Módulo celery_tasks_admin importado correctamente")
except Exception as e:
    logger.error(f"❌ Error importando celery_tasks_admin: {e}")

# --- TAREAS ---

@celery.task(
    bind=True,
    name='procesar_documento_async',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3},
    acks_late=True
)
def procesar_documento_async(self, doc_id, tipo_documento):
    from extensions import db
    from models import Documento
    from services.notificacion_extractor import NotificacionExtractor
    from utils import clean_and_convert_to_float
    from utils.storage_utils import resolve_document_path
    from datetime import datetime, timezone
    
    app = get_flask_app()
    with app.app_context():
        # Nota: Si falla, dejamos que Celery capture la excepción automáticamente.
        # NO USAR self.update_state(state='FAILURE') aquí manualmente.
        
        self.update_state(state='PROCESSING', meta={'progress': 10, 'status': 'Iniciando...'})
        
        doc = db.session.get(Documento, doc_id)
        if not doc: return {'status': NotificationTypes.ERROR, 'message': 'No encontrado'}
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'status': 'Analizando...'})
        
        extractor = NotificacionExtractor()
        logger.info(f"--- INICIO TAREA CELERY DOC {doc_id} ---")
        
        # Lógica para forzar perfil específico (Manual)
        if tipo_documento and tipo_documento.startswith('PROFILE:'):
            profile_name = tipo_documento.replace('PROFILE:', '')
            # Si es un perfil auto-creado, usar el extractor por proximidad
            if profile_name.startswith('auto_'):
                try:
                    from services.proximity_extractor import extraer_por_proximidad
                    # Derivar tipo_clave: auto_EMISOR_TIPO → TIPO
                    # Ej: auto_ajbcn_provisio_constrenyiment → provisio_constrenyiment
                    parts = profile_name.replace('auto_', '').split('_', 1)
                    tipo_clave = parts[1] if len(parts) > 1 else '_generico'
                    
                    # Usar el texto OCR ya guardado en BD (evita re-extraer el PDF)
                    texto_para_extraer = doc.texto_ocr or ''
                    if not texto_para_extraer:
                        # Si no hay OCR aún, extraer ahora
                        extractor_ocr = NotificacionExtractor()
                        pdf_path = resolve_document_path(doc)
                        texto_para_extraer = extractor_ocr.extraer_texto(pdf_path)
                    
                    # Obtener configuración del template para campos personalizados, activos y MAPEO DE LÍNEAS
                    etiquetas_extra = None
                    campos_activos = None
                    mapeo_lineas = None
                    try:
                        from models import ExtractionTemplate, ConfiguracionPerfil
                        # 1. Intentar obtener el mapeo de la configuración de la gestoría (prioridad)
                        config_perfil = ConfiguracionPerfil.query.filter_by(
                            gestoria_id=doc.gestoria_id,
                            perfil_clave=profile_name
                        ).first()
                        if config_perfil:
                            mapeo_lineas = config_perfil.mapeo_lineas
                            custom_bt = config_perfil.boundary_tags
                            logger.info(f"  Mapeo de líneas cargado para {profile_name}: {mapeo_lineas}")

                        # 2. Obtener etiquetas del template
                        tpl = ExtractionTemplate.query.get(profile_name)
                        if tpl and tpl.profile_json:
                            pj = tpl.profile_json
                            etiquetas_extra = pj.get('campos_personalizados') or {}
                            campos_activos = pj.get('campos_activos')
                            # Si hay boundary_tags en el template, los mezclamos
                            bt_tpl = pj.get('boundary_tags', [])
                            if custom_bt or bt_tpl:
                                # Prioridad a custom_bt (gestoría) sobre bt_tpl (template base)
                                all_bt = (custom_bt or []) + [t for t in (bt_tpl or []) if t not in (custom_bt or [])]
                                etiquetas_extra['boundary_tags'] = all_bt
                            
                            # Fallback si no hay config de gestoria pero el template tiene mapeo
                            if not mapeo_lineas:
                                mapeo_lineas = pj.get('mapeo_lineas')
                    except Exception as e_tpl_read:
                        logger.warning(f"Error leyendo configuración de template {profile_name}: {e_tpl_read}")

                    # Extraer con etiquetas base + personalizadas + mapeo de líneas
                    datos_proximidad = extraer_por_proximidad(
                        texto_para_extraer, 
                        tipo_clave, 
                        etiquetas_extra,
                        mapeo_lineas=mapeo_lineas
                    )
                    
                    # Filtrar por campos_activos si el usuario los ha configurado
                    if campos_activos:
                        datos_proximidad = {k: v for k, v in datos_proximidad.items() if k in campos_activos}
                        logger.info(f"  Filtrado a campos_activos: {list(datos_proximidad.keys())}")


                    # Combinar con metadatos
                    datos = {
                        'tipo_documento': profile_name.replace('auto_', '').replace('_', ' ').title(),
                        '_metadata': {
                            'tipo_detectado': profile_name,
                            'metodo': 'PROXIMITY_EXTRACTOR',
                            'campos_encontrados': list(datos_proximidad.keys()),
                        },
                        **datos_proximidad
                    }
                    logger.info(f"✅ ProximityExtractor [{tipo_clave}]: {list(datos_proximidad.keys())}")

                except Exception as e_prox:
                    logger.error(f"Error en ProximityExtractor para {profile_name}: {e_prox}")
                    pdf_path = resolve_document_path(doc)
                    datos = extractor.extract_with_specific_profile(pdf_path, profile_name)

            else:
                pdf_path = resolve_document_path(doc)
                datos = extractor.extract_with_specific_profile(pdf_path, profile_name)

            # MULTITENANT: Aplicar configuración de categoría/departamento
            try:
                from models import ConfiguracionPerfil
                config = ConfiguracionPerfil.query.filter_by(
                    gestoria_id=doc.gestoria_id,
                    perfil_clave=profile_name
                ).first()
                if config:
                    if config.categoria:
                        doc.categoria = config.categoria
                        if doc.categoria == 'Notificaciones' and config.prioridad_default:
                            doc.prioridad = config.prioridad_default
                        logger.info(f"Aplicando categoría {config.categoria} a doc {doc_id}")
                    if config.departamento:
                        datos['departamento_asignado'] = config.departamento

                    # ⭐ NUEVO: Guardar flag de notificación para procesar después del commit
                    doc._notificar_cliente_perfil = getattr(config, 'notificar_cliente', False)

                # ✅ FIX: Fallback para perfiles estáticos almacenados en TipoDocumentoConfig
                # batch_process lee de TipoDocumentoConfig para perfiles estáticos (TIPOS_PREDEFINIDOS),
                # pero Celery solo consultaba ConfiguracionPerfil → _notificar_cliente_perfil quedaba False
                if not config:
                    try:
                        from models import TipoDocumentoConfig
                        config_static = TipoDocumentoConfig.query.filter_by(
                            gestoria_id=doc.gestoria_id,
                            codigo=profile_name,
                            activo=True
                        ).first()
                        if config_static:
                            if config_static.categoria_default and not doc.categoria:
                                doc.categoria = config_static.categoria_default
                                if doc.categoria == 'Notificaciones' and getattr(config_static, 'prioridad_default', None):
                                    doc.prioridad = config_static.prioridad_default
                                logger.info(f"Aplicando categoría estática {config_static.categoria_default} a doc {doc_id}")
                            if getattr(config_static, 'departamento_default', None):
                                datos['departamento_asignado'] = config_static.departamento_default
                            doc._notificar_cliente_perfil = getattr(config_static, 'notificar_cliente', False)
                            logger.info(f"Config estática aplicada para perfil '{profile_name}', notificar_cliente={doc._notificar_cliente_perfil}")
                    except Exception as e_static:
                        logger.error(f"Error aplicando config estática para perfil '{profile_name}': {e_static}")
            except Exception as e:
                logger.error(f"Error aplicando configuración perfil: {e}")

        elif tipo_documento == 'aplazamiento':
            from services.impuesto_extractor import ImpuestoExtractor
            pdf_path = resolve_document_path(doc)
            datos = ImpuestoExtractor().extract_tax_data(pdf_path)
            # El usuario marcó explícitamente este doc como aplazamiento → forzar flag
            datos['is_aplazamiento'] = True

        else:
            plantillas = extractor.get_todas_plantillas()
            plantilla = plantillas.get(tipo_documento, plantillas.get('notificacion_generica'))
            pdf_path = resolve_document_path(doc)
            datos = extractor.extract_with_template(pdf_path, plantilla)
        
        if NotificationTypes.ERROR in datos:
            logger.error(f"Error detectado en extracción para doc {doc_id}: {datos[NotificationTypes.ERROR]}")
            # No lanzamos excepción para no dejar el documento en estado 'Analizando...' eternamente.
            # Los errores se guardarán en datos_extraidos y el doc se marcará como procesado.
        
        self.update_state(state='PROCESSING', meta={'progress': 90, 'status': 'Guardando...'})
        
        # Extraer texto OCR antes de guardar en datos_extraidos (no queremos el texto crudo en el JSON)
        texto_ocr = datos.pop('_texto_ocr', None)

        # ✅ MERGE: preservar campos internos del flujo de trabajo que ya estaban en datos_extraidos
        # (ej: email_preparado guardado previamente por routes_mesa_trabajo)
        datos_previos = doc.datos_extraidos or {}
        CAMPOS_A_PRESERVAR = ('email_preparado',)
        for campo in CAMPOS_A_PRESERVAR:
            if campo in datos_previos and campo not in datos:
                datos[campo] = datos_previos[campo]

        doc.datos_extraidos = datos
        doc.procesado = True
        doc.fecha_procesado = datetime.now(timezone.utc)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(doc, 'datos_extraidos')
        
        # Guardar texto OCR para búsqueda full-text
        if texto_ocr:
            doc.texto_ocr = texto_ocr

        
        imp = datos.get('importe_total_deuda') or datos.get('importe_embargado') or datos.get('importe_pagar')
        doc.importe = clean_and_convert_to_float(imp)
        
        db.session.commit()
        
        # ── AUTO-CREACIÓN DE PERFIL ─────────────────────────────────────────
        # Crear automáticamente un ConfiguracionPerfil para que este tipo de
        # documento aparezca en la lista listo para que el usuario configure
        # el destino. Si ya existe, no hace nada.
        try:
            if doc.texto_ocr:
                from services.auto_profile_detector import auto_crear_perfil
                auto_crear_perfil(doc, doc.gestoria_id, user_id=None)
        except Exception as e_perfil:
            logger.warning(f"Auto-perfil no creado para doc {doc_id}: {e_perfil}")
        # ────────────────────────────────────────────────────────────────────
        
        # Notificar en tiempo real que el documento fue procesado
        try:
            from app import app as flask_app
            with flask_app.app_context():
                socketio = flask_app.config.get('SOCKETIO')
                if socketio and doc:
                    # 1. Notificación estándar de procesamiento
                    notify_documento_procesado(
                        socketio, 
                        doc.id, 
                        None,
                        doc.nombre_archivo,
                        doc.categoria
                    )
                    
                    # 2. Si el perfil dice que notifiquemos al cliente, crear Notificacion y emitir
                    if getattr(doc, '_notificar_cliente_perfil', False):
                        from models import Notificacion
                        notif = Notificacion(
                            gestoria_id=doc.gestoria_id,
                            empresa_id=doc.empresa_id,
                            titulo="Nuevo Documento Procesado",
                            mensaje=f"Se ha clasificado un nuevo documento: {doc.nombre_archivo}",
                            tipo="info",
                            link=f"/documentos/{doc.id}"
                        )
                        db.session.add(notif)
                        db.session.commit()
                        
                        payload = notif.to_dict()
                        
                        # Notificar a todos los interesados (Staff e Invitados) de forma centralizada
                        from socketio_events import notify_guests_of_document
                        notify_guests_of_document(socketio, doc, payload)
        except Exception as e:
            logger.warning(f"Error enviando notificación WebSocket: {e}")
        
        return {'status': NotificationTypes.SUCCESS, 'doc_id': doc_id}
        
@celery.task(
    bind=True,
    name='sincronizar_saltra',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3},
    acks_late=True
)
def sincronizar_saltra(self, tipo='done', max_pages=10, gestoria_id=None):
    """
    Sincroniza notificaciones de Saltra con la BD local - MULTI-TENANT
    - tipo: 'done' (realizadas) o 'received' (recibidas)
    - max_pages: Número máximo de páginas a obtener
    - gestoria_id: ID de la gestoría (si no se proporciona, usa la del usuario actual)
    """
    # models_saltra ya importado al nivel superior
    from models import AliasNIF, Empresa, Gestoria
    import re
    app = get_flask_app()
    
    with app.app_context():
        # Obtener credenciales SALTRA de la gestoría
        if not gestoria_id:
            gestoria_id = get_current_gestoria_id()
        
        if not gestoria_id:
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No se pudo determinar la gestoría'}
        
        # Obtener credenciales de la gestoría
        gestoria = Gestoria.query.get(gestoria_id)
        if not gestoria or not gestoria.configuracion:
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Gestoría no encontrada o sin configuración'}
        
        # Verificar habilitado antes de desencriptar
        saltra_raw = (gestoria.configuracion or {}).get('saltra', {})
        if not saltra_raw.get('enabled', False):
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'SALTRA deshabilitado para esta gestoría'}

        # Usar helper que desencripta automáticamente (FIX: credenciales cifradas con Fernet)
        saltra_config = gestoria.get_saltra_config_decrypted()
        if not saltra_config.get('email') or not saltra_config.get('password') or not saltra_config.get('cert_secret'):
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'SALTRA no configurado para esta gestoría'}

        self.update_state(state='PROCESSING', meta={'progress': 5, 'status': 'Conectando...'})

        # Crear servicio SALTRA con credenciales desencriptadas de la gestoría
        saltra = SaltraService(
            api_key=saltra_config['email'],
            api_secret=saltra_config['password'],
            cert_secret=saltra_config['cert_secret']
        )
        
        items = saltra.get_all_notifications(notification_type=tipo, max_pages=max_pages)
        
        nuevas = 0
        actualizadas = 0
        
        for i, item in enumerate(items):
            self.update_state(state='PROCESSING', meta={'progress': int((i/len(items))*90)})
            sent_ref = item.get('sentReference')
            if not sent_ref: 
                continue
            
            existente = NotificacionSaltra.query.filter_by(
                sent_reference=sent_ref,
                gestoria_id=gestoria_id
            ).first()
            
            if existente:
                if existente.state != item.get('state'):
                    existente.state = item.get('state')
                    existente.datos_raw = item
                    actualizadas += 1
            else:
                nueva = NotificacionSaltra.from_api_data(item)
                nueva.gestoria_id = gestoria_id  # Asignar gestoría
                
                # Intentar asociar empresa por NIF (si tiene)
                nif = (item.get('nifTitular') or '').strip().upper()
                nif_clean = re.sub(r'[\s\.-]', '', nif).lstrip("ES").lstrip("0")[:9]
                if nif_clean:
                    alias = AliasNIF.query.filter_by(nif=nif_clean).first()
                    # Multi-tenant: filtrar por gestoria_id
                    emp = alias.empresa if alias else Empresa.query.filter_by(
                        nif=nif_clean,
                        gestoria_id=gestoria_id
                    ).first()
                    if emp: 
                        nueva.empresa_id = emp.id
                else:
                    logger.warning(f"Notificación {nueva.identifier} sin NIF - guardada sin empresa")
                
                db.session.add(nueva)
                nuevas += 1
            
            if i % 50 == 0: 
                db.session.commit()
        
        db.session.commit()
        
        # Log de sincronización
        sync_log = SaltraSyncLog(
            gestoria_id=gestoria_id,
            tipo=tipo,
            total_api=len(items),
            nuevas=nuevas,
            actualizadas=actualizadas,
            errores=0,
            mensaje='Sincronización completada correctamente'
        )
        db.session.add(sync_log)
        db.session.commit()
        
        self.update_state(state='SUCCESS', meta={'progress': 100})
        return {
            NotificationTypes.SUCCESS: True,
            'nuevas': nuevas,
            'actualizadas': actualizadas,
            'total': len(items),
            'gestoria_id': gestoria_id
        }   



@celery.task(
    bind=True,
    name='descargar_pdf_saltra',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3},
    acks_late=True
)
def descargar_pdf_saltra(self, notificacion_id):
    """
    Descarga el voucher/resguardo de una notificación de Saltra
    Verifica disponibilidad primero para evitar intentos fallidos
    """
    from extensions import db
    from models import Empresa, Documento
    # models_saltra ya importado al nivel superior
    from services.saltra_service import SaltraService
    
    app = get_flask_app()
    
    with app.app_context():
        notif = None
        try:
            self.update_state(state='PROCESSING', meta={'progress': 10, 'status': 'Iniciando...'})
            
            notif = db.session.get(NotificacionSaltra, notificacion_id)
            if not notif:
                return {'status': NotificationTypes.ERROR, 'message': 'Notificación no encontrada'}
            
            if notif.pdf_descargado and notif.pdf_path:
                return {'status': 'already_downloaded', 'path': notif.pdf_path}
            
            saltra = SaltraService()
            
            # PASO 1: Verificar disponibilidad
            self.update_state(state='PROCESSING', meta={'progress': 20, 'status': 'Verificando disponibilidad...'})
            
            check = saltra.check_voucher_availability(notif.sent_reference)
            
            if not check.get('available'):
                notif.error_mensaje = check.get('message', 'Resguardo no disponible')
                db.session.commit()
                return {
                    'status': 'not_available',
                    'message': check.get('message')
                }
            
            # PASO 2: Descargar si está disponible
            self.update_state(state='PROCESSING', meta={'progress': 50, 'status': 'Descargando resguardo...'})
            
            result = saltra.download_notification_voucher(notif.sent_reference)
            
            if not result:
                notif.error_mensaje = "No se pudo descargar el voucher"
                db.session.commit()
                return {'status': 'failed_download', 'message': 'Error descargando voucher'}
            
            pdf_bytes, filename = result
            
            # PASO 3: Guardar archivo
            self.update_state(state='PROCESSING', meta={'progress': 70, 'status': 'Guardando archivo...'})
            
            # Determinar ruta destino
            if notif.empresa_id and notif.empresa:
                ruta_base = os.path.join(
                    app.config['RUTA_RAIZ_NOTIFICACIONES'],
                    notif.empresa.nombre,
                    DocumentCategories.POR_PROCESAR
                )
            else:
                ruta_base = app.config.get('RUTA_INBOX', os.path.join(basedir, 'storage', '__INBOX_NO_CLASIFICADOS'))
            
            os.makedirs(ruta_base, exist_ok=True)
            
            # Generar nombre único
            safe_filename = f"DEHU_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
            ruta_completa = os.path.join(ruta_base, safe_filename)
            
            # Evitar duplicados
            counter = 1
            base_name, ext = os.path.splitext(ruta_completa)
            while os.path.exists(ruta_completa):
                ruta_completa = f"{base_name}_{counter}{ext}"
                counter += 1
            
            # Guardar PDF
            with open(ruta_completa, 'wb') as f:
                f.write(pdf_bytes)
            
            notif.pdf_descargado = True
            notif.pdf_path = ruta_completa
            notif.resguardo_path = ruta_completa
            notif.error_mensaje = None  # Limpiar error previo
            
            self.update_state(state='PROCESSING', meta={'progress': 90, 'status': 'Creando documento...'})
            
            # Crear documento en BD si tiene empresa
            if notif.empresa_id:
                doc = Documento(
                    empresa_id=notif.empresa_id,
                    gestoria_id=get_current_gestoria_id(),  # Multi-tenant
                    nombre_archivo=os.path.basename(ruta_completa),
                    ruta_archivo=ruta_completa,
                    categoria=DocumentCategories.POR_PROCESAR,
                    procesado=False,
                    datos_extraidos={
                        'origen': 'DEHU_SALTRA',
                        'identifier': notif.identifier,
                        'emisor': notif.emitter_entity,
                        'concepto': notif.concept,
                        'fecha_notificacion': notif.availability_date.isoformat() if notif.availability_date else None,
                        'estado': notif.state
                    }
                )
                db.session.add(doc)
                db.session.flush()
                notif.documento_id = doc.id
                notif.procesado = True
            
            db.session.commit()
            
            return {
                'status': NotificationTypes.SUCCESS,
                'path': ruta_completa,
                'empresa': notif.empresa.nombre if notif.empresa else None,
                'documento_id': notif.documento_id
            }
            
        except Exception as e:
            if notif:
                try:
                    notif.error_mensaje = str(e)[:500]
                    db.session.commit()
                except:
                    pass
            
            return {'status': NotificationTypes.ERROR, 'message': str(e)}

@celery.task(
    bind=True,
    name='descargar_masivo_saltra',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 2},
    acks_late=True
)
def descargar_masivo_saltra(self, gestoria_id, notificacion_ids):
    """
    Descarga masiva de notificaciones SALTRA con progreso en tiempo real
    
    Args:
        gestoria_id: ID de la gestoría
        notificacion_ids: Lista de IDs de notificaciones a descargar
    
    Returns:
        {
            'success': bool,
            'total': int,
            'descargados': int,
            'errores': int,
            'errores_detalle': [...]
        }
    """
    # models_saltra ya importado al nivel superior
    from models import Documento, Gestoria
    import json
    
    app = get_flask_app()
    
    with app.app_context():
        try:
            # Obtener credenciales de la gestoría
            gestoria = Gestoria.query.get(gestoria_id)
            if not gestoria or not gestoria.configuracion:
                return {'success': False, 'error': 'Gestoría no encontrada'}
            
            saltra_config = gestoria.configuracion.get('saltra', {})
            if not saltra_config.get('email') or not saltra_config.get('password'):
                return {'success': False, 'error': 'SALTRA no configurado'}
            
            # Crear servicio SALTRA
            saltra = SaltraService(
                api_key=saltra_config['email'],
                api_secret=saltra_config['password'],
                cert_secret=saltra_config.get('cert_secret')
            )
            
            total = len(notificacion_ids)
            descargados = 0
            errores = 0
            errores_detalle = []
            
            # Inicializar progreso en Redis
            progress_key = f"saltra_download_progress:{self.request.id}"
            celery.backend.set(progress_key, json.dumps({
                'task_id': self.request.id,
                'total': total,
                'current': 0,
                'descargados': 0,
                'errores': 0,
                'progreso': 0,
                'status': 'PROCESSING',
                'notificacion_actual': None,
                'errores_detalle': []
            }))
            
            for idx, notif_id in enumerate(notificacion_ids):
                try:
                    notif = NotificacionSaltra.query.get(notif_id)
                    if not notif:
                        errores += 1
                        errores_detalle.append({
                            'id': notif_id,
                            'error': 'Notificación no encontrada'
                        })
                        continue
                    
                    # Actualizar progreso actual
                    current_progress = {
                        'task_id': self.request.id,
                        'total': total,
                        'current': idx + 1,
                        'descargados': descargados,
                        'errores': errores,
                        'progreso': int(((idx + 1) / total) * 100),
                        'status': 'PROCESSING',
                        'notificacion_actual': {
                            'id': notif.id,
                            'identifier': notif.identifier,
                            'nombre': f"{notif.emitter_entity} - {notif.concept}"[:50]
                        },
                        'errores_detalle': errores_detalle[-10:]  # Solo últimos 10 errores
                    }
                    celery.backend.set(progress_key, json.dumps(current_progress))
                    
                    # Descargar archivos
                    result = saltra.download_notification_files_optimized(notif.sent_reference)
                    
                    if not result[NotificationTypes.SUCCESS]:
                        errores += 1
                        errores_detalle.append({
                            'id': notif.id,
                            'identifier': notif.identifier,
                            'error': ', '.join(result.get('errors', ['Error desconocido']))
                        })
                        continue
                    
                    # Guardar archivos
                    gestoria_slug = gestoria.slug
                    nombre_empresa_safe = re.sub(r'[^\w\s-]', '', notif.empresa.nombre).strip().replace('_', ' ') if notif.empresa else 'SIN_EMPRESA'
                    
                    ruta_base = os.path.join(
                        app.config['RUTA_RAIZ_NOTIFICACIONES'],
                        gestoria_slug,
                        nombre_empresa_safe,
                        DocumentCategories.POR_PROCESAR
                    )
                    
                    archivos_guardados = []
                    
                    # Guardar documento principal
                    if result['document']:
                        pdf_bytes, filename = result['document']
                        ruta_doc = os.path.join(ruta_base, 'DEHU_Documentos')
                        os.makedirs(ruta_doc, exist_ok=True)
                        
                        safe_filename = f"DOC_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                        ruta_completa = os.path.join(ruta_doc, safe_filename)
                        
                        with open(ruta_completa, 'wb') as f:
                            f.write(pdf_bytes)
                        
                        if notif.empresa_id:
                            doc = Documento(
                                empresa_id=notif.empresa_id,
                                gestoria_id=gestoria_id,
                                nombre_archivo=os.path.basename(ruta_completa),
                                ruta_archivo=ruta_completa,
                                categoria=DocumentCategories.POR_PROCESAR,
                                procesado=False,
                                datos_extraidos={
                                    'origen': 'DEHU_SALTRA',
                                    'tipo': 'Documento Principal',
                                    'subcategoria': 'Documentos',
                                    'identifier': notif.identifier,
                                    'sent_reference': notif.sent_reference
                                }
                            )
                            db.session.add(doc)
                        archivos_guardados.append('documento')
                    
                    # Guardar resguardo
                    if result['voucher']:
                        pdf_bytes, filename = result['voucher']
                        ruta_resg = os.path.join(ruta_base, 'DEHU_Resguardos')
                        os.makedirs(ruta_resg, exist_ok=True)
                        
                        safe_filename = f"RESG_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                        ruta_completa = os.path.join(ruta_resg, safe_filename)
                        
                        with open(ruta_completa, 'wb') as f:
                            f.write(pdf_bytes)
                        
                        if notif.empresa_id:
                            doc = Documento(
                                empresa_id=notif.empresa_id,
                                gestoria_id=gestoria_id,
                                nombre_archivo=os.path.basename(ruta_completa),
                                ruta_archivo=ruta_completa,
                                categoria=DocumentCategories.POR_PROCESAR,
                                procesado=False,
                                datos_extraidos={
                                    'origen': 'DEHU_SALTRA',
                                    'tipo': 'Resguardo',
                                    'subcategoria': 'Resguardos',
                                    'identifier': notif.identifier,
                                    'sent_reference': notif.sent_reference
                                }
                            )
                            db.session.add(doc)
                        archivos_guardados.append('resguardo')
                    
                    # Marcar como descargado
                    if archivos_guardados:
                        notif.pdf_descargado = True
                        notif.procesado = True
                        descargados += 1
                    
                    # Commit cada 10 notificaciones
                    if (idx + 1) % 10 == 0:
                        db.session.commit()
                    
                except Exception as e:
                    logger.error(f"Error descargando notificación {notif_id}: {str(e)}")
                    errores += 1
                    errores_detalle.append({
                        'id': notif_id,
                        'error': str(e)[:200]
                    })
                    db.session.rollback()
            
            # Commit final
            db.session.commit()
            
            # Actualizar progreso final
            final_progress = {
                'task_id': self.request.id,
                'total': total,
                'current': total,
                'descargados': descargados,
                'errores': errores,
                'progreso': 100,
                'status': 'SUCCESS',
                'notificacion_actual': None,
                'errores_detalle': errores_detalle[-10:]
            }
            celery.backend.set(progress_key, json.dumps(final_progress))
            
            # Emitir evento WebSocket de finalización
            try:
                from app import app as flask_app
                with flask_app.app_context():
                    socketio = flask_app.config.get('SOCKETIO')
                    if socketio:
                        socketio.emit('saltra_download_complete', {
                            'task_id': self.request.id,
                            'total': total,
                            'descargados': descargados,
                            'errores': errores
                        }, room=f'gestoria_{gestoria_id}')
            except Exception as e:
                logger.warning(f"Error enviando notificación WebSocket: {e}")
            
            return {
                'success': True,
                'total': total,
                'descargados': descargados,
                'errores': errores,
                'errores_detalle': errores_detalle
            }
            
        except Exception as e:
            logger.error(f"Error en descarga masiva: {str(e)}")
            # Actualizar progreso con error
            error_progress = {
                'task_id': self.request.id,
                'status': 'FAILURE',
                'error': str(e)
            }
            celery.backend.set(f"saltra_download_progress:{self.request.id}", json.dumps(error_progress))
            raise


@celery.task(bind=True)
def procesar_finiquito_inteligente(self, documento_id):
    """Detecta si es finiquito fiscal o laboral y procesa según corresponda"""
    from models import db, Documento, FiniquitoLinea, FiniquitoLaboral
    from services.notificacion_extractor import NotificacionExtractor
    import google.generativeai as genai
    import os
    from datetime import datetime
    
    app = get_flask_app()
    with app.app_context():
        doc = db.session.get(Documento, documento_id)
        if not doc:
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Documento no encontrado'}
        
        try:
            from gemini_utils import obtener_api_key_disponible
            
            # Configurar Gemini con multi-key fallback
            api_key, key_num = obtener_api_key_disponible()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            logger.info(f"Celery task usando API Key #{key_num} para doc {documento_id}")
            
            # Extraer texto usando resolución robusta de ruta
            from utils.storage_utils import resolve_document_path
            ruta_archivo = resolve_document_path(doc)
            
            if not ruta_archivo or not os.path.exists(ruta_archivo):
                logger.error(f"❌ ERROR: No se pudo resolver ruta física para doc {documento_id}: {doc.ruta_archivo}")
                doc.procesado = True
                doc.datos_extraidos = {'error': 'Archivo físico no encontrado'}
                db.session.commit()
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Archivo no encontrado'}

            extractor = NotificacionExtractor()
            extracted_text = extractor.extract_text_from_pdf(ruta_archivo)
            logger.info(f"Texto extraído (len={len(extracted_text or '')}) para doc {documento_id}")
            if not extracted_text:
                logger.error(f"❌ ERROR: No se pudo extraer texto del PDF {doc.ruta_archivo}")
                doc.procesado = True # Marcar como procesado aunque falle texto para no reintentar infinitamente en el bucle
                doc.datos_extraidos = {'error': 'No se pudo extraer texto del PDF'}
                db.session.commit()
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No se pudo extraer texto'}
            
            # PASO 1: Detectar tipo de finiquito
            logger.info(f"Detectando tipo de finiquito para doc {documento_id}...")
            prompt_deteccion = f"""
Analiza este documento y determina si es:
A) LIQUIDACIÓN FISCAL: Tiene una tabla con múltiples plazos de pago, fechas de vencimiento, importes fraccionados
B) FINIQUITO LABORAL: Tiene datos de un trabajador, conceptos de liquidación (salarios, deducciones), un solo importe líquido

Responde SOLO con: "FISCAL" o "LABORAL"

TEXTO:
{extracted_text[:2000]}
"""
            
            response = model.generate_content(prompt_deteccion)
            tipo = response.text.strip().upper()
            logger.info(f"Tipo detectado para doc {documento_id}: {tipo}")
            
            if 'FISCAL' in tipo:
                return procesar_finiquito_fiscal(documento_id, extracted_text, model)
            else:
                return procesar_finiquito_laboral_fn(documento_id, extracted_text, model)
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error procesando finiquito: {str(e)}")
            import traceback
            traceback.print_exc()
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}


def procesar_finiquito_fiscal(documento_id, texto, model):
    """Procesa liquidación fiscal con tabla de plazos"""
    from models import db, Documento, FiniquitoLinea
    from datetime import datetime
    
    doc = db.session.get(Documento, documento_id)
    
    prompt = f"""
Analiza este documento de liquidación fiscal y extrae:

1. TODAS las filas individuales de la tabla de plazos
2. La fila del TOTAL GENERAL

Para cada fila individual, extrae:
- importe_principal (número decimal)
- recargo_apremio (número decimal)
- importe_total_deuda (número decimal)
- importe_intereses (número decimal)
- importe_total_plazo (número decimal)
- fecha_vencimiento (formato DD-MM-YYYY como string)

Para el TOTAL GENERAL, extrae los mismos campos pero sin fecha_vencimiento.

Devuelve un JSON con esta estructura:
{{
  "lineas": [
    {{
      "importe_principal": 1291.52,
      "recargo_apremio": 0.00,
      "importe_total_deuda": 1291.52,
      "importe_intereses": 8.77,
      "importe_total_plazo": 1300.29,
      "fecha_vencimiento": "22-12-2025"
    }}
  ],
  "total_general": {{
    "importe_principal": 7749.16,
    "recargo_apremio": 0.00,
    "importe_total_deuda": 7749.16,
    "importe_intereses": 118.02,
    "importe_total_plazo": 7867.18
  }}
}}

IMPORTANTE:
- Usa nombres de claves SIN ESPACIOS y en minúsculas con guiones bajos
- El total_general NO debe tener fecha_vencimiento

TEXTO DEL DOCUMENTO:
{texto}
"""
    
    response = model.generate_content(prompt)
    respuesta_texto = response.text.strip()
    
    # Limpiar markdown
    if '```json' in respuesta_texto:
        respuesta_texto = respuesta_texto.split('```json')[1].split('```')[0].strip()
    elif '```' in respuesta_texto:
        respuesta_texto = respuesta_texto.split('```')[1].split('```')[0].strip()
    
    # Arreglar comillas simples
    respuesta_texto = respuesta_texto.replace("'", '"')
    
    # Log para debug
    logger.info(f"Respuesta de IA (finiquito fiscal):\n{respuesta_texto[:500]}")
    
    import json
    try:
        data = json.loads(respuesta_texto)
        lineas_data = data.get('lineas', [])
        total_general = data.get('total_general', {})
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON: {e}")
        logger.info(f"Texto completo:\n{respuesta_texto}")
        raise Exception(f"No se pudo parsear la respuesta: {respuesta_texto[:200]}")
    
    # Eliminar líneas existentes
    FiniquitoLinea.query.filter_by(documento_id=documento_id).delete()
    
    for linea_data in lineas_data:
        fecha_venc = None
        if linea_data.get('fecha_vencimiento'):
            try:
                fecha_venc = datetime.strptime(linea_data['fecha_vencimiento'], '%d-%m-%Y').date()
            except:
                pass
        
        linea = FiniquitoLinea(
            documento_id=documento_id,
            importe_principal=float(linea_data.get('importe_principal', 0)),
            recargo_apremio=float(linea_data.get('recargo_apremio', 0)),
            importe_total_deuda=float(linea_data.get('importe_total_deuda', 0)),
            importe_intereses=float(linea_data.get('importe_intereses', 0)),
            importe_total_plazo=float(linea_data.get('importe_total_plazo', 0)),
            fecha_vencimiento=fecha_venc,
            estado=TaskStates.PENDIENTE
        )
        db.session.add(linea)
    
    doc.procesado = True
    doc.datos_extraidos = {
        'tipo_finiquito': 'fiscal',
        'total_general': total_general  # 👈 Guardar el total general aquí
    }
    db.session.commit()
    
    return {NotificationTypes.SUCCESS: True, 'tipo': 'fiscal', 'lineas_extraidas': len(lineas_data), 'total_general': total_general}


def procesar_finiquito_laboral_fn(documento_id, texto, model):
    """Procesa finiquito laboral con desglose de conceptos"""
    from models import db, Documento, FiniquitoLaboral
    
    doc = db.session.get(Documento, documento_id)
    
    prompt = f"""
Analiza este FINIQUITO LABORAL y extrae:

1. Datos del trabajador:
   - nombre
   - nif
   - categoria
   - motivo_baja

2. Conceptos de DEVENGOS (lo que cobra):
   Array de {{"concepto": "nombre", "importe": valor}}

3. Conceptos de DEDUCCIONES (lo que se descuenta):
   Array de {{"concepto": "nombre", "importe": valor}}

4. Totales:
   - total_devengos
   - total_deducciones
   - importe_liquido (a percibir)

Responde en JSON:
{{
  "nombre_trabajador": "...",
  "nif_trabajador": "...",
  "categoria": "...",
  "motivo_baja": "...",
  "devengos": [{{"concepto": "...", "importe": 0.00}}],
  "deducciones": [{{"concepto": "...", "importe": 0.00}}],
  "total_devengos": 0.00,
  "total_deducciones": 0.00,
  "importe_liquido": 0.00
}}

TEXTO:
{texto}
"""
    
    response = model.generate_content(prompt)
    respuesta_texto = response.text.strip()
    
    # Limpiar markdown y caracteres problemáticos
    if '```json' in respuesta_texto:
        respuesta_texto = respuesta_texto.split('```json')[1].split('```')[0].strip()
    elif '```' in respuesta_texto:
        respuesta_texto = respuesta_texto.split('```')[1].split('```')[0].strip()
    
    # Intentar arreglar comillas simples a dobles
    respuesta_texto = respuesta_texto.replace("'", '"')
    
    # Log para debug
    logger.info(f"Respuesta de IA (finiquito laboral):\n{respuesta_texto[:500]}")
    
    import json
    try:
        data = json.loads(respuesta_texto)
    except json.JSONDecodeError as e:
        logger.error(f"Error parseando JSON: {e}")
        logger.info(f"Texto completo:\n{respuesta_texto}")
        # Intentar con json5 o ast.literal_eval como fallback
        try:
            import re
            # Eliminar comentarios si hay
            respuesta_texto = re.sub(r'//.*?\n', '\n', respuesta_texto)
            data = json.loads(respuesta_texto)
        except:
            raise Exception(f"No se pudo parsear la respuesta de la IA: {respuesta_texto[:200]}")
    
    # Eliminar existente si lo hay (para evitar error de UniqueConstraint)
    FiniquitoLaboral.query.filter_by(documento_id=documento_id).delete()
    
    # Crear nuevo
    finiquito = FiniquitoLaboral(
        documento_id=documento_id,
        nombre_trabajador=data.get('nombre_trabajador'),
        nif_trabajador=data.get('nif_trabajador'),
        categoria=data.get('categoria'),
        motivo_baja=data.get('motivo_baja'),
        conceptos_devengos=data.get('devengos', []),
        conceptos_deducciones=data.get('deducciones', []),
        total_devengos=float(data.get('total_devengos', 0)),
        total_deducciones=float(data.get('total_deducciones', 0)),
        importe_liquido=float(data.get('importe_liquido', 0)),
        estado=TaskStates.PENDIENTE
    )
    db.session.add(finiquito)
    
    doc.procesado = True
    doc.datos_extraidos = {'tipo_finiquito': 'laboral'}
    db.session.commit()
    
    return {NotificationTypes.SUCCESS: True, 'tipo': 'laboral', 'importe_liquido': finiquito.importe_liquido}

# ============================================
# CONFIGURACIÓN DE CELERY BEAT (TAREAS PROGRAMADAS)
# ============================================

from celery.schedules import crontab
from constants import DocumentCategories, NotificationTypes, TaskStates

# ⚠️ IMPORTANTE: Importar tareas de billing para registrarlas en el worker
import celery_tasks_billing
from utils.logger import logger


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configura las tareas programadas de Celery Beat"""
    
    # Recordatorios diarios a las 9:00 AM
    sender.add_periodic_task(
        crontab(hour=9, minute=0),
        procesar_recordatorios_diarios.s(),
        name='recordatorios-finiquitos-diarios'
    )


# ============================================
# TAREAS DE RECORDATORIOS DE PAGO
# ============================================

@celery.task
def procesar_recordatorios_diarios():
    """
    Tarea principal que se ejecuta diariamente.
    Revisa cuotas próximas a vencer y envía recordatorios.
    """
    from datetime import date, timedelta
    from models import FiniquitoLinea
    from email_sender import enviar_email_recordatorio
    
    app = get_flask_app()
    
    with app.app_context():
        hoy = date.today()
        fecha_7_dias = hoy + timedelta(days=7)
        fecha_3_dias = hoy + timedelta(days=3)
        
        print(f"\n{'='*60}")
        print(f"🔔 Procesando recordatorios diarios - {hoy.strftime('%d/%m/%Y')}")
        print(f"{'='*60}\n")
        
        # 1. Recordatorios de 7 días
        lineas_7_dias = FiniquitoLinea.query.filter(
            FiniquitoLinea.fecha_vencimiento == fecha_7_dias,
            FiniquitoLinea.estado == TaskStates.PENDIENTE
        ).all()
        
        print(f"📅 Cuotas que vencen en 7 días: {len(lineas_7_dias)}")
        for linea in lineas_7_dias:
            # Solo enviar si no se ha enviado recordatorio de 7 días aún
            if not linea.recordatorios_count or linea.recordatorios_count == 0:
                print(f"  → Enviando recordatorio 7 días para cuota ID {linea.id}")
                enviar_recordatorio_email.delay(linea.id, '7_dias')
        
        # 2. Recordatorios de 3 días
        lineas_3_dias = FiniquitoLinea.query.filter(
            FiniquitoLinea.fecha_vencimiento == fecha_3_dias,
            FiniquitoLinea.estado == TaskStates.PENDIENTE
        ).all()
        
        logger.warning(f" Cuotas que vencen en 3 días: {len(lineas_3_dias)}")
        for linea in lineas_3_dias:
            # Enviar si tiene menos de 2 recordatorios
            if (linea.recordatorios_count or 0) < 2:
                print(f"  → Enviando recordatorio 3 días para cuota ID {linea.id}")
                enviar_recordatorio_email.delay(linea.id, '3_dias')
        
        # 3. Recordatorios del día del vencimiento
        lineas_hoy = FiniquitoLinea.query.filter(
            FiniquitoLinea.fecha_vencimiento == hoy,
            FiniquitoLinea.estado == TaskStates.PENDIENTE
        ).all()
        
        print(f"🚨 Cuotas que vencen HOY: {len(lineas_hoy)}")
        for linea in lineas_hoy:
            print(f"  → Enviando recordatorio VENCIMIENTO para cuota ID {linea.id}")
            enviar_recordatorio_email.delay(linea.id, 'vencimiento')
            # Crear tarea de seguimiento
            crear_tarea_seguimiento.delay(linea.id)
        
        print(f"\n{'='*60}")
        logger.info(f"Recordatorios procesados correctamente")
        print(f"{'='*60}\n")
        
        return {
            'fecha': hoy.isoformat(),
            'recordatorios_7_dias': len(lineas_7_dias),
            'recordatorios_3_dias': len(lineas_3_dias),
            'recordatorios_vencimiento': len(lineas_hoy)
        }


@celery.task
def enviar_recordatorio_email(linea_id, tipo_recordatorio):
    """
    Envía un email de recordatorio para una línea específica.
    tipo_recordatorio: '7_dias', '3_dias', 'vencimiento'
    """
    from models import FiniquitoLinea
    from email_sender import enviar_email_recordatorio
    
    
    app = get_flask_app()
    
    with app.app_context():
        try:
            linea = db.session.get(FiniquitoLinea, linea_id)
            
            if not linea:
                logger.error(f"Línea {linea_id} no encontrada")
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Línea no encontrada'}
            
            if linea.estado != TaskStates.PENDIENTE:
                print(f"⏭️  Línea {linea_id} ya está pagada, omitiendo")
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Cuota ya pagada'}
            
            # Enviar email
            enviado = enviar_email_recordatorio(linea, tipo_recordatorio)
            
            if enviado:
                logger.info(f"Email de recordatorio '{tipo_recordatorio}' enviado para línea {linea_id}")
                return {NotificationTypes.SUCCESS: True, 'tipo': tipo_recordatorio, 'linea_id': linea_id}
            else:
                logger.error(f"Error enviando email para línea {linea_id}")
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Error enviando email'}
        
        except Exception as e:
            logger.error(f"Error procesando recordatorio para línea {linea_id}: {e}")
            import traceback
            traceback.print_exc()
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}


@celery.task
def crear_tarea_seguimiento(linea_id):
    """
    Crea una tarea de seguimiento para cuotas vencidas sin pago.
    Se integra con tu sistema de tareas existente.
    """
    from models import FiniquitoLinea, Documento, Empresa
    from datetime import datetime, timezone
    
    app = get_flask_app()
    
    with app.app_context():
        try:
            linea = db.session.get(FiniquitoLinea, linea_id)
            
            if not linea:
                return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Línea no encontrada'}
            
            documento = db.session.get(Documento, linea.documento_id)
            empresa = db.session.get(Empresa, documento.empresa_id)
            
            # Actualizar documento como tarea pendiente
            documento.estado_tarea = 'Pendiente'
            documento.fecha_plazo = datetime.now(timezone.utc)
            
            # Opcional: Asignar a un usuario específico
            # documento.asignado_a_id = 1  # ID del usuario responsable
            
            db.session.commit()
            
            logger.info(f"Tarea de seguimiento creada para cuota vencida: {empresa.nombre} - €{linea.importe_total_plazo:.2f}")
            
            return {
                NotificationTypes.SUCCESS: True,
                'linea_id': linea_id,
                'empresa': empresa.nombre,
                'importe': linea.importe_total_plazo
            }
        
        except Exception as e:
            logger.error(f"Error creando tarea de seguimiento: {e}")
            import traceback
            traceback.print_exc()
            return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}

# ========================================
# ENVÍO MASIVO DE CORREOS CON RATE LIMITING
# ========================================

@celery.task(bind=True, name='enviar_correos_masivo_async')
def enviar_correos_masivo_async(self, mes, anio, user_id, modo=None, tipos_documentos=None):
    """
    Tarea asíncrona para envío masivo de correos con rate limiting.
    Previene bloqueo de cuenta de email con delays entre envíos.
    
    Args:
        mes: Mes de los documentos
        anio: Año de los documentos
        user_id: ID del usuario que inició la tarea
        modo: (Legacy) 'NOMINAS' o 'NOMINAS_RNT'
        tipos_documentos: (Nuevo) Dict {'nominas': bool, 'rnt': bool, 'rlc': bool}
    
    Returns:
        dict con resultados del envío
    """
    from models import Empresa, Documento
    from email_payroll import enviar_nominas_automatico
    from sqlalchemy import extract
    from constants import DocumentCategories, NotificationTypes
    import time
    import re
    import os
    
    app = get_flask_app()
    
    # Normalizar tipos_documentos si viene de modo o es None
    if not tipos_documentos:
        tipos_documentos = {
            'nominas': True,
            'rnt': True if modo == 'NOMINAS_RNT' else False,
            'rlc': False
        }
    
    with app.app_context():
        resultados = {
            'enviados': 0,
            'errores': 0,
            'omitidos': 0,
            'detalles': []
        }
        
        # Obtener empresas con email de la gestoria actual (multi-tenant)
        # Nota: app.py ya filtra por gestoria_id, aquí lo hacemos global o por usuario_id
        # Para ser seguros, obtenemos la gestoria del usuario si fuera necesario, 
        # pero el filtrado actual por email != '' es un buen comienzo.
        empresas = Empresa.query.filter(
            Empresa.email.isnot(None),
            Empresa.email != ''
        ).all()
        
        total = len(empresas)
        logger.info(f"📧 Iniciando envío masivo: {total} empresas. Tipos: {tipos_documentos}")
        
        for idx, empresa in enumerate(empresas):
            try:
                # Actualizar progreso
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': idx + 1,
                        'total': total,
                        'empresa': empresa.nombre,
                        'enviados': resultados['enviados'],
                        'errores': resultados['errores']
                    }
                )
                
                # 1. Obtener Nóminas si está marcado
                nominas_data = []
                if tipos_documentos.get('nominas'):
                    nominas = Documento.query.filter(
                        Documento.empresa_id == empresa.id,
                        Documento.categoria == 'Nominas',
                        extract('month', Documento.fecha_creacion) == mes,
                        extract('year', Documento.fecha_creacion) == anio
                    ).all()
                    
                    for doc in nominas:
                        if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                            periodo_match = re.search(r'(\d{6})', doc.nombre_archivo)
                            periodo = periodo_match.group(1) if periodo_match else 'N/A'
                            
                            nominas_data.append({
                                'id': doc.id,
                                'ruta_pdf': doc.ruta_archivo,
                                'nombre_archivo': os.path.basename(doc.ruta_archivo),
                                'periodo': periodo,
                                'empresa_id': doc.empresa_id,
                                'empresa_nombre': empresa.nombre
                            })
                        else:
                            logger.warning(f"⚠️ Archivo de nómina no encontrado: {doc.ruta_archivo}")
                
                # 2. Obtener RNT/RLC si está marcado
                seguros_data = []
                if tipos_documentos.get('rnt') or tipos_documentos.get('rlc'):
                    filtros_ss = [Documento.empresa_id == empresa.id, 
                                 Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                                 extract('month', Documento.fecha_creacion) == mes,
                                 extract('year', Documento.fecha_creacion) == anio]
                    
                    docs_ss = Documento.query.filter(*filtros_ss).all()
                    for doc in docs_ss:
                        es_rnt = 'RNT' in doc.nombre_archivo.upper()
                        es_rlc = 'RLC' in doc.nombre_archivo.upper()
                        
                        if (es_rnt and tipos_documentos.get('rnt')) or (es_rlc and tipos_documentos.get('rlc')):
                            if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                                seguros_data.append({
                                    'id': doc.id,
                                    'ruta_pdf': doc.ruta_archivo,
                                    'nombre_archivo': os.path.basename(doc.ruta_archivo),
                                    'empresa_id': doc.empresa_id
                                })
                            else:
                                logger.warning(f"⚠️ Archivo de SS no encontrado ({doc.nombre_archivo}): {doc.ruta_archivo}")
                
                # Si no hay documentos para esta empresa, omitir
                if not nominas_data and not seguros_data:
                    resultados['omitidos'] += 1
                    resultados['detalles'].append({
                        'empresa': empresa.nombre,
                        'email': empresa.email,
                        'status': 'omitido',
                        'razon': 'Sin documentos encontrados para los criterios seleccionados'
                    })
                    continue
                
                # 3. Enviar correo (Reutilizamos la función que acepta lista de seguros)
                resultado_envio = enviar_nominas_automatico(
                    email_destino=empresa.email,
                    nominas=nominas_data,
                    rnt=seguros_data,
                    usuario_id=user_id
                )
                
                if resultado_envio.get(NotificationTypes.SUCCESS):
                    resultados['enviados'] += 1
                    resultados['detalles'].append({
                        'empresa': empresa.nombre,
                        'email': empresa.email,
                        'status': 'enviado',
                        'docs': len(nominas_data) + len(seguros_data)
                    })
                else:
                    resultados['errores'] += 1
                    resultados['detalles'].append({
                        'empresa': empresa.nombre,
                        'email': empresa.email,
                        'status': 'error',
                        'error': resultado_envio.get('message') or resultado_envio.get(NotificationTypes.ERROR)
                    })
                
                # Delay anti-spam (preventivo)
                time.sleep(1.5)
            except Exception as e:
                resultados['errores'] += 1
                resultados['detalles'].append({
                    'empresa': empresa.nombre,
                    'email': empresa.email if hasattr(empresa, 'email') else 'N/A',
                    'status': NotificationTypes.ERROR,
                    'razon': str(e)
                })
                logger.error(f"[{idx+1}/{total}] {empresa.nombre} - Excepción: {e}")
        
        print(f"\n✅ Envío masivo completado:")
        print(f"   📤 Enviados: {resultados['enviados']}")
        print(f"   ❌ Errores: {resultados['errores']}")
        print(f"   ⚠️  Omitidos: {resultados['omitidos']}\n")
        
        return resultados


@celery.task(name='activate_scheduled_maintenance')
def activate_scheduled_maintenance(user_id, scheduled_token=None):
    from models import SystemConfig
    from extensions import db
    app = get_flask_app()
    with app.app_context():
        # Forzar lectura fresca desde BD (evita caché de sesión SQLAlchemy)
        db.session.expire_all()

        # Verificar si la programación sigue siendo válida
        current_token = SystemConfig.get_value('maintenance_scheduled_token')

        # Cancelar si:
        #  a) El token fue limpiado (admin desactivó mientras esperaba) → current_token vacío/None
        #  b) El token no coincide (se reprogramó con otro countdown)
        token_limpio   = not current_token  # '' o None → admin canceló
        token_distinto = bool(scheduled_token and current_token != scheduled_token)

        if token_limpio or token_distinto:
            print(f"⚠️ [Celery] Cancelando activación de mantenimiento: "
                  f"token_limpio={token_limpio} token_distinto={token_distinto} "
                  f"(scheduled={scheduled_token!r} != current={current_token!r})")
            return {'success': False, 'reason': 'cancelled_or_reprogrammed'}

        SystemConfig.set_value('maintenance_mode', 'true', user_id)
        # Limpiar token tras activación exitosa
        SystemConfig.set_value('maintenance_scheduled_token', '', user_id)
        
        try:
            from app import app as flask_app
            socketio = flask_app.config.get('SOCKETIO')
            if socketio:
                socketio.emit('maintenance_activated', {
                    'message': SystemConfig.get_value('maintenance_message', 'Sistema en mantenimiento')
                })
        except: pass
        return {'success': True}



        
# ==========================================
# TAREA DE LIMPIEZA DE ARCHIVOS TEMPORALES
# ==========================================

@celery.task(name='cleanup_temp_files')
def cleanup_temp_files():
    '''
    Limpieza de archivos temporales - Ejecutar cada hora
    
    Elimina archivos temporales antiguos (más de 2 horas) que coincidan con:
    - temp_*
    - spainflow_*
    - tmp_*
    - *.tmp
    
    Returns:
        dict con estadísticas de limpieza
    '''
    import tempfile
    
    temp_dir = tempfile.gettempdir()
    temp_patterns = ['temp_', 'spainflow_', 'tmp_', 'iages_']
    temp_extensions = ['.tmp', '.temp']
    max_age_hours = 2
    max_age_seconds = max_age_hours * 3600
    
    cleaned_files = 0
    cleaned_dirs = 0
    total_size = 0
    errors = []
    
    try:
        current_time = time.time()
        
        # Listar archivos en directorio temporal
        for item in os.listdir(temp_dir):
            try:
                # Verificar si coincide con patrones
                matches_pattern = any(item.startswith(pattern) for pattern in temp_patterns)
                matches_extension = any(item.endswith(ext) for ext in temp_extensions)
                
                if not (matches_pattern or matches_extension):
                    continue
                
                item_path = os.path.join(temp_dir, item)
                
                # Verificar edad del archivo/directorio
                try:
                    mtime = os.path.getmtime(item_path)
                    age = current_time - mtime
                    
                    if age < max_age_seconds:
                        continue  # Muy reciente, no eliminar
                    
                except (OSError, FileNotFoundError):
                    continue
                
                # Eliminar archivo o directorio
                try:
                    if os.path.isdir(item_path):
                        # Calcular tamaño del directorio
                        dir_size = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, dirnames, filenames in os.walk(item_path)
                            for filename in filenames
                        )
                        shutil.rmtree(item_path)
                        cleaned_dirs += 1
                        total_size += dir_size
                        logger.info(f'Eliminado directorio temporal: {item} ({dir_size / 1024:.2f} KB)')
                    else:
                        file_size = os.path.getsize(item_path)
                        os.remove(item_path)
                        cleaned_files += 1
                        total_size += file_size
                        logger.debug(f'Eliminado archivo temporal: {item} ({file_size / 1024:.2f} KB)')
                        
                except PermissionError:
                    logger.warning(f'Sin permisos para eliminar: {item}')
                    errors.append(f'Permission denied: {item}')
                except Exception as e:
                    logger.warning(f'Error eliminando {item}: {str(e)}')
                    errors.append(f'{item}: {str(e)}')
                    
            except Exception as e:
                logger.warning(f'Error procesando item {item}: {str(e)}')
                continue
        
        result = {
            'success': True,
            'cleaned_files': cleaned_files,
            'cleaned_dirs': cleaned_dirs,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'errors_count': len(errors),
            'errors': errors[:10]  # Solo primeros 10 errores
        }
        
        logger.info(
            f'Limpieza completada: {cleaned_files} archivos, '
            f'{cleaned_dirs} directorios, '
            f'{result["total_size_mb"]} MB liberados'
        )
        
        return result
        
    except Exception as e:
        logger.error(f'Error en limpieza de archivos temporales: {str(e)}')
        return {
            'success': False,
            'error': str(e),
            'cleaned_files': cleaned_files,
            'cleaned_dirs': cleaned_dirs
        }


# ========================================
# BACKUPS AUTOMÁTICOS
# ========================================

#from backup_manager import backup_database

# @celery.task(name='backup_database_task')
#def backup_database_task():
 #   """
 #   Tarea de Celery para backup automático de BD.
 #   Programado para ejecutarse diariamente a las 2:00 AM.
#    """
 #   print("\n🕐 Ejecutando backup programado...")
#    resultado = backup_database()
    
 #   if resultado:
 #       print("✅ Backup programado completado con éxito")
 #       return {NotificationTypes.SUCCESS: True, "message": "Backup completado"}
  #  else:
  #      print("❌ Backup programado falló")
  #      return {NotificationTypes.SUCCESS: False, "message": "Error en backup"}


# Configurar Beat Schedule para backups automáticos
#celery.conf.beat_schedule = celery.conf.beat_schedule or {}
#celery.conf.beat_schedule['backup-database-daily'] = {
#    'task': 'backup_database_task',
#    'schedule': crontab(hour=2, minute=0),  # Diario a las 2:00 AM
#}

#print("✅ Task de backup automático registrada (2:00 AM diario)")

# ============================================
# CALENDARIO TRIBUTARIO AEAT
# ============================================

@celery.task(
    bind=True,
    name='sincronizar_calendario_aeat',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={'max_retries': 3},
    acks_late=True
)
def sincronizar_calendario_aeat(self, year=None):
    """
    Sincroniza el calendario tributario de la AEAT
    
    Args:
        year (int): Año del calendario (por defecto el año actual)
    
    Returns:
        dict: Resultado de la sincronización con estadísticas
    """
    from services.aeat_calendar_service import AEATCalendarService
    from models import FechaTributaria, db
    from datetime import datetime
    
    app = get_flask_app()
    
    with app.app_context():
        try:
            if not year:
                year = datetime.now().year
            
            logger.info(f"Iniciando sincronización del calendario AEAT para el año {year}")
            self.update_state(state='PROCESSING', meta={'progress': 10, 'status': 'Conectando con AEAT...'})
            
            # Crear servicio y obtener fechas
            service = AEATCalendarService()
            fechas = service.fetch_calendar(year)
            
            if not fechas:
                logger.warning(f"No se obtuvieron fechas del calendario AEAT para el año {year}")
                return {
                    'success': False,
                    'year': year,
                    'error': 'No se obtuvieron fechas del calendario'
                }
            
            self.update_state(state='PROCESSING', meta={'progress': 30, 'status': f'Procesando {len(fechas)} fechas...'})
            
            nuevas = 0
            actualizadas = 0
            
            for idx, fecha_data in enumerate(fechas):
                try:
                    # Buscar si ya existe
                    existente = FechaTributaria.query.filter_by(
                        fecha=fecha_data['fecha'],
                        titulo=fecha_data['titulo'],
                        año=year
                    ).first()
                    
                    if existente:
                        # Actualizar
                        existente.descripcion = fecha_data.get('descripcion')
                        existente.tipo_impuesto = fecha_data.get('tipo_impuesto')
                        existente.modelo = fecha_data.get('modelo')
                        existente.periodicidad = fecha_data.get('periodicidad')
                        existente.mes = fecha_data.get('mes')
                        existente.trimestre = fecha_data.get('trimestre')
                        existente.fecha_sincronizacion = datetime.utcnow()
                        actualizadas += 1
                    else:
                        # Crear nueva
                        nueva_fecha = FechaTributaria(**fecha_data)
                        nueva_fecha.fuente_url = f"{service.BASE_URL}/calendario-contribuyente-{year}.html"
                        db.session.add(nueva_fecha)
                        nuevas += 1
                    
                    # Commit cada 50 fechas
                    if (idx + 1) % 50 == 0:
                        db.session.commit()
                        progress = 30 + int(((idx + 1) / len(fechas)) * 60)
                        self.update_state(state='PROCESSING', meta={
                            'progress': progress,
                            'status': f'Procesadas {idx + 1}/{len(fechas)} fechas...'
                        })
                
                except Exception as e:
                    logger.error(f"Error procesando fecha {fecha_data.get('fecha')}: {e}")
                    continue
            
            # Commit final
            db.session.commit()
            
            logger.info(f"Sincronización completada: {nuevas} nuevas, {actualizadas} actualizadas")
            
            self.update_state(state='SUCCESS', meta={'progress': 100})
            
            return {
                'success': True,
                'year': year,
                'nuevas': nuevas,
                'actualizadas': actualizadas,
                'total': len(fechas)
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando calendario AEAT: {e}")
            import traceback
            traceback.print_exc()
            raise

# ============================================
# IMPORTAR TAREAS DE NÓMINAS Y SEGUROS SOCIALES
# ============================================
# Importar al final para evitar importación circular
import tasks_nominas  # noqa: E402
import tasks_seguros_sociales  # noqa: E402