# backend/routes_fiscal.py
"""
Rutas API para el Sistema de Gestión Fiscal
Endpoints para subir, confirmar, listar y gestionar documentos fiscales
"""

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_
import os
from tenant_utils import get_current_gestoria_id

from extensions import db
from models_fiscal import DocumentoFiscal, TipoDocumentoFiscal, ClasificacionFiscal, EstadoDocumentoFiscal
from procesar_documentos_fiscales import procesar_documento_fiscal
from auditoria import auditar, AccionesAuditoria
from constants import NotificationTypes

# Crear Blueprint
fiscal_bp = Blueprint('fiscal', __name__, url_prefix='/api/fiscal')

# ============================================================================
# UPLOAD Y PROCESAMIENTO
# ============================================================================

@fiscal_bp.route('/upload', methods=['POST'])
@login_required
@auditar(AccionesAuditoria.DOCUMENTO_CREADO, entidad_tipo='DocumentoFiscal')
def upload_documento_fiscal():
    """
    Sube y procesa un documento fiscal con IA
    
    Form Data:
        - file: PDF del documento
        - empresa_id: ID de la empresa (opcional, se detecta automáticamente del NIF)
        
    Returns:
        JSON con documento_id y sugerencias de IA
    """
    
    # ✅ VERIFICAR LÍMITE DE ALMACENAMIENTO
    gestoria_id = get_current_gestoria_id()
    if gestoria_id:
        from services.billing_service import BillingService
        try:
            limite_storage = BillingService.verificar_limites(gestoria_id, 'storage')
            if not limite_storage['permitido']:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'Límite de almacenamiento alcanzado',
                    'limite_alcanzado': True,
                    'uso_actual': limite_storage['uso_actual'],
                    'limite': limite_storage['limite'],
                    'porcentaje': limite_storage['porcentaje'],
                    'mensaje': f"Has alcanzado el límite de almacenamiento de tu plan ({limite_storage['limite']} GB). Contacta con soporte para ampliar tu plan."
                }), 403
        except Exception as e:
            # Si falla la verificación, permitir upload (no bloquear por error del sistema)
            print(f"Error verificando límite de storage: {e}")
    
    if 'file' not in request.files:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "No se proporcionó archivo"}), 400
    
    file = request.files['file']
    empresa_id = request.form.get('empresa_id')  # Opcional
    
    if file.filename == '':
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Archivo vacío"}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Solo se permiten archivos PDF"}), 400
    
    try:
        # Guardar archivo temporalmente
        upload_folder = os.path.join(os.path.dirname(__file__), 'storage', 'fiscal_temp')
        os.makedirs(upload_folder, exist_ok=True)
        
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Si no se proporcionó empresa_id, detectar con regex (como sistema general)
        if not empresa_id:
            # Extraer texto del PDF
            from services.notificacion_extractor import NotificacionExtractor
            extractor = NotificacionExtractor()
            texto = extractor.extract_text_from_pdf(filepath)
            
            # Buscar NIF con regex (mismo método que app.py)
            import re
            
            def _find_nif_with_regex(text):
                """Busca NIF/CIF en el texto usando regex"""
                if not text:
                    return None
                # Patrones para NIF/CIF español:
                # CIF: Letra + 8 dígitos (ej: B67246785)
                # NIF: 8 dígitos + Letra (ej: 12345678A)
                # NIE: Letra + 7 dígitos + Letra (ej: X1234567A)
                patterns = [
                    r'\b[A-Z]\d{8}\b',           # CIF: B67246785
                    r'\b\d{8}[A-Z]\b',           # NIF: 12345678A
                    r'\b[XYZ]\d{7}[A-Z]\b'       # NIE: X1234567A
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text.upper())
                    if matches:
                        return matches[0]
                return None
            
            nif = _find_nif_with_regex(texto)
            
            if nif:
                # Limpiar NIF
                nif_clean = re.sub(r'[\s\.-]', '', nif.strip().upper()).lstrip("ES").lstrip("0")[:9]
                
                # Buscar empresa por NIF o alias
                from models import Empresa, AliasNIF
                alias = AliasNIF.query.filter_by(nif=nif_clean).first()
                emp = alias.empresa if alias else Empresa.query.filter_by(nif=nif_clean, gestoria_id=get_current_gestoria_id()).first()
                
                if emp:
                    empresa_id = emp.id
                else:
                    return jsonify({
                        NotificationTypes.SUCCESS: False,
                        NotificationTypes.ERROR: f"No se encontró empresa con NIF {nif_clean}",
                        "nif_detectado": nif_clean
                    }), 404
            else:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "No se pudo detectar el NIF en el documento"
                }), 400
        
        # Validar duplicados (como sistema general)
        # 1. Verificar por nombre de archivo en documentos generales
        from models import Documento
        doc_existente_nombre = Documento.query.filter_by(
            empresa_id=empresa_id,
            nombre_archivo=file.filename
        ).first()
        
        if doc_existente_nombre:
            os.remove(filepath)  # Limpiar archivo temporal
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "duplicado_nombre",
                "message": f"⚠️ Ya existe un archivo con el nombre '{file.filename}' en documentos generales"
            }), 400
        
        # 2. Verificar por nombre de archivo en documentos fiscales
        # Buscar documentos fiscales con el mismo nombre de archivo original
        docs_fiscales_empresa = DocumentoFiscal.query.filter_by(empresa_id=empresa_id).all()
        for doc in docs_fiscales_empresa:
            existing_filename = os.path.basename(doc.archivo_pdf_path)
            # Extraer nombre original (quitar timestamp del inicio)
            # Formato: 20251208_202129_111_2T_2025_SHEHRAN EXPRESS SL.PDF
            # Queremos: 111_2T_2025_SHEHRAN EXPRESS SL.PDF
            if '_' in existing_filename:
                parts = existing_filename.split('_', 2)  # Split máximo 2 veces
                if len(parts) >= 3:
                    nombre_sin_timestamp = parts[2]  # Tercer elemento es el nombre original
                    if nombre_sin_timestamp == file.filename:
                        os.remove(filepath)
                        return jsonify({
                            NotificationTypes.SUCCESS: False,
                            NotificationTypes.ERROR: "duplicado_fiscal",
                            "message": f"⚠️ Documento fiscal ya existe: {file.filename}"
                        }), 400
        
        # 3. Verificar por hash (contenido idéntico) GLOBAL
        from app import get_file_hash
        file_hash = get_file_hash(filepath)
        
        if file_hash:
            # Buscar en documentos generales
            doc_duplicado = Documento.query.filter_by(file_hash=file_hash).first()
            if doc_duplicado:
                os.remove(filepath)
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "duplicado_hash",
                    "message": f"⚠️ Archivo idéntico ya existe en documentos generales: {doc_duplicado.nombre_archivo}"
                }), 400
        
        # Si se proporcionó empresa_id, validar que pertenece a la gestoría
        if empresa_id:
            try:
                empresa_id = int(empresa_id)
            except (TypeError, ValueError):
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "empresa_id inválido"}), 400
            from models import Empresa
            emp_validar = Empresa.query.filter_by(id=empresa_id, gestoria_id=gestoria_id).first()
            if not emp_validar:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Empresa no válida para esta gestoría"}), 403

        # Procesar con IA usando AsyncRunner (hilo dedicado, loop persistente)
        # para evitar conflictos con el loop de gevent/gunicorn.
        from async_runner import runner as async_runner
        resultado = async_runner.run_sync(
            procesar_documento_fiscal(filepath, empresa_id)
        )
        
        # Preparar respuesta
        response_data = {
            NotificationTypes.SUCCESS: True,
            "documento_id": resultado["documento_id"],
            "sugerencias": resultado["sugerencias"],
            "mensaje": "Documento procesado. Por favor, revisa y confirma la clasificación."
        }
        
        # Si se detectó automáticamente, agregar info
        if request.form.get('empresa_id') is None:
            from models import Empresa
            emp = Empresa.query.get(empresa_id)
            response_data["empresa_detectada"] = emp.nombre if emp else None
            response_data["nif_detectado"] = nif_clean
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================================================
# CONFIRMACIÓN DE CLASIFICACIÓN
# ============================================================================

