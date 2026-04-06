import { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import { devLog, devError } from '../utils/logger';

const PermisosContext = createContext();

export const PermisosProvider = ({ children }) => {
    const { user } = useAuth();
    const [permisos, setPermisos] = useState([]);
    const [rol, setRol] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            cargarPermisos();
        } else {
            setPermisos([]);
            setRol(null);
            setLoading(false);
        }
    }, [user]);

    const cargarPermisos = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/mis-permisos', {
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error('Error al cargar permisos');
            }

            const data = await response.json();

            if (data.success) {
                setPermisos(data.permisos || []);
                setRol(data.rol);
                devLog('✅ [PermisosContext] Permisos cargados:', data.permisos);
            }
        } catch (error) {
            devError('❌ [PermisosContext] Error cargando permisos:', error);
            setPermisos([]);
            setRol(null);
        } finally {
            setLoading(false);
        }
    };

    const tienePermiso = (codigo) => {
        // Super-admin tiene todos los permisos
        if (user?.is_super_admin) {
            return true;
        }

        // Verificar si tiene el permiso específico o wildcard
        return permisos.includes(codigo) || permisos.includes('*');
    };

    const tieneAlgunPermiso = (codigos) => {
        // Verificar si tiene al menos uno de los permisos
        return codigos.some(codigo => tienePermiso(codigo));
    };

    const tieneTodosPermisos = (codigos) => {
        // Verificar si tiene todos los permisos
        return codigos.every(codigo => tienePermiso(codigo));
    };

    const value = {
        permisos,
        rol,
        loading,
        tienePermiso,
        tieneAlgunPermiso,
        tieneTodosPermisos,
        recargarPermisos: cargarPermisos
    };

    return (
        <PermisosContext.Provider value={value}>
            {children}
        </PermisosContext.Provider>
    );
};

export const usePermisos = () => {
    const context = useContext(PermisosContext);
    if (!context) {
        throw new Error('usePermisos debe usarse dentro de PermisosProvider');
    }
    return context;
};
