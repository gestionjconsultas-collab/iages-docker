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

def procesar_certificados_180(pdf_path, output_dir, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Certificados Modelo 180.
    1. Para cada página, extrae la empresa (Pagador) y el arrendatario (Perceptor).
    2. Guarda al Arrendatario en la BD de Empleados (si no existe, lo usamos como entidad genérica de terceros).
    3. Separa el PDF individualmente y devuelve los resultados.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    resultados = []
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"[MOD-180] Procesando {pdf_path}: {len(doc)} páginas encontradas.")

        certificados = defaultdict(list)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            nif_empresa = None
            nombre_empresa = None
            nif_arrendatario = None
            nombre_arrendatario = None
            ejercicio = None

            textos = [b[4].strip() for b in blocks if b[4].strip()]
            texto_completo = page.get_text()
            
            # 1. Extraer Ejercicio (Año)
            ejercicio = None
            m_ej = re.search(r"Ejercicio\s*(20\d{2})", texto_completo, re.I)
            if m_ej:
                ejercicio = m_ej.group(1)
            else:
                m_ej = re.search(r"\b(20\d{2})\b", texto_completo[:1000])
                if m_ej: ejercicio = m_ej.group(1)

            # 2. Extraer pares (NIF, Nombre) de los bloques de la página
            pairs = []
            nif_regex = r"([A-Z][0-9]{8}|[0-9]{8}[A-Z])"
            
            for b in blocks:
                # Cada bloque puede tener varias líneas
                lines = [l.strip() for l in b[4].split("\n") if l.strip()]
                for i, line in enumerate(lines):
                    m = re.search(nif_regex, line)
                    if m:
                        nif = m.group(1)
                        # El nombre suele ser la siguiente línea en el mismo bloque
                        name = ""
                        if i + 1 < len(lines):
                            next_line = lines[i+1]
                            # Verificamos que no sea otro NIF y tenga longitud mínima
                            if not re.search(nif_regex, next_line) and len(next_line) > 3:
                                name = next_line
                        
                        # Si no hay nombre en la siguiente línea, buscamos la más larga del bloque que no sea NIF
                        if not name:
                            potential_names = [l for l in lines if l != line and not re.search(nif_regex, l) and len(l) > 5]
                            if potential_names:
                                # Filtramos ruidos comunes
                                filtered = [n for n in potential_names if not any(x in n.lower() for x in ["perceptor", "pagador", "retenedor", "datos"])]
                                if filtered:
                                    name = filtered[0]
                        
                        # Identificar tipo por palabras clave en el bloque
                        block_txt = b[4].lower()
                        type_id = "unknown"
                        if any(x in block_txt for x in ["pagadora", "retenedor", "empresa"]):
                            type_id = "pagador"
                        elif "perceptor" in block_txt:
                            type_id = "perceptor"
                        
                        pairs.append({'nif': nif, 'name': name, 'type': type_id, 'y': b[1]})

            # Ordenar por posición vertical
            pairs.sort(key=lambda x: x['y'])

            # Asignar Pagador y Perceptor
            pagador_data = next((p for p in pairs if p['type'] == 'pagador'), None)
            perceptor_data = next((p for p in pairs if p['type'] == 'perceptor'), None)

            # Mejorar asignación si falta uno pero tenemos dos pares
            if len(pairs) == 2:
                if pagador_data and not perceptor_data:
                    perceptor_data = next(p for p in pairs if p != pagador_data)
                elif perceptor_data and not pagador_data:
                    pagador_data = next(p for p in pairs if p != perceptor_data)
                elif not pagador_data and not perceptor_data:
                    # Si no hay etiquetas, el primero suele ser perceptor y el segundo pagador en este PDF
                    # pero vamos a ser cuidadosos. Históricamente en este archivo: P[0]=Perceptor, P[1]=Pagador
                    perceptor_data = pairs[0]
                    pagador_data = pairs[1]

            # Variables finales
            nif_empresa = pagador_data['nif'] if pagador_data else None
            nombre_empresa = pagador_data['name'] if pagador_data else None
            nif_arrendatario = perceptor_data['nif'] if perceptor_data else None
            nombre_arrendatario = perceptor_data['name'] if perceptor_data else None

            # Fallback de nombres
            nombre_empresa = nombre_empresa or "Empresa Desconocida"
            nombre_arrendatario = nombre_arrendatario or "Arrendatario Desconocido"

            if nif_empresa and nif_arrendatario:
                logger.info(f"[MOD-180] P.{page_num} -> Pagador: {nif_empresa} ({nombre_empresa}) | Perceptor: {nif_arrendatario} ({nombre_arrendatario})")
                key = (nif_empresa, nombre_empresa, nif_arrendatario, nombre_arrendatario, ejercicio)
                certificados[key].append(page_num)
            else:
                logger.warning(f"Página {page_num}: Faltan datos críticos (Pagador: {nif_empresa}, Perceptor: {nif_arrendatario})")

        doc.close()

        # Generar PDFs fragmentados y Guardar en BD
        pdf_reader = PdfReader(pdf_path)
        
        if not app_context:
            app = create_app('production')
            app_context = app.app_context()

        with app_context:
            for (nif_emp, nom_emp, nif_arr, nom_arr, ejercicio), page_nums in certificados.items():
                try:
                    # Asegurar nombres seguros para strings
                    nom_emp_safe = nom_emp or "SinNombreEmpresa"
                    nom_arr_safe = nom_arr or "SinNombreArren"

                    # 1. Buscar Empresa
                    empresa = None
                    if gestoria_id:
                        empresa = Empresa.query.filter_by(nif=nif_emp, gestoria_id=gestoria_id).first()
                    else:
                        empresa = Empresa.query.filter_by(nif=nif_emp).first()
                        
                    # 2. Búsqueda de empresa (solo para reporte, no guardamos perceptor en tabla de empleados)
                    empresa_id = empresa.id if empresa else None
                    emp_name_db = empresa.nombre if empresa else nom_emp_safe
                    
                    # 3. Generar PDF troceado
                    pdf_writer = PdfWriter()
                    for p_num in sorted(page_nums):
                        pdf_writer.add_page(pdf_reader.pages[p_num])
                    
                    clean_emp_name = "".join(c for c in emp_name_db[:20] if c.isalnum() or c == '_')
                    filename = f"CERT_180_{nif_arr}_{clean_emp_name}.pdf"
                    temp_pdf_path = os.path.join(output_dir, filename)
                    
                    with open(temp_pdf_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                        
                    resultados.append({
                        'nif_empresa': nif_emp,
                        'nombre_empresa': emp_name_db,
                        'empresa_id': empresa_id,
                        'nif_arrendatario': nif_arr,
                        'nombre_arrendatario': nom_arr_safe,
                        'ejercicio': ejercicio,
                        'pdf_path': temp_pdf_path,
                        'pages': len(page_nums)
                    })
                    
                except Exception as e:
                    logger.error(f"Error procesando arrendatario {nif_arr} de empresa {nif_emp}: {e}")
                    db.session.rollback()

    except Exception as e:
        logger.error(f"Error abriendo PDF 180 {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if len(sys.argv) > 1:
        pdf = sys.argv[1]
        res = procesar_certificados_180(pdf, "./temp_180", None, None)
        print(f"Total procesados: {len(res)}")
        for r in res:
            print(r)
