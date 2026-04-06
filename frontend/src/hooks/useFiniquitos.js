import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useFiniquitos = (empresaId) => {
  return useQuery({
    queryKey: ['finiquitos', empresaId],
    queryFn: async () => {
      const res = await axios.get(`/api/empresas/${empresaId}/finiquitos`, { withCredentials: true });
      return res.data;
    },
    enabled: !!empresaId,
    staleTime: 2 * 60 * 1000,
  });
};