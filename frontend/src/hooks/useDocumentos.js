import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useDocumentos = (empresaId, categoria, enabled = true) => {
  return useQuery({
    queryKey: ['documentos', empresaId, categoria],
    queryFn: async () => {
      // ✅ CORRECCIÓN: Usar query parameter ?categoria=X en lugar de path
      const url = `/api/empresas/${empresaId}/documentos${categoria ? `?categoria=${categoria}` : ''}`;
      const res = await axios.get(url, { withCredentials: true });
      return res.data;
    },
    enabled: enabled && !!empresaId,
    staleTime: 2 * 60 * 1000, // 2 minutos (documentos cambian más seguido)
  });
};