"""
Utilidades para manejo de archivos multi-tenant
Gestiona rutas de archivos específicas por gestoría
"""
import os
from flask import current_app
from constants import DocumentCategories

def get_gestoria_upload_path(gestoria_id, categoria):
    """
    Retorna la ruta de carpeta para una gestoría específica
    
    Args:
        gestoria_id: ID de la gestoría
        categoria: Nombre de la categoría (Por Procesar, Procesados, etc.)
    
    Returns:
        str: Ruta completa a la carpeta
    """
    base_path = os.path.join('storage', f'gestoria_{gestoria_id}', categoria)
    
    # Crear carpeta si no existe
    os.makedirs(base_path, exist_ok=True)
    
    return base_path

def get_document_path(gestoria_id, categoria, filename):
    """
    Retorna la ruta completa para un documento
    
    Args:
        gestoria_id: ID de la gestoría
        categoria: Nombre de la categoría
        filename: Nombre del archivo
    
    Returns:
        str: Ruta completa al archivo
    """
    folder = get_gestoria_upload_path(gestoria_id, categoria)
    return os.path.join(folder, filename)

def move_document(origen, gestoria_id, nueva_categoria, filename):
    """
    Mueve un documento a una nueva categoría dentro de la misma gestoría
    
    Args:
        origen: Ruta actual del archivo
        gestoria_id: ID de la gestoría
        nueva_categoria: Nueva categoría destino
        filename: Nombre del archivo
    
    Returns:
        str: Nueva ruta del archivo
    """
    import shutil
    
    destino = get_document_path(gestoria_id, nueva_categoria, filename)
    
    # Crear carpeta destino si no existe
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Mover archivo
    if os.path.exists(origen):
        shutil.move(origen, destino)
    else:
        raise FileNotFoundError(f"Archivo origen no encontrado: {origen}")
    
    return destino

def ensure_gestoria_folders(gestoria_id):
    """
    Crea todas las carpetas necesarias para una gestoría
    
    Args:
        gestoria_id: ID de la gestoría
    """
    categorias = [DocumentCategories.POR_PROCESAR, 'Procesados', 'Guardados', 'Archivados']
    
    for categoria in categorias:
        get_gestoria_upload_path(gestoria_id, categoria)
