// frontend/src/utils/urls.js

/**
 * Retorna la URL del backend dinámicamente según el entorno
 */
export const getBackendUrl = () => {
    // Si estamos en desarrollo (localhost:3000 o similar)
    if (window.location.origin.includes('localhost:') || window.location.origin.includes('127.0.0.1')) {
        // Si Vite está sirviendo en el puerto 3000, el backend suele estar en el 5000
        if (window.location.port === '3000' || window.location.port === '5173') {
            return 'http://localhost:5000';
        }
    }

    // En producción, usamos el mismo origen
    return window.location.origin;
};

export const BACKEND_URL = getBackendUrl();