@fiscal_bp.route('/documentos/<int:doc_id>/confirmar', methods=['POST'])
@login_required
@auditar(AccionesAuditoria.DOCUMENTO_ACTUALIZADO, entidad_tipo='DocumentoFiscal')
def confirmar_clasificacion(doc_id):
    """
    Usuario confirma o corrige la clasificación sugerida por IA
    
    JSON Body:
        - clasificacion: Clasificación confirmada
        - metadatos: Metadatos corregidos (opcional)
        - importe_pago: Importe corregido (opcional)
        - fecha_limite: Fecha límite corregida (opcional)
        
    Returns:
        JSON con success
    """
    
    data = request.json
    
    # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
    from models import Empresa
    documento = DocumentoFiscal.query.join(Empresa).filter(
        DocumentoFiscal.id == doc_id,
        Empresa.gestoria_id == get_current_gestoria_id()
    ).first_or_404()
    
    # Verificar que el documento está pendiente de revisión
    if documento.estado != 'PENDIENTE_REVISION':
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: "El documento ya fue confirmado"
        }), 400
    
    try:
        # Actualizar con confirmación del usuario
        clasificacion_confirmada = data.get('clasificacion')
        metadatos_corregidos = data.get('metadatos')
        importe_pago = data.get('importe_pago')
        fecha_limite = data.get('fecha_limite')
        
        # Usar método del modelo
        documento.marcar_como_confirmado(
            usuario_id=current_user.id,
            clasificacion_confirmada=clasificacion_confirmada,
            metadatos_corregidos=metadatos_corregidos
        )
        
        # Actualizar campos adicionales si se proporcionaron
        if importe_pago is not None:
            documento.importe_pago = importe_pago
        
        if fecha_limite:
            try:
                documento.fecha_limite_pago = datetime.strptime(fecha_limite, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "mensaje": "Clasificación confirmada exitosamente",
            "documento": documento.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================================================
# LISTADO DE DOCUMENTOS
# ============================================================================

@fiscal_bp.route('/documentos', methods=['GET'])
@login_required
def listar_documentos_fiscales():
    """
    Lista documentos fiscales con filtros
    
    Query Params:
        - empresa_id: Filtrar por empresa
        - ejercicio: Filtrar por ejercicio fiscal
        - tipo: Filtrar por tipo de documento
        - estado: Filtrar por estado
        - clasificacion: Filtrar por clasificación
        
    Returns:
        JSON con lista de documentos
    """
    
    # MULTI-TENANT: Filtrar por gestoría
    from models import Empresa
    query = DocumentoFiscal.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id()
    )
    
    # Filtros
    empresa_id = request.args.get('empresa_id')
    ejercicio = request.args.get('ejercicio')
    tipo = request.args.get('tipo')
    estado = request.args.get('estado')
    clasificacion = request.args.get('clasificacion')
    
    if empresa_id:
        try:
            query = query.filter_by(empresa_id=int(empresa_id))
        except (TypeError, ValueError):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "empresa_id inválido"}), 400

    if ejercicio:
        try:
            query = query.filter_by(ejercicio_fiscal=int(ejercicio))
        except (TypeError, ValueError):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "ejercicio inválido"}), 400
    
    if tipo:
        query = query.filter_by(tipo_documento=tipo)
    
    if estado:
        query = query.filter_by(estado=estado)
    
    if clasificacion:
        query = query.filter(
            or_(
                DocumentoFiscal.clasificacion_sugerida == clasificacion,
                DocumentoFiscal.clasificacion_confirmada == clasificacion
            )
        )
    
    # Ordenar por fecha de creación (más recientes primero)
    documentos = query.order_by(DocumentoFiscal.created_at.desc()).all()
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "documentos": [doc.to_dict() for doc in documentos],
        "total": len(documentos)
    }), 200


