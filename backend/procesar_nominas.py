"""
Procesador Automático de Nóminas
=================================

Divide archivos consolidados de nóminas por empresa y los almacena automáticamente.
Basado en la metodología de procesar_seguros_sociales.py

Ejecutar desde backend:
    python procesar_nominas.py NOMINAS_202508.pdf

O desde app.py como endpoint.
"""

import pdfplumber
import re
import os
import logging
from pypdf import PdfWriter, PdfReader
from datetime import datetime, timezone
from pathlib import Path
import sys
import shutil
from tenant_utils import get_current_gestoria_id

logger = logging.getLogger(__name__)

# ===== REGEX PRE-COMPILADOS A NIVEL MÓDULO =====
# Optimizamos compilando los patrones una sola vez al cargar el módulo
NIF_REGEX = re.compile(r'NIF[\\.:\s]+([A-Z]?\d{7,8}[A-Z]?)')
RAZON_SOCIAL_REGEX = re.compile(r'^[A-Z][A-Z\s,\.]+(?:SL|S\.L\.|SA|S\.A\.|SLU|S\.L\.U\.)$')
PERIODO_REGEX = re.compile(r'MENS\s+(\d{2})\s+([A-Z]{3})\s+(\d{2})', re.IGNORECASE)
TRABAJADOR_REGEX = re.compile(r'^[A-ZÑÁÉÍÓÚ\s]+,\s+[A-ZÑÁÉÍÓÚ\s]+$', re.MULTILINE)

# Mapeo exhaustivo de meses abreviados
MESES_MAP = {
    'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04',
    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
}

MESES_TEXTO_MAP = {
    'ENE': 'Enero', 'FEB': 'Febrero', 'MAR': 'Marzo', 'ABR': 'Abril',
    'MAY': 'Mayo', 'JUN': 'Junio', 'JUL': 'Julio', 'AGO': 'Agosto',
    'SEP': 'Septiembre', 'OCT': 'Octubre', 'NOV': 'Noviembre', 'DIC': 'Diciembre'
}

def extraer_info_empresa_nomina(page_or_text):
    """
    Versión OPTIMIZADA: Extrae info usando solo el área superior de la página si es un objeto Page.
    Si recibe texto, lo procesa directamente (retrocompatibilidad).
    """
    if hasattr(page_or_text, 'extract_text'):
        # Es un objeto Page de pdfplumber
        page = page_or_text
        # Aumentamos al 50% para mayor seguridad en el encabezado
        bbox = (0, 0, page.width, page.height * 0.5)
        cropped_page = page.within_bbox(bbox)
        text_chunk = cropped_page.extract_text()

        # Si no hay texto en el area recortada, probar pagina completa
        if not text_chunk or "MENS" not in text_chunk.upper():
            text_chunk = page.extract_text() or ""
    else:
        # Es texto directo (str)
        text_chunk = page_or_text or ""

    lines = text_chunk.split('\n')

    info = {
        'razon_social': None,
        'nif': None,
        'periodo': None,
        'periodo_texto': None,
        'trabajador': None
    }

    # 1. Buscar NIF (prioritario)
    for line in lines:
        nif_match = NIF_REGEX.search(line)
        if nif_match:
            info['nif'] = nif_match.group(1)
            break

    # 2. Buscar periodo (formato: MENS 01 NOV 25)
    periodo_match = PERIODO_REGEX.search(text_chunk)
    if periodo_match:
        # Grupos: (día_ignorado, mes_abr, año_corto)
        _, mes_abr, año_corto = periodo_match.groups()
        mes_abr = mes_abr.upper()
        mes_num = MESES_MAP.get(mes_abr, '01')
        mes_texto = MESES_TEXTO_MAP.get(mes_abr, mes_abr)
        año_completo = f"20{año_corto}"
        info['periodo'] = f"{año_completo}{mes_num}"
        info['periodo_texto'] = f"{mes_texto} {año_completo}"

    # Buscar trabajador
    for line in lines:
        if TRABAJADOR_REGEX.match(line.strip()):
            info['trabajador'] = line.strip()
            break

    return info


