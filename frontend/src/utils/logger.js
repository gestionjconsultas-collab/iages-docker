/**
 * Logger Utility - Environment-based logging
 * 
 * Uso:
 *   import { devLog, devWarn, devError, devTable } from '@/utils/logger';
 * 
 *   devLog('Mensaje de debug');
 *   devWarn('Advertencia');
 *   devError('Error crítico');
 *   devTable(data);
 */

// Detectar si estamos en desarrollo
const isDev = import.meta.env.DEV || import.meta.env.VITE_DEBUG === 'true';

/**
 * Log solo en desarrollo
 */
export const devLog = (...args) => {
    if (isDev) {
        console.log(...args);
    }
};

/**
 * Warning solo en desarrollo
 */
export const devWarn = (...args) => {
    if (isDev) {
        console.warn(...args);
    }
};

/**
 * Error - siempre se muestra (es crítico)
 */
export const devError = (...args) => {
    console.error(...args);
};

/**
 * Table solo en desarrollo
 */
export const devTable = (...args) => {
    if (isDev) {
        console.table(...args);
    }
};

/**
 * Group solo en desarrollo
 */
export const devGroup = (label, fn) => {
    if (isDev) {
        console.group(label);
        fn();
        console.groupEnd();
    }
};

/**
 * Time solo en desarrollo
 */
export const devTime = (label) => {
    if (isDev) {
        console.time(label);
    }
};

export const devTimeEnd = (label) => {
    if (isDev) {
        console.timeEnd(label);
    }
};

/**
 * Info sobre el entorno actual
 */
export const logEnvironment = () => {
    if (isDev) {
        console.log('🔧 Modo:', import.meta.env.MODE);
        console.log('🌍 Entorno:', import.meta.env.DEV ? 'Desarrollo' : 'Producción');
        console.log('🐛 Debug:', import.meta.env.VITE_DEBUG);
    }
};

// Log inicial del entorno (solo una vez)
if (isDev) {
    console.log('%c🚀 IAGES Dashboard - Modo Desarrollo', 'color: #3B82F6; font-size: 14px; font-weight: bold');
}

export default {
    devLog,
    devWarn,
    devError,
    devTable,
    devGroup,
    devTime,
    devTimeEnd,
    logEnvironment
};
