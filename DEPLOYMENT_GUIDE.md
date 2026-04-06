# 🚀 Guía de Deployment - SpainFlow

**Última actualización:** 2 de enero de 2026  
**Versión:** 1.0.0

---

## 📋 Pre-requisitos

### Servidor Linux (Ubuntu 22.04 LTS recomendado)
- 4 GB RAM mínimo (8 GB recomendado)
- 2 CPU cores mínimo (4 recomendado)
- 50 GB disco
- Acceso root/sudo

### Software requerido
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Nginx
- Node.js 18+ (para build del frontend)

---

## 🔧 Paso 1: Preparar el Servidor

### 1.1 Actualizar sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar dependencias
```bash
# Python y herramientas
sudo apt install -y python3.10 python3.10-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx

# Node.js (para build del frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Herramientas adicionales
sudo apt install -y git curl wget certbot python3-certbot-nginx
```

---

## 🗄️ Paso 2: Configurar PostgreSQL

```bash
# Crear usuario y base de datos
sudo -u postgres psql

CREATE USER spainflow WITH PASSWORD 'tu_password_seguro_aqui';
CREATE DATABASE spainflow OWNER spainflow;
GRANT ALL PRIVILEGES ON DATABASE spainflow TO spainflow;
\q
```

---

## 🔐 Paso 3: Configurar Redis

```bash
# Editar configuración
sudo nano /etc/redis/redis.conf

# Agregar/modificar:
requirepass tu_password_redis_aqui
maxmemory 256mb
maxmemory-policy allkeys-lru

# Reiniciar
sudo systemctl restart redis
sudo systemctl enable redis
```

---

## 📁 Paso 4: Preparar Directorios

```bash
# Crear estructura
sudo mkdir -p /var/www/spainflow
sudo mkdir -p /var/log/spainflow
sudo mkdir -p /var/run/spainflow
sudo mkdir -p /var/backups/spainflow

# Permisos
sudo chown -R www-data:www-data /var/www/spainflow
sudo chown -R www-data:www-data /var/log/spainflow
sudo chown -R www-data:www-data /var/run/spainflow
sudo chown -R www-data:www-data /var/backups/spainflow
```

---

## 📥 Paso 5: Subir Código

### Opción A: Git (Recomendado)
```bash
cd /var/www/spainflow
sudo -u www-data git clone https://github.com/tu-usuario/spainflow.git .
```

### Opción B: SCP/SFTP
```bash
# Desde tu máquina local:
scp -r C:\Users\Gestion\Documents\dashboard_carpetas/* usuario@servidor:/var/www/spainflow/
```

---

## 🐍 Paso 6: Configurar Backend

### 6.1 Crear entorno virtual
```bash
cd /var/www/spainflow/backend
sudo -u www-data python3 -m venv /var/www/spainflow/venv
```

### 6.2 Instalar dependencias
```bash
source /var/www/spainflow/venv/bin/activate
pip install -r requirements.txt
pip install gunicorn gevent  # Si no están en requirements.txt
```

### 6.3 Configurar variables de entorno
```bash
sudo -u www-data nano /var/www/spainflow/backend/.env
```

**Contenido del `.env`:**
```bash
# SEGURIDAD
SECRET_KEY=<generar-con-comando-abajo>
TOTP_ENCRYPTION_KEY=<generar-con-comando-abajo>

# BASE DE DATOS
DATABASE_URI=postgresql://spainflow:tu_password@localhost:5432/spainflow

# REDIS
REDIS_URL=redis://:tu_password_redis@localhost:6379/0

# APIS
GEMINI_API_KEY=tu_api_key_gemini

# EMAIL
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASS=tu_app_password

# FRONTEND
FRONTEND_URL=https://app.tudominio.com
ALLOWED_ORIGINS=https://tudominio.com,https://www.tudominio.com,https://app.tudominio.com

# FLASK
FLASK_ENV=production
FLASK_DEBUG=0

# LOGS
LOG_TO_FILE=True
LOG_FILE=/var/log/spainflow/app.log
LOG_LEVEL=INFO

# BACKUPS
BACKUP_DIR=/var/backups/spainflow
BACKUP_GPG_RECIPIENT=admin@tudominio.com
```

**Generar claves:**
```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# TOTP_ENCRYPTION_KEY (exactamente 32 caracteres)
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

### 6.4 Ejecutar migraciones
```bash
cd /var/www/spainflow/backend
source /var/www/spainflow/venv/bin/activate

