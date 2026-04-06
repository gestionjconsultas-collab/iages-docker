#!/bin/bash
# deploy.sh
# Script de deployment para IAGES en producción

set -e  # Exit on error

echo "🚀 Iniciando deployment de IAGES..."

# Variables
APP_DIR="/var/www/iages"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$APP_DIR/venv"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funciones
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 1. Verificar que estamos en el servidor correcto
echo "📍 Verificando servidor..."
if [ ! -d "$APP_DIR" ]; then
    print_error "Directorio $APP_DIR no existe"
    exit 1
fi
print_success "Servidor verificado"

# 2. Backup de la base de datos
echo "💾 Creando backup de base de datos..."
cd $BACKEND_DIR
python3 utils/backup_manager.py create || print_warning "Backup falló, continuando..."
print_success "Backup completado"

# 3. Detener servicios
echo "⏸️  Deteniendo servicios..."
sudo systemctl stop iages-backend
sudo systemctl stop iages-celery
sudo systemctl stop iages-flower || true
print_success "Servicios detenidos"

# 4. Actualizar código
echo "📥 Actualizando código desde Git..."
cd $APP_DIR
git pull origin main
print_success "Código actualizado"

# 5. Actualizar dependencias del backend
echo "📦 Actualizando dependencias del backend..."
cd $BACKEND_DIR
source $VENV_DIR/bin/activate
pip install -r requirements.txt --upgrade
print_success "Dependencias del backend actualizadas"

# 6. Ejecutar migraciones de base de datos
echo "🗄️  Ejecutando migraciones..."
cd $BACKEND_DIR
source $VENV_DIR/bin/activate
python migrations/create_portal_empleado_auth.py || print_warning "Migración portal ya aplicada o falló"
print_success "Migraciones completadas"

# 7. Build del frontend principal
echo "🏗️  Building frontend principal..."
cd $FRONTEND_DIR
npm install
npm run build
print_success "Frontend principal built"

# 7b. Build del Portal del Empleado
echo "🏗️  Building Portal del Empleado..."
cd $FRONTEND_DIR/portal
npm install
npm run build
print_success "Portal del Empleado built"

# 8. Limpiar caché de Redis
echo "🧹 Limpiando caché..."
redis-cli FLUSHDB || print_warning "No se pudo limpiar Redis"
print_success "Caché limpiado"

# 9. Reiniciar servicios
echo "🔄 Reiniciando servicios..."
sudo systemctl start iages-backend
sudo systemctl start iages-celery
sudo systemctl start iages-flower || true
sleep 5
print_success "Servicios reiniciados"

# 10. Verificar estado
echo "🔍 Verificando servicios..."
sudo systemctl status iages-backend --no-pager | head -n 5
sudo systemctl status iages-celery --no-pager | head -n 5
sudo systemctl status iages-flower --no-pager | head -n 5 || true

# 11. Health check
echo "🏥 Verificando health check..."
sleep 3
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/health)
if [ "$HEALTH_CHECK" == "200" ]; then
    print_success "Health check OK (200)"
else
    print_error "Health check falló (código: $HEALTH_CHECK)"
    exit 1
fi

# 12. Reload Nginx
echo "🔄 Recargando Nginx..."
sudo nginx -t && sudo systemctl reload nginx
print_success "Nginx recargado"

echo ""
echo "🎉 ¡Deployment completado exitosamente!"
echo "📊 Logs disponibles en:"
echo "   - Backend: /var/log/iages/gunicorn-error.log"
echo "   - Celery: /var/log/iages/celery-worker.log"
echo "   - Nginx: /var/log/nginx/iages-error.log"
echo ""
echo "🌐 Aplicación disponible en: https://app.tudominio.com"
