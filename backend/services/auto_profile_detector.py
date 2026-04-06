# backend/services/auto_profile_detector.py
"""
Servicio de autodetección y creación automática de perfiles.

Cuando un documento no coincide con ningún perfil existente, este servicio:
1. Lee el texto OCR del documento
2. Identifica el emisor y tipo de documento
3. Crea automáticamente un ConfiguracionPerfil sin destino (pendiente de configurar)
4. Crea un ExtractionTemplate con campos pre-populados según el tipo detectado
5. Devuelve el perfil creado para que el usuario configure el destino

El usuario solo necesita seleccionar carpeta + departamento; el perfil ya existe
con campos de extracción listos. Puede refinarlos desde el editor de plantillas.
"""

import re
import logging
import unicodedata
from models import ConfiguracionPerfil
from extensions import db

logger = logging.getLogger(__name__)


# ─── Patrones de detección de emisor ───
EMISORES = [
    # Hacienda / AEAT
    (r'agencia\s+estatal\s+de\s+administraci[oó]n\s+tributaria|A\.?E\.?A\.?T\.?|agencia\s+tributaria',
     'AEAT', 'Agencia Tributaria'),

    # Seguridad Social / TGSS
    (r'tesorer[ií]a\s+general\s+de\s+la\s+seguridad\s+social|T\.?G\.?S\.?S\.?',
     'TGSS', 'Seguridad Social (TGSS)'),

    # INSS
    (r'instituto\s+nacional\s+de\s+la\s+seguridad\s+social|I\.?N\.?S\.?S\.?',
     'INSS', 'INSS'),

    # SEPE / INEM
    (r'servicio\s+p[uú]blico\s+de\s+empleo\s+estatal|S\.?E\.?P\.?E\.?|servei\s+public\s+d\'ocupaci[oó]',
     'SEPE', 'SEPE'),

    # Comunidades Autónomas
    (r'generalitat\s+de\s+catalunya|departament\s+de\s+treball', 'GCAT', 'Generalitat de Catalunya'),
    (r'junta\s+de\s+andaluc[ií]a', 'JAND', 'Junta de Andalucía'),
    (r'gobierno\s+de\s+arag[oó]n|departamento.*arag[oó]n', 'GARAGON', 'Gobierno de Aragón'),
    (r'comunitat\s+valenciana|generalitat\s+valenciana', 'GVAL', 'Generalitat Valenciana'),
    (r'govern\s+de\s+les\s+illes\s+balears|govern\s+balear', 'GBALS', 'Govern de les Illes Balears'),

    # Ayuntamientos (genérico + específicos)
    (r'ajuntament\s+de\s+barcelona', 'AJBCN', 'Ajuntament de Barcelona'),
    (r'ajuntament\s+de\s+([a-zA-Záéíóúàèìòùüñ\s]+?)(?:\n|$)', 'AJCAT', None),
    (r'ayuntamiento\s+de\s+([a-zA-Záéíóúàèìòùüñ\s]+?)(?:\n|,|$)', 'AYTO', None),

    # DGT
    (r'direcci[oó]n\s+general\s+de\s+tr[aá]fico|D\.?G\.?T\.?', 'DGT', 'DGT'),

    # Catastro
    (r'catastro\s+inmobiliario|direcci[oó]n\s+general\s+del\s+catastro', 'CATASTRO', 'Catastro'),

    # Registro Mercantil
    (r'registro\s+mercantil', 'REGMERCANTIL', 'Registro Mercantil'),

    # Colegio profesional
    (r'colegio\s+oficial\s+de\s+([a-zA-Záéíóúàèìòùüñ\s]+?)(?:\n|,|$)', 'COLEGIO', None),

    # Notaría
    (r'notar[ií]a\s+de\s+([a-zA-Záéíóúàèìòùüñ\s]+?)(?:\n|$)', 'NOTARIA', None),
]


