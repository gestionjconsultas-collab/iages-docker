# backend/services/notificacion_extractor.py

"""
Extractor de texto para Notificaciones Españolas (AEAT, Seg. Social, etc.)
Basado en PDFExtractorNoAI pero adaptado para documentos oficiales.
- Regex multicapa con fallbacks
- Normalización robusta
- Validación de fechas y códigos de verificación (CSV)
"""

# Ajuste de imports para entorno actual
try:
    from services.pdf_extractor import PDFExtractor
except ImportError:
    # Fallback si PDFExtractor no está disponible directamente
    import fitz
    class PDFExtractor:
        def __init__(self): pass
        def extract_text_from_pdf(self, pdf_path):
            try:
                doc = fitz.open(pdf_path)
                text = ""
                for page in doc: text += page.get_text()
                doc.close()
                return text
            except: return ""

import re
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from constants import NotificationTypes
# Motor Declarativo
try:
    from services.declarative_extraction_engine import DeclarativeExtractionEngine, DatabaseProfileStore
    from extensions import db
except ImportError:
    pass

# Logger configuration
logger = logging.getLogger(__name__)

class NotificacionExtractor(PDFExtractor):
    """
    Extractor especializado en notificaciones oficiales sin IA.
    Nota: Renombrado a NotificacionExtractor (con 'c') para compatibilidad con la app.
    Original: NotificationExtractor
    """
    
    def __init__(self):
        super().__init__()
        # No inicializar modelo de IA
        self.model = None

        # Inicializar Motor Declarativo (Hybrid Engine)
        try:
            from extensions import db
            self.profile_store = DatabaseProfileStore(db.session)
            self.declarative_engine = DeclarativeExtractionEngine(self.profile_store)
            logger.info("✅ Motor Declarativo (Hybrid Engine) inicializado.")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo inicializar Motor Declarativo: {e}")
            self.declarative_engine = None
        
        # Patrones regex multicapa - ADAPTADOS para notificaciones
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
            'importe': [
                r'Importe[:\s]*([\d.,]+)',
                r'Total\s+a\s+ingresar[:\s]*([\d.,]+)',
                r'Cuota[:\s]*([\d.,]+)',
                r'Deuda[:\s]*([\d.,]+)',
            ]
        }
        logger.info("NotificacionExtractor (Original/NoAI) inicializado.")
    
    def _normalize_amount(self, text):
        """Normaliza cantidades monetarias"""
        if not text:
            return 0.0
        
        text = str(text).strip().replace('€', '').replace('$', '').strip()
        
        # Lógica de detección de separadores
        if ',' in text and '.' in text:
            pos_coma = text.rfind(',')
            pos_punto = text.rfind('.')
            if pos_coma > pos_punto: # 1.234,56 (Español)
                text = text.replace('.', '').replace(',', '.')
            else: # 1,234.56 (Inglés)
                text = text.replace(',', '')
        elif ',' in text: # 1234,56
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
            
    def _extract_with_patterns(self, text, patterns_list):
        """Intenta múltiples patrones regex hasta encontrar match"""
        for pattern in patterns_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''
    
    def _normalize_date(self, date_str):
        if not date_str: return ""
        date_str = date_str.lower().strip()
        
        meses = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 
            'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09', 
            'octubre': '10', 'noviembre': '11', 'diciembre': '12',
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
            'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        
        date_str = date_str.replace(' de ', ' ').replace(' de', ' ')
        meses_lista = sorted(meses.items(), key=lambda x: len(x[0]), reverse=True)
        
        for mes_nombre, mes_num in meses_lista:
            if mes_nombre in date_str:
                date_str = date_str.replace(mes_nombre, mes_num)
                break
        
        match = re.search(r'(\d{1,2})[-/.\s]+(\d{1,2})[-/.\s]+(\d{2,4})', date_str)
        if match:
            partes = match.groups()
            d, m, y = int(partes[0]), int(partes[1]), int(partes[2])
            if m > 12 and d <= 12: d, m = m, d
            y_str = str(y)
            if len(y_str) == 2: y_str = "20" + y_str
            return f"{str(d).zfill(2)}/{str(m).zfill(2)}/{y_str}"
        return ""

    # =========================================================================
    # MÉTODOS DE EXTRACCIÓN ESPECÍFICA (FORZADA)
    # =========================================================================
    
    def extract_with_specific_profile(self, pdf_path: str, profile_classname: str) -> dict:
        """
        Intenta extraer datos forzando el uso de un perfil específico.
        Útil para cuando el usuario selecciona manualmente el tipo de documento.
        Soporta perfiles Hardcoded (.py) y perfiles Declarativos (.json / DB).
        """
        text = self.extract_text_from_pdf(pdf_path)
        if not text: return {NotificationTypes.ERROR: "Sin texto en PDF"}

        # Limpiar prefijo PROFILE: si viene del frontend
        clean_name = profile_classname.replace("PROFILE:", "")

        try:
            # 1. INTENTAR CON PERFILES HARDCODED (.py)
            from services.extraction_profiles.notification_profiles import PROFILES
            
            def normalize(name):
                return name.lower().replace('_', '').replace('profile', '')

            target_profile = next((
                p for p in PROFILES 
                if normalize(type(p).__name__) == normalize(clean_name)
            ), None)
            
            if target_profile:
                logger.info(f"🔨 Forzando extracción con perfil HARDCODED: {type(target_profile).__name__}")
                datos = target_profile.extract_data(text)
                datos['_metadata'] = {
                    'tipo_detectado': type(target_profile).__name__,
                    'perfil_usado': True,
                    'metodo': 'FORZADO_MANUAL_HARDCODED'
                }
            
            # 2. INTENTAR CON MOTOR DECLARATIVO (JSON/DB)
            elif self.declarative_engine:
                # El profile_id en el motor coincide con el clean_name (ej: tgss_base)
                json_profile = self.declarative_engine.store.get_profile(clean_name)
                
                if json_profile:
                    logger.info(f"🔨 Forzando extracción con perfil DECLARATIVO: {json_profile.get('nombre')} ({clean_name})")
                    datos = self.declarative_engine.extract(text, profile=json_profile)
                    datos['_metadata'] = {
                        'tipo_detectado': clean_name,
                        'perfil_usado': True,
                        'metodo': 'FORZADO_MANUAL_DECLARATIVE'
                    }
                else:
                    logger.warning(f"Perfil solicitado no encontrado en ningún motor: {clean_name}")
                    return {NotificationTypes.ERROR: f"Perfil {clean_name} no encontrado"}
            else:
                logger.warning(f"Perfil solicitado no encontrado: {clean_name}")
                return {NotificationTypes.ERROR: f"Perfil {clean_name} no encontrado"}
            
            # Metadata común
            datos['_texto_ocr'] = text
            return datos
            
        except Exception as e:
            logger.error(f"Error en extracción forzada ({profile_classname}): {e}")
            return {NotificationTypes.ERROR: str(e)}

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
        
        logger.info(f"--- INICIO EXTRACCIÓN NOTIFICACIÓN --- (Texto len: {len(texto_completo)})")
        if not texto_completo:
            logger.warning("⚠️ Texto completo está vacío al entrar en extract_notification_data")
            return datos

        # --- 1. INTENTAR CON PERFILES ESPECÍFICOS ---
        try:
             # Ajuste de path para los perfiles que moví antes
            from services.extraction_profiles.notification_profiles import get_notification_profile
            profile = get_notification_profile(texto_completo)
            
            if profile:
                logger.info(f"🔍 Perfil de notificación detectado: {type(profile).__name__}")
                datos_perfil = profile.extract_data(texto_completo)
                datos.update(datos_perfil)
                # Ensure metadata
                datos['_metadata'] = {
                    'tipo_detectado': type(profile).__name__,
                    'perfil_usado': True,
                    'metodo': 'PROFILE'
                }
                return datos
            else:
                logger.info("❌ No se detectó perfil Hardcoded coincidente.")
        except Exception as e:
            logger.warning(f"Error cargando perfil: {e}")

        # --- 1.5. INTENTAR CON MOTOR DECLARATIVO (Hybrid Fallback) ---
        # Si no hay perfil hardcoded, probamos con los JSON de la BD
        if self.declarative_engine:
            try:
                # Detectar si algún perfil JSON coincide
                json_profile = self.declarative_engine.detect_profile(texto_completo)
                if json_profile:
                    logger.info(f"🔍 Perfil DINÁMICO detectado: {json_profile.get('nombre')} ({json_profile.get('id')})")
                    datos_dinamicos = self.declarative_engine.extract(texto_completo, profile=json_profile)
                    
                    # Merge con datos base
                    datos.update(datos_dinamicos)
                    
                    # Asegurar metadata correcta
                    if '_metadata' not in datos: datos['_metadata'] = {}
                    datos['_metadata'].update({
                        'metodo': 'DECLARATIVE_ENGINE_DB',
                        'motor': 'Hybrid v1.0'
                    })
                    
                    return datos
                else:
                    logger.info("❌ No se detectó perfil Dinámico coincidente.")
            except Exception as e:
                logger.error(f"❌ Error en Motor Declarativo: {e}")

        # --- 2. EXTRACCIÓN GENÉRICA (Fallback) ---
        logger.info("⚠️ No se detectó perfil específico. Usando extracción genérica.")
        
        if 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL' in texto_completo.upper():
            datos['organismo'] = 'SEGURIDAD SOCIAL'
        elif 'AGENCIA TRIBUTARIA' in texto_completo.upper() or 'AEAT' in texto_completo.upper():
            datos['organismo'] = 'AGENCIA TRIBUTARIA'

        if 'PROVIDENCIA DE APREMIO' in texto_completo.upper():
            datos['tipo_documento'] = 'PROVIDENCIA DE APREMIO'

        datos['referencia'] = self._extract_with_patterns(texto_completo, self.patterns['referencia'])
        datos['csv'] = self._extract_with_patterns(texto_completo, self.patterns['csv'])
        fecha_raw = self._extract_with_patterns(texto_completo, self.patterns['fecha'])
        datos['fecha'] = self._normalize_date(fecha_raw)
        importe_raw = self._extract_with_patterns(texto_completo, self.patterns.get('importe', []))
        datos['importe'] = self._normalize_amount(importe_raw)

        # NIF Destinatario
        nifs_encontrados = []
        for pat in self.patterns['nif']:
            matches = re.findall(pat, texto_completo, re.IGNORECASE)
            for m in matches:
                m_clean = m.upper().replace('ES', '').strip()
                if len(m_clean) >= 8 and len(m_clean) <= 9:
                     if not m_clean.startswith('Q'):
                        if m_clean not in nifs_encontrados:
                            nifs_encontrados.append(m_clean)
        
        datos['nif'] = nifs_encontrados[0] if nifs_encontrados else ''

        return datos

    # =========================================================================
    # MÉTODOS DE COMPATIBILIDAD CON LA APLICACIÓN (Mesa de Trabajo, etc.)
    # =========================================================================

    def _extract_with_regex(self, text: str, plantilla: dict) -> dict:
        """
        Extrae datos usando:
        1. Motor Avanzado de Perfiles (Providencias, etc.)
        2. Regex Simple por etiquetas (Campo: Valor)
        Llamado directamente por routes_plantilla_test.py
        """
        data = {}

        # --- 1. MOTOR AVANZADO (PERFILES) ---
        try:
            from services.extraction_profiles.notification_profiles import get_notification_profile
            profile = get_notification_profile(text)
            if profile:
                datos_perfil = profile.extract_data(text)
                mapping_keys = {
                    'fecha': ['fecha', 'fecha factura', 'fecha devengo', 'fecha notificacion'],
                    'importe': ['importe', 'total', 'importe total', 'total a ingresar', 'cuota'],
                    'nif': ['nif', 'cif', 'identificador'],
                    'referencia': ['referencia', 'ref', 'expediente'],
                    'providencia_numero': ['providencia', 'nº providencia', 'numero providencia'],
                    'csv': ['csv', 'código seguro verificación'],
                    'periodo': ['periodo', 'ejercicio'],
                    'concepto': ['concepto', 'descripcion'],
                    'importe_principal': ['principal', 'importe principal'],
                    'importe_recargo': ['recargo', 'importe recargo']
                }
                for key_plantilla in plantilla.get('campos', {}).keys():
                    key_norm = key_plantilla.lower().replace('_', ' ').strip()
                    for tipo_dato, posibles in mapping_keys.items():
                        if any(n in key_norm for n in posibles):
                            val = datos_perfil.get(tipo_dato)
                            if val:
                                data[key_plantilla] = val
                            break
                if datos_perfil.get('tipo_documento') and datos_perfil['tipo_documento'] != 'GENÉRICO':
                    data['_metadata'] = {'tipo_detectado': datos_perfil['tipo_documento'], 'perfil_usado': True}
        except Exception as e:
            logger.warning(f"Error en perfil avanzado (_extract_with_regex): {e}")

        # --- 2. REGEX SIMPLE (etiqueta: valor) ---
        for key, desc in plantilla.get('campos', {}).items():
            if key in data:
                continue
            # Buscar por descripción del campo
            m = re.search(re.escape(desc) + r'[:\s]+(.*?)$', text, re.IGNORECASE | re.MULTILINE)
            if m:
                data[key] = m.group(1).strip()
                continue
            # Buscar por nombre de clave
            m = re.search(re.escape(key.replace('_', ' ')) + r'[:\s]+(.*?)$', text, re.IGNORECASE | re.MULTILINE)
            if m:
                data[key] = m.group(1).strip()

        if data:
            if '_metadata' not in data:
                data['_metadata'] = {}
            data['_metadata']['metodo'] = 'HYBRID_REGEX'
        return data or None

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Wrapper que llama al PDFExtractor base y devuelve solo el texto completo (str).
        El PDFExtractor base devuelve una tupla (texto_completo, texto_ultima_pagina, texto_vertical).
        """
        result = super().extract_text_from_pdf(pdf_path)
        if isinstance(result, tuple):
            return result[0]  # texto_completo_horizontal
        return result or ""

    def extract_with_template(self, pdf_path: str, plantilla: dict):
        """
        Método bridging para que PlantillaTestBench funcione con este extractor.
        Usa extract_notification_data y mapea los resultados a la plantilla.
        """
        text = self.extract_text_from_pdf(pdf_path)
        if not text: return {NotificationTypes.ERROR: "Sin texto"}

        # 1. Ejecutar el extractor "Original" del usuario
        extracted_data = self.extract_notification_data(text, "")

        # Adjuntar texto OCR para que el caller lo guarde en BD (búsqueda full-text)
        extracted_data['_texto_ocr'] = text

        # 2. Mapear al formato de la plantilla solicitada
        final_data = {}
        
        # Mapping de claves internas del extractor "Original" -> Posibles nombres en plantilla
        mapping_keys = {
            'fecha': ['fecha', 'fecha factura', 'fecha devengo', 'fecha notificacion'],
            'importe': ['importe', 'total', 'importe total', 'total a ingresar', 'cuota'],
            'nif': ['nif', 'cif', 'identificador'],
            'referencia': ['referencia', 'ref', 'expediente', 'número de referencia'],
            'providencia_numero': ['providencia', 'nº providencia', 'numero providencia'],
            'csv': ['csv', 'código seguro verificación'],
            'periodo': ['periodo', 'ejercicio'],
            'concepto': ['concepto', 'descripcion']
        }
        
        if not plantilla or 'campos' not in plantilla:
            logger.warning("No se proporcionó plantilla válida para extract_with_template. Usando extracción genérica.")
            return extracted_data

        for key_plantilla in plantilla['campos'].keys():
            key_norm = key_plantilla.lower().replace('_', ' ').strip()
            found_value = None
            
            # Intentar encontrar en datos extraídos
            for internal_key, semantic_keys in mapping_keys.items():
                if any(k in key_norm for k in semantic_keys):
                    if extracted_data.get(internal_key):
                        found_value = extracted_data.get(internal_key)
                        break
            
            # Si no se encontró por mapping semántico, buscar si la clave exacta está
            if not found_value and key_plantilla in extracted_data:
                found_value = extracted_data[key_plantilla]
                
            # Si sigue sin encontrarse, intentar búsqueda simple regex "Campo: Valor" (Ultimo recurso)
            if not found_value:
                 pattern = re.escape(plantilla['campos'][key_plantilla]) + r'[:\s]+(.*?)$'
                 m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                 if m: found_value = m.group(1).strip()

            if found_value:
                final_data[key_plantilla] = found_value
        
        # Metadata visual para el usuario
        final_data['_metadata'] = {
            'tipo_documento': extracted_data.get('tipo_documento', 'GENÉRICO'),
            'extraccion_exitosa': True,
            'metodo': 'REGEX_ORIGINAL_NO_AI'
        }
        
        return final_data

    # Compatibilidad para detección automática
    def detectar_plantilla(self, pdf_path: str):
        try:
            from models import Plantilla
            import fitz
            # Extraer solo la primera página para rapidez INICIAL
            doc = fitz.open(pdf_path)
            if len(doc) == 0: return None
            from services.pdf_extractor import PDFExtractor as _Base
            _b = _Base()
            text_p1 = _b._get_horizontal_text_from_page(doc[0])
            doc.close()
            
            # Función auxiliar de búsqueda
            def buscar_en_texto(texto):
                if not texto: return None
                # 1. Intentar con el Motor Declarativo (ExtractionTemplate)
                if self.declarative_engine:
                    profile = self.declarative_engine.detect_profile(texto)
                    if profile:
                        class MatchMock:
                            def __init__(self, p):
                                self.id = p.get('id')
                                self.codigo = f"PROFILE:{p.get('id')}"
                                self.nombre = p.get('nombre')
                                self.categoria_default = p.get('deteccion', {}).get('categoria_default')
                                self.departamento_default = p.get('deteccion', {}).get('departamento_default')
                                self.prioridad_default = p.get('deteccion', {}).get('prioridad_default')
                                self.tipo = 'extraction_template'
                        return MatchMock(profile)

                # 2. Intentar con Plantillas clásicas
                plantillas = Plantilla.query.filter(Plantilla.patron_deteccion.isnot(None)).all()
                text_upper = texto.upper()
                for p in plantillas:
                    if p.patron_deteccion.upper() in text_upper:
                        if not hasattr(p, 'categoria_default'): p.categoria_default = None
                        if not hasattr(p, 'departamento_default'): p.departamento_default = None
                        if not hasattr(p, 'prioridad_default'): p.prioridad_default = None
                        p.tipo = 'plantilla_clasica'
                        return p
                return None

            # ESTRATEGIA: Primero página 1, si falla, todo el documento
            resultado = buscar_en_texto(text_p1)
            if not resultado:
                logger.info("🔍 No detectado en Pág 1, extrayendo texto completo...")
                text_full = self.extract_text_from_pdf(pdf_path)
                resultado = buscar_en_texto(text_full)
            
            return resultado
        except Exception as e:
            logger.error(f"Error detectando plantilla: {e}")
            return None

    def get_todas_plantillas(self):
        try:
            from models import Plantilla
            return {p.codigo: {'nombre': p.nombre, 'campos': p.campos} for p in Plantilla.query.all()}
        except: return {}

    def extract_with_ai(self, texto_completo, texto_ultima_pagina, texto_vertical, **kwargs):
        """
        MOCK COMPLETO: Simula ser IA pero solo imprime logs y llama al regex.
        Cumple estrictamente: NO USAR IA.
        """
        logger.info("extract_with_ai llamado. REDIRIGIENDO A MOTOR REGEX (Usuario solicitó NO IA).")
        print("\n" + "📜 " + "="*58 + "\n📜 EXTRACCIÓN DE NOTIFICACIÓN (Regex Only)\n" + "📜 " + "="*58 + "\n")
        return self.extract_notification_data(texto_completo, texto_vertical)
