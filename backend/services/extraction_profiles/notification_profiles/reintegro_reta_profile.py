import re
from typing import Dict, Any
from .base_notification_profile import BaseNotificationProfile


class ReintegroRetaProfile(BaseNotificationProfile):
    """
    Perfil para: Comunicación de Reintegro de la Regularización del RETA/RETA Mar.
    Organismo: Tesorería General de la Seguridad Social (TGSS)
    Secretaría de Estado de la Seguridad Social y Pensiones

    Campos extraídos:
    - expediente: Nº Expediente
    - num_documento: Nº Documento
    - fecha: Fecha del documento
    - tipo_identificador: Tipo/Identificador (NAF)
    - regimen: Régimen de la Seguridad Social
    - nif: NIF/CIF del autónomo
    - nombre: Apellidos y Nombre / Razón Social
    - importe: Importe del reintegro
    - titular: Titular de la cuenta bancaria
    - iban: Cuenta bancaria (IBAN)
    - forma_pago: Forma de pago
    - anio_regularizacion: Año de la regularización
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return (
            'REINTEGRO' in texto and
            ('RETA' in texto or 'REGULARIZACIÓN' in texto or 'REGULARIZACION' in texto) and
            ('TESORERÍA GENERAL' in texto or 'SEGURIDAD SOCIAL' in texto)
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'REINTEGRO REGULARIZACIÓN RETA',
            'expediente': '',
            'num_documento': '',
            'fecha': '',
            'tipo_identificador': '',
            'regimen': '',
            'nif': '',
            'nombre': '',
            'importe': 0.0,
            'titular': '',
            'iban': '',
            'forma_pago': '',
            'anio_regularizacion': '',
            # Campos de compatibilidad con el sistema de mapping
            'referencia': '',
            'concepto': 'Reintegro Regularización RETA',
        }

        # ── 1. Nº EXPEDIENTE ─────────────────────────────────────────────────
        # Formato: "08-2026-001919970"
        m = re.search(r'N[ºo°]?\s*Expediente[:\s]+(\d{2}-\d{4}-\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()
            datos['referencia'] = datos['expediente']

        # ── 2. Nº DOCUMENTO ───────────────────────────────────────────────────
        # Formato: "08 06 D27 26 074230477"
        m = re.search(r'N[ºo°]?\s*Documento[:\s]+([0-9A-Z]{2}(?:\s+[0-9A-Z]+){2,5})', texto_completo, re.IGNORECASE)
        if m:
            # Tomar solo la primera línea y limpiar texto extra
            num_doc = m.group(1).strip().split('\n')[0].strip()
            datos['num_documento'] = num_doc

        # ── 3. FECHA ──────────────────────────────────────────────────────────
        # Aparece como "Fecha: 6 de febrero de 2026" o en la firma "BARCELONA, a 6 de febrero de 2026"
        MESES = {
            'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
            'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
            'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
        }
        m = re.search(
            r'(?:Fecha[:\s]+|a\s+)(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
            texto_completo, re.IGNORECASE
        )
        if m:
            dia = m.group(1).zfill(2)
            mes_str = m.group(2).lower()
            anio = m.group(3)
            mes = MESES.get(mes_str, '??')
            datos['fecha'] = f"{dia}/{mes}/{anio}"
            datos['anio_regularizacion'] = str(int(anio) - 1)  # La regularización es del año anterior

        # Fallback: fecha numérica en cabecera "Fecha: 6 de febrero de 2026"
        if not datos['fecha']:
            m = re.search(r'Fecha[:\s]+(\d{1,2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1)

        # ── 4. TIPO/IDENTIFICADOR (NAF) ───────────────────────────────────────
        # Formato: "07 081145500651"
        m = re.search(r'Tipo[/\s]*Identificador[:\s]+(\d{2}\s+\d{12})', texto_completo, re.IGNORECASE)
        if m:
            datos['tipo_identificador'] = m.group(1).strip()

        # ── 5. RÉGIMEN ────────────────────────────────────────────────────────
        m = re.search(r'R[ée]gimen[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['regimen'] = m.group(1).strip()

        # ── 6. NIF/CIF ────────────────────────────────────────────────────────
        m = re.search(r'NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # ── 7. NOMBRE / RAZÓN SOCIAL ──────────────────────────────────────────
        # Formato: "Apellidos y Nombre/R.Social: EL HABIBA — ADIL"
        m = re.search(
            r'Apellidos\s+y\s+Nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|$)',
            texto_completo, re.IGNORECASE
        )
        if m:
            nombre_raw = m.group(1).strip()
            # Limpiar separadores como "—", "–", "-" y espacios múltiples
            nombre_raw = re.sub(r'\s*[—–-]\s*', ' ', nombre_raw)
            nombre_raw = re.sub(r'\s{2,}', ' ', nombre_raw).strip()
            datos['nombre'] = nombre_raw

        # ── 8. IMPORTE DEL REINTEGRO ──────────────────────────────────────────
        # Aparece varias veces: "importe de ****83,90 euros" o "Importe del reintegro: ****83,90"
        # Los asteriscos son para ocultar el importe en la notificación
        m = re.search(
            r'[Ii]mporte[^:]*?[:\s]+\*{0,10}([\d.,]+)\s*euros',
            texto_completo
        )
        if m:
            datos['importe'] = self._normalize_amount(m.group(1))
        else:
            # Buscar cualquier cantidad seguida de "euros" en el texto
            m = re.search(r'\*{2,}([\d.,]+)\s*euros', texto_completo)
            if m:
                datos['importe'] = self._normalize_amount(m.group(1))

        # ── 9. TITULAR ────────────────────────────────────────────────────────
        m = re.search(r'Titular[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['titular'] = m.group(1).strip()

        # ── 10. IBAN / CUENTA BANCARIA ────────────────────────────────────────
        # Formato: "ES26 2100 1841 06** **** 5454" (parcialmente enmascarado)
        m = re.search(
            r'(?:Cuenta\s+bancaria|IBAN)[:\s]+(ES\d{2}[\s\d*]{15,30})',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['iban'] = m.group(1).strip()

        # ── 11. FORMA DE PAGO ─────────────────────────────────────────────────
        m = re.search(r'Forma\s+de\s+pago[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['forma_pago'] = m.group(1).strip()

        # ── Concepto enriquecido ──────────────────────────────────────────────
        anio_reg = datos.get('anio_regularizacion', '')
        datos['concepto'] = (
            f"Reintegro RETA {anio_reg} - {datos['nombre']} - {datos['importe']}€"
            if datos['nombre'] else 'Reintegro Regularización RETA'
        )

        return datos