# ============================================================================
# DETALLE DE DOCUMENTO
# ============================================================================

@fiscal_bp.route('/documentos/<int:doc_id>', methods=['GET'])
@login_required
def obtener_documento_fiscal(doc_id):
    """
    Obtiene el detalle de un documento fiscal
    
    Returns:
        JSON con datos del documento
    """
    
    # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
    from models import Empresa
    documento = DocumentoFiscal.query.join(Empresa).filter(
        DocumentoFiscal.id == doc_id,
        Empresa.gestoria_id == get_current_gestoria_id()
    ).first_or_404()
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "documento": documento.to_dict()
    }), 200


# ============================================================================
# PRÓXIMAS OBLIGACIONES
# ============================================================================

@fiscal_bp.route('/obligaciones', methods=['GET'])
@login_required
def proximas_obligaciones():
    """
    Obtiene próximos vencimientos fiscales
    
    Query Params:
        - dias: Número de días a futuro (default: 30)
        - empresa_id: Filtrar por empresa (opcional)
        
    Returns:
        JSON con lista de obligaciones próximas
    """
    
    dias = int(request.args.get('dias', 30))
    empresa_id = request.args.get('empresa_id')
    
    hoy = date.today()
    fecha_limite = hoy + timedelta(days=dias)
    
    # MULTI-TENANT: Filtrar por gestoría a través de Empresa
    from models import Empresa
    query = DocumentoFiscal.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        DocumentoFiscal.fecha_limite_pago.isnot(None),
        DocumentoFiscal.fecha_limite_pago.between(hoy, fecha_limite),
        DocumentoFiscal.estado.in_(['CONFIRMADO', 'PRESENTADO'])
    )
    
    if empresa_id:
        query = query.filter(DocumentoFiscal.empresa_id == int(empresa_id))
    
    obligaciones = query.order_by(DocumentoFiscal.fecha_limite_pago).all()
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "obligaciones": [doc.to_dict() for doc in obligaciones],
        "total": len(obligaciones),
        "periodo": f"Próximos {dias} días"
    }), 200


