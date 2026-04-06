# 🎯 PASOS PARA EXPONER SPAINFLOW CON NGROK

## ✅ YA HECHO
- [x] Ngrok instalado
- [x] Authtoken configurado

## 📝 SIGUIENTE PASO

### 1. Detener Ngrok Actual
En la terminal donde corre ngrok, presionar: **Ctrl + C**

### 2. Verificar que SpainFlow Corre

**Terminal 1 - Backend**:
```bash
cd backend
python app.py
# Debe mostrar: Running on http://127.0.0.1:5000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm start
# Debe abrir: http://localhost:3000
```

### 3. Iniciar Ngrok en Puerto Correcto

**Terminal 3 - Ngrok**:
```bash
ngrok http 3000
```

**NO** `ngrok http 80` (puerto incorrecto)

### 4. Compartir URL

Ngrok mostrará algo como:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:3000
```

**Esa URL es la que compartes**: `https://abc123.ngrok-free.app`

---

## 🔍 VERIFICACIÓN

1. **Abrir URL de ngrok** en navegador
2. **Hacer login** con tus credenciales
3. **Navegar** a `/super-admin/dashboard`
4. **Probar funcionalidades**:
   - Ver gráficos
   - Exportar reportes (después de reiniciar Flask)
   - Ver gestorías

---

## ⚠️ IMPORTANTE

- **Puerto 3000**: React frontend
- **Puerto 5000**: Flask backend (no necesita ngrok, el frontend hace proxy)
- **URL temporal**: Cambia cada vez que reinicias ngrok (gratis)
- **Válida mientras**: Ngrok esté corriendo

---

## 🎊 LISTO PARA DEMO

Una vez que ngrok esté en puerto 3000, puedes compartir la URL con cualquiera.

**Credenciales de acceso**: Enviar por separado (email, WhatsApp, etc.)
