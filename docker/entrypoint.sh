#!/bin/bash
set -e

echo "🚀 Iniciando IAGES..."

# Esperar a que PostgreSQL esté disponible
echo "⏳ Esperando a PostgreSQL..."
until python -c "
import psycopg2, os
psycopg2.connect(os.environ['DATABASE_URL'])
" 2>/dev/null; do
    sleep 1
done
echo "✅ PostgreSQL disponible"

# Esperar a que Redis esté disponible
echo "⏳ Esperando a Redis..."
until python -c "
import redis, os
r = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
r.ping()
" 2>/dev/null; do
    sleep 1
done
echo "✅ Redis disponible"

# Ejecutar migraciones automáticas si existen
echo "🗄️  Ejecutando migraciones..."
python migrations/create_portal_empleado_auth.py 2>/dev/null || true

# Arrancar según el rol del contenedor
ROLE=${CONTAINER_ROLE:-backend}

case "$ROLE" in
    backend)
        echo "🌐 Arrancando Gunicorn (backend)..."
        exec gunicorn \
            --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
            --workers 2 \
            --bind 0.0.0.0:5000 \
            --timeout 120 \
            --keep-alive 5 \
            --log-level info \
            --access-logfile - \
            --error-logfile - \
            "app:app"
        ;;
    celery)
        echo "⚙️  Arrancando Celery worker..."
        exec celery -A celery_worker.celery worker \
            --loglevel=info \
            --concurrency=2 \
            -Q celery,ocr,emails
        ;;
    celery-beat)
        echo "⏰ Arrancando Celery beat..."
        exec celery -A celery_worker.celery beat \
            --loglevel=info \
            --scheduler celery.beat.PersistentScheduler
        ;;
    *)
        echo "❌ CONTAINER_ROLE desconocido: $ROLE"
        exit 1
        ;;
esac
