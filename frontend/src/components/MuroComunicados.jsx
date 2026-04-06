// frontend/src/components/MuroComunicados.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Bell, AlertTriangle, Info, FileText,
    Calendar, CheckCircle, X, ChevronRight,
    Megaphone
} from 'lucide-react';
import socket from '../socket';
import DocumentNotificationModal from './DocumentNotificationModal';

const MuroComunicados = () => {
    const [comunicados, setComunicados] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedDocument, setSelectedDocument] = useState(null);
    const [showDocumentModal, setShowDocumentModal] = useState(false);

    useEffect(() => {
        fetchComunicados();

        // ⭐ Escuchar nuevos comunicados vía WebSocket
        socket.on('nueva_notificacion', (data) => {
            if (data.is_comunicado) {
                console.log("📢 Nuevo comunicado recibido, actualizando muro...");
                fetchComunicados();
            }
        });

        return () => {
            socket.off('nueva_notificacion');
        };
    }, []);

    const fetchComunicados = async () => {
        try {
            const response = await axios.get('/api/comunicados');
            if (response.data.success) {
                setComunicados(response.data.comunicados);
            }
        } catch (error) {
            console.error("Error al cargar comunicados:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleComunicadoClick = (comunicado) => {
        const isDocumentNotification = comunicado.metadata?.type === 'document_notification';

        if (isDocumentNotification) {
            setSelectedDocument(comunicado);
            setShowDocumentModal(true);
        } else {
            // Lógica futura para comunicados normales (modal de detalle)
            console.log('Comunicado normal:', comunicado);
        }
    };

    if (loading) return null;
    if (comunicados.length === 0) return null;

    const getIcon = (comunicado) => {
        // Icono especial para notificaciones de documentos
        if (comunicado.metadata?.type === 'document_notification') {
            return <FileText className="w-5 h-5 text-blue-600" />;
        }

        // Iconos normales por tipo
        switch (comunicado.tipo) {
            case 'impuestos': return <FileText className="w-5 h-5 text-blue-500" />;
            case 'nominas': return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'seguros': return <Bell className="w-5 h-5 text-purple-500" />;
            case 'urgente': return <AlertTriangle className="w-5 h-5 text-red-500" />;
            default: return <Megaphone className="w-5 h-5 text-orange-500" />;
        }
    };

    const getPriorityStyles = (prioridad) => {
        switch (prioridad) {
            case 'alta': return 'border-l-4 border-l-red-500 bg-red-50/30';
            case 'media': return 'border-l-4 border-l-orange-400 bg-orange-50/20';
            default: return 'border-l-4 border-l-blue-400 bg-blue-50/10';
        }
    };

    const getButtonText = (comunicado) => {
        return comunicado.metadata?.type === 'document_notification'
            ? '📄 Ver documento'
            : 'Leer más';
    };

    return (
        <>
            <div className="mb-8 space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <Megaphone className="w-5 h-5 text-gray-700" />
                    <h2 className="text-lg font-bold text-gray-800">Muro de Comunicados</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {comunicados.map((com) => (
                        <div
                            key={com.id}
                            className={`p-4 rounded-xl border border-gray-100 shadow-sm transition-all hover:shadow-md ${getPriorityStyles(com.prioridad)}`}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="p-2 bg-white rounded-lg shadow-sm border border-gray-50">
                                    {getIcon(com)}
                                </div>
                                <span className="text-[10px] uppercase font-bold text-gray-400 bg-gray-50 px-2 py-1 rounded">
                                    {new Date(com.fecha_creacion).toLocaleDateString()}
                                </span>
                            </div>

                            <h3 className="font-bold text-gray-900 mb-1 line-clamp-1">{com.titulo}</h3>
                            <p className="text-sm text-gray-600 line-clamp-2 mb-3">
                                {com.contenido}
                            </p>

                            <div className="flex items-center justify-between pt-3 border-t border-gray-100/50">
                                <span className="text-xs text-gray-400">
                                    De: <span className="font-medium">{com.emisor_nombre}</span>
                                </span>
                                <button
                                    onClick={() => handleComunicadoClick(com)}
                                    className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 transition-colors"
                                >
                                    {getButtonText(com)} <ChevronRight className="w-3 h-3" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Modal de Documento */}
            {showDocumentModal && selectedDocument && (
                <DocumentNotificationModal
                    documentData={selectedDocument}
                    onClose={() => {
                        setShowDocumentModal(false);
                        setSelectedDocument(null);
                    }}
                />
            )}
        </>
    );
};

export default MuroComunicados;
