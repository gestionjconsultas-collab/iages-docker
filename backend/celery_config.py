"""
Configuración de Celery para SpainFlow
Tareas programadas para alertas automáticas y mantenimiento
"""
from celery import Celery
from celery.schedules import crontab
import os

# Configuración de Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Crear instancia de Celery
celery = Celery('iages')

# Configuración
celery.conf.update(
    broker_url=REDIS_URL,
    result_backend=REDIS_URL,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Madrid',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos máximo por tarea
)

# Programación de tareas periódicas
celery.conf.beat_schedule = {
    # Verificar límites cada hora
    'verificar-limites-cada-hora': {
        'task': 'tasks.verificar_limites_gestorias',
        'schedule': crontab(minute=0),  # Cada hora en punto
    },
    
    # Limpiar alertas antiguas diariamente a las 3 AM
    'limpiar-alertas-diario': {
        'task': 'tasks.limpiar_alertas_antiguas',
        'schedule': crontab(hour=3, minute=0),  # 3:00 AM
    },
    
    # Generar reporte de uso mensual (primer día del mes a las 6 AM)
    'reporte-uso-mensual': {
        'task': 'tasks.generar_reporte_uso_mensual',
        'schedule': crontab(day_of_month=1, hour=6, minute=0),
    },
    
    # Actualizar métricas de uso cada 15 minutos
    'actualizar-metricas-uso': {
        'task': 'tasks.actualizar_metricas_uso',
        'schedule': crontab(minute='*/15'),  # Cada 15 minutos
    },
    
    # ==========================================
    # TAREAS DE FACTURACIÓN
    # ==========================================
    
    # Generar facturas mensuales (día 1 a las 00:00)
    'generar-facturas-mensuales': {
        'task': 'generar_facturas_mensuales',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),
    },
    
    # Calcular uso mensual (diario a las 2 AM)
    'calcular-uso-mensual': {
        'task': 'calcular_uso_mensual_todas',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Verificar facturas vencidas (diario a las 3 AM)
    'verificar-facturas-vencidas': {
        'task': 'verificar_facturas_vencidas',
        'schedule': crontab(hour=3, minute=0),
    },
    
    # Recordatorios de facturas (diario a las 10 AM)
    'recordatorios-facturas': {
        'task': 'recordatorio_facturas_proximas_vencer',
        'schedule': crontab(hour=10, minute=0),
    },
}

# Configuración adicional
celery.conf.worker_prefetch_multiplier = 1
celery.conf.worker_max_tasks_per_child = 1000

if __name__ == '__main__':
    celery.start()
