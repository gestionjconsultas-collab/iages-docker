import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

/**
 * Hook para gestionar Empresas
 */
/**
 * Hook para obtener todas las empresas con estadísticas
 */
export const useEmpresasStats = () => useQuery({
  queryKey: ['empresas'],
  queryFn: async () => {
    const res = await axios.get('/api/empresas', { withCredentials: true });
    return res.data;
  },
  staleTime: 5 * 60 * 1000,
});

/**
 * Hook para obtener listado simple (id, nombre, nif)
 */
export const useEmpresasListadoSimple = () => useQuery({
  queryKey: ['empresas', 'lista-simple'],
  queryFn: async () => {
    const res = await axios.get('/api/empresas/lista-simple', { withCredentials: true });
    return res.data.empresas || [];
  },
  staleTime: 10 * 60 * 1000,
});