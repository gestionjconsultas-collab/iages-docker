from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models_dehu import NotificacionDehu
from models import Empresa, Documento, Plantilla
from utils.storage_utils import get_empresa_storage_path, get_gestoria_inbox_path
from utils.file_utils import get_file_hash
from constants import DocumentCategories
from services.notificacion_extractor import NotificacionExtractor
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

dehu_sync_bp = Blueprint('dehu_sync', __name__)

@dehu_sync_bp.route('/api/notificaciones/plan', methods=['GET'])
def get_plan_info():
    """Retorna información del plan y límites para SyncManager."""
    try:
        api_key = request.headers.get('X-Gestoria-Key')
        if not api_key:
            return jsonify({'error': 'X-Gestoria-Key required'}), 401
        
        from models import Gestoria
        gestoria = Gestoria.query.filter_by(api_key=api_key).first()
        if not gestoria:
            return jsonify({'error': 'Invalid API Key'}), 403
            
        # Obtener el límite real del plan configurado desde la suscripción activa
        from models_billing import Suscripcion
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria.id).first()
        limit = suscripcion.plan.certificados_max if (suscripcion and suscripcion.plan) else gestoria.max_certificados

        # Convención de ilimitado: -1 o null
        if limit == -1 or limit is None:
            limit = "ilimitado"

        response = jsonify({
            'plan': gestoria.plan,
            'limit': limit,
            'nombre_gestoria': gestoria.nombre
        })
        
        # Headers alternativos solicitados
        response.headers['X-Plan-Name'] = gestoria.plan
        response.headers['X-Plan-Limit'] = str(limit)
        
        return response
    except Exception as e:
        logger.error(f"Error en get_plan_info: {e}")
        return jsonify({'error': str(e)}), 500

