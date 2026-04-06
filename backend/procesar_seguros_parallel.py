"""
Wrapper para Procesamiento Paralelo de Seguros Sociales
========================================================

Función wrapper que habilita procesamiento paralelo en procesar_seguros_sociales.py
sin modificar el código existente.

Uso desde tasks_seguros_sociales.py:
    from procesar_seguros_parallel import procesar_seguros_auto
    
    resultados = procesar_seguros_auto(
        pdf_path=pdf_path,
        output_dir=output_dir,
        tipo_documento=tipo_documento
    )
"""

import os
import logging
from procesar_seguros_sociales import procesar_seguros_sociales

logger = logging.getLogger(__name__)


def procesar_seguros_auto(pdf_path, output_dir, tipo_documento='RLC', periodo_override=None, progress_callback=None):
    """
    Versión automática que decide si usar paralelo o secuencial para seguros sociales.
    
    Args:
        pdf_path: Ruta al PDF de seguros sociales
        output_dir: Directorio de salida
        tipo_documento: 'RLC' o 'RNT'
        periodo_override: Periodo manual (YYYYMM)
        progress_callback: Callback de progreso
    
    Returns:
        Lista de resultados (igual que procesar_seguros_sociales original)
    """
    
    # Por ahora, usar siempre el procesamiento secuencial para seguros sociales
    # El procesamiento paralelo se puede activar más adelante si es necesario
    # Los PDFs de seguros sociales suelen ser más pequeños que nóminas
    
    logger.info(f"📄 Procesando {tipo_documento} con método secuencial (optimizado)")
    
    return procesar_seguros_sociales(
        pdf_path=pdf_path,
        output_dir=output_dir,
        tipo_documento=tipo_documento,
        periodo_override=periodo_override,
        progress_callback=progress_callback
    )


def procesar_seguros_with_parallel(
    pdf_path,
    output_dir,
    tipo_documento='RLC',
    periodo_override=None,
    progress_callback=None,
    use_parallel=False,  # Desactivado por defecto para seguros
    num_workers=4
):
    """
    Wrapper con opción de procesamiento paralelo para seguros sociales.
    
    NOTA: El procesamiento paralelo está desactivado por defecto para seguros
    porque los PDFs suelen ser más pequeños y el overhead no vale la pena.
    
    Args:
        pdf_path: Ruta al PDF
        output_dir: Directorio de salida
        tipo_documento: 'RLC' o 'RNT'
        periodo_override: Periodo manual
        progress_callback: Callback de progreso
        use_parallel: Si True, intenta usar procesamiento paralelo
        num_workers: Número de workers (si use_parallel=True)
    
    Returns:
        Lista de resultados
    """
    
    # Verificar si el PDF es lo suficientemente grande para paralelización
    if use_parallel:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            
            # Solo usar paralelo si el PDF tiene >200 páginas (más restrictivo que nóminas)
            if total_pages >= 200:
                logger.info(f"📊 PDF grande detectado ({total_pages} páginas), usando procesamiento PARALELO")
                
                # Usar procesamiento paralelo
                return _procesar_seguros_paralelo(
                    pdf_path=pdf_path,
                    output_dir=output_dir,
                    tipo_documento=tipo_documento,
                    periodo_override=periodo_override,
                    progress_callback=progress_callback,
                    num_workers=num_workers,
                    total_pages=total_pages
                )
            else:
                logger.info(f"📄 PDF pequeño ({total_pages} páginas), usando procesamiento SECUENCIAL")
        
        except Exception as e:
            logger.warning(f"⚠️ Error verificando tamaño del PDF, usando procesamiento secuencial: {e}")
    
    # Fallback: usar función original (secuencial)
    return procesar_seguros_sociales(
        pdf_path=pdf_path,
        output_dir=output_dir,
        tipo_documento=tipo_documento,
        periodo_override=periodo_override,
        progress_callback=progress_callback
    )


def _procesar_seguros_paralelo(pdf_path, output_dir, tipo_documento, periodo_override, progress_callback, num_workers, total_pages):
    """
    Procesamiento paralelo interno para seguros sociales.
    Similar a nóminas pero adaptado para RLC/RNT.
    """
    import gc
    from collections import defaultdict
    from pdf_parallel_processor import process_pdf_parallel
    from pypdf import PdfWriter, PdfReader
    
    logger.info(f"🚀 Iniciando procesamiento paralelo de {tipo_documento} con {num_workers} workers")
    
    # Determinar tipo de extracción
    extraction_type = 'extract_seguros_rlc' if tipo_documento == 'RLC' else 'extract_seguros_rnt'
    
    # Callback de progreso para procesamiento paralelo
    def parallel_progress(current, total):
        if progress_callback:
            # 0-80% para extracción paralela
            percent = int((current / total) * 80)
            progress_callback(current, total, None, f"Extrayendo página {current}/{total}")
    
    # Procesar PDF en paralelo
    try:
        all_pages_data = process_pdf_parallel(
            pdf_path=pdf_path,
            extraction_type=extraction_type,
            num_workers=num_workers,
            progress_callback=parallel_progress
        )
        
        logger.info(f"✅ Extracción paralela completada: {len(all_pages_data)} páginas procesadas")
        
    except Exception as e:
        logger.error(f"❌ Error en procesamiento paralelo: {e}")
        # Fallback a secuencial
        logger.info("🔄 Fallback a procesamiento secuencial")
        return procesar_seguros_sociales(
            pdf_path=pdf_path,
            output_dir=output_dir,
            tipo_documento=tipo_documento,
            periodo_override=periodo_override,
            progress_callback=progress_callback
        )
    
    # Agrupar por empresa (similar a nóminas)
    if progress_callback:
        progress_callback(total_pages, total_pages, None, "Agrupando por empresa...")
    
    empresas = defaultdict(list)
    for page_data in all_pages_data:
        nif = page_data.get('nif')
        if nif:
            empresas[nif].append(page_data)
    
    logger.info(f"📊 Encontradas {len(empresas)} empresas distintas")
    
    # Generar PDFs por empresa
    if progress_callback:
        progress_callback(total_pages, total_pages, None, "Generando PDFs por empresa...")
    
    resultados = []
    pdf_reader = PdfReader(pdf_path)
    
    for idx, (nif, pages_data) in enumerate(empresas.items(), 1):
        try:
            first_page = pages_data[0]
            razon_social = first_page.get('razon_social', 'EMPRESA_DESCONOCIDA')
            periodo = periodo_override or first_page.get('periodo', 'SIN_PERIODO')
            
            # Crear PDF para esta empresa
            pdf_writer = PdfWriter()
            page_nums = sorted([p['page_num'] for p in pages_data])
            
            for page_num in page_nums:
                if page_num < len(pdf_reader.pages):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Guardar PDF temporal
            temp_pdf_path = os.path.join(output_dir, f"temp_{tipo_documento}_{nif}_{periodo}.pdf")
            with open(temp_pdf_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            resultados.append({
                'nif': nif,
                'razon_social': razon_social,
                'periodo': periodo,
                'num_trabajadores': len(pages_data),
                'pdf_path': temp_pdf_path,
                'empresa_id': None,
                'tipo_documento': tipo_documento
            })
            
            # GC cada 10 empresas
            if idx % 10 == 0:
                gc.collect()
        
        except Exception as e:
            logger.error(f"❌ Error procesando empresa {nif}: {e}")
            continue
    
    logger.info(f"✅ Generados {len(resultados)} PDFs de empresas")
    
    # Limpiar memoria
    del pdf_reader
    gc.collect()
    
    return resultados
