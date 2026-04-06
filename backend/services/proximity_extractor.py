# backend/services/proximity_extractor.py
"""
Extractor de campos por proximidad de etiquetas en texto OCR.

Para documentos de Hacienda / Ajuntament / TGSS donde el OCR genera
una estructura con la etiqueta en una línea y el valor en la siguiente:

    Data de la provisió
    18/07/2025
    
    Càrrec
    CR202510007024068
    
    Import
    84,56 €

Este extractor es mucho más robusto que regex tradicionales para
estos documentos porque no depende de la formateación exacta.
"""

import re
import logging

try:
    from etiquetas_por_tipo import ETIQUETAS_POR_TIPO
except ImportError:
    try:
        from .etiquetas_por_tipo import ETIQUETAS_POR_TIPO
    except ImportError:
        ETIQUETAS_POR_TIPO = {}
except Exception:
    ETIQUETAS_POR_TIPO = {}

logger = logging.getLogger(__name__)

# Máxima longitud de una línea para que se considere etiqueta (no párrafo)
MAX_LABEL_LEN = 70
# Máxima longitud de un valor (evita capturar párrafos enteros)
MAX_VALOR_LEN = 120

# Palabras que invalidan una captura si el valor solo contiene esto (párrafos)
STOP_WORDS = {"de", "del", "la", "el", "y", "a", "ante", "bajo", "con", "en", "para", "por", "su", "sus"}
# Campos que deberían ser numéricos
NUMERIC_FIELDS = {"importe", "total", "recarrec", "recargo", "intereses", "interessos", "costas", "costes", "importe_recargo", "principal"}


