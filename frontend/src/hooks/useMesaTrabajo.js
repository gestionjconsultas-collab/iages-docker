import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useMesaTrabajo = (page = 1, search = '', empresaFilter = '') => {
  return useQuery({
    queryKey: ['mesa-trabajo', page, search, empresaFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('per_page', 50);
      if (search) params.append('search', search);
      if (empresaFilter) params.append('empresa_id', empresaFilter);
      
      const res = await axios.get(`/api/mesa-trabajo/pendientes?${params}`, { 
        withCredentials: true 
      });
      return res.data;
    },
    staleTime: 1 * 60 * 1000,
  });
};

export const useMesaTrabajoStats = () => {
  return useQuery({
    queryKey: ['mesa-trabajo-stats'],
    queryFn: async () => {
      const res = await axios.get('/api/mesa-trabajo/stats', { withCredentials: true });
      return res.data;
    },
    staleTime: 30 * 1000,
  });
};