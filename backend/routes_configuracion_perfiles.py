from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import ConfiguracionPerfil, Documento
from constants import DocumentCategories, Departments, NotificationTypes
import logging
from datetime import datetime

config_perfiles_bp = Blueprint('config_perfiles', __name__)
logger = logging.getLogger(__name__)

@config_perfiles_bp.route('/api/configuracion-perfiles', methods=['GET'])
@login_required
def get_configuraciones():
    """
    Obtiene las configuraciones de perfiles para la gestoría actual.
    También devuelve las opciones disponibles de categorías y departamentos.
    """
    try:
        gestoria_id = current_user.gestoria_id
        if not gestoria_id:
             return jsonify({NotificationTypes.ERROR: "Usuario sin gestoría asignada"}), 400

        from models import TipoDocumentoConfig
        
        # 1. Configuraciones dinámicas y auto-creadas
        configs = ConfiguracionPerfil.query.filter_by(gestoria_id=gestoria_id).all()
        configs_dict = {c.perfil_clave: c.to_dict() for c in configs}

        # 2. Configuraciones estáticas (TipoDocumentoConfig)
        static_configs = TipoDocumentoConfig.query.filter_by(gestoria_id=gestoria_id).all()
        for sc in static_configs:
            configs_dict[sc.codigo] = {
                'perfil_clave': sc.codigo,
                'categoria': sc.categoria_default,
                'departamento': sc.departamento_default,
                'prioridad_default': getattr(sc, 'prioridad_default', 'informativa'),
                'notificar_cliente': sc.notificar_cliente,
                'activo': sc.activo
            }

        return jsonify({
            'configuraciones': configs_dict,
            'opciones': {
                'categorias': DocumentCategories.all(),
                'departamentos': Departments.all()
            }
        }), 200

    except Exception as e:
        logger.error(f"Error obteniendo configuraciones perfiles: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@config_perfiles_bp.route('/api/configuracion-perfiles', methods=['POST'])
@login_required
def save_configuracion():
    """
    Guarda o actualiza la configuración de un perfil específico.
    Body: { perfil_clave, categoria, departamento, notificar_cliente, activo }
    """
    try:
        data = request.json
        gestoria_id = current_user.gestoria_id
        if not gestoria_id:
             return jsonify({NotificationTypes.ERROR: "Usuario sin gestoría asignada"}), 400

        perfil_clave = data.get('perfil_clave')
        if not perfil_clave:
            return jsonify({NotificationTypes.ERROR: "Falta perfil_clave"}), 400

        # ─────────────────────────────────────────────────────────────────
        # SABER SI ES UN PERFIL ESTÁTICO (TipoDocumentoConfig)
        # ─────────────────────────────────────────────────────────────────
        from routes_tipos_documento import TIPOS_PREDEFINIDOS
        from models import TipoDocumentoConfig
        
        es_estatico = any(t['codigo'] == perfil_clave for t in TIPOS_PREDEFINIDOS)

        if es_estatico:
            config_estatica = TipoDocumentoConfig.query.filter_by(
                gestoria_id=gestoria_id, 
                codigo=perfil_clave
            ).first()

            if not config_estatica:
                # Fallback: crear si por alguna razón no existe (aunque suele auto-crearse)
                config_estatica = TipoDocumentoConfig(gestoria_id=gestoria_id, codigo=perfil_clave)
                db.session.add(config_estatica)

            if 'categoria' in data:
                if data['categoria'] and not DocumentCategories.is_valid(data['categoria']):
                    return jsonify({NotificationTypes.ERROR: "Categoría inválida"}), 400
                config_estatica.categoria_default = data['categoria']
                
            if 'prioridad_default' in data:
                config_estatica.prioridad_default = data['prioridad_default']

            if 'departamento' in data:
                if data['departamento'] and not Departments.is_valid(data['departamento']):
                    return jsonify({NotificationTypes.ERROR: "Departamento inválido"}), 400
                config_estatica.departamento_default = data['departamento']

            if 'notificar_cliente' in data:
                config_estatica.notificar_cliente = bool(data['notificar_cliente'])
                
            if 'activo' in data:
                config_estatica.activo = bool(data['activo'])

            config_estatica.actualizado_por_id = current_user.id
            config_estatica.fecha_actualizacion = datetime.utcnow()
            
            # Limpiar nombre_display estático (no se guarda en TipoDocumentoConfig)
            response_dict = config_estatica.to_dict()
            db.session.commit()
            return jsonify({
                NotificationTypes.SUCCESS: True, 
                'configuracion': response_dict
            }), 200

        # ─────────────────────────────────────────────────────────────────
        # SINO: ES UN PERFIL DINÁMICO/AUTO (ConfiguracionPerfil)
        # ─────────────────────────────────────────────────────────────────
        
        # Buscar existente o crear nuevo
        config = ConfiguracionPerfil.query.filter_by(
            gestoria_id=gestoria_id, 
            perfil_clave=perfil_clave
        ).first()

        if not config:
            config = ConfiguracionPerfil(
                gestoria_id=gestoria_id,
                perfil_clave=perfil_clave
            )
            db.session.add(config)

        # Actualizar campos
        if 'categoria' in data:
            if data['categoria'] and not DocumentCategories.is_valid(data['categoria']):
                return jsonify({NotificationTypes.ERROR: "Categoría inválida"}), 400
            config.categoria = data['categoria']
            
        if 'prioridad_default' in data:
            config.prioridad_default = data['prioridad_default']
            
        if 'departamento' in data:
            if data['departamento'] and not Departments.is_valid(data['departamento']):
                return jsonify({NotificationTypes.ERROR: "Departamento inválido"}), 400
            config.departamento = data['departamento']

        if 'notificar_cliente' in data:
            config.notificar_cliente = bool(data['notificar_cliente'])
            
        if 'activo' in data:
            config.activo = bool(data['activo'])

        # Actualizar nombre_display si se envía
        if 'nombre_display' in data:
            try:
                config.nombre_display = data['nombre_display']
            except Exception:
                pass  # Campo puede no existir aún en BD legacy

        config.actualizado_por_id = current_user.id
        config.fecha_actualizacion = datetime.utcnow()

        db.session.commit()

        return jsonify({
            NotificationTypes.SUCCESS: True, 
            'configuracion': config.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error guardando configuracion perfil: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@config_perfiles_bp.route('/api/configuracion-perfiles/auto-detectar', methods=['POST'])
@login_required
def auto_detectar_y_crear_perfil():
    """
    Dado un documento sin perfil coincidente, activa el OCR si es necesario,
    lee el contenido, detecta emisor + tipo de documento, y crea automáticamente
    un ConfiguracionPerfil (sin destino todavía) para que el usuario lo configure.

    Body: { doc_id: int }
    Returns: { perfil_clave, nombre, icono, es_nuevo, pendiente_destino, ... }
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        gestoria_id = current_user.gestoria_id

        if not doc_id:
            return jsonify({NotificationTypes.ERROR: "Falta doc_id"}), 400

        # Seguridad multitenant
        doc = Documento.query.filter_by(
            id=doc_id,
            gestoria_id=gestoria_id
        ).first()

        if not doc:
            return jsonify({NotificationTypes.ERROR: "Documento no encontrado"}), 404

        # Si el documento no tiene texto OCR, activar extracción primero
        if not doc.texto_ocr or len(doc.texto_ocr.strip()) < 50:
            logger.info(f"🔍 Doc {doc_id} sin texto OCR — lanzando extracción OCR automática")
            try:
                from celery_worker import procesar_documento_async
                task = procesar_documento_async.delay(doc_id, 'notificacion_generica')
                # Esperar resultado breve (hasta 15s) para tener el texto
                result = task.get(timeout=15, propagate=False)
                # Recargar el documento desde BD para obtener texto actualizado
                db.session.refresh(doc)
            except Exception as e_celery:
                logger.warning(f"OCR no disponible en este momento: {e_celery}")

        # Detectar y crear perfil
        from services.auto_profile_detector import auto_crear_perfil
        info = auto_crear_perfil(doc, gestoria_id, user_id=current_user.id)

        if info.get('error'):
            return jsonify({
                NotificationTypes.WARNING: True,
                'mensaje': info['error'],
                'necesita_ocr': True
            }), 200

        return jsonify({
            NotificationTypes.SUCCESS: True,
            'perfil': {
                'clave': info['perfil_clave'],
                'nombre': info['nombre'],
                'icono': info['icono'],
                'emisor': info['emisor'],
                'tipo_detectado': info['tipo'],
                'es_nuevo': info['es_nuevo'],
                'pendiente_destino': info['pendiente_destino'],
                'categoria_actual': info.get('categoria_actual'),
                'departamento_actual': info.get('departamento_actual'),
            }
        }), 200

    except Exception as e:
        logger.error(f"Error en auto-detectar perfil: {e}", exc_info=True)
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
