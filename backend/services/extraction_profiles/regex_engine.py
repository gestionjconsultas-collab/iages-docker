# backend/services/notification_extractor.py
"""
Extractor de texto para Notificaciones Españolas (AEAT, Seg. Social, etc.)
Basado en PDFExtractorNoAI pero adaptado para documentos oficiales.
- Regex multicapa con fallbacks
- Normalización robusta
- Validación de fechas y códigos de verificación (CSV)
"""

from services.pdf_extractor import PDFExtractor
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
# from services.extraction_profiles import get_profile # Comentado por ahora, las notificaciones no suelen tener perfiles de proveedor

class NotificationExtractor(PDFExtractor):
    """Extractor especializado en notificaciones oficiales sin IA"""
    
    def __init__(self):
        # No inicializar modelo de IA
        self.model = None
        
        # Patrones regex multicapa - ADAPTADOS para notificaciones (Pendiente de recibir hojas de ejemplo)
        # Por ahora mantenemos los genéricos como punto de partida
        self.patterns = {
            'nif': [
                r'ES([A-Z]\d{8})',
                r'(?:NIF|DNI|NIE)[:\s]*([A-Z]{0,2}\d{7,9}[A-Z]?)',
                r'([A-Z]\d{8})',
            ],
            'referencia': [
                r'Referencia[:\s]*([A-Z0-9]+)',
                r'Nº\s*Referencia[:\s]*([A-Z0-9]+)',
                r'Expediente[:\s]*([A-Z0-9/-]+)',
            ],
            'csv': [
                r'CSV[:\s]*([A-Z0-9]+)',
                r'Código\s+Seguro\s+de\s+Verificación[:\s]*([A-Z0-9]+)',
            ],
            'fecha': [
                r'Fecha[:\s]*(\d{1,2}[-/.](?:[a-zA-Z]{3,}|\d{1,2})[-/.]\d{2,4})',
                r'Madrid,\s*a\s*(\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4})',
                r'(\d{1,2}\s+de\s+[a-zA-Z]+\s+de\s+\d{4})',
            ],
            # Estos campos de importes pueden no ser relevantes para todas las notificaciones
            # pero los mantenemos por si acaso es una notificacion de pago/deuda
            'importe': [
                r'Importe[:\s]*([\d.,]+)',
                r'Total\s+a\s+ingresar[:\s]*([\d.,]+)',
                r'Cuota[:\s]*([\d.,]+)',
                r'Deuda[:\s]*([\d.,]+)',
            ]
        }
    
    def _normalize_amount(self, text):
        """Normaliza cantidades monetarias"""
        if not text:
            return 0.0
        
        text = str(text).strip().replace('€', '').replace('$', '').strip()
        
        if ',' in text and '.' in text:
            pos_coma = text.rfind(',')
            pos_punto = text.rfind('.')
            if pos_coma > pos_punto:
                text = text.replace('.', '').replace(',', '.')
            else:
                text = text.replace(',', '')
        elif ',' in text:
            partes = text.split(',')
            if len(partes[-1]) <= 2:
                text = text.replace(',', '.')
            else:
                text = text.replace(',', '')
        
        text = re.sub(r'[^\d.-]', '', text)
        
        try:
            return float(text)
        except (ValueError, TypeError):
            return 0.0
    
    def _extract_emails(self, texto: str) -> List[str]:
        """Extrae emails con corrección de OCR (Q→@, G→@)"""
        email_pattern = r'([a-zA-Z0-9._+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
        
        potential_emails = re.findall(
            r'([a-zA-Z0-9._+-]+(?:Q|G)?[a-zA-Z0-9._+-]?[a-zA-Z0-9-]*(?:\.[a-zA-Z0-9-.]+))', 
            texto
        )
        
        emails = []
        for email in potential_emails:
            normalized = email.replace('Q', '@').replace('G', '@').replace('O', '0')
            if re.match(email_pattern, normalized):
                emails.append(normalized)
        
        return emails if emails else []
    
    def _extract_with_patterns(self, text, patterns_list):
        """Intenta múltiples patrones regex hasta encontrar match"""
        for pattern in patterns_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    def _normalize_date(self, date_str):
        if not date_str: return ""
        
        # Limpiar
        date_str = date_str.lower().strip()
        
        # Diccionario de meses en español
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 
            'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09', 
            'octubre': '10', 'noviembre': '11', 'diciembre': '12',
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        
        # Limpiar ruidos comunes como " de " o " de"
        date_str = date_str.replace(' de ', ' ').replace(' de', ' ')
        
        # Ordenar por longitud descendente para evitar que 'ene' coincida dentro de 'enero'
        meses_lista = sorted(meses.items(), key=lambda x: len(x[0]), reverse=True)
        
        for mes_nombre, mes_num in meses_lista:
            if mes_nombre in date_str:
                date_str = date_str.replace(mes_nombre, mes_num)
                break
        
        # Regex para DD-MM-YYYY o DD/MM/YYYY
        match = re.search(r'(\d{1,2})[-/.\s]+(\d{1,2})[-/.\s]+(\d{2,4})', date_str)
        if match:
            partes = match.groups()
            d, m, y = int(partes[0]), int(partes[1]), int(partes[2])
            
            # Validación: si el mes es > 12 y el día es <= 12, es probable que estén cambiados
            if m > 12 and d <= 12:
                d, m = m, d
            
            # Año a 4 dígitos
            y_str = str(y)
            if len(y_str) == 2: y_str = "20" + y_str
            
            return f"{str(d).zfill(2)}/{str(m).zfill(2)}/{y_str}"
        return ""
    
    
    def extract_notification_data(self, texto_completo, texto_vertical):
        """Extrae datos de la notificación usando perfiles o regex genérico"""
        datos = {
            'organismo': 'DESCONOCIDO',
            'tipo_documento': 'GENÉRICO',
            'referencia': '',
            'fecha': '',
            'importe': 0.0,
            'providencia_numero': '',
            'nif': '',
            'nombre_razon_social': '',
            'concepto': ''
        }

        # --- 1. INTENTAR CON PERFILES ESPECÍFICOS ---
        # --- 1. INTENTAR CON PERFILES ESPECÍFICOS ---
        # Ruta corregida tras mover carpeta perfiles
        try:
            from services.extraction_profiles.notification_profiles import get_notification_profile
        except ImportError:
            # Fallback por si la estructura de carpetas varía
            try:
                from services.extraction_profiles.notification_profiles.base_notification_profile import get_notification_profile
            except:
                print("Error importando perfiles notificacion")
                return datos
        profile = get_notification_profile(texto_completo)
        
        if profile:
            print(f"   🔍 Perfil de notificación detectado: {type(profile).__name__}")
            datos_perfil = profile.extract_data(texto_completo)
            datos.update(datos_perfil)
            return datos

        # --- 2. EXTRACCIÓN GENÉRICA (Fallback) ---
        print("   ⚠️ No se detectó perfil específico. Usando extracción genérica.")
        
        # Identificación básica
        if 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL' in texto_completo.upper():
            datos['organismo'] = 'SEGURIDAD SOCIAL'
        elif 'AGENCIA TRIBUTARIA' in texto_completo.upper() or 'AEAT' in texto_completo.upper():
            datos['organismo'] = 'AGENCIA TRIBUTARIA'

        if 'PROVIDENCIA DE APREMIO' in texto_completo.upper():
            datos['tipo_documento'] = 'PROVIDENCIA DE APREMIO'

        # Referencia / Expediente
        datos['referencia'] = self._extract_with_patterns(texto_completo, self.patterns['referencia'])
        
        # CSV
        datos['csv'] = self._extract_with_patterns(texto_completo, self.patterns['csv'])

        # Fecha
        fecha_raw = self._extract_with_patterns(texto_completo, self.patterns['fecha'])
        datos['fecha'] = self._normalize_date(fecha_raw)
        
        # Importe (si aplica)
        importe_raw = self._extract_with_patterns(texto_completo, self.patterns.get('importe', []))
        datos['importe'] = self._normalize_amount(importe_raw)

        # NIF Destinatario
        nifs_encontrados = []
        for pat in self.patterns['nif']:
            matches = re.findall(pat, texto_completo, re.IGNORECASE)
            for m in matches:
                m_clean = m.upper().replace('ES', '').strip()
                if len(m_clean) >= 8 and len(m_clean) <= 9:
                     # Evitar NIFs de organismos si es posible (ej: Q28...)
                     if not m_clean.startswith('Q'):
                        if m_clean not in nifs_encontrados:
                            nifs_encontrados.append(m_clean)
        
        datos['nif'] = nifs_encontrados[0] if nifs_encontrados else ''

        return datos
    
    def extract_with_ai(self, texto_completo, texto_ultima_pagina, texto_vertical, **kwargs):
        """Override para NO usar IA - usa regex para notificaciones"""
        print("\n" + "📜 " + "="*58 + "\n📜 EXTRACCIÓN DE NOTIFICACIÓN (Regex)\n" + "📜 " + "="*58 + "\n")
        
        filename = kwargs.get('filename', '')
        
        # DEBUG: Mostrar texto extraído
        print("\n📝 TEXTO COMPLETO (primeras 500 caracteres):")
        print(texto_completo[:500])
        print("\n" + "="*60)
        
        print("\n📋 Extrayendo datos de notificación...")
        datos = self.extract_notification_data(texto_completo, texto_vertical)
        
        print(f"\n✅ Extracción completada:")
        print(f"   Organismo: {datos.get('organismo')}")
        print(f"   Tipo: {datos.get('tipo_documento')}")
        print(f"   Referencia: {datos.get('referencia')}")
        print(f"   Providencia Nº: {datos.get('providencia_numero')}")
        print(f"   Fecha: {datos.get('fecha')}")
        print(f"   NIF: {datos.get('nif')}")
        print(f"   Razón Social: {datos.get('nombre_razon_social')}")
        print(f"   CSV: {datos.get('csv')}")
        print(f"   Importe Total: {datos.get('importe')}€")
        print(f"   Importe Principal: {datos.get('importe_principal', 0)}€")
        print(f"   Recargo: {datos.get('importe_recargo', 0)}€")
        print(f"   Periodo: {datos.get('periodo', '')}")
        print(f"   Concepto: {datos.get('concepto')}")
        
        return datos
