import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useStats = () => {
  return useQuery({
    queryKey: ['estadisticas'],
    queryFn: async () => {
      const res = await axios.get('/api/dashboard/estadisticas', { withCredentials: true });
      // Retornar solo stats para que data.estadisticas funcione
      return { estadisticas: res.data.stats || {} };
    },
    staleTime: 5 * 60 * 1000,
  });
};