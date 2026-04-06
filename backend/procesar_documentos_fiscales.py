# backend/procesar_documentos_fiscales.py
"""
Procesador de Documentos Fiscales con IA Asistida
Detecta tipo, extrae metadatos, clasifica y sugiere al usuario
"""

import os
import re
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Tuple, Optional
import google.generativeai as genai
from services.notificacion_extractor import NotificacionExtractor
from models_fiscal import (
    DocumentoFiscal, 
    TipoDocumentoFiscal, 
    ClasificacionFiscal,
    calcular_fecha_limite_modelo_303,
    calcular_fecha_limite_modelo_200
)
from extensions import db

# Configurar Gemini con sistema multi-key
# La configuración real se hace en cada llamada usando gemini_utils

# ============================================================================
# DETECCIÓN DE TIPO DE DOCUMENTO
# ============================================================================

def detectar_tipo_documento(texto: str) -> str:
    """
    Detecta el tipo de documento fiscal por palabras clave y número de modelo
    
    Args:
        texto: Texto extraído del PDF
        
    Returns:
        Tipo de documento (enum TipoDocumentoFiscal)
    """
    import re
    texto_upper = texto.upper()
    
    # Buscar número de modelo con regex (más preciso)
    modelo_match = re.search(r'MODELO\s+(\d{3})', texto_upper)
    if modelo_match:
        numero_modelo = modelo_match.group(1)
        
        # Mapeo directo de números de modelo
        modelos_map = {
            '303': 'MODELO_303',  # IVA
            '200': 'MODELO_200',  # Impuesto Sociedades (Consolidado)
            '202': 'MODELO_202',  # Impuesto Sociedades (Pagos Fraccionados)
            '130': 'MODELO_130',  # IRPF Pagos Fraccionados
            '180': 'MODELO_180',  # Retenciones Alquileres Anual
            '190': 'MODELO_190',  # Resumen anual retenciones
            '111': 'MODELO_111',  # Retenciones trimestrales
            '115': 'MODELO_115',  # Retenciones alquileres
            '347': 'MODELO_347',  # Operaciones con terceros
        }
        
        if numero_modelo in modelos_map:
            return modelos_map[numero_modelo]
    
    # Fallback: detección por palabras clave (si no se encuentra número)
    
    # Modelo 303 - IVA
    if any(keyword in texto_upper for keyword in [
        'AUTOLIQUIDACIÓN PERIÓDICA',
        'IMPUESTO SOBRE EL VALOR AÑADIDO',
        'IVA - AUTOLIQUIDACIÓN'
    ]):
        return 'MODELO_303'
    
    # Modelo 200 - Impuesto Sociedades
    if any(keyword in texto_upper for keyword in [
        'IMPUESTO SOBRE SOCIEDADES',
        'DECLARACIÓN DEL IMPUESTO SOBRE SOCIEDADES'
    ]):
        return 'MODELO_200'
    
    # Modelo 190 - Retenciones anuales
    if any(keyword in texto_upper for keyword in [
        'RESUMEN ANUAL DE RETENCIONES',
        'RETENCIONES E INGRESOS A CUENTA'
    ]):
        return 'MODELO_190'
    
    # Certificado de Retenciones
    if any(keyword in texto_upper for keyword in [
        'CERTIFICADO DE RETENCIONES',
        'CERTIFICADO RETENCIONES IRPF',
        'RENDIMIENTOS DEL TRABAJO'
    ]):
        return 'CERTIFICADO_RETENCIONES'
    
    # Aplazamiento - Solicitud
    if 'APLAZAMIENTO' in texto_upper and 'SOLICITUD' in texto_upper:
        return 'APLAZAMIENTO_SOLICITUD'
    
    # Aplazamiento - Concesión
    if 'APLAZAMIENTO' in texto_upper and any(keyword in texto_upper for keyword in ['CONCESIÓN', 'CONCEDIDO', 'APROBADO']):
        return 'APLAZAMIENTO_CONCESION'
    
    return 'OTRO'


# ============================================================================
# EXTRACCIÓN DE METADATOS CON GEMINI
# ============================================================================

