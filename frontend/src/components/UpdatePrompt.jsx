import { useState, useEffect } from 'react';
import { X, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * Componente que muestra un prompt cuando hay una nueva versión disponible
 * Se muestra automáticamente cuando el Service Worker detecta una actualización
 * Auto-actualiza después de 5 segundos si el usuario no interactúa
 */
export default function UpdatePrompt() {
    const [showPrompt, setShowPrompt] = useState(false);
    const [waitingWorker, setWaitingWorker] = useState(null);
    const [countdown, setCountdown] = useState(5);

    useEffect(() => {
        // Solo ejecutar en el navegador
        if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
            return;
        }

        // Detectar cuando hay un nuevo service worker esperando
        const detectUpdate = async () => {
            const registration = await navigator.serviceWorker.getRegistration();

            if (!registration) return;

            // Si ya hay un worker esperando
            if (registration.waiting) {
                setWaitingWorker(registration.waiting);
                setShowPrompt(true);
            }

            // Escuchar cuando se instala un nuevo worker
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;

                if (!newWorker) return;

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // Hay un nuevo service worker disponible
                        setWaitingWorker(newWorker);
                        setShowPrompt(true);
                    }
                });
            });
        };

        detectUpdate();

        // ⭐ Escuchar evento personalizado desde main.jsx
        const handleSwUpdate = () => {
            navigator.serviceWorker.getRegistration().then(registration => {
                if (registration && registration.waiting) {
                    setWaitingWorker(registration.waiting);
                    setShowPrompt(true);
                }
            });
        };

        window.addEventListener('swUpdateAvailable', handleSwUpdate);

        // Escuchar mensajes del service worker
        navigator.serviceWorker.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'NEW_VERSION_AVAILABLE') {
                setShowPrompt(true);
            }
        });

        return () => {
            window.removeEventListener('swUpdateAvailable', handleSwUpdate);
        };
    }, []);

    // ⭐ Countdown timer para auto-actualización
    useEffect(() => {
        if (!showPrompt) return;

        const timer = setInterval(() => {
            setCountdown(prev => {
                if (prev <= 1) {
                    clearInterval(timer);
                    handleUpdate();
                    return 0;
                }
                return prev - 1;
            });
        }, 1000);

        return () => clearInterval(timer);
    }, [showPrompt]);

    const handleUpdate = () => {
        if (!waitingWorker) {
            // Si no hay waiting worker, recargar directamente
            window.location.reload();
            return;
        }

        toast.success('Actualizando aplicación...', {
            duration: 2000,
        });

        // Enviar mensaje al service worker para que se active
        waitingWorker.postMessage({ type: 'SKIP_WAITING' });

        // Configurar listener para controllerchange
        let reloaded = false;
        const reloadPage = () => {
            if (!reloaded) {
                reloaded = true;
                window.location.reload();
            }
        };

        // Recargar cuando el nuevo worker tome control
        navigator.serviceWorker.addEventListener('controllerchange', reloadPage, { once: true });

        // Fallback: recargar después de 1 segundo si no se dispara controllerchange
        setTimeout(() => {
            reloadPage();
        }, 1000);
    };

    const handleDismiss = () => {
        setShowPrompt(false);
        setCountdown(5); // Reset countdown
    };

    if (!showPrompt) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 max-w-md animate-slide-up">
            <div className="bg-white rounded-lg shadow-2xl border border-gray-200 p-4">
                <div className="flex items-start gap-3">
                    {/* Icon */}
                    <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <RefreshCw className="w-5 h-5 text-blue-600" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-semibold text-gray-900 mb-1">
                            Nueva versión disponible
                        </h3>
                        <p className="text-sm text-gray-600 mb-3">
                            Hay una actualización de IAGES lista. Actualizando automáticamente en <span className="font-bold text-blue-600">{countdown}s</span>...
                        </p>

                        {/* Actions */}
                        <div className="flex gap-2">
                            <button
                                onClick={handleUpdate}
                                className="flex-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Actualizar ahora
                            </button>
                            <button
                                onClick={handleDismiss}
                                className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors"
                            >
                                Más tarde
                            </button>
                        </div>
                    </div>

                    {/* Close button */}
                    <button
                        onClick={handleDismiss}
                        className="flex-shrink-0 p-1 hover:bg-gray-100 rounded transition-colors"
                    >
                        <X className="w-4 h-4 text-gray-400" />
                    </button>
                </div>
            </div>
        </div>
    );
}
