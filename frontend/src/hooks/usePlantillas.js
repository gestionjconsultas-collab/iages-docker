import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const usePlantillas = () => {
  return useQuery({
    queryKey: ['plantillas'],
    queryFn: async () => {
      const res = await axios.get('/api/plantillas', { withCredentials: true });
      return res.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutos (cambian poco)
  });
};