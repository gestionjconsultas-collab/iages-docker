import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import axios from 'axios';
import socket from '../socket';

export const useNoClasificados = () => {
  const queryClient = useQueryClient();

  // Escuchar evento en tiempo real cuando Conecta sube un archivo al inbox
  useEffect(() => {
    const handleInboxActualizado = () => {
      queryClient.invalidateQueries({ queryKey: ['no-clasificados'] });
    };

    socket.on('inbox_actualizado', handleInboxActualizado);

    return () => {
      socket.off('inbox_actualizado', handleInboxActualizado);
    };
  }, [queryClient]);

  return useQuery({
    queryKey: ['no-clasificados'],
    queryFn: async () => {
      const [resArchivos, resEmpresas] = await Promise.all([
        axios.get('/api/archivos-no-clasificados', { withCredentials: true }),
        axios.get('/api/empresas/lista-simple', { withCredentials: true })
      ]);

      return {
        files: resArchivos.data.files || [],
        empresas: resEmpresas.data.empresas || []
      };
    },
    staleTime: 30 * 1000, // 30 segundos
  });
};
