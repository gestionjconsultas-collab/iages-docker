import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class CapturaPrecintosVehiculosProfile(BaseNotificationProfile):
    """
    Perfil para: Solicitud de Captura, Depósito y Precinto de Vehículos
    Embargados (TVA-336)
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
    - importe_deuda: Importe deuda pendiente
    - destinatario: Destinatario de la solicitud (Jefatura de Tráfico u otro)
    - dir_destinatario: Dirección del destinatario
    - localidad_destinatario: Localidad del destinatario
    - provincia_destinatario: Provincia del destinatario
    - vehiculos: Lista de vehículos (modelo, marca, matrícula, observaciones)
    - csv: Código de referencia de verificación
    - fecha: Fecha del documento
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return (
            'TVA-336' in texto or
            ('CAPTURA' in texto and 'PRECINTO' in texto and 'VEHÍCULO' in texto) or
            ('CAPTURA' in texto and 'PRECINTO' in texto and 'VEHICULO' in texto)
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'CAPTURA, DEPÓSITO Y PRECINTO DE VEHÍCULOS (TVA-336)',
            'nif': '',
            'razon_social': '',
            'domicilio': '',
            'localidad': '',
            'tipo_identificador': '',
            'regimen': '',
            'expediente': '',
            'num_documento': '',
            'importe_deuda': 0.0,
            'destinatario': '',
            'dir_destinatario': '',
            'localidad_destinatario': '',
            'provincia_destinatario': '',
            'vehiculos': [],
            'referencia_verificacion': '',
            'fecha': '',
            # Compatibilidad con sistema de mapping
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Captura, Depósito y Precinto de Vehículos (TVA-336)',
        }

        # ── 1. NIF/CIF ────────────────────────────────────────────────────────
        m = re.search(r'NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # ── 2. APELLIDOS Y NOMBRE / RAZÓN SOCIAL ─────────────────────────────
        m = re.search(
            r'Apellidos\s+y\s+nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|Tipo|$)',
            texto_completo, re.IGNORECASE
        )
        if m:
            nombre_raw = re.sub(r'\s*[—–-]\s*', ' ', m.group(1).strip())
            datos['razon_social'] = re.sub(r'\s{2,}', ' ', nombre_raw).strip()

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
        # Formato: "08 15 25 00365116"
        m = re.search(r'N[ºo°]?\s*Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()
            datos['referencia'] = datos['expediente']

        # ── 7. Nº DOCUMENTO ───────────────────────────────────────────────────
        # Formato: "08 15 336 26 068393303"
        m = re.search(r'N[ºo°]?\s*Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_documento'] = m.group(1).strip()

        # ── 8. IMPORTE DEUDA PENDIENTE ────────────────────────────────────────
        m = re.search(r'Importe\s+deuda\s+pendiente[:\s]+([\d.,]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['importe_deuda'] = self._normalize_amount(m.group(1))
            datos['importe'] = datos['importe_deuda']

        # ── 9. DESTINATARIO ───────────────────────────────────────────────────
        # Formato:
        # DESTINATARIO: GRUP PUPA ENTERTAINMENT,S.L.
        # DIRECCIÓN:    CL AMADEU VIVES 52 2 3
        # LOCALIDAD:    08906 HOSPITALET DE LLOBRE
        # PROVINCIA:    BARCELONA
        m = re.search(r'DESTINATARIO[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['destinatario'] = m.group(1).strip()

        m = re.search(r'DIRECCI[ÓO]N[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['dir_destinatario'] = m.group(1).strip()

        m = re.search(r'LOCALIDAD[:\s]+(.+?)(?:\n|PROVINCIA|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['localidad_destinatario'] = m.group(1).strip()

        m = re.search(r'PROVINCIA[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['provincia_destinatario'] = m.group(1).strip()

        # ── 10. VEHÍCULOS ─────────────────────────────────────────────────────
        # Formato:
        # MODELO: RIFTER    MARCA: PEUGEOT    MATRÍCULA: 6659LSX
        # OBSERVACIONES: (puede estar vacío)
        #
        # Estrategia: buscar bloques MODELO/MARCA/MATRÍCULA
        patron_vehiculo = re.compile(
            r'MODELO[:\s]+([A-ZÁÉÍÓÚÑA-Z0-9\s]+?)\s+'
            r'MARCA[:\s]+([A-ZÁÉÍÓÚÑA-Z0-9\s]+?)\s+'
            r'MATR[IÍ]CULA[:\s]+([A-Z0-9]{4,8})',
            re.IGNORECASE
        )
        for m in patron_vehiculo.finditer(texto_completo):
            modelo = m.group(1).strip()
            marca = m.group(2).strip()
            matricula = m.group(3).strip()

            # Buscar OBSERVACIONES en las líneas siguientes
            pos_fin = m.end()
            texto_tras = texto_completo[pos_fin:pos_fin + 200]
            obs_match = re.search(r'OBSERVACIONES[:\s]*(.+?)(?:\n\n|\n[A-Z]|$)', texto_tras, re.IGNORECASE | re.DOTALL)
            observaciones = obs_match.group(1).strip() if obs_match else ''

            datos['vehiculos'].append({
                'modelo': modelo,
                'marca': marca,
                'matricula': matricula,
                'observaciones': observaciones,
            })

        # ── 11. CSV ───────────────────────────────────────────────────────────
        m = re.search(
            r'C[oó]digo[:\s]+([A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,})',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['referencia_verificacion'] = m.group(1).strip()

        # ── 12. FECHA ─────────────────────────────────────────────────────────
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
        n_veh = len(datos['vehiculos'])
        matriculas = ', '.join(v['matricula'] for v in datos['vehiculos'])
        datos['concepto'] = (
            f"Captura/Precinto Vehículos - {datos['razon_social']} - "
            f"{n_veh} vehículo{'s' if n_veh != 1 else ''}"
            f"{' (' + matriculas + ')' if matriculas else ''} - "
            f"{datos['importe_deuda']}€"
        )

        return datos
