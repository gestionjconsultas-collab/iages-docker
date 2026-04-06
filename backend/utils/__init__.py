# -*- coding: utf-8 -*-
"""
Utilidades del sistema
"""
import re

# Importar desde storage_utils
from .storage_utils import (
    get_gestoria_storage_path,
    get_empresa_storage_path,
    get_document_storage_path,
    migrate_empresa_files,
    get_legacy_empresa_path,
    is_multitenant_path,
    get_gestoria_inbox_path
)

# Funciones legacy (copiadas de utils.py para evitar circular import)
def limpiar_nombre_carpeta(nombre):
    """Elimina caracteres no válidos para nombres de carpetas en Windows"""
    if not nombre:
        return ""
    nombre_limpio = re.sub(r'[\\/*?:"<>|.,]', '', nombre)
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio).strip()
    return nombre_limpio

def clean_and_convert_to_float(value):
    """Convierte un string (ej: '1.234,56') a un float (ej: 1234.56)"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s_value = str(value).replace('.', '').replace(',', '.').strip()
    try:
        return float(s_value)
    except (ValueError, TypeError):
        return None

def _find_nif_with_regex(texto: str):
    """Encuentra el primer NIF/CIF/NIE válido en un bloque de texto"""
    if not texto:
        return None
    
    texto_limpio = texto.upper()
    texto_limpio = texto_limpio.replace("N.I.F", "NIF")
    texto_limpio = texto_limpio.replace("C.I.F", "CIF")
    
    lineas = texto_limpio.split('\n')
    for i, linea in enumerate(lineas):
        if 'NIF' in linea or 'CIF' in linea:
            texto_busqueda = linea
            if i + 1 < len(lineas):
                texto_busqueda += " " + lineas[i + 1]
            
            patron = r'\b0?(\d{8}[A-Z])\b'
            match = re.search(patron, texto_busqueda)
            
            if match:
                nif_encontrado = match.group(1)
                if re.fullmatch(r'\d{8}[A-Z]', nif_encontrado):
                    return nif_encontrado
    
    texto_sin_espacios = re.sub(r'[\s\.-]', '', texto_limpio)
    nie_regex = r'[XYZ]\d{7}[A-Z]'
    match_nie = re.search(nie_regex, texto_sin_espacios)
    if match_nie:
        return match_nie.group(0)
    
    cif_regex = r'[A-HJ-NP-SUVW]\d{8}'
    match_cif = re.search(cif_regex, texto_sin_espacios)
    if match_cif:
        return match_cif.group(0)
    
    return None

__all__ = [
    'get_gestoria_storage_path',
    'get_empresa_storage_path',
    'get_document_storage_path',
    'migrate_empresa_files',
    'get_legacy_empresa_path',
    'is_multitenant_path',
    'get_gestoria_inbox_path',
    'limpiar_nombre_carpeta',
    'clean_and_convert_to_float',
    '_find_nif_with_regex'
]
