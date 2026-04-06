// frontend/src/hooks/useCalendarioTributario.js
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

/**
 * Hook para obtener fechas del calendario tributario de la AEAT
 * 
 * @param {string} fechaInicio - Fecha de inicio en formato YYYY-MM-DD (opcional)
 * @param {string} fechaFin - Fecha de fin en formato YYYY-MM-DD (opcional)
 * @param {string} tipoImpuesto - Filtrar por tipo de impuesto (opcional)
 * @param {string} modelo - Filtrar por modelo (opcional)
 * @returns {object} Query result con eventos tributarios
 */
export function useCalendarioTributario(fechaInicio, fechaFin, tipoImpuesto, modelo) {
    return useQuery({
        queryKey: ['calendario-tributario', fechaInicio, fechaFin, tipoImpuesto, modelo],
        queryFn: async () => {
            const params = {};
            if (fechaInicio) params.fecha_inicio = fechaInicio;
            if (fechaFin) params.fecha_fin = fechaFin;
            if (tipoImpuesto) params.tipo_impuesto = tipoImpuesto;
            if (modelo) params.modelo = modelo;

            const { data } = await axios.get('/api/calendario/tributario', {
                params,
                withCredentials: true
            });

            return data;
        },
        staleTime: 1000 * 60 * 60, // 1 hora (las fechas tributarias no cambian frecuentemente)
        enabled: true, // Siempre habilitado
    });
}

/**
 * Hook para obtener tipos de impuesto disponibles
 */
export function useTiposImpuesto() {
    return useQuery({
        queryKey: ['tipos-impuesto'],
        queryFn: async () => {
            const { data } = await axios.get('/api/calendario/tributario/tipos', {
                withCredentials: true
            });
            return data;
        },
        staleTime: 1000 * 60 * 60 * 24, // 24 horas
    });
}

/**
 * Hook para obtener modelos disponibles
 */
export function useModelos() {
    return useQuery({
        queryKey: ['modelos'],
        queryFn: async () => {
            const { data } = await axios.get('/api/calendario/tributario/modelos', {
                withCredentials: true
            });
            return data;
        },
        staleTime: 1000 * 60 * 60 * 24, // 24 horas
    });
}

/**
 * Hook para sincronizar manualmente el calendario AEAT
 */
export function useSincronizarCalendario() {
    const sincronizar = async (year) => {
        try {
            const { data } = await axios.post('/api/calendario/tributario/sincronizar',
                { year },
                { withCredentials: true }
            );
            return data;
        } catch (error) {
            throw error;
        }
    };

    return { sincronizar };
}
