// frontend/src/contexts/TenantContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { devLog, devWarn, devError } from '../utils/logger';
import { BACKEND_URL } from '../utils/urls';

const TenantContext = createContext();

export const TenantProvider = ({ children }) => {
    const [tenant, setTenant] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        detectTenant();
    }, []);

    const detectTenant = async () => {
        try {
            // MULTI-TENANT: Detectar tenant desde el usuario logueado
            const response = await axios.get('/api/tenant/info', {
                withCredentials: true,
                timeout: 5000
            });

            if (response.data.success) {
                setTenant(response.data.tenant);
                applyBranding(response.data.tenant);
            } else {
                throw new Error('Tenant not found');
            }
        } catch (error) {
            devError('Error detectando tenant:', error);
            setError(error.message);

            // Fallback a tenant por defecto
            const fallbackTenant = {
                slug: 'principal',
                nombre: 'IAGES',
                configuracion: {}
            };
            setTenant(fallbackTenant);
            applyBranding(fallbackTenant);
        } finally {
            setLoading(false);
        }
    };

    // Helper para ajustar brillo de colores (hex)
    const adjustBrightness = (color, percent) => {
        try {
            const hex = color.replace('#', '');
            const num = parseInt(hex, 16);
            const amt = Math.round(2.55 * percent);

            const R = Math.max(0, Math.min(255, (num >> 16) + amt));
            const G = Math.max(0, Math.min(255, ((num >> 8) & 0x00FF) + amt));
            const B = Math.max(0, Math.min(255, (num & 0x0000FF) + amt));

            return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`;
        } catch (error) {
            devError('Error ajustando brillo:', error);
            return color;
        }
    };

    // Helper para actualizar favicon
    const updateFavicon = (faviconUrl) => {
        try {
            let link = document.querySelector("link[rel*='icon']");

            // Crear elemento si no existe
            if (!link) {
                link = document.createElement('link');
                link.rel = 'icon';
                document.head.appendChild(link);
            }

            // Actualizar href
            link.href = faviconUrl;
            devLog('🔄 [TenantContext] Favicon actualizado a:', faviconUrl);
        } catch (error) {
            devError('Error actualizando favicon:', error);
        }
    };

    const applyBranding = (tenant) => {
        try {
            devLog('🎨 [TenantContext] Aplicando branding para:', tenant.nombre);
            devLog('📦 [TenantContext] Configuración completa:', tenant.configuracion);

            const root = document.documentElement;
            const config = tenant.configuracion || {};
            const branding = config.branding || {};
            const colores = branding.colores || {};

            devLog('🎨 [TenantContext] Colores encontrados:', colores);

            // Aplicar colores personalizados
            if (colores.primario) {
                devLog('✅ [TenantContext] Aplicando color primario:', colores.primario);
                root.style.setProperty('--color-primary', colores.primario);
                root.style.setProperty('--color-primary-hover', adjustBrightness(colores.primario, -10));
                root.style.setProperty('--color-primary-light', adjustBrightness(colores.primario, 40));
                root.style.setProperty('--color-primary-dark', adjustBrightness(colores.primario, -20));
            } else {
                devWarn('⚠️ [TenantContext] No hay color primario configurado');
            }

            if (colores.secundario) {
                devLog('✅ [TenantContext] Aplicando color secundario:', colores.secundario);
                root.style.setProperty('--color-secondary', colores.secundario);
                root.style.setProperty('--color-secondary-hover', adjustBrightness(colores.secundario, -10));
                root.style.setProperty('--color-secondary-light', adjustBrightness(colores.secundario, 40));
                root.style.setProperty('--color-secondary-dark', adjustBrightness(colores.secundario, -20));
            }

            if (colores.acento) {
                devLog('✅ [TenantContext] Aplicando color acento:', colores.acento);
                root.style.setProperty('--color-accent', colores.acento);
                root.style.setProperty('--color-accent-hover', adjustBrightness(colores.acento, -10));
                root.style.setProperty('--color-accent-light', adjustBrightness(colores.acento, 40));
            }

            // Aplicar favicon personalizado o usar default de IAGES
            if (branding.favicon_url) {
                devLog('✅ [TenantContext] Aplicando favicon personalizado:', branding.favicon_url);
                updateFavicon(`${BACKEND_URL}${branding.favicon_url}`);
            } else {
                devLog('ℹ️ [TenantContext] Usando favicon por defecto de IAGES');
                updateFavicon('/favicon.png'); // Favicon por defecto de IAGES
            }

            // Actualizar título de la página
            document.title = tenant.nombre || 'IAGES';
            devLog('✅ [TenantContext] Branding aplicado correctamente');

        } catch (error) {
            devError('❌ [TenantContext] Error aplicando branding:', error);
        }
    };

    return (
        <TenantContext.Provider value={{
            tenant,
            loading,
            error,
            refreshTenant: detectTenant
        }}>
            {children}
        </TenantContext.Provider>
    );
};

export const useTenant = () => {
    const context = useContext(TenantContext);
    if (!context) {
        throw new Error('useTenant debe usarse dentro de TenantProvider');
    }
    return context;
};
