# backend/routes_tipos_documento.py
"""
Endpoints para gestión de Tipos de Documento predefinidos.
Los tipos de documento son perfiles de código (no BD), pero su configuración
(categoría destino, departamento, notificación) sí se guarda en BD.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import TipoDocumentoConfig
from utils.logger import logger

tipos_documento_bp = Blueprint('tipos_documento', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# Tipos de documento predefinidos (definidos en código, no en BD)
# ─────────────────────────────────────────────────────────────────────────────
TIPOS_PREDEFINIDOS = [
    {
        'codigo': 'providencia_apremio',
        'nombre': 'Providencia de Apremio',
        'descripcion': 'Notificación de inicio de procedimiento de apremio por deuda tributaria',
        'organismo': 'AEAT / Seguridad Social',
        'patron_deteccion': 'PROVIDENCIA DE APREMIO',
        'campos_extraidos': [
            'referencia', 'fecha', 'importe', 'importe_principal',
            'importe_recargo', 'nif', 'providencia_numero', 'csv', 'periodo'
        ],
        'activo': True,
    },
    {
        'codigo': 'resolucion_altas_bajas',
        'nombre': 'Resolución Altas/Bajas Trabajadores',
        'descripcion': 'Resolución de la TGSS sobre reconocimiento de altas y bajas de trabajadores en la Seguridad Social',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'RESOLUCIÓN SOBRE RECONOCIMIENTO DE ALTAS',
        'campos_extraidos': [
            'razon_social', 'ccc', 'regimen', 'fecha',
            'id_cea', 'codigo_cea', 'trabajadores'
        ],
        'activo': True,
    },
    {
        'codigo': 'reintegro_reta',
        'nombre': 'Reintegro Regularización RETA',
        'descripcion': 'Comunicación de reintegro de la regularización anual del RETA/RETA Mar. (autónomos)',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'REINTEGRO DE LA REGULARIZACIÓN DEL RETA',
        'campos_extraidos': [
            'expediente', 'num_documento', 'fecha', 'tipo_identificador',
            'regimen', 'nif', 'nombre', 'importe', 'titular', 'iban', 'forma_pago'
        ],
        'activo': True,
    },
    {
        'codigo': 'embargo_vehiculos',
        'nombre': 'Embargo de Vehículos (TVA-391)',
        'descripcion': 'Notificación de diligencia de embargo de vehículos a la Jefatura Provincial de Tráfico',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'TVA-391',
        'campos_extraidos': [
            'razon_social', 'nif', 'expediente', 'num_referencia', 'fecha',
            'importe_total', 'importe_principal', 'importe_recargo',
            'importe_intereses', 'importe_costas', 'vehiculos', 'iban', 'csv'
        ],
        'activo': True,
    },
    {
        'codigo': 'levantamiento_embargo_cuenta',
        'nombre': 'Levantamiento Embargo Cuenta Bancaria (TVA-350)',
        'descripcion': 'Notificación al deudor de levantamiento parcial de embargo de cuenta bancaria',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'TVA-350',
        'campos_extraidos': [
            'nif', 'razon_social', 'expediente', 'num_documento', 'fecha',
            'importe_deuda_pendiente', 'cuentas', 'csv'
        ],
        'activo': True,
    },
    {
        'codigo': 'captura_precinto_vehiculos',
        'nombre': 'Captura, Depósito y Precinto de Vehículos (TVA-336)',
        'descripcion': 'Solicitud de captura, depósito y precinto de vehículos embargados a la Jefatura de Tráfico',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'TVA-336',
        'campos_extraidos': [
            'nif', 'razon_social', 'expediente', 'num_documento', 'fecha',
            'importe_deuda', 'destinatario', 'vehiculos', 'referencia_verificacion'
        ],
        'activo': True,
    },
    {
        'codigo': 'embargo_cuentas',
        'nombre': 'Embargo de Cuentas Corrientes y de Ahorro (TVA-313)',
        'descripcion': 'Notificación de diligencia de embargo de cuentas corrientes y de ahorro',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'TVA-313',
        'campos_extraidos': [
            'razon_social', 'nif', 'expediente', 'num_documento', 'fecha',
            'cuentas', 'importe_principal', 'importe_recargo', 'importe_intereses',
            'importe_costas', 'importe_total_embargar', 'importe_embargado',
            'referencia_verificacion'
        ],
        'activo': True,
    },
    {
        'codigo': 'requerimiento_bienes',
        'nombre': 'Requerimiento de Bienes (TVA-218)',
        'descripcion': 'Requerimiento de manifestación de bienes y derechos por deudas a la Seguridad Social',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'TVA-218',
        'campos_extraidos': [
            'razon_social', 'nif', 'expediente', 'num_documento', 'fecha',
            'importe_total', 'importe_principal', 'importe_recargo',
            'importe_intereses', 'importe_costas', 'referencia_verificacion'
        ],
        'activo': True,
    },
    {
        'codigo': 'regularizacion_reta_devolucion',
        'nombre': 'Regularización RETA 2024 (Devolución)',
        'descripcion': 'Resolución de la TGSS sobre base de cotización definitiva de 2024 con resultado a devolver.',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'RESOLUCIÓN SOBRE BASE DE COTIZACIÓN DEFINITIVA',
        'campos_extraidos': [
            'razon_social', 'nif', 'naf', 'fecha', 'importe_devolucion',
            'id_cea', 'codigo_cea'
        ],
        'activo': True,
    },
    {
        'codigo': 'regularizacion_reta_ingreso',
        'nombre': 'Regularización RETA 2024 (Ingreso)',
        'descripcion': 'Resolución de la TGSS sobre base de cotización definitiva de 2024 con resultado a ingresar. Incluye boletín de pago.',
        'organismo': 'Tesorería General de la Seguridad Social',
        'patron_deteccion': 'RESOLUCIÓN SOBRE BASE DE COTIZACIÓN DEFINITIVA + A INGRESAR',
        'campos_extraidos': [
            'razon_social', 'nif', 'naf', 'fecha', 'importe_ingreso',
            'entidad_financiera', 'iban', 'num_referencia',
            'id_cea', 'codigo_cea'
        ],
        'activo': True,
    },
]











def _get_gestoria_id():
    return getattr(current_user, 'gestoria_id', 1)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/tipos-documento — Listar todos los tipos con su configuración
# ─────────────────────────────────────────────────────────────────────────────
@tipos_documento_bp.route('/api/tipos-documento', methods=['GET'])
@login_required
def listar_tipos():
    gestoria_id = _get_gestoria_id()

    # Cargar configuraciones guardadas en BD
    configs_bd = {
        c.codigo: c for c in TipoDocumentoConfig.query.filter_by(gestoria_id=gestoria_id).all()
    }

    resultado = []
    for tipo in TIPOS_PREDEFINIDOS:
        config = configs_bd.get(tipo['codigo'])
        resultado.append({
            **tipo,
            'config': config.to_dict() if config else None
        })

    # ── Añadir perfiles AUTO-CREADOS por OCR (Globales + Config Local) ─────────
    try:
        from models import ConfiguracionPerfil, ExtractionTemplate
        
        # 1. Obtener todas las configuraciones locales de esta gestoría
        configs_locales = {
            cp.perfil_clave: cp for cp in ConfiguracionPerfil.query.filter_by(gestoria_id=gestoria_id).all()
        }
        
        # 2. Obtener TODOS los templates automáticos (globales)
        tpls_globales = ExtractionTemplate.query.filter(
            ExtractionTemplate.id.like('auto_%'),
            ExtractionTemplate.activo == True
        ).all()
        
        for tpl in tpls_globales:
            ap = configs_locales.get(tpl.id)
            
            # Nombre prioritario: Config Local > Template Global > Fallback
            nombre = (ap.nombre_display if ap and getattr(ap, 'nombre_display', None) else None) or \
                     tpl.nombre or \
                     tpl.id.replace('auto_', '').replace('_', ' ').title()

            # Campos y patrón desde el template global
            campos_extraidos = []
            campos_personalizados = {}
            patron_deteccion = '—'
            
            if tpl.profile_json:
                pj = tpl.profile_json
                campos_base = list(pj.get('campos', {}).keys())
                campos_extraidos = campos_base
                campos_personalizados = pj.get('campos_personalizados', {})
                
                if campos_personalizados:
                    campos_extraidos = list(set(campos_base + list(campos_personalizados.keys())))

                debe_contener = pj.get('deteccion', {}).get('debe_contener', [])
                if debe_contener:
                    patron_deteccion = ' + '.join(f'"{k}"' for k in debe_contener)

            # Obtener etiquetas base de este tipo
            from etiquetas_por_tipo import ETIQUETAS_POR_TIPO
            parts = tpl.id.replace('auto_', '').split('_', 1)
            tipo_clave = parts[1] if len(parts) > 1 else '_generico'
            base_labels_dict = ETIQUETAS_POR_TIPO.get(tipo_clave, ETIQUETAS_POR_TIPO.get('_generico', {}))

            resultado.append({
                'codigo': tpl.id,
                'nombre': nombre,
                'descripcion': 'Perfil detectado automáticamente por OCR',
                'organismo': tpl.profile_json.get('organismo', 'Detectado automáticamente') if tpl.profile_json else 'Detectado automáticamente',
                'patron_deteccion': patron_deteccion,
                'campos_extraidos': campos_extraidos,
                'base_labels': base_labels_dict,
                'boundary_tags': (ap.boundary_tags if ap else []) or (tpl.profile_json.get('boundary_tags', []) if tpl.profile_json else []),
                'activo': ap.activo if ap else True,
                'auto_creado': True,
                'icono': '🔍',
                'config': {
                    'categoria_default': ap.categoria if ap else '',
                    'prioridad_default': ap.prioridad_default if ap else '',
                    'departamento_default': ap.departamento if ap else '',
                    'notificar_cliente': ap.notificar_cliente if ap else False,
                    'activo': ap.activo if ap else True,
                    'mapeo_lineas': ap.mapeo_lineas if ap else {},
                    'campos_activos': tpl.profile_json.get('campos_activos') if tpl.profile_json else None,
                    'campos_personalizados': campos_personalizados
                }
            })
    except Exception as e:
        logger.error(f"Error cargando perfiles auto-creados globales: {e}", exc_info=True)

    # ─────────────────────────────────────────────────────────────────────────

    return jsonify({'tipos': resultado})



# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/tipos-documento/<codigo>/config — Guardar configuración de un tipo
# ─────────────────────────────────────────────────────────────────────────────
@tipos_documento_bp.route('/api/tipos-documento/<codigo>/config', methods=['PUT'])
@login_required
def guardar_config(codigo):
    gestoria_id = _get_gestoria_id()
    data = request.get_json() or {}

    # ── Perfiles AUTO-CREADOS: guardar en ConfiguracionPerfil ────────────────
    if codigo.startswith('auto_'):
        try:
            from models import ConfiguracionPerfil, ExtractionTemplate
            config_auto = ConfiguracionPerfil.query.filter_by(
                gestoria_id=gestoria_id,
                perfil_clave=codigo
            ).first()
            if config_auto:
                # Guardar campos_activos, campos_personalizados y mapeo_lineas
                campos_activos = data.get('campos_activos')
                campos_personalizados = data.get('campos_personalizados')
                mapeo_lineas = data.get('mapeo_lineas')
                
                # Actualizar ConfiguracionPerfil
                config_auto.mapeo_lineas = mapeo_lineas if mapeo_lineas is not None else config_auto.mapeo_lineas
                if 'boundary_tags' in data: 
                    config_auto.boundary_tags = data['boundary_tags']
                
                if 'categoria_default' in data: config_auto.categoria = data['categoria_default']
                if 'prioridad_default' in data: config_auto.prioridad_default = data['prioridad_default']
                if 'departamento_default' in data: config_auto.departamento = data['departamento_default']
                if 'notificar_cliente' in data: config_auto.notificar_cliente = data['notificar_cliente']
                if 'activo' in data: config_auto.activo = data['activo']

                tpl = ExtractionTemplate.query.get(codigo)
                if tpl and tpl.profile_json:
                    pj = dict(tpl.profile_json)
                    if campos_activos is not None:
                        pj['campos_activos'] = campos_activos
                    if campos_personalizados is not None:
                        pj['campos_personalizados'] = campos_personalizados
                    # También guardamos el mapeo y boundary_tags en el JSON del template por redundancia/conveniencia
                    if mapeo_lineas is not None:
                        pj['mapeo_lineas'] = mapeo_lineas
                    if 'boundary_tags' in data:
                        pj['boundary_tags'] = data['boundary_tags']
                    tpl.profile_json = pj

                db.session.commit()
                return jsonify({'success': True, 'config': config_auto.to_dict()})
        except Exception as e:
            logger.error(f"Error guardando config auto-perfil {codigo}: {e}")
        return jsonify({'error': 'Perfil no encontrado'}), 404


    # ─────────────────────────────────────────────────────────────────────────

    # Verificar que el código es válido (perfiles estáticos)
    tipo = next((t for t in TIPOS_PREDEFINIDOS if t['codigo'] == codigo), None)
    if not tipo:
        return jsonify({'error': f'Tipo de documento desconocido: {codigo}'}), 404

    config = TipoDocumentoConfig.query.filter_by(
        codigo=codigo, gestoria_id=gestoria_id
    ).first()

    if not config:
        config = TipoDocumentoConfig(codigo=codigo, gestoria_id=gestoria_id)
        db.session.add(config)

    config.categoria_default = data.get('categoria_default', '')
    config.prioridad_default = data.get('prioridad_default', '')
    config.departamento_default = data.get('departamento_default', '')
    config.notificar_cliente = bool(data.get('notificar_cliente', False))
    config.activo = bool(data.get('activo', True))

    db.session.commit()
    logger.info(f"Config guardada para tipo '{codigo}' (gestoría {gestoria_id})")

    return jsonify({'success': True, 'config': config.to_dict()})


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/tipos-documento/<codigo> — Eliminar un perfil auto-creado
# ─────────────────────────────────────────────────────────────────────────────
@tipos_documento_bp.route('/api/tipos-documento/<codigo>', methods=['DELETE'])
@login_required
def eliminar_tipo(codigo):
    gestoria_id = _get_gestoria_id()
    
    if not codigo.startswith('auto_'):
        return jsonify({'error': 'Solo se pueden eliminar perfiles detectados automáticamente'}), 400
        
    try:
        from models import ConfiguracionPerfil, ExtractionTemplate
        
        # 1. Eliminar la configuración específica de esta gestoría
        config = ConfiguracionPerfil.query.filter_by(
            gestoria_id=gestoria_id, 
            perfil_clave=codigo
        ).first()
        
        if config:
            db.session.delete(config)
            
        # 2. Verificar si otras gestorías están usando este mismo perfil base
        otras_configs = ConfiguracionPerfil.query.filter(
            ConfiguracionPerfil.perfil_clave == codigo,
            ConfiguracionPerfil.gestoria_id != gestoria_id
        ).count()
        
        # 3. Si nadie más lo usa, eliminar el template maestro para limpiar la base de datos
        if otras_configs == 0:
            tpl = ExtractionTemplate.query.get(codigo)
            if tpl:
                db.session.delete(tpl)
                
        db.session.commit()
        logger.info(f"Perfil {codigo} eliminado por gestoría {gestoria_id}")
        return jsonify({'success': True, 'message': 'Perfil eliminado correctamente'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error eliminando perfil {codigo}: {e}")
        return jsonify({'error': 'Error interno al eliminar el perfil'}), 500



# ─────────────────────────────────────────────────────────────────────────────
# GET /api/tipos-documento/<codigo>/sample-ocr — Obtener texto lineado de ejemplo
# ─────────────────────────────────────────────────────────────────────────────
@tipos_documento_bp.route('/api/tipos-documento/<codigo>/sample-ocr', methods=['GET'])
@login_required
def get_sample_ocr(codigo):
    gestoria_id = _get_gestoria_id()
    
    # 1. Buscar el último documento procesado con este perfil que tenga metadata de líneas
    from models import Documento
    from sqlalchemy import and_
    
    # Buscamos en documentos procesados de esta gestoría
    # El tipo de documento suele estar en la categoría o guardado en el JSON de datos_extraidos
    # Para perfiles auto_, buscamos documentos que tengan ese 'tipo_documento' en sus datos
    doc = Documento.query.filter(
        Documento.gestoria_id == gestoria_id,
        Documento.procesado == True,
        Documento.datos_extraidos.isnot(None)
    ).order_by(Documento.fecha_procesado.desc()).all()
    
    # Filtrar manualmente por el perfil en el JSON (ya que puede variar la categoría)
    target_doc = None
    for d in doc:
        metadata = d.datos_extraidos.get('_metadata', {})
        # Buscar en tipo_detectado (perfiles auto), tipo_documento en metadata (normales), tipo_documento en raíz, o categoría
        tipo_meta = metadata.get('tipo_detectado') or metadata.get('tipo_documento') or d.datos_extraidos.get('tipo_documento') or d.categoria
        
        # Comparación flexible: código exacto, con PROFILE: o sin el auto_
        if (tipo_meta == codigo or 
            tipo_meta == f"PROFILE:{codigo}" or 
            (codigo.startswith('auto_') and tipo_meta == codigo.replace('auto_', ''))):
            
            if 'texto_lineado' in metadata or 'has_texto_ocr' in metadata or d.texto_ocr:
                target_doc = d
                break
    
    if not target_doc:
        # Intentar búsqueda más genérica si no hay coincidencia exacta
        target_doc = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            Documento.procesado == True
        ).order_by(Documento.fecha_procesado.desc()).first()
        
    if not target_doc or not target_doc.datos_extraidos:
        return jsonify({'error': 'No se encontraron documentos procesados para mostrar ejemplo'}), 404
        
    metadata = target_doc.datos_extraidos.get('_metadata', {})
    texto_lineado = metadata.get('texto_lineado')
    
    # Si no tiene texto_lineado (documentos antiguos), generarlo al vuelo si tiene texto_ocr
    if not texto_lineado and target_doc.texto_ocr:
        lineas = target_doc.texto_ocr.splitlines()
        texto_lineado = "\n".join([f"[LINEA {i+1:03d}] {l}" for i, l in enumerate(lineas)])

    if not texto_lineado:
        return jsonify({'error': 'El documento de ejemplo no contiene texto OCR legible'}), 404
        
    return jsonify({
        'documento_id': target_doc.id,
        'nombre': target_doc.nombre_archivo,
        'texto_lineado': texto_lineado,
        'total_lineas': metadata.get('total_lineas', len(texto_lineado.splitlines()))
    })