async def extraer_metadatos_gemini(texto: str, tipo_documento: str) -> Dict:
    """
    Extrae metadatos específicos del documento usando Gemini AI
    
    Args:
        texto: Texto del PDF
        tipo_documento: Tipo detectado
        
    Returns:
        Diccionario con metadatos extraídos
    """
    
    # Prompts específicos por tipo de documento
    prompts = {
        'MODELO_303': """
Analiza este documento Modelo 303 (IVA) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF de la empresa",
    "ejercicio": año fiscal (número),
    "periodo": "T1", "T2", "T3" o "T4",
    "resultado_autoliquidacion": importe de la casilla 71 (número, puede ser negativo),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

IMPORTANTE:
- El resultado de la autoliquidación (casilla 71) puede ser:
  * POSITIVO: A ingresar (requiere pago)
  * NEGATIVO: A devolver (informativo)
  * CERO: Sin actividad (informativo)

Texto del documento:
{texto}
""",
        
        'MODELO_200': """
Analiza este documento Modelo 200 (Impuesto Sociedades) y extrae en formato JSON:

{
    "nif": "NIF de la empresa",
    "ejercicio": año fiscal (número),
    "base_imponible": importe (número),
    "cuota_liquida": importe de la cuota líquida (número),
    "tipo_gravamen": porcentaje (número),
    "numero_justificante": "número de justificante",
    "fecha_presentacion": "YYYY-MM-DD"
}

IMPORTANTE:
- Si cuota_liquida > 0: Requiere pago
- Si cuota_liquida <= 0: Informativo

Texto del documento:
{texto}
""",
        
        'MODELO_190': """
Analiza este Modelo 190 (Retenciones) y extrae en formato JSON:

{
    "nif": "NIF del retenedor",
    "ejercicio": año fiscal (número),
    "total_retenciones": importe total (número),
    "numero_perceptores": cantidad de perceptores (número),
    "numero_justificante": "número de justificante"
}

Texto del documento:
{texto}
""",
        
        'MODELO_180': """
Analiza este Modelo 180 (Retenciones Alquileres Anual) y extrae en formato JSON:

{
    "nif": "NIF del retenedor",
    "ejercicio": año fiscal (número),
    "total_retenciones": importe total (número),
    "numero_perceptores": cantidad de perceptores (número),
    "numero_justificante": "número de justificante"
}

Texto del documento:
{texto}
""",
        
        'MODELO_111': """
Analiza este documento Modelo 111 (Retenciones Trimestrales) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF de la empresa",
    "ejercicio": año fiscal (número),
    "periodo": "T1", "T2", "T3" o "T4",
    "numero_perceptores": cantidad de perceptores (número),
    "importe_retenciones": importe total de retenciones (número),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

Texto del documento:
{texto}
""",
        
        'MODELO_115': """
Analiza este documento Modelo 115 (Retenciones Alquileres) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF de la empresa",
    "ejercicio": año fiscal (número),
    "periodo": "T1", "T2", "T3" o "T4",
    "numero_perceptores": cantidad de perceptores (número),
    "importe_retenciones": importe total de retenciones (número),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

Texto del documento:
{texto}
""",
        
        'MODELO_347': """
Analiza este documento Modelo 347 (Operaciones con Terceros) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF de la empresa declarante",
    "ejercicio": año fiscal (número),
    "numero_operaciones": cantidad de operaciones declaradas (número),
    "importe_total_operaciones": importe total de operaciones (número),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

IMPORTANTE:
- El Modelo 347 es una declaración anual informativa
- Declara operaciones con terceros superiores a 3.005,06€

Texto del documento:
{texto}
""",
        
        'MODELO_130': """
Analiza este documento Modelo 130 (IRPF - Pagos Fraccionados) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF del declarante",
    "ejercicio": año fiscal (número),
    "periodo": "T1", "T2", "T3" o "T4",
    "resultado_autoliquidacion": importe a ingresar o devolver (número),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

IMPORTANTE:
- El Modelo 130 es para autónomos en estimación directa
- Pagos fraccionados trimestrales del IRPF

Texto del documento:
{texto}
""",
        
        'MODELO_202': """
Analiza este documento Modelo 202 (Impuesto Sociedades - Pagos Fraccionados) y extrae la siguiente información en formato JSON:

{
    "nif": "NIF de la sociedad",
    "ejercicio": año fiscal (número),
    "periodo": "1P", "2P" o "3P" (primer, segundo o tercer pago fraccionado),
    "resultado_autoliquidacion": importe a ingresar (número),
    "numero_justificante": "número de 13 dígitos",
    "fecha_presentacion": "YYYY-MM-DD"
}

IMPORTANTE:
- El Modelo 202 son pagos fraccionados del Impuesto de Sociedades
- Se presenta 3 veces al año (abril, octubre, diciembre)

Texto del documento:
{texto}
""",
        
        'CERTIFICADO_RETENCIONES': """
Analiza este Certificado de Retenciones y extrae en formato JSON:

{
    "nif_perceptor": "NIF del perceptor",
    "nif_pagador": "NIF del pagador",
    "ejercicio": año fiscal (número),
    "retenciones_practicadas": importe total retenido (número),
    "rendimientos_trabajo": importe de rendimientos (número)
}

Texto del documento:
{texto}
""",
        
        'APLAZAMIENTO_SOLICITUD': """
Analiza esta Solicitud de Aplazamiento y extrae en formato JSON:

{
    "nif": "NIF del solicitante",
    "importe_deuda": importe total de la deuda (número),
    "num_plazos_solicitados": número de plazos (número),
    "fecha_solicitud": "YYYY-MM-DD"
}

Texto del documento:
{texto}
""",
        
        'APLAZAMIENTO_CONCESION': """
Analiza esta Concesión de Aplazamiento y extrae en formato JSON:

{
    "nif": "NIF del beneficiario",
    "importe_deuda": importe total (número),
    "num_plazos": número de plazos concedidos (número),
    "vencimientos": [
        {"fecha": "YYYY-MM-DD", "importe": número},
        {"fecha": "YYYY-MM-DD", "importe": número}
    ]
}

Texto del documento:
{texto}
"""
    }
    
    prompt = prompts.get(tipo_documento)
    if not prompt:
        return {}
    
    # Limitar texto para no exceder límites de API
    texto_limitado = texto[:8000]
    
    try:
        from gemini_utils import obtener_gemini_con_fallback
        
        # Usar sistema multi-key fallback
        response, key_usada = obtener_gemini_con_fallback(
            prompt=prompt.format(texto=texto_limitado),
            modelo='gemini-2.5-flash'
        )
        
        print(f"✅ Metadatos extraídos con API Key #{key_usada}")
        
        # Parsear respuesta JSON
        import json
        import re
        # Limpiar respuesta (quitar markdown si existe)
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        # Limpiar saltos de línea problemáticos en el JSON
        response_text = re.sub(r'\{\s+"', '{"', response_text)
        response_text = response_text.strip()
        
        metadatos = json.loads(response_text)
        
        # Asegurar que ejercicio tenga un valor (usar año actual si falta)
        if 'ejercicio' not in metadatos or metadatos['ejercicio'] is None:
            from datetime import datetime
            metadatos['ejercicio'] = datetime.now().year
        
        return metadatos
        
    except Exception as e:
        print(f"Error extrayendo metadatos con Gemini: {e}")
        print(f"Respuesta de Gemini: {response.text if 'response' in locals() else 'No response'}")
        # Retornar metadatos mínimos con año actual
        from datetime import datetime
        return {'ejercicio': datetime.now().year}


