import React from 'react';
import { X, Download, FileText } from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function DocumentNotificationModal({ documentData, onClose }) {
    const { user } = useAuth();
    const esInvitado = user?.departamento === 'Invitado' || user?.rol_nombre === 'Invitado';

    const {
        document_id,
        empresa_nombre,
        documento_nombre,
        documento_categoria
    } = documentData.metadata || {};

    const mensaje = documentData.contenido;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl w-full max-w-5xl h-[90vh] flex flex-col shadow-2xl">
                {/* Header */}
                <div className="p-6 border-b flex items-center justify-between bg-gradient-to-r from-blue-50 to-purple-50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-600 rounded-lg">
                            <FileText className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">{documento_nombre}</h2>
                            <p className="text-sm text-gray-600">{empresa_nombre}</p>
                            {documento_categoria && (
                                <span className="inline-block mt-1 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                                    {documento_categoria}
                                </span>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/50 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-600" />
                    </button>
                </div>

                {/* Mensaje de Jefatura */}
                {mensaje && mensaje !== `Nuevo documento de ${empresa_nombre}` && (
                    <div className="p-4 bg-gradient-to-r from-blue-50 to-blue-100 border-b border-blue-200">
                        <div className="flex items-start gap-2">
                            <div className="p-1.5 bg-blue-600 rounded-full mt-0.5">
                                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
                                    <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
                                </svg>
                            </div>
                            <div className="flex-1">
                                <p className="text-xs font-semibold text-blue-900 uppercase tracking-wide mb-1">
                                    Mensaje de Jefatura
                                </p>
                                <p className="text-sm text-blue-800 leading-relaxed">{mensaje}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Visor PDF */}
                <div className="flex-1 overflow-hidden bg-gray-100">
                    <iframe
                        src={`/api/documentos/${document_id}/archivo`}
                        className="w-full h-full"
                        title="Documento PDF"
                        style={{ border: 'none' }}
                    />
                </div>

                {/* Footer con acciones */}
                <div className="p-4 border-t bg-gray-50 flex gap-3">
                    {!esInvitado && (
                        <button
                            onClick={() => window.open(`/api/documentos/${document_id}/archivo?download=1`, '_blank')}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl font-semibold shadow-md hover:from-blue-700 hover:to-blue-800 transition-all active:scale-95"
                        >
                            <Download className="w-4 h-4" />
                            Descargar Documento
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        className={`${esInvitado ? 'w-full' : 'px-6'} py-3 border-2 border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-100 transition-colors`}
                    >
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}
