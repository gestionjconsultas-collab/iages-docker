import React, { useState, useEffect } from 'react';
import { Bell, X, Check } from 'lucide-react';
import { usePushNotifications } from '../hooks/usePushNotifications';

/**
 * Banner amigable para solicitar permisos de notificaciones del navegador
 * Se muestra solo si los permisos están en estado 'default'
 */
const NotificationPermissionBanner = () => {
    const [show, setShow] = useState(false);
    const [isDismissed, setIsDismissed] = useState(false);
    const [isSubscribing, setIsSubscribing] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);

    const { isSupported, requestPermission: subscribePush } = usePushNotifications();

    useEffect(() => {
        const checkStatus = async () => {
            const registered = localStorage.getItem('pushRegistered') === 'true';
            const permission = Notification.permission;

            // Si no está registrado en el servidor, mostramos el banner
            if (isSupported && !registered) {
                if (permission === 'default' || permission === 'granted') {
                    setShow(true);
                }
            }

            if (permission === 'denied') {
                console.warn('🚫 El permiso de notificaciones está DENIED.');
            }
        };

        checkStatus();
    }, [isSupported]);

    const handleActivate = async () => {
        setIsSubscribing(true);
        try {
            const success = await subscribePush();
            if (success) {
                setIsSuccess(true);
                localStorage.setItem('pushRegistered', 'true');
                // Auto-cerrar después de éxito
                setTimeout(() => {
                    setShow(false);
                    localStorage.setItem('notificationBannerDismissed', 'true');
                }, 3000);
            } else {
                // Si falla o deniega
                setShow(false);
                localStorage.setItem('notificationBannerDismissed', 'true');
            }
        } catch (error) {
            console.error('Error al activar notificaciones:', error);
            setShow(false);
        } finally {
            setIsSubscribing(false);
        }
    };

    const dismissBanner = () => {
        setShow(false);
        localStorage.setItem('notificationBannerDismissed', 'true');
    };

    if (!show) return null;

    return (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 max-w-2xl w-full mx-4">
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-lg shadow-2xl p-4 animate-slideDown">
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 flex-1">
                        <div className="bg-white/20 p-2 rounded-full">
                            <Bell className="w-6 h-6" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-lg mb-1">
                                Activa las notificaciones
                            </h3>
                            <p className="text-sm text-blue-100">
                                Recibe alertas importantes sobre tareas y documentos, incluso cuando no estés viendo la app
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-2">
                        {isSuccess ? (
                            <div className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white font-semibold rounded-lg shadow-md animate-in zoom-in">
                                <Check className="w-5 h-5" /> ¡Activado!
                            </div>
                        ) : (
                            <button
                                onClick={handleActivate}
                                disabled={isSubscribing}
                                className={`px-4 py-2 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50 transition-colors shadow-md ${isSubscribing ? 'opacity-50 cursor-wait' : ''}`}
                            >
                                {isSubscribing ? 'Activando...' : 'Activar'}
                            </button>
                        )}
                        <button
                            onClick={dismissBanner}
                            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            aria-label="Cerrar"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default NotificationPermissionBanner;
