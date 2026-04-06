# 🚀 Guía de Deployment - IAGES Dashboard

## 📋 Información que Necesitas Tener

Antes de empezar, asegúrate de tener:

- ✅ Archivo `.pem` (clave SSH)
- ✅ IP del servidor (ej: `123.45.67.89`)
- ✅ Usuario del servidor (ej: `ubuntu`, `root`, `admin`)
- ✅ Dominio configurado (opcional, pero recomendado)

---

## 🔐 PASO 1: Conectarse al Servidor (Windows)

### Opción A: Usar PowerShell (Recomendado)

```powershell
# 1. Mueve el archivo .pem a una ubicación segura
Move-Item "C:\Users\Gestion\Downloads\tu-clave.pem" "C:\Users\Gestion\.ssh\servidor.pem"

# 2. Cambia los permisos (importante)
icacls "C:\Users\Gestion\.ssh\servidor.pem" /inheritance:r
icacls "C:\Users\Gestion\.ssh\servidor.pem" /grant:r "$($env:USERNAME):(R)"

# 3. Conéctate al servidor
ssh -i "C:\Users\Gestion\.ssh\servidor.pem" ubuntu@IP_DEL_SERVIDOR
```

**Reemplaza:**
- `tu-clave.pem` → nombre real de tu archivo .pem
- `ubuntu` → usuario que te dieron (puede ser `root`, `admin`, etc.)
- `IP_DEL_SERVIDOR` → IP real del servidor

### Opción B: Usar PuTTY (Alternativa)

Si prefieres interfaz gráfica:

1. **Descarga PuTTY:** https://www.putty.org/
2. **Convierte .pem a .ppk:**
   - Abre PuTTYgen
   - Load → Selecciona tu .pem
   - Save private key → Guarda como .ppk
3. **Conecta con PuTTY:**
   - Host: IP del servidor
   - Connection → SSH → Auth → Browse → Selecciona .ppk
   - Open

---

## 🛠️ PASO 2: Preparar el Servidor

Una vez conectado al servidor, ejecuta estos comandos:

### 2.1 Actualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.2 Instalar Dependencias Base

```bash
# Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx

# Git
sudo apt install -y git

# Node.js (para el frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Supervisor (para Celery)
sudo apt install -y supervisor

# Certbot (SSL)
sudo apt install -y certbot python3-certbot-nginx
```

### 2.3 Configurar PostgreSQL

```bash
# Cambiar a usuario postgres
sudo -u postgres psql

# Dentro de PostgreSQL, ejecuta:
CREATE DATABASE iages_production;
CREATE USER iages_user WITH PASSWORD 'TU_PASSWORD_SEGURO_AQUI';
GRANT ALL PRIVILEGES ON DATABASE iages_production TO iages_user;
\q
```

### 2.4 Configurar Redis

```bash
# Editar configuración
sudo nano /etc/redis/redis.conf

# Busca y cambia:
# supervised no  →  supervised systemd
# requirepass foobared  →  requirepass TU_PASSWORD_REDIS

# Reiniciar Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

---

## 📦 PASO 3: Clonar y Configurar la Aplicación

### 3.1 Crear Directorio

```bash
sudo mkdir -p /var/www/iages
sudo chown -R $USER:$USER /var/www/iages
cd /var/www/iages
```

### 3.2 Clonar Repositorio

```bash
git clone https://github.com/gestionjconsultas-collab/iages-dashboard.git .
```

### 3.3 Configurar Backend

```bash
cd /var/www/iages/backend

# Crear entorno virtual
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Crear .env de producción
cp .env.production.example .env
nano .env
```

**Edita el archivo `.env` con estos valores:**

```env
# Base de datos
DATABASE_URI=postgresql://iages_user:TU_PASSWORD_SEGURO_AQUI@localhost:5432/iages_production

# Seguridad (genera nuevas claves)
SECRET_KEY=genera_una_clave_nueva_aqui
TOTP_ENCRYPTION_KEY=genera_otra_clave_aqui

# Entorno
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
LOG_TO_FILE=True

# Redis
REDIS_URL=redis://:TU_PASSWORD_REDIS@localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://:TU_PASSWORD_REDIS@localhost:6379/2
CELERY_RESULT_BACKEND=redis://:TU_PASSWORD_REDIS@localhost:6379/3

# Email (usa tus credenciales)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASS=tu-app-password

# URLs
FRONTEND_URL=https://tudominio.com
BASE_URL=https://tudominio.com

# APIs
GEMINI_API_KEY=tu-api-key
SENTRY_DSN=tu-sentry-dsn (opcional)

# Sesiones
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_DOMAIN=.tudominio.com
```

**Generar claves secretas:**

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# TOTP_ENCRYPTION_KEY
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

### 3.4 Inicializar Base de Datos

```bash
# Activar entorno virtual si no está activo
source venv/bin/activate