# ============================================================================
# CLASIFICACIÓN PAGO/INFORMATIVO
# ============================================================================

def clasificar_documento(tipo_documento: str, metadatos: Dict) -> Tuple[str, float]:
    """
    Clasifica el documento como PAGO_REQUERIDO o INFORMATIVO
    
    Args:
        tipo_documento: Tipo del documento
        metadatos: Metadatos extraídos
        
    Returns:
        Tupla (clasificacion, confianza)
        - clasificacion: ClasificacionFiscal
        - confianza: 0.0 - 1.0
    """
    
    # Certificados: siempre informativos
    if tipo_documento == 'CERTIFICADO_RETENCIONES':
        return 'INFORMATIVO', 1.0
    
    # Modelo 190, 180: siempre informativos
    if tipo_documento in ['MODELO_190', 'MODELO_180']:
        return 'INFORMATIVO', 1.0
    
    # Aplazamientos: siempre requieren pago
    if tipo_documento in ['APLAZAMIENTO_SOLICITUD', 'APLAZAMIENTO_CONCESION']:
        return 'PAGO_REQUERIDO', 1.0
    
    # Modelo 303: según resultado
    if tipo_documento == 'MODELO_303':
        resultado = metadatos.get('resultado_autoliquidacion', 0)
        try:
            resultado = float(resultado)
        except (ValueError, TypeError):
            return 'INFORMATIVO', 0.5  # Baja confianza si no se puede determinar
        
        if resultado > 0:
            return 'PAGO_REQUERIDO', 0.95
        elif resultado < 0:
            return 'INFORMATIVO_DEVOLUCION', 0.95
        else:
            return 'INFORMATIVO_SIN_ACTIVIDAD', 0.9
    
    # Modelo 200: según cuota líquida
    if tipo_documento == 'MODELO_200':
        cuota = metadatos.get('cuota_liquida', 0)
        try:
            cuota = float(cuota)
        except (ValueError, TypeError):
            return 'INFORMATIVO', 0.5
        
        if cuota > 0:
            return 'PAGO_REQUERIDO', 0.95
        else:
            return 'INFORMATIVO', 0.9
    
    # Por defecto: informativo con baja confianza
    return 'INFORMATIVO', 0.5


# ============================================================================
# CÁLCULO DE FECHA LÍMITE
# ============================================================================

