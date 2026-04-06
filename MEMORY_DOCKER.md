# Memoria: Entorno Docker (IAGES)

## Contexto
Se creó un entorno Docker **paralelo a producción** para poder desarrollar y probar
sin tocar el sistema que está corriendo en `/var/www/iages`.

La copia del proyecto para Docker está en `/var/www/iages-docker/` en el VPS.

---

## Archivos creados

| Archivo | Descripción |
|---|---|
| `Dockerfile` | Imagen única para backend + celery (Python 3.11-slim) |
| `docker-compose.yml` | Orquesta 5 servicios: postgres, redis, backend, celery, nginx |
| `docker/entrypoint.sh` | Arranque según `CONTAINER_ROLE` (backend / celery / celery-beat) |
| `docker/nginx.conf` | Proxy inverso: API, WebSocket, frontend principal, portal empleado |
| `docker/setup-vps.sh` | Script de instalación/arranque completo en el VPS |
| `.env.docker.example` | Plantilla de variables de entorno para el entorno Docker |

---

## Servicios (docker-compose.yml)

| Servicio | Imagen | Container name | Puerto interno |
|---|---|---|---|
| `postgres` | postgres:15-alpine | iages_docker_db | 5432 |
| `redis` | redis:7-alpine | iages_docker_redis | 6379 |
| `backend` | Build local | iages_docker_backend | 5000 |
| `celery` | Build local (mismo Dockerfile) | iages_docker_celery | — |
| `nginx` | nginx:alpine | iages_docker_nginx | `${NGINX_PORT:-8080}:80` |

**Puerto externo: 8080** (para no chocar con nginx de producción en 80/443)

---

## Variables de entorno (.env en raíz del proyecto)

Copiar desde `.env.docker.example` y rellenar:

```env
DB_NAME=iages_docker          # BD separada de producción
DB_USER=iages
DB_PASSWORD=...

SECRET_KEY=                   # Mismo valor que producción
TOTP_ENCRYPTION_KEY=          # Mismo valor que producción
FIELD_ENCRYPTION_KEY=         # Mismo valor que producción
PORTAL_JWT_SECRET=

PORTAL_BASE_URL=http://ip-del-vps:8080/portal
SMTP_SERVER=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

NGINX_PORT=8080
```

---

## Dockerfile (resumen)

```dockerfile
FROM python:3.11-slim
# Instala: gcc, libpq-dev, libmagic1, libmupdf-dev, tesseract-ocr (+ spa), curl
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
COPY frontend/dist/ ./static/dist/          # frontend principal
COPY frontend/portal/dist/ ./static/portal/ # portal empleado
COPY docker/entrypoint.sh /entrypoint.sh
EXPOSE 5000
ENTRYPOINT ["/entrypoint.sh"]
```

---

## entrypoint.sh (lógica de arranque)

Lee la variable `CONTAINER_ROLE`:
- `backend` → `gunicorn` con worker `GeventWebSocket`, 2 workers, puerto 5000
- `celery` → `celery worker`, concurrency 2, queues: `celery,ocr,emails`
- `celery-beat` → `celery beat` con `PersistentScheduler`

Antes de arrancar:
1. Espera a que PostgreSQL responda
2. Espera a que Redis responda
3. Ejecuta `python migrations/create_portal_empleado_auth.py` (si existe)

---

## nginx.conf (rutas)

| Location | Destino |
|---|---|
| `/portal/api/` | proxy → backend:5000 |
| `/portal/` | estático `/usr/share/nginx/html/portal/` (SPA) |
| `/api/` | proxy → backend:5000 |
| `/socket.io/` | proxy WebSocket → backend:5000 (timeout 7d) |
| `/static/` | proxy → backend:5000 (cache 30d) |
| `/` | estático `/usr/share/nginx/html/app/` (SPA React) |

---

## Volúmenes persistentes

```yaml
volumes:
  postgres_data:   # datos de PostgreSQL
  redis_data:      # datos de Redis
  storage_data:    # archivos subidos (/app/storage)
  uploads_data:    # uploads temporales (/app/uploads)
```

---

## Cómo arrancar desde cero (en el VPS, en /var/www/iages-docker/)

```bash
# 1. Permisos
chmod +x docker/setup-vps.sh

# 2. Crear .env
cp .env.docker.example .env
nano .env   # rellenar SECRET_KEY, TOTP_ENCRYPTION_KEY, FIELD_ENCRYPTION_KEY, DB_PASSWORD

# 3. Ejecutar setup (instala Docker si hace falta, compila frontends, levanta todo)
./docker/setup-vps.sh
```

El script pregunta si quieres copiar la BD de producción (`iages`) al contenedor Docker.
- **Sí**: hace `pg_dump iages` e importa en el contenedor → datos reales para pruebas
- **No**: arranca con BD vacía

---

## Comandos útiles del día a día

```bash
# Ver estado de contenedores
docker compose ps

# Logs en tiempo real
docker compose logs -f
docker compose logs -f backend
docker compose logs -f celery

# Reiniciar un servicio
docker compose restart backend
docker compose restart celery

# Reconstruir tras cambios de código
docker compose up -d --build

# Parar todo (sin borrar datos)
docker compose down

# Parar y borrar volúmenes (BD incluida) — ⚠️ destructivo
docker compose down -v

# Actualizar desde git
git pull && docker compose up -d --build

# Acceder a la BD del contenedor
docker compose exec postgres psql -U iages -d iages_docker
```

---

## URLs de acceso

- **App principal**: `http://ip-del-vps:8080/`
- **Portal empleado**: `http://ip-del-vps:8080/portal/`
- **Health check**: `http://ip-del-vps:8080/api/health`

---

## Notas importantes

- Producción sigue corriendo en `/var/www/iages` sin ningún cambio
- El entorno Docker usa **BD separada** (`iages_docker`) para no mezclar datos
- Si se copia la BD de producción, los archivos del `storage/` de producción **no se copian** (están fuera del dump SQL) — los documentos existentes en la web apuntarán a rutas que no existen en el contenedor
- El `NGINX_PORT=8080` es configurable en `.env` si ese puerto ya está ocupado
- `celery-beat` no está en el `docker-compose.yml` por defecto — añadir si se necesitan tareas programadas
