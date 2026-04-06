# backend/routes_documento_detect.py
"""
Endpoint para detectar el perfil de extracción sugerido para un documento.
Usa el texto_ocr almacenado y llama al método matches() de cada perfil.
"""
from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from models import Documento, db

detectar_bp = Blueprint('detectar_bp', __name__)

# Nombres amigables para mostrar en el frontend y claves de BD (TIPOS_PREDEFINIDOS)
PROFILE_DISPLAY = {
    'ProvidenciaApremioProfile':              {'nombre': 'Providencia de Apremio',            'icono': '⚖️',  'color': 'red', 'codigo': 'providencia_apremio'},
    'ResolucionAltasBajasProfile':            {'nombre': 'Resolución Altas/Bajas Trabajadores','icono': '📋',  'color': 'blue', 'codigo': 'resolucion_altas_bajas'},
    'ReintegroRetaProfile':                   {'nombre': 'Reintegro Regularización RETA',      'icono': '💰',  'color': 'green', 'codigo': 'reintegro_reta'},
    'CapturaPrecintosVehiculosProfile':       {'nombre': 'Captura y Precinto de Vehículos',   'icono': '🚗',  'color': 'orange', 'codigo': 'captura_hacienda_vehiculos'},
    'EmbargoVehiculosProfile':                {'nombre': 'Embargo de Vehículos (TVA-391)',    'icono': '🚗',  'color': 'orange', 'codigo': 'embargo_vehiculos'},
    'EmbargoCuentasProfile':                  {'nombre': 'Embargo de Cuentas Bancarias',       'icono': '🏦',  'color': 'purple', 'codigo': 'embargo_cuentas'},
    'LevantamientoEmbargoCuentaProfile':      {'nombre': 'Levantamiento de Embargo',           'icono': '✅',  'color': 'green', 'codigo': 'levantamiento_embargo'},
    'RequerimientoBienesProfile':             {'nombre': 'Requerimiento de Bienes',            'icono': '📝',  'color': 'yellow', 'codigo': 'requerimiento_bienes'},
    'RegularizacionRetaDevolucionProfile':    {'nombre': 'Regularización RETA (A Devolver)',   'icono': '↩️',  'color': 'green', 'codigo': 'regularizacion_reta_devolver'},
    'RegularizacionRetaIngresoProfile':       {'nombre': 'Regularización RETA (A Ingresar)',  'icono': '💳',  'color': 'red', 'codigo': 'regularizacion_reta_ingresar'},
}


