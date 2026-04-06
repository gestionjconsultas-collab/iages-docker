import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Download, RefreshCw, DollarSign, Hash, EyeOff, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

const AplazamientosView = () => {
    const [stats, setStats] = useState(null);
    const [documentos, setDocumentos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [expandidos, setExpandidos] = useState({});
    const [mostrarOcultos, setMostrarOcultos] = useState(false);

    useEffect(() => {
        cargarDatos();
    }, [mostrarOcultos]);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const params = { mostrar_ocultos: mostrarOcultos };
            const [statsRes, docsRes] = await Promise.all([
                axios.get('/api/aplazamientos/stats', { params }),
                axios.get('/api/aplazamientos/documentos', { params })
            ]);
            setStats(statsRes.data.stats);
            setDocumentos(docsRes.data.documentos);
        } catch (error) {
            toast.error('Error al cargar datos de aplazamientos');
        } finally {
            setLoading(false);
        }
    };

    const handleOmitir = async (doc) => {
        if (!confirm(`¿Ocultar el aplazamiento de ${doc.empresa_nombre}?`)) return;
        try {
            await axios.post(`/api/aplazamientos/documentos/${doc.id}/toggle-omitir`);
            toast.success('Aplazamiento ocultado');
            setDocumentos(prev => prev.filter(d => d.id !== doc.id));
            const statsRes = await axios.get('/api/aplazamientos/stats');
            setStats(statsRes.data.stats);
        } catch {
            toast.error('Error al ocultar el aplazamiento');
        }
    };

    const toggleExpand = (id) => {
        setExpandidos(prev => ({ ...prev, [id]: !prev[id] }));
    };

    if (loading) return <div className="p-8 text-center">Cargando aplazamientos...</div>;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-800 mb-4">Gestión de Aplazamientos</h1>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Documentos</p>
                                <p className="text-2xl font-bold text-gray-800">{stats?.total_documentos || 0}</p>
                            </div>
                            <FileText className="text-blue-500" size={32} />
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Deuda</p>
                                <p className="text-2xl font-bold text-red-600">€{stats?.total_deuda?.toFixed(2) || '0.00'}</p>
                            </div>
                            <DollarSign className="text-red-500" size={32} />
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Intereses</p>
                                <p className="text-2xl font-bold text-orange-600">€{stats?.total_intereses?.toFixed(2) || '0.00'}</p>
                            </div>
                            <DollarSign className="text-orange-500" size={32} />
                        </div>
                    </div>
                    <div className="bg-white p-4 rounded-lg shadow">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600">Total Cuotas</p>
                                <p className="text-2xl font-bold text-blue-600">{stats?.total_cuotas || 0}</p>
                            </div>
                            <Hash className="text-blue-500" size={32} />
                        </div>
                    </div>
                </div>

                <div className="flex gap-2 mb-4 justify-end">
                    <button onClick={cargarDatos} className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center gap-2">
                        <RefreshCw size={16} /> Actualizar
                    </button>
                    <button
                        onClick={() => setMostrarOcultos(!mostrarOcultos)}
                        className={`px-4 py-2 rounded-lg flex items-center gap-2 border transition-colors ${mostrarOcultos ? 'bg-gray-800 text-white border-gray-800' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'}`}
                    >
                        {mostrarOcultos ? <EyeOff size={16} /> : <FileText size={16} />}
                        {mostrarOcultos ? 'Ocultar Omitidos' : 'Ver Ocultos'}
                    </button>
                </div>
            </div>

            {/* Lista de aplazamientos con detalle expandible */}
            {documentos.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
                    No hay aplazamientos registrados
                </div>
            ) : (
                <div className="space-y-2">
                    {documentos.map(doc => {
                        const expandido = expandidos[doc.id];
                        const detalle = doc.detalle_liquidacion || [];
                        return (
                            <div key={doc.id} className="bg-white rounded-lg shadow overflow-hidden">
                                {/* Fila resumen (clickable) */}
                                <div
                                    className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 select-none"
                                    onClick={() => toggleExpand(doc.id)}
                                >
                                    <span className="text-gray-400">
                                        {expandido ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    </span>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-semibold text-gray-800 truncate">{doc.empresa_nombre}</p>
                                        <p className="text-xs text-gray-500 font-mono truncate">{doc.nombre_archivo}</p>
                                    </div>
                                    <div className="hidden sm:flex items-center gap-6 text-sm">
                                        <div className="text-center">
                                            <p className="text-xs text-gray-500">Expediente</p>
                                            <p className="font-mono text-xs text-gray-700">{doc.expediente || '—'}</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-gray-500">Cuotas</p>
                                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-semibold">{doc.num_cuotas}</span>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-gray-500">Total deuda</p>
                                            <p className="font-semibold text-red-600">€{doc.total_deuda.toFixed(2)}</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-xs text-gray-500">Intereses</p>
                                            <p className="text-orange-600">€{doc.total_intereses.toFixed(2)}</p>
                                        </div>
                                    </div>
                                    {/* Acciones */}
                                    <div className="flex items-center gap-2 ml-2" onClick={e => e.stopPropagation()}>
                                        <a
                                            href={`/api/aplazamientos/documentos/${doc.id}/pdf`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center gap-1 px-2 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-xs font-medium"
                                            title="Ver documento original"
                                        >
                                            <ExternalLink size={13} /> PDF
                                        </a>
                                        <a
                                            href={`/api/aplazamientos/documentos/${doc.id}/pdf`}
                                            download
                                            className="p-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded"
                                            title="Descargar"
                                        >
                                            <Download size={15} />
                                        </a>
                                        <button
                                            onClick={() => handleOmitir(doc)}
                                            className="p-1.5 bg-gray-100 hover:bg-red-100 hover:text-red-600 text-gray-500 rounded"
                                            title="Ocultar"
                                        >
                                            <EyeOff size={15} />
                                        </button>
                                    </div>
                                </div>

                                {/* Detalle expandido */}
                                {expandido && (
                                    <div className="border-t bg-gray-50 px-4 py-4">
                                        {detalle.length === 0 ? (
                                            <p className="text-sm text-gray-500 italic">Sin datos de liquidación extraídos.</p>
                                        ) : (
                                            <div className="space-y-4">
                                                {detalle.map((liq, liqIdx) => (
                                                    <div key={liqIdx} className="border rounded-lg overflow-hidden bg-white">
                                                        {/* Cabecera liquidación */}
                                                        <div className="bg-blue-50 px-3 py-2 border-b flex items-center gap-3">
                                                            <span className="font-mono text-sm font-bold text-blue-800">{liq.numero_liquidacion}</span>
                                                            {liq.concepto && <span className="text-xs text-blue-600">{liq.concepto}</span>}
                                                            {liq.fecha_intereses && <span className="text-xs text-gray-500 ml-auto">Int. desde: {liq.fecha_intereses}</span>}
                                                        </div>
                                                        {/* Tabla plazos */}
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-xs">
                                                                <thead className="bg-gray-100">
                                                                    <tr>
                                                                        <th className="px-3 py-1.5 text-center font-semibold border-b border-r">Plazo</th>
                                                                        <th className="px-3 py-1.5 text-right font-semibold border-b border-r">Principal</th>
                                                                        <th className="px-3 py-1.5 text-right font-semibold border-b border-r">Recargo</th>
                                                                        <th className="px-3 py-1.5 text-right font-semibold border-b border-r">Total Deuda</th>
                                                                        <th className="px-3 py-1.5 text-right font-semibold border-b border-r">Intereses</th>
                                                                        <th className="px-3 py-1.5 text-right font-semibold border-b border-r">Total Plazo</th>
                                                                        <th className="px-3 py-1.5 text-center font-semibold border-b">Vencimiento</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {(liq.plazos || []).map((p, pIdx) => (
                                                                        <tr key={pIdx} className="border-t hover:bg-blue-50">
                                                                            <td className="px-3 py-1.5 text-center border-r text-gray-500">{pIdx + 1}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(p.importe_principal || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(p.recargo_apremio || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(p.importe_total_deuda || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r text-orange-600">€{(p.importe_intereses || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r font-semibold">€{(p.importe_total_plazo || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-center font-medium text-blue-700">{p.fecha_vencimiento || '—'}</td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                                {liq.subtotal && (
                                                                    <tfoot className="bg-gray-100 font-semibold border-t-2">
                                                                        <tr>
                                                                            <td className="px-3 py-1.5 text-center border-r text-gray-500 text-xs">Sub</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(liq.subtotal.importe_principal || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(liq.subtotal.recargo_apremio || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(liq.subtotal.importe_total_deuda || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r text-orange-600">€{(liq.subtotal.importe_intereses || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-right border-r">€{(liq.subtotal.importe_total_plazo || 0).toFixed(2)}</td>
                                                                            <td className="px-3 py-1.5 text-center text-gray-400">Subtotal</td>
                                                                        </tr>
                                                                    </tfoot>
                                                                )}
                                                            </table>
                                                        </div>
                                                    </div>
                                                ))}
                                                {/* Total general */}
                                                <div className="flex justify-end pt-1">
                                                    <div className="bg-gray-800 text-white px-5 py-2 rounded-lg text-sm font-bold">
                                                        TOTAL GENERAL: €{doc.total_deuda.toFixed(2)}
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default AplazamientosView;