def calcular_fecha_limite(tipo_documento: str, metadatos: Dict) -> Optional[date]:
    """
    Calcula la fecha límite de pago/presentación
    
    Args:
        tipo_documento: Tipo del documento
        metadatos: Metadatos extraídos
        
    Returns:
        Fecha límite o None
    """
    
    ejercicio = metadatos.get('ejercicio')
    if not ejercicio:
        return None
    
    try:
        ejercicio = int(ejercicio)
    except (ValueError, TypeError):
        return None
    
    # Modelo 303
    if tipo_documento == 'MODELO_303':
        periodo = metadatos.get('periodo', '').upper()
        return calcular_fecha_limite_modelo_303(ejercicio, periodo)
    
    # Modelo 200
    if tipo_documento == 'MODELO_200':
        return calcular_fecha_limite_modelo_200(ejercicio)
    
    # Aplazamientos: usar primer vencimiento
    if tipo_documento == 'APLAZAMIENTO_CONCESION':
        vencimientos = metadatos.get('vencimientos', [])
        if vencimientos and len(vencimientos) > 0:
            primer_vencimiento = vencimientos[0].get('fecha')
            if primer_vencimiento:
                try:
                    return datetime.strptime(primer_vencimiento, '%Y-%m-%d').date()
                except ValueError:
                    pass
    
    return None


# ============================================================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ============================================================================

async def procesar_documento_fiscal(pdf_path: str, empresa_id: int) -> Dict:
    """
    Procesa un documento fiscal completo con IA
    Retorna sugerencias para confirmación del usuario
    
    Args:
        pdf_path: Ruta al archivo PDF
        empresa_id: ID de la empresa
        
    Returns:
        Diccionario con documento_id y sugerencias
    """
    
    # 1. Extraer texto del PDF
    extractor = NotificacionExtractor()
    texto = extractor.extract_text_from_pdf(pdf_path)
    
    # 2. Detectar tipo de documento
    # PRIMERO: Intentar desde el nombre del archivo (más confiable)
    # Formato: XXX_PERIODO_AÑO_EMPRESA.PDF (ej: 111_2T_2025_SHEHRAN EXPRESS SL.PDF)
    import os
    import re
    filename = os.path.basename(pdf_path)
    tipo = None
    
    # Buscar patrón: 3 dígitos al inicio del nombre
    filename_match = re.match(r'^(\d{3})_', filename)
    if filename_match:
        numero_modelo = filename_match.group(1)
        modelos_map = {
            '303': 'MODELO_303',
            '200': 'MODELO_200',
            '180': 'MODELO_180',
            '190': 'MODELO_190',
            '111': 'MODELO_111',
            '115': 'MODELO_115',
        }
        tipo = modelos_map.get(numero_modelo)
        print(f"📄 Modelo detectado desde filename: {numero_modelo} → {tipo}")
    
    # SEGUNDO: Si no se detectó desde filename, usar OCR
    if not tipo:
        tipo = detectar_tipo_documento(texto)
        print(f"📄 Modelo detectado desde OCR: {tipo}")
    
    # 3. Extraer metadatos con Gemini
    metadatos = await extraer_metadatos_gemini(texto, tipo)
    
    # 4. Clasificar (pago/informativo)
    clasificacion, confianza = clasificar_documento(tipo, metadatos)
    
    # 5. Calcular fecha límite si aplica
    fecha_limite = None
    importe_pago = None
    
    if clasificacion == 'PAGO_REQUERIDO':
        fecha_limite = calcular_fecha_limite(tipo, metadatos)
        
        # Extraer importe según tipo
        if tipo == 'MODELO_303':
            importe_pago = metadatos.get('resultado_autoliquidacion')
        elif tipo == 'MODELO_200':
            importe_pago = metadatos.get('cuota_liquida')
        elif tipo in ['APLAZAMIENTO_SOLICITUD', 'APLAZAMIENTO_CONCESION']:
            importe_pago = metadatos.get('importe_deuda')
    
    # 6. Guardar en BD con estado PENDIENTE_REVISION
    documento = DocumentoFiscal(
        empresa_id=empresa_id,
        tipo_documento=tipo,
        ejercicio_fiscal=metadatos.get('ejercicio'),
        periodo=metadatos.get('periodo'),
        nif=metadatos.get('nif'),
        numero_justificante=metadatos.get('numero_justificante'),
        fecha_presentacion=metadatos.get('fecha_presentacion'),
        clasificacion_sugerida=clasificacion,
        confianza_ia=confianza,
        metadatos=metadatos,
        importe_pago=importe_pago,
        fecha_limite_pago=fecha_limite,
        estado='PENDIENTE_REVISION',
        archivo_pdf_path=pdf_path,
        procesado_por_ia_at=datetime.now(timezone.utc)
    )
    
    db.session.add(documento)
    db.session.commit()
    
    return {
        "documento_id": documento.id,
        "sugerencias": {
            "tipo": tipo,
            "clasificacion": clasificacion,
            "confianza": confianza,
            "metadatos": metadatos,
            "importe_pago": importe_pago,
            "fecha_limite": fecha_limite.isoformat() if fecha_limite else None
        },
        "requiere_confirmacion": True
    }
