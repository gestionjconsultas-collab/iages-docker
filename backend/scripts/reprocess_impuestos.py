# backend/scripts/reprocess_impuestos.py
"""
Script para disparar el reprocesamiento global de la categoría 'Impuestos'
y monitorizar el progreso en tiempo real.
"""
import os
import sys
import time
import logging

# Añadir el directorio base al path
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from extensions import db
from models import Gestoria, User
from celery_tasks_admin import reprocesar_categoria_global_task
from celery.result import AsyncResult
from celery_worker import celery

def run():
    with app.app_context():
        print("🔍 Buscando gestoría y usuario administrador...")
        
        # 1. Obtener la gestoría (ID 1 es la que tiene los documentos)
        gestoria = Gestoria.query.filter(Gestoria.nombre.ilike('%Victor%')).first()
        if not gestoria:
            gestoria = Gestoria.query.get(1)
            
        if not gestoria:
            print("❌ Error: No se encontró ninguna gestoría en la base de datos.")
            return

        # 2. Obtener un usuario administrador para la auditoría
        admin = User.query.filter_by(gestoria_id=gestoria.id, is_super_admin=True).first()
        if not admin:
            admin = User.query.filter_by(gestoria_id=gestoria.id).first()
            
        if not admin:
            print("❌ Error: No se encontró ningún usuario para asociar a la tarea.")
            return

        print(f"🚀 Iniciando reprocesamiento de 'Impuestos' para {gestoria.nombre} (ID: {gestoria.id})")
        print(f"👤 Solicitado por: {admin.nombre} ({admin.email})")
        
        # 3. Disparar la tarea
        task = reprocesar_categoria_global_task.delay(gestoria.id, 'Impuestos', admin.id)
        task_id = task.id
        print(f"\n✅ Tarea enviada a Celery. Task ID: {task_id}")
        print("⏳ Monitorizando progreso (Ctrl+C para salir, la tarea seguirá ejecutándose en el servidor)...\n")
        
        # 4. Bucle de monitorización
        try:
            while True:
                res = AsyncResult(task_id, app=celery)
                state = res.state
                info = res.info or {}
                
                if state == 'PROGRESS':
                    current = info.get('current', 0)
                    total = info.get('total', 0)
                    progreso = (current / total * 100) if total > 0 else 0
                    print(f"\r📑 PROGRESO: [{current}/{total}] {progreso:.1f}% completo...", end="", flush=True)
                
                elif state == 'SUCCESS':
                    print(f"\n\n✨ TAREA COMPLETADA EXITOSAMENTE!")
                    print(f"✅ Procesados: {info.get('procesados', 0)}")
                    print(f"❌ Errores: {info.get('errores', 0)}")
                    break
                    
                elif state == 'FAILURE':
                    print(f"\n\n❌ TAREA FALLIDA")
                    print(f"Error: {res.result}")
                    break
                
                elif state == 'PENDING':
                    print("\r🕒 Estado: Esperando en cola...", end="", flush=True)
                
                else:
                    print(f"\r🔄 Estado: {state}...", end="", flush=True)
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Monitorización interrumpida por el usuario.")
            print(f"ℹ️ La tarea {task_id} continúa ejecutándose en segundo plano.")
            print(f"🔗 Puedes consultar el estado en el Dashboard o vía API.")

if __name__ == "__main__":
    run()
