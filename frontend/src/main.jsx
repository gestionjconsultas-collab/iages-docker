// frontend/src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'

// 1. Estilos de Tailwind (versión 4)
import './index.css'

// 1.5. Configuración global de Axios (interceptors)
import './utils/axiosConfig'

// 2. Estilos de librerías externas (IMPORTANTE: Cargar estos antes de tus overrides)
import 'react-datepicker/dist/react-datepicker.css'
import 'react-big-calendar/lib/css/react-big-calendar.css' // <--- AÑADE ESTO AQUÍ

// 3. Tus estilos personalizados
import './calendar.css'
// import './datepicker.css' // Si ya no lo usas, puedes borrarlo o dejarlo

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)

// ⭐ Registrar Service Worker SOLO en producción
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        console.log('✅ Service Worker registrado:', registration.scope);

        // ⭐ Verificar actualizaciones cada 5 minutos
        setInterval(() => {
          registration.update();
        }, 5 * 60 * 1000);

        // ⭐ Detectar nueva versión disponible
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // Hay una nueva versión esperando
              console.log('🆕 Nueva versión disponible');

              // Notificar al componente UpdatePrompt
              window.dispatchEvent(new CustomEvent('swUpdateAvailable'));
            }
          });
        });
      })
      .catch((error) => {
        console.error('❌ Error registrando Service Worker:', error);
      });
  });

  // ⭐ Recargar cuando el SW se active
  let refreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!refreshing) {
      refreshing = true;
      window.location.reload();
    }
  });
}
