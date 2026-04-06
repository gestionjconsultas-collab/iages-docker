import { useEffect, useState } from 'react';
import socket from '../socket';

// Solo permite rutas relativas para prevenir open redirect desde datos de WebSocket
const safeRedirect = (url) => {
  if (typeof url === 'string' && url.startsWith('/') && !url.startsWith('//')) {
    window.location.href = url;
  }
};

export default function useNotifications() {
    const [permission, setPermission] = useState(
        typeof Notification !== 'undefined' ? Notification.permission : 'denied'
    );
    const [supported, setSupported] = useState('Notification' in window);

    useEffect(() => {
        if (!supported) return;

        // Listeners de eventos WebSocket
        const handlers = {
            'test_notification': handleTestNotification,
            'nueva_notificacion': handleNuevaNotificacion,
            'documento_procesado': handleDocumentProcessed,
            // ✅ 'error_procesamiento' eliminado — backend no emite este evento
            'recordatorio_vencimiento': handleDeadline, // ✅ Corregido: era 'vencimiento_proximo' (nombre incorrecto)
            'tarea_asignada': handleTaskAssigned,
            'maintenance_warning': handleMaintenanceWarning
        };

        // Registrar listeners
        Object.entries(handlers).forEach(([event, handler]) => {
            socket.on(event, handler);
        });

        // Cleanup — ✅ usa referencia al handler para no quitar listeners de otros componentes
        return () => {
            Object.entries(handlers).forEach(([event, handler]) => {
                socket.off(event, handler);
            });
        };
    }, [supported]);

    const requestPermission = async () => {
        if (!supported) {
            console.warn('Notificaciones no soportadas en este navegador');
            return false;
        }

        try {
            const result = await Notification.requestPermission();
            setPermission(result);
            return result === 'granted';
        } catch (error) {
            console.error('Error solicitando permisos:', error);
            return false;
        }
    };

    const showNotification = (title, options = {}) => {
        if (permission !== 'granted') {
            console.warn('Permisos de notificación no concedidos');
            return null;
        }

        try {
            const notification = new Notification(title, {
                icon: '/logo192.png',
                badge: '/badge-72x72.png',
                vibrate: [200, 100, 200],
                requireInteraction: false,
                ...options
            });

            // Auto-cerrar después de 5 segundos si no requiere interacción
            if (!options.requireInteraction) {
                setTimeout(() => notification.close(), 5000);
            }

            // Click handler
            notification.onclick = () => {
                window.focus();
                notification.close();
                if (options.onClick) {
                    options.onClick();
                }
            };

            return notification;
        } catch (error) {
            console.error('Error mostrando notificación:', error);
            return null;
        }
    };

    const handleTestNotification = (data) => {
        console.log('📢 Notificación de prueba recibida:', data);
        showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            tag: data.tag || 'test-notification'
        });
    };

    const handleNuevaNotificacion = (data) => {
        console.log('🔔 Nueva Notificación (Hook):', data);
        showNotification(data.titulo || 'Nueva Notificación', {
            body: data.mensaje || 'Tienes una nueva notificación',
            tag: `notif-${data.id || Date.now()}`,
            onClick: () => {
                if (data.link) {
                    safeRedirect(data.link);
                }
            }
        });
    };

    const handleDocumentProcessed = (data) => {
        console.log('📄 Documento procesado:', data);
        showNotification('✅ Documento Procesado', {
            body: `${data.nombre_archivo} ha sido procesado exitosamente`,
            tag: `doc-${data.doc_id}`,
            onClick: () => {
                if (data.empresa_id && data.categoria) {
                    safeRedirect(`/empresa/${data.empresa_id}/${data.categoria}`);
                }
            }
        });
    };

    const handleDeadline = (data) => {
        console.log('⏰ Vencimiento próximo:', data);
        const urgency = data.dias <= 1 ? '🚨' : '⏰';
        showNotification(`${urgency} Vencimiento Próximo`, {
            body: `${data.empresa} - Vence en ${data.dias} día${data.dias !== 1 ? 's' : ''}`,
            tag: `deadline-${data.doc_id}`,
            requireInteraction: data.dias <= 1
        });
    };

    const handleTaskAssigned = (data) => {
        console.log('📋 Tarea asignada:', data);
        showNotification('📋 Nueva Tarea Asignada', {
            body: `${data.empresa} - ${data.categoria}`,
            tag: `task-${data.doc_id}`,
            onClick: () => {
                if (data.empresa_id && data.categoria) {
                    safeRedirect(`/empresa/${data.empresa_id}/${data.categoria}`);
                }
            }
        });
    };

    const handleMaintenanceWarning = (data) => {
        console.log('🛠️ Advertencia de mantenimiento:', data);
        showNotification('🛠️ Mantenimiento Programado', {
            body: `El sistema entrará en mantenimiento en ${data.delay_minutes} minutos`,
            tag: 'maintenance-warning',
            requireInteraction: true
        });
    };

    return {
        permission,
        supported,
        requestPermission,
        showNotification
    };
}
