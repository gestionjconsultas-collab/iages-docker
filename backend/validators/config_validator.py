"""
Validador de configuración de gestorías

Valida el schema JSON de configuración para asegurar:
- Colores en formato hexadecimal válido
- URLs correctamente formateadas
- Campos requeridos presentes
- Tipos de datos correctos
"""

import re
from typing import Dict, List, Tuple


def validate_hex_color(color: str) -> bool:
    """Valida que un color esté en formato hexadecimal (#RRGGBB)"""
    if not color:
        return False
    return bool(re.match(r'^#[0-9A-Fa-f]{6}$', color))


def validate_url(url: str) -> bool:
    """Valida que una URL esté correctamente formateada"""
    if not url:
        return True  # URLs vacías son válidas (opcional)
    return url.startswith('http://') or url.startswith('https://')


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    if not email:
        return True  # Email vacío es válido (opcional)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_gestoria_config(config: Dict) -> Tuple[bool, List[str]]:
    """
    Valida el schema completo de configuración de gestoría
    
    Args:
        config: Diccionario con configuración
    
    Returns:
        Tupla (is_valid, lista_de_errores)
    """
    errors = []
    
    if not isinstance(config, dict):
        return False, ["La configuración debe ser un objeto JSON"]
    
    # Validar sección de branding
    if 'branding' in config:
        branding = config['branding']
        
        # Validar colores
        if 'colores' in branding:
            colores = branding['colores']
            if not isinstance(colores, dict):
                errors.append("branding.colores debe ser un objeto")
            else:
                for key in ['primario', 'secundario', 'acento']:
                    if key in colores:
                        if not validate_hex_color(colores[key]):
                            errors.append(f"Color {key} inválido: {colores[key]}. Debe ser formato #RRGGBB")
        
        # Validar URLs de archivos
        for key in ['logo_url', 'favicon_url']:
            if key in branding:
                url = branding[key]
                if url and not (url.startswith('/storage/') or url.startswith('http')):
                    errors.append(f"{key} debe ser una ruta válida (/storage/... o http://...)")
    
    # Validar sección de contacto
    if 'contacto' in config:
        contacto = config['contacto']
        
        # Validar email
        if 'email' in contacto:
            if not validate_email(contacto['email']):
                errors.append(f"Email inválido: {contacto['email']}")
        
        # Validar redes sociales
        if 'redes_sociales' in contacto:
            redes = contacto['redes_sociales']
            if not isinstance(redes, dict):
                errors.append("contacto.redes_sociales debe ser un objeto")
            else:
                for key, value in redes.items():
                    if value and not validate_url(value):
                        errors.append(f"URL de {key} inválida: {value}")
    
    # Validar sección de personalización
    if 'personalizacion' in config:
        personalizacion = config['personalizacion']
        
        # Validar que los textos sean strings
        for key in ['mensaje_bienvenida', 'footer_texto']:
            if key in personalizacion:
                if not isinstance(personalizacion[key], str):
                    errors.append(f"personalizacion.{key} debe ser texto")
    
    return len(errors) == 0, errors


def get_default_config() -> Dict:
    """Retorna configuración por defecto para una nueva gestoría"""
    return {
        "branding": {
            "logo_url": "",
            "favicon_url": "",
            "colores": {
                "primario": "#FF6B35",
                "secundario": "#004E89",
                "acento": "#F7B801"
            }
        },
        "contacto": {
            "telefono": "",
            "email": "",
            "direccion": "",
            "redes_sociales": {
                "facebook": "",
                "linkedin": ""
            }
        },
        "personalizacion": {
            "mensaje_bienvenida": "Bienvenido a nuestra gestoría",
            "footer_texto": "© 2025 Gestoría - Todos los derechos reservados"
        }
    }
