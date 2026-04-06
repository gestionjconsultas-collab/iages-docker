# backend/services/procesar_impuestos.py
import os
import re
import logging
import traceback
from datetime import datetime
from services.impuesto_extractor import ImpuestoExtractor

logger = logging.getLogger(__name__)

def procesar_impuestos(pdf_path, output_dir, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Impuestos (Modelos AEAT).
    Utiliza ImpuestoExtractor para extraer NIF, Modelo, Ejercicio, etc.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    resultados = []
    
    try:
        extractor = ImpuestoExtractor()
        data = extractor.extract_tax_data(pdf_path)
        
        # Si el OCR no extrajo el ejercicio, intentar extraerlo del nombre del archivo
        # Ej: "111-12P-2025.pdf" -> "2025"
        ejercicio = data.get('ejercicio')
        if not ejercicio:
            year_match = re.search(r'(20\d{2})', os.path.basename(pdf_path))
            if year_match:
                ejercicio = year_match.group(1)
                logger.info(f"[IMPUESTO] Ejercicio extraído del nombre de archivo: {ejercicio}")
        
        logger.info(f"[IMPUESTO] Procesado {pdf_path}: Modelo {data.get('modelo')}, NIF {data.get('nif')}, Ejercicio {ejercicio}")

        # Estructura compatible con el flujo de guardado de app.py
        resultados.append({
            'nif_sujeto': data.get('nif'),
            'modelo': data.get('modelo'),
            'ejercicio': ejercicio,
            'razon_social': data.get('razon_social'),
            'fecha_presentacion': data.get('fecha_presentacion'),
            'numero_justificante': data.get('numero_justificante'),
            'csv': data.get('csv'),
            'resultado_texto': data.get('resultado_texto'),
            'is_aplazamiento': data.get('is_aplazamiento'),
            'pdf_path': pdf_path,
            'categoria_final': 'Impuestos'
        })

    except Exception as e:
        logger.error(f"Error procesando Impuesto {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados

