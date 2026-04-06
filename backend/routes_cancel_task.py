"""
Endpoint para cancelar tareas Celery
"""
from flask import Blueprint, jsonify
from flask_login import login_required
from celery_worker import celery
import os
import shutil
import tempfile

cancel_task_bp = Blueprint('cancel_task', __name__)

@cancel_task_bp.route('/api/cancel-task/<task_id>', methods=['POST'])
@login_required
def cancel_task(task_id):
    """
    Cancela una tarea Celery en ejecución
    
    Args:
        task_id: ID de la tarea a cancelar
    """
    try:
        # Revocar tarea en Celery
        celery.control.revoke(task_id, terminate=True, signal='SIGKILL')
        
        # Limpiar archivos temporales asociados al task_id
        temp_base = tempfile.gettempdir()
        cleaned_dirs = 0
        
        try:
            for item in os.listdir(temp_base):
                item_path = os.path.join(temp_base, item)
                # Buscar directorios que puedan estar relacionados con esta tarea
                if os.path.isdir(item_path) and (task_id in item or 'tmp' in item):
                    try:
                        shutil.rmtree(item_path, ignore_errors=True)
                        cleaned_dirs += 1
                    except Exception as e:
                        print(f"⚠️ No se pudo limpiar {item_path}: {e}")
        except Exception as e:
            print(f"⚠️ Error limpiando archivos temporales: {e}")
        
        print(f"🛑 Tarea {task_id} cancelada. {cleaned_dirs} directorios temporales limpiados.")
        
        return jsonify({
            'success': True,
            'message': 'Tarea cancelada correctamente',
            'cleaned_dirs': cleaned_dirs
        })
        
    except Exception as e:
        print(f"❌ Error cancelando tarea {task_id}: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al cancelar: {str(e)}'
        }), 500
