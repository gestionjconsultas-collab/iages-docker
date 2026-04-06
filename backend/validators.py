"""
Validadores centralizados para IAGES
"""

import re
from datetime import datetime


class NIFValidator:
    """Validador de NIF/CIF español"""
    
    NIF_REGEX = re.compile(r'^[0-9]{8}[A-Z]$')
    CIF_REGEX = re.compile(r'^[A-Z][0-9]{7}[A-Z0-9]$')
    NIE_REGEX = re.compile(r'^[XYZ][0-9]{7}[A-Z]$')
    
    @classmethod
    def validate(cls, nif):
        """
        Valida formato de NIF/CIF/NIE
        
        Args:
            nif: str - NIF/CIF/NIE a validar
        
        Returns:
            bool: True si es válido
        """
        if not nif:
            return False
        
        nif = cls.normalize(nif)
        
        # Validar NIF
        if cls.NIF_REGEX.match(nif):
            return cls._validate_nif_letter(nif)
        
        # Validar NIE
        if cls.NIE_REGEX.match(nif):
            return cls._validate_nie_letter(nif)
        
        # Validar CIF
        if cls.CIF_REGEX.match(nif):
            return True
        
        return False
    
    @classmethod
    def _validate_nif_letter(cls, nif):
        """Valida letra de control del NIF"""
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        number = int(nif[:8])
        return nif[8] == letters[number % 23]
    
    @classmethod
    def _validate_nie_letter(cls, nie):
        """Valida letra de control del NIE"""
        # Convertir primera letra a número
        nie_map = {'X': '0', 'Y': '1', 'Z': '2'}
        nie_number = nie_map[nie[0]] + nie[1:8]
        
        letters = 'TRWAGMYFPDXBNJZSQVHLCKE'
        number = int(nie_number)
        return nie[8] == letters[number % 23]
    
    @classmethod
    def normalize(cls, nif):
        """Normaliza formato de NIF (uppercase, sin espacios)"""
        if not nif:
            return None
        return nif.upper().strip().replace(' ', '').replace('-', '')


class EmailValidator:
    """Validador de email"""
    
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    @classmethod
    def validate(cls, email):
        """Valida formato de email"""
        if not email:
            return False
        return bool(cls.EMAIL_REGEX.match(email.strip()))
    
    @classmethod
    def normalize(cls, email):
        """Normaliza email (lowercase, sin espacios)"""
        if not email:
            return None
        return email.lower().strip()
    
    @classmethod
    def validate_list(cls, emails):
        """Valida una lista de emails"""
        if not emails:
            return True
        if isinstance(emails, str):
            emails = [e.strip() for e in emails.split(',')]
        return all(cls.validate(email) for email in emails if email)


class DateValidator:
    """Validador de fechas"""
    
    @classmethod
    def validate_range(cls, fecha_desde, fecha_hasta):
        """Valida que fecha_desde <= fecha_hasta"""
        if not fecha_desde or not fecha_hasta:
            return True
        
        # Convertir a datetime si son strings
        if isinstance(fecha_desde, str):
            fecha_desde = datetime.fromisoformat(fecha_desde)
        if isinstance(fecha_hasta, str):
            fecha_hasta = datetime.fromisoformat(fecha_hasta)
        
        return fecha_desde <= fecha_hasta
    
    @classmethod
    def is_future(cls, fecha):
        """Verifica si una fecha es futura"""
        if not fecha:
            return False
        if isinstance(fecha, str):
            fecha = datetime.fromisoformat(fecha)
        return fecha > datetime.now()
    
    @classmethod
    def is_past(cls, fecha):
        """Verifica si una fecha es pasada"""
        if not fecha:
            return False
        if isinstance(fecha, str):
            fecha = datetime.fromisoformat(fecha)
        return fecha < datetime.now()
    
    @classmethod
    def validate_periodo(cls, periodo):
        """Valida formato de periodo YYYYMM"""
        if not periodo:
            return False
        if not isinstance(periodo, str):
            periodo = str(periodo)
        
        # Debe ser 6 dígitos
        if len(periodo) != 6 or not periodo.isdigit():
            return False
        
        # Validar año y mes
        year = int(periodo[:4])
        month = int(periodo[4:])
        
        return 2000 <= year <= 2100 and 1 <= month <= 12


class FileValidator:
    """Validador de archivos"""
    
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png'}
    MAX_FILENAME_LENGTH = 255
    
    @classmethod
    def validate_extension(cls, filename):
        """Valida extensión de archivo"""
        if not filename:
            return False
        extension = filename.rsplit('.', 1)[-1].lower()
        return extension in cls.ALLOWED_EXTENSIONS
    
    @classmethod
    def validate_filename(cls, filename):
        """Valida nombre de archivo"""
        if not filename:
            return False
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            return False
        # No debe contener caracteres especiales peligrosos
        dangerous_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        return not any(char in filename for char in dangerous_chars)
    
    @classmethod
    def validate_size(cls, size_bytes, max_mb=50):
        """Valida tamaño de archivo"""
        max_bytes = max_mb * 1024 * 1024
        return 0 < size_bytes <= max_bytes


class PasswordValidator:
    """Validador de contraseñas"""
    
    MIN_LENGTH = 8
    
    @classmethod
    def validate(cls, password):
        """
        Valida fortaleza de contraseña
        Debe tener al menos 8 caracteres
        """
        if not password:
            return False, "La contraseña es requerida"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"La contraseña debe tener al menos {cls.MIN_LENGTH} caracteres"
        
        return True, "Contraseña válida"
    
    @classmethod
    def validate_strong(cls, password):
        """
        Valida contraseña fuerte
        Debe tener mayúsculas, minúsculas, números
        """
        if not password:
            return False, "La contraseña es requerida"
        
        if len(password) < cls.MIN_LENGTH:
            return False, f"La contraseña debe tener al menos {cls.MIN_LENGTH} caracteres"
        
        if not re.search(r'[A-Z]', password):
            return False, "Debe contener al menos una mayúscula"
        
        if not re.search(r'[a-z]', password):
            return False, "Debe contener al menos una minúscula"
        
        if not re.search(r'[0-9]', password):
            return False, "Debe contener al menos un número"
        
        return True, "Contraseña válida"
