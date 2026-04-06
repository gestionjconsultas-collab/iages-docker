// frontend/src/hooks/useDehuConnection.js
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_BASE = '/api/dehu-espana';

export const useDehuConnection = () => {
    const queryClient = useQueryClient();

    // Query para verificar estado de conexión
    const { data: statusData, isLoading: isCheckingStatus } = useQuery({
        queryKey: ['dehu-status'],
        queryFn: async () => {
            const { data } = await axios.get(`${API_BASE}/status`);
            return data;
        },
        refetchInterval: 30000, // Verificar cada 30 segundos
        retry: false
    });

    // Mutation para conectar
    const connectMutation = useMutation({
        mutationFn: async ({ pfxFile, passphrase }) => {
            const formData = new FormData();
            formData.append('pfx_file', pfxFile);
            formData.append('passphrase', passphrase);

            const { data } = await axios.post(`${API_BASE}/connect`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return data;
        },
        onSuccess: (data) => {
            toast.success('Conectado a DEHú exitosamente');
            queryClient.invalidateQueries(['dehu-status']);
            queryClient.invalidateQueries(['dehu-notifications']);
        },
        onError: (error) => {
            const message = error.response?.data?.message || 'Error al conectar';
            toast.error(message);
        }
    });

    // Mutation para desconectar
    const disconnectMutation = useMutation({
        mutationFn: async () => {
            const { data } = await axios.post(`${API_BASE}/disconnect`);
            return data;
        },
        onSuccess: () => {
            toast.success('Sesión cerrada');
            queryClient.invalidateQueries(['dehu-status']);
            queryClient.invalidateQueries(['dehu-notifications']);
        },
        onError: (error) => {
            toast.error('Error al desconectar');
        }
    });

    return {
        isConnected: statusData?.connected || false,
        userInfo: statusData?.user_info,
        isCheckingStatus,
        connect: connectMutation.mutate,
        disconnect: disconnectMutation.mutate,
        isConnecting: connectMutation.isPending,
        isDisconnecting: disconnectMutation.isPending
    };
};