def extraer_por_proximidad(texto: str, tipo_clave: str, etiquetas_extra: dict = None, mapeo_lineas: dict = None) -> dict:
    """
    Extrae campos de un documento OCR usando detección por proximidad de etiquetas.
    
    mapeo_lineas: dict opcional de { campo: "numero_linea" o "inicio-fin" }
    """
    # Normalizar texto: unificar comillas y otros símbolos
    for char in "’‘´`": 
        texto = texto.replace(char, "'")
    for char in "“”»«":
        texto = texto.replace(char, '"')
    
    # Obtener etiquetas base
    etiquetas = dict(ETIQUETAS_POR_TIPO.get(tipo_clave, ETIQUETAS_POR_TIPO.get('_generico', {})))
    
    # ... (combinar etiquetas_extra si existen)
    if etiquetas_extra:
        for campo, variantes in etiquetas_extra.items():
            if isinstance(variantes, str):
                variantes = [v.strip() for v in variantes.split(',') if v.strip()]
            
            # Si el campo es 'boundary_tags', lo extendemos especialmente
            if campo == 'boundary_tags':
                if 'boundary_tags' not in etiquetas: etiquetas['boundary_tags'] = []
                etiquetas['boundary_tags'] = variantes + [v for v in etiquetas['boundary_tags'] if v not in variantes]
                continue

            if campo in etiquetas:
                etiquetas[campo] = variantes + [v for v in etiquetas[campo] if v not in variantes]
            else:
                etiquetas[campo] = variantes

    # Preprocesar: dividir en líneas limpias
    lineas_raw = [l.strip() for l in texto.replace('\r', '\n').split('\n')]
    
    # Generar texto con números de línea para el UI (debug)
    texto_lineado = "\n".join([f"[LINE {i+1:03d}] {l}" for i, l in enumerate(lineas_raw)])

    # Eliminar líneas completamente vacías consecutivas para el motor de proximidad
    lineas_limpias = []
    prev_vacia = False
    for l in lineas_raw:
        if not l:
            if not prev_vacia:
                lineas_limpias.append(l)
            prev_vacia = True
        else:
            lineas_limpias.append(l)
            prev_vacia = False

    resultado = {}
    resultado["_metadata"] = {
        "metodo": "HYBRID_PROXIMITY",
        "total_lineas": len(lineas_raw),
        "texto_lineado": texto_lineado
    }
    
    n = len(lineas_limpias)
    n_raw = len(lineas_raw)

    # Iterar cada campo que queremos buscar
    for campo, variantes_etiqueta in etiquetas.items():
        valor_encontrado = None

        # ESTRATEGIA 0: Líneas fijas (asignación manual por el usuario)
        if mapeo_lineas and campo in mapeo_lineas:
            rule = str(mapeo_lineas[campo]).strip()
            if rule:
                try:
                    vals = []
                    if '-' in rule:
                        start, end = map(int, rule.split('-'))
                        for idx in range(start, end + 1):
                            if 1 <= idx <= n_raw: vals.append(lineas_raw[idx-1])
                    elif ',' in rule:
                        for idx_str in rule.split(','):
                            idx = int(idx_str.strip())
                            if 1 <= idx <= n_raw: vals.append(lineas_raw[idx-1])
                    else:
                        idx = int(rule)
                        if 1 <= idx <= n_raw: vals.append(lineas_raw[idx-1])
                    
                    if vals:
                        valor_encontrado = _limpiar_valor(" ".join(vals))
                        if valor_encontrado:
                            resultado[campo] = valor_encontrado
                            continue # Si hay línea fija, pasamos al siguiente campo
                except Exception as e:
                    logger.error(f"Error procesando regla de línea fija {rule} para {campo}: {e}")

        # Si no hay línea fija o falló, seguimos con Proximidad
        for etiqueta in variantes_etiqueta:
            etiqueta_lower = etiqueta.lower()
            # Normalizar comillas y apostrofes en la etiqueta también
            for char in "’‘´`": 
                etiqueta_lower = etiqueta_lower.replace(char, "'")
            for char in "“”»«":
                etiqueta_lower = etiqueta_lower.replace(char, '"')

            for i, linea in enumerate(lineas_limpias):
                linea_lower = linea.lower()
                valor_encontrado = None
                linea_objetivo = linea_lower
                usar_dos_lineas = False
                
                # PATRÓN 1: El label está en una sola línea
                patron_wb = r'(?<![a-zA-Z0-9\u00c0-\u024f])' + re.escape(etiqueta_lower) + r'(?![a-zA-Z0-9\u00c0-\u024f])'
                match_label = re.search(patron_wb, linea_lower)
                
                # PATRÓN 2: El label está dividido en dos líneas (ej: "Termini" \n "de pagament")
                if not match_label and ' ' in etiqueta_lower and i + 1 < n:
                    posible_dos_lineas = (linea_lower + " " + lineas_limpias[i+1].lower()).strip()
                    match_label = re.search(patron_wb, posible_dos_lineas)
                    if match_label:
                        linea_objetivo = posible_dos_lineas
                        usar_dos_lineas = True

                if not match_label: continue

                # Determinar desde qué línea empezar a buscar el valor
                offset_valor = 2 if usar_dos_lineas else 1

                # Estrategia 1: Misma línea con ":" 
                linea_para_colon = lineas_limpias[i+1] if usar_dos_lineas else linea
                if ':' in linea_para_colon:
                    parts = linea_para_colon.split(':', 1)
                    if len(parts) > 1:
                        resto = parts[1].strip()
                        if resto and not _es_solo_separador(resto) and len(resto) <= MAX_VALOR_LEN:
                            valor_encontrado = _limpiar_valor(resto)
                            if valor_encontrado: break

                # Estrategia 2: Etiqueta sola → valor en línea siguiente (greedy multiline)
                proporcion = len(etiqueta_lower) / max(len(linea_objetivo), 1)
                if proporcion > 0.4 or linea_objetivo.strip() == etiqueta_lower:
                    lineas_valor = []
                    for j in range(i + offset_valor, min(i + offset_valor + 10, n)):
                        candidate = lineas_limpias[j].strip()
                        if not candidate: continue
                        
                        # Si encontramos otra etiqueta conocida al INICIO, paramos
                        if _es_etiqueta_conocida(candidate, etiquetas):
                            break
                        
                        # Si la línea tiene un ":" (posible nueva etiqueta), paramos
                        if ':' in candidate and len(candidate.split(':')[0]) < 25:
                            if len(candidate.split(':')[1].strip()) > 0:
                                break
                        
                        # ANTI-BLEEDING: ¿Hay otra etiqueta dentro de esta línea?
                        indice_corte = _encontrar_inicio_otra_etiqueta(candidate, etiquetas)
                        if indice_corte != -1:
                            cleaned_part = _limpiar_valor(candidate[:indice_corte])
                            if cleaned_part: lineas_valor.append(cleaned_part)
                            break

                        cleaned = _limpiar_valor(candidate)
                        if cleaned:
                            if len(cleaned) == 1 and cleaned in '.-•·' and len(lineas_valor) > 0:
                                continue
                            lineas_valor.append(cleaned)
                    
                    if lineas_valor:
                        valor_encontrado = " ".join(lineas_valor)
                        break

                # Estrategia 3: Etiqueta + espacios + valor (Estricto para evitar párrafos)
                if not usar_dos_lineas:
                    # Capturamos el resto de la línea
                    # Caso A: Etiqueta al principio absoluto de línea + 1 o más espacios (común en tablas)
                    patron_inicio = r'^[^a-zA-Z0-9\u00c0-\u024f]*' + re.escape(etiqueta_lower) + r'\s+(.+)'
                    # Caso B: Etiqueta en cualquier sitio + 2 o más espacios (para evitar capturar palabras dentro de frases)
                    patron_medio = re.escape(etiqueta_lower) + r'\s{2,}(.+)'
                    
                    m = re.search(patron_inicio, linea_lower) or re.search(patron_medio, linea_lower)
                    if m:
                        candidato_raw = m.group(1).strip()
                        # Anti-bleeding: cortar si aparece otra etiqueta después
                        indice_corte = _encontrar_inicio_otra_etiqueta(candidato_raw, etiquetas)
                        if indice_corte != -1:
                            candidato_raw = candidato_raw[:indice_corte].strip()

                        if candidato_raw and len(candidato_raw) <= MAX_VALOR_LEN:
                            valor_encontrado = _limpiar_valor(candidato_raw)
                            # Validación extra para evitar "de la", "y", etc.
                            if not _validar_valor(valor_encontrado, campo):
                                valor_encontrado = None
                            
                            if valor_encontrado: break
            
            if valor_encontrado:
                resultado[campo] = valor_encontrado
                logger.debug(f"  [{tipo_clave}] {campo} = {valor_encontrado!r}")
                break 

    return resultado


