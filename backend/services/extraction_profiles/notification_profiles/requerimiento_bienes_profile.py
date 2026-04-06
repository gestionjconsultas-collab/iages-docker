import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class RequerimientoBienesProfile(BaseNotificationProfile):
    """
    Perfil para: Requerimiento de Bienes (TVA-218)
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    Campos extraídos:
    - razon_social: Apellidos y nombre / Razón Social
    - nif: NIF/CIF del deudor
    - domicilio: Domicilio del deudor
    - localidad: Localidad del deudor
    - tipo_identificador: Tipo/Identificador (CCC/NAF)
    - regimen: Código de régimen
    - expediente: Nº de expediente
    - num_documento: Nº de documento
    - num_referencia: Nº de referencia
    - importe_principal: Principal de la deuda
    - importe_recargo: Recargo
    - importe_intereses: Intereses de demora
    - importe_costas: Costas devengadas
    - importe_total: Total Deuda
    - referencia_verificacion: Código de referencia de verificación
    - fecha: Fecha del documento
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return (
            'TVA-218' in texto or
            ('REQUERIMIENTO DE BIENES' in texto and 'SEGURIDAD SOCIAL' in texto)
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'REQUERIMIENTO DE BIENES (TVA-218)',
            'razon_social': '',
            'nif': '',
            'domicilio': '',
            'localidad': '',
            'tipo_identificador': '',
            'regimen': '',
            'expediente': '',
            'num_documento': '',
            'num_referencia': '',
            'importe_principal': 0.0,
            'importe_recargo': 0.0,
            'importe_intereses': 0.0,
            'importe_costas': 0.0,
            'importe_total': 0.0,
            'referencia_verificacion': '',
            'fecha': '',
            # Compatibilidad con sistema de mapping
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Requerimiento de Bienes (TVA-218)',
        }

        # ── 1. APELLIDOS Y NOMBRE / RAZÓN SOCIAL ─────────────────────────────
        m = re.search(
            r'Apellidos\s+y\s+nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|NIF|$)',
            texto_completo, re.IGNORECASE
        )
        if m:
            nombre_raw = re.sub(r'\s*[—–-]\s*', ' ', m.group(1).strip())
            datos['razon_social'] = re.sub(r'\s{2,}', ' ', nombre_raw).strip()

        # ── 2. NIF/CIF ────────────────────────────────────────────────────────
        m = re.search(r'NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # ── 3. DOMICILIO ──────────────────────────────────────────────────────
        m = re.search(r'^Domicilio[:\s]+(.+?)$', texto_completo, re.IGNORECASE | re.MULTILINE)
        if m:
            datos['domicilio'] = m.group(1).strip()

        # ── 4. LOCALIDAD ──────────────────────────────────────────────────────
        m = re.search(r'^Localidad[:\s]+(.+?)$', texto_completo, re.IGNORECASE | re.MULTILINE)
        if m:
            datos['localidad'] = m.group(1).strip()

        # ── 5. Nº DE REFERENCIA ───────────────────────────────────────────────
        m = re.search(r'N[ºo°]?\s*de\s*referencia[:\s]+(\d{10,20})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_referencia'] = m.group(1).strip()

        # ── 6. TIPO/IDENTIFICADOR y RÉGIMEN ──────────────────────────────────
        m = re.search(
            r'Tipo[/\s]*Ident[^:]*?[:\s]+(\d{2}\s+\d{12})\s+R[eé]gimen[:\s]+(\d+)',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['tipo_identificador'] = m.group(1).strip()
            datos['regimen'] = m.group(2).strip()
        else:
            m = re.search(r'Tipo[/\s]*Ident[^:]*?[:\s]+(\d{2}\s+\d{12})', texto_completo, re.IGNORECASE)
            if m:
                datos['tipo_identificador'] = m.group(1).strip()
            m = re.search(r'R[eé]gimen[:\s]+(\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['regimen'] = m.group(1).strip()

        # ── 7. Nº EXPEDIENTE ─────────────────────────────────────────────────
        m = re.search(r'Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()
            datos['referencia'] = datos['expediente']

        # ── 8. Nº DOCUMENTO ───────────────────────────────────────────────────
        m = re.search(r'Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_documento'] = m.group(1).strip()

        # ── 9. IMPORTES DESGLOSADOS (TABLA TVA-218) ──────────────────────────
        # Formato: Principal  Recargo  Intereses... Total Deuda
        #          5,73       1,15     0,04         6,92
        m = re.search(
            r'Principal\s+Recargo\s+Intereses.*?\n'
            r'\s*([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)',
            texto_completo, re.IGNORECASE | re.DOTALL
        )
        if m:
            datos['importe_principal'] = self._normalize_amount(m.group(1))
            datos['importe_recargo'] = self._normalize_amount(m.group(2))
            datos['importe_intereses'] = self._normalize_amount(m.group(3))
            datos['importe_costas'] = self._normalize_amount(m.group(4))
            datos['importe_total'] = self._normalize_amount(m.group(5))
            datos['importe'] = datos['importe_total']

        # ── 10. REFERENCIA DE VERIFICACIÓN (CSV) ─────────────────────────────
        m = re.search(
            r'C[oó]digo[:\s]+([A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,})',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['referencia_verificacion'] = m.group(1).strip()

        # ── 11. FECHA ─────────────────────────────────────────────────────────
        MESES = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        m = re.search(
            r'(?:a\s+)?(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
            texto_completo, re.IGNORECASE
        )
        if m:
            dia = m.group(1).zfill(2)
            mes = MESES.get(m.group(2).lower(), '??')
            datos['fecha'] = f"{dia}/{mes}/{m.group(3)}"
        else:
            m = re.search(r'Fecha[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1)

        # ── Concepto enriquecido ──────────────────────────────────────────────
        datos['concepto'] = (
            f"Requerimiento Bienes - {datos['razon_social']} - "
            f"Deuda: {datos['importe_total']}€"
        )

        return datos