# ============================================================================
# APLAZAMIENTOS
# ============================================================================

@fiscal_bp.route('/aplazamientos', methods=['GET'])
@login_required
def listar_aplazamientos():
    """
    Lista aplazamientos activos
    
    Query Params:
        - empresa_id: Filtrar por empresa (opcional)
        
    Returns:
        JSON con lista de aplazamientos
    """
    
    empresa_id = request.args.get('empresa_id')
    
    # MULTI-TENANT: Filtrar por gestoría a través de Empresa
    from models import Empresa
    query = DocumentoFiscal.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        DocumentoFiscal.tipo_documento.in_([
            'APLAZAMIENTO_SOLICITUD',
            'APLAZAMIENTO_CONCESION'
        ])
    )
    
    if empresa_id:
        query = query.filter(DocumentoFiscal.empresa_id == int(empresa_id))
    
    aplazamientos = query.order_by(DocumentoFiscal.created_at.desc()).all()
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "aplazamientos": [doc.to_dict() for doc in aplazamientos],
        "total": len(aplazamientos)
    }), 200


# ============================================================================
# ACTUALIZAR ESTADO
# ============================================================================

@fiscal_bp.route('/documentos/<int:doc_id>/estado', methods=['PUT'])
@login_required
@auditar(AccionesAuditoria.DOCUMENTO_ACTUALIZADO, entidad_tipo='DocumentoFiscal')
def actualizar_estado(doc_id):
    """
    Actualiza el estado de un documento fiscal
    
    JSON Body:
        - estado: Nuevo estado (PRESENTADO, PAGADO, etc.)
        
    Returns:
        JSON con success
    """
    
    ESTADOS_FISCALES_PERMITIDOS = {'PENDIENTE', 'PRESENTADO', 'PAGADO', 'VENCIDO', 'CANCELADO'}

    data = request.json
    nuevo_estado = data.get('estado')

    if not nuevo_estado:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Estado requerido"}), 400

    if nuevo_estado not in ESTADOS_FISCALES_PERMITIDOS:
        return jsonify({
            NotificationTypes.SUCCESS: False,
            NotificationTypes.ERROR: f"Estado no válido. Permitidos: {', '.join(sorted(ESTADOS_FISCALES_PERMITIDOS))}"
        }), 400

    # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
    from models import Empresa
    documento = DocumentoFiscal.query.join(Empresa).filter(
        DocumentoFiscal.id == doc_id,
        Empresa.gestoria_id == get_current_gestoria_id()
    ).first_or_404()

    try:
        if nuevo_estado == 'PRESENTADO':
            documento.marcar_como_presentado()
        elif nuevo_estado == 'PAGADO':
            documento.marcar_como_pagado()
        else:
            documento.estado = nuevo_estado
            documento.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "mensaje": f"Estado actualizado a {nuevo_estado}",
            "documento": documento.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================================================
