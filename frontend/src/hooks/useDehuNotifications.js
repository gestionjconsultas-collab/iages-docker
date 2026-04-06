// frontend/src/hooks/useDehuNotifications.js
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE = '/api/dehu-espana';

export const useDehuNotifications = (type = 'pending', options = {}) => {
    const {
        page = 1,
        limit = 50,
        daysBack = 7,
        enabled = true
    } = options;

    // Query para notificaciones pendientes
    const pendingQuery = useQuery({
        queryKey: ['dehu-notifications', 'pending', page, limit],
        queryFn: async () => {
            const { data } = await axios.get(`${API_BASE}/notifications/pending`, {
                params: { page, limit }
            });
            return data.data;
        },
        enabled: enabled && type === 'pending',
        retry: false
    });

    // Query para notificaciones realizadas
    const realizedQuery = useQuery({
        queryKey: ['dehu-notifications', 'realized', daysBack, page, limit],
        queryFn: async () => {
            const { data } = await axios.get(`${API_BASE}/notifications/realized`, {
                params: { days_back: daysBack, page, limit }
            });
            return data.data;
        },
        enabled: enabled && type === 'realized',
        retry: false
    });

    const activeQuery = type === 'pending' ? pendingQuery : realizedQuery;

    return {
        notifications: activeQuery.data?.items || [],
        total: activeQuery.data?.total || 0,
        page: activeQuery.data?.page || 1,
        limit: activeQuery.data?.limit || 50,
        isLoading: activeQuery.isLoading,
        isError: activeQuery.isError,
        error: activeQuery.error,
        refetch: activeQuery.refetch
    };
};

export const useDehuNotificationDetail = (sentReference, type = 'pending', enabled = false) => {
    return useQuery({
        queryKey: ['dehu-notification-detail', sentReference, type],
        queryFn: async () => {
            const { data } = await axios.get(
                `${API_BASE}/notifications/${sentReference}/detail`,
                { params: { type } }
            );
            return data.data;
        },
        enabled: enabled && !!sentReference,
        retry: false
    });
};
