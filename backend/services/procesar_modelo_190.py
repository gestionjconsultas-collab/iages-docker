import fitz
import os
import re
import logging
import traceback
from collections import defaultdict
from pypdf import PdfWriter, PdfReader
from sqlalchemy.orm import Session
from models import Empresa, Documento, Empleado, db
from app import create_app
from extensions import db

logger = logging.getLogger(__name__)

def procesar_certificados_190(pdf_path, output_dir, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Certificados Modelo 190.
    1. Para cada página, extrae la empresa (Pagador) y el empleado (Perceptor).
    2. Guarda al Empleado en la BD (si no existe).
    3. Separa el PDF página por página (o empleado por empleado) y 
       lo asocia a la empresa correspondiente para guardarlo en la Base de Datos.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    resultados = []
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"[MOD-190] Procesando {pdf_path}: {len(doc)} páginas encontradas.")

        # Agrupar páginas por empleado (por si un certificado ocupa más de 1 página, aunque suele ser 1)
        # Diccionario: {(nif_empresa, nombre_empresa, nif_empleado, nombre_empleado): [page_nums]}
        certificados = defaultdict(list)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")

            # Ordenar los bloques verticalmente para un procesamiento estructurado
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            nif_empresa = None
            nombre_empresa = None
            nif_empleado = None
            nombre_empleado = None
            ejercicio = None

            # Extraer textos limpios
            textos = [b[4].strip() for b in blocks if b[4].strip()]

            for i, texto in enumerate(textos):
                # Buscar Perceptor
                if "Datos del perceptor" in texto or "Apellidos y nombre o denominación" in texto:
                    if not nif_empleado:
                        for next_txt in textos[i+1:i+6]:
                            parts = [p.strip() for p in next_txt.split('\n') if p.strip()]
                            if len(parts) >= 2 and re.match(r'^[A-Z0-9]{8,10}$', parts[0]) and not "N.I.F." in parts[0]:
                                nif_empleado = parts[0]
                                nombre_empleado = parts[1]
                                break

                # Buscar Pagador
                elif "Datos de la persona o entidad pagadora" in texto or "Razón social" in texto:
                    if not nif_empresa:
                        for next_txt in textos[i+1:i+6]:
                            parts = [p.strip() for p in next_txt.split('\n') if p.strip()]
                            if len(parts) >= 2 and re.match(r'^[A-Z0-9]{8,10}$', parts[0]) and not "N.I.F." in parts[0]:
                                nif_empresa = parts[0]
                                nombre_empresa = parts[1]
                                break

                # Buscar Ejercicio
                elif "Ejercicio" in texto or "EJERCICIO" in texto.upper():
                    if not ejercicio:
                        # Suele estar en el mismo bloque ("Ejercicio 2024") o en el siguiente
                        match = re.search(r'20\d{2}', texto)
                        if match:
                            ejercicio = match.group(0)
                        else:
                            # Mirar en los siguientes bloques de texto cortos
                            for next_txt in textos[i+1:i+4]:
                                match = re.search(r'^20\d{2}$', next_txt.strip())
                                if match:
                                    ejercicio = match.group(0)
                                    break

            # Fallback limpieza
            if nombre_empresa and "NIF" in nombre_empresa:
                nombre_empresa = nombre_empresa.split("NIF")[0].strip()
            if nombre_empleado and "NIF" in nombre_empleado:
                nombre_empleado = nombre_empleado.split("NIF")[0].strip()
            
            # Limpiar saltos de línea extraños
            if nombre_empresa: nombre_empresa = " ".join(nombre_empresa.split())
            if nombre_empleado: nombre_empleado = " ".join(nombre_empleado.split())

            if nif_empresa and nif_empleado:
                logger.info(f"Pagador: {nif_empresa} - {nombre_empresa} | Perceptor: {nif_empleado} - {nombre_empleado} | Ejercicio: {ejercicio} (Doc P.{page_num})")
                key = (nif_empresa, nombre_empresa, nif_empleado, nombre_empleado, ejercicio)
                certificados[key].append(page_num)
            else:
                logger.warning(f"Página {page_num}: No se pudo extraer NIF empresa o perceptor.")

        
        # Generar PDFs y guardar empleados
        pdf_reader = PdfReader(pdf_path)
        
        # Contexto de Flask si no viene
        if not app_context:
            try:
                from flask import current_app
                if current_app:
                    app_context = current_app.app_context()
            except RuntimeError:
                pass
                
        if not app_context:
            app = create_app('production')
            app_context = app.app_context()

        with app_context:
            for (nif_emp, nom_emp, nif_trab, nom_trab, ejercicio), page_nums in certificados.items():
                try:
                    # 1. Buscar Empresa
                    empresa = None
                    if gestoria_id:
                        empresa = Empresa.query.filter_by(nif=nif_emp, gestoria_id=gestoria_id).first()
                    else:
                        empresa = Empresa.query.filter_by(nif=nif_emp).first()
                        
                    empresa_id = empresa.id if empresa else None
                    empresa_nombre = empresa.nombre if empresa else nom_emp
                    
                    # 2. Guardar/Actualizar Empleado si tenemos info de Empresa
                    if empresa_id:
                        empleado = Empleado.query.filter_by(nif=nif_trab, empresa_id=empresa_id).first()
                        if not empleado:
                            empleado = Empleado(nif=nif_trab, nombre=nom_trab, empresa_id=empresa_id)
                            db.session.add(empleado)
                            db.session.commit()
                            logger.info(f"✅ Nuevo Empleado registrado: {nom_trab} ({nif_trab})")
                        elif empleado.nombre != nom_trab and nom_trab:
                            # Actualizar nombre si cambió
                            empleado.nombre = nom_trab
                            db.session.commit()
                    
                    # 3. Generar PDF troceado
                    pdf_writer = PdfWriter()
                    for p_num in sorted(page_nums):
                        pdf_writer.add_page(pdf_reader.pages[p_num])
                    
                    filename = f"CERT_190_{nif_trab}_{empresa_nombre[:20].replace(' ', '_')}.pdf"
                    filename = "".join(c for c in filename if c.isalnum() or c in ('_', '.', '-'))
                    temp_pdf_path = os.path.join(output_dir, filename)
                    
                    with open(temp_pdf_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                        
                    resultados.append({
                        'nif_empresa': nif_emp,
                        'nombre_empresa': empresa_nombre,
                        'empresa_id': empresa_id,
                        'nif_empleado': nif_trab,
                        'nombre_empleado': nom_trab,
                        'ejercicio': ejercicio,
                        'pdf_path': temp_pdf_path,
                        'pages': len(page_nums)
                    })
                    
                except Exception as e:
                    logger.error(f"Error procesando empleado {nif_trab} de empresa {nif_emp}: {e}")
                    db.session.rollback()

    except Exception as e:
        logger.error(f"Error abriendo PDF 190 {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if len(sys.argv) > 1:
        pdf = sys.argv[1]
        res = procesar_certificados_190(pdf, "./temp_190", None, None)
        print(f"Total procesados: {len(res)}")
        for r in res:
            print(r)
