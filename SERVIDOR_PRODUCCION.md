# 🖥️ Especificaciones de Servidor para Producción - IAGES Dashboard

## 📋 Resumen Ejecutivo

**Sistema Operativo Recomendado:** Ubuntu Server 22.04 LTS o 24.04 LTS  
**Tipo de Servidor:** VPS o Servidor Dedicado  
**Recursos Mínimos:** 4GB RAM, 2 vCPU, 50GB SSD  
**Recursos Recomendados:** 8GB RAM, 4 vCPU, 100GB SSD

---

## 🐧 Sistema Operativo

### ✅ Opción Recomendada: Ubuntu Server 22.04 LTS

**¿Por qué Ubuntu?**
- ✅ Soporte a largo plazo (LTS = 5 años de actualizaciones)
- ✅ Amplia documentación y comunidad
- ✅ Fácil instalación de dependencias
- ✅ Compatible con todas las tecnologías del stack
- ✅ Actualizaciones de seguridad automáticas

**Alternativas válidas:**
- Debian 12 (más estable, menos actualizaciones)
- Rocky Linux 9 (alternativa a CentOS)
- AlmaLinux 9 (alternativa a CentOS)

**❌ NO recomendado:**
- Windows Server (mayor costo, menor rendimiento para Python/Node.js)
- Distribuciones sin soporte LTS

---

## 💻 Especificaciones de Hardware

### 🟢 Configuración Mínima (1-10 usuarios)

```
CPU:      2 vCPU (cores virtuales)
RAM:      4 GB
Disco:    50 GB SSD
Ancho:    100 Mbps
```

**Casos de uso:**
- Pruebas de producción
- Empresas pequeñas (1-2 gestorías)
- Hasta 10 usuarios concurrentes

**Costo aproximado:** €10-20/mes

---

### 🟡 Configuración Recomendada (10-50 usuarios)

```
CPU:      4 vCPU
RAM:      8 GB
Disco:    100 GB SSD
Ancho:    500 Mbps
```

**Casos de uso:**
- Producción estándar
- 3-10 gestorías
- 10-50 usuarios concurrentes
- Procesamiento de documentos moderado

**Costo aproximado:** €30-50/mes

---

### 🔴 Configuración Óptima (50+ usuarios)

```
CPU:      8 vCPU
RAM:      16 GB
Disco:    200 GB SSD NVMe
Ancho:    1 Gbps
```

**Casos de uso:**
- Producción de alto tráfico
- 10+ gestorías
- 50+ usuarios concurrentes
- Procesamiento intensivo de documentos
- Múltiples workers de Celery

**Costo aproximado:** €80-120/mes

---

## 🏢 Proveedores Recomendados

### 1. DigitalOcean (Recomendado para empezar)

**Ventajas:**
- ✅ Interfaz muy simple
- ✅ Documentación excelente
- ✅ Backups automáticos (+20% del costo)
- ✅ Snapshots gratuitos
- ✅ Firewall incluido
- ✅ Monitoreo básico incluido

**Planes recomendados:**
- **Basic Droplet:** 4GB RAM, 2 vCPU, 80GB SSD → $24/mes
- **Regular Droplet:** 8GB RAM, 4 vCPU, 160GB SSD → $48/mes

**Ubicación:** Frankfurt o Amsterdam (más cerca de España)

🔗 https://www.digitalocean.com

---

### 2. Hetzner (Mejor relación calidad-precio)

**Ventajas:**
- ✅ Muy económico
- ✅ Servidores en Alemania (baja latencia)
- ✅ Excelente rendimiento
- ✅ Soporte en español

**Planes recomendados:**
- **CX21:** 4GB RAM, 2 vCPU, 40GB SSD → €5.83/mes
- **CX31:** 8GB RAM, 2 vCPU, 80GB SSD → €10.59/mes
- **CX41:** 16GB RAM, 4 vCPU, 160GB SSD → €19.90/mes

**Ubicación:** Falkenstein o Helsinki

🔗 https://www.hetzner.com

---

### 3. Linode (Akamai)

**Ventajas:**
- ✅ Rendimiento consistente
- ✅ Backups automáticos
- ✅ Soporte 24/7
- ✅ Red global de alta velocidad

**Planes recomendados:**
- **Linode 4GB:** 4GB RAM, 2 vCPU, 80GB SSD → $24/mes
- **Linode 8GB:** 8GB RAM, 4 vCPU, 160GB SSD → $48/mes

**Ubicación:** Frankfurt

🔗 https://www.linode.com

---

### 4. AWS EC2 (Para empresas grandes)

**Ventajas:**
- ✅ Escalabilidad infinita
- ✅ Servicios adicionales (RDS, S3, etc.)
- ✅ Alta disponibilidad

**Desventajas:**
- ❌ Más complejo de configurar
- ❌ Más costoso
- ❌ Facturación variable

**Planes recomendados:**
- **t3.medium:** 4GB RAM, 2 vCPU → ~$30/mes
- **t3.large:** 8GB RAM, 2 vCPU → ~$60/mes

**Ubicación:** eu-west-1 (Irlanda) o eu-south-1 (Milán)

🔗 https://aws.amazon.com/ec2

---

### 5. OVH (Opción española)

**Ventajas:**
- ✅ Empresa europea (GDPR)
- ✅ Servidores en España
- ✅ Soporte en español
- ✅ Precios competitivos

**Planes recomendados:**
- **VPS Value:** 4GB RAM, 2 vCPU, 80GB SSD → €6.99/mes
- **VPS Essential:** 8GB RAM, 4 vCPU, 160GB SSD → €13.99/mes

**Ubicación:** Gravelines (Francia) o Madrid