# Crear tablas
python3 create_superadmin.py
```

### 3.5 Configurar Frontend

```bash
cd /var/www/iages/frontend

# Instalar dependencias
npm install

# Crear .env de producción
nano .env.production
```

**Contenido de `.env.production`:**

```env
VITE_API_URL=https://tudominio.com
```

**Compilar frontend:**

```bash
npm run build
```

---

## 🔧 PASO 4: Configurar Gunicorn

### 4.1 Crear archivo de servicio

```bash
sudo nano /etc/systemd/system/iages.service
```

**Contenido:**

```ini
[Unit]
Description=IAGES Dashboard Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/iages/backend
Environment="PATH=/var/www/iages/backend/venv/bin"
ExecStart=/var/www/iages/backend/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
```

### 4.2 Iniciar servicio

```bash
sudo systemctl daemon-reload
sudo systemctl start iages
sudo systemctl enable iages
sudo systemctl status iages
```

---

## 🌐 PASO 5: Configurar Nginx

### 5.1 Crear configuración

```bash
sudo nano /etc/nginx/sites-available/iages
```

**Contenido:**

```nginx
server {
    listen 80;
    server_name tudominio.com www.tudominio.com;

    # Frontend
    location / {
        root /var/www/iages/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Socket.IO
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Metrics
    location /metrics {
        proxy_pass http://127.0.0.1:5000;
    }

    client_max_body_size 50M;
}
```

### 5.2 Activar configuración

```bash
sudo ln -s /etc/nginx/sites-available/iages /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔒 PASO 6: Configurar SSL (HTTPS)

```bash
# Obtener certificado SSL
sudo certbot --nginx -d tudominio.com -d www.tudominio.com

# Renovación automática
sudo systemctl enable certbot.timer
```

---

## 🔄 PASO 7: Configurar Celery

### 7.1 Celery Worker

```bash
sudo nano /etc/systemd/system/celery-worker.service
```

**Contenido:**

```ini
[Unit]
Description=Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/iages/backend
Environment="PATH=/var/www/iages/backend/venv/bin"
ExecStart=/var/www/iages/backend/venv/bin/celery -A celery_worker.celery worker --loglevel=info --detach

[Install]
WantedBy=multi-user.target
```

### 7.2 Celery Beat

```bash
sudo nano /etc/systemd/system/celery-beat.service
```

**Contenido:**

```ini
[Unit]
Description=Celery Beat
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/iages/backend
Environment="PATH=/var/www/iages/backend/venv/bin"
ExecStart=/var/www/iages/backend/venv/bin/celery -A celery_worker.celery beat --loglevel=info --detach

[Install]
WantedBy=multi-user.target
```

### 7.3 Iniciar servicios

```bash
sudo systemctl daemon-reload
sudo systemctl start celery-worker
sudo systemctl start celery-beat
sudo systemctl enable celery-worker
sudo systemctl enable celery-beat
```

---

## ✅ PASO 8: Verificar Deployment

### 8.1 Verificar servicios

```bash
sudo systemctl status iages
sudo systemctl status celery-worker
sudo systemctl status celery-beat
sudo systemctl status nginx
sudo systemctl status redis-server
sudo systemctl status postgresql
```

### 8.2 Ver logs

```bash
# Logs de la aplicación
sudo journalctl -u iages -f

# Logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Logs de Celery
sudo journalctl -u celery-worker -f
```

### 8.3 Probar la aplicación

Abre tu navegador y ve a:
```
https://tudominio.com
```

---

## 🔄 Actualizar la Aplicación

Cuando hagas cambios en el código:

```bash
# En tu PC
git add .
git commit -m "Descripción de cambios"
git push

# En el servidor
cd /var/www/iages
git pull

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart iages
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat

# Frontend (si hubo cambios)
cd ../frontend
npm install
npm run build
sudo systemctl reload nginx
```

---

## 🚨 Troubleshooting

### Error: No se puede conectar

```bash
# Verificar firewall
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### Error: Base de datos

```bash
# Verificar PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "\l"
```

### Error: Permisos

```bash
# Arreglar permisos
sudo chown -R www-data:www-data /var/www/iages
sudo chmod -R 755 /var/www/iages
```

---

## 📞 Comandos Útiles

```bash
# Reiniciar todo
sudo systemctl restart iages celery-worker celery-beat nginx

# Ver logs en tiempo real
sudo journalctl -u iages -f

# Verificar puertos
sudo netstat -tulpn | grep LISTEN

# Espacio en disco
df -h

# Memoria
free -h

# Procesos
htop
```

---

**¡Listo! Tu aplicación debería estar funcionando en producción.** 🎉