@detectar_bp.route('/api/documentos/<int:doc_id>/detectar-perfil', methods=['GET'])
@login_required
def detectar_perfil(doc_id):
    """
    Analiza el texto OCR del documento y devuelve el perfil de extracción
    que mejor coincide, para sugerirlo al usuario en la Mesa de Trabajo.
    """
    from services.extraction_profiles.notification_profiles import PROFILES

    # Seguridad multi-tenant
    gestoria_id = getattr(current_user, 'gestoria_id', None)
    doc = db.session.query(Documento).filter_by(id=doc_id, gestoria_id=gestoria_id).first()

    if not doc:
        return jsonify({'error': 'Documento no encontrado'}), 404

    if not doc.texto_ocr or not doc.texto_ocr.strip():
        # AUTO-HEALING: Si no hay texto OCR, intentamos extraerlo al vuelo
        try:
            import fitz  # PyMuPDF
            import os
            
            # Verificar ruta
            if not doc.ruta_archivo or not os.path.exists(doc.ruta_archivo):
                return jsonify({'perfil': None, 'motivo': 'archivo_no_encontrado'}), 200

            # Extraer texto rápido
            pdf_document = fitz.open(doc.ruta_archivo)
            text_parts = []
            for page in pdf_document:
                text_parts.append(page.get_text())
            pdf_document.close()
            
            full_text = "\n".join(text_parts)
            
            # Guardar en BD para la próxima (Auto-fix)
            if full_text.strip():
                doc.texto_ocr = full_text
                db.session.commit()
                texto = full_text
            else:
                return jsonify({'perfil': None, 'motivo': 'pdf_sin_texto'}), 200
                
        except Exception as e:
            print(f"Error en auto-healing OCR: {e}")
            return jsonify({'perfil': None, 'motivo': 'error_extraccion'}), 200
    else:
        texto = doc.texto_ocr

    # -- 1. PERFILES ESTÁTICOS (Python) --
    for profile in PROFILES:
        if profile.matches(texto):
            clase = type(profile).__name__
            info = PROFILE_DISPLAY.get(clase, {'nombre': clase, 'icono': '📄', 'color': 'gray', 'codigo': clase})
            return jsonify({
                'perfil': {
                    'clase': info['codigo'], # Usamos el codigo como 'clase' para que coincida con DB
                    'nombre': info['nombre'],
                    'icono': info['icono'],
                    'color': info['color'],
                    'tipo_documento': getattr(profile, 'tipo_documento', ''),
                }
            }), 200

    # -- 2. PERFILES DINÁMICOS (BD - Motor Declarativo) --
    try:
        from services.declarative_extraction_engine import DeclarativeExtractionEngine, DatabaseProfileStore
        from extensions import db as _db
        store = DatabaseProfileStore(_db.session)
        engine = DeclarativeExtractionEngine(store)
        json_profile = engine.detect_profile(texto)
        if json_profile:
            return jsonify({
                'perfil': {
                    'clase': f"dynamic::{json_profile.get('id')}",
                    'nombre': json_profile.get('nombre', 'Perfil Dinámico'),
                    'icono': '⚡',
                    'color': 'amber',
                    'tipo_documento': json_profile.get('nombre', ''),
                    'dinamico': True,
                    'perfil_id': json_profile.get('id'),
                }
            }), 200
    except Exception as e:
        print(f"Error en motor declarativo (detectar_perfil): {e}")

    # -- 3. PERFILES AUTO-CREADOS por OCR (Globales) --
    try:
        from services.auto_profile_detector import detectar_emisor, detectar_tipo_documento, _slugify
        from models import ExtractionTemplate, ConfiguracionPerfil
        emisor_codigo, emisor_nombre = detectar_emisor(texto)
        tipo_clave, tipo_nombre = detectar_tipo_documento(texto)
        perfil_clave_auto = f"auto_{_slugify(emisor_codigo)}_{_slugify(tipo_clave)}"

        # Solo proceder si detectamos algo concreto (no el fallback genérico)
        if tipo_clave != 'notificacion_generica' or emisor_codigo != 'DESCONOCIDO':
            # 3a. Buscar match exacto en templates globales
            tpl = ExtractionTemplate.query.get(perfil_clave_auto)
            
            # 3b. Si no hay match exacto, buscar entre todos los auto_* disponibles
            if not tpl:
                todos_tpls = ExtractionTemplate.query.filter(ExtractionTemplate.id.like('auto_%')).all()
                slug_emisor = _slugify(emisor_codigo)
                slug_tipo = _slugify(tipo_clave)
                for t in todos_tpls:
                    if slug_emisor in t.id or slug_tipo in t.id:
                        tpl = t
                        perfil_clave_auto = t.id
                        break

            if tpl:
                # Buscar si la gestoria ya tiene config para este perfil global
                config_local = ConfiguracionPerfil.query.filter_by(
                    gestoria_id=current_user.gestoria_id,
                    perfil_clave=perfil_clave_auto
                ).first()
                
                nombre = (config_local.nombre_display if config_local and getattr(config_local, 'nombre_display', None) else None) or \
                         tpl.nombre or f"{tipo_nombre} — {emisor_nombre}"
                
                print(f"[detectar-perfil] ✅ Perfil global encontrado: {perfil_clave_auto} → {nombre}")
                return jsonify({
                    'perfil': {
                        'clase': perfil_clave_auto,
                        'nombre': nombre,
                        'icono': '🔍',
                        'color': 'violet',
                        'tipo_documento': tipo_nombre,
                        'auto_creado': True,
                        'configurado': bool(config_local and config_local.categoria and config_local.departamento),
                    }
                }), 200
            else:
                print(f"[detectar-perfil] ℹ️ No hay auto-perfil global para: {perfil_clave_auto} (emisor={emisor_codigo}, tipo={tipo_clave})")
    except Exception as e:
        print(f"Error buscando perfil auto-creado global: {e}", flush=True)

    return jsonify({'perfil': None, 'motivo': 'sin_coincidencia'}), 200




