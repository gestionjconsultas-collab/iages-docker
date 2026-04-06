"""
Redis Pub/Sub para notificaciones desde Celery a Flask
Permite que las tareas de Celery envíen notificaciones en tiempo real sin importar socketio
"""
import redis
import json
import os
from typing import Dict, Any

# Configuración de Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

def get_redis_client():
    """Obtiene un cliente Redis"""
    return redis.from_url(REDIS_URL, decode_responses=True)

def publish_notification(channel: str, data: Dict[str, Any]):
    """
    Publica una notificación en un canal de Redis
    
    Args:
        channel: Nombre del canal (ej: 'nomina_progress', 'nomina_completed')
        data: Datos a enviar (dict que se convertirá a JSON)
    """
    try:
        r = get_redis_client()
        message = json.dumps(data)
        r.publish(channel, message)
        print(f"📢 Notificación publicada en canal '{channel}': {data}")
        return True
    except Exception as e:
        print(f"❌ Error publicando notificación: {e}")
        return False

def publish_task_progress(task_id: str, current: int, total: int, status: str = None, **kwargs):
    """
    Publica progreso de una tarea
    
    Args:
        task_id: ID de la tarea de Celery
        current: Progreso actual
        total: Total de items
        status: Mensaje de estado
        **kwargs: Datos adicionales (user_id, gestoria_id, etc.)
    """
    percentage = (current / total) * 100 if total > 0 else 0
    
    data = {
        'task_id': task_id,
        'current': current,
        'total': total,
        'percentage': round(percentage, 1),
        'status': status or f'Procesando {current} de {total}...',
        **kwargs
    }
    
    return publish_notification('task_progress', data)

def publish_task_completed(task_id: str, result: Dict[str, Any], **kwargs):
    """
    Publica finalización de una tarea
    
    Args:
        task_id: ID de la tarea de Celery
        result: Resultado de la tarea
        **kwargs: Datos adicionales (user_id, gestoria_id, etc.)
    """
    data = {
        'task_id': task_id,
        'result': result,
        **kwargs
    }
    
    return publish_notification('task_completed', data)

def publish_task_error(task_id: str, error: str, **kwargs):
    """
    Publica error de una tarea
    
    Args:
        task_id: ID de la tarea de Celery
        error: Mensaje de error
        **kwargs: Datos adicionales (user_id, gestoria_id, etc.)
    """
    data = {
        'task_id': task_id,
        'error': error,
        **kwargs
    }
    
    return publish_notification('task_error', data)

# Funciones específicas para nóminas
def publish_nomina_progress(task_id: str, current: int, total: int, user_id: int, 
                            nif: str = None, status: str = None):
    """Publica progreso de procesamiento de nóminas"""
    return publish_task_progress(
        task_id=task_id,
        current=current,
        total=total,
        status=status,
        user_id=user_id,
        nif=nif,
        type='nomina_progress'
    )

def publish_nomina_completed(task_id: str, user_id: int, total_empresas: int, 
                             total_trabajadores: int, periodo: str, **kwargs):
    """Publica finalización de procesamiento de nóminas"""
    result = {
        'total_empresas': total_empresas,
        'total_trabajadores': total_trabajadores,
        'periodo': periodo
    }
    # Combinar con cualquier dato extra (como detalles o empresas_clasificadas)
    result.update(kwargs)
    
    return publish_task_completed(
        task_id=task_id,
        result=result,
        user_id=user_id,
        type='nomina_completed'
    )

# Funciones específicas para seguros sociales
def publish_seguro_progress(task_id: str, current: int, total: int, user_id: int, 
                            empresa: str = None, status: str = None):
    """Publica progreso de procesamiento de seguros sociales"""
    return publish_task_progress(
        task_id=task_id,
        current=current,
        total=total,
        status=status,
        user_id=user_id,
        empresa=empresa,
        type='seguro_progress'
    )

def publish_seguro_completed(task_id: str, user_id: int, total_empresas: int, 
                             total_trabajadores: int, periodo: str, **kwargs):
    """Publica finalización de procesamiento de seguros sociales"""
    result = {
        'total_empresas': total_empresas,
        'total_trabajadores': total_trabajadores,
        'periodo': periodo
    }
    # Combinar con cualquier dato extra (como detalles o rlc_procesados)
    result.update(kwargs)
    
    return publish_task_completed(
        task_id=task_id,
        result=result,
        user_id=user_id,
        type='seguro_completed'
    )