def escribir_pdf_worker(args):
    """Worker para escribir PDFs en paralelo"""
    pdf_path, page_nums, output_path = args
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for p in page_nums:
            page = reader.pages[p]
            if '/MediaBox' in page: page.mediabox = page.mediabox
            if '/CropBox' in page: page.cropbox = page.cropbox
            writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)
        return True
    except Exception as e:
        logger.error("Error escribiendo PDF %s: %s", output_path, e)
        return False

def procesar_nominas(pdf_path, output_dir, periodo_override=None, progress_callback=None, chunk_size=50):
    """
    Versión OPTIMIZADA con Chunking, GC agresivo y Paralelización
    """
    import gc
    import psutil
    from concurrent.futures import ThreadPoolExecutor

    logger.info("PROCESANDO NÓMINAS (OPTIMIZADO): %s", os.path.basename(pdf_path))

    proceso = psutil.Process(os.getpid())
    memoria_inicial = proceso.memory_info().rss / 1024 / 1024

    # Determinar periodo inicial (desde nombre de archivo o override)
    periodo = periodo_override
    if not periodo:
        periodo_match = re.search(r'(\d{6})', os.path.basename(pdf_path))
        if periodo_match:
            periodo = periodo_match.group(1)
            logger.debug("Periodo detectado en nombre: %s", periodo)

    resultados = []
    empresas_dict = {}

    # Fase 1: Análisis (Chunking)
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info("Total de páginas: %d", total_pages)

        # STREAMING: Procesar página por página sin cargar todo en memoria
        for page_num in range(total_pages):
            # Cargar SOLO esta página
            page = pdf.pages[page_num]
            info_empresa = extraer_info_empresa_nomina(page)

            if info_empresa['nif']:
                # ✅ RESTAURADO: Si no tenemos periodo global, intentar usar el de la página
                if not periodo and info_empresa['periodo']:
                    periodo = info_empresa['periodo']
                    logger.debug("Periodo detectado en contenido: %s", periodo)

                nif = info_empresa['nif']
                if nif not in empresas_dict:
                    empresas_dict[nif] = {
                        'info': info_empresa,
                        'pages': [],
                        'trabajadores': []
                    }

                empresas_dict[nif]['pages'].append(page_num)
                if info_empresa['trabajador']:
                    empresas_dict[nif]['trabajadores'].append(info_empresa['trabajador'])

            # Liberar memoria de esta página inmediatamente
            del page

            # ✅ OPTIMIZACIÓN: Garbage collection más agresivo cada 5 páginas (antes era 10)
            if (page_num + 1) % 5 == 0:
                gc.collect()
                mem_actual = proceso.memory_info().rss / 1024 / 1024
                logger.debug(
                    "Progreso: %d/%d | Memoria: %.0fMB (Δ %.0fMB)",
                    page_num + 1, total_pages, mem_actual, mem_actual - memoria_inicial
                )
                if progress_callback:
                    progress_callback(page_num + 1, total_pages, nif if info_empresa['nif'] else None)

        # ✅ GARANTIZAR QUE SE REPORTE LA ÚLTIMA PÁGINA
        if progress_callback:
            progress_callback(total_pages, total_pages, None, "Análisis de páginas completado")

        logger.debug("Limpiando recursos del PDF...")

    # El PDF se cierra automáticamente al salir del context manager
    gc.collect()  # Forzar GC después de cerrar el PDF

    # ✅ FIX: No usar fecha actual como fallback - mejor dejar None si no se detecta
    # Fallback final si no se detectó nada
    if not periodo:
        periodo = None
        logger.warning("Periodo no detectado, se usará el de cada página individual")

    # Fase 2: Escritura en Paralelo
    logger.info("Generando PDFs individuales en paralelo para %d empresas...", len(empresas_dict))

    tareas_pdf = []
    for nif, data in empresas_dict.items():
        # ✅ FIX: Priorizar periodo_override sobre lo detectado por IA
        # Usar '000000' para el filename (6 chars) y None para BD si no se detecta
        periodo_extraido = periodo_override or data['info'].get('periodo') or periodo
        periodo_filename = periodo_extraido or '000000'

        filename = f"NOMINAS_{periodo_filename}_{nif}.pdf"
        output_path = os.path.join(output_dir, filename)
        tareas_pdf.append((pdf_path, data['pages'], output_path))

        resultados.append({
            'razon_social': data['info']['razon_social'] or 'EMPRESA DESCONOCIDA',
            'nif': nif,
            'pdf_path': output_path,
            'tipo': 'NOMINA',
            'periodo': periodo_extraido, # Será String(6) o None
            'num_trabajadores': len(data['pages']),
            'trabajadores': data['trabajadores']
        })

    # Ejecutar en paralelo (Usando hilos para compatibilidad con Celery)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(escribir_pdf_worker, tareas_pdf))

    logger.info("Proceso completado. Memoria final: %.0fMB", proceso.memory_info().rss / 1024 / 1024)
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
            # Otra tarea concurrente ya la creó — rollback y reutilizar la existente
            db.session.rollback()
            inbox = Empresa.query.filter_by(gestoria_id=gestoria_id, nif=nif_inbox).first()
            logger.info("Reutilizando INBOX existente para gestoría %s", gestoria_id)

    return inbox


