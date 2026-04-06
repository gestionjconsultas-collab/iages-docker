import React, { useState } from 'react';
import { X, FileDown, FileSpreadsheet, FileText, Download, Calendar, Filter } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function ExportModal({ onClose, empresas = [] }) {
    const [format, setFormat] = useState('excel');
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState({
        empresa_ids: [],
        fecha_desde: '',
        fecha_hasta: '',
        categorias: []
    });

    const formatOptions = [
        { value: 'excel', label: 'Excel (.xlsx)', icon: FileSpreadsheet, color: 'green' },
        { value: 'csv', label: 'CSV', icon: FileText, color: 'blue' },
        { value: 'pdf', label: 'PDF', icon: FileDown, color: 'red' }
    ];

    const categorias = [
        'nomina',
        'notificacion',
        'seguro_social',
        'contrato',
        'finiquito',
        'irpf',
        'otros'
    ];

    const handleExport = async () => {
        setLoading(true);
        try {
            // Preparar filtros - NO convertir a undefined
            const exportFilters = {
                empresa_ids: filters.empresa_ids,
                fecha_desde: filters.fecha_desde || undefined,
                fecha_hasta: filters.fecha_hasta || undefined,
                categorias: filters.categorias
            };

            console.log('📤 Exportando:', format);
            console.log('🔍 Filtros:', exportFilters);

            const response = await axios.post('/api/export/documentos-filtrado', {
                format,
                filters: exportFilters
            }, {
                responseType: 'blob',
                withCredentials: true
            });

            // Determinar extensión según formato
            const extensions = {
                excel: 'xlsx',
                csv: 'csv',
                pdf: 'pdf'
            };
            const ext = extensions[format];

            // Crear URL del blob y descargar
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `exportacion_iages_${Date.now()}.${ext}`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);

            toast.success('Exportación completada');
            onClose();
        } catch (error) {
            console.error('Error exportando:', error);
            toast.error(error.response?.data?.error || 'Error al exportar documentos');
        } finally {
            setLoading(false);
        }
    };

    const toggleEmpresa = (empresaId) => {
        setFilters(prev => ({
            ...prev,
            empresa_ids: prev.empresa_ids.includes(empresaId)
                ? prev.empresa_ids.filter(id => id !== empresaId)
                : [...prev.empresa_ids, empresaId]
        }));
    };

    const toggleCategoria = (categoria) => {
        setFilters(prev => ({
            ...prev,
            categorias: prev.categorias.includes(categoria)
                ? prev.categorias.filter(c => c !== categoria)
                : [...prev.categorias, categoria]
        }));
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                            <Download className="w-5 h-5 text-purple-600" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-gray-800">Exportar Documentos</h3>
                            <p className="text-sm text-gray-600">Selecciona formato y filtros</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Selector de Formato */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Formato de Exportación
                        </label>
                        <div className="grid grid-cols-3 gap-3">
                            {formatOptions.map(option => {
                                const Icon = option.icon;
                                const isSelected = format === option.value;
                                return (
                                    <button
                                        key={option.value}
                                        onClick={() => setFormat(option.value)}
                                        className={`p-4 rounded-lg border-2 transition-all ${isSelected
                                            ? `border-${option.color}-500 bg-${option.color}-50`
                                            : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                    >
                                        <Icon className={`w-8 h-8 mx-auto mb-2 ${isSelected ? `text-${option.color}-600` : 'text-gray-400'
                                            }`} />
                                        <p className={`text-sm font-medium ${isSelected ? `text-${option.color}-900` : 'text-gray-600'
                                            }`}>
                                            {option.label}
                                        </p>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Filtros de Fecha */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                            <Calendar className="w-4 h-4" />
                            Rango de Fechas
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs text-gray-600 mb-1">Desde</label>
                                <input
                                    type="date"
                                    value={filters.fecha_desde}
                                    onChange={(e) => setFilters(prev => ({ ...prev, fecha_desde: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-600 mb-1">Hasta</label>
                                <input
                                    type="date"
                                    value={filters.fecha_hasta}
                                    onChange={(e) => setFilters(prev => ({ ...prev, fecha_hasta: e.target.value }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Filtro de Empresas */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
                            <Filter className="w-4 h-4" />
                            Empresas ({filters.empresa_ids.length > 0 ? filters.empresa_ids.length : 'Todas'})
                        </label>
                        <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3 space-y-2">
                            {empresas.map(empresa => (
                                <label key={empresa.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                                    <input
                                        type="checkbox"
                                        checked={filters.empresa_ids.includes(empresa.id)}
                                        onChange={() => toggleEmpresa(empresa.id)}
                                        className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500"
                                    />
                                    <span className="text-sm text-gray-700">{empresa.nombre}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Filtro de Categorías */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Categorías ({filters.categorias.length > 0 ? filters.categorias.length : 'Todas'})
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {categorias.map(categoria => {
                                const isSelected = filters.categorias.includes(categoria);
                                return (
                                    <button
                                        key={categoria}
                                        onClick={() => toggleCategoria(categoria)}
                                        className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isSelected
                                            ? 'bg-purple-500 text-white'
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        {categoria.replace('_', ' ')}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-between items-center">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleExport}
                        disabled={loading}
                        className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Exportando...
                            </>
                        ) : (
                            <>
                                <Download className="w-4 h-4" />
                                Exportar
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
