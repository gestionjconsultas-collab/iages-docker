# Guía de Despliegue a Producción - Sistema de Facturación

## ✅ Estado Actual

### Configuraciones Completadas
- ✅ **Email SMTP**: Configurado con SMTP centralizado y nombres dinámicos por gestoría
- ✅ **Celery Beat**: Configurado con todas las tareas programadas
- ✅ **Tareas Programadas**: 4 tareas de facturación + 4 tareas de sistema

---

## 📋 Checklist Pre-Producción

### 1. Configuración de Email SMTP

**Estado:** ✅ YA CONFIGURADO

El sistema usa un solo SMTP centralizado con personalización del nombre del remitente:
- Archivo: `backend/email_sender.py`
- Función: `_get_smtp_config(gestoria_id)`
- Formato: `"Nombre Gestoría <email@centralizado.com>"`

**Variables de entorno requeridas en `.env`:**
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-contraseña-app
```

**Para producción:**
1. Crear cuenta de email corporativa
2. Generar contraseña de aplicación
3. Actualizar `.env` con credenciales reales
4. Probar envío de email de prueba

---

### 2. Celery Beat - Tareas Programadas

**Estado:** ✅ YA CONFIGURADO

**Tareas de Facturación:**
- `generar-facturas-mensuales`: Día 1 a las 00:00
- `calcular-uso-mensual`: Diario a las 02:00
- `verificar-facturas-vencidas`: Diario a las 03:00
- `recordatorios-facturas`: Diario a las 10:00

**Cómo iniciar Celery Beat:**

```bash
# Terminal 1: Celery Worker
cd backend
celery -A celery_worker worker --loglevel=info --pool=solo

# Terminal 2: Celery Beat (scheduler)
celery -A celery_worker beat --loglevel=info
```

**Para producción (Windows Service o PM2):**
```bash
# Con PM2
pm2 start celery_worker.py --name celery-worker
pm2 start celery_beat.py --name celery-beat
pm2 save
```

---

### 3. Configuración de IAGES

**Pendiente:** ⚠️ ACTUALIZAR ANTES DE PRODUCCIÓN

Actualizar en `backend/.env` o base de datos:
```bash
IAGES_CIF=B12345678
IAGES_IBAN=ES1234567890123456789012
```

Estos datos se usan en:
- Generación de facturas PDF
- Emails de facturación
- Instrucciones de pago

---

### 4. Base de Datos - Backup

**Crear script de backup:**

```bash
# backup_db.bat (Windows)
@echo off
set BACKUP_DIR=C:\backups\spainflow
set TIMESTAMP=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%
set BACKUP_FILE=%BACKUP_DIR%\backup_%TIMESTAMP%.sql

mkdir %BACKUP_DIR% 2>nul

pg_dump -U postgres -h localhost spainflow_db > %BACKUP_FILE%

echo Backup creado: %BACKUP_FILE%
```

**Programar backup diario:**
- Windows: Programador de tareas
- Linux: Crontab

**Procedimiento de restauración:**
```bash
psql -U postgres -h localhost spainflow_db < backup_YYYYMMDD_HHMM.sql
```

---

### 5. Pruebas de Facturación

**Checklist de pruebas:**

- [ ] Generar factura manualmente para una gestoría
- [ ] Verificar PDF se genera correctamente
- [ ] Descargar PDF desde la interfaz
- [ ] Verificar email se envía con factura adjunta
- [ ] Verificar datos de IAGES en factura
- [ ] Probar cambio de plan
- [ ] Probar aplicación de cupón
- [ ] Verificar cálculo de uso mensual

**Comando para prueba manual:**
```python
from services.billing_service import BillingService
from models_billing import Suscripcion

# Generar factura para suscripción ID 1
factura = BillingService.generar_factura_mensual(1)
print(f"Factura generada: {factura.numero_factura}")
```

---

## 🚀 Pasos para Ir a Producción

### 1. Configuración Final
- [ ] Actualizar CIF e IBAN de IAGES
- [ ] Configurar SMTP con credenciales reales
- [ ] Verificar variables de entorno en producción

### 2. Iniciar Servicios
```bash
# 1. Iniciar Redis
redis-server

# 2. Iniciar Celery Worker
celery -A celery_worker worker --loglevel=info --pool=solo

# 3. Iniciar Celery Beat
celery -A celery_worker beat --loglevel=info

# 4. Iniciar Flask
python app.py
```

### 3. Verificación Post-Despliegue
- [ ] Verificar Celery Beat está corriendo
- [ ] Verificar tareas programadas aparecen en logs
- [ ] Enviar email de prueba
- [ ] Generar factura de prueba
- [ ] Verificar PDF se descarga correctamente

### 4. Monitoreo
- Revisar logs de Celery diariamente
- Verificar emails se envían correctamente
- Monitorear facturas generadas
- Revisar errores en logs

---

## 📞 Soporte

**En caso de problemas:**
1. Revisar logs de Celery
2. Verificar Redis está corriendo
3. Verificar credenciales SMTP
4. Revisar logs de Flask

**Logs importantes:**
- `celery_worker.log`
- `celery_beat.log`
- `flask.log`
