"""
Formateadores centralizados para IAGES
"""

import re
from datetime import datetime
from constants import DateFormats


class DateFormatter:
    """Formateador de fechas"""
    
    @staticmethod
    def format_display(date):
        """Formato para mostrar al usuario: 19/12/2025"""
        if not date:
            return 'Sin fecha'
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                return date
        return date.strftime(DateFormats.DISPLAY)
    
    @staticmethod
    def format_display_with_time(date):
        """Formato con hora: 19/12/2025 10:30"""
        if not date:
            return 'Sin fecha'
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except:
                return date
        return date.strftime(DateFormats.DISPLAY_WITH_TIME)
    
    @staticmethod
    def format_iso(date):
        """Formato ISO para BD: 2025-12-19"""
        if not date:
            return None
        if isinstance(date, str):
            return date
        return date.strftime(DateFormats.ISO)
    
    @staticmethod
    def format_iso_with_time(date):
        """Formato ISO con hora: 2025-12-19 10:30:00"""
        if not date:
            return None
        if isinstance(date, str):
            return date
        return date.strftime(DateFormats.ISO_WITH_TIME)
    
    @staticmethod
    def format_filename(date=None):
        """Formato para nombres de archivo: 20251219_103000"""
        if not date:
            date = datetime.now()
        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        return date.strftime(DateFormats.FILENAME)
    
    @staticmethod
    def format_periodo(date):
        """Formato periodo YYYYMM: 202412"""
        if not date:
            return None
        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        return date.strftime(DateFormats.PERIODO)


class CurrencyFormatter:
    """Formateador de moneda"""
    
    @staticmethod
    def format_eur(amount):
        """Formato EUR: 1.234,56€"""
        if amount is None:
            return "0,00€"
        
        # Convertir a float si es necesario
        if isinstance(amount, str):
            amount = float(amount.replace(',', '.'))
        
        # Formatear con separadores
        formatted = f"{float(amount):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{formatted}€"
    
    @staticmethod
    def parse_eur(amount_str):
        """Parsea string de moneda a float"""
        if not amount_str:
            return 0.0
        
        # Eliminar símbolo de euro y espacios
        amount_str = amount_str.replace('€', '').strip()
        
        # Reemplazar separadores
        amount_str = amount_str.replace('.', '').replace(',', '.')
        
        try:
            return float(amount_str)
        except ValueError:
            return 0.0


class FileNameFormatter:
    """Formateador de nombres de archivo"""
    
    @staticmethod
    def sanitize(filename):
        """Sanitiza nombre de archivo (elimina caracteres especiales)"""
        if not filename:
            return 'archivo'
        
        # Eliminar caracteres no permitidos
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Eliminar espacios múltiples
        filename = re.sub(r'\s+', '_', filename)
        
        # Eliminar guiones bajos múltiples
        filename = re.sub(r'_+', '_', filename)
        
        # Eliminar guiones bajos al inicio y final
        filename = filename.strip('_')
        
        # Limitar longitud
        max_length = 200
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}" if ext else name
        
        return filename
    
    @staticmethod
    def generate_unique(base_name, extension='pdf'):
        """Genera nombre único con timestamp"""
        timestamp = DateFormatter.format_filename()
        base_name = FileNameFormatter.sanitize(base_name)
        
        # Eliminar extensión si ya la tiene
        if base_name.endswith(f'.{extension}'):
            base_name = base_name[:-len(extension)-1]
        
        return f"{base_name}_{timestamp}.{extension}"
    
    @staticmethod
    def extract_nif_from_filename(filename):
        """Extrae NIF de nombre de archivo"""
        # Buscar patrón de NIF/CIF
        patterns = [
            r'[A-Z]\d{7}[A-Z0-9]',  # CIF
            r'\d{8}[A-Z]',  # NIF
            r'[XYZ]\d{7}[A-Z]'  # NIE
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename.upper())
            if match:
                return match.group(0)
        
        return None


class TextFormatter:
    """Formateador de texto"""
    
    @staticmethod
    def truncate(text, max_length=100, suffix='...'):
        """Trunca texto a longitud máxima"""
        if not text:
            return ''
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def capitalize_words(text):
        """Capitaliza primera letra de cada palabra"""
        if not text:
            return ''
        return ' '.join(word.capitalize() for word in text.split())
    
    @staticmethod
    def remove_extra_spaces(text):
        """Elimina espacios múltiples"""
        if not text:
            return ''
        return re.sub(r'\s+', ' ', text).strip()
    
    @staticmethod
    def slugify(text):
        """Convierte texto a slug (URL-friendly)"""
        if not text:
            return ''
        
        # Convertir a minúsculas
        text = text.lower()
        
        # Reemplazar acentos
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Reemplazar espacios y caracteres especiales con guiones
        text = re.sub(r'[^a-z0-9]+', '-', text)
        
        # Eliminar guiones múltiples
        text = re.sub(r'-+', '-', text)
        
        # Eliminar guiones al inicio y final
        return text.strip('-')


class NumberFormatter:
    """Formateador de números"""
    
    @staticmethod
    def format_percentage(value, decimals=1):
        """Formatea porcentaje: 95.5%"""
        if value is None:
            return "0%"
        return f"{float(value):.{decimals}f}%"
    
    @staticmethod
    def format_file_size(bytes_size):
        """Formatea tamaño de archivo: 1.5 MB"""
        if bytes_size is None or bytes_size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(bytes_size)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    @staticmethod
    def format_number(number, decimals=0):
        """Formatea número con separadores: 1.234"""
        if number is None:
            return "0"
        
        if decimals > 0:
            formatted = f"{float(number):,.{decimals}f}"
        else:
            formatted = f"{int(number):,}"
        
        # Cambiar separadores a formato español
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
