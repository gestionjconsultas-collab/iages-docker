"""
Redis Listener para Flask - Escucha notificaciones de Celery y las reenvía vía SocketIO
"""
import redis
import json
from flask import current_app

class RedisListener:
    """Escucha mensajes de Redis pub/sub y los reenvía vía SocketIO"""
    
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.running = False
        self.worker_thread = None
        
        if app and socketio:
            self.init_app(app, socketio)
    
    def init_app(self, app, socketio):
        """Inicializa el listener con la app Flask y SocketIO"""
        self.app = app
        self.socketio = socketio
        
        # Obtener URL de Redis desde config
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()
        
        # Suscribirse a los canales
        self.pubsub.subscribe(**{
            'task_progress': self._handle_pubsub_message,
            'task_completed': self._handle_pubsub_message,
            'task_error': self._handle_pubsub_message
        })
        
        print("✅ Redis Listener inicializado y suscrito a canales")
    
    def start(self):
        """Inicia la escucha usando start_background_task (compatible con gevent y threading)"""
        if self.running:
            print("⚠️ Redis Listener ya está corriendo")
            return

        if not self.pubsub:
            print("❌ No se puede iniciar Redis Listener: pubsub no inicializado")
            return

        self.running = True
        # ✅ start_background_task usa gevent.spawn en modo gevent, threading.Thread en modo threading
        # Evita incompatibilidades entre redis-py threads y gevent greenlets
        self.socketio.start_background_task(self._listen_loop)
        print("🎧 Redis Listener iniciado (start_background_task)")

    def _listen_loop(self):
        """Loop de escucha compatible con gevent y threading"""
        try:
            for message in self.pubsub.listen():
                if not self.running:
                    break
                if message['type'] == 'message':
                    self._handle_pubsub_message(message)
        except Exception as e:
            print(f"❌ Redis Listener loop terminado: {e}")

    def stop(self):
        """Detiene la escucha"""
        self.running = False
        if self.pubsub:
            self.pubsub.unsubscribe()
        print("🛑 Redis Listener detenido")
    
    def _handle_pubsub_message(self, message):
        """Callback para mensajes de Redis pub/sub"""
        if message['type'] != 'message':
            return
            
        try:
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Ejecutar procesamiento dentro del contexto de la app
            with self.app.app_context():
                self._handle_message(channel, data)
                
        except Exception as e:
            print(f"❌ Error procesando mensaje de Redis: {e}")
    
    def _handle_message(self, channel, data):
        """Procesa un mensaje según su canal"""
        
        # Extraer información común
        task_id = data.get('task_id')
        user_id = data.get('user_id')
        task_type = data.get('type', channel)
        
        # Determinar el room de SocketIO
        room = f'user_{user_id}' if user_id else None
        
        # Emitir vía SocketIO según el tipo
        if channel == 'task_progress':
            self._emit_progress(task_type, data, room)
        elif channel == 'task_completed':
            self._emit_completed(task_type, data, room)
        elif channel == 'task_error':
            self._emit_error(task_type, data, room)
    
    def _emit_progress(self, task_type, data, room):
        """Emite progreso de tarea"""
        if task_type == 'nomina_progress':
            self.socketio.emit('nomina_progress', {
                'task_id': data.get('task_id'),
                'current': data.get('current'),
                'total': data.get('total'),
                'percentage': data.get('percentage'),
                'nif': data.get('nif'),
                'status': data.get('status')
            }, room=room)
            print(f"📤 Progreso de nómina emitido a {room}")
            
        elif task_type == 'seguro_progress':
            self.socketio.emit('seguro_progress', {
                'task_id': data.get('task_id'),
                'current': data.get('current'),
                'total': data.get('total'),
                'percentage': data.get('percentage'),
                'empresa': data.get('empresa'),
                'status': data.get('status')
            }, room=room)
            print(f"📤 Progreso de seguro emitido a {room}")
    
    def _emit_completed(self, task_type, data, room):
        """Emite finalización de tarea"""
        result = data.get('result', {})
        
        # Payload base
        payload = {
            'task_id': data.get('task_id'),
            **result  # Incluir TODO lo que venga en el resultado (detalles, métricas, etc)
        }
        
        if task_type == 'nomina_completed':
            self.socketio.emit('nomina_completed', payload, room=room)
            print(f"✅ Nómina completada emitida a {room}")
            
        elif task_type == 'seguro_completed':
            self.socketio.emit('seguro_completed', payload, room=room)
            print(f"✅ Seguro completado emitido a {room}")
    
    def _emit_error(self, task_type, data, room):
        """Emite error de tarea"""
        self.socketio.emit('task_error', {
            'task_id': data.get('task_id'),
            'error': data.get('error'),
            'type': task_type
        }, room=room)
        print(f"❌ Error de tarea emitido a {room}")

# Instancia global
redis_listener = RedisListener()

def init_redis_listener(app, socketio):
    """Inicializa y arranca el listener de Redis"""
    redis_listener.init_app(app, socketio)
    redis_listener.start()
    return redis_listener