def _encontrar_inicio_otra_etiqueta(texto: str, etiquetas: dict) -> int:
    """Busca si dentro de un texto aparece alguna de las etiquetas conocidas."""
    texto_lower = texto.lower()
    menor_indice = -1
    
    for variantes in etiquetas.values():
        for e in variantes:
            e_lower = e.lower()
            # Word boundary robusto
            patron = r'(?<![a-zA-Z0-9\u00c0-\u024f])' + re.escape(e_lower) + r'(?![a-zA-Z0-9\u00c0-\u024f])'
            m = re.search(patron, texto_lower)
            if m:
                if menor_indice == -1 or m.start() < menor_indice:
                    menor_indice = m.start()
                    
    return menor_indice


def _es_etiqueta_conocida(texto: str, etiquetas: dict) -> bool:
    """Comprueba si un texto es una etiqueta conocida."""
    texto_lower = texto.lower()
    for variantes in etiquetas.values():
        for e in variantes:
            if e.lower() == texto_lower or e.lower() in texto_lower:
                return True
    return False


def _es_solo_separador(texto: str) -> bool:
    """Comprueba si el texto es solo separadores."""
    return bool(re.match(r'^[-=_|.:\s]{2,}$', texto))


def _limpiar_valor(texto: str) -> str:
    """Limpia el valor extraído."""
    # Quitar separadores al inicio/fin, incluyendo barras verticales de tablas OCR
    texto = texto.strip().strip(':-|').strip()
    # Limpiar caracteres raros de OCR al inicio/fin (específicamente puntos o comas sueltos delante)
    texto = re.sub(r'^[|/\\_.,]+', '', texto).strip()
    # Limitar longitud razonable
    if len(texto) > 500:
        texto = texto[:500]
    return texto if texto else None


def _validar_valor(valor: str, campo: str) -> bool:
    """Valida si el valor capturado es razonable para el campo."""
    if not valor: return False
    
    val_lower = valor.lower().strip()
    
    # 1. Si el valor es íntegramente stop words (conectores de párrafos), rechazar
    words = [w for w in re.split(r'\W+', val_lower) if w]
    if all(w in STOP_WORDS for w in words) and len(words) <= 3:
        return False
        
    # 2. Si el campo es numérico, debe contener al menos un dígito
    if any(nf in campo.lower() for nf in NUMERIC_FIELDS):
        if not any(char.isdigit() for char in valor):
            return False
            
    # 3. Longitud mínima para nombres
    if 'nombre' in campo or 'nom' in campo:
        if len(valor) < 3: return False
        
    return True
