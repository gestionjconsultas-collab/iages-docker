import React, { useState } from 'react';
import { Lock, AlertTriangle, X, Eye, EyeOff } from 'lucide-react';

export default function PasswordConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title = "Confirmar Acción",
    message = "Por favor ingresa tu contraseña para continuar",
    confirmText = "Confirmar",
    confirmColor = "orange",
    showWarning = false,
    warningMessage = ""
}) {
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!password) return;

        setLoading(true);
        try {
            await onConfirm(password);
            setPassword('');
            onClose();
        } catch (error) {
            // El error ya se maneja en el componente padre
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setPassword('');
        onClose();
    };

    const colorClasses = {
        orange: 'bg-orange-500 hover:bg-orange-600',
        red: 'bg-red-500 hover:bg-red-600',
        blue: 'bg-blue-500 hover:bg-blue-600'
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-fadeIn">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                            <Lock className="w-5 h-5 text-orange-600" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-800">{title}</h3>
                    </div>
                    <button
                        onClick={handleClose}
                        className="text-gray-400 hover:text-gray-600 transition"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Warning (opcional) */}
                {showWarning && warningMessage && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                        <div className="flex items-start gap-2">
                            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                            <p className="text-sm text-yellow-800">{warningMessage}</p>
                        </div>
                    </div>
                )}

                {/* Message */}
                <p className="text-gray-600 mb-6">{message}</p>

                {/* Form */}
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                            Contraseña
                        </label>
                        <div className="relative">
                            <input
                                id="password"
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-orange-500 focus:outline-none transition pr-12"
                                placeholder="Ingresa tu contraseña"
                                autoFocus
                                required
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="flex-1 py-3 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition font-medium"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={!password || loading}
                            className={`flex-1 py-3 px-4 text-white rounded-lg transition font-medium disabled:opacity-50 disabled:cursor-not-allowed ${colorClasses[confirmColor] || colorClasses.orange}`}
                        >
                            {loading ? 'Procesando...' : confirmText}
                        </button>
                    </div>
                </form>
            </div>

            <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
      `}</style>
        </div>
    );
}
