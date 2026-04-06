# PWA Icons - IAGES

## Generar Iconos

Los iconos para la PWA deben estar en la carpeta `public/icons/`.

### Tamaños Requeridos

- 72x72
- 96x96
- 128x128
- 144x144
- 152x152
- 192x192
- 384x384
- 512x512

### Opción 1: Usar una herramienta online

1. Ve a https://realfavicongenerator.net/
2. Sube tu logo (preferiblemente 512x512 o mayor)
3. Descarga el paquete completo
4. Coloca los archivos en `public/icons/`

### Opción 2: Usar ImageMagick (línea de comandos)

```bash
# Instalar ImageMagick primero
# Windows: choco install imagemagick
# Mac: brew install imagemagick
# Linux: sudo apt-get install imagemagick

# Generar todos los tamaños desde un logo original
convert logo.png -resize 72x72 public/icons/icon-72x72.png
convert logo.png -resize 96x96 public/icons/icon-96x96.png
convert logo.png -resize 128x128 public/icons/icon-128x128.png
convert logo.png -resize 144x144 public/icons/icon-144x144.png
convert logo.png -resize 152x152 public/icons/icon-152x152.png
convert logo.png -resize 192x192 public/icons/icon-192x192.png
convert logo.png -resize 384x384 public/icons/icon-384x384.png
convert logo.png -resize 512x512 public/icons/icon-512x512.png
```

### Opción 3: Usar PWA Asset Generator

```bash
npx @vite-pwa/assets-generator --preset minimal public/logo.svg public/icons
```

## Iconos de Shortcuts

También necesitas crear iconos para los shortcuts (96x96):

- `shortcut-mesa.png` - Icono para Mesa de Trabajo
- `shortcut-empresas.png` - Icono para Empresas
- `shortcut-dashboard.png` - Icono para Dashboard

## Favicon

Coloca también un `favicon.png` en `public/` (192x192 recomendado).

## Verificar

Una vez generados los iconos, verifica que la PWA funcione:

1. Abre Chrome DevTools
2. Ve a Application > Manifest
3. Verifica que todos los iconos se carguen correctamente
4. Prueba instalar la app desde el navegador
