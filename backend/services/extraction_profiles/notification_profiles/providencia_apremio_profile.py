import re
from typing import Dict, Any
from .base_notification_profile import BaseNotificationProfile

class ProvidenciaApremioProfile(BaseNotificationProfile):
    """
    Perfil para: Providencia de Apremio (Tesorería General de la Seguridad Social)
    """

    def matches(self, texto_completo: str) -> bool:
        # Normalizar espacios y saltos de línea para la detección de frases
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return ('PROVIDENCIA DE APREMIO' in texto and 
                ('TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL' in texto or 'TGSS' in texto))

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'SEGURIDAD SOCIAL',
            'tipo_documento': 'PROVIDENCIA DE APREMIO',
            'providencia_numero': '',
            'referencia': '',
            'fecha': '',
            'importe': 0.0,
            'importe_principal': 0.0,
            'importe_recargo': 0.0,
            'nif': '',
            'nombre_razon_social': '',
            'concepto': '',
            'periodo': ''
        }

        # 1. Nº Providencia
        # Patrón estricto falla si hay texto intercalado (columnas). 
        # Buscamos el formato específico XX/XX/XXXXXXXXX que es muy característico
        m_prov = re.search(r'Providencia\s+de\s+Apremio.*?(\d{2}/\d{2}/\d{9})', texto_completo, re.DOTALL | re.IGNORECASE)
        if not m_prov:
             # Intento directo por formato si falla el contexto cercano
             m_prov = re.search(r'(?<!\d)(\d{2}/\d{2}/\d{9})(?!\d)', texto_completo)
        
        if m_prov:
            datos['providencia_numero'] = m_prov.group(1)
            datos['referencia'] = datos['providencia_numero']

        # 2. Fecha (Formato normalizado dd/mm/yyyy)
        # Puede haber texto entre "Fecha" y el valor debido a lectura de columnas
        # Usamos regex estricto para dia/mes para evitar confundir con Nº Providencia (ej: 08/25/...)
        m_fecha = re.search(r'Fecha.*?\b(\d{1,2}[-/](?:0[1-9]|1[0-2])[-/]\d{4})\b', texto_completo, re.DOTALL | re.IGNORECASE)
        if m_fecha:
            datos['fecha'] = m_fecha.group(1)

        # 3. Importes (Total, Principal, Recargo)
        # La estructura suele ser una tabla con cabeceras y debajo los valores
        # PRINCIPAL    RECARGO    INTERÉS...   TOTAL...
        # 5.454,81     1.090,96   0,00         6.545,77
        
        # Intentamos capturar la fila completa de valores
        # Buscamos la línea que tiene 4 o 5 importes numéricos juntos
        m_table = re.search(r'PRINCIPAL.*?TOTAL A INGRESAR\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)', texto_completo, re.DOTALL)
        
        if m_table:
            datos['importe_principal'] = self._normalize_amount(m_table.group(1))
            datos['importe_recargo'] = self._normalize_amount(m_table.group(2))
            # group(3) Intereses, group(4) Costas
            datos['importe'] = self._normalize_amount(m_table.group(5))
        else:
            # Fallback a búsqueda individual por etiqueta (menos fiable en columnas)
            m_total = re.search(r'TOTAL\s+A\s+INGRESAR\s.*?([\d.,]+)', texto_completo, re.DOTALL)
            if m_total: datos['importe'] = self._normalize_amount(m_total.group(1))
            
            m_principal = re.search(r'PRINCIPAL\s.*?([\d.,]+)', texto_completo, re.DOTALL)
            if m_principal: datos['importe_principal'] = self._normalize_amount(m_principal.group(1))

        # 4. Datos del Deudor
        m_nif = re.search(r'NIF/CIF.*?([A-HJ-NP-TV-Z]\d{7,8}[A-HJ-NP-TV-Z]?|[0-9]{8}[A-Z])', texto_completo, re.DOTALL | re.IGNORECASE)
        if m_nif:
            datos['nif'] = m_nif.group(1)
        
        # Nombre: Buscamos "Nombre o Razón Social" y cogemos la línea siguiente válida
        lines = texto_completo.split('\n')
        for i, line in enumerate(lines):
            if 'Nombre o Razón Social' in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1].strip()
                    if candidate and 'Unidad de Recaudación' not in candidate:
                        datos['nombre_razon_social'] = candidate
                        break

        # 5. Periodo
        m_periodo = re.search(r'(\d{2}/\d{4}\s*-\s*\d{2}/\d{4})', texto_completo)
        if m_periodo:
            datos['periodo'] = m_periodo.group(1)

        # 6. Concepto / Referencia Pago
        m_ref_pago = re.search(r'(?:N[º°]\s+de\s+referencia|Ref)[:\.\s]*(\d+)', texto_completo, re.IGNORECASE)
        ref_pago = m_ref_pago.group(1) if m_ref_pago else ""
        
        datos['concepto'] = f"Providencia {datos['providencia_numero']}"
        if ref_pago:
            datos['concepto'] += f" Ref:{ref_pago}"

        return datos