# SERVIR PDF
# ============================================================================

@fiscal_bp.route('/documentos/<int:doc_id>/pdf', methods=['GET'])
@login_required
def servir_pdf_fiscal(doc_id):
    """
    Sirve el archivo PDF del documento fiscal
    MULTI-TENANT: Validar que el documento pertenece a la gestoría del usuario
    
    Returns:
        Archivo PDF
    """
    
    documento = DocumentoFiscal.query.get_or_404(doc_id)
    
    # MULTI-TENANT: Verificar que el documento pertenece a la gestoría actual
    from models import Empresa
    empresa = Empresa.query.get(documento.empresa_id)
    if not empresa or empresa.gestoria_id != get_current_gestoria_id():
        return jsonify({NotificationTypes.ERROR: "Acceso denegado"}), 403
    
    if not os.path.exists(documento.archivo_pdf_path):
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Archivo no encontrado"}), 404
    
    return send_file(
        documento.archivo_pdf_path,
        mimetype='application/pdf',
        as_attachment=False
    )


# ============================================================================
# RESUMEN FISCAL POR EMPRESA
# ============================================================================

@fiscal_bp.route('/empresas/<int:empresa_id>/resumen', methods=['GET'])
@login_required
def resumen_fiscal_empresa(empresa_id):
    """
    Obtiene resumen fiscal de una empresa
    
    Query Params:
        - ejercicio: Año fiscal (default: año actual)
        
    Returns:
        JSON con resumen fiscal
    """
    
    ejercicio = int(request.args.get('ejercicio', date.today().year))
    
    # MULTI-TENANT: Validar que la empresa pertenece a la gestoría
    from models import Empresa
    empresa = Empresa.query.filter_by(id=empresa_id, gestoria_id=get_current_gestoria_id()).first()
    if not empresa:
        return jsonify({NotificationTypes.ERROR: "Empresa no válida"}), 403
        
    # Obtener todos los documentos del ejercicio
    documentos = DocumentoFiscal.query.filter_by(
        empresa_id=empresa_id,
        ejercicio_fiscal=ejercicio
    ).all()
    
    # Agrupar por tipo
    por_tipo = {}
    for doc in documentos:
        tipo = doc.tipo_documento
        if tipo not in por_tipo:
            por_tipo[tipo] = []
        por_tipo[tipo].append(doc.to_dict())
    
    # Contar pendientes de revisión
    pendientes_revision = len([d for d in documentos if d.estado == 'PENDIENTE_REVISION'])
    
    # Próximos vencimientos (30 días)
    hoy = date.today()
    proximos_30 = hoy + timedelta(days=30)
    vencimientos = [
        d.to_dict() for d in documentos 
        if d.fecha_limite_pago and hoy <= d.fecha_limite_pago <= proximos_30
    ]
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "empresa_id": empresa_id,
        "ejercicio": ejercicio,
        "total_documentos": len(documentos),
        "pendientes_revision": pendientes_revision,
        "por_tipo": por_tipo,
        "proximos_vencimientos": vencimientos
    }), 200
