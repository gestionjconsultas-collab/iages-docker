#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script standalone para verificar certificados en Saltra
No requiere cargar la aplicación completa
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from constants import NotificationTypes

# Cargar variables de entorno
load_dotenv()

def obtener_certificados_saltra():
    """
    Consulta la API de Saltra para obtener certificados registrados
    """
    print("\n" + "="*70)
    print("🔍 VERIFICACIÓN DE CERTIFICADOS SALTRA")
    print("="*70 + "\n")
    
    # Credenciales
    email = os.getenv('SALTRA_EMAIL')
    password = os.getenv('SALTRA_PASSWORD')
    cert_secret = os.getenv('SALTRA_CERT_SECRET')
    
    if not all([email, password, cert_secret]):
        print("❌ Error: Credenciales de Saltra no configuradas en .env")
        print("   Necesitas:")
        print("   - SALTRA_EMAIL")
        print("   - SALTRA_PASSWORD")
        print("   - SALTRA_CERT_SECRET")
        return
    
    print(f"📧 Email: {email}")
    print(f"🔑 Cert-Secret: {cert_secret[:10]}...{cert_secret[-10:]}\n")
    
    # 1. Login
    print("🔐 Iniciando sesión en Saltra...")
    try:
        response = requests.post(
            "https://api.saltra.es/api/v4/auth/login",
            json={"email": email, "password": password},
            timeout=30
        )
        
        data = response.json()
        
        if not data.get(NotificationTypes.SUCCESS):
            print(f"❌ Error en login: {data.get('message')}")
            return
        
        token = data["data"]["access_token"]
        expires = data["data"]["expires_in"]
        print(f"✅ Login exitoso")
        print(f"   Token expira: {expires}\n")
        
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        return
    
    # 2. Obtener certificados
    print("📋 Obteniendo certificados registrados...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Cert-Secret": cert_secret,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            "https://api.saltra.es/api/v4/office/configuration/certificates",
            headers=headers,
            timeout=30
        )
        
        data = response.json()
        
        if not data.get(NotificationTypes.SUCCESS):
            print(f"❌ Error obteniendo certificados: {data.get('message')}")
            return
        
        certificados = data.get("data", [])
        print(f"✅ {len(certificados)} certificados encontrados\n")
        
        if not certificados:
            print("⚠️  No hay certificados registrados en Saltra")
            print("   Debes registrar certificados para poder recibir notificaciones DEHU")
            return
        
        # 3. Mostrar certificados
        print("="*70)
        print("CERTIFICADOS REGISTRADOS")
        print("="*70 + "\n")
        
        for i, cert in enumerate(certificados, 1):
            print(f"📜 Certificado #{i}")
            print(f"   Alias: {cert.get('alias', 'N/A')}")
            print(f"   NIF: {cert.get('nif', 'N/A')}")
            print(f"   Tipo: {cert.get('tipo', 'Autorizado RED')}")
            
            # Estado
            activo = cert.get('activo', cert.get('active', True))
            estado = "🟢 Activo" if activo else "🔴 Inactivo"
            print(f"   Estado: {estado}")
            
            # Fechas
            if cert.get('creacion'):
                print(f"   Creación: {cert.get('creacion')}")
            if cert.get('expiracion'):
                print(f"   Expiración: {cert.get('expiracion')}")
            
            # Emisor
            if cert.get('emitido_por'):
                print(f"   Emisor: {cert.get('emitido_por')}")
            
            print()
        
        # 4. Resumen
        print("="*70)
        print("RESUMEN")
        print("="*70)
        print(f"  Total certificados: {len(certificados)}")
        
        activos = [c for c in certificados if c.get('activo', c.get('active', True))]
        print(f"  🟢 Activos: {len(activos)}")
        print(f"  🔴 Inactivos: {len(certificados) - len(activos)}")
        
        # Listar NIFs
        nifs = [c.get('nif') for c in certificados if c.get('nif')]
        if nifs:
            print(f"\n  NIFs registrados:")
            for nif in nifs:
                print(f"    • {nif}")
        
        print("\n✅ Estos NIFs pueden recibir notificaciones DEHU")
        print("⚠️  Empresas con otros NIFs NO recibirán notificaciones\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    obtener_certificados_saltra()
