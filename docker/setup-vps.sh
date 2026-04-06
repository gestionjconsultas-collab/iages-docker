#!/bin/bash
# setup-vps.sh
# Configura el entorno Docker en el VPS sin tocar producción.
# Ejecutar desde /var/www/iages-docker/
#
# Uso:
#   chmod +x docker/setup-vps.sh
#   ./docker/setup-vps.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

echo "============================================="
echo "  IAGES Docker — Setup en VPS"
echo "============================================="

# ── 1. Verificar Docker ────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    warn "Docker no instalado. Instalando..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    ok "Docker instalado (reinicia sesión SSH si hay problemas de permisos)"
else
    ok "Docker disponible: $(docker --version)"
fi

if ! command -v docker &>/dev/null || ! docker compose version &>/dev/null; then
    warn "Docker Compose plugin no encontrado. Instalando..."
    sudo apt-get install -y docker-compose-plugin
fi
ok "Docker Compose: $(docker compose version)"

# ── 2. Verificar .env ─────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env
        err "Creado .env desde .env.docker.example — EDÍTALO antes de continuar:\n  nano .env"
    else
        err "No existe .env ni .env.docker.example"
    fi
fi
ok ".env encontrado"

# Verificar que las claves obligatorias están definidas
for VAR in SECRET_KEY TOTP_ENCRYPTION_KEY FIELD_ENCRYPTION_KEY DB_PASSWORD; do
    val=$(grep "^${VAR}=" .env | cut -d= -f2-)
    if [ -z "$val" ]; then
        err "Variable $VAR está vacía en .env"
    fi
done
ok "Variables de entorno verificadas"

# ── 3. Build de frontends ─────────────────────────────────────────────────────
echo ""
echo "🏗️  Compilando frontends..."

# Frontend principal
if [ -d "frontend/node_modules" ]; then
    ok "node_modules del frontend principal ya existe, saltando npm install"
else
    cd frontend && npm install --silent && cd ..
fi
cd frontend && npm run build --silent && cd ..
ok "Frontend principal compilado → frontend/dist/"

# Portal del empleado
if [ -d "frontend/portal/node_modules" ]; then
    ok "node_modules del portal ya existe, saltando npm install"
else
    cd frontend/portal && npm install --silent && cd ../..
fi
cd frontend/portal && npm run build --silent && cd ../..
ok "Portal del Empleado compilado → frontend/portal/dist/"

# ── 4. Copia de la BD de producción (opcional) ────────────────────────────────
echo ""
echo "💾 ¿Copiar la BD de producción al entorno Docker? (recomendado para pruebas reales)"
read -p "   [s/N]: " COPY_DB

if [[ "$COPY_DB" =~ ^[sS]$ ]]; then
    # Leer config del .env
    DB_NAME=$(grep "^DB_NAME=" .env | cut -d= -f2-)
    DB_USER=$(grep "^DB_USER=" .env | cut -d= -f2-)
    DB_PASSWORD=$(grep "^DB_PASSWORD=" .env | cut -d= -f2-)
    DB_NAME=${DB_NAME:-iages_docker}

    echo "📦 Exportando BD de producción (iages_production)..."
    DUMP_FILE="/tmp/iages_prod_$(date +%Y%m%d_%H%M%S).sql"
    pg_dump -U postgres iages_production > "$DUMP_FILE" 2>/dev/null || \
    sudo -u postgres pg_dump iages_production > "$DUMP_FILE"
    ok "Dump creado en $DUMP_FILE"

    echo "⬆️  Importando al contenedor Docker..."
    # Levantar solo postgres primero
    docker compose up -d postgres
    sleep 5

    # Importar
    docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" < "$DUMP_FILE"
    ok "BD importada en contenedor Docker (base: $DB_NAME)"
    rm -f "$DUMP_FILE"
else
    warn "Saltando copia de BD — el sistema arrancará con BD vacía"
fi

# ── 5. Levantar todos los servicios ──────────────────────────────────────────
echo ""
echo "🚀 Levantando contenedores..."
docker compose up -d --build

# Esperar a que el backend responda
echo "⏳ Esperando al backend..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:${NGINX_PORT:-8080}/api/health &>/dev/null; then
        break
    fi
    sleep 2
done

# ── 6. Verificación final ─────────────────────────────────────────────────────
echo ""
echo "🔍 Estado de los contenedores:"
docker compose ps

HEALTH=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:${NGINX_PORT:-8080}/api/health || echo "000")
if [ "$HEALTH" = "200" ]; then
    ok "Health check OK"
else
    warn "Health check respondió $HEALTH — revisa logs: docker compose logs backend"
fi

PORT=$(grep "^NGINX_PORT=" .env | cut -d= -f2-)
PORT=${PORT:-8080}
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================="
echo "  ✅ Setup completado"
echo "============================================="
echo ""
echo "  🌐 App principal:    http://$IP:$PORT/"
echo "  👤 Portal empleado:  http://$IP:$PORT/portal/"
echo "  🔍 Logs:             docker compose logs -f"
echo "  🛑 Parar:            docker compose down"
echo "  🔄 Actualizar:       git pull && docker compose up -d --build"
echo ""
echo "  ⚠️  Producción sigue en /var/www/iages (sin cambios)"
echo "============================================="
