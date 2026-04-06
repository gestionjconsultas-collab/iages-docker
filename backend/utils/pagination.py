"""
Helper de paginación para endpoints de la API
"""
from flask import request, jsonify
from math import ceil


def paginate_query(query, default_per_page=50, max_per_page=200):
    """
    Pagina una query de SQLAlchemy y devuelve resultados + metadata
    
    Args:
        query: SQLAlchemy query object
        default_per_page: Items por página por defecto
        max_per_page: Máximo de items por página permitido
    
    Returns:
        dict con 'items', 'total', 'page', 'per_page', 'pages'
    
    Ejemplo:
        from tenant_utils import get_current_gestoria_id
        query = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id())
        result = paginate_query(query)
        return jsonify(result)
    """
    # Obtener parámetros de paginación
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)
    
    # Validar límites
    if page < 1:
        page = 1
    if per_page < 1:
        per_page = default_per_page
    if per_page > max_per_page:
        per_page = max_per_page
    
    # Obtener total de items
    total = query.count()
    
    # Calcular offset
    offset = (page - 1) * per_page
    
    # Obtener items paginados
    items = query.limit(per_page).offset(offset).all()
    
    # Calcular total de páginas
    total_pages = ceil(total / per_page) if total > 0 else 1
    
    return {
        'items': items,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }


def paginate_response(query, serializer=None, default_per_page=50, max_per_page=200):
    """
    Versión que devuelve JSON directamente con serialización
    
    Args:
        query: SQLAlchemy query
        serializer: Función para serializar cada item (ej: lambda x: x.to_dict())
        default_per_page: Items por página
        max_per_page: Máximo permitido
    
    Returns:
        dict listo para jsonify()
    
    Ejemplo:
        from tenant_utils import get_current_gestoria_id
        query = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id())
        return jsonify(paginate_response(query, lambda e: e.to_dict()))
    """
    result = paginate_query(query, default_per_page, max_per_page)
    
    # Serializar items si se proporciona serializer
    if serializer:
        items = [serializer(item) for item in result['items']]
    else:
        # Intentar usar to_dict() si existe
        items = []
        for item in result['items']:
            if hasattr(item, 'to_dict'):
                items.append(item.to_dict())
            else:
                # Fallback: convertir a dict básico
                items.append({c.name: getattr(item, c.name) for c in item.__table__.columns})
    
    return {
        'success': True,
        'data': items,
        'pagination': result['pagination']
    }
