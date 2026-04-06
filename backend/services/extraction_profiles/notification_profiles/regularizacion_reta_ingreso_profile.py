import re
import unicodedata
from typing import Dict, Any
from .base_notification_profile import BaseNotificationProfile


class RegularizacionRetaIngresoProfile(BaseNotificationProfile):
    """
    Perfil para: Resolución sobre Base de Cotización Definitiva (Regularización RETA) - A INGRESAR
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    El documento tiene 6 páginas:
      - Pág. 1: Carta de presentación con nombre del autónomo
      - Pág. 2-3: Resolución con NAF, NIF, base definitiva, importe a ingresar
      - Pág. 4-5: Detalle mensual de diferencias de cotización
      - Pág. 6: Boletín/Documento de Pago con IBAN y referencia

    Campos extraídos:
      - razon_social: Nombre del trabajador autónomo
      - nif: DNI/NIE/NIF
      - naf: Número de afiliación (CCC Afiliación)
      - fecha: Fecha de la resolución
      - base_definitiva: Base de cotización definitiva anual
      - importe_ingreso: Importe a ingresar (diferencia de cotización)
      - entidad_financiera: Banco donde realizar el ingreso
      - iban: IBAN de la cuenta de ingreso
      - num_referencia: Número de referencia para el pago
      - id_cea: Identificador CEA
      - codigo_cea: Código CEA (CSV de verificación)
      - resultado: "A INGRESAR"
    """

    @staticmethod
    def _normalizar(s: str) -> str:
        """Elimina tildes y convierte a mayúsculas para comparación robusta."""
        return ''.join(
            c for c in unicodedata.normalize('NFD', s)
            if unicodedata.category(c) != 'Mn'
        ).upper()

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', self._normalizar(texto_completo))
        return (
            'RESOLUCION SOBRE BASE DE COTIZACION DEFINITIVA' in texto and
            'PERSONA TRABAJADORA AUTONOMA' in texto and
            'A INGRESAR' in texto and
            'A DEVOLVER' not in texto  # Exclusión explícita del perfil de devolución
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'RESOLUCIÓN REGULARIZACIÓN RETA (INGRESO)',
            'razon_social': '',
            'nif': '',
            'naf': '',
            'fecha': '',
            'anio': '2024',
            'base_definitiva': 0.0,
            'importe_ingreso': 0.0,
            'entidad_financiera': '',
            'iban': '',
            'num_referencia': '',
            'id_cea': '',
            'codigo_cea': '',
            'resultado': 'A INGRESAR',
            # Compatibilidad con sistema general
            'referencia': '',
            'importe': 0.0,
            'concepto': '',
        }

        # 1. NOMBRE / RAZÓN SOCIAL
        # Formato carta: "Hola, KAUR MANINDER ---:" — captura todo hasta los guiones finales y el colon
        m = re.search(r'Hola,\s+(.+?)\s*(?:-{2,}\s*)?:', texto_completo)
        if m:
            datos['razon_social'] = m.group(1).strip()
        else:
            # Formato resolución: "D./Dña. KAUR MANINDER" o "D./Dna. KAUR MANINDER"
            m = re.search(r'D\./D(?:ña|na)\.\s+(.+?)\s*(?:-{2,})?$', texto_completo, re.MULTILINE)
            if m:
                datos['razon_social'] = m.group(1).strip()
            else:
                # Formato boletín: "Nombre/Razón social:  KAUR MANINDER"
                m = re.search(r'Nombre/Raz[oó]n\s+social:\s+(.+?)\s*(?:-{2,})?$', texto_completo, re.MULTILINE | re.IGNORECASE)
                if m:
                    datos['razon_social'] = m.group(1).strip()

        # 2. NAF (Número de afiliación / CCC Afiliación)
        m = re.search(r'n[uú]mero\s+de\s+afiliaci[oó]n\s+(\d{12})', texto_completo, re.IGNORECASE)
        if m:
            datos['naf'] = m.group(1).strip()
        else:
            # En el boletín aparece como "CCC/Nº Afiliación"
            m = re.search(r'CCC/N[º°]\s*Afiliaci[oó]n\s+(\d{12})', texto_completo, re.IGNORECASE)
            if m:
                datos['naf'] = m.group(1).strip()

        # 3. DNI / NIE / NIF
        m = re.search(r'DNI/NIE\s+([A-Z0-9]{8,9})', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()
        else:
            m = re.search(r'NIF\s+deudor[:\s]+([A-Z0-9]{8,9})', texto_completo, re.IGNORECASE)
            if m:
                datos['nif'] = m.group(1).strip()

        # 4. FECHA DE RESOLUCIÓN
        m = re.search(r'Fecha\s+de\s+resoluci[oó]n:\s*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        if m:
            datos['fecha'] = m.group(1).strip()
        else:
            # En la tabla de referencias CEA la fecha aparece en la segunda columna
            m = re.search(r'(?:Id\.?\s+CEA:[^\n]*\n\S+\s+)(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1).strip()
        # Fallback: "Fecha de emisión del documento: 04/02/2026"
        if not datos['fecha']:
            m = re.search(r'Fecha\s+de\s+emisi[oó]n\s+del\s+documento:\s*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1).strip()

        # 5. BASE DE COTIZACIÓN DEFINITIVA
        m = re.search(
            r'base\s+de\s+cotizaci[oó]n\s+definitiva\s+del\s+a[ñn]o\s+2024\s+es\s+de\s+([\d.,]+)\s+euros',
            texto_completo, re.IGNORECASE
        )
        if m:
            datos['base_definitiva'] = self._normalize_amount(m.group(1))

        # 6. IMPORTE A INGRESAR
        # Buscar "A INGRESAR   442,56 €" o "A INGRESAR   442,56"
        m = re.search(r'A\s+INGRESAR\s+([\d.,]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['importe_ingreso'] = self._normalize_amount(m.group(1))
        else:
            # En el boletín: "Total a ingresar:   442,56"
            m = re.search(r'Total\s+a\s+ingresar:\s*([\d.,]+)', texto_completo, re.IGNORECASE)
            if m:
                datos['importe_ingreso'] = self._normalize_amount(m.group(1))
        datos['importe'] = datos['importe_ingreso']

        # 7. ENTIDAD FINANCIERA E IBAN
        m = re.search(r'Entidad\s+Financiera\s+ingreso:\s+([^\n]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['entidad_financiera'] = m.group(1).strip()

        # IBAN: buscar formato "ES15  0182  6035  ..." o comprimido "ES150182..."
        m = re.search(r'\b(ES\d{2}(?:\s+\d{4}){5})\b', texto_completo, re.IGNORECASE)
        if m:
            datos['iban'] = re.sub(r'\s+', ' ', m.group(1).strip())
        else:
            m = re.search(r'\b(ES\d{22})\b', texto_completo, re.IGNORECASE)
            if m:
                datos['iban'] = m.group(1).strip()

        # 8. NÚMERO DE REFERENCIA PARA EL PAGO
        m = re.search(r'N[oº°]?\s*(?:de\s+)?referencia[:\s]+(\d{15,18})', texto_completo, re.IGNORECASE)
        if m:
            datos['num_referencia'] = m.group(1).strip()

        # 9. REFERENCIAS ELECTRÓNICAS (Id CEA y Código CEA)
        # Patrón del Código CEA: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
        CEA_PATTERN = r'[A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){4,5}'

        # Buscar Código CEA (con guiones)
        m_cea = re.search(CEA_PATTERN, texto_completo)
        if m_cea:
            datos['codigo_cea'] = m_cea.group(0).strip()

        # Buscar Id. CEA en la misma fila que el Código CEA
        if datos['codigo_cea']:
            m_id = re.search(
                r'([A-Z0-9]{8,15})\s+\d{2}/\d{2}/\d{4}\s+' + re.escape(datos['codigo_cea']),
                texto_completo, re.IGNORECASE
            )
            if m_id:
                datos['id_cea'] = m_id.group(1).strip()
                datos['referencia'] = datos['id_cea']
        # Fallback Id. CEA con encabezado
        if not datos['id_cea']:
            m = re.search(r'Id\.\s+CEA:\s*\n?\s*([A-Z0-9]{8,15})(?:\s|$)', texto_completo, re.IGNORECASE)
            if m:
                datos['id_cea'] = m.group(1).strip()
                datos['referencia'] = datos['id_cea']

        # Usar num_referencia como referencia si no hay id_cea
        if not datos['referencia'] and datos['num_referencia']:
            datos['referencia'] = datos['num_referencia']

        # 10. CONCEPTO
        datos['concepto'] = (
            f"Regularización RETA 2024 - {datos['razon_social']} "
            f"- A INGRESAR {datos['importe_ingreso']}€"
        )

        return datos
