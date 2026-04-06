import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export const useEmpresa = (empresaId, enabled = true) => {
  const navigate = useNavigate();

  return useQuery({
    queryKey: ['empresa', empresaId],
    queryFn: async () => {
      try {
        const [empRes, countRes] = await Promise.all([
          axios.get(`/api/empresas/${empresaId}`, { withCredentials: true }),
          axios.get(`/api/empresas/${empresaId}/categorias-conteo`, { withCredentials: true })
        ]);

        return {
          empresa: empRes.data.empresa,
          conteos: countRes.data.conteos
        };
      } catch (error) {
        console.error('Error cargando empresa:', error);

        // Si es error 404, la empresa no pertenece a la gestoría
        if (error.response?.status === 404) {
          toast.error('⛔ No tienes acceso a esta empresa');
          setTimeout(() => navigate('/empresas'), 1000);
        }

        throw error;
      }
    },
    enabled: enabled && !!empresaId,
    retry: false, // No reintentar en caso de error
    staleTime: 0, // Forzar refresco inmediato tras invalidación
  });
};