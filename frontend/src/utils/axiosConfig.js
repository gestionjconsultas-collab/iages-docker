/**
 * Axios Configuration - Interceptors para manejo de errores
 * 
 * Silencia errores de red en producción para evitar spam en console
 */

import axios from 'axios';
import { devError, devWarn } from './logger';

// ✅ CRÍTICO: Enviar cookies en todas las peticiones
axios.defaults.withCredentials = true;

// Interceptor de respuestas para manejo de errores
axios.interceptors.response.use(
    response => response,
    error => {
        const isDev = import.meta.env.DEV;
        const status = error.response?.status;
        const url = error.config?.url;

        // ⚠️ SESIÓN EXPIRADA - Redirigir a login en 401
        if (status === 401) {
            const publicPaths = ['/login', '/reset-password', '/reset_password', '/maintenance'];
            const isPublic = publicPaths.some(p => window.location.pathname.startsWith(p));
            if (!isPublic) {
                window.location.href = '/login';
            }
            return Promise.reject(error);
        }

        // ⚠️ MODO DE MANTENIMIENTO - Prioridad máxima
        // Detectar 503 con flag de mantenimiento O cualquier 503 del backend
        const isMaintenanceMode = status === 503 && (
            error.response?.data?.maintenance === true ||
            error.response?.data?.error === 'Sistema en mantenimiento'
        );

        if (isMaintenanceMode) {
            console.log('🛠️ Modo de mantenimiento detectado, redirigiendo...');
            // Redirigir a página de mantenimiento
            if (window.location.pathname !== '/maintenance') {
                window.location.href = '/maintenance';
            }
            return Promise.reject(error);
        }

        // En desarrollo, mostrar todos los errores
        if (isDev) {
            // Rate limiting (429)
            if (status === 429) {
                devWarn(`⚠️ Rate limit alcanzado: ${url}`);
            }
            // Errores de servidor (5xx)
            else if (status >= 500) {
                devError(`❌ Error del servidor (${status}): ${url}`);
            }
            // Errores de cliente (4xx)
            else if (status >= 400 && status !== 401) {
                devError(`❌ Error de petición (${status}): ${url}`);
            }
            // Errores de red
            else if (error.message === 'Network Error') {
                devError('❌ Error de red - Servidor no disponible');
            }
        }

        // En producción, solo mostrar errores críticos
        else {
            // Solo mostrar errores de servidor (5xx) y errores de red
            if (status >= 500 || error.message === 'Network Error') {
                console.error('Error de conexión con el servidor');
            }
            // Silenciar 429, 404, 401, etc. en producción
        }

        // Siempre rechazar la promesa para que el código pueda manejar el error
        return Promise.reject(error);
    }
);

// Interceptor de peticiones (opcional - para debugging)
axios.interceptors.request.use(
    config => {
        // En desarrollo, loggear peticiones si es necesario
        // devLog(`📤 ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    error => {
        devError('Error en petición:', error);
        return Promise.reject(error);
    }
);

export default axios;
