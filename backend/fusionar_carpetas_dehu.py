# backend/fusionar_carpetas_dehu.py
"""
Script para fusionar contenido de empresa_X/DEHU/ a principal/NOMBRE_EMPRESA/Por Procesar/DEHU_*
"""

import os
import shutil
import re
from app import app, db
from models import Empresa

def fusionar_carpetas_dehu(dry_run=True):
    """
    Fusiona archivos de empresa_X/DEHU/ a principal/NOMBRE_EMPRESA/Por Procesar/DEHU_*
    
    Args:
        dry_run: Si True, solo muestra lo que haría sin ejecutar
    """
    
    with app.app_context():
        ruta_storage = app.config.get('RUTA_RAIZ_NOTIFICACIONES', r'C:\Users\Gestion\Documents\Notificaciones')
        ruta_principal = os.path.join(ruta_storage, 'principal')
        
        print(f"📂 Storage: {ruta_storage}")
        print(f"📁 Principal: {ruta_principal}")
        print("="*80)
        
        # Buscar carpetas empresa_*
        carpetas_empresa = []
        for item in os.listdir(ruta_storage):
            item_path = os.path.join(ruta_storage, item)
            if os.path.isdir(item_path) and item.startswith('empresa_'):
                carpetas_empresa.append(item)
        
        if not carpetas_empresa:
            print("ℹ️  No se encontraron carpetas 'empresa_*'")
            return
        
        print(f"📁 Encontradas {len(carpetas_empresa)} carpetas 'empresa_*'\n")
        
        archivos_movidos = 0
        carpetas_procesadas = 0
        errores = 0
        
        for carpeta_nombre in sorted(carpetas_empresa, key=lambda x: int(re.search(r'\d+', x).group())):
            # Extraer ID
            match = re.search(r'empresa_(\d+)', carpeta_nombre)
            if not match:
                continue
            
            empresa_id = int(match.group(1))
            
            # Buscar empresa
            empresa = Empresa.query.get(empresa_id)
            if not empresa:
                print(f"⚠️ {carpeta_nombre} - Empresa ID {empresa_id} no encontrada")
                errores += 1
                continue
            
            # Sanitizar nombre
            nombre_empresa_safe = re.sub(r'[^\w\s-]', '', empresa.nombre).strip().replace('_', ' ')
            
            # Rutas
            ruta_origen_base = os.path.join(ruta_storage, carpeta_nombre)
            ruta_destino_base = os.path.join(ruta_principal, nombre_empresa_safe)
            
            print(f"\n{'='*80}")
            print(f"📦 {carpeta_nombre} → {nombre_empresa_safe}")
            print(f"{'='*80}")
            
            # Buscar carpeta DEHU en origen
            ruta_dehu_origen = os.path.join(ruta_origen_base, 'DEHU')
            
            if not os.path.exists(ruta_dehu_origen):
                print(f"   ⚠️ No existe carpeta DEHU en origen")
                continue
            
            # Procesar subcarpetas (Documentos, Resguardos)
            archivos_en_carpeta = 0
            
            for subcarpeta in ['Documentos', 'Resguardos']:
                ruta_subcarpeta_origen = os.path.join(ruta_dehu_origen, subcarpeta)
                
                if not os.path.exists(ruta_subcarpeta_origen):
                    continue
                
                archivos = [f for f in os.listdir(ruta_subcarpeta_origen) if f.endswith('.pdf')]
                
                if not archivos:
                    continue
                
                # Ruta destino: principal/NOMBRE/Por Procesar/DEHU_Documentos
                ruta_subcarpeta_destino = os.path.join(
                    ruta_destino_base,
                    'Por Procesar',
                    f'DEHU_{subcarpeta}'
                )
                
                print(f"\n   📁 DEHU/{subcarpeta}: {len(archivos)} archivos")
                print(f"      Destino: Por Procesar/DEHU_{subcarpeta}/")
                
                for archivo in archivos:
                    ruta_archivo_origen = os.path.join(ruta_subcarpeta_origen, archivo)
                    ruta_archivo_destino = os.path.join(ruta_subcarpeta_destino, archivo)
                    
                    # Verificar si ya existe
                    if os.path.exists(ruta_archivo_destino):
                        print(f"         ⚠️ {archivo} - Ya existe")
                        continue
                    
                    print(f"         📄 {archivo}")
                    
                    if not dry_run:
                        try:
                            # Crear carpeta destino
                            os.makedirs(ruta_subcarpeta_destino, exist_ok=True)
                            
                            # Mover archivo
                            shutil.move(ruta_archivo_origen, ruta_archivo_destino)
                            archivos_movidos += 1
                            archivos_en_carpeta += 1
                            
                        except Exception as e:
                            print(f"            ❌ ERROR: {e}")
                            errores += 1
                    else:
                        archivos_movidos += 1
                        archivos_en_carpeta += 1
            
            if archivos_en_carpeta > 0:
                carpetas_procesadas += 1
                
                if not dry_run:
                    # Intentar eliminar carpetas vacías
                    try:
                        for subcarpeta in ['Documentos', 'Resguardos']:
                            ruta_sub = os.path.join(ruta_dehu_origen, subcarpeta)
                            if os.path.exists(ruta_sub) and not os.listdir(ruta_sub):
                                os.rmdir(ruta_sub)
                        
                        if os.path.exists(ruta_dehu_origen) and not os.listdir(ruta_dehu_origen):
                            os.rmdir(ruta_dehu_origen)
                        
                        if os.path.exists(ruta_origen_base) and not os.listdir(ruta_origen_base):
                            os.rmdir(ruta_origen_base)
                            print(f"\n   🗑️ Carpeta {carpeta_nombre} eliminada (vacía)")
                    except Exception as e:
                        print(f"   ⚠️ No se pudo eliminar carpeta vacía: {e}")
        
        # Resumen
        print("\n" + "="*80)
        print("📊 RESUMEN")
        print("="*80)
        print(f"📁 Carpetas procesadas:   {carpetas_procesadas}")
        print(f"📄 Archivos movidos:      {archivos_movidos}")
        print(f"❌ Errores:               {errores}")
        print("="*80)
        
        if dry_run:
            print("\n⚠️  MODO PREVISUALIZACIÓN - No se realizaron cambios")
            print("   Para ejecutar: python fusionar_carpetas_dehu.py --execute")
        else:
            print("\n✅ ARCHIVOS MOVIDOS")
            print("\n📋 SIGUIENTE PASO:")
            print("   python actualizar_rutas_bd.py --execute")

if __name__ == '__main__':
    import sys
    
    dry_run = '--execute' not in sys.argv
    
    print("\n" + "="*80)
    print("🔄 FUSIONAR: empresa_*/DEHU/ → principal/*/Por Procesar/DEHU_*")
    print("="*80 + "\n")
    
    if dry_run:
        print("🔍 MODO PREVISUALIZACIÓN")
        print("   Se mostrará qué archivos se moverían sin hacer cambios")
        print("   Para ejecutar: python fusionar_carpetas_dehu.py --execute\n")
    else:
        print("⚠️  MODO EJECUCIÓN")
        print("   Se moverán los archivos DEHU\n")
        confirmacion = input("¿Estás seguro de continuar? (escribe 'SI' para confirmar): ")
        if confirmacion.upper() != 'SI':
            print("\n❌ Cancelado")
            sys.exit(0)
        print()
    
    fusionar_carpetas_dehu(dry_run=dry_run)
    
    print("\n✅ Proceso finalizado\n")
