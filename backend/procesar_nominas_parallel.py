"""
Wrapper para Procesamiento Paralelo de Nóminas
===============================================

Función wrapper que habilita procesamiento paralelo en procesar_nominas.py
sin modificar el código existente.

Uso desde tasks_nominas.py:
    from procesar_nominas_parallel import procesar_nominas_with_parallel
    
    resultados = procesar_nominas_with_parallel(
        pdf_path=pdf_path,
        output_dir=output_dir,
        use_parallel=True,  # Activar procesamiento paralelo
        progress_callback=callback
    )
"""

import os
import logging
from procesar_nominas import procesar_nominas

logger = logging.getLogger(__name__)


def procesar_nominas_with_parallel(
    pdf_path,
    output_dir,
    periodo_override=None,
    progress_callback=None,
    use_parallel=True,
    num_workers=4
):
    """
    Wrapper que añade procesamiento paralelo a procesar_nominas.
    
    Args:
        pdf_path: Ruta al PDF de nóminas
        output_dir: Directorio de salida
        periodo_override: Periodo manual (YYYYMM)
        progress_callback: Callback de progreso
        use_parallel: Si True, usa procesamiento paralelo para PDFs >100 páginas
        num_workers: Número de workers paralelos (default: 4)
    
    Returns:
        Lista de resultados (igual que procesar_nominas original)
    """
    
    # Verificar si el PDF es lo suficientemente grande para paralelización
    if use_parallel:
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            
            # Solo usar paralelo si el PDF tiene >100 páginas
            if total_pages >= 100:
                logger.info(f"📊 PDF grande detectado ({total_pages} páginas), usando procesamiento PARALELO")
                
                # Usar procesamiento paralelo
                return _procesar_paralelo(
                    pdf_path=pdf_path,
                    output_dir=output_dir,
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
    return procesar_nominas(
        pdf_path=pdf_path,
        output_dir=output_dir,
        periodo_override=periodo_override,
        progress_callback=progress_callback
    )


def _procesar_paralelo(pdf_path, output_dir, periodo_override, progress_callback, num_workers, total_pages):
    """
    Procesamiento paralelo interno.
    Extrae páginas en paralelo y luego usa procesar_nominas para el resto.
    """
    import gc
    from collections import defaultdict
    from pdf_parallel_processor import process_pdf_parallel
    from procesar_nominas import extraer_info_empresa_nomina
    from pypdf import PdfWriter, PdfReader
    
    print(f"🚀 Iniciando procesamiento PARALELO con {num_workers} workers para {total_pages} páginas")
    logger.info(f"🚀 Iniciando procesamiento paralelo con {num_workers} workers")
    
    # Callback de progreso para procesamiento paralelo
    def parallel_progress(current, total):
        if progress_callback:
            # 0-90% para extracción paralela
            progress_callback(current, total, None, f"Extrayendo página {current}/{total} en paralelo")
    
    # Procesar PDF en paralelo
    try:
        all_pages_data = process_pdf_parallel(
            pdf_path=pdf_path,
            extraction_type='extract_nomina',
            num_workers=num_workers,
            progress_callback=parallel_progress
        )
        
        print(f"✅ Extracción paralela completada: {len(all_pages_data)} páginas procesadas")
        logger.info(f"✅ Extracción paralela completada: {len(all_pages_data)} páginas procesadas")
        
    except Exception as e:
        print(f"❌ Error en procesamiento paralelo: {e}")
        logger.error(f"❌ Error en procesamiento paralelo: {e}")
        # Fallback a secuencial
        logger.info("🔄 Fallback a procesamiento secuencial")
        return procesar_nominas(
            pdf_path=pdf_path,
            output_dir=output_dir,
            periodo_override=periodo_override,
            progress_callback=progress_callback
        )
    
    # Agrupar por empresa
    if progress_callback:
        progress_callback(total_pages, total_pages, None, "Agrupando por empresa...")
    
    empresas = defaultdict(list)
    for page_data in all_pages_data:
        nif = page_data.get('nif')
        if nif:
            empresas[nif].append(page_data)
    
    print(f"📊 Encontradas {len(empresas)} empresas distintas")
    logger.info(f"📊 Encontradas {len(empresas)} empresas distintas")
    
    # Generar PDFs por empresa
    if progress_callback:
        progress_callback(total_pages, total_pages, None, "Generando PDFs por empresa...")
    
    resultados = []
    pdf_reader = PdfReader(pdf_path)
    
    for idx, (nif, pages_data) in enumerate(empresas.items(), 1):
        try:
            # Obtener info de la primera página
            first_page = pages_data[0]
            razon_social = first_page.get('razon_social', 'EMPRESA_DESCONOCIDA')
            # ✅ FIX: Usar periodo corto (max 6 chars) para evitar DataError en BD
            periodo_final = periodo_override or first_page.get('periodo')
            periodo_safe = periodo_final or '000000'
            periodo_texto = first_page.get('periodo_texto', periodo_safe)
            
            # Crear PDF para esta empresa
            pdf_writer = PdfWriter()
            page_nums = sorted([p['page_num'] for p in pages_data])
            
            for page_num in page_nums:
                if page_num < len(pdf_reader.pages):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
            
            # Guardar PDF por empresa (con nombre profesional)
            filename = f"NOMINAS_{periodo_safe}_{nif}.pdf"
            temp_pdf_path = os.path.join(output_dir, filename)
            with open(temp_pdf_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            resultados.append({
                'nif': nif,
                'razon_social': razon_social,
                'periodo': periodo_final, # None o String(6)
                'periodo_texto': periodo_texto,
                'num_trabajadores': len(pages_data),
                'pdf_path': temp_pdf_path,
                'empresa_id': None  # Se asignará después en tasks_nominas.py
            })
            
            # Actualizar progreso
            if progress_callback and idx % 5 == 0:
                progress_callback(total_pages, total_pages, nif, f"Generando PDF {idx}/{len(empresas)}")
            
            # GC cada 10 empresas
            if idx % 10 == 0:
                gc.collect()
        
        except Exception as e:
            print(f"❌ Error procesando empresa {nif}: {e}")
            logger.error(f"❌ Error procesando empresa {nif}: {e}")
            continue
    
    print(f"✅ Generados {len(resultados)} PDFs de empresas")
    logger.info(f"✅ Generados {len(resultados)} PDFs de empresas")
    
    # Limpiar memoria
    del pdf_reader
    gc.collect()
    
    # Filtrar resultados None o inválidos
    resultados_validos = [r for r in resultados if r is not None and r.get('nif')]
    
    if len(resultados_validos) < len(resultados):
        logger.warning(f"⚠️ Filtrados {len(resultados) - len(resultados_validos)} resultados inválidos")
        print(f"⚠️ Filtrados {len(resultados) - len(resultados_validos)} resultados inválidos")
    
    return resultados_validos



# Función de conveniencia para mantener compatibilidad
def procesar_nominas_auto(pdf_path, output_dir, periodo_override=None, progress_callback=None):
    """
    Versión automática que decide si usar paralelo o secuencial.
    """
    return procesar_nominas_with_parallel(
        pdf_path=pdf_path,
        output_dir=output_dir,
        periodo_override=periodo_override,
        progress_callback=progress_callback,
        use_parallel=True  # Automático
    )
