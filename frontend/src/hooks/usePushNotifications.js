import { useState, useEffect } from 'react';
import axios from '../utils/axiosConfig';

/**
 * Hook para manejar notificaciones push
 * Solicita permiso, suscribe al usuario y maneja notificaciones
 */
export function usePushNotifications() {
    const [permission, setPermission] = useState('default');
    const [subscription, setSubscription] = useState(null);
    const [isSupported, setIsSupported] = useState(false);

    useEffect(() => {
        // Verificar soporte
        const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && window.isSecureContext;
        setIsSupported(supported);

        if (supported) {
            const currentPermission = Notification.permission;
            setPermission(currentPermission);

            if (currentPermission === 'granted') {
                // Pasar los valores frescos para evitar cierres obsoletos (stale closures)
                checkExistingSubscription(supported, currentPermission);
            }
        } else {
            console.error('❌ Este navegador no soporta Push Notifications o no es un contexto seguro.');
        }
    }, []);

    const checkExistingSubscription = async (forcedSupported, forcedPermission) => {
        const checkSupported = forcedSupported !== undefined ? forcedSupported : isSupported;
        const checkPermission = forcedPermission !== undefined ? forcedPermission : (typeof Notification !== 'undefined' ? Notification.permission : 'default');

        if (!checkSupported) return;

        try {
            const registration = await navigator.serviceWorker.ready;
            const existingSub = await registration.pushManager.getSubscription();

            if (existingSub) {
                setSubscription(existingSub);
                localStorage.setItem('pushRegistered', 'true');

                // Actualizar en el servidor por si acaso
                await axios.post('/api/push/subscribe', {
                    subscription: existingSub.toJSON()
                });
            } else if (checkPermission === 'granted') {
                // Si hay permiso pero no suscripción, crearla
                await subscribe(checkSupported, checkPermission);
            }
        } catch (error) {
            console.error('Error al verificar suscripción:', error);
        }
    };

    /**
     * Solicitar permiso para notificaciones
     */
    const requestPermission = async () => {
        if (!isSupported) {
            return false;
        }

        try {
            const result = await Notification.requestPermission();
            setPermission(result);

            if (result === 'granted') {
                await subscribe(isSupported, result);
                return true;
            }

            return false;
        } catch (error) {
            console.error('Error solicitando permiso:', error);
            return false;
        }
    };

    /**
     * Suscribir al usuario a push notifications
     */
    const subscribe = async (forcedSupported, forcedPermission) => {
        // Usar valores pasados o valores frescos del BOM para evitar estados de React obsoletos
        const currentSupported = forcedSupported !== undefined ? forcedSupported : isSupported;
        const currentPermission = forcedPermission !== undefined ? forcedPermission : (typeof Notification !== 'undefined' ? Notification.permission : 'default');

        if (!currentSupported || currentPermission !== 'granted') {
            return null;
        }

        try {
            // Obtener service worker registration
            const registration = await navigator.serviceWorker.ready;

            // Obtener clave pública VAPID del servidor
            const vapidResponse = await axios.get('/api/push/vapid-public-key');
            const vapidPublicKey = vapidResponse.data.publicKey;

            // Convertir clave a Uint8Array
            const applicationServerKey = urlBase64ToUint8Array(vapidPublicKey);

            // Suscribirse
            console.log('🛰️ Suscribiendo vía pushManager...');
            const newSubscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });
            console.log('✅ Suscripción de navegador obtenida:', newSubscription.endpoint);

            // Guardar suscripción en el servidor
            console.log('💾 Guardando suscripción en el servidor...');
            const saveResponse = await axios.post('/api/push/subscribe', {
                subscription: newSubscription.toJSON()
            });
            console.log('✅ Respuesta del servidor:', saveResponse.data);

            setSubscription(newSubscription);
            localStorage.setItem('pushRegistered', 'true');
            console.log('🚀 ¡Suscrito a push notifications con éxito!');
            return pushSubscription;

        } catch (error) {
            console.error('❌ Error crítico en el flujo de suscripción:', error);
            // Si el error es que ya existe una suscripción, podemos intentar recuperarla
            return null;
        }
    };

    /**
     * Desuscribir de push notifications
     */
    const unsubscribe = async () => {
        if (!subscription) return;

        try {
            // Desuscribir del navegador
            await subscription.unsubscribe();

            // Notificar al servidor
            await axios.post('/api/push/unsubscribe', {
                endpoint: subscription.endpoint
            });

            setSubscription(null);
            console.log('✅ Desuscrito de push notifications');
        } catch (error) {
            console.error('Error desuscribiendo:', error);
        }
    };

    /**
     * Enviar notificación de prueba
     */
    const sendTestNotification = async () => {
        try {
            const { data } = await axios.post('/api/push/test');
            return data.success;
        } catch (error) {
            console.error('Error enviando notificación de prueba:', error);
            return false;
        }
    };

    return {
        isSupported,
        permission,
        subscription,
        requestPermission,
        subscribe,
        unsubscribe,
        sendTestNotification
    };
}

/**
 * Convertir clave VAPID de base64 a Uint8Array
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}
