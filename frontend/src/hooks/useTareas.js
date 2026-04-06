import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useTareas = () => {
  return useQuery({
    queryKey: ['tareas'],
    queryFn: async () => {
      const res = await axios.get('/api/tareas/calendario', { withCredentials: true });
      return res.data;
    },
    staleTime: 1 * 60 * 1000, // 1 minuto (tareas son dinámicas)
  });
};