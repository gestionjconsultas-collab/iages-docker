// frontend/src/hooks/useGruposDocumentos.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

// Obtener grupos de una empresa
export const useGrupos = (empresaId) => {
  return useQuery({
    queryKey: ['grupos', empresaId],
    queryFn: async () => {
      const params = empresaId ? { empresa_id: empresaId } : {};
      const { data } = await axios.get('/api/grupos-documentos', { params });
      return data.grupos;
    },
    enabled: !!empresaId
  });
};

// Obtener un grupo específico con sus documentos
export const useGrupo = (grupoId) => {
  return useQuery({
    queryKey: ['grupo', grupoId],
    queryFn: async () => {
      const { data } = await axios.get(`/api/grupos-documentos/${grupoId}`);
      return data.grupo;
    },
    enabled: !!grupoId
  });
};

// Obtener grupos de un documento
export const useGruposDeDocumento = (documentoId) => {
  return useQuery({
    queryKey: ['grupos-documento', documentoId],
    queryFn: async () => {
      const { data } = await axios.get(`/api/documentos/${documentoId}/grupos`);
      return data.grupos;
    },
    enabled: !!documentoId
  });
};

// Crear grupo
export const useCrearGrupo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (grupoData) => {
      const { data } = await axios.post('/api/grupos-documentos', grupoData);
      return data.grupo;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['grupos', variables.empresa_id] });
      toast.success('Grupo creado correctamente');
    },
    onError: (error) => {
      toast.error(error.response?.data?.error || 'Error al crear grupo');
    }
  });
};

// Eliminar grupo
export const useEliminarGrupo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (grupoId) => {
      await axios.delete(`/api/grupos-documentos/${grupoId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['grupos'] });
      toast.success('Grupo eliminado');
    },
    onError: (error) => {
      toast.error(error.response?.data?.error || 'Error al eliminar grupo');
    }
  });
};

// Agregar documento a grupo
export const useAgregarDocumentoAGrupo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ grupoId, documentoId }) => {
      const { data } = await axios.post(
        `/api/grupos-documentos/${grupoId}/documentos`,
        { documento_id: documentoId }
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['grupo', variables.grupoId] });
      queryClient.invalidateQueries({ queryKey: ['grupos-documento', variables.documentoId] });
      toast.success('Documento agregado al grupo');
    },
    onError: (error) => {
      toast.error(error.response?.data?.error || 'Error al agregar documento');
    }
  });
};

// Quitar documento de grupo
export const useQuitarDocumentoDeGrupo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ grupoId, documentoId }) => {
      await axios.delete(`/api/grupos-documentos/${grupoId}/documentos/${documentoId}`);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['grupo', variables.grupoId] });
      queryClient.invalidateQueries({ queryKey: ['grupos-documento', variables.documentoId] });
      toast.success('Documento quitado del grupo');
    },
    onError: (error) => {
      toast.error(error.response?.data?.error || 'Error al quitar documento');
    }
  });
};

// Enviar email masivo
export const useEnviarEmailMasivo = () => {
  return useMutation({
    mutationFn: async ({ grupoId, destinatarios, asunto, mensaje }) => {
      const { data } = await axios.post(
        `/api/grupos-documentos/${grupoId}/enviar-email`,
        {
          destinatarios,
          asunto,
          mensaje
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      return data;
    },
    onSuccess: (data) => {
      toast.success(data.mensaje || 'Email enviado correctamente');
    },
    onError: (error) => {
      toast.error(error.response?.data?.error || 'Error al enviar email');
    }
  });
};