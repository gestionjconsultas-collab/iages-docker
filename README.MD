# SpainFlow - Sistema de Gestión Documental

Sistema completo de gestión documental para gestorías con IA, multi-tenant, facturación y más.

## 🚀 Características Principales

### Seguridad
- ✅ Autenticación con 2FA (TOTP)
- ✅ Control de acceso basado en roles (RBAC)
- ✅ Aislamiento multi-tenant
- ✅ Rate limiting (50 req/min global, 5 req/min login)
- ✅ Sanitización SQL (protección contra injection)
- ✅ Validación de archivos (límite 50MB)
- ✅ Headers de seguridad (HSTS, CSP, etc.)
- ✅ Sesiones seguras con Redis

### Funcionalidades
- 📄 Procesamiento de documentos con IA (Gemini)
- 🔔 Integración con Saltra DEHU
- 💰 Sistema de facturación y suscripciones
- 📊 Dashboard con métricas y gráficos
- 📧 Envío masivo de emails
- 🔄 Tareas programadas con Celery
- 🌐 Notificaciones push (PWA)
- 📱 Responsive design

### Infraestructura
- ✅ Health checks (/api/health, /api/health/deep)
- ✅ Logging estructurado
- ✅ Reintentos automáticos en Celery
- ✅ Paginación universal
- ✅ Compresión de respuestas
- ✅ Tests automatizados

---

## 📋 Requisitos

### Backend
- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### Frontend
- Node.js 16+
- npm 8+

---

## 🛠️ Instalación

### 1. Backend

```bash
cd backend

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
copy .env.production.example .env
# Editar .env con tus valores

# Inicializar base de datos
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### 2. Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Configurar variables de entorno
copy .env.example .env.local
# Editar .env.local

# Modo desarrollo
npm run dev

# Modo producción
npm run build
```

### 3. Redis

```bash
# Windows (con WSL o instalador)
redis-server

# Linux
sudo systemctl start redis

# Verificar
redis-cli ping  # Debe devolver PONG
```

---

## 🚀 Ejecución

### Desarrollo

```bash
# Terminal 1: Backend (Flask)
cd backend
.venv\Scripts\activate
python app.py

# Terminal 2: Celery Worker
cd backend
.venv\Scripts\activate
celery -A celery_worker worker --loglevel=info --pool=solo

# Terminal 3: Celery Beat (tareas programadas)
cd backend
.venv\Scripts\activate
celery -A celery_worker beat --loglevel=info

# Terminal 4: Frontend
cd frontend
npm run dev
```

### Producción

```bash
# Backend con Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Celery Worker
celery -A celery_worker worker --loglevel=info

# Celery Beat
celery -A celery_worker beat --loglevel=info

# Frontend (servir build)
npm run build
# Servir carpeta dist/ con nginx o similar
```

---

## 🧪 Testing

```bash
cd backend

# Instalar dependencias de testing
pip install -r requirements-test.txt

# Ejecutar tests
pytest test_basic.py -v

# Con cobertura
pytest test_basic.py --cov=. --cov-report=html

# Tests de seguridad
python test_security.py
python test_file_limit.py
python test_rate_limit.py
```

---

## 📊 Health Checks

```bash
# Check básico (para load balancers)
curl http://localhost:5000/api/health

# Check profundo (para monitoreo)
curl http://localhost:5000/api/health/deep
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "checks": {
    "database": {"healthy": true},
    "redis": {"healthy": true},
    "celery": {"healthy": true, "workers": 1},
    "storage": {"healthy": true, "path": "/path/to/storage"}
  },
  "timestamp": "2024-12-30T14:00:00Z"
}
```

---

## 🔐 Variables de Entorno

Ver `.env.production.example` para la lista completa.

### Críticas (Requeridas)

```env
SECRET_KEY=tu_clave_secreta_aqui
TOTP_ENCRYPTION_KEY=clave_32_caracteres_exactos
DATABASE_URI=postgresql://user:pass@localhost/spainflow
REDIS_URL=redis://localhost:6379/0
```

### Opcionales

```env
GEMINI_API_KEY=tu_api_key_gemini
SALTRA_USERNAME=tu_usuario_saltra
SALTRA_PASSWORD=tu_password_saltra
SMTP_SERVER=smtp.gmail.com
SMTP_USER=tu_email@gmail.com
```

---

## 📁 Estructura del Proyecto

```
spainflow/
├── backend/
│   ├── app.py                 # Aplicación Flask principal
│   ├── config.py              # Configuración
│   ├── models.py              # Modelos SQLAlchemy
│   ├── celery_worker.py       # Tareas Celery
│   ├── routes_*.py            # Blueprints de rutas
│   ├── services/              # Lógica de negocio
│   ├── middleware/            # Middleware personalizado
│   ├── utils/                 # Utilidades
│   └── tests/                 # Tests
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Componentes React
│   │   ├── contexts/          # Contextos (Auth, Theme, etc.)
│   │   ├── hooks/             # Custom hooks
│   │   └── utils/             # Utilidades
│   └── public/                # Archivos estáticos
│
└── storage/                   # Almacenamiento de archivos
```

---

## 🔄 Tareas Programadas (Celery Beat)

| Tarea | Frecuencia | Descripción |
|-------|------------|-------------|
| `sincronizar_saltra` | Cada 15 min | Sincroniza notificaciones de Saltra |
| `generar_facturas_mensuales` | Día 1, 00:00 | Genera facturas mensuales |
| `calcular_uso_mensual` | Diario, 02:00 | Calcula uso de recursos |
| `verificar_facturas_vencidas` | Diario, 03:00 | Verifica y suspende por impago |
| `recordatorio_facturas` | Diario, 10:00 | Envía recordatorios de pago |

---

## 🛡️ Seguridad

### Implementado

- ✅ Autenticación 2FA con TOTP
- ✅ Rate limiting en todos los endpoints
- ✅ Sanitización de inputs SQL
- ✅ Validación de tamaño de archivos
- ✅ Headers de seguridad (HSTS, CSP, X-Frame-Options)
- ✅ Sesiones seguras con HttpOnly cookies
- ✅ Aislamiento multi-tenant estricto
- ✅ Logging de auditoría

### Recomendaciones Adicionales

- [ ] Configurar Sentry para monitoreo de errores
- [ ] Implementar WAF (Web Application Firewall)
- [ ] Configurar backups automáticos
- [ ] Habilitar SSL/TLS en producción
- [ ] Configurar firewall de red

---

## 📈 Monitoreo

### Logs

Los logs se guardan en formato estructurado:

```python
logger.info("Mensaje informativo")
logger.warning("Advertencia")
logger.error("Error crítico")
```

### Métricas

- Health checks: `/api/health/deep`
- Uso de recursos: Dashboard de admin
- Celery: Flower (opcional)

---

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

## 📝 Licencia

Propietario - Todos los derechos reservados

---

## 📞 Soporte

Para soporte técnico, contactar a: [email de soporte]

---

## 🎯 Roadmap

### Completado ✅
- Sistema de autenticación y autorización
- Procesamiento de documentos con IA
- Integración Saltra
- Sistema de facturación
- Multi-tenancy
- PWA con notificaciones push

### En Desarrollo 🚧
- Circuit breakers para APIs externas
- Caché de respuestas IA
- Tests de integración completos
- Documentación API con Swagger

### Planeado 📋
- App móvil nativa
- Integración con más APIs gubernamentales
- Dashboard de analytics avanzado
- Exportación de reportes personalizados

---

**Última actualización:** 30 de diciembre de 2024