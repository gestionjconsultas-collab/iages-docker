import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class EmbargoCuentasProfile(BaseNotificationProfile):
    """
    Perfil para: Notificación de la Diligencia de Embargo de Cuentas
    Corrientes y de Ahorro (TVA-313)
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
    - cuentas: Lista de cuentas embargadas con IBAN, importe e incidencias
    - importe_principal: Principal de la deuda
    - importe_recargo: Recargo
    - importe_intereses: Intereses
    - importe_costas: Costas
    - importe_total_embargar: Importe total a embargar
    - importe_embargado: Importe efectivamente embargado
    - referencia_verificacion: Código de referencia de verificación
    - fecha: Fecha del documento
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return (
            'TVA-313' in texto or
            ('EMBARGO DE CUENTAS CORRIENTES' in texto and 'SEGURIDAD SOCIAL' in texto) or
            ('EMBARGO' in texto and 'CUENTAS CORRIENTES' in texto and 'AHORRO' in texto and 'SEGURIDAD SOCIAL' in texto)
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'EMBARGO DE CUENTAS CORRIENTES Y DE AHORRO (TVA-313)',
            'razon_social': '',
            'nif': '',
            'domicilio': '',
            'localidad': '',
            'tipo_identificador': '',
            'regimen': '',
            'expediente': '',
            'num_documento': '',
            'cuentas': [],
            'importe_principal': 0.0,
            'importe_recargo': 0.0,
            'importe_intereses': 0.0,
            'importe_costas': 0.0,
            'importe_total_embargar': 0.0,
            'importe_embargado': 0.0,
            'referencia_verificacion': '',
            'fecha': '',
            # Compatibilidad con sistema de mapping
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Embargo de Cuentas Corrientes y de Ahorro (TVA-313)',
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

        # ── 5. TIPO/IDENTIFICADOR y RÉGIMEN ──────────────────────────────────
        m = re.search(
            r'Tipo[/\s]*Identificador[:\s]+(\d{2}\s+\d{12})\s+R[eé]gimen[:\s]+(\d+)',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['tipo_identificador'] = m.group(1).strip()
            datos['regimen'] = m.group(2).strip()
        else:
            m = re.search(r'Tipo[/\s]*Identificador[:\s]+(\d{2}\s+\d{12})', texto_completo, re.IGNORECASE)
            if m:
                datos['tipo_identificador'] = m.group(1).strip()
            m = re.search(r'R[eé]gimen[:\s]+(\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['regimen'] = m.group(1).strip()

        # ── 6. Nº EXPEDIENTE ─────────────────────────────────────────────────
        # Formato: "08 13 25 01659995"
        m = re.search(r'N[uú]mero\s+Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if not m:
            m = re.search(r'N[ºo°]?\s*Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()
            datos['referencia'] = datos['expediente']

        # ── 7. Nº DOCUMENTO ───────────────────────────────────────────────────
        # Formato: "08 13 313 26 065518075"
        m = re.search(r'N[ºo°]?\s*Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_documento'] = m.group(1).strip()

        # ── 8. CUENTAS EMBARGADAS ─────────────────────────────────────────────
        # Formato de la tabla:
        # Número de cuenta          Importe    Incidencias
        # ES72 2100 3109 6422 0031 8481  14,58
        #
        # Buscar la sección de cuentas declaradas embargadas
        tabla_match = re.search(
            r'(?:DETALLE\s+DE\s+LAS\s+CUENTAS|N[uú]mero\s+de\s+cuenta).*?'
            r'Importe.*?\n'
            r'(.*?)(?:\n\s*\n|\nPrincipal|\nTranscurridos|\Z)',
            texto_completo, re.DOTALL | re.IGNORECASE
        )

        if tabla_match:
            texto_tabla = tabla_match.group(1)
            # Patrón: IBAN + importe (+ incidencias opcionales)
            patron_fila = re.compile(
                r'(ES\d{2}(?:\s+\d{4}){5})\s+'  # IBAN (formato ES + 22 dígitos en grupos)
                r'([\d.,]+)'                       # Importe
                r'(?:\s+(.+?))?$',                 # Incidencias (opcional)
                re.MULTILINE | re.IGNORECASE
            )
            for m in patron_fila.finditer(texto_tabla):
                iban = re.sub(r'\s+', ' ', m.group(1).strip())
                incidencias = m.group(3).strip() if m.group(3) else ''
                datos['cuentas'].append({
                    'iban': iban,
                    'importe': self._normalize_amount(m.group(2)),
                    'incidencias': incidencias,
                })

        # Fallback: buscar IBANs directamente
        if not datos['cuentas']:
            for m in re.finditer(r'(ES\d{2}(?:\s+\d{4}){5})\s+([\d.,]+)', texto_completo):
                iban = re.sub(r'\s+', ' ', m.group(1).strip())
                datos['cuentas'].append({
                    'iban': iban,
                    'importe': self._normalize_amount(m.group(2)),
                    'incidencias': '',
                })

        # ── 9. IMPORTES DESGLOSADOS ───────────────────────────────────────────
        # Formato: "Principal  Recargo  Intereses  Costas  Importe total a embargar  Importe embargado"
        #          "576,54     115,32   5,12       0,00    696,98                    14,58"
        m = re.search(
            r'Principal\s+Recargo\s+Intereses\s+Costas\s+Importe\s+total\s+a\s+embargar\s+Importe\s+embargado\s*\n'
            r'\s*([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['importe_principal'] = self._normalize_amount(m.group(1))
            datos['importe_recargo'] = self._normalize_amount(m.group(2))
            datos['importe_intereses'] = self._normalize_amount(m.group(3))
            datos['importe_costas'] = self._normalize_amount(m.group(4))
            datos['importe_total_embargar'] = self._normalize_amount(m.group(5))
            datos['importe_embargado'] = self._normalize_amount(m.group(6))
            datos['importe'] = datos['importe_embargado']
        else:
            # Fallback por etiquetas
            for campo, patron in [
                ('importe_principal',    r'Principal[:\s]+([\d.,]+)'),
                ('importe_recargo',      r'Recargo[:\s]+([\d.,]+)'),
                ('importe_intereses',    r'Intereses[:\s]+([\d.,]+)'),
                ('importe_costas',       r'Costas[:\s]+([\d.,]+)'),
                ('importe_total_embargar', r'Importe\s+total\s+a\s+embargar[:\s]+([\d.,]+)'),
                ('importe_embargado',    r'Importe\s+embargado[:\s]+([\d.,]+)'),
            ]:
                m2 = re.search(patron, texto_completo, re.IGNORECASE)
                if m2:
                    datos[campo] = self._normalize_amount(m2.group(1))
            datos['importe'] = datos['importe_embargado']

        # ── 10. REFERENCIA DE VERIFICACIÓN ───────────────────────────────────
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
        datos['concepto'] = (
            f"Embargo Cuentas - {datos['razon_social']} - "
            f"{n_cuentas} cuenta{'s' if n_cuentas != 1 else ''} - "
            f"Embargado: {datos['importe_embargado']}€ / Total: {datos['importe_total_embargar']}€"
        )

        return datos
