import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useAuditoria = (filters = {}) => {
  return useQuery({
    queryKey: ['auditoria', filters],
    queryFn: async () => {
      const params = new URLSearchParams(filters);
      const res = await axios.get(`/api/auditoria/logs?${params}`, { withCredentials: true });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};