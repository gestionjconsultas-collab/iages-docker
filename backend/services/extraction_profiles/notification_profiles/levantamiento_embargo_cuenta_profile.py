import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class LevantamientoEmbargoCuentaProfile(BaseNotificationProfile):
    """
    Perfil para: Notificación al Deudor de Levantamiento Parcial de Embargo
    de Cuenta Bancaria (TVA-350)
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    Campos extraídos:
    - nif: NIF/CIF del deudor
    - razon_social: Apellidos y nombre / Razón Social
    - domicilio: Domicilio del deudor
    - localidad: Localidad del deudor
    - tipo_identificador: Tipo/Identificador (CCC/NAF)
    - regimen: Código de régimen
    - expediente: Nº de expediente
    - num_documento: Nº de documento
    - importe_deuda_pendiente: Importe deuda pendiente (tras el levantamiento)
    - cuentas: Lista de cuentas con importe trabado, a levantar y final embargado
    - csv: Código de referencia de verificación
    - fecha: Fecha del documento
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        # Excluir TVA-313 (Embargo Cuentas) que también menciona embargo+cuenta
        if 'TVA-313' in texto:
            return False
        return (
            'TVA-350' in texto or
            ('LEVANTAMIENTO' in texto and 'EMBARGO' in texto and 'CUENTA' in texto and 'SEGURIDAD SOCIAL' in texto)
        )


    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'LEVANTAMIENTO EMBARGO CUENTA BANCARIA (TVA-350)',
            'nif': '',
            'razon_social': '',
            'domicilio': '',
            'localidad': '',
            'tipo_identificador': '',
            'regimen': '',
            'expediente': '',
            'num_documento': '',
            'importe_deuda_pendiente': 0.0,
            'cuentas': [],
            'referencia_verificacion': '',
            'fecha': '',
            # Compatibilidad con sistema de mapping
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Levantamiento Embargo Cuenta Bancaria (TVA-350)',
        }

        # ── 1. NIF/CIF ────────────────────────────────────────────────────────
        m = re.search(r'NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # ── 2. APELLIDOS Y NOMBRE / RAZÓN SOCIAL ─────────────────────────────
        # Formato cabecera: "Apellidos y nombre/R.Social: MOHAMMAD — RIAZ"
        m = re.search(
            r'Apellidos\s+y\s+nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|Tipo|$)',
            texto_completo, re.IGNORECASE
        )
        if m:
            nombre_raw = m.group(1).strip()
            nombre_raw = re.sub(r'\s*[—–-]\s*', ' ', nombre_raw)
            datos['razon_social'] = re.sub(r'\s{2,}', ' ', nombre_raw).strip()
        else:
            # Fallback: buscar "DEUDOR:" en el cuerpo del documento
            m = re.search(r'DEUDOR[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
            if m:
                nombre_raw = m.group(1).strip()
                nombre_raw = re.sub(r'\s*[—–-]\s*', ' ', nombre_raw)
                datos['razon_social'] = re.sub(r'\s{2,}', ' ', nombre_raw).strip()

        # ── 3. DOMICILIO ──────────────────────────────────────────────────────
        m = re.search(r'Domicilio[:\s]+(.+?)(?:\n|Localidad|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['domicilio'] = m.group(1).strip()
        else:
            m = re.search(r'DOMICILIO[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
            if m:
                datos['domicilio'] = m.group(1).strip()

        # ── 4. LOCALIDAD ──────────────────────────────────────────────────────
        m = re.search(r'Localidad[:\s]+(.+?)(?:\n|Importe|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['localidad'] = m.group(1).strip()
        else:
            m = re.search(r'LOCALIDAD[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
            if m:
                datos['localidad'] = m.group(1).strip()

        # ── 5. TIPO/IDENTIFICADOR y RÉGIMEN ──────────────────────────────────
        # Formato: "Tipo/Ident.: 10 08218441804  Régimen: 0111"
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

        # ── 6. Nº EXPEDIENTE ─────────────────────────────────────────────────
        # Formato: "08 15 25 01008144"
        m = re.search(r'N[ºo°]?\s*Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()
            datos['referencia'] = datos['expediente']

        # ── 7. Nº DOCUMENTO ───────────────────────────────────────────────────
        # Formato: "08 15 350 26 007788970"
        m = re.search(r'N[ºo°]?\s*Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_documento'] = m.group(1).strip()

        # ── 8. IMPORTE DEUDA PENDIENTE ────────────────────────────────────────
        m = re.search(r'Importe\s+deuda\s+pendiente[:\s]+([\d.,]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['importe_deuda_pendiente'] = self._normalize_amount(m.group(1))
            datos['importe'] = datos['importe_deuda_pendiente']

        # ── 9. CUENTAS EMBARGADAS (tabla) ─────────────────────────────────────
        # Formato real:
        # Número de cuenta embargada    Importe trabado    Importe a levantar    Importe final embargado a transferir
        # ES07 2100 0817 4601 0606 6035  242,66             241,64                1,02
        # TOTAL                          242,66             241,64                1,02

        # Buscar la sección de la tabla de cuentas
        tabla_match = re.search(
            r'N[uú]mero\s+de\s+cuenta\s+embargada.*?'
            r'Importe\s+trabado.*?'
            r'Importe\s+a\s+levantar.*?'
            r'Importe\s+final.*?\n'
            r'(.*?)(?:TOTAL|Y\s+para|$)',
            texto_completo, re.DOTALL | re.IGNORECASE
        )

        if tabla_match:
            texto_tabla = tabla_match.group(1)
            # Patrón para cada fila: IBAN + 3 importes
            patron_fila = re.compile(
                r'(ES\d{2}[\s\d]{15,25})\s+'   # IBAN
                r'([\d.,]+)\s+'                  # Importe trabado
                r'([\d.,]+)\s+'                  # Importe a levantar
                r'([\d.,]+)',                     # Importe final embargado
                re.IGNORECASE
            )
            for m in patron_fila.finditer(texto_tabla):
                iban = re.sub(r'\s+', ' ', m.group(1).strip())
                datos['cuentas'].append({
                    'iban': iban,
                    'importe_trabado': self._normalize_amount(m.group(2)),
                    'importe_a_levantar': self._normalize_amount(m.group(3)),
                    'importe_final_embargado': self._normalize_amount(m.group(4)),
                })

        # Fallback: buscar IBAN directamente si no se encontró la tabla
        if not datos['cuentas']:
            patron_iban = re.compile(r'(ES\d{2}(?:\s+\d{4}){5})', re.IGNORECASE)
            for m in patron_iban.finditer(texto_completo):
                iban = re.sub(r'\s+', ' ', m.group(1).strip())
                datos['cuentas'].append({'iban': iban, 'importe_trabado': 0.0, 'importe_a_levantar': 0.0, 'importe_final_embargado': 0.0})

        # ── 10. CSV ───────────────────────────────────────────────────────────
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
        n_cuentas = len(datos['cuentas'])
        ibans = ', '.join(c['iban'] for c in datos['cuentas'])
        datos['concepto'] = (
            f"Levantamiento Embargo - {datos['razon_social']} - "
            f"Deuda pendiente: {datos['importe_deuda_pendiente']}€"
            f"{' - ' + ibans if ibans else ''}"
        )

        return datos
