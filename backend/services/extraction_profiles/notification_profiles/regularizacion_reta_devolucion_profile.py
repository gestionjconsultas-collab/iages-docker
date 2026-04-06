import re
from typing import Dict, Any
from .base_notification_profile import BaseNotificationProfile


class RegularizacionRetaDevolucionProfile(BaseNotificationProfile):
    """
    Perfil para: Resolución sobre Base de Cotización Definitiva (Regularización RETA) - A DEVOLVER
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    Campos extraídos:
    - razon_social: Nombre del trabajador
    - nif: DNI/NIE/NIF
    - naf: Número de afiliación
    - fecha: Fecha de la resolución
    - anio: Año de la regularización (2024)
    - base_definitiva: Base de cotización definitiva anual/mensual
    - importe_devolucion: Importe que se va a devolver
    - id_cea: Identificador CEA
    - codigo_cea: Código CEA (CSV)
    - resultado: "A DEVOLVER" o "A FAVOR"
    """

    def matches(self, texto_completo: str) -> bool:
        import unicodedata
        # Normalizar: quitar tildes y pasar a mayúsculas para comparación robusta
        def normalizar(s):
            return ''.join(
                c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn'
            ).upper()

        texto = re.sub(r'\s+', ' ', normalizar(texto_completo))
        return (
            'RESOLUCION SOBRE BASE DE COTIZACION DEFINITIVA' in texto and
            'PERSONA TRABAJADORA AUTONOMA' in texto and
            ('A DEVOLVER' in texto or 'A FAVOR' in texto or 'DIFERENCIAS DE COTIZACION A SU FAVOR' in texto)
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'RESOLUCIÓN REGULARIZACIÓN RETA (DEVOLUCIÓN)',
            'razon_social': '',
            'nif': '',
            'naf': '',
            'fecha': '',
            'anio': '2024',
            'base_definitiva': 0.0,
            'importe_devolucion': 0.0,
            'id_cea': '',
            'codigo_cea': '',
            'resultado': 'A DEVOLVER',
            # Compatibilidad
            'referencia': '',
            'importe': 0.0,
            'concepto': 'Regularización RETA 2024 - A DEVOLVER',
        }

        # 1. NOMBRE / RAZÓN SOCIAL — acepta con o sin tilde (Dña./Dna.)
        m = re.search(r'D\./D(?:ña|na)\.\s+([^\n,]+)', texto_completo)
        if m:
            datos['razon_social'] = m.group(1).strip()
        else:
            m = re.search(r'Hola,\s+([^:]+):', texto_completo)
            if m:
                datos['razon_social'] = m.group(1).strip()

        # 2. NAF (Número de afiliación) — acepta con o sin tilde
        m = re.search(r'n[uú]mero\s+de\s+afiliaci[oó]n\s+(\d{12})', texto_completo, re.IGNORECASE)
        if m:
            datos['naf'] = m.group(1).strip()

        # 3. DNI / NIE / NIF
        m = re.search(r'DNI/NIE\s+([A-Z0-9]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['nif'] = m.group(1).strip()

        # 4. FECHA DE RESOLUCIÓN — acepta con o sin tilde
        m = re.search(r'Fecha\s+de\s+resoluci[oó]n:\s*(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
        if m:
            datos['fecha'] = m.group(1).strip()
        else:
            # En la línea de datos de la tabla de referencias (segunda columna = fecha)
            m = re.search(r'(?:Id\.?\s+CEA:[^\n]*\n\S+\s+)(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1).strip()

        # 5. IMPORTES (Base definitiva y Devolución)
        m = re.search(r'base\s+de\s+cotización\s+definitiva\s+del\s+año\s+2024\s+es\s+de\s+([\d.,]+)\s+euros', texto_completo, re.IGNORECASE)
        if m:
            datos['base_definitiva'] = self._normalize_amount(m.group(1))

        # Importe a devolver - Buscamos "A DEVOLVER" seguido de un importe o "a su favor"
        m = re.search(r'A\s+DEVOLVER\s+([\d.,]+)', texto_completo, re.IGNORECASE)
        if m:
            datos['importe_devolucion'] = self._normalize_amount(m.group(1))
        else:
            m = re.search(r'diferencias\s+de\s+cotización\s+a\s+su\s+favor.*?(\d+,\d{2})\s+euros', texto_completo, re.IGNORECASE | re.DOTALL)
            if m:
                datos['importe_devolucion'] = self._normalize_amount(m.group(1))

        datos['importe'] = datos['importe_devolucion']

        # 6. REFERENCIAS ELECTRÓNICAS (Id CEA y Código CEA)
        # El PDF tiene una tabla de dos líneas:
        #   Línea 1: "Id. CEA:    Fecha:    Código CEA:    Página:"
        #   Línea 2: "9A6FUK...   04/02/2026  UOPSC-W34XS-...   1"
        # El patrón del CEA/CSV es: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX (5-6 grupos)
        CEA_PATTERN = r'[A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){4,5}'

        # Buscar codigo CEA (patrón con guiones, muy distintivo)
        m_cea = re.search(CEA_PATTERN, texto_completo)
        if m_cea:
            datos['codigo_cea'] = m_cea.group(0).strip()

        # Buscar Id. CEA: buscar la fila de datos de la tabla de referencias
        # El Id. CEA está en la misma fila que el Código CEA pero sin guiones
        # Formato: "9A6FUK4938SY     04/02/2026  UOPSC-W34XS-..."
        if datos['codigo_cea']:
            m_id = re.search(
                r'([A-Z0-9]{8,15})\s+\d{2}/\d{2}/\d{4}\s+' + re.escape(datos['codigo_cea']),
                texto_completo, re.IGNORECASE
            )
            if m_id:
                datos['id_cea'] = m_id.group(1).strip()
                datos['referencia'] = datos['id_cea']
        # Fallback: buscar por encabezado
        if not datos['id_cea']:
            m = re.search(r'Id\.\s+CEA:\s*\n?\s*([A-Z0-9]{8,15})(?:\s|$)', texto_completo, re.IGNORECASE)
            if m:
                datos['id_cea'] = m.group(1).strip()
                datos['referencia'] = datos['id_cea']




        # 7. CONCEPTO
        datos['concepto'] = f"Regularización RETA 2024 - {datos['razon_social']} - A DEVOLVER {datos['importe_devolucion']}€"

        return datos
