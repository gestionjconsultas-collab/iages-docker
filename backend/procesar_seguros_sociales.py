"""
Procesador Automático de Seguros Sociales
==========================================

Divide archivos consolidados de SS (RLC y RNT) por empresa y los almacena automáticamente.

Ejecutar desde backend:
    python procesar_seguros_sociales.py RLC_202511.pdf RNT_202511.pdf

O desde app.py como endpoint.
"""

import pdfplumber
import re
import os
import logging
from pypdf import PdfWriter, PdfReader
from datetime import datetime
from pathlib import Path
import sys
import shutil
from tenant_utils import get_current_gestoria_id

logger = logging.getLogger(__name__)

# ===== REGEX PRE-COMPILADOS (NIVEL MÓDULO) =====
RLC_RAZON_SOCIAL = re.compile(r'Raz[oó]n\s+Social:\s+(.+?)\s+N[uú]mero\s+de\s+liquidaci[oó]n:', re.IGNORECASE)
RLC_CCC_NIF = re.compile(r'C[oó]digo\s+de\s+Cuenta\s+de\s+Cotizaci[oó]n[:\s]+(\d+\s+\d+).*?C[oó]digo\s+de\s+Empresario[:\s]+\d+\s+([A-Z0-9]+)', re.DOTALL | re.IGNORECASE)
RNT_RAZON_SOCIAL_NIF = re.compile(r'Raz[oó]n\s+social\s+(.+?)\s+C[oó]digo\s+de\s+empresario\s+\d+\s+([A-Z0-9]+)', re.IGNORECASE)
RNT_CCC = re.compile(r'C[oó]digo\s+cuenta\s+cotizaci[oó]n\s+(\d+\s+\d+)', re.IGNORECASE)
# Patrón ultra-flexible para Periodo de Liquidación
PERIODO_LIQUIDACION = re.compile(r'Peri[oó]do\s+de\s+[Ll]iquidaci[oó]n[:\s]*(\d{1,2})/(\d{4})', re.IGNORECASE)
FECHA_CONTROL = re.compile(r'Fecha\s+de\s+control[:\s]*(\d{1,2})/(\d{4})', re.IGNORECASE)

# Patrones Importe RLC
IMPORTE_PATRONES = [
    re.compile(r'LIQUIDO\s+DE\s+TOTALES\s+([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})', re.IGNORECASE),
    re.compile(r'TOTAL\s+A\s+INGRESAR[:\s]+([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})', re.IGNORECASE),
    re.compile(r'IMPORTE\s+A\s+PAGAR[:\s]+([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})', re.IGNORECASE),
    re.compile(r'LÍQUIDO\s+A\s+INGRESAR[:\s]+([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})', re.IGNORECASE),
    re.compile(r'TOTALES.*?([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2})', re.IGNORECASE | re.DOTALL),
]

