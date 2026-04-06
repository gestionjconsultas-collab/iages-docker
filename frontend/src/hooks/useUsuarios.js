import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useUsuarios = () => {
  return useQuery({
    queryKey: ['usuarios'],
    queryFn: async () => {
      const [resUsers, resDept] = await Promise.all([
        axios.get('/api/users', { withCredentials: true }),
        axios.get('/api/departamentos', { withCredentials: true })
      ]);

      return {
        users: resUsers.data.users || [],
        departamentos: resDept.data.departamentos || []
      };
    },
    staleTime: 0, // Siempre fresh para evitar confusión en admin
  });
};