@detectar_bp.route('/api/perfiles-sistema', methods=['GET'])
@login_required
def listar_perfiles_sistema():
    """
    Devuelve la lista de perfiles de sistema disponibles con su configuración personalizada.
    """
    from services.extraction_profiles.notification_profiles import PROFILES
    
    # Obtener configuraciones personalizadas de la gestoría
    configs_map = {}
    if getattr(current_user, 'gestoria_id', None):
        from models import ConfiguracionPerfil, TipoDocumentoConfig
        try:
            # 1. Configuraciones dinámicas y auto-creadas
            configs = ConfiguracionPerfil.query.filter_by(gestoria_id=current_user.gestoria_id).all()
            for c in configs:
                configs_map[c.perfil_clave] = {
                    'categoria': c.categoria,
                    'departamento': c.departamento,
                    'notificar_cliente': c.notificar_cliente,
                    'activo': c.activo,
                    'prioridad_default': getattr(c, 'prioridad_default', 'informativa')
                }
            
            # 2. Configuraciones estáticas (TipoDocumentoConfig)
            static_configs = TipoDocumentoConfig.query.filter_by(gestoria_id=current_user.gestoria_id).all()
            for sc in static_configs:
                configs_map[sc.codigo] = {
                    'categoria': sc.categoria_default,
                    'departamento': sc.departamento_default,
                    'notificar_cliente': sc.notificar_cliente,
                    'activo': sc.activo,
                    'prioridad_default': getattr(sc, 'prioridad_default', 'informativa')
                }
        except Exception as e:
            print(f"Error cargando configs: {e}")

    lista = []
    for profile in PROFILES:
        clase_base = type(profile).__name__
        info = PROFILE_DISPLAY.get(clase_base, {'nombre': clase_base, 'icono': '📄', 'color': 'gray', 'codigo': clase_base})
        clase = info['codigo']
        
        # Configuración
        config = configs_map.get(clase)
        
        lista.append({
            'clase': clase,
            'nombre': info['nombre'],
            'icono': info['icono'],
            'color': info['color'],
            'descripcion': getattr(profile, 'tipo_documento', '') or info['nombre'],
            'configuracion': {
                'categoria': config['categoria'] if config else None,
                'departamento': config['departamento'] if config else None,
                'notificar_cliente': config['notificar_cliente'] if config else False,
                'prioridad_default': config.get('prioridad_default', 'informativa') if config else 'informativa',
                'activo': config['activo'] if config and 'activo' in config else True
            }
        })
    
    # -- Perfiles DINÁMICOS desde BD --
    try:
        from models import ExtractionTemplate
        plantillas = ExtractionTemplate.query.filter_by(activo=True).all()
        for t in plantillas:
            lista.append({
                'clase': f"dynamic::{t.id}",
                'nombre': t.nombre,
                'icono': '⚡',
                'color': 'amber',
                'descripcion': f"Motor Dinámico — {t.idioma_principal.upper()}",
                'dinamico': True,
                'configuracion': {
                    'categoria': None,
                    'departamento': None,
                    'notificar_cliente': False,
                    'activo': True
                }
            })
    except Exception as e:
        print(f"Error cargando plantillas dinámicas: {e}")

    # -- Perfiles AUTO-CREADOS (detectados por OCR) --
    try:
        from models import ConfiguracionPerfil
        todos_configs = ConfiguracionPerfil.query.filter_by(
            gestoria_id=current_user.gestoria_id
        ).all()
        auto_perfiles = [ap for ap in todos_configs if ap.perfil_clave.startswith('auto_')]
        
        # Nombres de perfiles estáticos para evitar duplicados
        nombres_estaticos = [info['nombre'] for info in PROFILE_DISPLAY.values()]
        
        for ap in auto_perfiles:
            nombre = getattr(ap, 'nombre_display', None) or ap.perfil_clave.replace('auto_', '').replace('_', ' ').title()
            
            # Saltar si este perfil auto-creado tiene el mismo nombre que un estático
            if nombre in nombres_estaticos:
                continue
                
            lista.append({
                'clase': ap.perfil_clave,
                'nombre': nombre,
                'icono': '🔍',
                'color': 'violet',
                'descripcion': 'Perfil detectado automáticamente por OCR',
                'auto_creado': True,
                'configuracion': {
                    'categoria': ap.categoria,
                    'departamento': ap.departamento,
                    'notificar_cliente': ap.notificar_cliente if ap.notificar_cliente is not None else False,
                    'activo': ap.activo if ap.activo is not None else True
                }
            })
    except Exception as e:
        print(f"Error cargando perfiles auto-creados: {e}")

    return jsonify({'perfiles': lista}), 200