def asociar_con_empresas_bd(resultados, gestoria_id=None):
    """
    Versión OPTIMIZADA: Pre-carga masiva para evitar N+1 queries
    """
    from app import create_app
    from models import db, Empresa
    from difflib import SequenceMatcher

    # ✅ FILTRO DEFENSIVO: Eliminar None y resultados inválidos
    if resultados is None:
        logger.warning("resultados es None, retornando lista vacía")
        return []

    resultados_validos = [r for r in resultados if r is not None and isinstance(r, dict) and r.get('nif')]

    if len(resultados_validos) < len(resultados):
        logger.warning(
            "Filtrados %d resultados None o inválidos en asociar_con_empresas_bd",
            len(resultados) - len(resultados_validos)
        )

    if not resultados_validos:
        logger.warning("No hay resultados válidos para asociar")
        return []

    resultados = resultados_validos  # Usar solo resultados válidos

    app = create_app()
    with app.app_context():
        if gestoria_id is None:
            gestoria_id = get_current_gestoria_id()

        # ✅ Una sola query para cargar TODAS las empresas de esta gestoría
        empresas_bd = Empresa.query.filter_by(gestoria_id=gestoria_id).all()

        # Índices en RAM para búsqueda O(1)
        empresas_por_nif = {e.nif.lstrip('0').upper(): e for e in empresas_bd if e.nif}
        empresas_por_nombre = {e.nombre.upper(): e for e in empresas_bd}

        for resultado in resultados:
            empresa_encontrada = None
            metodo = None

            # Limpiar NIF del documento (quitar ceros a la izquierda)
            nif_key = (resultado['nif'] or "").lstrip('0').upper()
            empresa_encontrada = empresas_por_nif.get(nif_key)
            if empresa_encontrada:
                metodo = 'NIF exacto'
            else:
                # Fuzzy match por nombre
                mejor_match = None
                mejor_ratio = 0
                razon_upper = (resultado['razon_social'] or "").upper()

                for nombre_bd, empresa in empresas_por_nombre.items():
                    ratio = SequenceMatcher(None, razon_upper, nombre_bd).ratio()
                    if ratio > mejor_ratio:
                        mejor_ratio = ratio
                        mejor_match = empresa

                if mejor_ratio > 0.8:
                    empresa_encontrada = mejor_match
                    metodo = f'Nombre similar ({mejor_ratio*100:.1f}%)'

            if empresa_encontrada:
                resultado['empresa_id'] = empresa_encontrada.id
                resultado['empresa_bd_nombre'] = empresa_encontrada.nombre
                resultado['gestoria_id'] = empresa_encontrada.gestoria_id
                resultado['metodo_asociacion'] = metodo
                resultado['es_inbox'] = False
                razon = resultado.get('razon_social') or 'SIN RAZÓN SOCIAL'
                logger.info("Asociada: %s → %s (%s)", razon[:35], empresa_encontrada.nombre[:30], metodo)
            else:
                # 📥 FALLBACK: Marcar para Inbox físico (No registrar en DB por ahora)
                resultado['empresa_id'] = None
                resultado['empresa_bd_nombre'] = None
                resultado['gestoria_id'] = gestoria_id
                resultado['metodo_asociacion'] = 'No encontrada (Inbox)'
                resultado['es_inbox'] = True
                razon = resultado.get('razon_social') or 'SIN RAZÓN SOCIAL'
                logger.info("Sin asociar (inbox): %s", razon[:35])

        asociadas = sum(1 for r in resultados if not r.get('es_inbox'))
        logger.info(
            "Asociación BD: %d/%d empresas vinculadas. %d a Inbox.",
            asociadas, len(resultados), len(resultados) - asociadas
        )

    return resultados


