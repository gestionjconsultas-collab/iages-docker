import fitz
import os
import re
import logging
import traceback
from datetime import datetime
from models import Empresa, Documento, db
from extensions import db

logger = logging.getLogger(__name__)

def procesar_contratos(pdf_path, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Contrato de Trabajo.
    Identifica la empresa, el trabajador y fechas clave.
    """
    resultados = []
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"[CONTRATO] Procesando {pdf_path}: {len(doc)} páginas.")

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
        fecha_inicio = None
        tipo_contrato = "Contrato"

        # 1. NIF del trabajador (NIF/NIE)
        # En el formato SEPE suele estar debajo de NIF/NIE
        nif_t_match = re.search(r"NIF/NIE\s+([0-9]{8}[A-Z]|[XYZ][0-9]{7}[A-Z])", texto_completo, re.I)
        if nif_t_match:
            nif_trabajador = nif_t_match.group(1).upper()
        
        # 2. Nombre del trabajador
        # Suele estar debajo de D/Dª o DATOS DEL/LA TRABAJADOR/A
        nombre_t_match = re.search(r"(?:D/Dª|TRABAJADOR/A)[:\s\n]+([A-ZÁÉÍÓÚÑ ]+)(?:\n|NIF/NIE|Fecha)", texto_completo, re.I)
        if nombre_t_match:
            nombre_trabajador = nombre_t_match.group(1).strip()

        # 3. Datos de la empresa
        # CIF/NIF/NIE de la empresa
        cif_e_match = re.search(r"CIF/NIF/NIE\s+([ABCDEFGHKLMNPQS]\d{7}[0-9A-Z])", texto_completo, re.I)
        if cif_e_match:
            potencial_cif = cif_e_match.group(1).upper()
            if potencial_cif != nif_trabajador:
                cif_empresa = potencial_cif
        
        # Nombre o Razón Social de la Empresa
        nombre_e_match = re.search(r"(?:Nombre o Razón Social de la Empresa|RAZÓN SOCIAL)[:\s\n]+([A-ZÁÉÍÓÚÑ0-9\s,\.]+?)(?:\n|Domicilio|CIF|NIF)", texto_completo, re.I)
        if nombre_e_match:
            # Validar que no hayamos pescado una línea de texto de un párrafo (ej. "el país")
            candidato = nombre_e_match.group(1).strip()
            if len(candidato) < 50 and not candidato.lower().startswith('ha sido') and candidato.lower() != 'país':
                nombre_empresa = candidato

        # FALLBACK PARA CONTRATOS OFICIALES SEPE CON FORMULARIOS ACROFORM (Textos desordenados en PyMuPDF)
        if (not nombre_trabajador or 'ha sido informado' in nombre_trabajador.lower()) or not nombre_empresa:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(pdf_path)
                text_pypdf2 = reader.pages[0].extract_text()
                
                # En PyPDF2 los datos tabulares del contrato oficial salen muy limpios en las primeras líneas
                # Ejemplo:
                # B66259516
                # GHULAM MURTAZA
                # ZARYAB IRFAN
                # ESTUDIOS PRIMARIOS COMPLETOS
                
                # También:
                # Y8603910S
                # ADMINISTRADOR
                # RINKO INSTALACIONES INTERNACIONALES SL
                # TUSET 19
                
                # Intentar pescar el CIF si PyMuPDF falló, ya que suele venir muy limpio
                if not cif_empresa:
                    cif_matches = re.findall(r"\b([A-HJ-NP-SUVW]\d{7}[0-9A-J])\b", text_pypdf2, re.I)
                    for m in cif_matches:
                        pot = m.upper()
                        if pot != nif_trabajador:
                            cif_empresa = pot
                            break
                            
                # Intentar pescar el NIF del trabajador si PyMuPDF falló
                if not nif_trabajador:
                    nifs = re.findall(r"\b([XYZ]\d{7}[A-Z]|\d{8}[A-Z])\b", text_pypdf2, re.I)
                    valid_nifs = [n.upper() for n in nifs if n.upper() != (cif_empresa or "")]
                    if valid_nifs:
                        # En contratos SEPE, el último NIF suele ser el del trabajador (el primero es el del representante legal)
                        nif_trabajador = valid_nifs[-1]

                text_lines = [l.strip() for l in text_pypdf2.split('\n') if l.strip()]
                
                for i, line in enumerate(text_lines):
                    # Buscar la empresa cerca del CIF encontrado
                    if not nombre_empresa and cif_empresa and cif_empresa in line:
                        # Buscar tanto antes como después (en el recibo SEPE sale ANTES, en el contrato sale DESPUÉS del CIF)
                        for offset in range(-4, 5):
                            if 0 <= i + offset < len(text_lines):
                                candidate_empresa = text_lines[i + offset]
                                if len(candidate_empresa) > 4 and candidate_empresa.upper() == candidate_empresa and not candidate_empresa in ['SÍ', 'NO', 'ADMINISTRADOR', 'EMPRESA']:
                                    # Heurística: Si contiene SL o SA es muy probable que sea la empresa
                                    if "SL" in candidate_empresa or "S.L" in candidate_empresa or "SA" in candidate_empresa or "S.A" in candidate_empresa:
                                        nombre_empresa = candidate_empresa
                                        break
                                    # Si no hay SL/SA, nos quedamos con la primera línea toda en mayúsculas larga
                                    if not nombre_empresa:
                                        nombre_empresa = candidate_empresa
                    
                    # Buscar el trabajador cerca del NIF encontrado (solo si no tenemos nada útil aún)
                    if (not nombre_trabajador or len(nombre_trabajador) < 4 or 'sido informado' in nombre_trabajador.lower()) and nif_trabajador and nif_trabajador in line:
                        # BUSCAR EN RANGO AMPLIO: El nombre suele estar ANTES del NIF en el PDF lineal
                        for offset in range(-6, 6):
                            if 0 <= i + offset < len(text_lines):
                                candidate_trab = text_lines[i + offset]
                                if len(candidate_trab) > 3 and candidate_trab.upper() == candidate_trab and candidate_trab not in ['ADMINISTRADOR', 'TRABAJADOR/A'] and (not nombre_empresa or candidate_trab != nombre_empresa):
                                    # FILTRO DE DIRECCIONES: Los nombres de personas no suelen llevar números
                                    if not any(char.isdigit() for char in candidate_trab):
                                        # FILTRO DE EMPRESAS: No debe ser la empresa ni tener sufijos empresariales
                                        if not ("SL" in candidate_trab or "S.L" in candidate_trab or "SA" in candidate_trab or "S.A" in candidate_trab):
                                            # FILTRO DE CUIDADES/CALLES
                                            if not any(x in candidate_trab for x in [' BARCELONA', ' MADRID', ' CALLE ', ' AVDA ', ' CL ']):
                                                nombre_trabajador = candidate_trab
                                                break
                                    
                # Heurística final por sufijos empresariales si aún no hay nombre de empresa
                if not nombre_empresa:
                    for line in text_lines:
                        if len(line) < 60 and line.upper() == line and not "ADMINISTRADOR" in line:
                            if re.search(r"\b(S\.?L\.?|S\.?A\.?|S\.?C\.?P\.?|COOP)\b$", line, re.I):
                                nombre_empresa = line
                                break
                                    
                # Si aún no tenemos trabajador, probamos una búsqueda más heurística en PyPDF2
                if not nombre_trabajador or 'sido informado' in nombre_trabajador.lower():
                    for i, line in enumerate(text_lines):
                        if 'ESTUDIOS' in line.upper(): # "ESTUDIOS PRIMARIOS COMPLETOS"
                            if i > 0:
                                cand = text_lines[i-1].split(',')[0].strip() # ZARYAB IRFAN, tutor/a...
                                if not any(char.isdigit() for char in cand):
                                    nombre_trabajador = cand
                                break
            except ImportError:
                pass
            except Exception as e:
                # Check if current_app is available, otherwise use local logger
                try:
                    from flask import current_app
                    current_app.logger.warning(f"Error en fallback PyPDF2: {e}")
                except RuntimeError:
                    logger.warning(f"Fallback PyPDF2 falló: {e}")
                
        # Limpieza final de nombre_trabajador por si acaso pescó basura
        if nombre_trabajador and "sido informado" in nombre_trabajador.lower():
            nombre_trabajador = "Desconocido"
        
        # 4. Fecha de Inicio
        # Para evitar problemas con las fechas de firma frente a la de inicio, buscaremos todas las fechas en el bloque de inicio.
        try:
            from PyPDF2 import PdfReader
            pt = PdfReader(pdf_path).pages[0].extract_text()
            
            # Buscar el bloque de inicio y extraer todas las fechas de ese bloque
            idx_inicio = pt.lower().find("inicio")
            if idx_inicio == -1: idx_inicio = pt.lower().find("iniciándose")
            
            if idx_inicio != -1:
                chunk_inicio = pt[idx_inicio : idx_inicio + 250]
                fechas_bloque = re.findall(r"(\d{2}[-/]\d{2}[-/]\d{4})", chunk_inicio)
                if fechas_bloque:
                    # De las fechas en el bloque de inicio, solemos querer la más reciente/avanzada (evitando nacimiento)
                    validas = []
                    for f in fechas_bloque:
                        try:
                            y = int(f[-4:])
                            if y >= 2020: validas.append(f)
                        except: pass
                    
                    if validas:
                        # Ordenar cronológicamente y coger la última (la de inicio suele ser la más lejana en el tiempo)
                        validas_sort = sorted(validas, key=lambda x: (int(x[-4:]), int(x.replace('-','/')[3:5]), int(x.replace('-','/')[0:2])))
                        fecha_str = validas_sort[-1].replace('-', '/')
                        fecha_inicio = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except:
            pass

        # Si aún no tenemos la fecha de inicio, hacer la búsqueda en el texto principal de PyMuPDF con etiquetas explícitas
        if not fecha_inicio:
            # 4a. Etiqueta directa SEPE (en algunos layouts de PyMuPDF sale bien)
            fecha_match = re.search(r"Fecha de Inicio del Contrato[^\d]+(\d{2}[-/]\d{2}[-/]\d{4})", texto_completo, re.I)
            if not fecha_match:
                # 4b. Frase exacta en el contrato
                fecha_match = re.search(r"inici[áa]ndose la relaci[óo]n laboral en fecha\s+(\d{2}[-/]\d{2}[-/]\d{4})", texto_completo, re.I)

            if fecha_match:
                try:
                    fecha_str = fecha_match.group(1).replace('-', '/')
                    fecha_inicio = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                except:
                    pass

        # Si no se encuentra con la etiqueta de texto explícita, buscar la última fecha válida del documento (Fecha de Firma)
        if not fecha_inicio:
            fechas = re.findall(r"(\d{2}[-/]\d{2}[-/]\d{4})", texto_completo)
            if fechas:
                # Filtrar fechas lógicas para un contrato para evitar fechas de nacimiento (ej. año >= 2020)
                fechas_validas = []
                for f in fechas:
                    year = int(f[-4:])
                    if year >= 1990: # Solo excluir del todo fechas pre-1990
                        fechas_validas.append(f)
                
                # Para contratos, la fecha de inicio/firma suele estar al final del documento
                if fechas_validas:
                    # Priorizar las fechas del presente/futuro en vez de pasadas
                    fechas_recientes = [f for f in fechas_validas if int(f[-4:]) >= 2023]
                    fecha_str = fechas_recientes[-1] if fechas_recientes else fechas_validas[-1]
                    fecha_str = fecha_str.replace('-', '/')
                else:
                    fecha_str = fechas[-1].replace('-', '/')
                    
                try:
                    fecha_inicio = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                except:
                    pass

        # 5. Tipo de Contrato (Código)
        codigo_match = re.search(r"CÓDIGO\s+(\d{3})", texto_completo, re.I)
        if codigo_match:
            tipo_contrato = f"Contrato Código {codigo_match.group(1)}"

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
                empresa = Empresa.query.filter_by(nif=cif_empresa, gestoria_id=gestoria_id).first()
            
            if not empresa and nombre_empresa and gestoria_id:
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
                'empresa_id': empresa.id if empresa else None,
                'fecha_inicio': fecha_inicio.strftime("%d/%m/%Y") if fecha_inicio else None,
                'pdf_path': pdf_path,
                'tipo_documento': tipo_contrato,
                'categoria_final': 'Contratos'
            })

    except Exception as e:
        logger.error(f"Error procesando Contrato {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados
