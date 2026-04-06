# backend/services/pdf_extractor.py
# VERSIÓN COMPLETA CON OCR TESSERACT Y ANÁLISIS MULTI-ESTRATEGIA

import fitz  # PyMuPDF
import google.generativeai as genai
import json
import re
import os
import platform
import shutil
from flask import current_app
import pytesseract
from PIL import Image
from itertools import permutations
from constants import NotificationTypes
from utils.logger import logger


# Tasas de IVA a buscar
VAT_RATES = [21.0, 10.0, 4.0, 12.0, 10.5, 7.5, 5.0, 2.0, 1.0, 0.0]

def configurar_tesseract():
    """
    Configura la ruta de Tesseract de forma multiplataforma.
    
    Prioridad de búsqueda:
    1. Variable de entorno TESSERACT_PATH
    2. Tesseract en el PATH del sistema
    3. Ubicaciones comunes según el sistema operativo
    
    Returns:
        str: Ruta al ejecutable de Tesseract, o None si no se encuentra
    """
    # 1. Primero verificar variable de entorno
    tesseract_env = os.getenv('TESSERACT_PATH')
    if tesseract_env and os.path.exists(tesseract_env):
        logger.info(f"Tesseract encontrado en variable de entorno: {tesseract_env}")
        return tesseract_env
    
    # 2. Intentar encontrar en el PATH del sistema
    tesseract_cmd = shutil.which('tesseract')
    if tesseract_cmd:
        logger.info(f"Tesseract encontrado en PATH del sistema: {tesseract_cmd}")
        return tesseract_cmd
    
    # 3. Buscar en ubicaciones comunes según el sistema operativo
    sistema = platform.system()
    rutas_comunes = []
    
    if sistema == 'Windows':
        rutas_comunes = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
    elif sistema == 'Linux':
        rutas_comunes = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
    elif sistema == 'Darwin':  # macOS
        rutas_comunes = ['/usr/local/bin/tesseract', '/opt/homebrew/bin/tesseract']
    
    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            logger.info(f"Tesseract encontrado en ubicación común: {ruta}")
            return ruta
    
    # No se encontró Tesseract
    print("⚠️  ADVERTENCIA: No se encontró Tesseract OCR.")
    print("   Para habilitar OCR, instala Tesseract:")
    if sistema == 'Windows':
        print("   - Descarga: https://github.com/UB-Mannheim/tesseract/wiki")
    elif sistema == 'Linux':
        print("   - Ejecuta: sudo apt-get install tesseract-ocr tesseract-ocr-spa")
    elif sistema == 'Darwin':
        print("   - Ejecuta: brew install tesseract tesseract-lang")
    print("   O configura la variable de entorno TESSERACT_PATH con la ruta al ejecutable.")
    
    return None