# ─── Patrones de detección del tipo de documento ───
TIPOS_DOCUMENTO = [
    (r'provid[êe]ncia\s+de\s+constrenyiment|provisi[oó]\s+de\s+constrenyiment',
     'provisio_constrenyiment', 'Provisió de Constrenyiment'),

    (r'providencia\s+de\s+apremio',
     'providencia_apremio', 'Providencia de Apremio'),

    (r'diligencia\s+de\s+embargo\s+de\s+veh[ií]culos?',
     'embargo_vehiculos', 'Embargo de Vehículos'),

    (r'diligencia\s+de\s+embargo\s+de\s+cuentas?|embargo\s+de\s+cuenta',
     'embargo_cuentas', 'Embargo de Cuentas Bancarias'),

    (r'diligencia\s+de\s+embargo\s+de\s+cr[eé]ditos?|embargo\s+de\s+cr[eé]dito',
     'embargo_creditos', 'Embargo de Créditos'),

    (r'diligencia\s+de\s+embargo\s+de\s+bienes\s+inmuebles?|embargo\s+inmueble',
     'embargo_inmuebles', 'Embargo de Bienes Inmuebles'),

    (r'regularizaci[oó]n\s+reta|cuotas?\s+de\s+aut[oó]nomos?\s+regularizaci[oó]n',
     'regularizacion_reta', 'Regularización RETA'),

    (r'propuesta\s+de\s+liquidaci[oó]n|liquidaci[oó]n\s+provisional',
     'liquidacion_provisional', 'Liquidación Provisional'),

    (r'acta\s+de\s+inspecci[oó]n|acta\s+de\s+disconformidad',
     'acta_inspeccion', 'Acta de Inspección'),

    (r'expediente\s+sancionador|resoluci[oó]n\s+sancionadora|propuesta\s+de\s+sanci[oó]n',
     'expediente_sancionador', 'Expediente Sancionador'),

    (r'denuncia|bolet[ií]n\s+de\s+denuncia',
     'denuncia', 'Denuncia / Sanción de Tráfico'),

    (r'requerimiento\s+de\s+informaci[oó]n|requerimiento\s+de\s+datos',
     'requerimiento_informacion', 'Requerimiento de Información'),

    (r'notificaci[oó]\s+d\'inici|notificaci[oó]n\s+de\s+inicio\s+de\s+expediente',
     'inicio_expediente', 'Inicio de Expediente'),

    (r'certificado\s+de\s+deuda|certificaci[oó]n\s+de\s+deuda',
     'certificado_deuda', 'Certificado de Deuda'),

    (r'certificado\s+de\s+estar\s+al\s+corriente|certificado\s+de\s+no\s+deuda',
     'certificado_no_deuda', 'Certificado al Corriente de Pagos'),

    (r'notificaci[oó][n|ó]\s+electr[oó]nica',
     'notificacion_electronica', 'Notificación Electrónica'),

    (r'comunicaci[oó]n\s+de\s+alta|alta\s+en\s+el\s+r[eé]gimen',
     'alta_regimen', 'Comunicación de Alta'),

    (r'comunicaci[oó]n\s+de\s+baja',
     'baja_regimen', 'Comunicación de Baja'),
]


# ─── Campos de extracción pre-populados por tipo de documento ───────────────────
# Formato idéntico al de los archivos JSON de templates (tgss_base.json, etc.)
# Cada tipo tiene sus campos específicos + los campos básicos siempre presentes.

_CAMPOS_BASICOS = {
    "nif": {
        "tipo": "nif",
        "patrones": [
            "NIF[/\\s]*CIF[:\\s]+([A-Z0-9]{8,10})",
            "NIF[:\\s]+([A-Z0-9]{8,10})",
            "CIF[:\\s]+([A-Z0-9]{8,10})",
            "([A-Z]\\d{7}[A-Z0-9])"
        ]
    },
    "fecha": {
        "tipo": "fecha",
        "patrones": [
            "[Ff]echa[:\\s]+(\\d{1,2}[/\\-]\\d{1,2}[/\\-]\\d{2,4})",
            "[Dd]ata[:\\s]+(\\d{1,2}[/\\-]\\d{1,2}[/\\-]\\d{2,4})",
            "(\\d{1,2}\\s+de\\s+\\w+\\s+de\\s+\\d{4})"
        ]
    },
    "referencia": {
        "tipo": "texto",
        "patrones": [
            "[Rr]ef(?:erencia)?[:\\s]+([A-Z0-9/\\-]{5,30})",
            "[Rr]ef(?:erència)?[:\\s]+([A-Z0-9/\\-]{5,30})",
            "Expedient(?:e)?[:\\s]+([A-Z0-9/\\-]{5,30})"
        ]
    },
}