# Si tienes script de migración
python crear_tablas.py

# O ejecutar SQL directamente
psql -U spainflow -d spainflow < add_password_reset_fields.sql
```

---

## ⚛️ Paso 7: Build del Frontend

```bash
cd /var/www/spainflow/frontend

# Configurar variables de entorno
echo "VITE_API_URL=https://app.tudominio.com" > .env.production

# Instalar y build
npm install
npm run build

# El output estará en: /var/www/spainflow/frontend/dist
```

---

## 🌐 Paso 8: Configurar Nginx

### 8.1 Copiar configuración
```bash
sudo cp /var/www/spainflow/backend/nginx.conf /etc/nginx/sites-available/spainflow
```

### 8.2 Editar dominios
```bash
sudo nano /etc/nginx/sites-available/spainflow

# Reemplazar "tudominio.com" con tu dominio real
```

### 8.3 Habilitar sitio
```bash
sudo ln -s /etc/nginx/sites-available/spainflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔒 Paso 9: Configurar SSL con Let's Encrypt

```bash
# Obtener certificado
sudo certbot --nginx -d app.tudominio.com

# Renovación automática (ya configurado por certbot)
sudo certbot renew --dry-run
```

---

## ⚙️ Paso 10: Configurar Systemd Services

### 10.1 Copiar archivos de servicio
```bash
sudo cp /var/www/spainflow/backend/spainflow.service /etc/systemd/system/
sudo cp /var/www/spainflow/backend/celery-worker.service /etc/systemd/system/
sudo cp /var/www/spainflow/backend/celery-beat.service /etc/systemd/system/
```

### 10.2 Recargar systemd
```bash
sudo systemctl daemon-reload
```

### 10.3 Habilitar e iniciar servicios
```bash
# Backend
sudo systemctl enable spainflow
sudo systemctl start spainflow

# Celery Worker
sudo systemctl enable celery-worker
sudo systemctl start celery-worker

# Celery Beat
sudo systemctl enable celery-beat
sudo systemctl start celery-beat
```

### 10.4 Verificar estado
```bash
sudo systemctl status spainflow
sudo systemctl status celery-worker
sudo systemctl status celery-beat
```

---

## 🔥 Paso 11: Configurar Firewall

```bash
# Habilitar UFW
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Verificar
sudo ufw status
```

---

## 📊 Paso 12: Configurar Logs

### 12.1 Logrotate
```bash
sudo nano /etc/logrotate.d/spainflow
```

**Contenido:**
```
/var/log/spainflow/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload spainflow
    endscript
}
```

---

## ✅ Paso 13: Verificación Final

### 13.1 Health check
```bash
curl http://localhost:5000/api/health
# Debe devolver: {"status": "healthy"}
```

### 13.2 Verificar HTTPS
```bash
curl -I https://app.tudominio.com
# Debe devolver: HTTP/2 200
```

### 13.3 Verificar servicios
```bash
sudo systemctl status spainflow celery-worker celery-beat nginx postgresql redis
```

### 13.4 Ver logs
```bash
# Backend
sudo tail -f /var/log/spainflow/gunicorn-error.log

# Celery
sudo tail -f /var/log/spainflow/celery-worker.log

# Nginx
sudo tail -f /var/log/nginx/spainflow-error.log
```

---

## 🔄 Deployments Futuros

### Usar el script automático
```bash
cd /var/www/spainflow/backend
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

---

## 🆘 Troubleshooting

### Servicio no inicia
```bash
# Ver logs detallados
sudo journalctl -u spainflow -n 50 --no-pager

# Verificar permisos
ls -la /var/www/spainflow/backend
```

### Error de base de datos
```bash
# Verificar conexión
psql -U spainflow -d spainflow -h localhost

# Ver logs de PostgreSQL
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### Redis no conecta
```bash
# Verificar servicio
sudo systemctl status redis

# Probar conexión
redis-cli -a tu_password ping
```

---

## 📞 Soporte

**Documentación:**
- `production_readiness.md` - Checklist completo
- `security_final.md` - Configuración de seguridad
- `README.md` - Documentación general

**Logs importantes:**
- Backend: `/var/log/spainflow/gunicorn-error.log`
- Celery: `/var/log/spainflow/celery-worker.log`
- Nginx: `/var/log/nginx/spainflow-error.log`
- Systemd: `sudo journalctl -u spainflow`

---

**¡Deployment completado! 🎉**
