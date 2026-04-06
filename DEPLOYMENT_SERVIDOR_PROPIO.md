# 🚀 Guía de Deployment - SpainFlow en Servidor Propio

## 📋 Requisitos del Servidor

### Especificaciones Mínimas
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM**: 4GB mínimo (8GB recomendado)
- **CPU**: 2 cores mínimo
- **Disco**: 50GB SSD
- **Ancho de banda**: 100Mbps

### Software Necesario
- Node.js 18+ (para frontend)
- Python 3.10+ (para backend)
- PostgreSQL 14+
- Nginx (proxy reverso)
- Redis (para Celery)
- Certbot (SSL/HTTPS)

---

## 🔧 INSTALACIÓN EN SERVIDOR

### 1. Preparar Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias básicas
sudo apt install -y git curl wget build-essential

# Instalar Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Instalar Python 3.10
sudo apt install -y python3.10 python3.10-venv python3-pip

# Instalar PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Instalar Redis
sudo apt install -y redis-server

# Instalar Nginx
sudo apt install -y nginx
```

### 2. Configurar PostgreSQL

```bash
# Crear base de datos
sudo -u postgres psql
```

```sql
CREATE DATABASE spainflow;
CREATE USER spainflow_user WITH PASSWORD 'tu_password_seguro';
GRANT ALL PRIVILEGES ON DATABASE spainflow TO spainflow_user;
\q
```

### 3. Clonar Proyecto

```bash
# Crear directorio
sudo mkdir -p /var/www/spainflow
sudo chown $USER:$USER /var/www/spainflow

# Clonar (o subir archivos)
cd /var/www/spainflow
# Subir archivos vía FTP/SCP o git clone
```

### 4. Configurar Backend

```bash
cd /var/www/spainflow/backend

# Crear entorno virtual
python3.10 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements_celery.txt
pip install -r requirements_reportes.txt
pip install gunicorn

# Configurar variables de entorno
nano .env
```

**`.env`**:
```env
FLASK_ENV=production
SECRET_KEY=tu_clave_secreta_muy_larga_y_segura
DATABASE_URL=postgresql://spainflow_user:tu_password_seguro@localhost/spainflow
REDIS_URL=redis://localhost:6379/0
```

```bash
# Ejecutar migraciones
python -c "from app import db; db.create_all()"
python migrations/001_sistema_multigestoria_avanzado.sql
python migrations/002_historial_cambios_planes.sql
```

### 5. Configurar Frontend

```bash
cd /var/www/spainflow/frontend

# Instalar dependencias
npm install

# Configurar variables de entorno
nano .env.production
```

**`.env.production`**:
```env
VITE_API_URL=https://api.tudominio.com
```

```bash
# Build para producción
npm run build
# Esto genera carpeta 'dist' con archivos estáticos
```

### 6. Configurar Nginx

```bash
sudo nano /etc/nginx/sites-available/spainflow
```

**`/etc/nginx/sites-available/spainflow`**:
```nginx
# Frontend
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;
    
    root /var/www/spainflow/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Proxy para API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # WebSockets para Socket.IO
    location /socket.io {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

```bash
# Activar sitio
sudo ln -s /etc/nginx/sites-available/spainflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Configurar SSL (HTTPS)

```bash
# Instalar Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d tudominio.com -d www.tudominio.com

# Renovación automática (ya configurada)
sudo certbot renew --dry-run
```

### 8. Configurar Servicios Systemd

**Backend (Gunicorn)**:
```bash
sudo nano /etc/systemd/system/spainflow-backend.service
```

```ini
[Unit]
Description=SpainFlow Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/spainflow/backend
Environment="PATH=/var/www/spainflow/backend/venv/bin"
ExecStart=/var/www/spainflow/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

**Celery Worker**:
```bash
sudo nano /etc/systemd/system/spainflow-celery.service
```

```ini
[Unit]
Description=SpainFlow Celery Worker
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/spainflow/backend
Environment="PATH=/var/www/spainflow/backend/venv/bin"
ExecStart=/var/www/spainflow/backend/venv/bin/celery -A tasks worker --loglevel=info

[Install]
WantedBy=multi-user.target
```

**Celery Beat**:
```bash
sudo nano /etc/systemd/system/spainflow-celery-beat.service
```

```ini
[Unit]
Description=SpainFlow Celery Beat
After=network.target redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/spainflow/backend
Environment="PATH=/var/www/spainflow/backend/venv/bin"
ExecStart=/var/www/spainflow/backend/venv/bin/celery -A tasks beat --loglevel=info

[Install]
WantedBy=multi-user.target
```

**Activar servicios**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable spainflow-backend
sudo systemctl enable spainflow-celery
sudo systemctl enable spainflow-celery-beat
sudo systemctl start spainflow-backend
sudo systemctl start spainflow-celery
sudo systemctl start spainflow-celery-beat
```

---

## 🔍 VERIFICACIÓN

```bash
# Ver estado de servicios
sudo systemctl status spainflow-backend
sudo systemctl status spainflow-celery
sudo systemctl status spainflow-celery-beat
sudo systemctl status nginx

# Ver logs
sudo journalctl -u spainflow-backend -f
sudo journalctl -u spainflow-celery -f
```

---

## 🔒 SEGURIDAD

### Firewall
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### Backups Automáticos
```bash
# Crear script de backup
sudo nano /usr/local/bin/backup-spainflow.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/spainflow"

# Backup base de datos
pg_dump -U spainflow_user spainflow > $BACKUP_DIR/db_$DATE.sql

# Backup archivos
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /var/www/spainflow/backend/uploads

# Limpiar backups antiguos (>30 días)
find $BACKUP_DIR -type f -mtime +30 -delete
```

```bash
# Hacer ejecutable
sudo chmod +x /usr/local/bin/backup-spainflow.sh

# Cron diario 3 AM
sudo crontab -e
0 3 * * * /usr/local/bin/backup-spainflow.sh
```

---

## 📊 MONITOREO

### Logs
```bash
# Nginx
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Backend
sudo journalctl -u spainflow-backend -f

# Celery
sudo journalctl -u spainflow-celery -f
```

### Performance
```bash
# Instalar htop
sudo apt install htop

# Monitorear recursos
htop
```

---

## 🚀 ACTUALIZACIÓN

```bash
# Detener servicios
sudo systemctl stop spainflow-backend spainflow-celery spainflow-celery-beat

# Actualizar código
cd /var/www/spainflow
git pull  # o subir nuevos archivos

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run build

# Reiniciar servicios
sudo systemctl start spainflow-backend spainflow-celery spainflow-celery-beat
```

---

## 📝 CHECKLIST DEPLOYMENT

- [ ] Servidor configurado con requisitos
- [ ] PostgreSQL instalado y configurado
- [ ] Redis instalado
- [ ] Código subido al servidor
- [ ] Backend configurado (.env)
- [ ] Frontend compilado (npm run build)
- [ ] Nginx configurado
- [ ] SSL/HTTPS activado
- [ ] Servicios systemd creados
- [ ] Servicios iniciados y activos
- [ ] Firewall configurado
- [ ] Backups automáticos configurados
- [ ] DNS apuntando al servidor
- [ ] Aplicación accesible vía HTTPS

---

## 🎯 RESULTADO FINAL

**URL**: `https://tudominio.com`
- Frontend servido por Nginx
- Backend en Gunicorn
- HTTPS automático
- Celery corriendo en background
- Backups automáticos
- Logs centralizados

**Performance**:
- Sin latencia de ngrok
- WebSockets en tiempo real
- Escalable con más workers
- Caché con Redis

---

¿Necesitas ayuda con algún paso específico del deployment?
