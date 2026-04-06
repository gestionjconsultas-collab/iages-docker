"""
Endpoint para consultar estado de tareas Celery en tiempo real
"""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from celery.result import AsyncResult
from celery_worker import celery

task_status_bp = Blueprint('task_status', __name__)


@task_status_bp.route('/api/task/<task_id>/status', methods=['GET'])
@login_required
def get_task_status(task_id):
    """
    Obtiene el estado actual de una tarea Celery
    
    Returns:
        {
            'task_id': str,
            'state': str,  # PENDING, PROGRESS, SUCCESS, FAILURE
            'info': dict   # Metadata específica del estado
        }
    """
    try:
        # Obtener resultado de Celery
        task_result = AsyncResult(task_id, app=celery)
        
        response = {
            'task_id': task_id,
            'state': task_result.state,
            'info': {}
        }
        
        if task_result.state == 'PENDING':
            # Tarea aún no ha empezado
            response['info'] = {
                'status': 'En cola, esperando procesamiento...',
                'percentage': 0
            }
        
        elif task_result.state == 'PROGRESS':
            # Tarea en progreso - info viene del update_state en tasks_nominas.py
            response['info'] = task_result.info or {}
            
        elif task_result.state == 'SUCCESS':
            # Tarea completada exitosamente
            response['info'] = task_result.result or {}
            
        elif task_result.state == 'FAILURE':
            # Tarea falló
            response['info'] = {
                'status': 'Error en procesamiento',
                'error': str(task_result.info)
            }
        
        else:
            # Otros estados (RETRY, REVOKED, etc.)
            response['info'] = {
                'status': f'Estado: {task_result.state}'
            }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'task_id': task_id,
            'state': 'UNKNOWN'
        }), 500


@task_status_bp.route('/api/task/<task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id):
    """
    Cancela una tarea Celery en ejecución
    """
    try:
        task_result = AsyncResult(task_id, app=celery)
        
        if task_result.state in ['PENDING', 'PROGRESS']:
            # Revocar tarea
            celery.control.revoke(task_id, terminate=True)
            
            return jsonify({
                'success': True,
                'message': 'Tarea cancelada exitosamente'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'No se puede cancelar tarea en estado {task_result.state}'
            }), 400
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@task_status_bp.route('/api/tasks/active', methods=['GET'])
@login_required
def get_active_tasks():
    """
    Obtiene todas las tareas activas del usuario actual
    """
    try:
        # Obtener tareas activas de Celery
        inspect = celery.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return jsonify({
                'active_tasks': [],
                'count': 0
            })
        
        # Flatten el diccionario de workers
        all_tasks = []
        for worker_tasks in active_tasks.values():
            all_tasks.extend(worker_tasks)
        
        # Filtrar solo tareas de procesamiento
        processing_tasks = [
            {
                'task_id': task['id'],
                'name': task['name'],
                'started': task.get('time_start'),
                'args': task.get('args', []),
            }
            for task in all_tasks
            if task['name'] in [
                'tasks_nominas.procesar_nominas_async',
                'tasks_seguros_sociales.procesar_seguros_async',
                'reprocesar_categoria_global_task'
            ]
        ]
        
        return jsonify({
            'active_tasks': processing_tasks,
            'count': len(processing_tasks)
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'active_tasks': [],
            'count': 0
        })
