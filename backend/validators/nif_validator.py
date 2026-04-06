"""
Validador de NIF/CIF español
Soporta: CIF, NIF, NIE
"""
import re

def validar_nif_espanol(nif):
    """
    Valida formato de NIF/CIF/NIE español
    
    Formatos válidos:
    - CIF: Letra + 7 dígitos + letra/dígito (B12345678)
    - NIF: 8 dígitos + letra (12345678Z)
    - NIE: X/Y/Z + 7 dígitos + letra (X1234567L)
    
    Args:
        nif (str): NIF/CIF/NIE a validar
    
    Returns:
        bool: True si es válido, False si no
    """
    if not nif:
        return False
    
    nif = nif.strip().upper().replace('-', '').replace(' ', '')
    
    # CIF: Letra + 7 dígitos + letra/dígito
    if re.match(r'^[ABCDEFGHJNPQRSUVW]\d{7}[A-J0-9]$', nif):
        return True
    
    # NIF: 8 dígitos + letra
    if re.match(r'^\d{8}[A-Z]$', nif):
        return True
    
    # NIE: X/Y/Z + 7 dígitos + letra
    if re.match(r'^[XYZ]\d{7}[A-Z]$', nif):
        return True
    
    return False


def normalizar_nif(nif):
    """
    Normaliza un NIF eliminando espacios y guiones
    
    Args:
        nif (str): NIF a normalizar
    
    Returns:
        str: NIF normalizado en mayúsculas
    """
    if not nif:
        return ''
    
    return nif.strip().upper().replace('-', '').replace(' ', '')
