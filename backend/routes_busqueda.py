# backend/routes_busqueda.py
"""
Endpoint de búsqueda full-text de documentos por texto OCR.
Permite buscar documentos que contengan cualquier texto: NIF, nombre, NAF, etc.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, func, text
from extensions import db
from models import Documento, Empresa

busqueda_bp = Blueprint('busqueda', __name__)


@busqueda_bp.route('/api/documentos/buscar', methods=['GET'])
@login_required
def buscar_documentos():
    """
    Búsqueda full-text en el texto OCR de los documentos.

    Query params:
      q         (str, requerido)  - Texto a buscar (NIF, nombre, NAF, cualquier texto)
      empresa_id (int, opcional)  - Filtrar por empresa específica
      categoria  (str, opcional)  - Filtrar por categoría (ej: 'Notificaciones')
      page       (int, default=1) - Página
      per_page   (int, default=20) - Resultados por página
    """
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify({'error': 'El texto de búsqueda debe tener al menos 2 caracteres'}), 400

    empresa_id = request.args.get('empresa_id', type=int)
    categoria = request.args.get('categoria', '').strip() or None
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)

    gestoria_id = getattr(current_user, 'gestoria_id', None)

    # Base query — siempre filtrar por gestoría (multi-tenant)
    query = Documento.query.filter(Documento.gestoria_id == gestoria_id)

    # Filtros opcionales
    if empresa_id:
        query = query.filter(Documento.empresa_id == empresa_id)
    if categoria:
        query = query.filter(Documento.categoria == categoria)

    # Solo documentos que ya tienen texto OCR guardado
    query = query.filter(Documento.texto_ocr.isnot(None))

    # Búsqueda: ILIKE para insensitivo a mayúsculas/minúsculas
    # Para frases largas dividimos por palabras (AND implícito)
    terminos = [t for t in q.split() if len(t) >= 2]
    for termino in terminos:
        query = query.filter(
            Documento.texto_ocr.ilike(f'%{termino}%')
        )

    # También buscar en datos_extraidos como fallback (para doc sin texto_ocr todavía)
    # Esto es menos eficiente pero asegura resultados incluso para doc. viejos
    query_fallback = Documento.query.filter(
        Documento.gestoria_id == gestoria_id,
        Documento.texto_ocr.is_(None),
        Documento.datos_extraidos.isnot(None)
    )
    if empresa_id:
        query_fallback = query_fallback.filter(Documento.empresa_id == empresa_id)
    if categoria:
        query_fallback = query_fallback.filter(Documento.categoria == categoria)

    # Buscar en JSON de datos_extraidos (cast a texto)
    for termino in terminos:
        query_fallback = query_fallback.filter(
            func.cast(Documento.datos_extraidos, db.Text).ilike(f'%{termino}%')
        )

    # Combinar ambas queries con UNION (via Python tras paginar)
    total_ocr = query.count()
    total_fallback = query_fallback.count()

    # Paginar la query principal (texto_ocr)
    docs_ocr = query.order_by(Documento.fecha_creacion.desc()).limit(per_page).offset((page - 1) * per_page).all()

    # Si hay espacio en la página, completar con fallback
    docs_fallback = []
    espacio_restante = per_page - len(docs_ocr)
    if espacio_restante > 0 and page == 1:
        docs_fallback = query_fallback.order_by(Documento.fecha_creacion.desc()).limit(espacio_restante).all()

    total = total_ocr + total_fallback

    # Serializar resultados
    resultados = []
    for doc in (docs_ocr + docs_fallback):
        empresa_nombre = doc.empresa.nombre if doc.empresa else None
        datos = doc.datos_extraidos or {}

        # Extraer fragmento de contexto donde aparece el primer término
        fragmento = None
        if doc.texto_ocr and terminos:
            idx = doc.texto_ocr.lower().find(terminos[0].lower())
            if idx != -1:
                inicio = max(0, idx - 60)
                fin = min(len(doc.texto_ocr), idx + 120)
                fragmento = '...' + doc.texto_ocr[inicio:fin].replace('\n', ' ').strip() + '...'

        resultados.append({
            'id': doc.id,
            'nombre_archivo': doc.nombre_archivo,
            'empresa_id': doc.empresa_id,
            'empresa_nombre': empresa_nombre,
            'categoria': doc.categoria,
            'fecha_creacion': doc.fecha_creacion.isoformat() if doc.fecha_creacion else None,
            'procesado': doc.procesado,
            'tipo_documento': datos.get('tipo_documento', ''),
            'razon_social': datos.get('razon_social') or datos.get('nombre_razon_social', ''),
            'nif': datos.get('nif', ''),
            'importe': doc.importe,
            'fragmento': fragmento,  # Contexto del texto encontrado
            'tiene_texto_ocr': doc.texto_ocr is not None,
        })

    return jsonify({
        'query': q,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': max(1, (total + per_page - 1) // per_page),
        'resultados': resultados,
        'con_texto_ocr': total_ocr,
        'sin_texto_ocr': total_fallback,  # Encontrados en JSON (menos preciso)
    })
