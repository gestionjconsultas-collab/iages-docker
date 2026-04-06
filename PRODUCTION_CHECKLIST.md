# ✅ Checklist de Preparación para Producción

## 🔐 Seguridad

- [ ] **SECRET_KEY**: Generar clave secreta única
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] **FLASK_DEBUG**: Establecer en `False`
- [ ] **SESSION_COOKIE_SECURE**: Establecer en `True` (requiere HTTPS)
- [ ] **SESSION_COOKIE_HTTPONLY**: Establecer en `True`
- [ ] **SWAGGER_ENABLED**: Establecer en `False` (ocultar documentación API)
- [ ] Cambiar todas las contraseñas por defecto
- [ ] Configurar firewall (solo puertos 80, 443, 22)
- [ ] Configurar fail2ban para protección contra ataques
- [ ] Habilitar 2FA para usuarios admin

## 🗄️ Base de Datos

- [ ] **Migrar a PostgreSQL** (recomendado para producción)
- [ ] Configurar backups automáticos diarios
- [ ] Configurar replicación (opcional)
- [ ] Optimizar índices de base de datos
- [ ] Establecer límites de conexión
- [ ] Configurar pool de conexiones

## 🚀 Servidor

- [ ] **Instalar dependencias de producción**
  ```bash
  pip install -r requirements.txt
  pip install gunicorn psycopg2-binary redis
  ```
- [ ] **Configurar Gunicorn** (servidor WSGI)
- [ ] **Configurar Nginx** (proxy reverso)
- [ ] **Configurar SSL/TLS** (Let's Encrypt)
- [ ] Configurar systemd para auto-inicio
- [ ] Configurar logs rotativos
- [ ] Establecer límites de recursos (CPU, RAM)

## 📦 Redis

- [ ] Instalar Redis Server
- [ ] Configurar persistencia (RDB + AOF)
- [ ] Establecer contraseña de Redis
- [ ] Configurar límites de memoria
- [ ] Habilitar Redis como servicio

## 📧 Email

- [ ] Configurar servidor SMTP
- [ ] Obtener credenciales de aplicación (Gmail)
- [ ] Verificar dominio para emails
- [ ] Configurar plantillas de email
- [ ] Probar envío de emails

## 🔍 Monitoreo

- [ ] **Configurar Sentry** para tracking de errores
  - Crear proyecto en sentry.io
  - Obtener DSN
  - Configurar SENTRY_DSN en .env
- [ ] **Configurar Prometheus** para métricas
- [ ] Opcional: Configurar Grafana para visualización
- [ ] Configurar alertas por email/Slack
- [ ] Configurar health checks

## 🔄 Celery (Tareas Asíncronas)

- [ ] Configurar Celery worker como servicio
- [ ] Configurar Celery beat para tareas programadas
- [ ] Configurar supervisord para gestión de procesos
- [ ] Establecer límites de workers
- [ ] Configurar reintentos y timeouts

## 📁 Archivos

- [ ] Crear directorio de uploads con permisos correctos
  ```bash
  mkdir -p /var/www/iages/uploads
  chown www-data:www-data /var/www/iages/uploads
  chmod 755 /var/www/iages/uploads
  ```
- [ ] Configurar límites de tamaño de archivo
- [ ] Configurar limpieza automática de archivos temporales
- [ ] Opcional: Configurar almacenamiento en S3/Cloud

## 🌐 Dominio y DNS

- [ ] Configurar dominio (A record)
- [ ] Configurar subdominios si es necesario
- [ ] Configurar certificado SSL (Let's Encrypt)
- [ ] Configurar renovación automática de SSL
- [ ] Configurar CORS para dominio de producción

## 🔧 Variables de Entorno

- [ ] Copiar `.env.production.example` a `.env`
- [ ] Completar todas las variables con valores reales
- [ ] Verificar que `.env` está en `.gitignore`
- [ ] NO subir `.env` a Git

## 🧪 Testing

- [ ] Ejecutar tests en entorno de staging
- [ ] Probar flujo completo de usuario
- [ ] Verificar integración con Saltra
- [ ] Probar envío de emails
- [ ] Verificar procesamiento de archivos
- [ ] Probar límites de rate limiting
- [ ] Verificar backups automáticos

## 📊 Performance

- [ ] Configurar caché de Redis
- [ ] Optimizar consultas SQL (usar EXPLAIN)
- [ ] Configurar compresión HTTP (gzip)
- [ ] Configurar CDN para assets estáticos (opcional)
- [ ] Minimizar y comprimir JavaScript/CSS
- [ ] Configurar lazy loading de imágenes

## 🔄 CI/CD (Opcional)

- [ ] Configurar GitHub Actions / GitLab CI
- [ ] Configurar deploy automático
- [ ] Configurar tests automáticos
- [ ] Configurar rollback automático en caso de error

## 📝 Documentación

- [ ] Documentar proceso de deploy
- [ ] Documentar proceso de backup/restore
- [ ] Documentar troubleshooting común
- [ ] Crear runbook para incidentes
- [ ] Documentar arquitectura del sistema

## 🚨 Plan de Contingencia

- [ ] Definir proceso de rollback
- [ ] Configurar backups automáticos
- [ ] Probar restauración de backups
- [ ] Definir contactos de emergencia
- [ ] Crear plan de recuperación ante desastres

## 🎯 Post-Deployment

- [ ] Monitorear logs por 24-48 horas
- [ ] Verificar métricas de performance
- [ ] Verificar que no hay errores en Sentry
- [ ] Verificar que backups se están ejecutando
- [ ] Recopilar feedback de usuarios
- [ ] Optimizar según métricas reales

---

## 📚 Comandos Útiles

### Generar SECRET_KEY
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Iniciar Gunicorn
```bash
gunicorn -c gunicorn_config.py app:app
```

### Iniciar Celery Worker
```bash
celery -A celery_worker.celery worker --loglevel=info
```

### Iniciar Celery Beat
```bash
celery -A celery_worker.celery beat --loglevel=info
```

### Ver logs en tiempo real
```bash
tail -f /var/log/iages/app.log
```

### Backup manual de base de datos
```bash
pg_dump iages_production > backup_$(date +%Y%m%d).sql
```

### Restaurar backup
```bash
psql iages_production < backup_20260105.sql
```
