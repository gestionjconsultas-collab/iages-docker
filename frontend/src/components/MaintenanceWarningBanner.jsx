import React, { useState, useEffect } from 'react';
import { AlertTriangle, X, Clock, Wrench } from 'lucide-react';

export default function MaintenanceWarningBanner({ warningData, onDismiss }) {
    const [timeRemaining, setTimeRemaining] = useState(0);
    const [dismissed, setDismissed] = useState(false);
    const [soundEnabled, setSoundEnabled] = useState(true);

    useEffect(() => {
        if (!warningData) return;

        // Calcular tiempo restante
        const scheduledTime = new Date(warningData.scheduled_time);
        const updateTimer = () => {
            const now = new Date();
            const remaining = Math.max(0, Math.floor((scheduledTime - now) / 1000));
            setTimeRemaining(remaining);

            // Redirigir cuando llegue a 0
            if (remaining === 0) {
                window.location.href = '/maintenance';
            }
        };

        updateTimer();
        const interval = setInterval(updateTimer, 1000);

        // Reproducir sonido de notificación
        if (soundEnabled) {
            playNotificationSound();
        }

        return () => clearInterval(interval);
    }, [warningData, soundEnabled]);

    // Reaparecer cada 60 segundos si fue cerrado
    useEffect(() => {
        if (dismissed) {
            const timer = setTimeout(() => {
                setDismissed(false);
            }, 60000); // 1 minuto
            return () => clearTimeout(timer);
        }
    }, [dismissed]);

    const playNotificationSound = () => {
        try {
            // Crear un tono de advertencia usando Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800; // Frecuencia del tono
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.warn('No se pudo reproducir el sonido de notificación:', error);
        }
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getUrgencyLevel = () => {
        if (timeRemaining <= 60) return 'critical'; // Último minuto
        if (timeRemaining <= 180) return 'high'; // Últimos 3 minutos
        return 'medium';
    };

    const handleDismiss = () => {
        setDismissed(true);
        if (onDismiss) onDismiss();
    };

    if (!warningData || dismissed) return null;

    const urgency = getUrgencyLevel();
    const minutes = Math.floor(timeRemaining / 60);

    return (
        <div className="fixed top-0 left-0 right-0 z-50 animate-slide-down">
            {/* Banner principal */}
            <div className={`
                ${urgency === 'critical' ? 'bg-gradient-to-r from-red-600 via-red-500 to-orange-500' : ''}
                ${urgency === 'high' ? 'bg-gradient-to-r from-orange-600 via-orange-500 to-yellow-500' : ''}
                ${urgency === 'medium' ? 'bg-gradient-to-r from-yellow-600 via-yellow-500 to-amber-500' : ''}
                text-white shadow-2xl
                ${urgency === 'critical' ? 'animate-pulse-slow' : ''}
            `}>
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                        {/* Icono animado */}
                        <div className="flex items-center gap-4">
                            <div className={`
                                p-3 rounded-full bg-white bg-opacity-20 backdrop-blur-sm
                                ${urgency === 'critical' ? 'animate-bounce' : 'animate-pulse'}
                            `}>
                                {urgency === 'critical' ? (
                                    <Wrench className="w-6 h-6" />
                                ) : (
                                    <AlertTriangle className="w-6 h-6" />
                                )}
                            </div>

                            {/* Mensaje */}
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-1">
                                    <h3 className="text-lg font-bold">
                                        ⚠️ Mantenimiento Programado
                                    </h3>
                                    {urgency === 'critical' && (
                                        <span className="px-2 py-1 bg-red-900 bg-opacity-50 rounded text-xs font-bold animate-pulse">
                                            ¡INMINENTE!
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm opacity-90">
                                    {warningData.message || 'El sistema entrará en mantenimiento pronto'}
                                </p>
                            </div>
                        </div>

                        {/* Countdown */}
                        <div className="flex items-center gap-4">
                            <div className="text-center bg-black bg-opacity-30 backdrop-blur-sm rounded-lg px-6 py-3 min-w-[140px] border-2 border-white border-opacity-30">
                                <div className="flex items-center justify-center gap-2 mb-1">
                                    <Clock className="w-4 h-4 text-white" />
                                    <span className="text-xs font-medium text-white opacity-90">Tiempo restante</span>
                                </div>
                                <div className={`text-3xl font-bold tabular-nums text-white ${urgency === 'critical' ? 'animate-pulse' : ''}`}>
                                    {formatTime(timeRemaining)}
                                </div>
                                <div className="text-xs text-white opacity-80 mt-1">
                                    {minutes === 0 ? 'menos de 1 minuto' : `${minutes} minuto${minutes !== 1 ? 's' : ''}`}
                                </div>
                            </div>

                            {/* Botón cerrar */}
                            <button
                                onClick={handleDismiss}
                                className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-all"
                                title="Cerrar (reaparecerá en 1 minuto)"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Barra de progreso */}
                    <div className="mt-3 h-1 bg-white bg-opacity-20 rounded-full overflow-hidden">
                        <div
                            className={`h-full transition-all duration-1000 ease-linear ${urgency === 'critical' ? 'bg-white' : 'bg-white bg-opacity-60'
                                }`}
                            style={{
                                width: `${(timeRemaining / (warningData.delay_minutes * 60)) * 100}%`
                            }}
                        />
                    </div>

                    {/* Mensaje adicional */}
                    {urgency === 'critical' && (
                        <div className="mt-3 text-center text-sm font-medium animate-pulse">
                            💾 Por favor, guarda tu trabajo ahora
                        </div>
                    )}
                </div>
            </div>

            {/* Sombra decorativa */}
            <div className="h-1 bg-gradient-to-b from-black/20 to-transparent" />
        </div>
    );
}
