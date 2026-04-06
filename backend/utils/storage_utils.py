#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilidades para Almacenamiento Multi-Tenant

Gestiona rutas de archivos con estructura:
storage/gestoria_{id}/EMPRESA_NAME/archivo.pdf
"""

import os
import shutil
from flask import current_app
from constants import NotificationTypes
import logging

logger = logging.getLogger(__name__)


def get_gestoria_storage_path(gestoria_id):
    """
    Retorna la ruta base de almacenamiento para una gestoría
    Usa el slug de la gestoría para nombres legibles
    
    Args:
        gestoria_id (int): ID de la gestoría
    
    Returns:
        str: Ruta absoluta a storage/{gestoria_slug}/
    """
    from flask import current_app
    from models import Gestoria, db
    
    base_path = current_app.config.get('RUTA_RAIZ_NOTIFICACIONES', 'storage')
    
    # Obtener slug de la gestoría
    gestoria = db.session.get(Gestoria, gestoria_id)
    if not gestoria:
        # Fallback a ID si no se encuentra la gestoría
        gestoria_folder = f'gestoria_{gestoria_id}'
    else:
        # Usar slug (URL-friendly) o nombre limpio
        gestoria_folder = gestoria.slug if gestoria.slug else f'gestoria_{gestoria_id}'
    
    gestoria_path = os.path.join(base_path, gestoria_folder)
    
    # Crear carpeta si no existe
    os.makedirs(gestoria_path, exist_ok=True)
    
    return gestoria_path


def get_empresa_storage_path(gestoria_id, empresa_nombre):
    """
    Retorna la ruta de almacenamiento para una empresa específica
    
    Args:
        gestoria_id (int): ID de la gestoría
        empresa_nombre (str): Nombre de la empresa
    
    Returns:
        str: Ruta absoluta a storage/gestoria_{id}/EMPRESA_NAME/
    """
    from utils import limpiar_nombre_carpeta
    gestoria_path = get_gestoria_storage_path(gestoria_id)
    nombre_limpio = limpiar_nombre_carpeta(empresa_nombre)
    empresa_path = os.path.join(gestoria_path, nombre_limpio)
    
    # Crear carpeta si no existe
    os.makedirs(empresa_path, exist_ok=True)
    
    return empresa_path


def get_document_storage_path(gestoria_id, empresa_nombre, filename):
    """
    Retorna la ruta completa para guardar un documento
    
    Args:
        gestoria_id (int): ID de la gestoría
        empresa_nombre (str): Nombre de la empresa
        filename (str): Nombre del archivo
    
    Returns:
        str: Ruta completa al archivo
    """
    empresa_path = get_empresa_storage_path(gestoria_id, empresa_nombre)
    return os.path.join(empresa_path, filename)


def migrate_empresa_files(empresa_id, old_path, new_path):
    """
    Migra archivos de una empresa de la estructura antigua a la nueva
    
    Args:
        empresa_id (int): ID de la empresa
        old_path (str): Ruta antigua (storage/EMPRESA_NAME/)
        new_path (str): Ruta nueva (storage/gestoria_X/EMPRESA_NAME/)
    
    Returns:
        dict: Reporte de migración con éxito, archivos movidos o error
    """
    if not os.path.exists(old_path):
        return {NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Ruta antigua no existe', 'files_moved': 0}
    
    # Si la ruta nueva ya existe, verificar si tiene archivos
    if os.path.exists(new_path):
        existing_files = os.listdir(new_path)
        if existing_files:
            return {
                NotificationTypes.SUCCESS: False, 
                NotificationTypes.ERROR: f'Ruta nueva ya existe con {len(existing_files)} archivos',
                'files_moved': 0
            }
    
    try:
        # Crear directorio padre si no existe
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        
        # Mover toda la carpeta
        shutil.move(old_path, new_path)
        
        files_count = len(os.listdir(new_path)) if os.path.exists(new_path) else 0
        
        return {
            NotificationTypes.SUCCESS: True,
            'empresa_id': empresa_id,
            'files_moved': files_count
        }
    except Exception as e:
        return {
            NotificationTypes.SUCCESS: False, 
            NotificationTypes.ERROR: str(e),
            'files_moved': 0
        }


def get_legacy_empresa_path(empresa_nombre):
    """
    Retorna la ruta antigua (pre-multi-tenant) de una empresa
    
    Args:
        empresa_nombre (str): Nombre de la empresa
    
    Returns:
        str: Ruta a storage/EMPRESA_NAME/
    """
    from flask import current_app
    base_path = current_app.config.get('RUTA_RAIZ_NOTIFICACIONES', 'storage')
    return os.path.join(base_path, empresa_nombre)


def is_multitenant_path(file_path):
    """
    Verifica si una ruta usa la estructura multi-tenant
    
    Args:
        file_path (str): Ruta del archivo
    
    Returns:
        bool: True si usa estructura gestoria_X/, False si no
    """
    return 'gestoria_' in file_path and os.path.sep + 'gestoria_' in file_path


def get_gestoria_inbox_path(gestoria_id):
    """
    Retorna la ruta del inbox de no clasificados para una gestoría específica
    
    Args:
        gestoria_id (int): ID de la gestoría
    
    Returns:
        str: Ruta absoluta a storage/gestoria_{id}/__INBOX_NO_CLASIFICADOS/
    """
    gestoria_path = get_gestoria_storage_path(gestoria_id)
    inbox_path = os.path.join(gestoria_path, '__INBOX_NO_CLASIFICADOS')
    
    # Crear carpeta si no existe
    os.makedirs(inbox_path, exist_ok=True)
    
    return inbox_path


def resolve_document_path(doc):
    """
    Resuelve la ruta de un documento manejando fallbacks por migración de slugs,
    nombres de carpetas de empresas con discrepancias de espacios y subcarpetas profundas.
    """
    if not doc or not doc.ruta_archivo:
        return None
        
    # 1. Caso ideal: La ruta existe
    if os.path.exists(doc.ruta_archivo):
        return doc.ruta_archivo
        
    try:
        from models import Gestoria, Empresa, db
        gestoria = db.session.get(Gestoria, doc.gestoria_id)
        if not gestoria:
            return doc.ruta_archivo
            
        original_path = doc.ruta_archivo
        filename = os.path.basename(original_path)
        base_storage = current_app.config.get('RUTA_RAIZ_NOTIFICACIONES', 'storage')
        
        # 2. Intentar buscar en el INBOX de la gestoría
        from utils.storage_utils import get_gestoria_inbox_path
        inbox_path = get_gestoria_inbox_path(doc.gestoria_id)
        potential_inbox = os.path.join(inbox_path, filename)
        if os.path.exists(potential_inbox):
            logger.info(f"🔧 Archivo encontrado en INBOX: {filename}")
            doc.ruta_archivo = potential_inbox
            db.session.commit()
            return potential_inbox

        # 3. Intentar buscar en la carpeta de la EMPRESA (buscando subcarpetas)
        if doc.empresa_id:
            empresa = db.session.get(Empresa, doc.empresa_id)
            if empresa:
                from utils.storage_utils import get_empresa_storage_path
                empresa_base_dir = get_empresa_storage_path(doc.gestoria_id, empresa.nombre)
                
                if os.path.exists(empresa_base_dir):
                    # Búsqueda recursiva insensible a mayúsculas
                    filename_lower = filename.lower()
                    for root, dirs, files in os.walk(empresa_base_dir):
                        for f in files:
                            if f.lower() == filename_lower:
                                found_path = os.path.join(root, f)
                                logger.info(f"🔧 Archivo encontrado (insensible) en empresa: {found_path}")
                                doc.ruta_archivo = found_path
                                db.session.commit()
                                return found_path
                else:
                    logger.warning(f"⚠️ Carpeta base de empresa no existe: {empresa_base_dir}")

        # 4. Fallback de GESTORÍA (si cambió el slug)
        fallbacks = [f"gestoria_{gestoria.id}", "victor-cisneros"]
        if gestoria.slug and gestoria.slug not in fallbacks:
            fallbacks.insert(0, gestoria.slug)
            
        filename_lower = filename.lower()
        for folder in fallbacks:
            parts = original_path.split(os.sep)
            try:
                idx = -1
                for i, part in enumerate(parts):
                    if part == 'storage' or part == 'backend':
                        if i+1 < len(parts) and 'storage' in parts[i+1]:
                            idx = i + 2
                        else:
                            idx = i + 1
                        break
                
                if idx != -1 and idx < len(parts):
                    new_parts = list(parts)
                    new_parts[idx] = folder
                    new_gestoria_base = os.sep.join(new_parts[:idx+1])
                    
                    if os.path.exists(new_gestoria_base):
                        # Búsqueda recursiva en la nueva carpeta de gestoría
                        for root, dirs, files in os.walk(new_gestoria_base):
                            for f in files:
                                if f.lower() == filename_lower:
                                    found_path = os.path.join(root, f)
                                    logger.info(f"🔧 Archivo encontrado en fallback de gestoría [{folder}]: {found_path}")
                                    doc.ruta_archivo = found_path
                                    db.session.commit()
                                    return found_path
            except Exception as e_fallback:
                logger.error(f"Error en fallback {folder}: {e_fallback}")
                continue
                
    except Exception as e:
        logger.error(f"⚠️ Error en resolve_document_path: {e}")
        
    return doc.ruta_archivo
