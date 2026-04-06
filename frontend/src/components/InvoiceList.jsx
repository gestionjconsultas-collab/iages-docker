// frontend/src/components/InvoiceList.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { Download, Eye, CheckCircle, Clock, AlertCircle, XCircle } from 'lucide-react';

const InvoiceList = ({ facturas, onRefresh }) => {
    const [downloading, setDownloading] = useState(null);

    const descargarPDF = async (facturaId, numeroFactura) => {
        setDownloading(facturaId);
        try {
            const response = await axios.get(`/api/facturas/${facturaId}/pdf`, {
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `${numeroFactura}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            alert('Error descargando PDF');
        } finally {
            setDownloading(null);
        }
    };

    const getEstadoBadge = (estado) => {
        const badges = {
            'pendiente': {
                icon: Clock,
                color: 'yellow',
                text: 'Pendiente'
            },
            'pagada': {
                icon: CheckCircle,
                color: 'green',
                text: 'Pagada'
            },
            'vencida': {
                icon: AlertCircle,
                color: 'red',
                text: 'Vencida'
            },
            'cancelada': {
                icon: XCircle,
                color: 'gray',
                text: 'Cancelada'
            }
        };

        const badge = badges[estado] || badges.pendiente;
        const Icon = badge.icon;

        return (
            <span className={`
        inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium
        bg-${badge.color}-100 text-${badge.color}-700
      `}>
                <Icon className="w-3 h-3" />
                {badge.text}
            </span>
        );
    };

    if (!facturas || facturas.length === 0) {
        return (
            <div className="text-center py-12">
                <div className="text-gray-400 mb-4">
                    <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                    No hay facturas
                </h3>
                <p className="text-gray-600">
                    Las facturas aparecerán aquí cuando se generen
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                    Historial de Facturas ({facturas.length})
                </h3>
                <button
                    onClick={onRefresh}
                    className="text-sm text-orange-600 hover:text-orange-700 font-medium"
                >
                    Actualizar
                </button>
            </div>

            <div className="space-y-3">
                {facturas.map(factura => (
                    <div
                        key={factura.id}
                        className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                        <div className="flex items-start justify-between">
                            {/* Info */}
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <h4 className="font-semibold text-gray-900">
                                        {factura.numero_factura}
                                    </h4>
                                    {getEstadoBadge(factura.estado)}
                                </div>

                                <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                                    <div>
                                        <span className="text-gray-600">Fecha emisión:</span>
                                        <span className="ml-2 font-medium text-gray-900">
                                            {new Date(factura.fecha_emision).toLocaleDateString('es-ES')}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gray-600">Vencimiento:</span>
                                        <span className="ml-2 font-medium text-gray-900">
                                            {new Date(factura.fecha_vencimiento).toLocaleDateString('es-ES')}
                                        </span>
                                    </div>
                                </div>

                                <div className="text-sm text-gray-600">
                                    {factura.concepto}
                                </div>

                                {factura.estado === 'pendiente' && factura.dias_hasta_vencimiento !== null && (
                                    <div className={`
                    mt-2 text-xs font-medium
                    ${factura.dias_hasta_vencimiento < 0
                                            ? 'text-red-600'
                                            : factura.dias_hasta_vencimiento <= 3
                                                ? 'text-yellow-600'
                                                : 'text-gray-600'
                                        }
                  `}>
                                        {factura.dias_hasta_vencimiento < 0
                                            ? `Vencida hace ${Math.abs(factura.dias_hasta_vencimiento)} días`
                                            : `Vence en ${factura.dias_hasta_vencimiento} días`
                                        }
                                    </div>
                                )}
                            </div>

                            {/* Precio y Acciones */}
                            <div className="text-right">
                                <div className="text-2xl font-bold text-gray-900 mb-3">
                                    €{factura.total}
                                </div>

                                <div className="flex gap-2">
                                    <button
                                        onClick={() => descargarPDF(factura.id, factura.numero_factura)}
                                        disabled={downloading === factura.id}
                                        className="flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        <Download className="w-4 h-4" />
                                        {downloading === factura.id ? 'Descargando...' : 'PDF'}
                                    </button>
                                </div>

                                {factura.fecha_pago && (
                                    <div className="mt-2 text-xs text-gray-600">
                                        Pagada: {new Date(factura.fecha_pago).toLocaleDateString('es-ES')}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Desglose */}
                        <div className="mt-4 pt-4 border-t border-gray-100">
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-600">Subtotal:</span>
                                    <span className="ml-2 font-medium">€{factura.subtotal}</span>
                                </div>
                                <div>
                                    <span className="text-gray-600">IVA ({factura.iva_porcentaje}%):</span>
                                    <span className="ml-2 font-medium">€{factura.iva_importe}</span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Total:</span>
                                    <span className="ml-2 font-bold text-orange-600">€{factura.total}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default InvoiceList;
