import React, { useState, useEffect } from 'react';
import './ToastNotifications.css';

import { useAuth } from '../AuthContext';

/**
 * Sistema de notificaciones toast para WebSocket events
 * Muestra notificaciones en tiempo real con animaciones suaves y sonidos
 */
const ToastNotifications = ({ socket }) => {
    const { checkAuthStatus } = useAuth();
    const [toasts, setToasts] = useState([]);

    // ⭐ Control de sonidos (respeta preferencias del usuario)
    const [soundEnabled, setSoundEnabled] = useState(
        localStorage.getItem('notificationSounds') !== 'false'
    );

    // ⭐ Función para reproducir sonido de notificación
    const playNotificationSound = (type = 'info') => {
        if (!soundEnabled) return;

        // Usar Web Audio API para sonidos más suaves
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        // Frecuencias según tipo
        const frequencies = {
            success: 800,  // Tono alto agradable
            info: 600,     // Tono medio
            warning: 500,  // Tono medio-bajo
            error: 400     // Tono bajo
        };

        oscillator.frequency.value = frequencies[type] || frequencies.info;
        oscillator.type = 'sine'; // Onda suave

        // Volumen bajo y fade out
        gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    };

    useEffect(() => {
        if (!socket) return;

        // ✅ Handlers con nombre para poder hacer cleanup selectivo (evita quitar listeners de otros componentes)

        const handleTareaChatIA = (data) => {
            playNotificationSound('success');
            addToast({ id: Date.now(), type: 'success', icon: '🤖', title: 'Chat IA', message: data.mensaje, duration: 5000 });
        };

        const handleDocumentoProcesado = (data) => {
            playNotificationSound('info');
            addToast({ id: Date.now(), type: 'info', icon: '📄', title: 'Documento Procesado', message: data.mensaje, duration: 5000 });
        };

        const handleTareaAsignada = (data) => {
            playNotificationSound('info');
            addToast({ id: Date.now(), type: 'info', icon: '📋', title: 'Nueva Tarea', message: data.mensaje, duration: 5000 });
        };

        const handleRecordatorioVencimiento = (data) => {
            const type = data.horas_restantes <= 24 ? 'error' : 'warning';
            addToast({ id: Date.now(), type, icon: data.horas_restantes <= 24 ? '🚨' : '⚠️', title: 'Recordatorio', message: data.mensaje, duration: 7000 });
        };

        const handleNotificacionSaltra = (data) => {
            addToast({ id: Date.now(), type: 'info', icon: '📨', title: 'SALTRA', message: data.mensaje, duration: 6000 });
        };

        const handlePermissionsUpdated = (data) => {
            console.log('🔄 Permisos actualizados:', data);
            if (checkAuthStatus) checkAuthStatus();
            addToast({ id: Date.now(), type: 'info', icon: '🔐', title: 'Seguridad', message: data.mensaje, duration: 6000 });
        };

        // ✅ Listener para notificaciones personalizadas del backend (notify_custom)
        const handleNotificacionCustom = (data) => {
            const iconMap = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
            const type = ['success', 'error', 'warning', 'info'].includes(data.tipo) ? data.tipo : 'info';
            addToast({ id: Date.now(), type, icon: iconMap[type], title: 'Notificación', message: data.mensaje, duration: 5000 });
        };

        socket.on('tarea_chat_ia', handleTareaChatIA);
        socket.on('documento_procesado', handleDocumentoProcesado);
        socket.on('tarea_asignada', handleTareaAsignada);
        socket.on('recordatorio_vencimiento', handleRecordatorioVencimiento);
        socket.on('notificacion_saltra', handleNotificacionSaltra);
        socket.on('permissions_updated', handlePermissionsUpdated);
        socket.on('notificacion_custom', handleNotificacionCustom);

        // ✅ Cleanup selectivo — solo elimina ESTOS handlers, no los de otros componentes
        return () => {
            socket.off('tarea_chat_ia', handleTareaChatIA);
            socket.off('documento_procesado', handleDocumentoProcesado);
            socket.off('tarea_asignada', handleTareaAsignada);
            socket.off('recordatorio_vencimiento', handleRecordatorioVencimiento);
            socket.off('notificacion_saltra', handleNotificacionSaltra);
            socket.off('permissions_updated', handlePermissionsUpdated);
            socket.off('notificacion_custom', handleNotificacionCustom);
        };
    }, [socket]);

    const addToast = (toast) => {
        setToasts(prev => {
            // Máximo 3 toasts visibles
            const newToasts = [toast, ...prev].slice(0, 3);
            return newToasts;
        });

        // Auto-remove después de duration
        setTimeout(() => {
            removeToast(toast.id);
        }, toast.duration);
    };

    const removeToast = (id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    if (toasts.length === 0) return null;

    return (
        <div className="toast-container">
            {toasts.map(toast => (
                <div
                    key={toast.id}
                    className={`toast toast-${toast.type}`}
                    onClick={() => removeToast(toast.id)}
                >
                    <div className="toast-icon">{toast.icon}</div>
                    <div className="toast-content">
                        <div className="toast-title">{toast.title}</div>
                        <div className="toast-message">{toast.message}</div>
                    </div>
                    <button
                        className="toast-close"
                        onClick={(e) => {
                            e.stopPropagation();
                            removeToast(toast.id);
                        }}
                        aria-label="Cerrar"
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
};

export default ToastNotifications;
