# backend/utils.py
import re

def limpiar_nombre_carpeta(nombre):
    """
    Elimina caracteres no válidos para nombres de carpetas en Windows
    y quita espacios extra.
    """
    if not nombre:
        return ""
    # Elimina caracteres no válidos: \ / : * ? " < > | . ,
    nombre_limpio = re.sub(r'[\\/*?:"<>|.,]', '', nombre)
    # Reemplaza múltiples espacios con uno solo
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio).strip()
    return nombre_limpio

def clean_and_convert_to_float(value):
    """
    Convierte un string (ej: '1.234,56' o '4,64') a un float (ej: 1234.56 o 4.64).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    
    s_value = str(value).replace('.', '').replace(',', '.').strip()
    
    try:
        return float(s_value)
    except (ValueError, TypeError):
        return None

def _find_nif_with_regex(texto: str) -> str | None:
    """
    Encuentra el primer NIF/CIF/NIE válido en un bloque de texto.
    Versión mejorada que busca formato estricto de NIF.
    """
    if not texto:
        return None
    
    # 1. Limpieza de texto:
    texto_limpio = texto.upper()
    texto_limpio = texto_limpio.replace("N.I.F", "NIF")
    texto_limpio = texto_limpio.replace("C.I.F", "CIF")

    # 2. BÚSQUEDA MUY ESTRICTA: Buscar en línea con NIF/CIF
    lineas = texto_limpio.split('\n')
    
    for i, linea in enumerate(lineas):
        # Si la línea contiene NIF o CIF
        if 'NIF' in linea or 'CIF' in linea:
            # Buscar en esta línea Y la siguiente (el NIF puede estar en la línea siguiente)
            texto_busqueda = linea
            if i + 1 < len(lineas):
                texto_busqueda += " " + lineas[i + 1]
            
            # Buscar patrón ESTRICTO: 0-9 dígitos seguidos de exactamente 1 letra
            # Acepta 8 o 9 dígitos (algunos NIFs tienen 0 inicial)
            patron = r'\b0?(\d{8}[A-Z])\b'
            match = re.search(patron, texto_busqueda)
            
            if match:
                nif_encontrado = match.group(1)  # Sin el 0 inicial si existe
                # Validar que sea exactamente 8 dígitos + 1 letra
                if re.fullmatch(r'\d{8}[A-Z]', nif_encontrado):
                    return nif_encontrado
    
    # 3. Si no encontró, buscar NIE (X/Y/Z + 7 dígitos + letra)
    texto_sin_espacios = re.sub(r'[\s\.-]', '', texto_limpio)
    nie_regex = r'[XYZ]\d{7}[A-Z]'
    match_nie = re.search(nie_regex, texto_sin_espacios)
    if match_nie:
        return match_nie.group(0)
    
    # 4. Buscar CIF (letra + 8 dígitos)
    cif_regex = r'[A-HJ-NP-SUVW]\d{8}'
    match_cif = re.search(cif_regex, texto_sin_espacios)
    if match_cif:
        return match_cif.group(0)

    return None


def escape_like(value, max_length=100):
    """
    Sanitiza input para consultas LIKE de SQL.
    
    Previene SQL injection escapando caracteres especiales de LIKE ('%', '_')
    y eliminando caracteres potencialmente peligrosos.
    
    Args:
        value: String a sanitizar
        max_length: Longitud máxima permitida (default: 100)
    
    Returns:
        String sanitizado seguro para usar en consultas LIKE
    
    Example:
        >>> q = escape_like(request.args.get('q'))
        >>> Empresa.query.filter(Empresa.nombre.ilike(f'%{q}%', escape='\\'))
    """
    if not value:
        return ''
    
    # Limitar longitud
    value = str(value)[:max_length]
    
    # Escapar backslash primero (para evitar doble escape)
    value = value.replace('\\', '\\\\')
    
    # Escapar caracteres especiales de LIKE
    value = value.replace('%', '\\%')
    value = value.replace('_', '\\_')
    
    # Eliminar caracteres potencialmente peligrosos
    # Permitir: letras, números, espacios, guiones, @, punto
    value = re.sub(r'[^\w\s\-@.]', '', value)
    
    return value.strip()