class PDFExtractor:
    def __init__(self):
        """
        Inicializa el extractor de PDF con soporte multi-key para Gemini API
        """
        from gemini_utils import obtener_api_key_disponible
        
        try:
            # Obtener primera API key disponible
            api_key, key_num = obtener_api_key_disponible()
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
            self.usa_multi_key = True
            logger.info(f"PDFExtractor inicializado con API Key #{key_num}")
        except Exception as e:
            self.model = None
            self.usa_multi_key = False
            logger.warning(f" ADVERTENCIA: La API de Gemini no está configurada: {e}")

    # ============================================================================
    # MÉTODOS AUXILIARES DE EXTRACCIÓN DE TEXTO
    # ============================================================================

    def _get_horizontal_text_from_page(self, page: fitz.Page) -> str:
        """Extrae texto horizontal reconstruyendo el layout con coordenadas (y, x)."""
        page_text = ""
        words = page.get_text("words")
        if not words:
            return ""
        
        # Ordenar palabras por coordenada Y (fila) y luego X (columna)
        words.sort(key=lambda w: (w[1], w[0])) 
        
        current_y = 0
        line_text = []
        
        for w in words:
            # Si cambia significativamente la coordenada Y, es una nueva línea
            if abs(w[1] - current_y) > 5:
                page_text += " ".join(line_text) + "\n"
                line_text = [w[4]]
                current_y = w[1]
            else:
                line_text.append(w[4])
        
        page_text += " ".join(line_text) + "\n"
        return page_text

    def _get_vertical_text_from_page(self, page: fitz.Page) -> str:
        """Extrae SÓLO el texto vertical usando 'dict' y 'span["dir"]'."""
        page_vertical_text = []
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    # Verificar si el texto está en orientación vertical
                    dir_x = round(span["dir"][0])
                    dir_y = round(span["dir"][1])
                    
                    if dir_x == 0 and abs(dir_y) == 1:
                        page_vertical_text.append(span["text"])
        
        return " ".join(page_vertical_text).replace("\n", " ")

    def _get_ocr_text_from_page(self, page: fitz.Page) -> str:
        """Ejecuta OCR en UNA página (Fallback para PDFs escaneados)."""
        try:
            # Configurar la ruta de Tesseract de forma multiplataforma
            tesseract_path = configurar_tesseract()
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            else:
                raise Exception("Tesseract OCR no está instalado o no se encuentra en el sistema")
            
            # Renderizar la página como imagen de alta resolución
            pix_ocr = page.get_pixmap(dpi=300)
            img_ocr = Image.frombytes("RGB", [pix_ocr.width, pix_ocr.height], pix_ocr.samples)
            
            # Ejecutar OCR
            return pytesseract.image_to_string(img_ocr, lang='spa')
        except Exception as e:
            print(f"  ❌ Error de OCR en página: {e}")
            return ""

    # ============================================================================
    # FUNCIÓN PRINCIPAL DE EXTRACCIÓN DE TEXTO (ORQUESTADOR)
    # ============================================================================

    def extract_text_from_pdf(self, pdf_path: str) -> tuple[str, str, str]:
        """
        Extrae texto digital (horizontal + vertical) y OCR (como fallback).
        
        Returns:
            tuple: (texto_completo_horizontal, texto_ultima_pagina_horizontal, texto_vertical_completo)
        """
        if not pdf_path or not os.path.exists(pdf_path):
            logger.warning(f"⚠️ Archivo no encontrado: {pdf_path}")
            return "", "", ""

        logger.info(f"Iniciando extracción de texto avanzada para: {pdf_path}")
        
        texto_horizontal_por_pagina = []
        texto_vertical_por_pagina = []
        
        try:
            doc = fitz.open(pdf_path)
            
            # Intentar extracción digital primero
            for page in doc:
                texto_horizontal_por_pagina.append(self._get_horizontal_text_from_page(page))
                texto_vertical_por_pagina.append(self._get_vertical_text_from_page(page))
            
            texto_completo_horizontal = "\n\n".join(texto_horizontal_por_pagina)
            texto_ultima_pagina_horizontal = texto_horizontal_por_pagina[-1] if texto_horizontal_por_pagina else ""
            texto_vertical_completo = " ".join(texto_vertical_por_pagina)
            
            # Verificar si se extrajo suficiente texto
            if len(texto_completo_horizontal.strip()) < 100 and not texto_vertical_completo.strip():
                raise Exception("PDF es probablemente una imagen escaneada.")
            
            logger.info(f"Texto extraído digitalmente. {len(texto_vertical_completo)}B de texto vertical encontrado.")
            
        except Exception as e:
            print(f"ℹ️  Fallback a OCR (Tesseract): {e}")
            
            # Resetear variables
            texto_completo_horizontal, texto_ultima_pagina_horizontal, texto_vertical_completo = "", "", ""
            
            try:
                # Reabrir documento si es necesario
                if 'doc' not in locals() or doc.is_closed:
                    doc = fitz.open(pdf_path)
                
                # Ejecutar OCR en todas las páginas
                ocr_texts = [self._get_ocr_text_from_page(page) for page in doc]
                
                texto_completo_horizontal = "\n\n".join(ocr_texts)
                texto_ultima_pagina_horizontal = ocr_texts[-1] if ocr_texts else ""
                
                if len(texto_completo_horizontal.strip()) < 50:
                    raise Exception("Fallo de OCR: No se pudo extraer texto suficiente")
                
                print("✅ Texto extraído con OCR (Tesseract).")
                
            except Exception as ocr_error:
                logger.error(f"Error crítico: {ocr_error}")
                if 'doc' in locals() and not doc.is_closed:
                    doc.close()
                return "", "", ""
        
        # Cerrar documento
        if 'doc' in locals() and not doc.is_closed:
            doc.close()
        
        return texto_completo_horizontal, texto_ultima_pagina_horizontal, texto_vertical_completo

    # ============================================================================
    # UTILIDADES PARA ANÁLISIS NUMÉRICO
    # ============================================================================

    def _parse_number(self, s):
        """Convierte cualquier formato numérico a float."""
        if s is None or s == '':
            return 0.0
        
        s = str(s).strip().replace('€', '').replace('$', '').strip()
        
        # Manejar formatos como "1.234,56" o "1,234.56"
        if ',' in s and '.' in s:
            pos_coma = s.rfind(',')
            pos_punto = s.rfind('.')
            if pos_coma > pos_punto:
                s = s.replace('.', '').replace(',', '.')
            else:
                s = s.replace(',', '')
        elif ',' in s:
            partes = s.split(',')
            if len(partes[-1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        
        # Eliminar caracteres no numéricos excepto punto y signo negativo
        s = re.sub(r'[^\d.\-]', '', s)
        
        try:
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    # ============================================================================
    # ESTRATEGIAS DE EXTRACCIÓN DE IVA
    # ============================================================================

    def _extract_iva_with_multiple_strategies(self, texto_analizar):
        """
        Extrae líneas de IVA usando múltiples estrategias:
        1. Análisis matemático (más confiable)
        2. IA de Gemini (fallback)
        """
        lineas_iva = []
        lineas_texto = texto_analizar.splitlines()
        
        print("\n" + "="*60)
        print("🔍 ANÁLISIS MULTI-ESTRATEGIA DE IVA")
        print("="*60)
        
        # ========================================================================
        # ESTRATEGIA 1: ANÁLISIS MATEMÁTICO (Posición Independiente)
        # ========================================================================
        print("\n🔬 Estrategia 1: Análisis Matemático (Posición Independiente)...")
        
        processed_lines = set()
        
        for rate in VAT_RATES:
            rate_str = str(rate)
            rate_str_int = str(int(rate)) if rate == int(rate) else None
            
            # Crear patrón regex para buscar el porcentaje
            if rate_str_int and rate_str_int != rate_str:
                pattern_rate = re.compile(rf'(\b{re.escape(rate_str)}\b\s*%)|(\b{re.escape(rate_str_int)}\b\s*%)')
            else:
                pattern_rate = re.compile(rf'\b{re.escape(rate_str)}\b\s*%')
            
            for i, line in enumerate(lineas_texto):
                if i in processed_lines:
                    continue
                
                match = pattern_rate.search(line)
                if match:
                    # Extraer la línea sin el porcentaje
                    line_sin_tasa = pattern_rate.sub('', line)
                    
                    # Buscar todos los números en la línea
                    numeros = re.findall(r'[\d\.,]+', line_sin_tasa)
                    candidates = [self._parse_number(n) for n in numeros if self._parse_number(n) > 0]
                    
                    if len(candidates) >= 2:
                        # Probar todas las combinaciones de 2 números
                        for n1, n2 in permutations(candidates, 2):
                            cuota_calculada = (n1 * rate) / 100
                            
                            # Si la cuota calculada coincide con el segundo número
                            if abs(cuota_calculada - n2) < 0.10:
                                lineas_iva.append({
                                    'base': round(n1, 2),
                                    'iva_porcentaje': round(rate, 2),
                                    'iva_importe': round(n2, 2),
                                    'fuente': f'Math: {line.strip()[:60]}...',
                                    'confianza': 'math_analysis'
                                })
                                print(f"  ✅ Encontrado (Math): Base={n1}, IVA={rate}%, Cuota={n2}")
                                processed_lines.add(i)
                                break
                        
                        if i in processed_lines:
                            break
        
        # ========================================================================
        # ESTRATEGIA 2: IA DE GEMINI (FALLBACK)
        # ========================================================================
        if not lineas_iva and self.model:
            print("\n🤖 Estrategia 2: Llamando a IA como respaldo final...")
            lineas_ia = self._extract_iva_with_ia(texto_analizar)
            if lineas_ia:
                lineas_iva.extend(lineas_ia)
                print(f"  ✅ IA encontró {len(lineas_ia)} línea(s) de IVA")
        
        # ========================================================================
        # AGRUPACIÓN Y LIMPIEZA DE RESULTADOS
        # ========================================================================
        if lineas_iva:
            lineas_iva = self._agrupar_lineas_iva(lineas_iva)
            print(f"\n✅ Total de líneas de IVA encontradas: {len(lineas_iva)}")
        else:
            print("\n⚠️  No se encontraron líneas de IVA con ninguna estrategia")
        
        return lineas_iva

    def _extract_iva_with_ia(self, texto):
        """Extrae líneas de IVA usando IA de Gemini."""
        if not self.model:
            return []
        
        prompt = f"""
Analiza este texto de factura y extrae TODAS las líneas de desglose de IVA.

TEXTO:
---
{texto[:4000]}
---

Devuelve un JSON con un array "lineas", donde cada elemento tiene:
- "base": base imponible (número)
- "iva_porcentaje": porcentaje de IVA (número)
- "iva_importe": importe del IVA (número)

Ejemplo:
{{
  "lineas": [
    {{"base": 100.50, "iva_porcentaje": 21, "iva_importe": 21.11}},
    {{"base": 50.00, "iva_porcentaje": 10, "iva_importe": 5.00}}
  ]
}}

JSON:
"""
        
        try:
            response = self.model.generate_content(prompt)
            json_limpio = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            resultado = json.loads(json_limpio)
            lineas = resultado.get('lineas', [])
            
            # Normalizar los datos
            for linea in lineas:
                linea['base'] = float(self._parse_number(linea.get('base', 0)))
                linea['iva_porcentaje'] = float(self._parse_number(linea.get('iva_porcentaje', 0)))
                linea['iva_importe'] = float(self._parse_number(linea.get('iva_importe', 0)))
                linea['fuente'] = 'Extraído por IA'
                linea['confianza'] = 'ia'
            
            return lineas
        except Exception as e:
            print(f"  ⚠️  Error en extracción de IVA con IA: {e}")
            return []

    def _agrupar_lineas_iva(self, lineas):
        """Agrupa líneas de IVA por tasa y confianza."""
        if not lineas:
            return []
        
        grupos = {}
        
        for linea in lineas:
            porc = round(linea['iva_porcentaje'], 2)
            porc_key = float(porc)
            
            if porc_key not in grupos:
                grupos[porc_key] = linea.copy()
            else:
                # Comparar confianza
                conf_existente = grupos[porc_key].get('confianza', 'baja')
                conf_nueva = linea.get('confianza', 'baja')
                
                if self._comparar_confianza(conf_nueva, conf_existente) > 0:
                    grupos[porc_key] = linea.copy()
                elif conf_nueva == conf_existente and conf_nueva == 'math_analysis':
                    # Si ambas tienen confianza matemática, sumar
                    grupos[porc_key]['base'] += linea['base']
                    grupos[porc_key]['iva_importe'] += linea['iva_importe']
        
        return sorted(grupos.values(), key=lambda x: x['iva_porcentaje'], reverse=True)

    def _comparar_confianza(self, conf1, conf2):
        """Compara la confianza de dos métodos de extracción."""
        niveles = {
            'math_analysis': 4,
            'regex_table': 3,
            'ia': 2,
            'baja': 1
        }
        return niveles.get(conf1, 0) - niveles.get(conf2, 0)

    # ============================================================================
    # MÉTODO PRINCIPAL DE EXTRACCIÓN CON IA
    # ============================================================================

    def extract_with_ai(self, texto_completo, texto_ultima_pagina, texto_vertical):
        """
        Método principal que orquesta toda la extracción de datos de la factura.
        """
        if not self.model:
            return {NotificationTypes.ERROR: "El modelo de IA no está configurado."}
        
        print("\n" + "🚀 " + "="*58)
        print("🚀 INICIANDO EXTRACCIÓN COMPLETA DE FACTURA")
        print("🚀 " + "="*58 + "\n")
        
        # ========================================================================
        # PASO 1.A: Extraer datos básicos con IA
        # ========================================================================
        print("📋 PASO 1.A: Extrayendo datos básicos (NIF, Proveedor, Fecha...)")
        
        prompt_basico = f"""
Eres un experto contable extrayendo datos de facturas españolas.

TEXTO HORIZONTAL:
---
{texto_completo[:8000]}
---

TEXTO VERTICAL (Comprobar NIF/CIF aquí si no está en el horizontal):
---
{texto_vertical[:2000]}
---

Devuelve SOLO un JSON con estos campos:
{{
  "nif": "El NIF/CIF del emisor (ej: A08615106, B12345678). Busca 'NIF', 'CIF' o 'C.I.F.:' primero en TEXTO HORIZONTAL, luego en VERTICAL.",
  "proveedor": "Nombre completo del proveedor/empresa emisora",
  "numero_factura": "Número de la factura. Busca 'Factura:', 'Nº', 'Fra Nº' (ej: 12345, '2025/001', '80/2025000626')",
  "fecha": "Fecha en formato DD/MM/YYYY",
  "concepto": "Concepto principal de la factura. Si no hay, genera uno combinando proveedor y número de factura",
  
  "tasa_metropolitana": "Importe de 'TASA METROPOLITANA' (número o 0 si no existe)",
  "canon_agua": "Importe de 'CANON DEL AGUA' o 'CANON DE SANEAMIENTO' (número o 0 si no existe)",
  "tasa_alcantarillado": "Importe de 'TASA DE ALCANTARILLADO' (número o 0 si no existe)",
  
  "base_total_leida": "Base Imponible Total de la factura (número)",
  "iva_total_leido": "Importe Total de IVA (21%, 10%, 4%) - NO incluir tasas de agua (número)",
  "total_factura_leido": "TOTAL final de la factura incluyendo todo (número)"
}}

IMPORTANTE: Devuelve SOLO el JSON, sin texto adicional.

JSON:
"""
        
        try:
            response = self.model.generate_content(prompt_basico)
            json_limpio = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
            datos_basicos = json.loads(json_limpio)
            print("✅ Datos básicos y totales extraídos correctamente\n")
        except Exception as e:
            logger.warning(f" Error extrayendo datos básicos: {e}\n")
            return {NotificationTypes.ERROR: f"Fallo al analizar la respuesta de la IA (Paso 1): {e}"}
        
        # ========================================================================
        # PASO 1.B: LIMPIEZA DE NIF/CIF
        # ========================================================================
        nif_extraido = datos_basicos.get('nif', '').strip().upper()
        nif_limpio = re.sub(r'[\s.-]+', '', nif_extraido)
        
        # Si empieza con "ES", quitarlo
        if nif_limpio.startswith('ES') and len(nif_limpio) == 11:
            posible_nif = nif_limpio[2:]
            if len(posible_nif) == 9 and posible_nif[0].isalpha():
                logger.info(f"NIF/CIF limpiado: '{nif_extraido}' -> '{posible_nif}'")
                datos_basicos['nif'] = posible_nif
            else:
                datos_basicos['nif'] = nif_limpio
        else:
            datos_basicos['nif'] = nif_limpio
        
        # ========================================================================
        # PASO 1.C: CÁLCULO DE IMPUESTOS DE AGUA
        # ========================================================================
        print("💧 PASO 1.C: Calculando impuestos específicos de agua...")
        
        tasa_metro = self._parse_number(datos_basicos.get('tasa_metropolitana', 0))
        canon_agua = self._parse_number(datos_basicos.get('canon_agua', 0))
        tasa_alcan = self._parse_number(datos_basicos.get('tasa_alcantarillado', 0))
        
        total_impuestos_agua = round(tasa_metro + canon_agua + tasa_alcan, 2)
        
        datos_basicos['otros_impuestos_agua'] = total_impuestos_agua
        print(f"  ✅ Total 'Otros Impuestos Agua' calculado: {total_impuestos_agua}€")
        
        # ========================================================================
        # PASO 2: Extraer IVA (Usa SOLO TEXTO DE ÚLTIMA PÁGINA)
        # ========================================================================
        print("\n📊 PASO 2: Extrayendo desglose de IVA (analizando SÓLO la última página)...")
        lineas_iva = self._extract_iva_with_multiple_strategies(texto_ultima_pagina)
        
        # ========================================================================
        # PASO 3: Construir resultado final y VERIFICACIÓN
        # ========================================================================
        print("\n🔧 PASO 3: Construyendo resultado final y verificando...")
        
        datos_basicos['desgloseIVA'] = lineas_iva
        
        # Calcular totales del desglose
        total_base = sum([l['base'] for l in lineas_iva])
        total_iva = sum([l['iva_importe'] for l in lineas_iva])
        
        # Total factura = Base + IVA + Impuestos de Agua
        total_factura = total_base + total_iva + total_impuestos_agua
        
        datos_basicos['_resumen'] = {
            'total_base_calculado': round(total_base, 2),
            'total_iva_calculado': round(total_iva, 2),
            'total_impuestos_agua_calculado': round(total_impuestos_agua, 2),
            'total_factura_calculado': round(total_factura, 2),
            'num_lineas_iva': len(lineas_iva)
        }
        
        # ========================================================================
        # VERIFICACIÓN MATEMÁTICA
        # ========================================================================
        try:
            total_leido = self._parse_number(datos_basicos.get('total_factura_leido'))
            if total_leido > 0:
                diferencia = abs(total_leido - total_factura)
                if diferencia > 0.10:
                    mensaje_advertencia = f"⚠️  ADVERTENCIA: Total leído ({total_leido}€) vs. Desglose calculado ({total_factura}€). Diferencia: {diferencia}€"
                    print(f"🔥 {mensaje_advertencia}")
                    datos_basicos['_advertencia'] = mensaje_advertencia
                else:
                    print("✅ Verificación matemática superada.")
            else:
                print("⚠️  No se encontró un total leído para verificar (Total Leído = 0).")
        except Exception as e:
            logger.warning(f" No se pudo realizar la verificación matemática: {e}")
        
        # ========================================================================
        # RESUMEN FINAL
        # ========================================================================
        print(f"\n✅ Resumen:")
        print(f"   - Base calculada: {total_base:.2f}€")
        print(f"   - IVA calculado: {total_iva:.2f}€")
        print(f"   - Otros Impuestos Agua: {total_impuestos_agua:.2f}€")
        print(f"   - Total calculado: {total_factura:.2f}€")
        print(f"   - Total leído (de IA): {datos_basicos.get('total_factura_leido')}")
        
        print("\n" + "="*60)
        print("✅ EXTRACCIÓN COMPLETADA CON ÉXITO")
        print("="*60 + "\n")
        
        return datos_basicos