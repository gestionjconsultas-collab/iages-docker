// frontend/src/utils/NotificationManager.js
/**
 * Gestiona las notificaciones del navegador (Browser Notifications API)
 */
class NotificationManager {
    /**
     * Solicita permiso al usuario para mostrar notificaciones
     * @returns {Promise<string>} 'granted', 'denied', o 'default'
     */
    static async requestPermission() {
        if (!('Notification' in window)) {
            console.warn('Este navegador no soporta notificaciones');
            return 'denied';
        }

        if (Notification.permission === 'default') {
            return await Notification.requestPermission();
        }

        return Notification.permission;
    }

    /**
     * Muestra una notificación del navegador
     * @param {string} title - Título de la notificación
     * @param {string} body - Cuerpo del mensaje
     * @param {object} data - Datos adicionales (ticket_id, etc.)
     * @returns {Notification|null} Objeto de notificación o null si no se pudo mostrar
     */
    static show(title, body, data = {}) {
        if (!('Notification' in window)) {
            return null;
        }

        if (Notification.permission !== 'granted') {
            console.log('Permisos de notificación no concedidos');
            return null;
        }

        try {
            const notification = new Notification(title, {
                body,
                icon: '/logo192.png', // Usar logo de la app
                badge: '/logo192.png',
                tag: `ticket-${data.ticket_id}`, // Evita duplicados
                requireInteraction: false, // Se cierra automáticamente
                silent: false,
                data
            });

            // Handler para click en la notificación
            notification.onclick = () => {
                window.focus(); // Enfocar la ventana

                // Emitir evento personalizado para abrir el chat
                window.dispatchEvent(new CustomEvent('open-ticket-chat', {
                    detail: { ticketId: data.ticket_id }
                }));

                notification.close();
            };

            // Auto-cerrar después de 5 segundos
            setTimeout(() => {
                notification.close();
            }, 5000);

            return notification;
        } catch (error) {
            console.error('Error mostrando notificación:', error);
            return null;
        }
    }

    /**
     * Verifica si las notificaciones están habilitadas
     * @returns {boolean}
     */
    static isEnabled() {
        return 'Notification' in window && Notification.permission === 'granted';
    }

    /**
     * Verifica si las notificaciones están soportadas
     * @returns {boolean}
     */
    static isSupported() {
        return 'Notification' in window;
    }
}

export default NotificationManager;
