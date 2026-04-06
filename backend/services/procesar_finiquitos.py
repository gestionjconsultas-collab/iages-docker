import fitz
import os
import re
import logging
import traceback
from datetime import datetime
from models import Empresa, Documento, db
from extensions import db

logger = logging.getLogger(__name__)

def procesar_finiquitos(pdf_path, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Finiquito.
    Identifica la empresa y el trabajador.
    """
    resultados = []
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"[FINIQUITO] Procesando {pdf_path}: {len(doc)} páginas.")

        texto_completo = ""
        for page in doc:
            texto_completo += page.get_text()
        
        doc.close()
        
        # Normalizar espacios
        texto_completo = re.sub(r'[^\S\r\n]+', ' ', texto_completo)

        # EXTRACCIÓN DE DATOS
        nif_trabajador = None
        nombre_trabajador = None
        nombre_empresa = None
        cif_empresa = None
        fecha_finiquito = None
        importe_liquido = None

        # 1. NIF del trabajador
        nif_t_match = re.search(r"(?:TRABAJADOR|D\./Dñ?a\.?|N\.?I\.?[FE]\.?|DNI)[:\s.]+(\d{8}[A-Z]|[XYZ]\d{7}[A-Z])", texto_completo, re.I)
        if nif_t_match:
            nif_trabajador = nif_t_match.group(1).upper()
        
        # 2. Nombre del trabajador
        # Primero buscamos "Apellidos y Nombre" o "Nombre y Apellidos"
        nombre_t_match = re.search(r"(?:Apellidos y Nombres?|Nombre y Apellidos?|Trabajador)[:\s]+([A-ZÁÉÍÓÚÑ\s,]+)(?:\n|N\.?I\.?[FE]\.?|DNI)", texto_completo, re.I)
        if nombre_t_match:
            nombre_extraido = nombre_t_match.group(1).strip()
            # Invertir si viene con coma "APELLIDOS, NOMBRE"
            if "," in nombre_extraido:
                partes = [p.strip() for p in nombre_extraido.split(",")]
                if len(partes) == 2:
                    nombre_extraido = f"{partes[1]} {partes[0]}"
            nombre_trabajador = nombre_extraido
        else:
            # Fallback a "D./Dña."
            m = re.search(r"(?:D\./Dñ?a\.?)\s+([A-ZÁÉÍÓÚÑ\s]+)(?:,|\s+con\s+NIF|\n|con\s+DNI)", re.sub(r'\s+', ' ', texto_completo), re.I)
            if m:
                nombre_trabajador = m.group(1).strip()

        # 3. Datos de la empresa
        # RAZÓN SOCIAL o EMPRESA
        nombre_e_match = re.search(r"(?:RAZÓN SOCIAL|EMPRESA|EMPLEADOR)[:\s]+([A-ZÁÉÍÓÚÑ0-9\s,\.]+?)(?:\n|CIF|NIF|CCC|DIR|CALLE|DOMICILIO)", texto_completo, re.I)
        if nombre_e_match:
            nombre_empresa = nombre_e_match.group(1).strip()
        
        # CIF de la empresa
        cif_e_match = re.search(r"(?:CIF|NIF|N\.?I\.?F\.?|C\.?I\.?F\.?)[:\s]+([ABCDEFGHKLMNPQS]\d{7}[0-9A-Z])", texto_completo, re.I)
        if cif_e_match:
            # Si ya tenemos un NIF de trabajador, el segundo NIF/CIF suele ser de la empresa
            potential_cif = cif_e_match.group(1).upper()
            if potential_cif != nif_trabajador:
                cif_empresa = potential_cif
        
        # 4. Fecha
        # "en Ciudad, a DD de MES de YYYY" o simplemente "DD/MM/YYYY"
        fecha_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", texto_completo)
        if fecha_match:
            try:
                fecha_finiquito = datetime.strptime(fecha_match.group(0).replace('-', '/'), "%d/%m/%Y").date()
            except:
                pass
        
        # 5. Importe Líquido
        importe_match = re.search(r"(?:LIQUIDO|TOTAL|A PERCIBIR|SALDO)[:\s]+([\d\.,]+)", texto_completo, re.I)
        if importe_match:
            try:
                imp_str = importe_match.group(1).replace('.', '').replace(',', '.')
                importe_liquido = float(imp_str)
            except:
                pass

        if not app_context:
            try:
                from flask import current_app
                app_context = current_app.app_context()
            except RuntimeError:
                pass

        if not app_context:
            from app import create_app
            app = create_app('production')
            app_context = app.app_context()

        with app_context:
            empresa = None
            if cif_empresa and gestoria_id:
                # Prioridad por CIF
                empresa = Empresa.query.filter_by(nif=cif_empresa, gestoria_id=gestoria_id).first()
            
            if not empresa and nombre_empresa and gestoria_id:
                # Fallback por nombre
                nombre_busqueda = re.sub(r'[,\.]+', ' ', nombre_empresa).strip()
                nombre_busqueda = re.sub(r'\s+(SL|SLU|SA|SCP|CB|SC)$', '', nombre_busqueda, flags=re.I).strip()
                empresa = Empresa.query.filter(
                    Empresa.nombre.ilike(f"%{nombre_busqueda}%"),
                    Empresa.gestoria_id == gestoria_id
                ).first()

            resultados.append({
                'nombre_trabajador': nombre_trabajador or "Desconocido",
                'nif_trabajador': nif_trabajador,
                'nombre_empresa': empresa.nombre if empresa else (nombre_empresa or "Empresa Desconocida"),
                'cif_empresa': cif_empresa,
                'empresa_id': empresa.id if empresa else None,
                'fecha': fecha_finiquito.strftime("%d/%m/%Y") if fecha_finiquito else None,
                'importe': importe_liquido,
                'pdf_path': pdf_path,
                'tipo_documento': 'Finiquito',
                'categoria_final': 'Finiquitos'
            })

    except Exception as e:
        logger.error(f"Error procesando Finiquito {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados
