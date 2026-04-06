# backend/cocoindex/pdf_partitioner.py
"""
PDF Partitioner usando técnicas de CocoIndex
Particiona PDF en elementos estructurados para mejor extracción con regex
"""

import pypdf
from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class PdfElement:
    """Elemento extraído del PDF"""
    page_number: int
    element_type: str  # 'header', 'body', 'footer', 'table'
    text: str
    line_number: int
    confidence: float

class PdfPartitioner:
    """
    Particiona PDF en elementos estructurados
    Inspirado en CocoIndex pero standalone para uso con regex
    """
    
    def partition_pdf(self, pdf_path: str) -> List[PdfElement]:
        """
        Particiona PDF en elementos estructurados
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Lista de elementos con su tipo y posición
        """
        elements = []
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                
                for page_num, page in enumerate(reader.pages, 1):
                    # Extraer texto con posiciones
                    page_elements = self._extract_page_elements(page, page_num)
                    elements.extend(page_elements)
        except Exception as e:
            print(f"⚠️ Error particionando PDF: {e}")
            return []
        
        return elements

    def find_nif_early_exit(self, pdf_path: str, max_pages: int = 15) -> Optional[dict]:
        """
        Busca NIF página a página y se detiene al encontrar uno que esté en la BD.
        Evita procesar el documento completo si no es necesario (Optic para archivos grandes).
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                total_pages = len(reader.pages)
                pages_to_scan = min(total_pages, max_pages)
                
                print(f"🔍 Iniciando búsqueda temprana de NIF (escaneando hasta {pages_to_scan} páginas)...")
                
                for page_num in range(pages_to_scan):
                    page = reader.pages[page_num]
                    # Extraer elementos de esta página únicamente
                    elements = self._extract_page_elements(page, page_num + 1)
                    
                    # Buscar NIF en estos elementos
                    result = self.find_nif_in_elements(elements)
                    
                    # Si encontramos un NIF que existe en BD, cortamos el proceso (Early Exit)
                    if result and result.get('in_db'):
                        print(f"✅ NIF ENCONTRADO TEMPRANO (Página {page_num+1}): {result['nif']}")
                        result['early_exit'] = True
                        result['page_found'] = page_num + 1
                        return result
                
                print("ℹ️ Búsqueda temprana finalizada sin match en BD.")
                return None
        except Exception as e:
            print(f"⚠️ Error en búsqueda temprana de NIF: {e}")
            return None
    
    def _extract_page_elements(self, page, page_num: int) -> List[PdfElement]:
        """Extrae elementos de una página con clasificación"""
        elements = []
        
        # Obtener texto completo
        text = page.extract_text()
        
        if not text:
            return elements
        
        # Dividir en líneas
        lines = text.split('\n')
        
        # Clasificar líneas por tipo
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Detectar tipo de elemento
            element_type = self._classify_line(line, i, len(lines))
            
            elements.append(PdfElement(
                page_number=page_num,
                element_type=element_type,
                text=line,
                line_number=i,
                confidence=0.9
            ))
        
        return elements
    
    def _classify_line(self, line: str, line_num: int, total_lines: int) -> str:
        """Clasifica una línea según su contenido y posición"""
        
        # Header: primeras 5 líneas o texto todo mayúsculas
        if line_num < 5 or (line.isupper() and len(line) > 10):
            return 'header'
        
        # Footer: últimas 2 líneas
        if line_num >= total_lines - 2:
            return 'footer'
        
        # Tabla: contiene múltiples números o separadores
        if re.search(r'(\d+\s+){3,}', line) or '\t' in line:
            return 'table'
        
        # Body: resto
        return 'body'
    
    def find_nif_in_elements(self, elements: List[PdfElement]) -> Optional[dict]:
        """
        Busca NIF en elementos particionados con regex mejorado
        
        Estrategia:
        1. Buscar en líneas que contengan "NIF", "CIF", "N.I.F."
        2. Buscar en headers (primeras líneas)
        3. Buscar en body como último recurso
        4. Filtrar números de certificado y referencias
        5. Priorizar NIFs que existen en BD, pero aceptar otros como fallback
        
        Returns:
            dict con 'nif', 'method', 'confidence', 'context' o None
        """
        
        # Patrón de NIF mejorado - acepta TODOS los formatos españoles
        # - NIF empresa: [A-Z]\d{8} (ej: B12345678)
        # - NIF empresa con 0: 0[A-HJ-NP-Z]\d{8} (ej: 0B67418087, 0B13734470)
        # - NIF persona: \d{8}[A-Z] (ej: 12345678A)
        # - NIE numérico 9 dígitos: [0-2]\d{7}[A-Z] (ej: 046482255Z)
        # - NIE numérico 10 dígitos: [0-2]\d{8}[A-Z] (ej: 026318467G, 055653908A)
        # - NIE con letra: [XYZ]\d{7}[A-Z] (ej: Y4975836F, X1234567A)
        # - NIE con 0Y/0X/0Z: 0[XYZ]\d{7}[A-Z] (ej: 0Y4975836F, 0X5501465A - se limpiará después)
        # Usa \s* para hacer el espacio opcional (permite NIFs pegados)
        nif_pattern = r'(?:^|\s*)([A-HJ-NP-Z]\d{8}|0[A-HJ-NP-Z]\d{8,9}|\d{8}[A-Z]|[0-2]\d{7,8}[A-Z]|0[XYZ]\d{7}[A-Z]|[XYZ]\d{7}[A-Z])(?:\s|$|:)'
        
        # Palabras clave que indican NIF cercano
        nif_keywords = ['NIF', 'CIF', 'N.I.F.', 'C.I.F.', 'DESTINATARIO', 'DEUDOR', 'OBLIGADO']
        
        # Colectar todos los candidatos
        candidates = []
        
        # 1. PRIORIDAD ALTA: Buscar en líneas con keywords específicos
        for element in elements:
            if element.element_type in ['header', 'body']:
                # Verificar si contiene keyword
                text_upper = element.text.upper()
                has_keyword = any(kw in text_upper for kw in nif_keywords)
                
                if has_keyword:
                    # Buscar NIF en esta línea
                    match = re.search(nif_pattern, element.text)
                    if match:
                        nif = match.group(1).strip()
                        
                        # Limpiar 0X, 0Y, 0Z -> X, Y, Z (el 0 NO es parte del NIE)
                        # Pero NO limpiar 0A, 0B, 0C... (el 0 SÍ es parte del NIF de empresa)
                        if len(nif) == 10 and nif[0] == '0' and nif[1] in ['X', 'Y', 'Z']:
                            nif = nif[1:]  # Quitar el 0 inicial
                        
                        # Validar que no sea número de certificado
                        if not self._is_false_positive(nif, element.text, elements):
                            in_db = self._validate_nif_in_db(nif)
                            candidates.append({
                                'nif': nif,
                                'method': 'regex_keyword',
                                'confidence': 0.95,
                                'context': element.text,
                                'element_type': element.element_type,
                                'in_db': in_db
                            })
                            # Si está en BD, retornar inmediatamente
                            if in_db:
                                return candidates[-1]
        
        # 2. PRIORIDAD MEDIA: Buscar en headers (primeras 10 líneas)
        for element in elements[:10]:
            if element.element_type == 'header':
                match = re.search(nif_pattern, element.text)
                if match:
                    nif = match.group(1).strip()
                    if not self._is_false_positive(nif, element.text, elements):
                        in_db = self._validate_nif_in_db(nif)
                        candidates.append({
                            'nif': nif,
                            'method': 'regex_header',
                            'confidence': 0.85,
                            'context': element.text,
                            'element_type': element.element_type,
                            'in_db': in_db
                        })
                        # Si está en BD, retornar inmediatamente
                        if in_db:
                            return candidates[-1]
        
        # 3. PRIORIDAD BAJA: Buscar en todo el body
        for element in elements:
            if element.element_type == 'body':
                match = re.search(nif_pattern, element.text)
                if match:
                    nif = match.group(1).strip()
                    if not self._is_false_positive(nif, element.text, elements):
                        in_db = self._validate_nif_in_db(nif)
                        candidates.append({
                            'nif': nif,
                            'method': 'regex_body',
                            'confidence': 0.70,
                            'context': element.text,
                            'element_type': element.element_type,
                            'in_db': in_db
                        })
                        # Si está en BD, retornar inmediatamente
                        if in_db:
                            return candidates[-1]
        
        # Si hay candidatos pero ninguno en BD, retornar el mejor (mayor confianza)
        if candidates:
            best = max(candidates, key=lambda x: x['confidence'])
            return best
        
        return None
    
    def _is_false_positive(self, nif: str, context: str, all_elements: List[PdfElement]) -> bool:
        """
        Detecta si el NIF es un falso positivo (número de certificado, referencia, etc.)
        
        Args:
            nif: NIF candidato
            context: Línea donde se encontró
            all_elements: Todos los elementos para contexto adicional
            
        Returns:
            True si es falso positivo, False si es NIF válido
        """
        context_upper = context.upper()
        
        # FILTRO 1: Código DIR3 (código de oficina de Seguridad Social)
        # Ejemplo: "Código DIR3: EA0042309"
        if 'DIR3' in context_upper and nif in context:
            return True
        
        # FILTRO 2: Códigos que empiezan con EA (códigos DIR3)
        if nif.startswith('EA'):
            return True
        
        # FILTRO 3: Lista de keywords que indican que NO es un NIF
        # IMPORTANTE: Solo rechazar si el NIF NO está etiquetado como "NIF" o "CIF"
        false_positive_keywords = [
            'CERTIFICADO',
            'Nº CERTIFICADO',
            'N° CERTIFICADO',
            'CLAVE DE LIQUIDACIÓN',
            'CLAVE LIQUIDACIÓN',
            'EXPEDIENTE',
            'NÚMERO DE EXPEDIENTE'
        ]
        
        # Si el contexto contiene keywords de falso positivo, verificar si está etiquetado como NIF
        for keyword in false_positive_keywords:
            if keyword in context_upper:
                # Si la línea contiene "NIF" o "CIF", es un NIF válido, no rechazar
                if 'NIF' in context_upper or 'CIF' in context_upper:
                    continue
                # Si no tiene etiqueta NIF/CIF y está cerca del keyword, rechazar
                if nif in context:
                    return True
        
        # Patrón específico de números de certificado (suelen ser más largos)
        # Ejemplo: "Nº Certificado: 2559039109421" - no es NIF
        if re.search(r'CERTIFICADO.*\d{10,}', context_upper):
            return True
        
        # Si el NIF empieza con 'R' o 'L' seguido de números, suele ser referencia
        # Ejemplo: R08610, L91553680 (estos son códigos de oficina/referencia)
        if re.match(r'^[RL]\d{5,}$', nif):
            return True
        
        return False
    
    def _validate_nif_in_db(self, nif: str) -> bool:
        """
        Valida si el NIF existe en la base de datos (tabla empresas)
        
        Args:
            nif: NIF a validar
            
        Returns:
            True si existe en BD, False si no
        """
        try:
            from models import db
            from sqlalchemy import text
            
            # Buscar en tabla empresas
            query = text("""
            SELECT COUNT(*) as count
            FROM empresas
            WHERE nif = :nif
            """)
            
            result = db.session.execute(query, {'nif': nif}).fetchone()
            exists = result[0] > 0 if result else False
            
            return exists
            
        except Exception as e:
            print(f"   ⚠️ Error validando NIF en BD: {e}")
            # Si hay error en BD, aceptar el NIF (mejor falso positivo que perder datos)
            return True
    
    def get_text_from_elements(self, elements: List[PdfElement]) -> str:
        """Reconstruye texto completo desde elementos"""
        return '\n'.join(elem.text for elem in elements)


# Instancia singleton
_partitioner_instance = None

def get_pdf_partitioner() -> PdfPartitioner:
    """Obtiene instancia singleton del partitioner"""
    global _partitioner_instance
    
    if _partitioner_instance is None:
        _partitioner_instance = PdfPartitioner()
    
    return _partitioner_instance
