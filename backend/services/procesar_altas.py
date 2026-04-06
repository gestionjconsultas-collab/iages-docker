import fitz
import os
import re
import logging
import traceback
from datetime import datetime
from collections import defaultdict
from pypdf import PdfWriter, PdfReader
from sqlalchemy.orm import Session
from models import Empresa, Documento, Empleado, db
from extensions import db

logger = logging.getLogger(__name__)

def procesar_altas(pdf_path, output_dir, gestoria_id=None, app_context=None):
    """
    Procesa un PDF de Altas (TA, IDC).
    1. Extrae NIF, Nombre, CCC, Empresa y Fecha.
    2. Identifica la empresa por CCC o Nombre.
    3. Asocia al empleado.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    resultados = []
    
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"[ALTA] Procesando {pdf_path}: {len(doc)} páginas.")

        # Por ahora tratamos cada archivo como un solo documento (no división de páginas)
        # pero mantenemos la estructura compatible por si acaso.
        
        texto_completo = ""
        for page in doc:
            texto_completo += page.get_text()
        
        doc.close()
        
        # NORMALIZAR ESPACIOS (Evitar problemas con doble espacios en PDFs, pero preservando saltos de línea)
        texto_completo = re.sub(r'[^\S\r\n]+', ' ', texto_completo)

        # EXTRACCIÓN DE DATOS
        nif = None
        nss = None
        nombre_trabajador = None
        ccc = None
        nombre_empresa = None
        fecha_alta = None
        tipo_doc = "Alta"

        # 1. NIF/NIE
        # TA:  "NIE 0Y6092811X" → label NIE seguido del número
        # IDC: "NUM: 0Y6092811X" → label NUM: seguido del número
        # Formato NIE español con cero inicial: 0Y1234567X (10 chars) o Y1234567X (9 chars)
        # \d{7,9} allow 7..9 digits (handling leading zeros in DNI)
        nif_match = re.search(r"(?:N\.?I\.?[FE]\.?|DNI|NUM)[:\s.]+(\d{0,1}[A-Z]\d{7,8}[A-Z]|\d{8,9}[A-Z])", texto_completo, re.I)
        if nif_match:
            nif = re.sub(r'[\s\.\-]', '', nif_match.group(1)).upper()
        else:
            # Búsqueda genérica: NIE con posible cero inicial o NIF estándar
            nif_match = re.search(r"\b(\d{0,1}[A-Z]\d{7,8}[A-Z]|\d{8,9}[A-Z])\b", texto_completo)
            if nif_match:
                nif = nif_match.group(1).strip().upper()
        
        logger.info(f"[ALTA] NIF encontrado: {nif}")
        
        # Limpiar NIF
        if nif:
            nif = re.sub(r'[\s\.\-]', '', nif)

        # 2. NSS (Número de Seguridad Social)
        # TA/IDC: "NSS:\s*(\d{2}\s*\d{10})"
        nss_match = re.search(r"NSS[:\s]*(\d{2}[/\s]*\d{10}|\d{12})", texto_completo, re.I)
        if nss_match:
            nss = re.sub(r'[\s/]', '', nss_match.group(1))

        # 3. Nombre Trabajador
        # TA: "reconocer el alta ... de D./Dña. ([A-Z\s,]+)"
        # IDC: "NOMBRE Y APELLIDOS:\n([A-Z\s,]+)"
        
        # Versión ultra-normalizada para nombres (unir líneas rotas)
        texto_ultra_norm = re.sub(r'\s+', ' ', texto_completo)
        
        nombre_t_match = re.search(r"D\./Dñ?a\.?\s+([A-ZÁÉÍÓÚÑ ]+)(?:,|\s+con\s+fecha)", texto_ultra_norm, re.I)
        if nombre_t_match:
            nombre_trabajador = nombre_t_match.group(1).strip()
            # Ignorar si el nombre extraído es "SUSTITUTO"
            if nombre_trabajador.upper() == "SUSTITUTO":
                nombre_trabajador = None
        
        if not nombre_trabajador:
            # Intento específico para IDC donde el nombre está en la siguiente línea
            lines = texto_completo.split('\n')
            for i, line in enumerate(lines):
                if "NOMBRE Y APELLIDOS:" in line.upper() and i+1 < len(lines):
                    potential_name = lines[i+1].strip()
                    if potential_name and ":" not in potential_name and not potential_name.startswith("NSS:"):
                        nombre_trabajador = potential_name
                        break
            
            if not nombre_trabajador:
                # Fallback restringido para evitar pillar "TRABAJADOR DE [EMPRESA]"
                nombre_t_match = re.search(r"TRABAJADOR[:\s]+(?!DE\s)([A-ZÁÉÍÓÚÑ ]+)", texto_ultra_norm, re.I)
                if nombre_t_match:
                    nombre_trabajador = nombre_t_match.group(1).strip()

        # 4. CCC (Código Cuenta Cotización)
        # TA: "código de cuenta de cotización 0111 08 189529639" → 0111 es ruido, CCC = "08 189529639"
        # IDC: "C.C.C.: 08/189529639/XX"
        ccc = None
        ccc_match = re.search(
            r"(?:c[oó]digo de cuenta de cotizaci[oó]n|C\.C\.C\.)[:\s\d]*((?:\d{2}[\s/]?\d{8,10}[\s/]?\d{0,2}))",
            texto_completo, re.I
        )
        if ccc_match:
            ccc = re.sub(r"[\s/]", "", ccc_match.group(1))
            logger.info(f"[ALTA] CCC encontrado: {ccc}")
        
        # 5. Nombre Empresa
        # TA: "trabajador de [EMPRESA]"
        # IDC: "RAZÓN SOCIAL:\n[EMPRESA]"
        # TA Nuevo: "trabajador de RINKO INSTALACIONES INTERNACIONALES SL"
        # Búsqueda tras normalización de espacios (ahora presenvando saltos de línea para el split)
        nombre_e_match = re.search(r"(?:como trabajador de|RAZ\u00d3N SOCIAL)[:\s\n]+([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d10-9\s,\.]+?)(?: con c\u00f3digo|C\.C\.C\.|CIF:|HORA:|FECHA:)", texto_completo, re.I)
        if nombre_e_match:
            nombre_empresa = nombre_e_match.group(1).strip()
        else:
            # Búsqueda más agresiva si falla la anterior
            nombre_e_match2 = re.search(r"trabajador de\s+([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d10-9\s,\.]+?)(?:\s+perteneciente|\s+con\s+c\u00f3digo|\n|$)", texto_completo, re.I)
            if nombre_e_match2:
                nombre_empresa = nombre_e_match2.group(1).strip()
            else:
                if "RAZÓN SOCIAL:" in texto_completo.upper():
                    m = re.search(r"RAZ\u00d3N SOCIAL[:\s\n]+([A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d10-9\s,\.]+?)(?:\s+C\.C\.C\.|CIF:)", texto_completo, re.I)
                    if m:
                        nombre_empresa = m.group(1).strip()
        
        logger.info(f"[ALTA] Empresa extraída: '{nombre_empresa}'")

        # 6. Fecha Alta/Baja
        # IDC Baja: "FECHA EFECTO BAJA: 02-03-2026" / "BAJA: 02-03-2026" / "FIN CONTRATO DE TRABAJO: 02-03-2026"
        # IDC Alta: "DESDE 05-03-2026" / "con fecha 05-03-2026"
        # TA: "2 de marzo de 2026"
        meses = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }

        # Try DD-MM-YYYY patterns in priority order
        fecha_patterns_dd = [
            r"FECHA\s+EFECTO\s+BAJA[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
            r"(?<!\w)BAJA[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
            r"FIN\s+CONTRATO\s+DE\s+TRABAJO[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
            r"(?:con fecha|DESDE)[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
            r"CONTRATO\s+DE\s+TRABAJO[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
            r"(?:ALTA)[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})",
        ]
        for pat in fecha_patterns_dd:
            m = re.search(pat, texto_completo, re.I)
            if m:
                fecha_str = m.group(1).replace('-', '/').replace('.', '/')
                try:
                    fecha_alta = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                    break
                except:
                    pass

        if not fecha_alta:
            # TA format: "2 de marzo de 2026"
            ta_fecha_match = re.search(r"(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})", texto_completo, re.I)
            if ta_fecha_match:
                dia = ta_fecha_match.group(1).zfill(2)
                mes_nombre = ta_fecha_match.group(2).lower()
                anio = ta_fecha_match.group(3)
                if mes_nombre in meses:
                    mes = meses[mes_nombre]
                    try:
                        fecha_alta = datetime.strptime(f"{dia}/{mes}/{anio}", "%d/%m/%Y").date()
                    except:
                        pass

        # 7. Grupo de Cotización, Tipo Contrato y CCC (IDC)
        grupo_cotiz = None
        tipo_contrato = None
        
        # Grupo cotización: "GRUPO COTIZACIÓN: 01" o "GR. COTIZ.: 01"
        gc_match = re.search(r"(?:GRUPO\s+COTIZACI[OÓ]N|GR\.?\s*COTIZ\.?)[:\s]*(\d{1,2})", texto_completo, re.I)
        if gc_match: 
            grupo_cotiz = gc_match.group(1).zfill(2)
        
        # Tipo contrato: "TIPO CONTRATO: 100" o "COD. CONTRATO: 100"
        tc_match = re.search(r"(?:TIPO\s+CONTRATO|CÓD\.?\s*CONTRATO|TIPO\s+DE\s+CONTRATO)[:\s]*(\d{2,3})", texto_completo, re.I)
        if tc_match: 
            tipo_contrato = tc_match.group(1)

        # CCC: "CÓDIGO DE CUENTA DE COTIZACIÓN: 08/XXXXXXXXX/YY"
        if not ccc:
            ccc_match2 = re.search(r"(?:C\.?C\.?C\.?|CUENTA\s+COTIZACI[OÓ]N)[:\s]*(\d{2}[/\s]?\d{7,11}[/\s]?\d{0,2})", texto_completo, re.I)
            if ccc_match2:
                ccc = re.sub(r'[\s/]', '', ccc_match2.group(1))
        
        logger.info(f"[ALTA/BAJA] IDC extras: grupo={grupo_cotiz}, contrato={tipo_contrato}, ccc={ccc}")

        # DETERMINAR SI ES ALTA O BAJA (Búsqueda de palabras clave)
        is_baja = False
        
        # 1. Prioridad: Nombre del archivo
        # TGSS genera archivos como IDC_BAJA_xxx o IDC_ALTA_xxx (IDC primero)
        filename_upper = os.path.basename(pdf_path).upper()
        has_baja_nombre = 'BAJA' in filename_upper
        has_alta_nombre = 'ALTA' in filename_upper
        has_idc_nombre = 'IDC' in filename_upper or 'I.D.C.' in filename_upper
        has_ta_nombre = 'TA2S' in filename_upper or '_TA_' in filename_upper or '_TA.' in filename_upper or filename_upper.startswith('TA_') or filename_upper.startswith('TA.')

        if has_baja_nombre and (has_idc_nombre or has_ta_nombre):
            is_baja = True
            logger.info(f"[ALTA/BAJA] Forzando BAJA por nombre de archivo: {filename_upper}")
        elif has_alta_nombre and (has_idc_nombre or has_ta_nombre):
            is_baja = False
            logger.info(f"[ALTA/BAJA] Forzando ALTA por nombre de archivo: {filename_upper}")
        else:
            # 2. Análisis de contenido (Heurística mejorada)

            # Indicadores Fuertes de ALTA
            keywords_alta_fuertes = [
                r"resoluci[oó]n del alta",
                r"comunicaci[oó]n del alta",
                r"SITUACI[OÓ]N\s+DE\s+ALTA",
                r"RECONOCIMIENTO\s+DE\s+ALTA",
                r"FECHA\s+EFECTO\s+ALTA"
            ]

            # Indicadores Fuertes de BAJA (requieren fecha si son etiquetas de campo)
            keywords_baja_fuertes = [
                r"resoluci[oó]n de la baja",
                r"resoluci[oó]n sobre reconocimiento de baja",
                r"comunicaci[oó]n de la baja",
                r"SITUACI[OÓ]N\s+DE\s+BAJA",
                r"FECHA\s+EFECTO\s+BAJA[:\s]+\d",
                r"FIN\s+CONTRATO\s+DE\s+TRABAJO[:\s]+\d",
                r"INFORME\s+DE\s+SITUACI[OÓ]N\s+DE\s+BAJA"
            ]

            # Indicadores Débiles — evitar "BAJA" genérico que aparece en todo IDC
            keywords_alta_debiles = [r"IDC\s+TRABAJADOR\s+DE\s+ALTA", r"TRABAJADOR\s+DE\s+ALTA"]
            keywords_baja_debiles = [r"IDC\s+TRABAJADOR\s+DE\s+BAJA", r"TRABAJADOR\s+DE\s+BAJA"]

            # Check específico para IDC: etiqueta BAJA seguida de fecha
            baja_idc_match = re.search(r"BAJA[:\s]+(\d{2}[-/\.]\d{2}[-/\.]\d{4})", texto_completo, re.I)

            has_alta_fuerte = any(re.search(kw, texto_completo, re.I) for kw in keywords_alta_fuertes)
            has_baja_fuerte = any(re.search(kw, texto_completo, re.I) for kw in keywords_baja_fuertes) or (baja_idc_match is not None)

            if has_baja_fuerte:
                is_baja = True
            elif has_alta_fuerte:
                is_baja = False
            else:
                # Fallback a débiles — se chequean ambos para evitar falsos positivos
                has_baja_debil = any(re.search(kw, texto_completo, re.I) for kw in keywords_baja_debiles)
                has_alta_debil = any(re.search(kw, texto_completo, re.I) for kw in keywords_alta_debiles)

                if has_baja_debil and not has_alta_debil:
                    is_baja = True
                else:
                    is_baja = False  # Default: alta si no hay indicador claro de baja

        # DETERMINAR TIPO DE DOCUMENTO
        if "INFORME DE SITUACIÓN DE ALTA" in texto_completo.upper() or "INFORME DE SITUACIÓN DE BAJA" in texto_completo.upper() or "RESOLUCIÓN SOBRE RECONOCIMIENTO DE BAJA" in texto_completo.upper():
            tipo_doc = "Baja (TA)" if is_baja else "Alta (TA)"
        elif "INFORME DE DATOS PARA LA COTIZACIÓN" in texto_completo.upper() or "I.D.C." in texto_completo.upper():
            tipo_doc = "Baja (IDC)" if is_baja else "Alta (IDC)"
        
        # CATEGORÍA FINAL
        categoria_final = "Bajas de Trabajadores" if is_baja else "Altas de Trabajadores"

        # FALLBACKS
        nombre_trabajador = nombre_trabajador or "Trabajador Desconocido"
        nombre_empresa = nombre_empresa or "Empresa Desconocida"

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
            # Normalizar nombre para búsqueda (quitar comas, puntos, SL, SLU, SA)
            nombre_busqueda = nombre_empresa
            if nombre_busqueda:
                # Quitar comas y normalizar espacios
                nombre_busqueda = re.sub(r'[,\.]+', ' ', nombre_busqueda).strip()
                nombre_busqueda = re.sub(r'\s+', ' ', nombre_busqueda)
                # Quitar mercantiles comunes del final para mejorar fuzzy match
                nombre_busqueda_corto = re.sub(r'\s+(SL|SLU|SA|SCP|CB|SC)$', '', nombre_busqueda, flags=re.I).strip()
            
            # Prioridad 1: Exacta/parcial con nombre normalizado
            if nombre_busqueda and gestoria_id:
                empresa = Empresa.query.filter(
                    Empresa.nombre.ilike(f"%{nombre_busqueda_corto}%"),
                    Empresa.gestoria_id == gestoria_id
                ).first()
            
            # Prioridad 2: Por palabra clave principal (primera palabra larga)
            if not empresa and nombre_busqueda and gestoria_id:
                palabras = [p for p in nombre_busqueda.split() if len(p) > 3 and p.upper() not in ('INSTALACIONES','INTERNACIONALES','SERVICIOS','GESTIONES','SOLUCIONES')]
                if palabras:
                    empresa = Empresa.query.filter(
                        Empresa.nombre.ilike(f"%{palabras[0]}%"),
                        Empresa.gestoria_id == gestoria_id
                    ).first()

            # Prioridad 3: Por CCC (fallback cuando el nombre no se extrae del TA)
            if not empresa and ccc and gestoria_id:
                ccc_busqueda = re.sub(r'[\s/\-]', '', ccc)
                # Intentar match parcial del CCC (a veces los últimos 2 dígitos o los primeros varían)
                empresa = Empresa.query.filter(
                    Empresa.cuenta_cotizacion.ilike(f"%{ccc_busqueda}%"),
                    Empresa.gestoria_id == gestoria_id
                ).first()
                if not empresa and len(ccc_busqueda) > 9:
                    # Reintento con CCC truncado (sin los últimos 2 dígitos que a veces son de provincia/control)
                    ccc_corto = ccc_busqueda[:9]
                    empresa = Empresa.query.filter(
                        Empresa.cuenta_cotizacion.ilike(f"%{ccc_corto}%"),
                        Empresa.gestoria_id == gestoria_id
                    ).first()
                
                if empresa:
                    logger.info(f"[ALTA/BAJA] Empresa encontrada por CCC {ccc_busqueda}: {empresa.nombre}")
                else:
                    logger.warning(f"[ALTA/BAJA] No se encontró empresa con CCC: {ccc_busqueda} en gestoría {gestoria_id}")

            if empresa:
                logger.info(f"[ALTA/BAJA] Empresa encontrada: {empresa.nombre} (ID={empresa.id})")
            else:
                logger.warning(f"[ALTA/BAJA] Empresa no encontrada para: '{nombre_empresa}' (CCC: {ccc})")

            empresa_id = empresa.id if empresa else None
            emp_name_db = empresa.nombre if empresa else nombre_empresa

            # --- LÓGICA DE VALIDACIÓN / UPSERT ---
            if empresa_id and (nif or nombre_trabajador != "Trabajador Desconocido"):
                if nif:
                    empleado = Empleado.query.filter_by(nif=nif, empresa_id=empresa_id).first()
                else:
                    empleado = Empleado.query.filter_by(nombre=nombre_trabajador, empresa_id=empresa_id).first()
                
                if not empleado:
                    logger.info(f"[ALTA/BAJA] Creando nuevo empleado: {nombre_trabajador} ({nif})")
                    empleado = Empleado(
                        nif=nif or f"SINIF_{nombre_trabajador[:10].replace(' ','_')}",
                        nombre=nombre_trabajador, 
                        empresa_id=empresa_id,
                        nss=nss,
                        fecha_alta=fecha_alta if not is_baja else None,
                        grupo_cotizacion=grupo_cotiz,
                        tipo_contrato=tipo_contrato,
                        ccc=ccc
                    )
                    db.session.add(empleado)
                else:
                    logger.info(f"[ALTA/BAJA] Actualizando empleado existente: {nif}")
                    if nombre_trabajador != "Trabajador Desconocido":
                        empleado.nombre = nombre_trabajador
                    if nss: empleado.nss = nss
                    if not is_baja:
                        if fecha_alta: empleado.fecha_alta = fecha_alta
                    if grupo_cotiz: empleado.grupo_cotizacion = grupo_cotiz
                    if tipo_contrato: empleado.tipo_contrato = tipo_contrato
                    if ccc: empleado.ccc = ccc
                
                db.session.commit()

            resultados.append({
                'nif_trabajador': nif,
                'nombre_trabajador': nombre_trabajador,
                'nss': nss,
                'ccc': ccc,
                'nombre_empresa': emp_name_db,
                'empresa_id': empresa_id,
                'fecha_alta': fecha_alta.strftime("%d/%m/%Y") if fecha_alta else None,
                'fecha_movimiento': fecha_alta.strftime("%d/%m/%Y") if fecha_alta else None,
                'tipo_documento': tipo_doc,
                'categoria_final': categoria_final,
                'is_baja': is_baja,
                'grupo_cotizacion': grupo_cotiz,
                'tipo_contrato': tipo_contrato,
                'pdf_path': pdf_path,
                'ejercicio': str(fecha_alta.year) if fecha_alta else None
            })

    except Exception as e:
        logger.error(f"Error procesando Alta {pdf_path}: {e}")
        logger.error(traceback.format_exc())
        
    return resultados
