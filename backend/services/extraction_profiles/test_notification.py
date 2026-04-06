# -*- coding: utf-8 -*-
"""
test_notification.py
Script de prueba para los perfiles de extracción de notificaciones.

USO:
    python test_notification.py

Pon tus PDFs en: backend/services/extraction_profiles/test_pdfs/
"""
import sys
import os
import glob

# Forzar UTF-8 en Windows para que los emojis no rompan la consola
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# Ajustar path para importar desde backend/
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, BACKEND_DIR)

import fitz  # PyMuPDF

from services.extraction_profiles.notification_profiles import get_notification_profile, PROFILES


def extraer_texto_pdf(pdf_path: str) -> str:
    """Extrae texto de un PDF usando PyMuPDF."""
    doc = fitz.open(pdf_path)
    texto = ""
    for page in doc:
        texto += page.get_text()
    doc.close()
    return texto


def probar_pdf(pdf_path: str):
    print(f"\n{'='*60}")
    print(f"📄 Archivo: {os.path.basename(pdf_path)}")
    print(f"{'='*60}")

    try:
        texto = extraer_texto_pdf(pdf_path)
        print(f"📝 Texto extraído ({len(texto)} caracteres)")
        print(f"\n--- PRIMEROS 300 CARACTERES ---")
        print(texto[:300])
        print("--- FIN PREVIEW ---\n")

        # Detectar perfil
        profile = get_notification_profile(texto)

        if profile:
            print(f"✅ Perfil detectado: {type(profile).__name__}")
            datos = profile.extract_data(texto)
            print(f"\n📊 DATOS EXTRAÍDOS:")
            for k, v in datos.items():
                if k == 'trabajadores':
                    print(f"   trabajadores ({len(v)}):")
                    for t in v:
                        print(f"      - {t['nss']} | {t['nombre']} | Alta: {t['fecha_real_alta']} | Baja: {t['fecha_real_baja']}")
                else:
                    print(f"   {k}: {v}")
        else:
            print(f"⚠️  Ningún perfil detectó este documento.")
            print(f"   Perfiles disponibles: {[type(p).__name__ for p in PROFILES]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def probar_texto_muestra():
    """Prueba con textos de muestra hardcodeados (sin necesidad de PDFs)."""

    print("\n" + "="*60)
    print("🧪 PRUEBA 1: Providencia de Apremio (texto de muestra)")
    print("="*60)
    sample_providencia = """
TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL
PROVIDENCIA DE APREMIO

Nombre o Razón Social
ALYAQOOB 493 S.L.

Providencia de Apremio N.º
08/25/618339167

Fecha
07/02/2026

NIF/CIF
B65999344

PRINCIPAL    RECARGO    INTERÉS DE DEMORA    COSTAS    TOTAL A INGRESAR
5.454,81     1.090,96   0,00                0,00      6.545,77

Nº de referencia: 082500618339167
"""
    profile = get_notification_profile(sample_providencia)
    if profile:
        print(f"✅ Perfil: {type(profile).__name__}")
        datos = profile.extract_data(sample_providencia)
        for k, v in datos.items():
            print(f"   {k}: {v}")
    else:
        print("⚠️  No detectado")

    print("\n" + "="*60)
    print("🧪 PRUEBA 2: Resolución Altas/Bajas Trabajadores (texto de muestra)")
    print("="*60)
    sample_altas_bajas = """
MINISTERIO DE INCLUSIÓN, SEGURIDAD SOCIAL Y MIGRACIONES
TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL

RESOLUCIÓN SOBRE RECONOCIMIENTO DE ALTAS/BAJAS TRABAJADORES

RAZÓN SOCIAL:  FOOD ALIMENT SL
CCC:  08 187040173
RÉGIMEN:  Régimen General

Esta Tesorería General de la Seguridad social...

REFERENCIAS ELECTRÓNICAS
Id. CEA:          Fecha:      Código CEA:                              Página:
99EBHV4A62UL     05/02/2026  KQFFR-P5FSK-P2Z42-KIHWA-GOFXO-EKVD7    1

ANEXO

NSS               APELLIDOS Y NOMBRE    F.R.ALTA    F.E.ALTA    F.R.BAJA    F.E.BAJA
08 1468294322     ALI ASHAR             27-01-2026  27-01-2026
46 1166353302     AHMED SOHAIL                                  24-01-2026  24-01-2026

Firmado digitalmente por SELLO ELECTRÓNICO - TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL
Fecha: 05/02/2026 23:31:26
"""
    profile = get_notification_profile(sample_altas_bajas)
    if profile:
        print(f"✅ Perfil: {type(profile).__name__}")
        datos = profile.extract_data(sample_altas_bajas)
        for k, v in datos.items():
            if k == 'trabajadores':
                print(f"   trabajadores ({len(v)}):")
                for t in v:
                    print(f"      - NSS: {t['nss']} | {t['nombre']} | Alta: {t['fecha_real_alta']} | Baja: {t['fecha_real_baja']}")
            else:
                print(f"   {k}: {v}")
    else:
        print("⚠️  No detectado")


    print("\n" + "="*60)
    print("🧪 PRUEBA 3: Regularización RETA 2024 - Devolución (texto de muestra)")
    print("="*60)
    sample_regularizacion = """
MINISTERIO DE INCLUSIÓN, SEGURIDAD SOCIAL Y MIGRACIONES
TESORERÍA GENERAL DE LA SEGURIDAD SOCIAL

RESOLUCIÓN SOBRE BASE DE COTIZACIÓN DEFINITIVA DEL AÑO 2024 COMO PERSONA TRABAJADORA AUTÓNOMA

D./Dña. KATHERINNE DAYANA LOZANO BARBOSA
con número de afiliación 081459047087
y DNI/NIE Z0319916Z

La Tesorería General ha procedido a la determinación de su base de cotización definitiva del año 2024 es de 900,00 euros.
se han detectado diferencias de cotización a su favor, que ascienden a un total de 15,97 euros.

Id. CEA:          Fecha:      Código CEA:                              Página:
9A6FUK4938SY     04/02/2026  UOPSC-W34XS-XOKVA-MSXDM-HRYLJ-M5V5V    2

Dicho importe le será devuelto de oficio, antes del 30 de abril de 2026.

RESULTADO ANUAL DE LA REGULARIZACIÓN:       A DEVOLVER                15,97 €
"""
    profile = get_notification_profile(sample_regularizacion)
    if profile:
        print(f"✅ Perfil: {type(profile).__name__}")
        datos = profile.extract_data(sample_regularizacion)
        for k, v in datos.items():
            print(f"   {k}: {v}")
    else:
        print("⚠️  No detectado")



    print("\n" + "="*60)
    print("🧪 PRUEBA 4: Regularización RETA 2024 - Ingreso (texto de muestra)")
    print("="*60)
    sample_reta_ingreso = """
Hola, KAUR MANINDER --:

RESOLUCION SOBRE BASE DE COTIZACION DEFINITIVA DEL ANO 2024 COMO PERSONA TRABAJADORA AUTONOMA

D./Dna. KAUR MANINDER ---
con numero de afiliacion 081411429282
y DNI/NIE Y6674238C

el importe de la base de cotizacion definitiva del ano 2024 es de 1.078,43 euros.
diferencias de cotizacion que ascienden a un total de 442,56 euros.

Fecha de resolucion: 04/02/2026

RESULTADO ANUAL DE LA REGULARIZACION:       A INGRESAR                442,56

DOCUMENTO DE PAGO BOLETIN PAGO REGULARIZACION
Entidad Financiera ingreso: BANCO BILBAO VIZCAYA ARGENTARIA
Cuenta de ingreso: ES15  0182  6035  4702  0156  6343
NIF deudor: Y6674238C     No de referencia: 750826013467317
Total a ingresar: 442,56

Id. CEA:          Fecha:      Codigo CEA:                              Pagina:
992FWP4972JS     04/02/2026  65KDV-DACYK-5XTTC-TVHQB-HVQCE-A66KT    1
"""
    profile = get_notification_profile(sample_reta_ingreso)
    if profile:
        print(f"✅ Perfil: {type(profile).__name__}")
        datos = profile.extract_data(sample_reta_ingreso)
        for k, v in datos.items():
            print(f"   {k}: {v}")
    else:
        print("⚠️  No detectado")



if __name__ == "__main__":


    # 1. Probar con PDFs reales si existen
    pdf_dir = os.path.join(os.path.dirname(__file__), 'test_pdfs')
    pdf_files = glob.glob(os.path.join(pdf_dir, '*.pdf'))

    if pdf_files:
        print(f"\n📂 Encontrados {len(pdf_files)} PDFs en test_pdfs/")
        for pdf_path in sorted(pdf_files):
            probar_pdf(pdf_path)
    else:
        print(f"\n⚠️  No hay PDFs en {pdf_dir}")
        print("   Ejecutando pruebas con textos de muestra...\n")
        probar_texto_muestra()