CAMPOS_POR_TIPO = {
    "provisio_constrenyiment": {
        "deteccion": {
            "debe_contener": ["CONSTRENYIMENT"],
            "prioridad": 5
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe": {
                "tipo": "importe",
                "patrones": [
                    "[Ii]mport\\s+total[:\\s]+([\\d.,]+)",
                    "[Ii]mporte[:\\s]+([\\d.,]+)\\s*€?",
                    "([\\d.,]+)\\s*€\\b"
                ]
            },
            "organisme": {
                "tipo": "texto",
                "patrones": [
                    "Organisme[:\\s]+(.+?)(?:\\n|$)",
                    "Ajuntament[\\s]+de[\\s]+([A-Za-záéíóúàèòüñ\\s]+?)(?:\\n|,)"
                ]
            },
            "periode": {
                "tipo": "texto",
                "patrones": [
                    "[Pp]er[ií]ode?[:\\s]+([\\d/\\-\\s]+(?:trimestre|anual|mensual)?)",
                    "[Pp]erío[d]?o[:\\s]+([\\d/\\-\\s]+)"
                ]
            }
        }
    },

    "providencia_apremio": {
        "deteccion": {
            "debe_contener": ["PROVIDENCIA DE APREMIO"],
            "prioridad": 5
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe": {
                "tipo": "importe",
                "patrones": [
                    "[Ii]mporte\\s+(?:total\\s+)?(?:de\\s+)?(?:la\\s+)?deuda[:\\s]+([\\d.,]+)",
                    "[Ii]mporte[:\\s]+([\\d.,]+)\\s*€?"
                ]
            },
            "importe_recargo": {
                "tipo": "importe",
                "patrones": ["[Rr]ecargo[:\\s]+([\\d.,]+)"]
            },
            "periodo": {
                "tipo": "texto",
                "patrones": ["[Pp]er[ií]odo[:\\s]+([\\d/\\-\\s]+(?:trimestre|anual|mensual)?)"]
            },
            "providencia_numero": {
                "tipo": "texto",
                "patrones": ["(?:N[.º°]?\\s*)?[Pp]rovidencia[:\\s#]+([A-Z0-9/\\-]+)"]
            }
        }
    },

    "embargo_vehiculos": {
        "deteccion": {
            "debe_contener": ["EMBARGO", "VEHÍCULO"],
            "prioridad": 5
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe_total": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte\\s+total[:\\s]+([\\d.,]+)"]
            },
            "importe_principal": {
                "tipo": "importe",
                "patrones": ["[Pp]rincipal[:\\s]+([\\d.,]+)"]
            },
            "vehiculos": {
                "tipo": "texto",
                "patrones": ["[Mm]atrícula[:\\s]+([A-Z0-9\\-]+)", "([A-Z]{1,4}\\s*\\d{4}\\s*[A-Z]{0,3})"]
            },
            "num_expediente": {
                "tipo": "texto",
                "patrones": ["[Ee]xpediente[:\\s]+([A-Z0-9/\\-]+)"]
            }
        }
    },

    "embargo_cuentas": {
        "deteccion": {
            "debe_contener": ["EMBARGO", "CUENTAS"],
            "prioridad": 5
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe_embargado": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte\\s+a\\s+embargar[:\\s]+([\\d.,]+)", "[Ee]mbargado[:\\s]+([\\d.,]+)"]
            },
            "entidad_financiera": {
                "tipo": "texto",
                "patrones": ["[Ee]ntidad[:\\s]+(.+?)(?:\\n|IBAN|$)", "Banco[:\\s]+(.+?)(?:\\n|$)"]
            },
            "num_expediente": {
                "tipo": "texto",
                "patrones": ["[Ee]xpediente[:\\s]+([A-Z0-9/\\-]+)"]
            }
        }
    },

    "regularizacion_reta": {
        "deteccion": {
            "debe_contener": ["RETA"],
            "prioridad": 5
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte[:\\s]+([\\d.,]+)\\s*€?", "[Cc]uota[:\\s]+([\\d.,]+)"]
            },
            "regimen": {
                "tipo": "texto",
                "patrones": ["[Rr][eé]gimen[:\\s]+(.+?)(?:\\n|$)"]
            },
            "iban": {
                "tipo": "texto",
                "patrones": ["IBAN[:\\s]+([A-Z]{2}\\d{2}\\s*(?:\\d{4}\\s*){4,6})"]
            }
        }
    },

    "liquidacion_provisional": {
        "deteccion": {
            "debe_contener": ["LIQUIDACIÓN"],
            "prioridad": 4
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe_a_ingresar": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte\\s+a\\s+ingresar[:\\s]+([\\d.,]+)"]
            },
            "base_imponible": {
                "tipo": "importe",
                "patrones": ["[Bb]ase\\s+imponible[:\\s]+([\\d.,]+)"]
            }
        }
    },

    "expediente_sancionador": {
        "deteccion": {
            "debe_contener": ["SANCIONADOR", "SANCIÓN"],
            "prioridad": 4
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe_sancion": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte[:\\s]+(?:de\\s+la\\s+)?[Ss]anci[oó]n[:\\s]+([\\d.,]+)"]
            },
            "num_expediente": {
                "tipo": "texto",
                "patrones": ["[Ee]xpediente\\s+(?:sancionador)?[:\\s]+([A-Z0-9/\\-]+)"]
            }
        }
    },

    "requerimiento_informacion": {
        "deteccion": {
            "debe_contener": ["REQUERIMIENTO"],
            "prioridad": 4
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "plazo": {
                "tipo": "texto",
                "patrones": ["[Pp]lazo[:\\s]+(.+?)(?:\\n|días|$)", "(\\d+)\\s*d[ií]as?\\s+h[áa]biles?"]
            }
        }
    },

    "certificado_deuda": {
        "deteccion": {
            "debe_contener": ["CERTIFICADO", "DEUDA"],
            "prioridad": 4
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe_deuda": {
                "tipo": "importe",
                "patrones": ["[Ii]mporte\\s+(?:total\\s+de\\s+)?(?:la\\s+)?deuda[:\\s]+([\\d.,]+)"]
            }
        }
    },

    # Fallback genérico para tipos no clasificados específicamente
    "_generico": {
        "deteccion": {
            "debe_contener": [],
            "prioridad": 1
        },
        "campos": {
            **_CAMPOS_BASICOS,
            "importe": {
                "tipo": "importe",
                "patrones": [
                    "[Ii]mporte[:\\s]+([\\d.,]+)\\s*€?",
                    "TOTAL[:\\s]+([\\d.,]+)\\s*€?",
                    "([\\d.,]+)\\s*€\\b"
                ]
            }
        }
    }
}