🔗 https://www.ovhcloud.com

---

## 📦 Software Necesario

### Stack Completo

```bash
# Sistema Operativo
Ubuntu Server 22.04 LTS

# Backend
Python 3.11+
PostgreSQL 15+
Redis 7+
Nginx 1.24+
Gunicorn 21+

# Tareas Asíncronas
Celery 5+
Supervisor

# Monitoreo
Prometheus
Sentry (SaaS)

# Seguridad
Certbot (Let's Encrypt)
Fail2ban
UFW (Firewall)

# Utilidades
Git
Vim/Nano
htop
```

---

## 🔧 Configuración Inicial del Servidor

### 1. Actualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Configurar Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 3. Instalar Dependencias Base

```bash
# Python y herramientas
sudo apt install -y python3.11 python3.11-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx

# Git
sudo apt install -y git

# Supervisor (para Celery)
sudo apt install -y supervisor

# Certbot (SSL)
sudo apt install -y certbot python3-certbot-nginx
```

---

## 💾 Almacenamiento

### Distribución Recomendada de Disco

```
/                    20 GB   (Sistema operativo)
/var/www/iages       10 GB   (Aplicación)
/var/www/uploads     30 GB   (Archivos subidos)
/var/lib/postgresql  20 GB   (Base de datos)
/var/backups         20 GB   (Backups)
```

### Crecimiento Estimado

- **Base de datos:** ~100 MB/mes por gestoría
- **Archivos:** ~1-5 GB/mes por gestoría (depende del volumen)
- **Logs:** ~500 MB/mes

**Recomendación:** Empezar con 100GB y monitorear crecimiento

---

## 🌐 Dominio y DNS

### Requisitos

1. **Dominio propio** (ej: `tuempresa.com`)
2. **Configuración DNS:**
   ```
   A     @              -> IP_DEL_SERVIDOR
   A     www            -> IP_DEL_SERVIDOR
   A     app            -> IP_DEL_SERVIDOR (opcional)
   CNAME api            -> tuempresa.com (opcional)
   ```

### Proveedores de Dominio

- Namecheap
- GoDaddy
- Cloudflare (incluye CDN gratis)
- Google Domains

---

## 🔒 Seguridad

### Medidas Obligatorias

- ✅ Firewall (UFW) configurado
- ✅ SSH con clave pública (deshabilitar password)
- ✅ Fail2ban contra ataques de fuerza bruta
- ✅ SSL/TLS (Let's Encrypt)
- ✅ Actualizaciones automáticas de seguridad
- ✅ Usuario no-root para la aplicación
- ✅ Backups automáticos diarios

### Configuración SSH Segura

```bash
# Editar /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

---

## 📊 Monitoreo

### Herramientas Incluidas

- **Sentry:** Tracking de errores (SaaS)
- **Prometheus:** Métricas del sistema
- **Nginx logs:** Tráfico HTTP
- **PostgreSQL logs:** Queries lentas

### Opcional (Recomendado)

- **Grafana:** Visualización de métricas
- **Uptime Robot:** Monitoreo de disponibilidad (gratis)
- **New Relic / Datadog:** APM completo (de pago)

---

## 💰 Estimación de Costos Mensual

### Configuración Básica (10 usuarios)

```
Servidor (Hetzner CX21):        €5.83
Dominio:                        €1.00
Backups (opcional):             €2.00
Sentry (gratis hasta 5K eventos): €0
--------------------------------
TOTAL:                          ~€9/mes
```

### Configuración Recomendada (50 usuarios)

```
Servidor (Hetzner CX41):        €19.90
Dominio:                        €1.00
Backups:                        €5.00
Sentry Team:                    €26/mes
--------------------------------
TOTAL:                          ~€52/mes
```

### Configuración Enterprise (100+ usuarios)

```
Servidor (AWS t3.large):        €60
Dominio:                        €1
RDS PostgreSQL:                 €30
S3 Storage:                     €10
Backups:                        €10
Sentry Business:                €80
CloudFlare Pro:                 €20
--------------------------------
TOTAL:                          ~€211/mes
```

---

## 🚀 Recomendación Final

### Para Empezar (Fase 1)

**Proveedor:** Hetzner  
**Plan:** CX31 (8GB RAM, 2 vCPU, 80GB SSD)  
**Costo:** €10.59/mes  
**SO:** Ubuntu Server 22.04 LTS  

**¿Por qué?**
- Excelente relación calidad-precio
- Suficiente para 20-30 usuarios
- Fácil de escalar
- Servidores en Europa (GDPR)

### Cuando Crezcas (Fase 2)

**Proveedor:** DigitalOcean o AWS  
**Plan:** 16GB RAM, 4 vCPU  
**Costo:** €50-80/mes  
**Extras:** Load balancer, base de datos gestionada

---

## 📞 Soporte

### ¿Necesitas ayuda con la configuración?

1. **Documentación oficial:** Revisa `DEPLOYMENT_SERVIDOR_PROPIO.md`
2. **Checklist:** Usa `PRODUCTION_CHECKLIST.md`
3. **Comunidad:** Stack Overflow, Reddit r/selfhosted

---

## ✅ Checklist Rápido

- [ ] Elegir proveedor de servidor
- [ ] Contratar servidor (Ubuntu 22.04 LTS)
- [ ] Configurar dominio y DNS
- [ ] Configurar firewall y seguridad
- [ ] Instalar dependencias
- [ ] Configurar SSL/TLS
- [ ] Desplegar aplicación
- [ ] Configurar backups
- [ ] Configurar monitoreo
- [ ] Probar en producción

---

**Última actualización:** Enero 2026
