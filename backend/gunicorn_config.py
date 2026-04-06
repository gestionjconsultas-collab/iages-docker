# gunicorn_config.py
# Configuración de Gunicorn para producción

import multiprocessing
import os

# Dirección de escucha
bind = "127.0.0.1:5000"

# ✅ OPTIMIZADO: Número de workers (antes: cpu_count() * 2 + 1 = 9)
# Para apps I/O bound como Flask, la fórmula óptima es:
workers = multiprocessing.cpu_count() + 1  # 5 workers (mejor para 4 cores)
worker_class = "gevent"  # Cambiado de eventlet para consistencia con app.py

# ✅ OPTIMIZADO: Aumentar conexiones por worker para compensar menos workers
worker_connections = 2000  # ANTES: 1000

# ✅ OPTIMIZADO: Timeouts más agresivos
timeout = 60  # ANTES: 120 (muy alto para requests normales)
keepalive = 2  # ANTES: 5
graceful_timeout = 30

# Logging
accesslog = "/var/log/iages/gunicorn-access.log"
errorlog = "/var/log/iages/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "iages"

# Server mechanics
daemon = False
pidfile = "/var/run/iages/gunicorn.pid"
# user = "www-data"
# group = "www-data"
tmp_upload_dir = "/tmp"

# SSL (si Gunicorn maneja SSL directamente, sino usar Nginx)
# keyfile = "/etc/ssl/private/spainflow.key"
# certfile = "/etc/ssl/certs/spainflow.crt"

# Preload app para mejor rendimiento
preload_app = True

# Límites
max_requests = 1000
max_requests_jitter = 50

# Hooks para logging
def on_starting(server):
    server.log.info("🚀 Gunicorn iniciando IAGES")

def on_reload(server):
    server.log.info("🔄 Gunicorn recargando configuración")

def worker_int(worker):
    worker.log.info("⚠️ Worker recibió INT o QUIT")

def pre_fork(server, worker):
    pass

def post_fork(server, worker):
    server.log.info(f"✅ Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    server.log.info("🔄 Forked child, re-executing")

def when_ready(server):
    server.log.info("✅ Server is ready. Spawning workers")

def worker_abort(worker):
    worker.log.info(f"❌ Worker recibió SIGABRT (pid: {worker.pid})")
