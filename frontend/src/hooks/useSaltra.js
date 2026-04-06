import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export const useSaltraInbox = (
  page = 1,
  filtroNif = '',
  filtroEstado = '',
  filtroSinEmpresa = false,
  // ✅ FASE 2: Nuevos parámetros de búsqueda avanzada
  filtroIdentifier = '',
  filtroOrganismo = '',
  filtroFechaInicio = '',
  filtroFechaFin = ''
) => {
  return useQuery({
    queryKey: ['saltra-inbox', page, filtroNif, filtroEstado, filtroSinEmpresa, filtroIdentifier, filtroOrganismo, filtroFechaInicio, filtroFechaFin],
    queryFn: async () => {
      const params = new URLSearchParams({ page, limit: 50 });
      if (filtroNif) params.append('nif', filtroNif);
      if (filtroEstado) params.append('estado', filtroEstado);
      if (filtroSinEmpresa) params.append('sin_empresa', 'true');
      // ✅ FASE 2: Agregar nuevos filtros
      if (filtroIdentifier) params.append('identifier', filtroIdentifier);
      if (filtroOrganismo) params.append('emitter_entity', filtroOrganismo);
      if (filtroFechaInicio) params.append('start_date', filtroFechaInicio);
      if (filtroFechaFin) params.append('end_date', filtroFechaFin);

      const [resNotif, resStats] = await Promise.all([
        axios.get(`/api/saltra/notificaciones?${params}`, { withCredentials: true }),
        axios.get('/api/saltra/stats', { withCredentials: true })
      ]);

      return {
        notificaciones: resNotif.data.notificaciones || [],
        total: resNotif.data.total || 0,
        stats: resStats.data.stats || {}
      };
    },
    staleTime: 2 * 60 * 1000,
  });
};

export const useSaltraEmpresas = () => {
  return useQuery({
    queryKey: ['saltra-empresas'],
    queryFn: async () => {
      const res = await axios.get('/api/empresas/lista-simple', { withCredentials: true });
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
};

// ✅ NUEVO: Hook para alertas de vencimiento
export const useAlertasVencimiento = () => {
  return useQuery({
    queryKey: ['alertas-vencimiento'],
    queryFn: async () => {
      const res = await axios.get('/api/saltra/alertas-vencimiento', { withCredentials: true });
      return res.data;
    },
    staleTime: 60 * 1000, // 1 minuto
    refetchInterval: 60 * 1000, // Auto-refresh cada minuto
  });
};

// ✅ Hook para obtener TODAS las notificaciones DEHU pendientes (para calendario)
export const useNotificacionesCalendario = () => {
  return useQuery({
    queryKey: ['notificaciones-calendario'],
    queryFn: async () => {
      const res = await axios.get('/api/saltra/notificaciones-calendario', { withCredentials: true });
      return res.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutos
  });
};
