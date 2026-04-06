// frontend/src/components/ConfirmarClasificacionModal.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { X, CheckCircle, AlertTriangle, TrendingUp, Calendar, DollarSign, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ConfirmarClasificacionModal({ documento, onClose }) {
    const [clasificacion, setClasificacion] = useState(documento.clasificacion_sugerida || documento.clasificacion);
    const [metadatos, setMetadatos] = useState(documento.metadatos || {});
    const [importePago, setImportePago] = useState(documento.importe_pago || '');
    const [fechaLimite, setFechaLimite] = useState(documento.fecha_limite || '');
    const [confirmando, setConfirmando] = useState(false);

    const handleConfirmar = async () => {
        setConfirmando(true);

        try {
            const res = await axios.post(
                `/api/fiscal/documentos/${documento.id}/confirmar`,
                {
                    clasificacion,
                    metadatos,
                    importe_pago: importePago ? parseFloat(importePago) : null,
                    fecha_limite: fechaLimite || null
                },
                { withCredentials: true }
            );

            if (res.data.success) {
                toast.success('Clasificación confirmada exitosamente');
                onClose();
            }
        } catch (error) {
            toast.error('Error confirmando clasificación');
            console.error(error);
        } finally {
            setConfirmando(false);
        }
    };

    const confianzaColor = (confianza) => {
        if (confianza >= 0.9) return 'text-green-600';
        if (confianza >= 0.7) return 'text-yellow-600';
        return 'text-red-600';
    };

    const confianzaLabel = (confianza) => {
        if (confianza >= 0.9) return 'Alta';
        if (confianza >= 0.7) return 'Media';
        return 'Baja';
    };

    // Formatear tipo de documento para mostrar nombre legible
    const formatTipoDocumento = (tipo) => {
        const tiposMap = {
            'MODELO_130': 'Modelo 130 - IRPF Pagos Fraccionados',
            'MODELO_303': 'Modelo 303 - IVA',
            'MODELO_200': 'Modelo 200 - Impuesto Sociedades',
            'MODELO_202': 'Modelo 202 - Pagos Fraccionados Sociedades',
            'MODELO_190': 'Modelo 190 - Retenciones Anuales',
            'MODELO_111': 'Modelo 111 - Retenciones Trimestrales',
            'MODELO_115': 'Modelo 115 - Retenciones Alquileres',
            'MODELO_347': 'Modelo 347 - Operaciones con Terceros',
            'CERTIFICADO_RETENCIONES': 'Certificado de Retenciones',
            'APLAZAMIENTO_SOLICITUD': 'Solicitud de Aplazamiento',
            'APLAZAMIENTO_CONCESION': 'Concesión de Aplazamiento',
            'OTRO': 'Otro'
        };
        return tiposMap[tipo] || tipo;
    };

    // Construir URL del PDF
    const pdfUrl = documento.archivo_pdf_path
        ? `/api/fiscal/documentos/${documento.id}/pdf`
        : null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-7xl max-h-[95vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-200">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">Confirmar Clasificación IA</h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Revisa el documento y confirma la información extraída por la IA
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content - Split Layout */}
                <div className="flex-1 overflow-hidden flex">
                    {/* Left: PDF Viewer */}
                    <div className="w-1/2 border-r border-gray-200 bg-gray-100 flex flex-col">
                        <div className="p-4 bg-gray-50 border-b border-gray-200">
                            <div className="flex items-center gap-2 text-gray-700">
                                <FileText className="w-5 h-5" />
                                <span className="font-semibold">Documento PDF</span>
                            </div>
                        </div>
                        <div className="flex-1 overflow-auto p-4">
                            {pdfUrl ? (
                                <iframe
                                    src={pdfUrl}
                                    className="w-full h-full border-0 rounded-lg shadow-sm"
                                    title="Vista previa del documento"
                                />
                            ) : (
                                <div className="flex items-center justify-center h-full text-gray-500">
                                    <div className="text-center">
                                        <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                                        <p>No se puede mostrar el PDF</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Right: Form */}
                    <div className="w-1/2 overflow-y-auto">
                        <div className="p-6 space-y-6">
                            {/* Confianza IA */}
                            {documento.confianza_ia && (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5 text-blue-600" />
                                        <span className="font-semibold text-blue-900">Confianza de IA:</span>
                                        <span className={`font-bold ${confianzaColor(documento.confianza_ia)}`}>
                                            {(documento.confianza_ia * 100).toFixed(0)}% - {confianzaLabel(documento.confianza_ia)}
                                        </span>
                                    </div>
                                </div>
                            )}

                            {/* Tipo de Documento */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Tipo de Documento
                                </label>
                                <input
                                    type="text"
                                    value={formatTipoDocumento(documento.tipo || documento.tipo_documento)}
                                    disabled
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50"
                                />
                            </div>

                            {/* Clasificación */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Clasificación *
                                </label>
                                <select
                                    value={clasificacion}
                                    onChange={(e) => setClasificacion(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="PAGO_REQUERIDO">Pago Requerido</option>
                                    <option value="INFORMATIVO">Informativo</option>
                                    <option value="INFORMATIVO_DEVOLUCION">Informativo - Devolución</option>
                                    <option value="INFORMATIVO_SIN_ACTIVIDAD">Informativo - Sin Actividad</option>
                                </select>
                            </div>

                            {/* Metadatos Extraídos */}
                            {Object.keys(metadatos).length > 0 && (
                                <div className="bg-gray-50 rounded-lg p-4">
                                    <h3 className="font-semibold text-gray-900 mb-3">Datos Extraídos</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        {Object.entries(metadatos).map(([key, value]) => (
                                            <div key={key}>
                                                <label className="block text-xs font-medium text-gray-600 mb-1">
                                                    {key.replace('_', ' ').toUpperCase()}
                                                </label>
                                                <input
                                                    type="text"
                                                    value={value || ''}
                                                    onChange={(e) => setMetadatos({ ...metadatos, [key]: e.target.value })}
                                                    className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                                                />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Importe de Pago */}
                            {clasificacion === 'PAGO_REQUERIDO' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        <DollarSign className="inline w-4 h-4 mr-1" />
                                        Importe a Pagar (€)
                                    </label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        value={importePago}
                                        onChange={(e) => setImportePago(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                        placeholder="Consulta el PDF para obtener el importe"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        💡 Revisa el PDF a la izquierda para encontrar el importe exacto
                                    </p>
                                </div>
                            )}

                            {/* Fecha Límite */}
                            {clasificacion === 'PAGO_REQUERIDO' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        <Calendar className="inline w-4 h-4 mr-1" />
                                        Fecha Límite de Pago
                                    </label>
                                    <input
                                        type="date"
                                        value={fechaLimite}
                                        onChange={(e) => setFechaLimite(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                    />
                                    <p className="text-xs text-gray-500 mt-1">
                                        💡 Revisa el PDF para confirmar la fecha límite
                                    </p>
                                </div>
                            )}

                            {/* Advertencia si confianza es baja */}
                            {documento.confianza_ia < 0.7 && (
                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                    <div className="flex items-start gap-2">
                                        <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                                        <div>
                                            <p className="font-semibold text-yellow-900">Confianza Baja</p>
                                            <p className="text-sm text-yellow-700 mt-1">
                                                La IA tiene baja confianza en esta clasificación. Por favor, revisa cuidadosamente el PDF y los datos extraídos.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex gap-3 p-6 border-t border-gray-200 bg-gray-50">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleConfirmar}
                        disabled={confirmando}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                    >
                        {confirmando ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                Confirmando...
                            </>
                        ) : (
                            <>
                                <CheckCircle size={18} />
                                Confirmar Clasificación
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
