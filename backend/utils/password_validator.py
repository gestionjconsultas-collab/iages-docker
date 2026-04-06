"""
Validador de políticas de contraseñas
Implementa validación de contraseñas fuertes según mejores prácticas de seguridad
"""
import re
from typing import Tuple, List


# Lista de contraseñas comunes a rechazar
COMMON_PASSWORDS = {
    'password', '12345678', '123456789', 'qwerty', 'abc123', 'password1',
    'password123', 'admin', 'letmein', 'welcome', 'monkey', '1234567890',
    'dragon', 'master', 'sunshine', 'princess', 'football', 'iloveyou',
    'admin123', 'root', 'toor', 'pass', 'test', 'guest', 'info', 'adm',
    'mysql', 'user', 'administrator', 'oracle', 'ftp', 'pi', 'puppet',
    'ansible', 'ec2-user', 'vagrant', 'azureuser', 'administrador'
}


def validate_password_strength(password: str, username: str = None, email: str = None) -> Tuple[bool, List[str]]:
    """
    Valida la fortaleza de una contraseña según políticas de seguridad
    
    Args:
        password: Contraseña a validar
        username: Nombre de usuario (opcional, para evitar que esté en la contraseña)
        email: Email del usuario (opcional, para evitar que esté en la contraseña)
    
    Returns:
        Tuple[bool, List[str]]: (es_válida, lista_de_errores)
    
    Política de contraseñas:
    - Mínimo 12 caracteres
    - Al menos 1 mayúscula
    - Al menos 1 minúscula
    - Al menos 1 número
    - Al menos 1 símbolo especial
    - No puede ser una contraseña común
    - No puede contener el username o email
    """
    errors = []
    
    # 1. Longitud mínima
    if len(password) < 12:
        errors.append("La contraseña debe tener al menos 12 caracteres")
    
    # 2. Longitud máxima (prevenir DoS)
    if len(password) > 128:
        errors.append("La contraseña no puede tener más de 128 caracteres")
    
    # 3. Debe contener mayúsculas
    if not re.search(r'[A-Z]', password):
        errors.append("Debe contener al menos una letra mayúscula")
    
    # 4. Debe contener minúsculas
    if not re.search(r'[a-z]', password):
        errors.append("Debe contener al menos una letra minúscula")
    
    # 5. Debe contener números
    if not re.search(r'[0-9]', password):
        errors.append("Debe contener al menos un número")
    
    # 6. Debe contener símbolos especiales
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        errors.append("Debe contener al menos un símbolo especial (!@#$%^&*...)")
    
    # 7. No puede ser una contraseña común
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Esta contraseña es demasiado común. Elige una más segura")
    
    # 8. No puede contener el username
    if username and len(username) >= 3 and username.lower() in password.lower():
        errors.append("La contraseña no puede contener tu nombre de usuario")
    
    # 9. No puede contener el email (parte antes del @)
    if email:
        email_prefix = email.split('@')[0]
        if len(email_prefix) >= 3 and email_prefix.lower() in password.lower():
            errors.append("La contraseña no puede contener tu email")
    
    # 10. No puede tener caracteres repetidos consecutivos (más de 3)
    if re.search(r'(.)\1{3,}', password):
        errors.append("No puede tener más de 3 caracteres idénticos consecutivos")
    
    # 11. No puede ser una secuencia simple
    sequences = ['123456', 'abcdef', 'qwerty', '098765', 'fedcba']
    for seq in sequences:
        if seq in password.lower():
            errors.append("No puede contener secuencias simples de caracteres")
            break
    
    is_valid = len(errors) == 0
    return is_valid, errors


def get_password_strength_score(password: str) -> Tuple[int, str]:
    """
    Calcula un score de fortaleza de contraseña (0-100)
    
    Returns:
        Tuple[int, str]: (score, nivel) donde nivel es: Muy Débil, Débil, Media, Fuerte, Muy Fuerte
    """
    score = 0
    
    # Longitud (hasta 40 puntos)
    length = len(password)
    if length >= 12:
        score += min(40, (length - 12) * 2 + 20)
    else:
        score += length * 1.5
    
    # Variedad de caracteres (hasta 60 puntos)
    has_lower = bool(re.search(r'[a-z]', password))
    has_upper = bool(re.search(r'[A-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password))
    
    variety_score = sum([has_lower, has_upper, has_digit, has_special]) * 15
    score += variety_score
    
    # Penalizaciones
    if password.lower() in COMMON_PASSWORDS:
        score -= 30
    
    if re.search(r'(.)\1{2,}', password):  # Caracteres repetidos
        score -= 10
    
    # Normalizar a 0-100
    score = max(0, min(100, score))
    
    # Determinar nivel
    if score < 30:
        level = "Muy Débil"
    elif score < 50:
        level = "Débil"
    elif score < 70:
        level = "Media"
    elif score < 90:
        level = "Fuerte"
    else:
        level = "Muy Fuerte"
    
    return score, level


def generate_password_requirements_message() -> str:
    """
    Genera un mensaje con los requisitos de contraseña
    """
    return """
Requisitos de contraseña:
• Mínimo 12 caracteres
• Al menos 1 letra mayúscula (A-Z)
• Al menos 1 letra minúscula (a-z)
• Al menos 1 número (0-9)
• Al menos 1 símbolo especial (!@#$%^&*...)
• No puede ser una contraseña común
• No puede contener tu nombre de usuario o email
    """.strip()
