"""
═══════════════════════════════════════════════════════════════════════════════
 Motor de Extracción Declarativo para Notificaciones Administrativas Españolas
═══════════════════════════════════════════════════════════════════════════════

PROBLEMA:
  - Crear 1 archivo .py por cada tipo de notificación × provincia × idioma = inviable
  - ~50 tipos de documento × ~52 provincias × 4 idiomas = miles de combinaciones

SOLUCIÓN:
  - Perfiles declarativos en JSON (almacenados en BD o archivos)
  - Un único motor genérico que interpreta las definiciones
  - Herencia de perfiles: base → tipo_documento → variante_provincial
  - Soporte multiidioma con alias de campos

ARQUITECTURA:
  ┌─────────────────────────────────────────────────────────┐
  │                    JSON Profile Store                    │
  │  (PostgreSQL / archivos .json / Redis cache)            │
  │                                                         │
  │  ┌─────────┐  ┌──────────────┐  ┌───────────────────┐  │
  │  │  BASE   │→ │  TVA-391     │→ │ TVA-391_CATALUÑA  │  │
  │  │ (TGSS)  │  │  (Embargo    │  │  (variante CAT)   │  │
  │  │         │  │   Vehículos) │  │                    │  │
  │  └─────────┘  └──────────────┘  └───────────────────┘  │
  └─────────────────────────────────────────────────────────┘
                          │
                          ▼
  ┌─────────────────────────────────────────────────────────┐
  │            DeclarativeExtractionEngine                   │
  │  1. Detectar tipo de documento (matches)                │
  │  2. Resolver herencia de perfil                         │
  │  3. Ejecutar extracción campo por campo                 │
  │  4. Post-procesado (normalización, validación)          │
  └─────────────────────────────────────────────────────────┘
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. DEFINICIÓN DE UN PERFIL DECLARATIVO (el JSON que reemplaza a cada .py)
# ═══════════════════════════════════════════════════════════════════════════════

"""
EJEMPLO DE PERFIL JSON (esto va en BD o archivo):

{
    "id": "tgss_embargo_vehiculos_tva391",
    "nombre": "Embargo de Vehículos (TVA-391)",
    "version": "1.0",
    "hereda_de": "tgss_base",           // ← herencia de campos comunes
    "idioma_principal": "es",
    
    // ── Reglas de detección (reemplaza a matches()) ──
    "deteccion": {
        "debe_contener": ["TVA-391"],
        "debe_contener_alguno": [
            ["DILIGENCIA", "JEFATURA PROVINCIAL DE TRÁFICO"],
            ["DILIGENCIA", "JEFATURA PROVINCIAL DE TRAFICO"],
            ["EMBARGO", "VEHÍCULO", "SEGURIDAD SOCIAL"]
        ],
        "no_debe_contener": ["TVA-336"],
        "prioridad": 10
    },
    
    // ── Campos a extraer (reemplaza a extract_data()) ──
    "campos": {
        "razon_social": {
            "tipo": "texto",
            "patrones": [
                "Apellidos\\s+y\\s+nombre[/\\s]*R\\.?Social[:\\s]+(.+?)(?:\\n|NIF|$)",
                "Cognoms\\s+i\\s+nom[/\\s]*R\\.?Social[:\\s]+(.+?)(?:\\n|NIF|$)"  // catalán
            ],
            "etiquetas": ["Apellidos y nombre", "Cognoms i nom", "Razón Social"]
        },
        "nif": {
            "tipo": "nif",
            "patrones": ["NIF[/\\s]*CIF[:\\s]+([A-Z0-9]{8,10})"],
            "validacion": "^[A-Z]?\\d{7,8}[A-Z]?$"
        },
        "importe_total": {
            "tipo": "importe",
            "patrones": [
                "Importe\\s+deuda\\s+pendiente[:\\s]+([\\d.,]+)",
                "Import\\s+deute\\s+pendent[:\\s]+([\\d.,]+)"  // catalán
            ]
        },
        "vehiculos": {
            "tipo": "tabla_repetitiva",
            "seccion": {
                "inicio": "VEH[IÍ]CULOS",
                "fin": "Con\\s+fecha|En\\s+virtud",
                "patron_fila": "^([A-Z0-9]{4,8})\\s{2,}([A-Z]{3,20})\\s{2,}(.+?)$",
                "columnas": ["matricula", "marca", "modelo"]
            }
        }
    },
    
    // ── Post-procesado ──
    "concepto_template": "Embargo Vehículos - {razon_social} - {len(vehiculos)} vehículo(s) - {importe_total}€",
    
    // ── Alias multiidioma ──
    "alias_idiomas": {
        "ca": {  // catalán
            "razon_social": "rao_social",
            "domicilio": "domicili",
            "localidad": "localitat",
            "fecha": "data"
        },
        "eu": {  // euskera
            "fecha": "data"
        }
    }
}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DICCIONARIO MULTIIDIOMA INTEGRADO
# ═══════════════════════════════════════════════════════════════════════════════

