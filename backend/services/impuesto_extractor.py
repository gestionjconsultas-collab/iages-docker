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
        '131': r'Modelo\s*131|MODELO\s*131|IRPF\s*(?:-|–)\s*PAGOS\s*FRACCIONADOS|MÓDULOS',
        '115': r'Modelo\s*115|MODELO\s*115',
        '190': r'Modelo\s*190|MODELO\s*190',
        '180': r'Modelo\s*180|MODELO\s*180',
        '216': r'Modelo\s*216|MODELO\s*216|RETENCIONES\s*NO\s*RESIDENTES',
        '296': r'Modelo\s*296|MODELO\s*296|RENTAS\s*DE\s*NO\s*RESIDENTES\s*ANUAL',
        '349': r'Modelo\s*349|MODELO\s*349|OPERACIONES\s*INTRACOMUNITARIAS',
        '347': r'Modelo\s*347|MODELO\s*347',
        '200': r'Modelo\s*200|MODELO\s*200|IMPUESTO\s*SOCIEDADES',
        '100': r'Modelo\s*100|MODELO\s*100|IRPF',
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
        
        Returns:
            dict: {
                'nif': str,
                'modelo': str,
                'es_negativa': bool,
                'sin_actividad': bool,
                'resultado_cero': bool,
                'calidad': str,
                'confianza': float,
                'fecha_presentacion': str,
                'numero_justificante': str,
                'expediente': str,
                'csv': str,
                'razon_social': str,
                'ejercicio': str,
                'periodo': str
            }
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
            ejercicio = self._detect_ejercicio(texto_primera_pagina, expediente=expediente)
            periodo = self._detect_periodo(texto_primera_pagina, expediente=expediente)
            
            # Detectar si es un aplazamiento (ya detectado arriba)
            # is_aplazamiento = self._detect_aplazamiento(texto_primera_pagina) # Ya lo tenemos
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
                'detalle_liquidacion': detalle_liquidacion,
                'ejercicio': ejercicio,
                'periodo': periodo
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
            'detalle_liquidacion': None,
            'ejercicio': None,
            'periodo': None
        }

    # ... (rest of methods) ...

    def _detect_resultado_texto(self, text: str) -> str:
        """
        Detecta la línea del resultado basándose en la posición.
        Toma la primera línea con contenido relevante que aparece DESPUÉS de 'En calidad de:'.
        """
        lines = text.split('\n')
        capture_next = False
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Si ya encontramos la marca, esta línea es el resultado
            if capture_next:
                # Filtrar si es un número de página o pie de página
                if len(line) < 5 and line.isdigit(): continue
                return line
            
            # Buscar la marca de inicio
            if "En calidad de:" in line or "En calidad de" in line:
                capture_next = True
                
        return None

    def _detect_fecha_presentacion(self, text: str) -> str:
        """Detecta fecha de presentación: 'Presentación realizada el: 21-07-2025'"""
        pattern = r'Presentación realizada el:\s*(\d{2}-\d{2}-\d{4}\s+a\s+las\s+\d{2}:\d{2}:\d{2})'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_numero_justificante(self, text: str) -> str:
        """Detecta número de justificante"""
        pattern = r'Número de justificante:\s*(\d+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_expediente(self, text: str) -> str:
        """Detecta expediente/referencia"""
        # Primero: Patrón estándar que evita capturar la 'n' de '(nº registro asignado):'
        pattern1 = r'Expediente/Referencia[^\n]*:\s*([A-Z0-9]{10,})'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            return match1.group(1)
            
        # Fallback: Tabular layouts (como Modelo 200 antiguo)
        pattern2 = r'\b(20\d{2}[A-Z0-9]{11,})\b'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
            return match2.group(1)
            
        return None

    def _detect_csv(self, text: str) -> str:
        """Detecta Código Seguro de Verificación (CSV)"""
        pattern = r'Código Seguro de Verificación:\s*([A-Z0-9]+)'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _detect_razon_social(self, text: str) -> str:
        """Detecta Razón Social / Apellidos y Nombre"""
        pattern = r'Apellidos y Nombre / Razón social:\s*(.+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    
    def _detect_ejercicio(self, text: str, expediente: str = None) -> str:
        """Detecta el Ejercicio (Año) del impuesto"""
        # 1. Intentar deducirlo del expediente si es formato AEAT (20XX...)
        if expediente and re.match(r'^20\d{2}', expediente):
            return expediente[:4]
            
        # 2. Buscar en el texto formatos específicos de recibos AEAT
        # "Presentación realizada el: DD-MM-YYYY" -> Tomamos el año de la fecha si no hay más
        date_match = re.search(r'Presentación realizada el:\s*\d{2}-\d{2}-(20\d{2})', text)
        if date_match:
            return date_match.group(1)

        # 3. Buscar directamente la palabra Ejercicio seguida de un año
        pattern1 = r'Ejercicio[:\s]*(20\d{2})'
        match1 = re.search(pattern1, text, re.IGNORECASE)
        if match1:
            return match1.group(1)
            
        # 4. Buscar "Año" como fallback
        pattern2 = r'Año[:\s]*(20\d{2})'
        match2 = re.search(pattern2, text, re.IGNORECASE)
        if match2:
             return match2.group(1)
             
        # Fallback: buscar año en primeras 30 líneas EXCLUYENDO líneas con fechas completas
        lines = text.split('\n')[:30]
        for line in lines:
            if any(kw in line.lower() for kw in ['presentación', 'presentacion', 'impresión', 'impresion', 'generado', 'fecha']):
                continue
            match_any_year = re.search(r'\b(20\d{2})\b', line)
            if match_any_year:
                return match_any_year.group(1)
                 
        return None

    def _detect_periodo(self, text: str, expediente: str = None) -> str:
        """
        Detecta el periodo (T1, T2, T3, T4, ANUAL, etc.)
        Formatos AEAT: 1T, 2T, 3T, 4T, 0A (Anual), 0M (Mensual?)
        """
        # 1. Intentar deducirlo del expediente AEAT (posiciones 8-9 o similar)
        # En los ejemplos: 2025 131 67... (no parece estar ahí directamente)
        
        # 2. Buscar patrones en el texto
        text_upper = text.upper()
        
        # Trimestres
        if re.search(r'\b1\s*T\b|PRIMER\s*TRIMESTRE', text_upper): return 'T1'
        if re.search(r'\b2\s*T\b|SEGUNDO\s*TRIMESTRE', text_upper): return 'T2'
        if re.search(r'\b3\s*T\b|TERCER\s*TRIMESTRE', text_upper): return 'T3'
        if re.search(r'\b4\s*T\b|CUARTO\s*TRIMESTRE', text_upper): return 'T4'
        
        # Otros (como 2P para pagos fraccionados, común en Modelo 216)
        match_p = re.search(r'\b(\d)\s*P\b', text_upper)
        if match_p:
            return f"P{match_p.group(1)}"
            
        # Mensuales
        months = {
            r'MES\s*0?1|ENERO': '01', r'MES\s*0?2|FEBRERO': '02', r'MES\s*0?3|MARZO': '03',
            r'MES\s*0?4|ABRIL': '04', r'MES\s*0?5|MAYO': '05', r'MES\s*0?6|JUNIO': '06',
            r'MES\s*0?7|JULIO': '07', r'MES\s*0?8|AGOSTO': '08', r'MES\s*0?9|SEPTIEMBRE': '09',
            r'MES\s*10|OCTUBRE': '10', r'MES\s*11|NOVIEMBRE': '11', r'MES\s*12|DICIEMBRE': '12'
        }
        for pattern, code in months.items():
            if re.search(pattern, text_upper):
                return code
                
        # Anual
        if re.search(r'\b0\s*A\b|ANUAL|RESUMEN\s*ANUAL', text_upper): return 'ANUAL'
        
        # 3. Fallback: Deducir por fecha de presentación si no hay nada en el texto
        # Si se presenta en Abril -> T1, Julio -> T2, Octubre -> T3, Enero -> T4 (año anterior)
        # Este fallback es útil para los recibos AEAT que no tienen el periodo en pág 1
        fecha_pres = self._detect_fecha_presentacion(text)
        if fecha_pres:
            # Formato: 06-04-2025 a las ...
            m_fecha = re.search(r'\d{2}-(\d{2})-\d{4}', fecha_pres)
            if m_fecha:
                mes_pres = int(m_fecha.group(1))
                if mes_pres in [1, 2]: return 'ANUAL' # O T4, pero usualmente 296/390 son en Ene/Feb
                if mes_pres in [4, 5]: return 'T1'
                if mes_pres in [7, 8]: return 'T2'
                if mes_pres in [10, 11]: return 'T3'

        return None

    def _detect_aplazamiento(self, text: str) -> bool:
        """Detecta si el documento es una concesión de aplazamiento"""
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
        """
        Extrae bloques de 'Número Liquidación' del ANEXO I (plazos de pago).
        Los valores vienen uno por línea — se recogen tokens y se agrupan en plazos de 5+fecha.
        Se detiene al encontrar 'DETALLE DE LA LIQUIDACIÓN' (inicio del Anexo II).
        """
        try:
            text_upper = text.upper()

            # 1. Encontrar inicio: primera "Número Liquidación:"
            idx_start = -1
            for variant in ['NÚMERO LIQUIDACIÓN', 'NUMERO LIQUIDACION',
                            'NÚMERO LIQUIDACION', 'NUMERO LIQUIDACIÓN']:
                idx = text_upper.find(variant)
                if idx != -1 and (idx_start == -1 or idx < idx_start):
                    idx_start = idx

            if idx_start == -1:
                logger.warning("No se encontró 'Número Liquidación' en el documento")
                return None

            # 2. Encontrar fin: inicio del Anexo II
            idx_end = -1
            for variant in ['DETALLE DE LA LIQUIDACIÓN', 'DETALLE DE LA LIQUIDACION']:
                idx = text_upper.find(variant, idx_start)
                if idx != -1 and (idx_end == -1 or idx < idx_end):
                    idx_end = idx

            zona = text[idx_start:idx_end] if idx_end != -1 else text[idx_start:]
            logger.info(f"📋 Zona ANEXO I: {len(zona)} chars")

            # 3. Dividir en bloques por "Número Liquidación:"
            bloques_raw = re.split(r'(?i)N[úu]mero\s+Liquidaci[óo]n\s*:', zona)
            bloques_raw = bloques_raw[1:]  # Saltar texto previo al primer bloque

            if not bloques_raw:
                return None

            # Regexes de token — cada valor viene en su propia línea
            AMOUNT_RE = re.compile(r'^-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}$')  # 588,14 / 1.190,08
            DATE_RE   = re.compile(r'^\d{2}-\d{2}-\d{4}$')                  # 22-06-2026
            SEP_RE    = re.compile(r'^-{3,}')                                # ----...
            SKIP_RE   = re.compile(
                r'(?i)concepto|fecha\s+de\s+inter|importe\s+principal|recargo|'
                r'total\s+(deuda|general)|intereses|plazo|vencimiento|apremio|'
                r'deuda\s*\(|n\.?i\.?f|expediente|p[aá]gina|referencia|deudor|'
                r'anexo|acuerdo|identificaci|si\s+en\s+el\s+momento'
            )

            liquidaciones = []

            for bloque in bloques_raw:
                lines = [l.strip() for l in bloque.split('\n') if l.strip()]
                if not lines:
                    continue

                numero = lines[0].strip()
                concepto = None
                fecha_intereses = None
                pre_amounts = []   # importes antes del separador ----
                pre_dates   = []   # fechas de vencimiento antes del separador
                post_amounts = []  # importes después del separador (subtotal)
                past_sep = False

                for line in lines[1:]:
                    if re.match(r'(?i)concepto\s*:', line):
                        concepto = re.sub(r'(?i)concepto\s*:\s*', '', line).strip()
                        continue
                    if re.match(r'(?i)fecha\s+de\s+intereses\s*:', line):
                        m = re.search(r'(\d{2}-\d{2}-\d{4})', line)
                        if m:
                            fecha_intereses = m.group(1)
                        continue
                    if SKIP_RE.search(line):
                        continue
                    if SEP_RE.match(line):
                        past_sep = True
                        continue
                    if DATE_RE.match(line):
                        if not past_sep:
                            pre_dates.append(line)
                        continue
                    if AMOUNT_RE.match(line):
                        val = self._parse_amount(line)
                        if past_sep:
                            post_amounts.append(val)
                        else:
                            pre_amounts.append(val)

                # Agrupar en plazos: cada plazo = 5 importes consecutivos + 1 fecha
                plazos = []
                num_plazos = min(len(pre_amounts) // 5, len(pre_dates))
                for j in range(num_plazos):
                    b = j * 5
                    plazos.append({
                        'importe_principal':   pre_amounts[b],
                        'recargo_apremio':     pre_amounts[b + 1],
                        'importe_total_deuda': pre_amounts[b + 2],
                        'importe_intereses':   pre_amounts[b + 3],
                        'importe_total_plazo': pre_amounts[b + 4],
                        'fecha_vencimiento':   pre_dates[j],
                    })

                # Subtotal: primeros 5 importes tras el separador
                subtotal = None
                if len(post_amounts) >= 5:
                    subtotal = {
                        'importe_principal':   post_amounts[0],
                        'recargo_apremio':     post_amounts[1],
                        'importe_total_deuda': post_amounts[2],
                        'importe_intereses':   post_amounts[3],
                        'importe_total_plazo': post_amounts[4],
                    }

                liquidaciones.append({
                    'numero_liquidacion': numero,
                    'concepto': concepto,
                    'fecha_intereses': fecha_intereses,
                    'plazos': plazos,
                    'subtotal': subtotal,
                })

            total_plazos = sum(len(l['plazos']) for l in liquidaciones)
            logger.info(f"✅ {len(liquidaciones)} liquidaciones, {total_plazos} plazos extraídos")
            return liquidaciones if liquidaciones else None

        except Exception as e:
            logger.error(f"Error extrayendo detalle de liquidación: {e}")
            return None
    
    def _parse_amount(self, amount_str: str) -> float:
        """Convierte string de importe a float (1.234,56 -> 1234.56)"""
        try:
            # Eliminar puntos de miles y reemplazar coma decimal por punto
            clean = amount_str.replace('.', '').replace(',', '.')
            return float(clean)
        except:
            return 0.0
    
    def _detect_nif(self, text: str) -> str:
        """
        Detecta NIF en el texto.
        Formatos soportados:
        - A12345678 (CIF)
        - 12345678A (DNI)
        - A1234567B (NIE)
        """
        # Patrón para NIF español (CIF, DNI, NIE)
        nif_pattern = r'\b([A-Z]\d{8}|[A-Z]\d{7}[A-Z]|\d{8}[A-Z])\b'
        matches = re.findall(nif_pattern, text.upper())
        
        if matches:
            # Filtrar NIFs comunes que no son válidos
            for match in matches:
                # Evitar patrones como "A12345678" que podrían ser códigos
                if len(match) == 9:
                    return match
        
        return None
    
    def _detect_modelo(self, text: str) -> str:
        """Detecta modelo de impuesto en el texto"""
        text_upper = text.upper()
        
        # Buscar en orden de especificidad (más específico primero)
        for modelo, pattern in sorted(self.MODELO_PATTERNS.items(), key=lambda x: len(x[1]), reverse=True):
            if re.search(pattern, text_upper, re.IGNORECASE):
                return modelo
        
        return None
    
    def _detect_estado(self, text: str) -> dict:
        """Detecta estados informativos (negativa, sin actividad, resultado cero)"""
        text_upper = text.upper()
        
        return {
            'negativa': bool(re.search(self.ESTADO_PATTERNS['negativa'], text_upper, re.IGNORECASE)),
            'sin_actividad': bool(re.search(self.ESTADO_PATTERNS['sin_actividad'], text_upper, re.IGNORECASE)),
            'resultado_cero': bool(re.search(self.ESTADO_PATTERNS['resultado_cero'], text_upper, re.IGNORECASE)),
        }
    
    def _detect_calidad(self, text: str) -> str:
        """
        Detecta calidad del declarante (Colaborador o Titular).
        Returns:
            str: 'Colaborador', 'Titular', o None
        """
        text_upper = text.upper()
        
        if re.search(self.CALIDAD_PATTERNS['colaborador'], text_upper, re.IGNORECASE):
            return 'Colaborador'
        if re.search(self.CALIDAD_PATTERNS['titular'], text_upper, re.IGNORECASE):
            return 'Titular'
        
        return None
    
    def _calculate_confidence(self, nif, modelo, calidad) -> float:
        """
        Calcula confianza de la extracción (0.0 - 1.0).
        
        Pesos:
        - NIF: 40%
        - Modelo: 40%
        - Calidad: 20%
        """
        score = 0.0
        
        if nif:
            score += 0.4
        if modelo:
            score += 0.4
        if calidad:
            score += 0.2
        
        return round(score, 2)
