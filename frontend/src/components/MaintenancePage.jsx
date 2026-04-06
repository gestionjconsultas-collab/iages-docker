import React, { useState } from 'react';
import { Wrench, Clock, RefreshCw } from 'lucide-react';
import axios from 'axios';

export default function MaintenancePage({ message }) {
    const defaultMessage = 'Estamos mejorando el sistema para ofrecerte una mejor experiencia. Volveremos pronto.';
    const [checking, setChecking] = useState(false);

    const handleRefresh = async () => {
        setChecking(true);

        try {
            // Intentar acceder a un endpoint público (auth status)
            // Si responde sin 503, el mantenimiento está desactivado
            const response = await axios.get('/api/auth/status');

            // Si llegamos aquí sin error 503, redirigir al login
            window.location.href = '/login';
        } catch (error) {
            // Si hay error 503, aún estamos en mantenimiento
            if (error.response?.status === 503) {
                // Mostrar feedback visual
                setChecking(false);
                // Pequeña pausa para mostrar el estado
                setTimeout(() => {
                    setChecking(false);
                }, 1000);
            } else {
                // Cualquier otro error (401, 404, etc.) significa que el servidor está respondiendo
                // Por lo tanto, el mantenimiento está desactivado
                window.location.href = '/login';
            }
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 flex items-center justify-center p-4">
            <div className="max-w-lg w-full">
                {/* Card principal */}
                <div className="bg-white rounded-2xl shadow-2xl p-8 md:p-12 text-center">
                    {/* Icono animado */}
                    <div className="mb-8">
                        <div className="w-24 h-24 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                            <Wrench className="w-12 h-12 text-blue-600 animate-pulse" />
                        </div>
                        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
                            Mantenimiento en Progreso
                        </h1>
                        <p className="text-lg text-gray-600 leading-relaxed">
                            {message || defaultMessage}
                        </p>
                    </div>

                    {/* Info box */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-5 mb-8 border border-blue-100">
                        <div className="flex items-center justify-center gap-3 text-blue-800">
                            <Clock className="w-6 h-6" />
                            <span className="font-semibold text-lg">Volveremos muy pronto</span>
                        </div>
                    </div>

                    {/* Botón de refrescar */}
                    <button
                        onClick={handleRefresh}
                        disabled={checking}
                        className={`flex items-center gap-2 mx-auto px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all transform hover:scale-105 font-medium shadow-lg ${checking ? 'opacity-50 cursor-not-allowed' : ''
                            }`}
                    >
                        <RefreshCw className={`w-5 h-5 ${checking ? 'animate-spin' : ''}`} />
                        {checking ? 'Verificando...' : 'Reintentar'}
                    </button>

                    {/* Footer */}
                    <p className="text-sm text-gray-500 mt-8">
                        Gracias por tu paciencia 💙
                    </p>
                </div>

                {/* Decoración */}
                <div className="mt-8 text-center">
                    <div className="inline-flex items-center gap-2 text-gray-400 text-sm">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                        <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                    </div>
                </div>
            </div>
        </div>
    );
}
