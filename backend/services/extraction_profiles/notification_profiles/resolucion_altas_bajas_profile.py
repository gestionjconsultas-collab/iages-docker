import re
from typing import Dict, Any, List
from .base_notification_profile import BaseNotificationProfile


class ResolucionAltasBajasProfile(BaseNotificationProfile):
    """
    Perfil para: Resolución sobre Reconocimiento de Altas/Bajas Trabajadores
    Organismo: Tesorería General de la Seguridad Social (TGSS)

    Campos extraídos:
    - razon_social: Nombre de la empresa
    - ccc: Código de Cuenta de Cotización
    - regimen: Régimen de la Seguridad Social
    - fecha: Fecha del documento
    - id_cea: Identificador CEA
    - codigo_cea: Código Seguro de Verificación (CEA)
    - trabajadores: Lista de trabajadores con NSS, nombre y fechas de alta/baja
    """

    def matches(self, texto_completo: str) -> bool:
        texto = re.sub(r'\s+', ' ', texto_completo).upper()
        return (
            'RESOLUCIÓN SOBRE RECONOCIMIENTO DE ALTAS' in texto or
            'RECONOCIMIENTO DE ALTAS/BAJAS' in texto or
            'RECONOCIMIENTO DE ALTAS' in texto
        ) and (
            'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL' in texto or
            'TGSS' in texto
        )

    def extract_data(self, texto_completo: str) -> Dict[str, Any]:
        datos = {
            'organismo': 'TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL',
            'tipo_documento': 'RESOLUCIÓN ALTAS/BAJAS TRABAJADORES',
            'razon_social': '',
            'ccc': '',
            'regimen': '',
            'fecha': '',
            'id_cea': '',
            'codigo_cea': '',
            'trabajadores': [],
            # Campos de compatibilidad con el sistema de mapping
            'referencia': '',
            'nif': '',
            'concepto': 'Resolución Altas/Bajas Trabajadores',
        }

        lines = texto_completo.split('\n')

        # ── 1. RAZÓN SOCIAL ──────────────────────────────────────────────────
        # Aparece justo después de "RAZÓN SOCIAL:"
        m = re.search(r'RAZ[ÓO]N\s+SOCIAL[:\s]+(.+)', texto_completo, re.IGNORECASE)
        if m:
            datos['razon_social'] = m.group(1).strip()

        # ── 2. CCC (Código de Cuenta de Cotización) ───────────────────────────
        # Formato: "CCC:  08 187040173"  o  "08 187040173"
        m = re.search(r'CCC[:\s]+(\d{2}\s*\d{9,})', texto_completo, re.IGNORECASE)
        if m:
            datos['ccc'] = m.group(1).strip()
        else:
            # Buscar en el texto de resolución: "código cuenta de cotización 08 187040173"
            m = re.search(r'c[oó]digo\s+cuenta\s+de\s+cotizaci[oó]n\s+(\d{2}\s+\d{9,})', texto_completo, re.IGNORECASE)
            if m:
                datos['ccc'] = m.group(1).strip()

        # ── 3. RÉGIMEN ────────────────────────────────────────────────────────
        m = re.search(r'R[ÉE]GIMEN[:\s]+(.+)', texto_completo, re.IGNORECASE)
        if m:
            datos['regimen'] = m.group(1).strip()

        # ── 4. FECHA ──────────────────────────────────────────────────────────
        # Tabla "REFERENCIAS ELECTRÓNICAS": Id. CEA | Fecha | Código CEA | Página
        # La fecha aparece como "05/02/2026" en la tabla
        m = re.search(
            r'REFERENCIAS\s+ELECTR[OÓ]NICAS.*?'
            r'(?:Id\.?\s*CEA|Id\s+CEA).*?'
            r'Fecha.*?'
            r'(\d{2}/\d{2}/\d{4})',
            texto_completo, re.DOTALL | re.IGNORECASE
        )
        if m:
            datos['fecha'] = m.group(1)
        else:
            # Fallback: buscar fecha en firma digital "Fecha: 05/02/2026"
            m = re.search(r'Fecha[:\s]+(\d{2}/\d{2}/\d{4})', texto_completo, re.IGNORECASE)
            if m:
                datos['fecha'] = m.group(1)

        # ── 5. ID CEA y CÓDIGO CEA ────────────────────────────────────────────
        # Tabla: "99EBHV4A62UL  |  05/02/2026  |  KQFFR-P5FSK-P2Z42-KIHWA-GOFXO-EKVD7  |  1"
        m = re.search(
            r'([A-Z0-9]{10,14})\s+'           # Id. CEA (ej: 99EBHV4A62UL)
            r'\d{2}/\d{2}/\d{4}\s+'           # Fecha
            r'([A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){3,})',  # Código CEA (ej: KQFFR-P5FSK-...)
            texto_completo
        )
        if m:
            datos['id_cea'] = m.group(1).strip()
            datos['codigo_cea'] = m.group(2).strip()
            datos['referencia'] = datos['id_cea']

        # ── 6. TRABAJADORES (del ANEXO) ───────────────────────────────────────
        # Formato real del PDF (extraído con PyMuPDF):
        #
        # ANEXO
        # NSS1
        # APELLIDOS Y NOMBRE
        # F.R.ALTA2 F.E.ALTA3 F.R.BAJA4 F.E.BAJA5
        # 08 1482509771 TCHAVTCHAVADZE ALEKSANDRE
        #  
        #  
        # 26-01-2026 26-01-2026
        #
        # Estrategia:
        # 1. Buscar líneas que empiecen con NSS (2 dígitos + espacio + 10 dígitos)
        # 2. El nombre está en la misma línea, después del NSS
        # 3. Las fechas están en las líneas siguientes (puede haber líneas vacías entre ellas)

        # Buscar la sección ANEXO
        anexo_match = re.search(r'ANEXO\s*\n(.+?)(?:Firmado|$)', texto_completo, re.DOTALL | re.IGNORECASE)
        texto_anexo = anexo_match.group(1) if anexo_match else texto_completo

        # Patrón para línea de NSS + Nombre: "08 1482509771 TCHAVTCHAVADZE ALEKSANDRE"
        # Quitamos boundaries estrictos ^ $ que suelen fallar con OCR o variaciones de línea
        patron_nss_nombre = re.compile(
            r'(\d{2}\s+\d{10})\s+([A-ZÁÉÍÓÚÑÜA-Z][A-ZÁÉÍÓÚÑÜA-Z\s,]+)',
            re.IGNORECASE
        )

        # Patrón para fechas: "26-01-2026 26-01-2026" o "27-01-2026 27-01-2026"
        patron_fecha = re.compile(r'(\d{2}-\d{2}-\d{4})')

        lines_anexo = texto_anexo.split('\n')

        for i, line in enumerate(lines_anexo):
            m_nss = patron_nss_nombre.match(line.strip())
            if not m_nss:
                continue

            nss = m_nss.group(1).strip()
            nombre = m_nss.group(2).strip()

            # Buscar fechas en las siguientes 5 líneas (puede haber líneas en blanco)
            fechas = []
            for j in range(i + 1, min(i + 6, len(lines_anexo))):
                fechas_en_linea = patron_fecha.findall(lines_anexo[j])
                fechas.extend(fechas_en_linea)
                if len(fechas) >= 2:
                    break

            trabajador = {
                'nss': nss,
                'nombre': nombre,
                'fecha_real_alta': fechas[0] if len(fechas) > 0 else '',
                'fecha_efectos_alta': fechas[1] if len(fechas) > 1 else '',
                'fecha_real_baja': fechas[2] if len(fechas) > 2 else '',
                'fecha_efectos_baja': fechas[3] if len(fechas) > 3 else '',
            }
            datos['trabajadores'].append(trabajador)


        # Concepto enriquecido
        n_trabajadores = len(datos['trabajadores'])
        datos['concepto'] = f"Resolución Altas/Bajas - {datos['razon_social']} ({n_trabajadores} trabajador{'es' if n_trabajadores != 1 else ''})"

        return datos
