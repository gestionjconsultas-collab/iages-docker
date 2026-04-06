import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

/**
 * Hook para implementar infinite scroll con paginación backend
 * 
 * @param {string} endpoint - URL del endpoint (ej: '/api/empresas')
 * @param {number} initialPerPage - Items por página (default: 50)
 * @param {object} params - Parámetros adicionales para el request
 * @returns {object} - { items, loading, error, hasMore, loadMore, reset }
 * 
 * @example
 * const { items: empresas, loading, hasMore } = useInfiniteScroll('/api/empresas', 50);
 */
export function useInfiniteScroll(endpoint, initialPerPage = 50, params = {}) {
    const [items, setItems] = useState([]);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [initialLoad, setInitialLoad] = useState(true);

    const loadMore = useCallback(async () => {
        if (loading || !hasMore) return;

        setLoading(true);
        setError(null);

        try {
            const res = await axios.get(endpoint, {
                params: {
                    page,
                    per_page: initialPerPage,
                    ...params
                },
                withCredentials: true
            });

            // Manejar respuesta paginada
            if (res.data.items && res.data.pagination) {
                setItems(prev => [...prev, ...res.data.items]);
                setHasMore(res.data.pagination.has_next);
                setPage(prev => prev + 1);
            } else {
                // Fallback para endpoints sin paginación
                console.warn(`Endpoint ${endpoint} no devuelve formato paginado`);
                setItems(res.data.empresas || res.data.items || []);
                setHasMore(false);
            }
        } catch (err) {
            console.error('Error loading more items:', err);
            setError(err.message);
        } finally {
            setLoading(false);
            setInitialLoad(false);
        }
    }, [endpoint, page, loading, hasMore, initialPerPage, params]);

    // Auto-load inicial
    useEffect(() => {
        if (initialLoad) {
            loadMore();
        }
    }, [initialLoad, loadMore]);

    // Scroll detection
    useEffect(() => {
        const handleScroll = () => {
            // Detectar si está cerca del final (500px antes)
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
                loadMore();
            }
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, [loadMore]);

    const reset = useCallback(() => {
        setItems([]);
        setPage(1);
        setHasMore(true);
        setError(null);
        setInitialLoad(true);
    }, []);

    return {
        items,
        loading,
        error,
        hasMore,
        loadMore,
        reset,
        isInitialLoad: initialLoad
    };
}
