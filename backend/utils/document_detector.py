import fitz
import re
import logging
import traceback

logger = logging.getLogger(__name__)

def predecir_categoria_documento(file_path):
    """
    Analiza la primera (o primeras) páginas de un PDF para determinar su tipo:
    - Alta / Baja (alta_baja)
    - Finiquito (finiquito)
    - Contrato (contrato)
    - Nomina (nomina)
    - Seguros (seguros)
    
    Devuelve un diccionario { "tipo_detectado": str, "empresa_detectada": str, "detalles": dict }
    El tipo_detectado está alineado con las categorías del frontend.
    """
    try:
        doc = fitz.open(file_path)
            
        if len(doc) == 0:
            return {"tipo_detectado": "desconocido", "empresa_detectada": None}
            
        # Extraer texto de la primera página como muestra representativa
        texto_pag1 = doc[0].get_text()
        
        # Guardar una versión del documento también
        texto_completo = ""
        for i in range(min(3, len(doc))):
            texto_completo += doc[i].get_text() + " "
            
        doc.close()
        
        texto_upper = texto_completo.upper()
        # Normalizar espacios
        texto_norm = re.sub(r'\s+', ' ', texto_upper)
        
        tipo = "desconocido"
        empresa = "Empresa no detectada"
        
        # 1. Detectar Finiquitos
        if "DOCUMENTO DE LIQUIDACIÓN Y FINIQUITO" in texto_norm or "RECIBO DE FINIQUITO" in texto_norm or "SALDO Y FINIQUITO" in texto_norm:
            tipo = "finiquito"
            # Intento de extraer nombre de empresa
            empresa_match = re.search(r'EMPRESA[:\s]+([A-Z0-9\s,\.-]+?)(?:\s+TRABAJADOR|\s+N[\.\s]*I[\.\s]*F|\s+C\.?C\.?C\.?|\s+DOMICILIO)', texto_norm)
            if empresa_match:
                empresa = empresa_match.group(1).strip()
                
        # 2. Detectar Altas y Bajas (TA / IDC)
        elif "INFORME DE DATOS PARA LA COTIZACIÓN" in texto_norm or "I.D.C." in texto_norm or "INFORME DE SITUACIÓN DE ALTA" in texto_norm or "RESOLUCIÓN DE LA BAJA" in texto_norm or "RECONOCIMIENTO DE BAJA" in texto_norm or "RESOLUCIÓN SOBRE RECONOCIMIENTO DE ALTA" in texto_norm:
            tipo = "alta_baja"
            # Intento de extraer empresa para dar contexto al usuario
            empresa_match = re.search(r'(?:RAZÓN|RAZ\ÓN SOCIAL|TRABAJADOR DE)[:\s]+([A-Z0-9\s,\.]+?)(?:\s+C\.C\.C\.|CIF:|CON CÓDIGO)', texto_norm)
            if empresa_match:
                empresa = empresa_match.group(1).strip()
                
        # 3. Detectar Contratos
        elif "CONTRATO DE TRABAJO" in texto_norm and ("EMPRESA" in texto_norm and "TRABAJADOR" in texto_norm):
            tipo = "contratos"
            # Búsqueda rapida
            try:
                empresa_match = re.search(r'D/DÑA\.*?([A-Z0-9\s,\.]+?)EN CONCEPTO DE', texto_norm)
                if empresa_match:
                     empresa = empresa_match.group(1).strip()
            except:
                pass
                
        # 4. Seguros Sociales
        elif "RELACIÓN NOMINAL DE TRABAJADORES" in texto_norm or "RNT" in texto_norm or "RECIBO DE LIQUIDACIÓN DE COTIZACIONES" in texto_norm or ("RLC" in texto_norm and "SEGURIDAD SOCIAL" in texto_norm):
            tipo = "seguros"
            
        # 5. Nominas
        elif "RECIBO INDIVIDUAL DE SALARIOS" in texto_norm or "RECIBO DE SALARIOS" in texto_norm or "HOJA DE SALARIO" in texto_norm:
            tipo = "nominas"
            
        # 6. Impuestos
        elif "MODELO 303" in texto_norm or "IMPUESTO SOBRE EL VALOR AÑADIDO" in texto_norm or "MODELO 130" in texto_norm or "MODELO 111" in texto_norm or "MODELO 115" in texto_norm or "MODELO 200" in texto_norm or "PAGO FRACCIONADO" in texto_norm or "AUTOLIQUIDACIÓN" in texto_norm:
            tipo = "impuestos"
            
        # 7. Modelo 180
        elif "MODELO 180" in texto_norm or ("RESUMEN ANUAL" in texto_norm and "RENDIMIENTOS PROCEDENTES DEL ARRENDAMIENTO DE INMUEBLES URBANOS" in texto_norm):
            tipo = "certificados_180"
            
        # 8. Modelo 190
        elif "MODELO 190" in texto_norm or ("RESUMEN ANUAL" in texto_norm and "RENDIMIENTOS DEL TRABAJO Y DE ACTIVIDADES ECONÓMICAS" in texto_norm):
            tipo = "certificados_190"
        
        return {
            "tipo_detectado": tipo,
            "empresa_detectada": empresa,
            "analizado": True
        }
        
    except Exception as e:
        logger.error(f"Error en document_detector: {e}")
        logger.error(traceback.format_exc())
        return {
            "tipo_detectado": "error",
            "empresa_detectada": None,
            "analizado": False,
            "error": str(e)
        }
