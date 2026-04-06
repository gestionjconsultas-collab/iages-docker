import React, { useState } from 'react';
import { Download, FileText, AlertTriangle, TrendingUp, Calendar, X } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ExportarReportes({ onClose }) {
    const [tipo, setTipo] = useState('uso');
    const [formato, setFormato] = useState('csv');
    const [fechaInicio, setFechaInicio] = useState('');
    const [fechaFin, setFechaFin] = useState('');
    const [loading, setLoading] = useState(false);

    const tiposReporte = [
        { value: 'uso', label: 'Reporte de Uso', icon: <FileText className="w-5 h-5" />, description: 'Usuarios, empresas, documentos, tokens IA' },
        { value: 'alertas', label: 'Reporte de Alertas', icon: <AlertTriangle className="w-5 h-5" />, description: 'Alertas generadas por el sistema' },
        { value: 'planes', label: 'Cambios de Planes', icon: <TrendingUp className="w-5 h-5" />, description: 'Historial de cambios en planes' }
    ];

    const handleExportar = async () => {
        setLoading(true);

        try {
            // Construir URL con parámetros
            const params = new URLSearchParams({
                tipo,
                formato
            });

            if (fechaInicio) params.append('fecha_inicio', fechaInicio);
            if (fechaFin) params.append('fecha_fin', fechaFin);

            // Descargar archivo
            const url = `/api/super-admin/exportar-reporte?${params.toString()}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al exportar reporte');
            }

            // Obtener blob y descargar
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;

            // Obtener nombre de archivo del header o generar uno
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition
                ? contentDisposition.split('filename=')[1].replace(/"/g, '')
                : `reporte_${tipo}_${Date.now()}.${formato === 'csv' ? 'csv' : 'xlsx'}`;

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);

            toast.success('Reporte descargado correctamente');
            onClose();
        } catch (error) {
            console.error('Error exportando:', error);
            toast.error(error.message || 'Error al exportar reporte');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
                    <div className="flex items-center gap-2">
                        <Download className="w-6 h-6 text-blue-600" />
                        <h2 className="text-2xl font-bold text-gray-900">Exportar Reporte</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Tipo de Reporte */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Tipo de Reporte
                        </label>
                        <div className="grid grid-cols-1 gap-3">
                            {tiposReporte.map((t) => (
                                <button
                                    key={t.value}
                                    onClick={() => setTipo(t.value)}
                                    className={`p-4 border-2 rounded-lg transition text-left ${tipo === t.value
                                            ? 'border-blue-600 bg-blue-50'
                                            : 'border-gray-200 hover:border-gray-300'
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className={`mt-0.5 ${tipo === t.value ? 'text-blue-600' : 'text-gray-400'}`}>
                                            {t.icon}
                                        </div>
                                        <div className="flex-1">
                                            <div className="font-medium text-gray-900">{t.label}</div>
                                            <div className="text-sm text-gray-600 mt-1">{t.description}</div>
                                        </div>
                                        {tipo === t.value && (
                                            <div className="text-blue-600">
                                                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Formato */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Formato de Exportación
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => setFormato('csv')}
                                className={`p-4 border-2 rounded-lg transition ${formato === 'csv'
                                        ? 'border-blue-600 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className="font-medium text-gray-900">CSV</div>
                                <div className="text-sm text-gray-600 mt-1">Archivo de texto separado por comas</div>
                            </button>
                            <button
                                onClick={() => setFormato('excel')}
                                className={`p-4 border-2 rounded-lg transition ${formato === 'excel'
                                        ? 'border-blue-600 bg-blue-50'
                                        : 'border-gray-200 hover:border-gray-300'
                                    }`}
                            >
                                <div className="font-medium text-gray-900">Excel</div>
                                <div className="text-sm text-gray-600 mt-1">Hoja de cálculo (.xlsx)</div>
                            </button>
                        </div>
                    </div>

                    {/* Rango de Fechas */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            <div className="flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                Rango de Fechas (Opcional)
                            </div>
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs text-gray-600 mb-1">Desde</label>
                                <input
                                    type="date"
                                    value={fechaInicio}
                                    onChange={(e) => setFechaInicio(e.target.value)}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-600 mb-1">Hasta</label>
                                <input
                                    type="date"
                                    value={fechaFin}
                                    onChange={(e) => setFechaFin(e.target.value)}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            Si no seleccionas fechas, se exportarán todos los datos disponibles
                        </p>
                    </div>

                    {/* Info */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-sm text-blue-800">
                            <strong>ℹ️ Nota:</strong> El reporte se descargará automáticamente en tu navegador.
                        </p>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-2 p-6 border-t border-gray-200 sticky bottom-0 bg-white">
                    <button
                        onClick={onClose}
                        className="px-6 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition font-medium"
                        disabled={loading}
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleExportar}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition font-medium flex items-center gap-2 disabled:opacity-50"
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                Exportando...
                            </>
                        ) : (
                            <>
                                <Download className="w-4 h-4" />
                                Descargar Reporte
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