def guardar_en_carpetas_empresas(resultados, base_storage_dir):
    """
    Movimiento por lotes
    """
    from app import create_app
    from models import Empresa
    from utils import limpiar_nombre_carpeta

    app = create_app()
    with app.app_context():
        from utils.storage_utils import get_gestoria_inbox_path, get_empresa_storage_path

        # Pre-cargar nombres de carpetas para evitar queries
        empresa_ids = [r['empresa_id'] for r in resultados if r.get('empresa_id')]
        empresas_lookup = {e.id: e.nombre for e in Empresa.query.filter(Empresa.id.in_(empresa_ids)).all()}

        # Multi-tenant inbox
        gestoria_id = resultados[0].get('gestoria_id') or get_current_gestoria_id()
        no_clasificados_dir = get_gestoria_inbox_path(gestoria_id)

        for resultado in resultados:
            pdf_path = resultado['pdf_path']
            if not os.path.exists(pdf_path):
                logger.warning("Archivo ya movido o no encontrado: %s", os.path.basename(pdf_path))
                continue

            filename = os.path.basename(pdf_path)

            if resultado.get('empresa_id') and resultado['empresa_id'] in empresas_lookup:
                nombre_empresa = empresas_lookup[resultado['empresa_id']]
                # Ruta estandarizada: storage/{gestoria}/{empresa}/Nominas/
                dest_dir = os.path.join(get_empresa_storage_path(gestoria_id, nombre_empresa), "Nominas")
                logger.info("Moviendo %s → %s", filename, dest_dir)
            else:
                dest_dir = no_clasificados_dir
                logger.info("Moviendo %s → %s (No clasificado)", filename, dest_dir)

            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)

            # Windows fix: Retry con delay para archivos bloqueados
            import time
            import gc
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    gc.collect()  # Forzar cierre de file handles
                    time.sleep(0.1)  # Pequeño delay
                    shutil.move(pdf_path, dest_path)
                    break  # Éxito
                except PermissionError as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "Intento %d/%d falló para %s, reintentando...",
                            attempt + 1, max_retries, filename
                        )
                        time.sleep(0.5)  # Esperar más tiempo
                    else:
                        logger.error(
                            "Error moviendo %s después de %d intentos: %s",
                            filename, max_retries, e
                        )
                        # Copiar en lugar de mover como último recurso
                        try:
                            shutil.copy2(pdf_path, dest_path)
                            logger.info("Archivo copiado exitosamente: %s", filename)
                        except Exception as copy_error:
                            logger.error("Error copiando %s: %s", filename, copy_error)
                            raise

            resultado['pdf_path_final'] = dest_path


def registrar_en_bd(resultados):
    """
    Versión OPTIMIZADA: Bulk insert masivo
    """
    from app import create_app
    from models import db, Documento

    app = create_app()
    with app.app_context():
        # 1. Identificar duplicados en un solo batch
        nombres_archivos_a_insertar = [os.path.basename(r['pdf_path_final']) for r in resultados if r.get('pdf_path_final')]

        # Solo consultar si hay nombres para evitar una query vacía
        if nombres_archivos_a_insertar:
            existentes = {d.nombre_archivo for d in Documento.query.filter(Documento.nombre_archivo.in_(nombres_archivos_a_insertar)).all()}
        else:
            existentes = set()

        documentos_bulk = []
        now = datetime.now(timezone.utc)

        for resultado in resultados:
            dest_path = resultado.get('pdf_path_final')
            if not dest_path: continue

            # ✅ EXCLUIR: No registrar en BD si es Inbox (el usuario lo clasificará manualmente)
            if resultado.get('es_inbox'):
                logger.debug("Saltando registro en BD para Inbox: %s", os.path.basename(dest_path))
                continue

            nombre = os.path.basename(dest_path)
            if nombre in existentes:
                logger.debug("Ya existe en BD: %s", nombre)
                continue

            documentos_bulk.append({
                'empresa_id': resultado.get('empresa_id'),
                'gestoria_id': resultado.get('gestoria_id'),
                'nombre_archivo': nombre,
                'ruta_archivo': dest_path,
                'categoria': 'Inbox' if resultado.get('es_inbox') else 'Nominas',
                'periodo': resultado.get('periodo'),
                'fecha_creacion': now,
                'guardado': True,
                'procesado': True
            })

        if documentos_bulk:
            try:
                db.session.bulk_insert_mappings(Documento, documentos_bulk)
                db.session.commit()
                logger.info("%d documentos registrados en un solo batch.", len(documentos_bulk))
            except Exception as e:
                db.session.rollback()
                logger.error("Error en bulk insert de documentos: %s", e)
                raise
        else:
            logger.info("No se registraron nuevos documentos (posibles duplicados).")