def _slugify(text: str) -> str:
    """Convierte texto a slug seguro para usar como clave de BD."""
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_text = nfkd.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9]+', '_', ascii_text.lower()).strip('_')[:60]


def detectar_emisor(texto: str) -> tuple:
    """
    Detecta el emisor del documento.
    Returns: (codigo, nombre_display)
    """
    texto_lower = texto.lower()
    for patron, codigo, nombre in EMISORES:
        m = re.search(patron, texto_lower[:3000], re.IGNORECASE | re.MULTILINE)
        if m:
            if nombre is None:
                try:
                    nombre = m.group(1).strip().title()[:60]
                except Exception:
                    nombre = codigo
            return codigo, nombre
    return 'DESCONOCIDO', 'Administración Pública'


def detectar_tipo_documento(texto: str) -> tuple:
    """
    Detecta el tipo de documento.
    Returns: (tipo_clave, nombre_display)
    """
    for patron, clave, nombre in TIPOS_DOCUMENTO:
        m = re.search(patron, texto[:5000], re.IGNORECASE | re.MULTILINE)
        if m:
            return clave, nombre
    return 'notificacion_generica', 'Notificación Genérica'


def auto_crear_extraction_template(perfil_clave: str, tipo_clave: str, nombre: str,
                                   emisor_nombre: str) -> bool:
    """
    Crea o actualiza un ExtractionTemplate en la BD con los campos pre-populados
    para el tipo de documento detectado.

    El template usa el mismo formato JSON que tgss_base.json:
    { "id": ..., "nombre": ..., "deteccion": {...}, "campos": {...} }

    Returns: True si es nuevo, False si ya existía
    """
    try:
        from models import ExtractionTemplate

        # Obtener la definición de campos para este tipo
        campos_def = CAMPOS_POR_TIPO.get(tipo_clave, CAMPOS_POR_TIPO['_generico'])

        # Construir el JSON del template
        profile_json = {
            "id": perfil_clave,
            "nombre": nombre,
            "version": "1.0",
            "organismo": emisor_nombre,
            "idioma_principal": "ca" if any(c in tipo_clave for c in ['constrenyiment', 'provisio']) else "es",
            "origen": "auto_ocr",
            "deteccion": campos_def.get("deteccion", {"debe_contener": [], "prioridad": 3}),
            "campos": campos_def.get("campos", CAMPOS_POR_TIPO['_generico']['campos'])
        }

        existing = ExtractionTemplate.query.get(perfil_clave)
        if existing:
            logger.info(f"♻️ ExtractionTemplate ya existe: {perfil_clave}")
            return False

        template = ExtractionTemplate(
            id=perfil_clave,
            nombre=nombre,
            version="1.0",
            hereda_de=None,
            idioma_principal=profile_json["idioma_principal"],
            profile_json=profile_json,
            activo=True
        )
        db.session.add(template)
        db.session.commit()
        logger.info(f"✨ ExtractionTemplate creado: {perfil_clave} ({len(profile_json['campos'])} campos)")
        return True

    except Exception as e:
        logger.error(f"Error creando ExtractionTemplate {perfil_clave}: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def auto_crear_perfil(doc, gestoria_id: int, user_id: int = None) -> dict:
    """
    Dado un documento sin perfil, extrae su tipo y emisor del texto OCR,
    crea (o recupera) un ConfiguracionPerfil + un ExtractionTemplate en la BD.

    Returns:
        dict con 'perfil_clave', 'nombre', 'es_nuevo', 'icono', 'pendiente_destino'
    """
    texto = doc.texto_ocr or ''

    if not texto.strip():
        logger.warning(f"Documento {doc.id} sin texto OCR — no se puede auto-crear perfil")
        return {
            'perfil_clave': '_sin_ocr_',
            'nombre': 'Sin texto extraído',
            'es_nuevo': False,
            'pendiente_destino': False,
            'error': 'El documento no tiene texto OCR disponible'
        }

    # 1. Detectar emisor y tipo
    emisor_codigo, emisor_nombre = detectar_emisor(texto)
    tipo_clave, tipo_nombre = detectar_tipo_documento(texto)

    logger.info(f"Doc {doc.id}: emisor={emisor_nombre}, tipo={tipo_nombre}")

    # 2. Generar clave única
    perfil_clave = f"auto_{_slugify(emisor_codigo)}_{_slugify(tipo_clave)}"
    nombre_display = f"{tipo_nombre} — {emisor_nombre}"
    icono = _icono_para_tipo(tipo_clave)

    # 3. Buscar ExtractionTemplate global existente
    from models import ExtractionTemplate
    template_global = ExtractionTemplate.query.get(perfil_clave)
    
    # 4. Buscar ConfiguracionPerfil local existente
    config = ConfiguracionPerfil.query.filter_by(
        gestoria_id=gestoria_id,
        perfil_clave=perfil_clave
    ).first()

    es_nuevo_local = config is None
    es_nuevo_global = template_global is None

    # 4a. Crear ConfiguracionPerfil local si no existe
    if es_nuevo_local:
        config = ConfiguracionPerfil(
            gestoria_id=gestoria_id,
            perfil_clave=perfil_clave,
            activo=True,
            actualizado_por_id=user_id
        )
        try:
            config.nombre_display = nombre_display
        except Exception:
            pass
        db.session.add(config)
        db.session.commit()
        logger.info(f"✨ ConfiguracionPerfil local auto-creado: {perfil_clave}")
    else:
        logger.info(f"♻️ Perfil local ya existente: {perfil_clave}")

    # 4b. Crear ExtractionTemplate global si no existe (Compartido)
    if es_nuevo_global:
        auto_crear_extraction_template(perfil_clave, tipo_clave, nombre_display, emisor_nombre)
        logger.info(f"🌍 ExtractionTemplate global creado: {perfil_clave}")
    else:
        logger.info(f"🤝 Reutilizando ExtractionTemplate global existente: {perfil_clave}")

    pendiente_destino = not (config.categoria and config.departamento)

    return {
        'perfil_clave': perfil_clave,
        'nombre': nombre_display,
        'icono': icono,
        'emisor': emisor_nombre,
        'tipo': tipo_nombre,
        'es_nuevo': es_nuevo_local,
        'pendiente_destino': pendiente_destino,
        'categoria_actual': config.categoria,
        'departamento_actual': config.departamento,
    }


def _icono_para_tipo(tipo: str) -> str:
    ICONOS = {
        'providencia_apremio': '⚖️',
        'provisio_constrenyiment': '⚖️',
        'embargo_vehiculos': '🚗',
        'embargo_cuentas': '🏦',
        'embargo_creditos': '💳',
        'embargo_inmuebles': '🏠',
        'regularizacion_reta': '👔',
        'liquidacion_provisional': '📊',
        'acta_inspeccion': '🔍',
        'expediente_sancionador': '🚨',
        'denuncia': '🚔',
        'requerimiento_informacion': '📋',
        'inicio_expediente': '📂',
        'certificado_deuda': '📜',
        'certificado_no_deuda': '✅',
        'notificacion_electronica': '📬',
        'alta_regimen': '📝',
        'baja_regimen': '📝',
    }
    return ICONOS.get(tipo, '📄')
