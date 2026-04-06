import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useDocumentosPaged = (empresaId, categoria, page = 1, limit = 50) => {
  return useQuery({
    queryKey: ['documentos', empresaId, categoria, page],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      });
      
      if (categoria) {
        params.append('categoria', categoria);
      }
      
      const res = await axios.get(
        `/api/empresas/${empresaId}/documentos/paged?${params}`,
        { withCredentials: true }
      );
      
      return res.data;
    },
    enabled: !!empresaId,
    keepPreviousData: true // Mantiene datos anteriores mientras carga nuevos
  });
};