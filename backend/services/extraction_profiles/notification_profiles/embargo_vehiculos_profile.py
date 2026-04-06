import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class EmbargoVehiculosProfile(BaseNotificationProfile):
    """
    Perfil para: Notificación al Deudor de la Diligencia para Comunicar a la
    Jefatura Provincial de Tráfico que no se Expida Permiso o Licencia de
    Circulación de Vehículos (TVA-391)
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    Campos extraídos:
    - razon_social: Nombre/Razón Social del deudor
    - nif: NIF/CIF del deudor
    - domicilio: Domicilio del deudor
    - localidad: Localidad del deudor
    - num_referencia: Nº de referencia
    - tipo_identificador: Tipo/Identificador (CCC/NAF)
    - regimen: Código de régimen
    - expediente: Nº de expediente
    - num_documento: Nº de documento
    - importe_total: Importe total de la deuda
    - importe_principal: Principal
    - importe_recargo: Recargo
    - importe_intereses: Intereses de demora
    - importe_costas: Costas devengadas
    - vehiculos: Lista de vehículos embargados (matrícula, marca, modelo)
    - iban: Cuenta bancaria para el pago
    - entidad_financiera: Entidad financiera
    - csv: Código de referencia de verificación
    - fecha: Fecha del documento
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        # Excluir TVA-336 (Captura/Precinto) que también menciona embargo+vehículo
        if 'TVA-336' in texto:
            return False
        return (
            'TVA-391' in texto or
            ('DILIGENCIA' in texto and 'JEFATURA PROVINCIAL DE TRÁFICO' in texto) or
            ('DILIGENCIA' in texto and 'JEFATURA PROVINCIAL DE TRAFICO' in texto) or
            ('EMBARGO' in texto and 'VEHÍCULO' in texto and 'SEGURIDAD SOCIAL' in texto) or
            ('EMBARGO' in texto and 'VEHICULO' in texto and 'SEGURIDAD SOCIAL' in texto)
        )


    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'EMBARGO DE VEHÍCULOS (TVA-391)',
            'razon_social': '',
            'nif': '',
            'domicilio': '',
            'localidad': '',
            'num_referencia': '',
            'tipo_identificador': '',
            'regimen': '',
            'expediente': '',
            'num_documento': '',
            'importe_total': 0.0,
            'importe_principal': 0.0,
            'importe_recargo': 0.0,
            'importe_intereses': 0.0,
            'importe_costas': 0.0,
            'vehiculos': [],
            'iban': '',
            'entidad_financiera': '',
            'referencia_verificacion': '',
            'fecha': '',
            # Compatibilidad con sistema de mapping
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Embargo de Vehículos (TVA-391)',
        }

        lines = texto_completo.split('\n')

        # ── 1. APELLIDOS Y NOMBRE / RAZÓN SOCIAL ─────────────────────────────
        m = re.search(
            r'Apellidos\s+y\s+nombre[/\s]*R\.?Social[:\s]+(.+?)(?:\n|NIF|$)',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['razon_social'] = m.group(1).strip()

        # ── 2. NIF/CIF ────────────────────────────────────────────────────────
        m = re.search(r'NIF[/\s]*CIF[:\s]+([A-Z0-9]{8,10})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # ── 3. DOMICILIO ──────────────────────────────────────────────────────
        m = re.search(r'Domicilio[:\s]+(.+?)(?:\n|Localidad|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['domicilio'] = m.group(1).strip()

        # ── 4. LOCALIDAD ──────────────────────────────────────────────────────
        m = re.search(r'Localidad[:\s]+(.+?)(?:\n|Importe|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['localidad'] = m.group(1).strip()

        # ── 5. Nº DE REFERENCIA ───────────────────────────────────────────────
        # Formato: "80260000329957610" (17-18 dígitos)
        m = re.search(r'N[ºo°]?\s*de\s*referencia[:\s]+(\d{15,20})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_referencia'] = m.group(1).strip()
            datos['referencia'] = datos['num_referencia']

        # ── 6. TIPO/IDENTIFICADOR y RÉGIMEN ──────────────────────────────────
        # Formato: "10 082125198851  Régimen: 0111"
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

        # ── 7. EXPEDIENTE ─────────────────────────────────────────────────────
        # Formato: "08 15 25 00365116"
        m = re.search(r'Expediente[:\s]+(\d{2}\s+\d{2}\s+\d{2}\s+\d{8})', texto_completo, re.IGNORECASE)
        if m:
            datos['expediente'] = m.group(1).strip()

        # ── 8. Nº DOCUMENTO ───────────────────────────────────────────────────
        # Formato: "08 15 391 26 058391279"
        m = re.search(r'N[ºo°]?\s*Documento[:\s]+(\d{2}\s+\d{2}\s+\d{3}\s+\d{2}\s+\d{9})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_documento'] = m.group(1).strip()

        # ── 9. IMPORTE DEUDA PENDIENTE ────────────────────────────────────────
        m = re.search(r'Importe\s+deuda\s+pendiente[:\s]+([\d.,]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['importe_total'] = self._normalize_amount(m.group(1))
            datos['importe'] = datos['importe_total']

        # ── 10. IMPORTES DESGLOSADOS (tabla: Principal, Recargo, Intereses, Costas, Total) ──
        # Formato: "1.634,08  326,81  27,02  21,78  0,00  2.009,69"
        m = re.search(
            r'IMPORTE\s+DEUDA.*?'
            r'Principal\s+Recargo\s+Intereses\s+Costas\s+devengadas.*?'
            r'([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+[\d.,]+\s+([\d.,]+)',
            texto_completo, re.DOTALL | re.IGNORECASE
        )
        if m:
            datos['importe_principal'] = self._normalize_amount(m.group(1))
            datos['importe_recargo'] = self._normalize_amount(m.group(2))
            datos['importe_intereses'] = self._normalize_amount(m.group(3))
            datos['importe_costas'] = self._normalize_amount(m.group(4))
            if not datos['importe_total']:
                datos['importe_total'] = self._normalize_amount(m.group(5))
                datos['importe'] = datos['importe_total']
        else:
            # Fallback: buscar cada importe por etiqueta
            for campo, patron in [
                ('importe_principal', r'(?:Importe\s+)?[Pp]rincipal[:\s]+([\d.,]+)'),
                ('importe_recargo',   r'[Rr]ecargo[:\s]+([\d.,]+)'),
                ('importe_intereses', r'[Ii]nter[eé]s[^:]*?[:\s]+([\d.,]+)'),
                ('importe_costas',    r'[Cc]ostas[^:]*?[:\s]+([\d.,]+)'),
            ]:
                m2 = re.search(patron, texto_completo)
                if m2:
                    datos[campo] = self._normalize_amount(m2.group(1))

        # ── 11. VEHÍCULOS EMBARGADOS ──────────────────────────────────────────
        # Formato real del PDF:
        # VEHÍCULOS
        # MATRÍCULA MARCA\nMODELO\nMATRÍCULA MARCA\nMODELO\nMATRÍCULA MARCA\nMODELO
        # 6659LSX    PEUGEOT        RIFTER
        # Con fecha 12 de DICIEMBRE...  ← aquí termina la sección
        #
        # Estrategia: buscar la sección VEHÍCULOS y extraer líneas con
        # matrícula (alfanumérico 5-8 chars) + marca + modelo separados por espacios

        # Localizar la sección VEHÍCULOS (termina en la primera línea de texto largo)
        vehiculos_match = re.search(
            r'VEH[IÍ]CULOS\s*\n(.*?)(?:Con\s+fecha|En\s+virtud|\Z)',
            texto_completo, re.DOTALL | re.IGNORECASE
        )

        if vehiculos_match:
            texto_vehiculos = vehiculos_match.group(1)
            # Patrón para línea de datos: "6659LSX    PEUGEOT        RIFTER"
            # Matrícula: 4-8 chars alfanuméricos (no solo letras)
            # Separados por 2+ espacios de marca y modelo
            patron_linea = re.compile(
                r'^([A-Z0-9]{4,8})\s{2,}'     # Matrícula (mín 2 espacios de separación)
                r'([A-ZÁÉÍÓÚÑ]{3,20})\s{2,}'  # Marca
                r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑA-Z\s]{1,20}?)\s*$',  # Modelo
                re.MULTILINE | re.IGNORECASE
            )
            for m in patron_linea.finditer(texto_vehiculos):
                matricula = m.group(1).strip()
                marca = m.group(2).strip()
                modelo = m.group(3).strip()
                # Filtrar cabeceras de columna
                if matricula.upper() not in ('MATRICULA', 'MATRÍCULA', 'MODELO', 'MARCA'):
                    datos['vehiculos'].append({
                        'matricula': matricula,
                        'marca': marca,
                        'modelo': modelo,
                    })



        # ── 12. ENTIDAD FINANCIERA ────────────────────────────────────────────
        m = re.search(r'ENTIDAD\s+FINANCIERA[:\s]+(.+?)(?:\n|$)', texto_completo, re.IGNORECASE)
        if m:
            datos['entidad_financiera'] = m.group(1).strip()

        # ── 13. IBAN / NÚMERO DE CUENTA ───────────────────────────────────────
        m = re.search(
            r'(?:N[ÚU]MERO\s+DE\s+CUENTA|IBAN|Cuenta\s+de\s+ingreso)[:\s]+(ES\d{2}[\s\d]{15,25})',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['iban'] = re.sub(r'\s+', ' ', m.group(1).strip())

        # ── 14. CSV (Código de Referencia de Verificación) ────────────────────
        m = re.search(
            r'C[oó]digo[:\s]+([A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,})',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['referencia_verificacion'] = m.group(1).strip()

        # ── 15. FECHA ─────────────────────────────────────────────────────────
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
            # Fecha en CSV: "Fecha: 05/02/2026"
            m = re.search(r'Fecha[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1)

        # ── Concepto enriquecido ──────────────────────────────────────────────
        n_veh = len(datos['vehiculos'])
        matriculas = ', '.join(v['matricula'] for v in datos['vehiculos'])
        datos['concepto'] = (
            f"Embargo Vehículos - {datos['razon_social']} - "
            f"{n_veh} vehículo{'s' if n_veh != 1 else ''}"
            f"{' (' + matriculas + ')' if matriculas else ''} - "
            f"{datos['importe_total']}€"
        )

        return datos
