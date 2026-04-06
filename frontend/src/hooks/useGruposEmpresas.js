import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { toast } from 'react-hot-toast';

/**
 * Hook para gestionar Agrupaciones de Empresas (Holdings)
 */
/**
 * Hook para listar grupos
 */
export const useGrupos = () => useQuery({
    queryKey: ['grupos-empresas'],
    queryFn: async () => {
        const res = await axios.get('/api/grupos-empresas', { withCredentials: true });
        return res.data.grupos || [];
    }
});

/**
 * Hook para crear grupo
 */
export const useCrearGrupo = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (nuevoGrupo) => {
            const res = await axios.post('/api/grupos-empresas', nuevoGrupo, { withCredentials: true });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['grupos-empresas'] });
            toast.success('Agrupación creada correctamente');
        },
        onError: (err) => {
            toast.error(err.response?.data?.error || 'Error al crear la agrupación');
        }
    });
};

/**
 * Hook para actualizar grupo
 */
export const useActualizarGrupo = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, ...datos }) => {
            const res = await axios.put(`/api/grupos-empresas/${id}`, datos, { withCredentials: true });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['grupos-empresas'] });
            toast.success('Agrupación actualizada');
        }
    });
};

/**
 * Hook para eliminar grupo
 */
export const useEliminarGrupo = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (id) => {
            const res = await axios.delete(`/api/grupos-empresas/${id}`, { withCredentials: true });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['grupos-empresas'] });
            queryClient.invalidateQueries({ queryKey: ['empresas'] });
            toast.success('Agrupación eliminada');
        }
    });
};

/**
 * Hook para asignar empresas a grupo
 */
export const useAsignarEmpresas = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async ({ id, empresa_ids }) => {
            const res = await axios.post(`/api/grupos-empresas/${id}/asignar`, { empresa_ids }, { withCredentials: true });
            return res.data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['grupos-empresas'] });
            queryClient.invalidateQueries({ queryKey: ['empresas'] });
            toast.success('Empresas asignadas correctamente');
        }
    });
};
/**
 * Hook para importar grupos desde Excel
 */
export const useImportarGruposExcel = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: async (file) => {
            const formData = new FormData();
            formData.append('file', file);
            const res = await axios.post('/api/admin/grupos/import-excel', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                withCredentials: true
            });
            return res.data;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['grupos-empresas'] });
            queryClient.invalidateQueries({ queryKey: ['empresas'] });
            
            const exitosos = data.exitosos?.length || 0;
            const errores = data.errores?.length || 0;
            
            if (errores > 0) {
                toast.success(`Importación finalizada: ${exitosos} correctos, ${errores} errores`);
            } else {
                toast.success(`Importación exitosa: ${exitosos} grupos creados/actualizados`);
            }
        },
        onError: (err) => {
            toast.error(err.response?.data?.error || 'Error al importar el archivo Excel');
        }
    });
};

/**
 * Función para descargar la plantilla de importación de grupos
 */
export const descargarPlantillaGrupos = async () => {
    try {
        const response = await axios.get('/api/admin/grupos/plantilla-excel', {
            responseType: 'blob',
            withCredentials: true
        });
        
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'plantilla_importar_grupos.xlsx');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error descargando plantilla:', error);
        toast.error('Error al descargar la plantilla');
    }
};
