// frontend/src/components/dehu/DehuNotificationDetail.jsx
import React from 'react';
import { X, Download, CheckCircle, Building2, Calendar, FileText, User, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { useDehuNotificationDetail } from '../../hooks/useDehuNotifications';
import { useDehuActions } from '../../hooks/useDehuActions';

const DehuNotificationDetail = ({ notification, type, onClose, onAcceptSuccess }) => {
    const { data: detail, isLoading } = useDehuNotificationDetail(
        notification?.sentReference,
        type,
        !!notification
    );

    const [isChainBusy, setIsChainBusy] = React.useState(false);
    const { acceptNotification, isAccepting, downloadDocument, downloadDocumentAsync, isDownloading } = useDehuActions();

    const handleAccept = () => {
        if (confirm('⚠️ ATENCIÓN: Esta acción es IRREVERSIBLE.\n\n¿Estás seguro de aceptar esta notificación?')) {
            acceptNotification(notification.sentReference, {
                onSuccess: async () => {
                    setIsChainBusy(true);
                    toast.success('Notificación aceptada. Iniciando descarga...');

                    // Esperar un poco para asegurar que el backend tenga listo el doc (aunque el backend ya espera, esto es visual)
                    await new Promise(r => setTimeout(r, 2000));

                    try {
                        // Intentar annexe primero
                        await downloadDocumentAsync({ sentReference: notification.sentReference, type: 'annexe' });
                    } catch (e) {
                        console.warn('Annexe no disponible, intentando voucher:', e);
                        try {
                            await downloadDocumentAsync({ sentReference: notification.sentReference, type: 'voucher' });
                        } catch (e2) {
                            toast.error('No se pudo descargar automáticamente. Búscalo en "Realizadas".');
                        }
                    }
                    setIsChainBusy(false);
                    onAcceptSuccess?.();
                    // Mantener el modal abierto un momento o cerrarlo según preferencia
                    // El usuario pidió: "si aparece el toast... cierre el modal o cambiar estado"
                    // Al finalizar la descarga (líneas arriba), ya se cerrará.
                    onClose();
                },
                onError: () => {
                    setIsChainBusy(false);
                }
            });
        }
    };

    const handleDownload = () => {
        downloadDocument({ sentReference: notification.sentReference, type: 'annexe' });
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        try {
            return new Date(dateStr).toLocaleString('es-ES');
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-red-600 text-white p-6 flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-bold">{notification?.identifier}</h2>
                        <p className="text-blue-100 text-sm mt-1">{notification?.emitterEntity}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {isLoading ? (
                        <div className="flex items-center justify-center py-12">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* Concepto */}
                            <div>
                                <h3 className="font-semibold text-gray-900 mb-2 flex items-center space-x-2">
                                    <FileText className="w-5 h-5 text-blue-600" />
                                    <span>Concepto</span>
                                </h3>
                                <p className="text-gray-700 bg-gray-50 p-4 rounded-lg">
                                    {detail?.concept || notification?.concept}
                                </p>
                            </div>

                            {/* Descripción */}
                            {detail?.description && (
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2">Descripción</h3>
                                    <p className="text-gray-700 bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">
                                        {detail.description}
                                    </p>
                                </div>
                            )}

                            {/* Información del titular */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center space-x-2">
                                        <User className="w-5 h-5 text-blue-600" />
                                        <span>NIF Titular</span>
                                    </h3>
                                    <p className="text-gray-700">{detail?.nifTitular || notification?.nifTitular}</p>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center space-x-2">
                                        <Building2 className="w-5 h-5 text-blue-600" />
                                        <span>Organismo Emisor</span>
                                    </h3>
                                    <p className="text-gray-700">{detail?.emitterEntity || notification?.emitterEntity}</p>
                                </div>
                            </div>

                            {/* Fechas */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center space-x-2">
                                        <Calendar className="w-5 h-5 text-blue-600" />
                                        <span>Fecha Disponible</span>
                                    </h3>
                                    <p className="text-gray-700">{formatDate(detail?.availabilityDate || notification?.availabilityDate)}</p>
                                </div>
                                {(detail?.expirationDate || notification?.expirationDate) && (
                                    <div>
                                        <h3 className="font-semibold text-gray-900 mb-2 flex items-center space-x-2">
                                            <AlertCircle className="w-5 h-5 text-orange-600" />
                                            <span>Fecha Expiración</span>
                                        </h3>
                                        <p className="text-gray-700">{formatDate(detail?.expirationDate || notification?.expirationDate)}</p>
                                    </div>
                                )}
                            </div>

                            {/* Información adicional */}
                            {detail?.bondType && (
                                <div>
                                    <h3 className="font-semibold text-gray-900 mb-2">Tipo de Garantía</h3>
                                    <p className="text-gray-700">{detail.bondType}</p>
                                </div>
                            )}

                            {/* Referencia */}
                            <div className="bg-blue-50 p-4 rounded-lg">
                                <h3 className="font-semibold text-gray-900 mb-1 text-sm">Referencia de Envío</h3>
                                <p className="text-xs text-gray-600 font-mono break-all">{notification?.sentReference}</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer con acciones */}
                <div className="border-t border-gray-200 p-4 bg-gray-50 flex items-center justify-between">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                        Cerrar
                    </button>

                    <div className="flex items-center space-x-3">
                        {type === 'realized' && (
                            <button
                                onClick={handleDownload}
                                disabled={isDownloading}
                                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isDownloading ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        <span>Descargando...</span>
                                    </>
                                ) : (
                                    <>
                                        <Download className="w-4 h-4" />
                                        <span>Descargar Documento</span>
                                    </>
                                )}
                            </button>
                        )}

                        {type === 'pending' && (
                            <button
                                onClick={handleAccept}
                                disabled={isAccepting || isChainBusy}
                                className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {(isAccepting || isChainBusy) ? (
                                    <>
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                        <span>{isAccepting ? 'Aceptando...' : 'Descargando...'}</span>
                                    </>
                                ) : (
                                    <>
                                        <CheckCircle className="w-4 h-4" />
                                        <span>Aceptar Notificación</span>
                                    </>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DehuNotificationDetail;
