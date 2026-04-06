import { useEffect } from 'react';
import socket from '../socket';

export function useSocketConnection() {
    useEffect(() => {
        const onConnectError = (err) => {
            console.warn('[Socket] connect_error:', err.message);
        };
        const onDisconnect = (reason) => {
            console.warn('[Socket] disconnected:', reason);
        };
        const onReconnect = (attempt) => {
            console.info('[Socket] reconnected after', attempt, 'attempts');
        };
        const onReconnectFailed = () => {
            console.error('[Socket] reconnect failed permanently');
        };

        socket.on('connect_error', onConnectError);
        socket.on('disconnect', onDisconnect);
        socket.on('reconnect', onReconnect);
        socket.on('reconnect_failed', onReconnectFailed);

        return () => {
            socket.off('connect_error', onConnectError);
            socket.off('disconnect', onDisconnect);
            socket.off('reconnect', onReconnect);
            socket.off('reconnect_failed', onReconnectFailed);
        };
    }, []);
}