def main(nominas_path):
    """
    Flujo principal optimizado
    """
    print("\n" + "="*60)
    print("🚀 PROCESADOR DE NÓMINAS")
    print("="*60)

    # Directorio temporal para PDFs divididos
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_nominas')
    os.makedirs(temp_dir, exist_ok=True)

    # Directorio de storage
    storage_dir = os.path.join(os.path.dirname(__file__), 'storage')

    # 1. Procesar PDF
    resultados = procesar_nominas(nominas_path, temp_dir)

    # 2. Asociar (Optimizado)
    print(f"\n{'='*60}")
    print("🔗 ASOCIANDO CON EMPRESAS EN BD")
    print("="*60)
    resultados = asociar_con_empresas_bd(resultados)

    # 3. Mover archivos
    print(f"\n{'='*60}")
    print("📁 MOVIENDO A CARPETAS DE EMPRESAS")
    print("="*60)
    guardar_en_carpetas_empresas(resultados, storage_dir)

    # 4. Registrar (Bulk)
    print(f"\n{'='*60}")
    print("💾 REGISTRANDO EN BASE DE DATOS")
    print("="*60)
    registrar_en_bd(resultados)

    # Limpieza: eliminar carpeta temporal con retry (Windows file locks)
    import gc
    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            gc.collect()  # Forzar liberación de recursos
            time.sleep(0.5)  # Esperar a que se liberen los archivos
            shutil.rmtree(temp_dir)
            print(f"\n🗑️ Carpeta temporal eliminada")
            break
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"\n⏳ Reintentando eliminar carpeta temporal... ({attempt + 1}/{max_retries})")
                time.sleep(1)
            else:
                print(f"\n⚠️ No se pudo eliminar carpeta temporal después de {max_retries} intentos: {e}")
        except Exception as e:
            print(f"\n⚠️ Error eliminando carpeta temporal: {e}")
            break


    # Resumen final
    total_docs = len(resultados)
    docs_clasificados = sum(1 for r in resultados if r.get('empresa_id'))
    docs_no_clasificados = total_docs - docs_clasificados
    total_trabajadores = sum(r.get('num_trabajadores', 0) for r in resultados)

    print("\n" + "="*60)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("="*60)
    print(f"\n📊 RESUMEN:")
    print(f"  • Total empresas procesadas: {total_docs}")
    print(f"  • Total trabajadores: {total_trabajadores}")
    if total_docs > 0:
        print(f"  • Empresas clasificadas: {docs_clasificados} ({(docs_clasificados/total_docs*100):.1f}%)")
        print(f"  • Empresas en __INBOX_NO_CLASIFICADOS: {docs_no_clasificados}")
        if docs_no_clasificados > 0:
            print(f"\n⚠️  Revisa la carpeta __INBOX_NO_CLASIFICADOS para clasificar manualmente")
    else:
        print(f"  • ⚠️ No se pudo procesar ninguna empresa. Verifica el formato del PDF.")
    print("="*60)

    return resultados


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python procesar_nominas.py NOMINAS_202508.pdf")
        sys.exit(1)

    nominas_path = sys.argv[1]

    if not os.path.exists(nominas_path):
        print(f"❌ Archivo no encontrado: {nominas_path}")
        sys.exit(1)

    main(nominas_path)
