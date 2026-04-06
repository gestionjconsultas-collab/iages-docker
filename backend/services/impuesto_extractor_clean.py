# backend/services/impuesto_extractor.py
import re
import fitz  # PyMuPDF
from services.pdf_extractor import PDFExtractor
from utils.logger import logger


class ImpuestoExtractor(PDFExtractor):
    """Extractor especializado para documentos de impuestos"""
    
    # Patrones de detección de modelos de impuestos
    MODELO_PATTERNS = {
        '303': r'Modelo\s*303|MODELO\s*303|IVA\s*TRIMESTRAL',
        '111': r'Modelo\s*111|MODELO\s*111|RETENCIONES',
        '130': r'Modelo\s*130|MODELO\s*130|IRPF\s*TRIMESTRAL',
        '115': r'Modelo\s*115|MODELO\s*115',
        '190': r'Modelo\s*190|MODELO\s*190',
        '180': r'Modelo\s*180|MODELO\s*180',
        '349': r'Modelo\s*349|MODELO\s*349|OPERACIONES\s*INTRACOMUNITARIAS',
        '347': r'Modelo\s*347|MODELO\s*347',
        '200': r'Modelo\s*200|MODELO\s*200|IMPUESTO\s*SOCIEDADES',
        '100': r'Modelo\s*100|MODELO\s*100|IRPF',
        '216': r'Modelo\s*216|MODELO\s*216',
        '202': r'Modelo\s*202|MODELO\s*202',
        '390': r'Modelo\s*390|MODELO\s*390',
    }
    
    # Patrones de detección de estados informativos
    ESTADO_PATTERNS = {
        'negativa': r'NEGATIVA|DECLARACIÓN\s*NEGATIVA|RESULTADO\s*NEGATIVO|DECLARACION\s*NEGATIVA',
        'sin_actividad': r'SIN\s*ACTIVIDAD|NO\s*ACTIVIDAD|SIN\s*OPERACIONES|NO\s*OPERACIONES',
        'resultado_cero': r'RESULTADO\s*CERO|RESULTADO:\s*0[,.]00|RESULTADO\s*0[,.]00|RESULTADO\s*0\s*€',
    }
    
    # Patrones de detección de calidad del declarante
    CALIDAD_PATTERNS = {
        'colaborador': r'En\s*calidad\s*de:\s*Colaborador|COLABORADOR\s*SOCIAL|CALIDAD:\s*COLABORADOR',
        'titular': r'En\s*calidad\s*de:\s*Titular|TITULAR|CALIDAD:\s*TITULAR',
    }
    
    def extract_tax_data(self, pdf_path: str) -> dict:
        """
        Extrae datos específicos de documentos de impuestos.
        Solo procesa la PRIMERA página para optimizar rendimiento.
        """
        try:
            # Extraer texto de primera página para detección inicial
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                logger.warning(f"PDF vacío: {pdf_path}")
                return self._empty_result()
            
            first_page = doc[0]
            texto_primera_pagina = first_page.get_text()
            
            # Detectar si es aplazamiento
            is_aplazamiento = self._detect_aplazamiento(texto_primera_pagina)
            
            # Si es aplazamiento, necesitamos leer TOODAS las páginas porque la tabla suele estar en anexos
            if is_aplazamiento:
                texto_completo = ""
                for page in doc:
                    texto_completo += page.get_text() + "\n"
                logger.info(f"Aplazamiento detectado: Leyendo {len(doc)} páginas para extracción completa")
            else:
                texto_completo = texto_primera_pagina
                
            doc.close()
            
            if not texto_completo or len(texto_completo.strip()) < 20:
                logger.warning(f"No se pudo extraer texto suficiente de {pdf_path}")
                return self._empty_result()
            
            # Detectar campos básicos
            nif = self._detect_nif(texto_primera_pagina)
            modelo = self._detect_modelo(texto_primera_pagina)
            estado = self._detect_estado(texto_primera_pagina)
            calidad = self._detect_calidad(texto_primera_pagina)
            
            # Detectar campos extendidos (Solicitud usuario)
            fecha_presentacion = self._detect_fecha_presentacion(texto_primera_pagina)
            numero_justificante = self._detect_numero_justificante(texto_primera_pagina)
            expediente = self._detect_expediente(texto_primera_pagina)
            csv = self._detect_csv(texto_primera_pagina)
            razon_social = self._detect_razon_social(texto_primera_pagina)
            resultado_texto = self._detect_resultado_texto(texto_primera_pagina)
            
            detalle_liquidacion = None
            if is_aplazamiento:
                detalle_liquidacion = self._extract_detalle_liquidacion(texto_completo)

            logger.info(f"Datos extraídos - NIF: {nif}, Modelo: {modelo}, Aplazamiento: {is_aplazamiento}")
            
            return {
                'nif': nif,
                'modelo': modelo,
                'es_negativa': estado.get('negativa', False),
                'sin_actividad': estado.get('sin_actividad', False),
                'resultado_cero': estado.get('resultado_cero', False),
                'calidad': calidad,
                'confianza': self._calculate_confidence(nif, modelo, calidad),
                'fecha_presentacion': fecha_presentacion,
                'numero_justificante': numero_justificante,
                'expediente': expediente,
                'csv': csv,
                'razon_social': razon_social,
                'resultado_texto': resultado_texto,
                'is_aplazamiento': is_aplazamiento,
                'detalle_liquidacion': detalle_liquidacion
            }
        except Exception as e:
            logger.error(f"Error extrayendo datos de impuesto: {e}")
            return self._empty_result()
    
    def _empty_result(self) -> dict:
        """Retorna resultado vacío"""
        return {
            'nif': None,
            'modelo': None,
            'es_negativa': False,
            'sin_actividad': False,
            'resultado_cero': False,
            'calidad': None,
            'confianza': 0.0,
            'fecha_presentacion': None,
            'numero_justificante': None,
            'expediente': None,
            'csv': None,
            'razon_social': None,
            'resultado_texto': None,
            'is_aplazamiento': False,
            'detalle_liquidacion': None
        }

    # ... (rest of methods unchanged until detect_nif/expediente)

    def _detect_resultado_texto(self, text: str) -> str:
        lines = text.split('\n')
        capture_next = False
        for line in lines:
            line = line.strip()
            if not line: continue
            if capture_next:
                if len(line) < 5 and line.isdigit(): continue
                return line
            if "En calidad de:" in line or "En calidad de" in line:
                capture_next = True
        return None

    def _detect_fecha_presentacion(self, text: str) -> str:
        pattern = r'Presentación realizada el:\s*(\d{2}-\d{2}-\d{4}\s+a\s+las\s+\d{2}:\d{2}:\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_numero_justificante(self, text: str) -> str:
        pattern = r'Número de justificante:\s*(\d+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_expediente(self, text: str) -> str:
        """Detecta expediente/referencia"""
        # Patrones ordenados por prioridad (más específico primero)
        patterns = [
            r'Número\s+de\s+expediente\s*:?\s*([A-Z0-9]+)',  # Número de expediente: ...
            r'Expediente\s*:?\s*([A-Z0-9]+)',                # Expediente: ...
            r'Referencia\s*:?\s*([A-Z0-9]+)',                # Referencia: ...
            r'Expediente/Referencia.*?:?\s*([A-Z0-9]+)'      # Genérico
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

    def _detect_csv(self, text: str) -> str:
        pattern = r'Código Seguro de Verificación:\s*([A-Z0-9]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_razon_social(self, text: str) -> str:
        pattern = r'Apellidos y Nombre / Razón social:\s*(.+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def _detect_aplazamiento(self, text: str) -> bool:
        keywords = [
            r'CONCESIÓN DEL APLAZAMIENTO',
            r'CONCESION DEL APLAZAMIENTO',
            r'FRACCIONAMIENTO DE PAGO',
            r'APLAZAMIENTO/FRACCIONAMIENTO'
        ]
        for keyword in keywords:
            if re.search(keyword, text, re.IGNORECASE):
                logger.info(f"✅ Documento de aplazamiento detectado: {keyword}")
                return True
        return False
    
    def _extract_detalle_liquidacion(self, text: str) -> list:
        # (El mismo que arreglé antes, versión limpia)
        try:
            idx_anexo = text.upper().find("ANEXO II")
            if idx_anexo == -1:
                idx_anexo = text.upper().rfind("ANEXO II")
            
            if idx_anexo != -1:
                texto_anexo = text[idx_anexo:]
                match_detalle = re.search(r'DETALLE DE LA LIQUIDACIÓN', texto_anexo, re.IGNORECASE)
                if match_detalle:
                    detalle_text = texto_anexo[match_detalle.end():]
                else:
                    detalle_text = texto_anexo
            else:
                detalle_text = text[-10000:]
            
            lines = detalle_text.split('\n')
            current_cuota = {}
            state = 0
            cuotas = [] 
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line: continue
                
                if state == 0:
                    match_ref = re.search(r'([A-Z0-9]{15,})', line)
                    if match_ref:
                        ref = match_ref.group(1)
                        if len(ref) > 15 and not ref.startswith('B66'): 
                            current_cuota = {'numero_liquidacion': ref}
                            state = 1
                elif state == 1:
                    match = re.search(r'([\d,.]+)\s+(\d{2}-\d{2}-\d{4})\s+(\d{2}-\d{2}-\d{4})', line)
                    if match:
                        current_cuota['importe_principal'] = self._parse_amount(match.group(1))
                        current_cuota['fecha_desde'] = match.group(2)
                        current_cuota['fecha_hasta'] = match.group(3)
                        state = 2
                    elif re.search(r'([A-Z0-9]{15,})', line):
                        ref_match = re.search(r'([A-Z0-9]{15,})', line)
                        ref = ref_match.group(1)
                        if len(ref) > 15:
                            current_cuota = {'numero_liquidacion': ref}
                            state = 1
                elif state == 2:
                    if line.isdigit():
                        current_cuota['dias'] = int(line)
                        state = 3
                elif state == 3:
                    if re.match(r'^[\d,.]+$', line):
                        val_str = line
                        if '.' in val_str and ',' not in val_str:
                            amount = float(val_str)
                        else:
                            amount = self._parse_amount(val_str)
                        current_cuota['tipo_interes'] = amount
                        state = 4
                elif state == 4:
                    if re.match(r'^[\d,.]+$', line):
                        current_cuota['intereses'] = self._parse_amount(line)
                        state = 5
                elif state == 5:
                    if re.match(r'^[\d,.]+$', line):
                        current_cuota['total_intereses'] = self._parse_amount(line)
                        cuotas.append(current_cuota)
                        state = 0
            
            logger.info(f"✅ Extraídas {len(cuotas)} cuotas con parser de estados")
            return cuotas
        except Exception as e:
            logger.error(f"Error extrayendo detalle de liquidación: {e}")
            return None
    
    def _parse_amount(self, amount_str: str) -> float:
        try:
            clean = amount_str.replace('.', '').replace(',', '.')
            return float(clean)
        except:
            return 0.0
    
    def _detect_nif(self, text: str) -> str:
        """
        Detecta NIF en el texto.
        Prioriza la búsqueda con etiqueta 'N.I.F.:'
        """
        # 1. Búsqueda específica con etiqueta (Más confiable)
        label_pattern = r'(?:N\.I\.F\.|NIF)\s*:?\s*([A-Z0-9]{9})'
        match = re.search(label_pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # 2. Fallback: Patrón general
        nif_pattern = r'\b([A-Z]\d{8}|[A-Z]\d{7}[A-Z]|\d{8}[A-Z])\b'
        matches = re.findall(nif_pattern, text.upper())
        if matches:
            for match in matches:
                # Evitar patrones como "A12345678" que podrían ser códigos
                if len(match) == 9:
                    return match
        return None
    
    def _detect_modelo(self, text: str) -> str:
        text_upper = text.upper()
        for modelo, pattern in sorted(self.MODELO_PATTERNS.items(), key=lambda x: len(x[1]), reverse=True):
            if re.search(pattern, text_upper, re.IGNORECASE):
                return modelo
        return None
    
    def _detect_estado(self, text: str) -> dict:
        text_upper = text.upper()
        return {
            'negativa': bool(re.search(self.ESTADO_PATTERNS['negativa'], text_upper, re.IGNORECASE)),
            'sin_actividad': bool(re.search(self.ESTADO_PATTERNS['sin_actividad'], text_upper, re.IGNORECASE)),
            'resultado_cero': bool(re.search(self.ESTADO_PATTERNS['resultado_cero'], text_upper, re.IGNORECASE)),
        }
    
    def _detect_calidad(self, text: str) -> str:
        text_upper = text.upper()
        if re.search(self.CALIDAD_PATTERNS['colaborador'], text_upper, re.IGNORECASE):
            return 'Colaborador'
        if re.search(self.CALIDAD_PATTERNS['titular'], text_upper, re.IGNORECASE):
            return 'Titular'
        return None
    
    def _calculate_confidence(self, nif, modelo, calidad) -> float:
        score = 0.0
        if nif: score += 0.4
        if modelo: score += 0.4
        if calidad: score += 0.2
        return round(score, 2)
