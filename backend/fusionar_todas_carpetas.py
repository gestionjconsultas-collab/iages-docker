# backend/fusionar_todas_carpetas.py
"""
Script para fusionar TODAS las carpetas de empresas de storage/ a storage/principal/
Incluye tanto empresa_X como carpetas con nombres de empresas
"""

import os
import shutil
import re
from app import app, db
from models import Empresa

# Carpetas del sistema que NO son empresas
CARPETAS_SISTEMA = {'principal', 'logos', 'gestoria-prueba', 'gestoriaprueba1', 'gestoria-testing', '__INBOX_NO_CLASIFICADOS'}

def fusionar_todas_carpetas(dry_run=True):
    """
    Fusiona todas las carpetas de empresas de storage/ a storage/principal/
    
    Args:
        dry_run: Si True, solo muestra lo que haría sin ejecutar
    """
    
    with app.app_context():
        ruta_storage = app.config.get('RUTA_RAIZ_NOTIFICACIONES', r'C:\Users\Gestion\Documents\Notificaciones')
        ruta_principal = os.path.join(ruta_storage, 'principal')
        
        print(f"📂 Storage: {ruta_storage}")
        print(f"📁 Principal: {ruta_principal}")
        print("="*80)
        
        if not os.path.exists(ruta_storage):
            print(f"❌ No existe: {ruta_storage}")
            return
        
        if not os.path.exists(ruta_principal):
            print(f"❌ No existe: {ruta_principal}")
            return
        
        # Buscar TODAS las carpetas que no sean del sistema
        carpetas_a_mover = []
        for item in os.listdir(ruta_storage):
            item_path = os.path.join(ruta_storage, item)
            if os.path.isdir(item_path) and item not in CARPETAS_SISTEMA:
                carpetas_a_mover.append(item)
        
        if not carpetas_a_mover:
            print("ℹ️  No se encontraron carpetas de empresas")
            return
        
        print(f"📁 Encontradas {len(carpetas_a_mover)} carpetas de empresas\n")
        
        archivos_movidos = 0
        carpetas_procesadas = 0
        errores = 0
        
        for carpeta_nombre in sorted(carpetas_a_mover):
            ruta_origen = os.path.join(ruta_storage, carpeta_nombre)
            ruta_destino = os.path.join(ruta_principal, carpeta_nombre)
            
            print(f"\n{'='*80}")
            print(f"📦 {carpeta_nombre}")
            print(f"   Origen:  storage/{carpeta_nombre}/")
            print(f"   Destino: storage/principal/{carpeta_nombre}/")
            print(f"{'='*80}")
            
            # Verificar si ya existe en destino
            if os.path.exists(ruta_destino):
                print(f"   ℹ️  Carpeta destino ya existe - FUSIONANDO contenido")
                
                # Fusionar contenido
                archivos_fusionados = fusionar_directorios(ruta_origen, ruta_destino, dry_run)
                archivos_movidos += archivos_fusionados
                
                if archivos_fusionados > 0:
                    carpetas_procesadas += 1
                    print(f"   ✅ {archivos_fusionados} archivos fusionados")
                
                # Eliminar carpeta origen si está vacía
                if not dry_run:
                    try:
                        if esta_vacia_recursivo(ruta_origen):
                            shutil.rmtree(ruta_origen)
                            print(f"   🗑️  Carpeta origen eliminada (vacía)")
                    except Exception as e:
                        print(f"   ⚠️  No se pudo eliminar carpeta vacía: {e}")
            else:
                # Mover carpeta completa
                print(f"   📁 Carpeta nueva - MOVIENDO completa")
                
                if not dry_run:
                    try:
                        shutil.move(ruta_origen, ruta_destino)
                        print(f"   ✅ Carpeta movida")
                        carpetas_procesadas += 1
                    except Exception as e:
                        print(f"   ❌ ERROR: {e}")
                        errores += 1
                else:
                    print(f"   🔍 DRY RUN - Se movería")
                    carpetas_procesadas += 1
        
        # Resumen
        print("\n" + "="*80)
        print("📊 RESUMEN")
        print("="*80)
        print(f"📁 Carpetas procesadas:   {carpetas_procesadas}")
        print(f"📄 Archivos fusionados:   {archivos_movidos}")
        print(f"❌ Errores:               {errores}")
        print("="*80)
        
        if dry_run:
            print("\n⚠️  MODO PREVISUALIZACIÓN - No se realizaron cambios")
            print("   Para ejecutar: python fusionar_todas_carpetas.py --execute")
        else:
            print("\n✅ CARPETAS FUSIONADAS")
            print("\n📋 SIGUIENTE PASO:")
            print("   python actualizar_rutas_bd.py --execute")

def fusionar_directorios(origen, destino, dry_run=True):
    """
    Fusiona recursivamente el contenido de origen en destino
    Retorna el número de archivos movidos
    """
    archivos_movidos = 0
    
    for item in os.listdir(origen):
        ruta_item_origen = os.path.join(origen, item)
        ruta_item_destino = os.path.join(destino, item)
        
        if os.path.isdir(ruta_item_origen):
            # Es un directorio - fusionar recursivamente
            if not dry_run:
                os.makedirs(ruta_item_destino, exist_ok=True)
            archivos_movidos += fusionar_directorios(ruta_item_origen, ruta_item_destino, dry_run)
        else:
            # Es un archivo
            if os.path.exists(ruta_item_destino):
                print(f"      ⚠️  {item} - Ya existe")
            else:
                print(f"      📄 {item}")
                if not dry_run:
                    try:
                        os.makedirs(os.path.dirname(ruta_item_destino), exist_ok=True)
                        shutil.move(ruta_item_origen, ruta_item_destino)
                        archivos_movidos += 1
                    except Exception as e:
                        print(f"         ❌ ERROR: {e}")
                else:
                    archivos_movidos += 1
    
    return archivos_movidos

def esta_vacia_recursivo(directorio):
    """Verifica si un directorio está vacío recursivamente"""
    for item in os.listdir(directorio):
        item_path = os.path.join(directorio, item)
        if os.path.isdir(item_path):
            if not esta_vacia_recursivo(item_path):
                return False
        else:
            return False
    return True

if __name__ == '__main__':
    import sys
    
    dry_run = '--execute' not in sys.argv
    
    print("\n" + "="*80)
    print("🔄 FUSIONAR TODAS LAS CARPETAS: storage/* → storage/principal/")
    print("="*80 + "\n")
    
    if dry_run:
        print("🔍 MODO PREVISUALIZACIÓN")
        print("   Se mostrará qué se movería sin hacer cambios")
        print("   Para ejecutar: python fusionar_todas_carpetas.py --execute\n")
    else:
        print("⚠️  MODO EJECUCIÓN")
        print("   Se moverán TODAS las carpetas de empresas a principal/\n")
        confirmacion = input("¿Estás seguro de continuar? (escribe 'SI' para confirmar): ")
        if confirmacion.upper() != 'SI':
            print("\n❌ Cancelado")
            sys.exit(0)
        print()
    
    fusionar_todas_carpetas(dry_run=dry_run)
    
    print("\n✅ Proceso finalizado\n")
