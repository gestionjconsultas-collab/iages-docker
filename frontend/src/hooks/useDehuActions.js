// frontend/src/hooks/useDehuActions.js
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE = '/api/dehu-espana';

export const useDehuActions = () => {
    const queryClient = useQueryClient();

    // Mutation para aceptar notificación
    const acceptMutation = useMutation({
        mutationFn: async (sentReference) => {
            const { data } = await axios.post(
                `${API_BASE}/notifications/${sentReference}/accept`
            );
            return data;
        },
        onSuccess: (data) => {
            toast.success('Notificación aceptada exitosamente');
            // Invalidar queries para refrescar listas
            queryClient.invalidateQueries(['dehu-notifications']);
        },
        onError: (error) => {
            const message = error.response?.data?.message || 'Error al aceptar notificación';
            toast.error(message);
        }
    });

    // Mutation para descargar documento
    const downloadMutation = useMutation({
        mutationFn: async ({ sentReference, type = 'annexe' }) => {
            const response = await axios.get(
                `${API_BASE}/notifications/${sentReference}/download`,
                {
                    params: { type },
                    responseType: 'blob'
                }
            );
            return { data: response.data, sentReference, type };
        },
        onSuccess: ({ data, sentReference, type }) => {
            // Crear URL del blob y descargar
            const url = window.URL.createObjectURL(new Blob([data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${sentReference.substring(0, 20)}_${type}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            toast.success('Documento descargado');
        },
        onError: (error) => {
            const message = error.response?.data?.message || 'Error al descargar documento';
            toast.error(message);
            throw error; // Re-throw para manejar en el componente si es necesario
        }
    });

    return {
        acceptNotification: acceptMutation.mutate,
        isAccepting: acceptMutation.isPending,
        downloadDocument: downloadMutation.mutate,
        downloadDocumentAsync: downloadMutation.mutateAsync,
        isDownloading: downloadMutation.isPending
    };
};