MULTILANG_LABELS = {
    # Etiquetas comunes en los 4 idiomas oficiales de España
    # es=castellano, ca=catalán, eu=euskera, gl=gallego
    "apellidos_nombre": {
        "es": ["Apellidos y nombre", "Nombre y apellidos", "Razón Social"],
        "ca": ["Cognoms i nom", "Nom i cognoms", "Raó social"],
        "eu": ["Abizenak eta izena", "Izen-abizenak"],
        "gl": ["Apelidos e nome", "Nome e apelidos", "Razón Social"],
    },
    "nif": {
        "es": ["NIF", "CIF", "NIF/CIF", "DNI"],
        "ca": ["NIF", "CIF", "NIF/CIF", "DNI"],
        "eu": ["IFZ", "NIF", "CIF"],
        "gl": ["NIF", "CIF", "NIF/CIF"],
    },
    "domicilio": {
        "es": ["Domicilio", "Dirección"],
        "ca": ["Domicili", "Adreça"],
        "eu": ["Helbidea", "Egoitza"],
        "gl": ["Domicilio", "Enderezo"],
    },
    "localidad": {
        "es": ["Localidad", "Municipio", "Población"],
        "ca": ["Localitat", "Municipi", "Població"],
        "eu": ["Herria", "Udalerria"],
        "gl": ["Localidade", "Municipio", "Poboación"],
    },
    "fecha": {
        "es": ["Fecha", "Fecha del documento"],
        "ca": ["Data", "Data del document"],
        "eu": ["Data", "Dokumentuaren data"],
        "gl": ["Data", "Data do documento"],
    },
    "importe": {
        "es": ["Importe", "Total", "Importe total", "Cuota"],
        "ca": ["Import", "Total", "Import total", "Quota"],
        "eu": ["Zenbatekoa", "Guztira"],
        "gl": ["Importe", "Total", "Importe total"],
    },
    "referencia": {
        "es": ["Referencia", "Nº de referencia", "Número de referencia"],
        "ca": ["Referència", "Núm. de referència"],
        "eu": ["Erreferentzia", "Erreferentzia zk."],
        "gl": ["Referencia", "Nº de referencia"],
    },
    "expediente": {
        "es": ["Expediente", "Nº Expediente"],
        "ca": ["Expedient", "Núm. Expedient"],
        "eu": ["Espedientea", "Espediente zk."],
        "gl": ["Expediente", "Nº Expediente"],
    },
    "meses": {
        "es": {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
        },
        "ca": {
            'gener': '01', 'febrer': '02', 'març': '03', 'abril': '04',
            'maig': '05', 'juny': '06', 'juliol': '07', 'agost': '08',
            'setembre': '09', 'octubre': '10', 'novembre': '11', 'desembre': '12',
        },
        "eu": {
            'urtarril': '01', 'otsail': '02', 'martxo': '03', 'apiril': '04',
            'maiatz': '05', 'ekain': '06', 'uztail': '07', 'abuztu': '08',
            'irail': '09', 'urri': '10', 'azaro': '11', 'abendu': '12',
        },
        "gl": {
            'xaneiro': '01', 'febreiro': '02', 'marzo': '03', 'abril': '04',
            'maio': '05', 'xuño': '06', 'xullo': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'decembro': '12',
        },
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MOTOR DE EXTRACCIÓN DECLARATIVO
# ═══════════════════════════════════════════════════════════════════════════════

class DeclarativeExtractionEngine:
    """
    Motor que interpreta perfiles JSON para extraer datos de notificaciones.
    Reemplaza la necesidad de crear una clase Python por cada tipo de documento.
    """

    def __init__(self, profile_store=None):
        """
        Args:
            profile_store: instancia de ProfileStore (BD, archivos, etc.)
                           Si es None, usa InMemoryProfileStore
        """
        self.store = profile_store or InMemoryProfileStore()
        self._profile_cache: Dict[str, dict] = {}
        self._resolved_cache: Dict[str, dict] = {}  # Perfiles con herencia resuelta

    # ── DETECCIÓN AUTOMÁTICA ──────────────────────────────────────────────

    def detect_profile(self, texto: str) -> Optional[dict]:
        """
        Detecta qué perfil corresponde al texto.
        Equivale al matches() de tus perfiles .py, pero declarativo.
        """
        texto_upper = re.sub(r'\s+', ' ', texto).upper()
        candidates = []

        for profile in self.store.get_all_profiles():
            deteccion = profile.get('deteccion', {})
            if self._check_detection_rules(texto_upper, deteccion):
                prioridad = deteccion.get('prioridad', 0)
                candidates.append((prioridad, profile))

        if not candidates:
            return None

        # Mayor prioridad gana
        candidates.sort(key=lambda x: x[0], reverse=True)
        winner = candidates[0][1]
        logger.info(f"🔍 Perfil detectado: {winner['nombre']} (id={winner['id']})")
        return winner

    def _check_detection_rules(self, texto_upper: str, reglas: dict) -> bool:
        """Evalúa las reglas de detección contra el texto."""
        # no_debe_contener: si aparece alguno, descartar
        for excl in reglas.get('no_debe_contener', []):
            if excl.upper() in texto_upper:
                return False

        # debe_contener: TODOS deben estar presentes
        for req in reglas.get('debe_contener', []):
            if req.upper() not in texto_upper:
                return False

        # Si hay debe_contener y se cumplió, es match
        if reglas.get('debe_contener'):
            return True

        # debe_contener_alguno: al menos UN grupo debe cumplirse completo
        for grupo in reglas.get('debe_contener_alguno', []):
            if all(term.upper() in texto_upper for term in grupo):
                return True

        # Si no hay reglas de contención, no hace match
        return bool(reglas.get('debe_contener'))

    # ── EXTRACCIÓN DE DATOS ───────────────────────────────────────────────

    def extract(self, texto: str, profile: dict = None) -> Dict[str, Any]:
        """
        Extrae datos del texto usando un perfil declarativo.
        
        Args:
            texto: texto completo del PDF
            profile: perfil JSON (si None, lo detecta automáticamente)
        
        Returns:
            dict con todos los campos extraídos
        """
        if profile is None:
            profile = self.detect_profile(texto)

        if profile is None:
            logger.warning("⚠️ Sin perfil detectado, usando extracción genérica")
            return self._extract_generic(texto)

        # Resolver herencia
        resolved = self._resolve_inheritance(profile)

        # Detectar idioma del documento
        idioma = self._detect_language(texto)
        logger.info(f"📝 Idioma detectado: {idioma}")

        # Extraer campos
        datos = {
            'organismo': resolved.get('organismo', ''),
            'tipo_documento': resolved.get('nombre', 'GENÉRICO'),
        }

        campos_def = resolved.get('campos', {})
        for nombre_campo, config in campos_def.items():
            valor = self._extract_field(texto, config, idioma)
            datos[nombre_campo] = valor

        # Post-procesado
        self._apply_post_processing(datos, resolved)

        # Metadata
        datos['_metadata'] = {
            'tipo_detectado': resolved.get('id', 'unknown'),
            'perfil_usado': True,
            'idioma': idioma,
            'metodo': 'DECLARATIVE_ENGINE',
            'version_perfil': resolved.get('version', '1.0'),
        }

        return datos

    def _extract_field(self, texto: str, config: dict, idioma: str) -> Any:
        """
        Extrae un campo individual según su configuración.
        
        Tipos soportados:
        - texto: string simple
        - nif: NIF/CIF con validación
        - importe: cantidad monetaria normalizada
        - fecha: fecha normalizada
        - tabla_repetitiva: lista de registros (ej: vehículos)
        - codigo: código alfanumérico
        """
        tipo = config.get('tipo', 'texto')

        # 1. Intentar patrones explícitos del perfil
        patrones = config.get('patrones', [])
        for patron in patrones:
            try:
                m = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
                if m:
                    raw = m.group(1).strip()
                    return self._normalize_value(raw, tipo)
            except re.error as e:
                logger.warning(f"Regex inválido en perfil: {patron} → {e}")

        # 2. Intentar por etiquetas (multiidioma)
        etiquetas = config.get('etiquetas', [])
        # Añadir etiquetas del diccionario multiidioma
        etiquetas_ml = self._get_multilang_labels(config.get('multilang_key'), idioma)
        all_labels = etiquetas + etiquetas_ml

        for label in all_labels:
            # Patrón: "Etiqueta: valor" o "Etiqueta    valor"
            patron = re.escape(label) + r'[:\s]+(.+?)(?:\n|$)'
            m = re.search(patron, texto, re.IGNORECASE)
            if m:
                raw = m.group(1).strip()
                return self._normalize_value(raw, tipo)

        # 3. Tipo especial: tabla repetitiva
        if tipo == 'tabla_repetitiva':
            return self._extract_table(texto, config.get('seccion', {}))

        # 4. Valor por defecto
        default = config.get('default')
        if default is not None:
            return default

        return '' if tipo == 'texto' else 0.0 if tipo == 'importe' else ''

    def _extract_table(self, texto: str, seccion_config: dict) -> List[dict]:
        """Extrae datos tabulares repetitivos (ej: lista de vehículos)."""
        inicio = seccion_config.get('inicio', '')
        fin = seccion_config.get('fin', r'\Z')
        patron_fila = seccion_config.get('patron_fila', '')
        columnas = seccion_config.get('columnas', [])
        excluir = seccion_config.get('excluir_valores', [])

        if not inicio or not patron_fila:
            return []

        # Encontrar la sección
        m = re.search(
            f'{inicio}\\s*\\n(.*?)(?:{fin}|\\Z)',
            texto, re.DOTALL | re.IGNORECASE
        )
        if not m:
            return []

        texto_seccion = m.group(1)
        resultados = []

        for m_fila in re.finditer(patron_fila, texto_seccion, re.MULTILINE | re.IGNORECASE):
            fila = {}
            for i, col in enumerate(columnas):
                try:
                    val = m_fila.group(i + 1).strip()
                    if val.upper() not in [e.upper() for e in excluir]:
                        fila[col] = val
                except IndexError:
                    fila[col] = ''

            if fila and all(v for v in fila.values()):
                resultados.append(fila)

        return resultados

    # ── HERENCIA DE PERFILES ──────────────────────────────────────────────

    def _resolve_inheritance(self, profile: dict) -> dict:
        """
        Resuelve la cadena de herencia de perfiles.
        Ej: tva391_cataluña → tva391 → tgss_base
        """
        profile_id = profile.get('id', '')
        if profile_id in self._resolved_cache:
            return self._resolved_cache[profile_id]

        # Construir cadena de herencia
        chain = [profile]
        current = profile
        visited = {profile_id}

        while current.get('hereda_de'):
            parent_id = current['hereda_de']
            if parent_id in visited:
                logger.warning(f"⚠️ Herencia circular detectada: {parent_id}")
                break
            visited.add(parent_id)

            parent = self.store.get_profile(parent_id)
            if not parent:
                logger.warning(f"⚠️ Perfil padre no encontrado: {parent_id}")
                break
            chain.append(parent)
            current = parent

        # Merge: padre → hijo (hijo sobreescribe)
        resolved = {}
        for p in reversed(chain):
            self._deep_merge(resolved, p)

        self._resolved_cache[profile_id] = resolved
        return resolved

    def _deep_merge(self, base: dict, override: dict):
        """Merge profundo: override gana sobre base, pero campos/patrones se combinan."""
        for key, val in override.items():
            if key == 'campos' and key in base:
                # Merge de campos: añadir patrones nuevos, no reemplazar todo
                for campo, config in val.items():
                    if campo in base['campos']:
                        # Combinar patrones
                        existing = base['campos'][campo].get('patrones', [])
                        new_patterns = config.get('patrones', [])
                        merged_patterns = existing + [p for p in new_patterns if p not in existing]
                        base['campos'][campo].update(config)
                        base['campos'][campo]['patrones'] = merged_patterns
                    else:
                        base['campos'][campo] = config
            elif isinstance(val, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], val)
            else:
                base[key] = val

    # ── DETECCIÓN DE IDIOMA ───────────────────────────────────────────────

    def _detect_language(self, texto: str) -> str:
        """
        Detecta el idioma del documento basándose en palabras clave.
        Retorna: 'es', 'ca', 'eu', 'gl'
        """
        texto_lower = texto.lower()

        # Marcadores por idioma (palabras que NO aparecen en castellano)
        markers = {
            'ca': [
                'cognoms i nom', 'domicili', 'localitat', 'data del document',
                'import', 'notificació', 'diligència', 'referència', 'expedient',
                'amb data', 'del mes de', 'gener', 'febrer', 'març', 'maig',
                'juny', 'juliol', 'setembre', 'novembre', 'desembre',
                'vehicle', 'vehicles', 'deute pendent', 'trànsit',
            ],
            'eu': [
                'abizenak eta izena', 'helbidea', 'herria', 'data',
                'jakinarazpena', 'urtarril', 'otsail', 'martxo', 'apiril',
                'maiatz', 'ekain', 'uztail', 'abuztu', 'irail', 'azaro', 'abendu',
                'zenbatekoa', 'ibilgailua',
            ],
            'gl': [
                'apelidos e nome', 'enderezo', 'localidade', 'concello',
                'xaneiro', 'febreiro', 'maio', 'xuño', 'xullo', 'setembro',
                'outubro', 'novembro', 'decembro', 'notificación ao debedor',
            ],
        }

        scores = {'es': 0, 'ca': 0, 'eu': 0, 'gl': 0}
        for lang, words in markers.items():
            for word in words:
                if word in texto_lower:
                    scores[lang] += 1

        best_lang = max(scores, key=scores.get)
        if scores[best_lang] >= 2:
            return best_lang
        return 'es'  # default castellano

    def _get_multilang_labels(self, multilang_key: str, idioma: str) -> List[str]:
        """Obtiene las etiquetas en el idioma detectado."""
        if not multilang_key:
            return []
        entry = MULTILANG_LABELS.get(multilang_key, {})
        labels = entry.get(idioma, [])
        # Siempre incluir castellano como fallback
        if idioma != 'es':
            labels = labels + entry.get('es', [])
        return labels

    # ── NORMALIZACIÓN ─────────────────────────────────────────────────────

    def _normalize_value(self, raw: str, tipo: str) -> Any:
        """Normaliza el valor extraído según su tipo."""
        if tipo == 'importe':
            return self._normalize_amount(raw)
        elif tipo == 'fecha':
            return self._normalize_date(raw)
        elif tipo == 'nif':
            return raw.upper().strip()
        elif tipo == 'codigo':
            return re.sub(r'\s+', '', raw).upper()
        else:
            return raw.strip()

    def _normalize_amount(self, text: str) -> float:
        """Normaliza importes al formato float."""
        if not text:
            return 0.0
        text = str(text).strip().replace('€', '').replace('$', '').strip()

        if ',' in text and '.' in text:
            if text.rfind(',') > text.rfind('.'):
                text = text.replace('.', '').replace(',', '.')
            else:
                text = text.replace(',', '')
        elif ',' in text:
            partes = text.split(',')
            if len(partes[-1]) <= 2:
                text = text.replace(',', '.')
            else:
                text = text.replace(',', '')

        text = re.sub(r'[^\d.-]', '', text)
        try:
            return float(text)
        except (ValueError, TypeError):
            return 0.0

    def _normalize_date(self, date_str: str) -> str:
        """Normaliza fechas multiidioma."""
        if not date_str:
            return ""

        date_str = date_str.strip()

        # Combinar meses de todos los idiomas
        all_months = {}
        for lang_months in MULTILANG_LABELS.get('meses', {}).values():
            if isinstance(lang_months, dict):
                all_months.update(lang_months)

        date_lower = date_str.lower()
        # Limpiar preposiciones en varios idiomas
        for prep in [' de ', ' del ', " d'", ' de', ' del']:
            date_lower = date_lower.replace(prep, ' ')

        for mes_nombre, mes_num in sorted(all_months.items(), key=lambda x: len(x[0]), reverse=True):
            if mes_nombre in date_lower:
                date_lower = date_lower.replace(mes_nombre, mes_num)
                break

        match = re.search(r'(\d{1,2})[-/.\s]+(\d{1,2})[-/.\s]+(\d{2,4})', date_lower)
        if match:
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if m > 12 and d <= 12:
                d, m = m, d
            y_str = str(y) if len(str(y)) == 4 else f"20{y}"
            return f"{str(d).zfill(2)}/{str(m).zfill(2)}/{y_str}"

        return date_str

    # ── POST-PROCESADO ────────────────────────────────────────────────────

    def _apply_post_processing(self, datos: dict, profile: dict):
        """Aplica template de concepto y compatibilidad con sistema existente."""
        # Template de concepto
        tpl = profile.get('concepto_template')
        if tpl:
            try:
                datos['concepto'] = tpl.format(**datos)
            except (KeyError, ValueError):
                datos['concepto'] = profile.get('nombre', '')

        # Campos de compatibilidad
        if 'importe_total' in datos and not datos.get('importe'):
            datos['importe'] = datos['importe_total']
        if 'num_referencia' in datos and not datos.get('referencia'):
            datos['referencia'] = datos['num_referencia']

    # ── EXTRACCIÓN GENÉRICA (FALLBACK) ────────────────────────────────────

    def _extract_generic(self, texto: str) -> Dict[str, Any]:
        """Extracción sin perfil: intenta sacar campos básicos con heurísticas."""
        datos = {
            'organismo': 'DESCONOCIDO',
            'tipo_documento': 'GENÉRICO',
            'referencia': '',
            'fecha': '',
            'importe': 0.0,
            'nif': '',
            'concepto': '',
        }

        texto_upper = texto.upper()

        # Detectar organismo
        if 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL' in texto_upper:
            datos['organismo'] = 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL'
        elif 'AGENCIA TRIBUTARIA' in texto_upper or 'AEAT' in texto_upper:
            datos['organismo'] = 'AGENCIA TRIBUTARIA'
        elif 'AGÈNCIA TRIBUTÀRIA' in texto_upper:
            datos['organismo'] = 'AGENCIA TRIBUTARIA'

        # NIF genérico
        m = re.search(r'(?:NIF|CIF|DNI)[/\s:]+([A-Z]?\d{7,8}[A-Z]?)', texto, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).upper()

        # Referencia genérica
        m = re.search(r'(?:Referencia|Referència|Erreferentzia)[:\s]+([A-Z0-9\-/]+)', texto, re.IGNORECASE)
        if m:
            datos['referencia'] = m.group(1)

        # Fecha genérica (multiidioma)
        m = re.search(r'(\d{1,2})\s+(?:de\s+)?(\w+)\s+(?:de\s+)?(\d{4})', texto)
        if m:
            datos['fecha'] = self._normalize_date(m.group(0))

        # Importe genérico
        for pattern in [
            r'[Ii]mporte[:\s]+([\d.,]+)',
            r'[Tt]otal[:\s]+([\d.,]+)',
            r'[Ii]mport[:\s]+([\d.,]+)',  # catalán
        ]:
            m = re.search(pattern, texto)
            if m:
                datos['importe'] = self._normalize_amount(m.group(1))
                break

        datos['_metadata'] = {
            'tipo_detectado': 'GENÉRICO',
            'perfil_usado': False,
            'idioma': self._detect_language(texto),
            'metodo': 'GENERIC_FALLBACK',
        }

        return datos


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PROFILE STORES (dónde guardar los perfiles)
# ═══════════════════════════════════════════════════════════════════════════════

class InMemoryProfileStore:
    """Store simple en memoria (para testing o apps pequeñas)."""

    def __init__(self):
        self._profiles: Dict[str, dict] = {}

    def add_profile(self, profile: dict):
        self._profiles[profile['id']] = profile

    def get_profile(self, profile_id: str) -> Optional[dict]:
        return self._profiles.get(profile_id)

    def get_all_profiles(self) -> List[dict]:
        return list(self._profiles.values())

    def load_from_directory(self, directory: str):
        """Carga todos los .json de un directorio."""
        path = Path(directory)
        for json_file in path.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    if 'id' in profile:
                        self.add_profile(profile)
                        logger.info(f"✅ Perfil cargado: {profile['id']} ({json_file.name})")
            except Exception as e:
                logger.warning(f"⚠️ Error cargando {json_file}: {e}")


class DatabaseProfileStore:
    """
    Store en PostgreSQL - para producción con SpainFlow.
    
    Tabla sugerida:
    CREATE TABLE extraction_profiles (
        id VARCHAR(100) PRIMARY KEY,
        nombre VARCHAR(255),
        version VARCHAR(10) DEFAULT '1.0',
        hereda_de VARCHAR(100) REFERENCES extraction_profiles(id),
        idioma_principal VARCHAR(5) DEFAULT 'es',
        profile_json JSONB NOT NULL,
        activo BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    
    CREATE INDEX idx_profiles_activo ON extraction_profiles(activo);
    """

    def __init__(self, db_session):
        self.db = db_session
        self._cache: Dict[str, dict] = {}

    def get_profile(self, profile_id: str) -> Optional[dict]:
        if profile_id in self._cache:
            return self._cache[profile_id]

        # Query BD
        from models import ExtractionTemplate  # Tu modelo SQLAlchemy
        row = ExtractionTemplate.query.filter_by(id=profile_id, activo=True).first()
        if row:
            profile = row.profile_json
            profile['id'] = row.id
            self._cache[profile_id] = profile
            return profile
        return None

    def get_all_profiles(self) -> List[dict]:
        from models import ExtractionTemplate
        rows = ExtractionTemplate.query.filter_by(activo=True).all()
        profiles = []
        for row in rows:
            p = row.profile_json
            p['id'] = row.id
            profiles.append(p)
            self._cache[row.id] = p
        return profiles

    def add_profile(self, profile: dict):
        from models import ExtractionTemplate
        row = ExtractionTemplate(
            id=profile['id'],
            nombre=profile.get('nombre', ''),
            version=profile.get('version', '1.0'),
            hereda_de=profile.get('hereda_de'),
            idioma_principal=profile.get('idioma_principal', 'es'),
            profile_json=profile,
        )
        self.db.add(row)
        self.db.commit()
        self._cache[profile['id']] = profile

    def invalidate_cache(self):
        self._cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EJEMPLOS DE PERFILES JSON (los que reemplazan a tus .py)
# ═══════════════════════════════════════════════════════════════════════════════

EXAMPLE_PROFILES = {
    # ── PERFIL BASE TGSS (heredado por todos los docs de Seg. Social) ─────
    "tgss_base": {
        "id": "tgss_base",
        "nombre": "Base TGSS",
        "version": "1.0",
        "organismo": "TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL",
        "idioma_principal": "es",
        "deteccion": {
            "debe_contener": ["SEGURIDAD SOCIAL"],
            "prioridad": 1,
        },
        "campos": {
            "razon_social": {
                "tipo": "texto",
                "patrones": [
                    r"Apellidos\s+y\s+nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|NIF|$)",
                    r"Cognoms\s+i\s+nom[/\s]*R\.?Social[:\s]+(.+?)(?:\n|NIF|$)",
                ],
                "multilang_key": "apellidos_nombre",
            },
            "nif": {
                "tipo": "nif",
                "patrones": [r"NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})"],
                "multilang_key": "nif",
                "validacion": r"^[A-Z]?\d{7,8}[A-Z]?$",
            },
            "domicilio": {
                "tipo": "texto",
                "patrones": [r"Domicilio[:\s]+(.+?)(?:\n|Localidad|Localitat|$)"],
                "multilang_key": "domicilio",
            },
            "localidad": {
                "tipo": "texto",
                "patrones": [r"Localidad[:\s]+(.+?)(?:\n|Importe|Import|$)"],
                "multilang_key": "localidad",
            },
            "num_referencia": {
                "tipo": "codigo",
                "patrones": [r"N[ºo°]?\s*de\s*referencia[:\s]+(\d{15,20})"],
                "multilang_key": "referencia",
            },
            "tipo_identificador": {
                "tipo": "texto",
                "patrones": [r"Tipo[/\s]*Identificador[:\s]+(\d{2}\s+\d{12})"],
            },
            "regimen": {
                "tipo": "codigo",
                "patrones": [r"R[eé]gimen[:\s]+(\d{4})"],
            },
            "expediente": {
                "tipo": "texto",
                "patrones": [r"Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})"],
                "multilang_key": "expediente",
            },
            "fecha": {
                "tipo": "fecha",
                "patrones": [
                    r"(?:a\s+)?(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})",
                    r"Fecha[:\s]+(\d{2}/\d{2}/\d{4})",
                    r"Data[:\s]+(\d{2}/\d{2}/\d{4})",  # catalán
                ],
                "multilang_key": "fecha",
            },
            "iban": {
                "tipo": "texto",
                "patrones": [
                    r"(?:N[ÚU]MERO\s+DE\s+CUENTA|IBAN|Cuenta\s+de\s+ingreso)[:\s]+(ES\d{2}[\s\d]{15,25})",
                ],
            },
            "referencia_verificacion": {
                "tipo": "texto",
                "patrones": [
                    r"C[oó]digo[:\s]+([A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,})",
                ],
            },
        },
    },

    # ── TVA-391 EMBARGO VEHÍCULOS (hereda de tgss_base) ──────────────────
    "tgss_embargo_vehiculos_tva391": {
        "id": "tgss_embargo_vehiculos_tva391",
        "nombre": "Embargo de Vehículos (TVA-391)",
        "version": "1.0",
        "hereda_de": "tgss_base",
        "deteccion": {
            "debe_contener_alguno": [
                ["TVA-391"],
                ["DILIGENCIA", "JEFATURA PROVINCIAL DE TRÁFICO"],
                ["DILIGENCIA", "JEFATURA PROVINCIAL DE TRAFICO"],
                ["EMBARGO", "VEHÍCULO", "SEGURIDAD SOCIAL"],
                ["EMBARGO", "VEHICULO", "SEGURIDAD SOCIAL"],
                # Catalán
                ["DILIGÈNCIA", "PREFECTURA PROVINCIAL DE TRÀNSIT"],
                ["EMBARGAMENT", "VEHICLE", "SEGURETAT SOCIAL"],
            ],
            "no_debe_contener": ["TVA-336"],
            "prioridad": 10,
        },
        "campos": {
            # Campos adicionales (los comunes ya vienen de tgss_base)
            "num_documento": {
                "tipo": "texto",
                "patrones": [r"N[ºo°]?\s*Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})"],
            },
            "importe_total": {
                "tipo": "importe",
                "patrones": [
                    r"Importe\s+deuda\s+pendiente[:\s]+([\d.,]+)",
                    r"Import\s+deute\s+pendent[:\s]+([\d.,]+)",
                ],
                "multilang_key": "importe",
            },
            "importe_principal": {
                "tipo": "importe",
                "patrones": [r"(?:Importe\s+)?[Pp]rincipal[:\s]+([\d.,]+)"],
                "default": 0.0,
            },
            "importe_recargo": {
                "tipo": "importe",
                "patrones": [r"[Rr]ecargo[:\s]+([\d.,]+)", r"[Rr]ecàrrec[:\s]+([\d.,]+)"],
                "default": 0.0,
            },
            "importe_intereses": {
                "tipo": "importe",
                "patrones": [r"[Ii]nter[eé]s[^:]*?[:\s]+([\d.,]+)"],
                "default": 0.0,
            },
            "importe_costas": {
                "tipo": "importe",
                "patrones": [r"[Cc]ostas[^:]*?[:\s]+([\d.,]+)", r"[Cc]ostes[^:]*?[:\s]+([\d.,]+)"],
                "default": 0.0,
            },
            "vehiculos": {
                "tipo": "tabla_repetitiva",
                "seccion": {
                    "inicio": r"VEH[IÍ]CULOS",
                    "fin": r"Con\s+fecha|En\s+virtud|Amb\s+data",
                    "patron_fila": r"^([A-Z0-9]{4,8})\s{2,}([A-ZÁÉÍÓÚÑ]{3,20})\s{2,}([A-ZÁÉÍÓÚÑA-Z\s]{1,20}?)\s*$",
                    "columnas": ["matricula", "marca", "modelo"],
                    "excluir_valores": ["MATRICULA", "MATRÍCULA", "MODELO", "MARCA"],
                },
            },
            "entidad_financiera": {
                "tipo": "texto",
                "patrones": [r"ENTIDAD\s+FINANCIERA[:\s]+(.+?)(?:\n|$)"],
            },
        },
        "concepto_template": "Embargo Vehículos - {razon_social} - {importe_total}€",
    },

    # ── TVA-391 VARIANTE CATALUÑA (hereda de tva391, añade catalán) ──────
    "tgss_embargo_vehiculos_tva391_cat": {
        "id": "tgss_embargo_vehiculos_tva391_cat",
        "nombre": "Embargo de Vehicles (TVA-391) - Cataluña",
        "version": "1.0",
        "hereda_de": "tgss_embargo_vehiculos_tva391",
        "idioma_principal": "ca",
        "deteccion": {
            "debe_contener_alguno": [
                ["TVA-391", "TRÀNSIT"],
                ["DILIGÈNCIA", "PREFECTURA PROVINCIAL DE TRÀNSIT"],
                ["EMBARGAMENT", "VEHICLE"],
            ],
            "no_debe_contener": ["TVA-336"],
            "prioridad": 15,  # Mayor prioridad que el genérico
        },
        "campos": {
            # Solo añade patrones catalanes extras; los castellanos ya están heredados
            "razon_social": {
                "tipo": "texto",
                "patrones": [
                    r"Cognoms\s+i\s+nom[/\s]*R\.?Social[:\s]+(.+?)(?:\n|NIF|$)",
                ],
            },
            "domicilio": {
                "tipo": "texto",
                "patrones": [r"Domicili[:\s]+(.+?)(?:\n|Localitat|$)"],
            },
            "localidad": {
                "tipo": "texto",
                "patrones": [r"Localitat[:\s]+(.+?)(?:\n|Import|$)"],
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. INTEGRACIÓN CON TU SISTEMA EXISTENTE (bridge)
# ═══════════════════════════════════════════════════════════════════════════════

class DeclarativeNotificacionExtractor:
    """
    Drop-in replacement para NotificacionExtractor que usa el motor declarativo.
    Compatible con tu sistema actual de plantillas y mesa de trabajo.
    """

    def __init__(self, profile_source='memory'):
        """
        Args:
            profile_source: 'memory', 'files', 'database'
        """
        if profile_source == 'database':
            from extensions import db
            self.store = DatabaseProfileStore(db.session)
        elif profile_source == 'files':
            self.store = InMemoryProfileStore()
            self.store.load_from_directory('extraction_profiles/json/')
        else:
            self.store = InMemoryProfileStore()
            # Cargar perfiles de ejemplo
            for profile in EXAMPLE_PROFILES.values():
                self.store.add_profile(profile)

        self.engine = DeclarativeExtractionEngine(self.store)

        # PDFExtractor para leer PDFs
        try:
            from services.pdf_extractor import PDFExtractor
            self._pdf = PDFExtractor()
        except ImportError:
            import fitz
            class _SimplePDF:
                def extract_text_from_pdf(self, path):
                    doc = fitz.open(path)
                    text = "".join(page.get_text() for page in doc)
                    doc.close()
                    return text
            self._pdf = _SimplePDF()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        result = self._pdf.extract_text_from_pdf(pdf_path)
        return result[0] if isinstance(result, tuple) else (result or "")

    def extract_notification_data(self, pdf_path: str) -> Dict[str, Any]:
        """API principal: extrae datos de un PDF de notificación."""
        texto = self.extract_text_from_pdf(pdf_path)
        if not texto:
            return {'error': 'Sin texto en PDF'}

        datos = self.engine.extract(texto)
        datos['_texto_ocr'] = texto
        return datos

    def extract_with_template(self, pdf_path: str, plantilla: dict) -> Dict[str, Any]:
        """Compatible con PlantillaTestBench."""
        datos = self.extract_notification_data(pdf_path)

        # Mapear al formato de la plantilla
        mapping_keys = {
            'fecha': ['fecha', 'fecha factura', 'fecha devengo', 'fecha notificacion'],
            'importe': ['importe', 'total', 'importe total', 'cuota'],
            'importe_total': ['importe total', 'total deuda'],
            'nif': ['nif', 'cif', 'identificador'],
            'referencia': ['referencia', 'ref', 'expediente'],
            'csv': ['csv', 'código seguro verificación'],
            'concepto': ['concepto', 'descripcion'],
        }

        final = {}
        for key_plantilla in plantilla.get('campos', {}).keys():
            key_norm = key_plantilla.lower().replace('_', ' ').strip()
            for tipo_dato, posibles in mapping_keys.items():
                if any(n in key_norm for n in posibles):
                    val = datos.get(tipo_dato)
                    if val:
                        final[key_plantilla] = val
                    break
            # Fallback: clave exacta
            if key_plantilla not in final and key_plantilla in datos:
                final[key_plantilla] = datos[key_plantilla]

        final['_metadata'] = datos.get('_metadata', {})
        final['_texto_ocr'] = datos.get('_texto_ocr', '')
        return final


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CLI PARA GESTIÓN DE PERFILES
# ═══════════════════════════════════════════════════════════════════════════════

def create_profile_cli():
    """
    Herramienta CLI para crear perfiles interactivamente.
    Uso: python declarative_extraction_engine.py create
    """
    import sys

    print("═" * 60)
    print(" Crear Perfil de Extracción Declarativo")
    print("═" * 60)

    profile = {
        "version": "1.0",
        "idioma_principal": "es",
        "deteccion": {},
        "campos": {},
    }

    profile['id'] = input("ID del perfil (ej: tgss_providencia_apremio): ").strip()
    profile['nombre'] = input("Nombre descriptivo: ").strip()

    parent = input("¿Hereda de otro perfil? (ID o vacío): ").strip()
    if parent:
        profile['hereda_de'] = parent

    print("\n── Reglas de detección ──")
    debe = input("Palabras que DEBEN estar (separadas por coma): ").strip()
    if debe:
        profile['deteccion']['debe_contener'] = [w.strip() for w in debe.split(',')]

    no_debe = input("Palabras que NO deben estar (separadas por coma): ").strip()
    if no_debe:
        profile['deteccion']['no_debe_contener'] = [w.strip() for w in no_debe.split(',')]

    profile['deteccion']['prioridad'] = int(input("Prioridad (1-20, mayor=gana): ") or "5")

    print("\n── Campos ──")
    print("Tipos: texto, importe, fecha, nif, codigo, tabla_repetitiva")
    while True:
        nombre = input("\nNombre del campo (vacío para terminar): ").strip()
        if not nombre:
            break
        tipo = input(f"  Tipo de '{nombre}': ").strip() or "texto"
        patron = input(f"  Patrón regex (grupo 1 = valor): ").strip()

        campo = {"tipo": tipo}
        if patron:
            campo["patrones"] = [patron]

        label = input(f"  Etiqueta en el PDF (ej: 'Referencia'): ").strip()
        if label:
            campo["etiquetas"] = [label]

        profile['campos'][nombre] = campo

    # Guardar
    filename = f"{profile['id']}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Perfil guardado en: {filename}")
    print(json.dumps(profile, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'create':
        create_profile_cli()
    else:
        # Demo: cargar perfiles y probar detección
        store = InMemoryProfileStore()
        for p in EXAMPLE_PROFILES.values():
            store.add_profile(p)

        engine = DeclarativeExtractionEngine(store)

        # Simular texto de prueba
        test_text = """
        TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL
        TVA-391
        Notificación al Deudor de la Diligencia para Comunicar a la
        Jefatura Provincial de Tráfico
        
        Apellidos y nombre/R.Social: EMPRESA EJEMPLO SL
        NIF/CIF: B12345678
        Domicilio: CALLE FALSA 123
        Localidad: BARCELONA
        
        Importe deuda pendiente: 2.009,69
        
        VEHÍCULOS
        MATRÍCULA    MARCA       MODELO
        6659LSX      PEUGEOT     RIFTER
        
        Con fecha 12 de DICIEMBRE de 2025
        """

        result = engine.extract(test_text)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
