from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseNotificationProfile(ABC):
    """Interfaz base para perfiles de extracción de notificaciones"""

    def __init__(self):
        pass

    @abstractmethod
    def matches(self, texto_completo: str) -> bool:
        """Devuelve True si este perfil aplica al texto dado"""
        pass

    @abstractmethod
    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        """Extrae los datos específicos de la notificación"""
        pass

    def _normalize_amount(self, text: str) -> float:
        """Ayuda para normalizar importes"""
        if not text:
            return 0.0
        text = str(text).strip().replace('€', '').replace('$', '').strip()
        # Lógica estándar de coma/punto
        import re
        if ',' in text and '.' in text:
            if text.rfind(',') > text.rfind('.'):
                text = text.replace('.', '').replace(',', '.')
            else:
                text = text.replace(',', '')
        elif ',' in text:
            if re.search(r',\d{2}$', text):
                text = text.replace(',', '.')
            else:
                text = text.replace(',', '')
        
        text = re.sub(r'[^\d.-]', '', text)
        try:
            return float(text)
        except:
            return 0.0