def extraer_texto_pdf_simple(pdf_path: str) -> str:
    """Extrae texto de las primeras páginas para análisis de importe"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            texto = ""
            # Normalmente el importe de RLC está en la primera o última página
            for page in pdf.pages[:2]: # Solo primeras 2 para rapidez
                texto += page.extract_text() or ""
            return texto
    except Exception:
        return ""

def extraer_texto_pagina_robusto(page_plumber, pdf_path, page_num):
    """
    Intenta extraer texto con pdfplumber. Si falla o devuelve vacío,
    intenta usar pypdf como fallback.
    """
    try:
        # 1. Intentar pdfplumber
        text = page_plumber.extract_text()
        if text and len(text.strip()) > 50:  # Si hay texto razonable
            return text

        # 2. Fallback PyPDF
        reader = PdfReader(pdf_path)
        if page_num < len(reader.pages):
            text_pypdf = reader.pages[page_num].extract_text()
            if text_pypdf and len(text_pypdf.strip()) > 0:
                return text_pypdf

        return text or ""
    except Exception as e:
        logger.error("Error en extracción robusta: %s", e)
        return ""


def extraer_importe_rlc(texto_pdf: str) -> float:
    """Extrae el importe a pagar usando regex pre-compilados"""
    for patron in IMPORTE_PATRONES:
        match = patron.search(texto_pdf)
        if match:
            importe_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                importe = float(importe_str)
                if 0 < importe < 100000:
                    return round(importe, 2)
            except ValueError: continue
    return None

# Expresiones regulares pre-compiladas (Consolidadas y Corregidas)
CCC_REGEX = re.compile(r'C[oó]digo\s+de\s+Cuenta\s+de\s+Cotizaci[oó]n[:\s]+(\d+\s+\d+)', re.IGNORECASE)
CCC_RNT_REGEX = re.compile(r'C[oó]digo\s+cuenta\s+cotizaci[oó]n\s+(\d+\s+\d+)', re.IGNORECASE)
NIF_REGEX_SS = re.compile(r'C[oó]digo\s+de\s+Empresario[:\s]+\d+\s+([A-Z0-9]+)', re.IGNORECASE)
RAZON_SOCIAL_RLC = RLC_RAZON_SOCIAL
RAZON_SOCIAL_RNT = RNT_RAZON_SOCIAL_NIF

# Patrón ULTRA-ROBUSTO para Periodo de Liquidación (Soporta DD/MM/YYYY y MM/YYYY)
PERIODO_LIQUIDACION = re.compile(r'Peri[oó]do\s+de\s+[Ll]iquidaci[oó]n[:\s-]+(?:(\d{1,2})[\s/-]+)?(\d{1,2})[\s/-]+(\d{4})', re.IGNORECASE)
FECHA_CONTROL = re.compile(r'Fecha\s+de\s+control[:\s-]+(?:(\d{1,2})[\s/-]+)?(\d{1,2})[\s/-]+(\d{4})', re.IGNORECASE)

# Patrones adicionales para RNT (más flexibles)
PERIODO_RNT_ALTERNATIVO = re.compile(r'(?:Periodo|Período|Mes)[:\s]+(\d{1,2})[/\s-]+(\d{4})', re.IGNORECASE)
PERIODO_TEXTO_NOMBRE = re.compile(r'(?:Periodo|Período|Mes)[:\s]+(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)[,\s]+(\d{4})', re.IGNORECASE)

MESES_SS = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}

# Diccionario inverso para convertir nombre de mes a número
MESES_INVERSO = {v.upper(): k for k, v in MESES_SS.items()}

def extraer_info_empresa_rlc(page_or_text):
    """
    Extrae información de empresa y periodo de una página RLC.
    Versión mejorada con extracción estructurada (patrón ocr_lnp)
    """
    # Extraer texto
    if hasattr(page_or_text, 'extract_text'):
        page = page_or_text
        bbox = (0, 0, page.width, page.height * 0.7)
        text_chunk = page.within_bbox(bbox).extract_text()

        # Fallback a página completa si no hay texto o no hay periodo
        if not text_chunk or "PERIODO" not in text_chunk.upper():
            text_chunk = page.extract_text() or ""
    else:
        text_chunk = page_or_text or ""

    # Patrones de búsqueda mejorados
    patterns = {
        "periodo": [
            r'Per[í][oó]do\s+de\s+[Ll]iquidaci[oó]n[:\s-]+(\d{1,2})[/-](\d{4})(?:\s*-\s*\d{1,2}[/-]\d{4})?',
            r'(?:Periodo|Período|Mes)[:\s]+(\d{1,2})[/\s-]+(\d{4})',
            r'(?:Periodo|Período|Mes)[:\s]+(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)[,\s]+(\d{4})',
            r'Fecha\s+de\s+control[:\s-]+(?:(\d{1,2})[/-])?(\d{1,2})[/-](\d{4})'
        ],
        "ccc": [
            r'C[oó]digo\s+de\s+Cuenta\s+de\s+Cotizaci[oó]n[:\s]+(\d+\s+\d+)',
            r'CCC[:\s]+(\d+\s+\d+)'
        ],
        "nif": [
            r'C[oó]digo\s+de\s+Empresario[:\s]+\d+\s+([A-Z0-9]+)',
            r'NIF[:\s/]+([A-Z0-9]+)'
        ],
        "razon_social": [
            r'Raz[oó]n\s+Social[:\s]+(.+?)(?:\s+N[uú]mero\s+de\s+liquidaci[oó]n|$)'
        ]
    }

    info = {
        'razon_social': None,
        'ccc': None,
        'nif': None,
        'periodo': None,
        'periodo_texto': None
    }

    # Extraer periodo con múltiples patrones
    for pattern in patterns["periodo"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            groups = match.groups()

            # Detectar si es nombre de mes o número
            if any(mes in match.group(0).upper() for mes in MESES_INVERSO.keys()):
                # Formato: "Mes: Octubre 2025"
                for mes_nombre, mes_num in MESES_INVERSO.items():
                    if mes_nombre in match.group(0).upper():
                        año = groups[-1]  # Último grupo es siempre el año
                        info['periodo'] = f"{año}{mes_num}"
                        info['periodo_texto'] = f"{mes_nombre.capitalize()} {año}"
                        break
            else:
                # Formato numérico: MM/YYYY o DD/MM/YYYY
                if len(groups) == 3 and groups[2]:  # Tiene 3 grupos
                    mes, año = groups[1], groups[2]
                elif len(groups) == 2:  # Solo MM/YYYY
                    mes, año = groups[0], groups[1]
                else:
                    continue

                if mes and año:
                    mes = f"{int(mes):02d}"
                    info['periodo'] = f"{año}{mes}"
                    info['periodo_texto'] = f"{MESES_SS.get(mes, mes)} {año}"

            if info['periodo']:
                break

    # Extraer CCC
    for pattern in patterns["ccc"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            info['ccc'] = match.group(1).replace(' ', '')
            break

    # Extraer NIF
    for pattern in patterns["nif"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            info['nif'] = match.group(1).strip()
            break

    # Extraer Razón Social
    for pattern in patterns["razon_social"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE | re.DOTALL)
        if match:
            razon_raw = match.group(1).strip()
            # Limpiar: tomar solo la primera línea
            razon_limpia = razon_raw.split('\n')[0].strip()
            # Eliminar texto después de "Número de liquidación"
            razon_limpia = re.sub(r'\s*N[uú]mero\s+de\s+liquidaci[oó]n.*', '', razon_limpia, flags=re.IGNORECASE)
            info['razon_social'] = razon_limpia
            break

    # --- PATRÓN DE RESCATE (Textos desordenados) ---
    # Ejemplo: "9 0B67040535 ABUZAR BUTT S.L. Recibo de Liquidación"
    if not info['nif'] or not info['razon_social']:
        # Busca secuencia: [NIF] [NOMBRE] "Recibo de Liquidación"
        # El NIF debe tener 8-11 caracteres y al menos 4 dígitos para evitar coincidencias con palabras enteras.
        rescue_pattern = r'(?:^|\s)(\d{1,2}\s+)?((?=(?:\D*\d){4})[A-Z0-9]{8,11})\s+([A-ZÑ0-9\.\-,\'&]{3,50}?)\s+(?:Recibo\s+de\s+Liquidaci[oó]n)'
        match_rescue = re.search(rescue_pattern, text_chunk, re.IGNORECASE)
        if match_rescue:
            if not info['nif']:
                info['nif'] = match_rescue.group(2).strip()
            if not info['razon_social']:
                info['razon_social'] = match_rescue.group(3).strip()

    return info

def extraer_info_empresa_rnt(page_or_text):
    """
    Extrae información de empresa y periodo de una página RNT.
    Versión mejorada con extracción estructurada (patrón ocr_lnp)
    """
    # Extraer texto
    if hasattr(page_or_text, 'extract_text'):
        page = page_or_text
        bbox = (0, 0, page.width, page.height * 0.7)
        text_chunk = page.within_bbox(bbox).extract_text()

        # Fallback a página completa
        if not text_chunk or "PERIODO" not in text_chunk.upper():
            text_chunk = page.extract_text() or ""
    else:
        text_chunk = page_or_text or ""

    # Patrones de búsqueda mejorados
    patterns = {
        "periodo": [
            r'Per[ií]?[oó]do\s+de\s+[Ll]iquidaci[oó]n[:\s-]+(\d{1,2})[/-](\d{4})',
            r'(?:Periodo|Período|Mes)[:\s]+(\d{1,2})[/\s-]+(\d{4})',
            r'(?:Periodo|Período|Mes)[:\s]+(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)[,\s]+(\d{4})',
            r'Fecha\s+de\s+control[:\s-]+(?:(\d{1,2})[/-])?(\d{1,2})[/-](\d{4})'
        ],
        "ccc": [
            r'C[oó]digo\s+cuenta\s+cotizaci[oó]n[:\s]+(\d+\s+\d+)',
            r'C[oó]digo\s+de\s+Cuenta\s+de\s+Cotizaci[oó]n[:\s]+(\d+\s+\d+)'
        ],
        "nif": [
            r'C[oó]digo\s+de\s+empresario[:\s]+\d+\s+([A-Z0-9]+)',
            r'NIF[:\s/]+([A-Z0-9]+)'
        ],
        "razon_social": [
            r'Raz[oó]n\s+social[:\s]+(.+?)(?:\s+C[oó]digo\s+de\s+empresario|\s+NIF|$)'
        ]
    }

    info = {
        'razon_social': None,
        'ccc': None,
        'nif': None,
        'periodo': None,
        'periodo_texto': None
    }

    # Extraer periodo con múltiples patrones
    for pattern in patterns["periodo"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            groups = match.groups()

            # Detectar si es nombre de mes o número
            if any(mes in match.group(0).upper() for mes in MESES_INVERSO.keys()):
                # Formato: "Mes: Octubre 2025"
                for mes_nombre, mes_num in MESES_INVERSO.items():
                    if mes_nombre in match.group(0).upper():
                        año = groups[-1]  # Último grupo es siempre el año
                        info['periodo'] = f"{año}{mes_num}"
                        info['periodo_texto'] = f"{mes_nombre.capitalize()} {año}"
                        break
            else:
                # Formato numérico: MM/YYYY o DD/MM/YYYY
                if len(groups) == 3 and groups[2]:  # Tiene 3 grupos
                    mes, año = groups[1], groups[2]
                elif len(groups) == 2:  # Solo MM/YYYY
                    mes, año = groups[0], groups[1]
                else:
                    continue

                if mes and año:
                    mes = f"{int(mes):02d}"
                    info['periodo'] = f"{año}{mes}"
                    info['periodo_texto'] = f"{MESES_SS.get(mes, mes)} {año}"

            if info['periodo']:
                break

    # Extraer CCC
    for pattern in patterns["ccc"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            info['ccc'] = match.group(1).replace(' ', '')
            break

    # Extraer NIF
    for pattern in patterns["nif"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE)
        if match:
            info['nif'] = match.group(1).strip()
            break

    # Extraer Razón Social
    for pattern in patterns["razon_social"]:
        match = re.search(pattern, text_chunk, re.IGNORECASE | re.DOTALL)
        if match:
            razon_raw = match.group(1).strip()
            # Limpiar: tomar solo la primera línea
            razon_limpia = razon_raw.split('\n')[0].strip()
            # Eliminar texto después de "Número de liquidación"
            razon_limpia = re.sub(r'\s*N[uú]mero\s+de\s+liquidaci[oó]n.*', '', razon_limpia, flags=re.IGNORECASE)
            info['razon_social'] = razon_limpia
            break

    return info

def procesar_rlc(pdf_path, output_dir, periodo_override=None, chunk_size=10, progress_callback=None):
    """Versión optimizada RLC"""
    import gc
    logger.info("Procesando RLC: %s", os.path.basename(pdf_path))

    # Intentar detectar periodo desde el nombre
    periodo = periodo_override
    if not periodo:
        match_fn = re.search(r'(\d{6})', os.path.basename(pdf_path))
        if match_fn: periodo = match_fn.group(1)

    resultados = []
    empresas_dict = {}

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        logger.info("Total páginas RLC: %d", total)

        # STREAMING: Procesar página por página sin cargar todo en memoria
        for p_num in range(total):
            # Cargar SOLO esta página
            page = pdf.pages[p_num]
            # Extraer texto con fallback robusto
            text_content = extraer_texto_pagina_robusto(page, pdf_path, p_num)
            info = extraer_info_empresa_rlc(text_content)

            if info['ccc']:
                if not periodo and info['periodo']:
                    periodo = info['periodo']
                    logger.debug("Periodo detectado: %s", periodo)

                ccc = info['ccc']
                if ccc not in empresas_dict:
                    empresas_dict[ccc] = {'info': info, 'pages': []}
                empresas_dict[ccc]['pages'].append(p_num)

            # Liberar memoria de esta página inmediatamente
            del page

            # ✅ OPTIMIZACIÓN: Garbage collection más agresivo cada 5 páginas (antes era 10)
            if (p_num + 1) % 5 == 0:
                gc.collect()
                logger.debug("Progreso RLC: %d/%d páginas", p_num + 1, total)
                if progress_callback:
                    progress_callback(p_num + 1, total, 'RLC')

        # ✅ REPORTE FINAL DE FASE
        if progress_callback:
            progress_callback(total, total, 'RLC', status="Análisis de RLC completado")

        logger.debug("Limpiando recursos del PDF RLC...")

    # El PDF se cierra automáticamente al salir del context manager
    gc.collect()  # Forzar GC después de cerrar el PDF

    # ✅ FIX: No usar fecha actual como fallback - mejor dejar None si no se detecta
    if not periodo: periodo = None

    reader = PdfReader(pdf_path)
    for ccc, data in empresas_dict.items():
        writer = PdfWriter()
        for p in data['pages']: writer.add_page(reader.pages[p])
        # ✅ FIX: Priorizar periodo_override sobre lo detectado por IA
        periodo_documento = periodo_override or data['info'].get('periodo') or periodo
        filename = f"RLC_{periodo_documento}_{ccc}.pdf"
        dest = os.path.join(output_dir, filename)
        with open(dest, 'wb') as f: writer.write(f)
        resultados.append({
            'razon_social': data['info']['razon_social'],
            'ccc': ccc,
            'nif': data['info']['nif'],
            'pdf_path': dest,
            'tipo': 'RLC',
            'periodo': periodo_documento
        })

    return resultados

def procesar_rnt(pdf_path, output_dir, periodo_override=None, chunk_size=10, progress_callback=None):
    """Versión optimizada RNT"""
    import gc
    logger.info("Procesando RNT: %s", os.path.basename(pdf_path))

    # Intentar detectar periodo desde el nombre
    periodo = periodo_override
    if not periodo:
        match_fn = re.search(r'(\d{6})', os.path.basename(pdf_path))
        if match_fn: periodo = match_fn.group(1)

    resultados = []
    empresas_dict = {}

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        logger.info("Total páginas RNT: %d", total)

        # STREAMING: Procesar página por página sin cargar todo en memoria
        for p_num in range(total):
            # Cargar SOLO esta página
            page = pdf.pages[p_num]
            # Extraer texto con fallback robusto
            text_content = extraer_texto_pagina_robusto(page, pdf_path, p_num)
            info = extraer_info_empresa_rnt(text_content)

            if info['ccc']:
                if not periodo and info['periodo']:
                    periodo = info['periodo']
                    logger.debug("Periodo detectado: %s", periodo)

                ccc = info['ccc']
                if ccc not in empresas_dict:
                    empresas_dict[ccc] = {'info': info, 'pages': []}
                empresas_dict[ccc]['pages'].append(p_num)

            # Liberar memoria de esta página inmediatamente
            del page

            # ✅ OPTIMIZACIÓN: Garbage collection más agresivo cada 5 páginas (antes era 10)
            if (p_num + 1) % 5 == 0:
                gc.collect()
                logger.debug("Progreso RNT: %d/%d páginas", p_num + 1, total)
                if progress_callback:
                    progress_callback(p_num + 1, total, 'RNT')

        # ✅ REPORTE FINAL DE FASE
        if progress_callback:
            progress_callback(total, total, 'RNT', status="Análisis de RNT completado")

        logger.debug("Limpiando recursos del PDF RNT...")

    # El PDF se cierra automáticamente al salir del context manager
    gc.collect()  # Forzar GC después de cerrar el PDF

    # ✅ FIX: No usar fecha actual como fallback - mejor dejar None si no se detecta
    if not periodo: periodo = None

    reader = PdfReader(pdf_path)
    for ccc, data in empresas_dict.items():
        writer = PdfWriter()
        for p in data['pages']: writer.add_page(reader.pages[p])
        # ✅ FIX: Priorizar periodo_override sobre lo detectado por IA
        periodo_documento = periodo_override or data['info'].get('periodo') or periodo
        filename = f"RNT_{periodo_documento}_{ccc}.pdf"
        dest = os.path.join(output_dir, filename)
        with open(dest, 'wb') as f: writer.write(f)
        resultados.append({
            'razon_social': data['info']['razon_social'],
            'ccc': ccc,
            'nif': data['info']['nif'],
            'pdf_path': dest,
            'tipo': 'RNT',
            'periodo': periodo_documento
        })

    return resultados


def get_or_create_inbox_empresa(db, Empresa, gestoria_id):
    """
    Busca o crea la empresa especial 'INBOX - NO CLASIFICADOS' para una gestoría.
    Patrón optimistic-concurrency: si dos tareas Celery coinciden, la segunda
    captura el IntegrityError y recupera el registro ya creado por la primera.
    """
    nif_inbox = f"INBOX_{gestoria_id}"
    nombre_inbox = f"INBOX - NO CLASIFICADOS ({gestoria_id})"

    inbox = Empresa.query.filter_by(gestoria_id=gestoria_id, nif=nif_inbox).first()

    if not inbox:
        logger.info("Creando empresa INBOX para gestoría %s", gestoria_id)
        try:
            inbox = Empresa(
                nombre=nombre_inbox,
                nif=nif_inbox,
                gestoria_id=gestoria_id,
                email='inbox@gestoria.com',
                codigo_empresa='INBOX'
            )
            db.session.add(inbox)
            db.session.commit()
        except Exception:
            db.session.rollback()
            inbox = Empresa.query.filter_by(gestoria_id=gestoria_id, nif=nif_inbox).first()
            logger.info("Reutilizando INBOX existente para gestoría %s", gestoria_id)

    return inbox


def asociar_con_empresas_bd(resultados, gestoria_id=None):
    """Pre-carga masiva con soporte multi-tenant"""
    from app import create_app
    from models import db, Empresa
    from difflib import SequenceMatcher
    from tenant_utils import get_current_gestoria_id

    app = create_app()
    with app.app_context():
        if gestoria_id is None:
            gestoria_id = get_current_gestoria_id()

        empresas_bd = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
        # Mejorar: almacenar NIF sin ceros a la izquierda y normalizado
        by_nif = {e.nif.lstrip('0').upper(): e for e in empresas_bd if e.nif}
        by_name = {e.nombre.upper(): e for e in empresas_bd}

        for r in resultados:
            # Limpiar NIF del documento (quitar ceros a la izquierda)
            nif_doc = (r['nif'] or "").lstrip('0').upper()
            emp = by_nif.get(nif_doc)

            if not emp:
                best_r = 0
                rs_up = (r['razon_social'] or "").upper()
                for n, e in by_name.items():
                    ratio = SequenceMatcher(None, rs_up, n).ratio()
                    if ratio > best_r: best_r = ratio; emp = e
                if best_r <= 0.8: emp = None

            if emp:
                r['empresa_id'] = emp.id
                r['empresa_nombre'] = emp.nombre  # nombre real de BD para mostrar en tabla
                r['gestoria_id'] = emp.gestoria_id
                r['es_inbox'] = False
            else:
                # 📥 FALLBACK: Marcar para Inbox físico (No registrar en DB por ahora)
                r['empresa_id'] = None
                r['gestoria_id'] = gestoria_id
                r['es_inbox'] = True
                logger.info("Sin asociar (inbox): CCC %s", r.get('ccc'))
    return resultados

def guardar_en_carpetas_empresas(resultados, base_storage_dir):
    """Movimiento optimizado"""
    from app import create_app
    from models import Empresa
    import unicodedata

    def sanitizar(nombre):
        nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        for char in '<>:"/\\|?*': nombre = nombre.replace(char, '')
        return ' '.join(nombre.split())

    app = create_app()
    with app.app_context():
        from utils.storage_utils import get_gestoria_inbox_path, get_empresa_storage_path
        from tenant_utils import get_current_gestoria_id

        emp_ids = [r['empresa_id'] for r in resultados if r.get('empresa_id')]
        names = {e.id: e.nombre for e in Empresa.query.filter(Empresa.id.in_(emp_ids)).all()}

        # Multi-tenant inbox
        gestoria_id = resultados[0].get('gestoria_id') if (resultados and resultados[0].get('gestoria_id')) else get_current_gestoria_id()
        no_clas_dir = get_gestoria_inbox_path(gestoria_id)

        for r in resultados:
            src = r['pdf_path']
            if not os.path.exists(src): continue
            fname = os.path.basename(src)
            if r.get('empresa_id') and r['empresa_id'] in names:
                nombre_empresa = names[r['empresa_id']]
                # Ruta estandarizada: storage/{gestoria}/{empresa}/Seguros Sociales/
                dest_dir = os.path.join(get_empresa_storage_path(gestoria_id, nombre_empresa), "Seguros Sociales")
            else:
                dest_dir = no_clas_dir
                logger.info("Moviendo %s → %s (No clasificado)", fname, dest_dir)

            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, fname)
            shutil.move(src, dest)
            r['pdf_path_final'] = dest

def registrar_en_bd(resultados):
    """Bulk Insert"""
    from app import create_app
    from models import db, Documento
    app = create_app()
    with app.app_context():
        names = [os.path.basename(r['pdf_path_final']) for r in resultados if r.get('pdf_path_final')]
        existing = {d.nombre_archivo for d in Documento.query.filter(Documento.nombre_archivo.in_(names)).all()} if names else set()

        bulk = []
        now = datetime.utcnow()
        for r in resultados:
            dest_path = r.get('pdf_path_final')
            if not dest_path: continue

            # ✅ EXCLUIR: No registrar en BD si es Inbox (el usuario lo clasificará manualmente)
            if r.get('es_inbox'):
                logger.debug("Saltando registro en BD para Inbox: %s", os.path.basename(dest_path))
                continue

            fname = os.path.basename(dest_path)
            empresa_id_r = r.get('empresa_id')
            # ✅ FIX: el check de duplicados incluye empresa_id para no saltar registros
            # que existen bajo otra empresa (ej: empresa única guardó con empresa_id distinto)
            if fname in existing and any(
                d.empresa_id == empresa_id_r
                for d in Documento.query.filter_by(nombre_archivo=fname, empresa_id=empresa_id_r).limit(1).all()
            ):
                logger.debug("Documento ya existe con misma empresa_id, saltando: %s (empresa_id=%s)", fname, empresa_id_r)
                continue

            # Importe RLC
            imp = None
            if 'RLC' in fname.upper():
                txt = extraer_texto_pdf_simple(dest_path)
                imp = extraer_importe_rlc(txt)

            # Periodo - Robustez Extra
            periodo_doc = r.get('periodo')
            if not periodo_doc or str(periodo_doc).lower() == 'none':
                # Fallback: Extraer del nombre del archivo (nombrado como RLC_202511_...)
                match_p = re.search(r'(\d{6})', fname)
                if match_p:
                    periodo_doc = match_p.group(1)
                    logger.debug("Recuperado periodo %s desde nombre de archivo para %s", periodo_doc, fname)

            logger.info("Registrando: %s → empresa_id=%s empresa_nombre=%s periodo=%s",
                        fname, r.get('empresa_id'), r.get('empresa_nombre', '?'), periodo_doc)
            bulk.append({
                'empresa_id': r.get('empresa_id'),
                'gestoria_id': r.get('gestoria_id'),
                'nombre_archivo': fname,
                'ruta_archivo': dest_path,
                'categoria': 'Seguros Sociales',
                'fecha_creacion': now,
                'guardado': True,
                'procesado': True,
                'importe_pagar': imp,
                'periodo': periodo_doc
            })

        if bulk:
            try:
                db.session.bulk_insert_mappings(Documento, bulk)
                db.session.commit()
                logger.info("%d documentos registrados.", len(bulk))
            except Exception as e:
                db.session.rollback()
                logger.error("Error en bulk insert de documentos: %s", e)
                raise

def procesar_seguros_sociales(rlc_path, rnt_path, gestoria_id=None, periodo_override=None, progress_callback=None):
    """Principal"""
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_seguros_sociales')
    os.makedirs(temp_dir, exist_ok=True)

    # Procesar RLC
    res_rlc = procesar_rlc(rlc_path, temp_dir, periodo_override, progress_callback=progress_callback)

    # Procesar RNT
    res_rnt = procesar_rnt(rnt_path, temp_dir, periodo_override, progress_callback=progress_callback)

    # Combinar y procesar
    todos = res_rlc + res_rnt

    if progress_callback:
        progress_callback(100, 100, 'ASOCIACION', status="Asociando con empresas en BD...")

    todos = asociar_con_empresas_bd(todos, gestoria_id=gestoria_id)

    if progress_callback:
        progress_callback(100, 100, 'GUARDADO', status="Moviendo archivos a carpetas...")

    guardar_en_carpetas_empresas(todos, os.path.join(os.path.dirname(__file__), 'storage'))

    if progress_callback:
        progress_callback(100, 100, 'REGISTRO', status="Registrando documentos finales...")

    registrar_en_bd(todos)

    if progress_callback:
        progress_callback(100, 100, 'FIN', status="¡Procesamiento completado!")


    # Limpieza: eliminar carpeta temporal con retry (Windows file locks)
    import gc
    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            gc.collect()  # Forzar liberación de recursos
            time.sleep(0.5)  # Esperar a que se liberen los archivos
            shutil.rmtree(temp_dir)
            logger.info("Carpeta temporal eliminada")
            break
        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.warning("Reintentando eliminar carpeta temporal... (%d/%d)", attempt + 1, max_retries)
                time.sleep(1)
            else:
                logger.warning("No se pudo eliminar carpeta temporal después de %d intentos: %s", max_retries, e)
        except Exception as e:
            logger.warning("Error eliminando carpeta temporal: %s", e)
            break

    logger.info("Completado: %d docs", len(todos))
    return todos

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(1)
    procesar_seguros_sociales(sys.argv[1], sys.argv[2])
