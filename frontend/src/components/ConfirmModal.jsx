import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

export default function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title = "Confirmar acción",
    message = "¿Estás seguro de que deseas realizar esta acción?",
    confirmText = "Eliminar",
    cancelText = "Cancelar",
    isDanger = true
}) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm transition-all duration-300">
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all scale-100 animate-in fade-in zoom-in duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header con icono */}
                <div className={`p-6 pb-0 flex items-center justify-center`}>
                    <div className={`p-4 rounded-full ${isDanger ? 'bg-red-50 text-red-500' : 'bg-primary-50 text-primary-hover'}`}>
                        <AlertTriangle className="w-8 h-8" />
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 text-center">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
                    <p className="text-gray-500 text-sm leading-relaxed whitespace-pre-line">{message}</p>
                </div>

                {/* Actions */}
                <div className="p-6 bg-gray-50/50 flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors shadow-sm"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={() => {
                            onConfirm();
                            onClose();
                        }}
                        className={`flex-1 px-4 py-2.5 font-semibold text-white rounded-xl shadow-md transition-all active:scale-95 ${isDanger
                            ? 'bg-gradient-to-r from-red-600 to-rose-500 hover:from-red-700 hover:to-rose-600 shadow-red-200'
                            : 'bg-gradient-to-r from-primary-hover to-primary hover:from-primary-hover hover:to-primary shadow-primary-light'
                            }`}
                    >
                        {confirmText}
                    </button>
                </div>

                {/* Botón cerrar esquina */}
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>
        </div>
    );
}
