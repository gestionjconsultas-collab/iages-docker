import React, { useState } from 'react';
import { Bell, X, Send } from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

export default function NotifyDocumentButton({ document, company }) {
    const [showModal, setShowModal] = useState(false);
    const [customMessage, setCustomMessage] = useState('');
    const [sending, setSending] = useState(false);

    const handleNotify = async () => {
        if (sending) return;

        setSending(true);
        try {
            const response = await axios.post(`/api/documents/${document.id}/notify`, {
                message: customMessage
            });

            if (response.data.success) {
                toast.success(`✅ Notificación enviada a ${response.data.users_notified} usuario(s)`);
                setShowModal(false);
                setCustomMessage('');
            } else {
                toast.error(response.data.error || 'Error al enviar notificación');
            }
        } catch (error) {
            console.error('Error enviando notificación:', error);
            toast.error(error.response?.data?.error || 'Error al enviar notificación');
        } finally {
            setSending(false);
        }
    };

    if (!showModal) {
        return (
            <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white text-sm font-medium rounded-lg hover:from-blue-700 hover:to-blue-600 transition-all shadow-sm hover:shadow-md active:scale-95"
                title="Notificar a la empresa sobre este documento"
            >
                <Bell className="w-4 h-4" />
                <span>Notificar</span>
            </button>
        );
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm transition-all duration-300">
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden transform transition-all scale-100 animate-in fade-in zoom-in duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="p-6 pb-4 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-full bg-blue-50 text-blue-600">
                                <Bell className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Notificar documento</h3>
                                <p className="text-sm text-gray-500">Enviar notificación push a la empresa</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setShowModal(false)}
                            className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-4">
                    {/* Información del documento */}
                    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                        <div className="flex justify-between items-start">
                            <span className="text-xs font-medium text-gray-500 uppercase">Documento</span>
                            <span className="text-sm font-medium text-gray-900 text-right max-w-[70%] truncate">
                                {document.nombre_archivo}
                            </span>
                        </div>
                        <div className="flex justify-between items-start">
                            <span className="text-xs font-medium text-gray-500 uppercase">Destinatario</span>
                            <span className="text-sm font-semibold text-blue-600 text-right">
                                {company?.nombre || 'Empresa'}
                            </span>
                        </div>
                        {document.categoria && (
                            <div className="flex justify-between items-start">
                                <span className="text-xs font-medium text-gray-500 uppercase">Tipo</span>
                                <span className="text-sm text-gray-700 text-right">
                                    {document.categoria}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Mensaje personalizado */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Mensaje personalizado (opcional)
                        </label>
                        <textarea
                            value={customMessage}
                            onChange={(e) => setCustomMessage(e.target.value)}
                            placeholder="Añade un mensaje adicional para la empresa..."
                            rows={3}
                            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                            maxLength={200}
                        />
                        <div className="flex justify-between items-center mt-1">
                            <p className="text-xs text-gray-400">
                                La notificación incluirá el nombre del documento automáticamente
                            </p>
                            <span className="text-xs text-gray-400">
                                {customMessage.length}/200
                            </span>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="p-6 bg-gray-50/50 flex gap-3">
                    <button
                        onClick={() => setShowModal(false)}
                        disabled={sending}
                        className="flex-1 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleNotify}
                        disabled={sending}
                        className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 text-white font-semibold rounded-xl shadow-md hover:from-blue-700 hover:to-blue-600 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {sending ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>Enviando...</span>
                            </>
                        ) : (
                            <>
                                <Send className="w-4 h-4" />
                                <span>Enviar notificación</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