@dehu_sync_bp.route('/api/validate', methods=['GET'])
def validate_conecta():
    """Valida la API Key y retorna info de plan para Conecta/Iages."""
    try:
        api_key = request.headers.get('X-Gestoria-Key')
        if not api_key:
            return jsonify({'success': False, 'error': 'X-Gestoria-Key required'}), 401
        
        from models import Gestoria
        gestoria = Gestoria.query.filter_by(api_key=api_key).first()
        if not gestoria:
            return jsonify({'success': False, 'error': 'Invalid API Key'}), 403
            
        # Obtener el límite real
        from models_billing import Suscripcion
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria.id).first()
        limit = suscripcion.plan.certificados_max if (suscripcion and suscripcion.plan) else gestoria.max_certificados

        return jsonify({
            'success': True,
            'data': {
                'plan': gestoria.plan,
                'limit': limit,
                'iages_active': getattr(gestoria, 'iages_active', False),
                'expires_at': gestoria.fecha_expiracion.isoformat() if gestoria.fecha_expiracion else None
            }
        })
    except Exception as e:
        logger.error(f"Error en validate_conecta: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@dehu_sync_bp.route('/api/notificaciones/upload', methods=['POST'])
def upload_notification_complete():
    """
    Endpoint unificado para el conector SyncManager.
    Soporta múltiples nomenclaturas para máxima compatibilidad.
    """
    try:
        # 1. Validar Autenticación
        api_key = request.headers.get('X-Gestoria-Key')
        if not api_key:
            logger.warning("Intento de sync sin X-Gestoria-Key")
            return jsonify({'error': 'X-Gestoria-Key required'}), 401
        
        from models import Gestoria
        gestoria = Gestoria.query.filter_by(api_key=api_key).first()
        if not gestoria:
            logger.warning(f"API Key inválida: {api_key}")
            return jsonify({'error': 'Invalid API Key'}), 403

        # 2. Extraer Datos (Soporte Multi-lenguaje)
        data = request.form
        ref = data.get('referencia') or data.get('reference') or data.get('identificador') or data.get('identifier')
        
        if not ref:
            logger.error(f"Falta referencia en el payload. Recibido: {list(data.keys())}")
            return jsonify({'error': 'Reference required (referencia/reference/identifier)'}), 400

        # Mapeo de archivos
        anexo = request.files.get('anexo') or request.files.get('file')
        resguardo = request.files.get('resguardo') or request.files.get('voucher')

        # 3. Buscar o crear registro
        notif = NotificacionDehu.query.filter_by(referencia=ref).first()
        if not notif:
            notif = NotificacionDehu(referencia=ref, gestoria_id=gestoria.id)
            db.session.add(notif)
            logger.info(f"Creando nuevo registro DEHú vía Sync: {ref}")
        else:
            # Asegurar que tiene gestoria_id si es una actualización
            if not notif.gestoria_id:
                notif.gestoria_id = gestoria.id

        # 4. Actualizar metadatos (Soporte flexible)
        notif.nif_titular = data.get('nif') or data.get('nif_titular') or data.get('nifTitular') or notif.nif_titular
        notif.nombre_titular = data.get('nombre') or data.get('titular') or data.get('nombreTitular') or notif.nombre_titular
        notif.titulo = data.get('titulo') or data.get('subject') or data.get('concept') or notif.titulo
        
        # Fechas
        for field in ['fecha_emision', 'fecha_descarga', 'date_download']:
            val = data.get(field)
            if val:
                try:
                    db_field = 'fecha_descarga' if field == 'date_download' else field
                    setattr(notif, db_field, datetime.fromisoformat(val.replace('Z', '+00:00')))
                except Exception as e:
                    logger.warning(f"Error parseando fecha {field}: {e}")

        # Vincular empresa (Estrategia Cascada)
        if not notif.empresa_id:
            from models import Empresa
            import re
            import unicodedata

            def normalize_name(name):
                if not name: return ""
                # Quitar acentos
                n = ''.join(c for c in unicodedata.normalize('NFD', str(name)) if unicodedata.category(c) != 'Mn')
                n = n.upper()
                # Quitar puntuación
                n = re.sub(r'[^A-Z0-9\s]', ' ', n)
                # Normalizar espacios
                n = ' '.join(n.split())
                # Quitar sufijos legales comunes al final
                sufijos = [r'\bS\s*L\b', r'\bS\s*L\s*U\b', r'\bS\s*A\b', r'\bS\s*A\s*U\b', r'\bSOCIEDAD LIMITADA\b', r'\bSOCIEDAD ANONIMA\b']
                for suf in sufijos:
                    n = re.sub(suf + r'$', '', n).strip()
                return n

            empresa_id_found = None

            # 1. Búsqueda por NIF
            if notif.nif_titular:
                empresa = Empresa.query.filter_by(nif=notif.nif_titular, gestoria_id=gestoria.id).first()
                if empresa:
                    empresa_id_found = empresa.id
                    logger.debug(f"Empresa vinculada por NIF exacto: ID {empresa.id}")

            # 2. Búsqueda por Nombre Normalizado
            if not empresa_id_found and notif.nombre_titular:
                nom_norm_doc = normalize_name(notif.nombre_titular)
                if nom_norm_doc:
                    # Cargar empresas de la gestoría
                    empresas_gest = Empresa.query.filter_by(gestoria_id=gestoria.id).all()
                    for emp in empresas_gest:
                        if normalize_name(emp.nombre) == nom_norm_doc:
                            empresa_id_found = emp.id
                            logger.info(f"Empresa vinculada por NOM. NORMALIZADO ('{notif.nombre_titular}'): ID {emp.id}")
                            break

            # 3. Búsqueda por Cuenta de Cotización (CCC)
            cuenta_cotizacion = data.get('cuenta_cotizacion') or data.get('ccc')
            if not empresa_id_found and cuenta_cotizacion:
                empresa = Empresa.query.filter_by(cuenta_cotizacion=cuenta_cotizacion, gestoria_id=gestoria.id).first()
                if empresa:
                    empresa_id_found = empresa.id
                    logger.info(f"Empresa vinculada por CUENTA COTIZACIÓN ('{cuenta_cotizacion}'): ID {emp.id}")

            # Guardar resultado
            if empresa_id_found:
                notif.empresa_id = empresa_id_found
                logger.debug(f"Éxito: Vinculada lograda para notificación {ref}")
            else:
                logger.warning(f"Falla: No se pudo vincular empresa para notif {ref}. NIF: {notif.nif_titular}, Nom: {notif.nombre_titular}")

        # 5. Guardar Archivos (Estructura Multi-tenant Estandarizada)
        year_folder = str(datetime.now().year)
        
        doc_creado = None # Para devolver ID si se crea
        
        if notif.empresa_id:
            # CASO A: Vinculada a Empresa -> Guardar en 'Por Procesar' y crear Documento
            empresa = Empresa.query.get(notif.empresa_id)
            base_dir = get_empresa_storage_path(gestoria.id, empresa.nombre)
            
            # Usar constante DocumentCategories.POR_PROCESAR (generalmente "Por Procesar")
            dest_dir = os.path.join(base_dir, DocumentCategories.POR_PROCESAR)
        else:
            # CASO B: No vinculada -> Inbox (Raíz para que sea visible en 'No Clasificados')
            # No usamos subcarpeta 'dehu/{year}' para asegurar que el scanner de inbox lo vea
            base_dir = get_gestoria_inbox_path(gestoria.id)
            dest_dir = base_dir
            
        os.makedirs(dest_dir, exist_ok=True)

        if anexo:
            # Definir ruta del archivo (Bug fix: variable no definida)
            filename = getattr(anexo, 'filename', f"{ref}.pdf")
            if not filename or filename == '': filename = f"{ref}.pdf"
            anexo_path = os.path.join(dest_dir, os.path.basename(filename))
            
            anexo.save(anexo_path)
            notif.file_path = anexo_path
            notif.upload_status = 'UPLOADED'
            logger.info(f"Anexo guardado: {anexo_path}")
            
            # ⭐ CLASIFICACIÓN AUTOMÁTICA (Reglas por Plantilla)
            categoria_doc = DocumentCategories.POR_PROCESAR
            procesado_doc = False
            datos_extraidos = {
                'origen': 'dehu',
                'referencia_dehu': ref,
                'titulo': notif.titulo
            }
            
            try:
                extractor = NotificacionExtractor()
                plantilla_detectada = extractor.detectar_plantilla(anexo_path)
                
                if plantilla_detectada and plantilla_detectada.categoria_default:
                    # Mover a la carpeta definitiva según la plantilla
                    nueva_categoria = plantilla_detectada.categoria_default
                    logger.info(f"✨ Clasificación automática: {plantilla_detectada.nombre} -> {nueva_categoria}")
                    
                    # Calcular destino final
                    if notif.empresa_id:
                        empresa = Empresa.query.get(notif.empresa_id)
                        base_dir = get_empresa_storage_path(gestoria.id, empresa.nombre)
                        final_dest_dir = os.path.join(base_dir, nueva_categoria)
                        os.makedirs(final_dest_dir, exist_ok=True)
                        
                        final_path = os.path.join(final_dest_dir, os.path.basename(anexo_path))
                        
                        # Mover físico
                        if final_path != anexo_path:
                            shutil.move(anexo_path, final_path)
                            anexo_path = final_path
                            notif.file_path = anexo_path
                            
                        categoria_doc = nueva_categoria
                        procesado_doc = True # Ya está clasificado
                        datos_extraidos['plantilla_auto'] = plantilla_detectada.codigo
                        if plantilla_detectada.departamento_default:
                            datos_extraidos['departamento_auto'] = plantilla_detectada.departamento_default
                        
            except Exception as classify_err:
                logger.error(f"Error en clasificación automática: {classify_err}")
                # No interrumpir el upload si falla la clasificación
            
            # ⭐ CREAR DOCUMENTO SI ESTÁ VINCULADA A EMPRESA
            if notif.empresa_id:
                try:
                    # Calcular hash
                    file_hash = get_file_hash(anexo_path)
                    
                    # Verificar si ya existe el documento (por hash o nombre en esa empresa)
                    doc_existe = Documento.query.filter_by(
                        empresa_id=notif.empresa_id,
                        file_hash=file_hash
                    ).first()
                    
                    if not doc_existe:
                        # Crear Documento
                        nuevo_doc = Documento(
                            empresa_id=notif.empresa_id,
                            gestoria_id=gestoria.id,
                            categoria=categoria_doc,
                            nombre_archivo=os.path.basename(anexo_path),
                            ruta_archivo=anexo_path,
                            procesado=procesado_doc,
                            file_hash=file_hash,
                            fecha_creacion=datetime.utcnow(),
                            datos_extraidos=datos_extraidos
                        )
                        db.session.add(nuevo_doc)
                        db.session.flush() # Para obtener ID
                        doc_creado = nuevo_doc.id
                        logger.info(f"Documento creado (ID: {doc_creado}) para notificación {ref} en categoría {categoria_doc}")

                        # Notificar al departamento correspondiente
                        from routes_notificaciones import notificar
                        dept_notif = "Administrativo"
                        if plantilla_detectada and plantilla_detectada.departamento_default:
                            dept_notif = plantilla_detectada.departamento_default

                        notificar(
                            titulo="Nueva Notificación (Sync)", 
                            descripcion=f"Recibida: {notif.titulo} para {empresa.nombre}. Clasificada como: {categoria_doc}",
                            gestoria_id=gestoria.id,
                            departamento=dept_notif,
                            link=f"/empresa/{notif.empresa_id}/{categoria_doc}",
                            tipo="success"
                        )
                    else:
                        logger.info(f"Documento ya existe para notificación {ref} (ID: {doc_existe.id})")
                        doc_creado = doc_existe.id
                        
                except Exception as doc_err:
                    logger.error(f"Error creando Documento para notificación {ref}: {doc_err}")
                    # No fallar el upload completo, solo loguear error

        if resguardo:
            resguardo_path = os.path.join(dest_dir, f"{ref}_voucher.pdf")
            resguardo.save(resguardo_path)
            logger.info(f"Resguardo guardado: {resguardo_path}")

        db.session.commit()
        
        # Obtener límite real del plan de facturación
        from models_billing import Suscripcion
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria.id).first()
        limit = suscripcion.plan.certificados_max if (suscripcion and suscripcion.plan) else gestoria.max_certificados

        if limit == -1 or limit is None:
            limit = "ilimitado"

        res_data = {
            'success': True, 
            'id': notif.id, 
            'status': notif.upload_status,
            'reference': ref,
            'plan_name': gestoria.plan,
            'max_certificates': limit
        }
        
        response = jsonify(res_data)
        response.headers['X-Plan-Name'] = gestoria.plan
        response.headers['X-Plan-Limit'] = str(limit)
        
        return response, 200

    except Exception as e:
        logger.error(f"Error crítico en sincronización DEHú: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@dehu_sync_bp.route('/api/dehu-sync/credentials', methods=['GET'])
@login_required
def get_sync_credentials():
    """Retorna la API Key de la gestoría del usuario."""
    rol_nombre = current_user.rol.nombre if current_user.rol else "Sin Rol"
    logger.info(f"Checking credentials for User: {current_user.id}, Role: {rol_nombre}, Super: {current_user.is_super_admin}")

    # Permisividad en roles: SuperAdmin or any role containing 'Jefatura' or 'Admin'
    is_authorized = (
        current_user.is_super_admin or 
        (current_user.rol and (
            'jefe' in current_user.rol.nombre.lower() or 
            'admin' in current_user.rol.nombre.lower() or
            'jefatura' in current_user.rol.nombre.lower()
        ))
    )

    if not is_authorized:
        logger.warning(f"Unauthorized sync credentials access attempt: {current_user.id} (Role: {rol_nombre})")
        return jsonify({'error': f'Unauthorized. Your role ({rol_nombre}) does not have Jefatura permissions.'}), 403
    
    from models import Gestoria
    gestoria = Gestoria.query.get(current_user.gestoria_id)
    if not gestoria:
        logger.error(f"Gestoría {current_user.gestoria_id} not found for user {current_user.id}")
        return jsonify({'error': 'Gestoría not found'}), 404
        
    return jsonify({
        'api_key': gestoria.api_key,
        'nombre_gestoria': gestoria.nombre
    })

@dehu_sync_bp.route('/api/dehu-sync/rotate-key', methods=['POST'])
@login_required
def rotate_sync_key():
    """Genera una nueva API Key para la gestoría."""
    is_authorized = (
        current_user.is_super_admin or 
        (current_user.rol and (
            'jefe' in current_user.rol.nombre.lower() or 
            'admin' in current_user.rol.nombre.lower()
        ))
    )

    if not is_authorized:
        return jsonify({'error': 'Unauthorized'}), 403
        
    from models import Gestoria
    import secrets
    
    gestoria = Gestoria.query.get(current_user.gestoria_id)
    if not gestoria:
        return jsonify({'error': 'Gestoría not found'}), 404

    new_key = f"JS-{secrets.token_hex(16)}" 
    gestoria.api_key = new_key
    db.session.commit()
    
    return jsonify({'success': True, 'api_key': new_key})

@dehu_sync_bp.route('/api/dehu-sync/download-app', methods=['GET'])
@login_required
def download_sync_app():
    """Retorna la URL del instalador de la app de escritorio configurado por el Super Admin."""
    from models import ConfiguracionGlobal
    from flask import jsonify
    
    config_url = ConfiguracionGlobal.query.filter_by(clave='conecta_url').first()
    
    if config_url and config_url.valor:
        return jsonify({'success': True, 'url': config_url.valor})
        
    return jsonify({'error': 'URL de descarga no configurada en el sistema'}), 404

@dehu_sync_bp.route('/api/dehu-sync/check/<reference>', methods=['GET'])
def check_status(reference):
    """Verifica el estado de una notificación"""
    notif = NotificacionDehu.query.filter_by(referencia=reference).first()
    if not notif:
        return jsonify({'exists': False}), 404
    
    return jsonify({
        'exists': True,
        'status': notif.upload_status,
        'empresa_id': notif.empresa_id
    })

@dehu_sync_bp.route('/api/dehu-sync/pending', methods=['GET'])
def get_pending_notifications():
    """
    Lista las notificaciones que están pendientes de subir archivos.
    Utilizado por el SyncManager para auto-reintentar fallos.
    """
    api_key = request.headers.get('X-Gestoria-Key')
    if not api_key:
        return jsonify({'error': 'X-Gestoria-Key required'}), 401
    
    from models import Gestoria
    gestoria = Gestoria.query.filter_by(api_key=api_key).first()
    if not gestoria:
        return jsonify({'error': 'Invalid API Key'}), 403
    
    # Buscar notificaciones PENDING o ERROR para esta gestoría
    pending = NotificacionDehu.query.filter(
        NotificacionDehu.gestoria_id == gestoria.id,
        NotificacionDehu.upload_status.in_(['PENDING', 'ERROR'])
    ).all()
    
    return jsonify({
        'count': len(pending),
        'items': [n.to_dict() for n in pending]
    })
