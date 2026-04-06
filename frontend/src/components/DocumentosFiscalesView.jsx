// frontend/src/components/DocumentosFiscalesView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, Upload, Filter, Calendar, Building2, AlertCircle, CheckCircle, Clock, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import ConfirmarClasificacionModal from './ConfirmarClasificacionModal';

export default function DocumentosFiscalesView() {
    const [documentos, setDocumentos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [empresas, setEmpresas] = useState([]);
    const [documentoSeleccionado, setDocumentoSeleccionado] = useState(null);

    // Filtros
    const [filtros, setFiltros] = useState({
        empresa_id: '',
        ejercicio: new Date().getFullYear(),
        tipo: '',
        estado: ''
    });

    // Cargar datos iniciales
    useEffect(() => {
        cargarEmpresas();
        cargarDocumentos();
    }, [filtros]);

    const cargarEmpresas = async () => {
        try {
            const res = await axios.get('/api/empresas', { withCredentials: true });
            if (res.data.success) {
                setEmpresas(res.data.empresas);
            }
        } catch (error) {
            console.error('Error cargando empresas:', error);
        }
    };

    const cargarDocumentos = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (filtros.empresa_id) params.append('empresa_id', filtros.empresa_id);
            if (filtros.ejercicio) params.append('ejercicio', filtros.ejercicio);
            if (filtros.tipo) params.append('tipo', filtros.tipo);
            if (filtros.estado) params.append('estado', filtros.estado);

            const res = await axios.get(`/api/fiscal/documentos?${params}`, { withCredentials: true });
            if (res.data.success) {
                setDocumentos(res.data.documentos);
            }
        } catch (error) {
            console.error('Error cargando documentos:', error);
            toast.error('Error cargando documentos fiscales');
        } finally {
            setLoading(false);
        }
    };



    const getEstadoBadge = (estado) => {
        const badges = {
            'PENDIENTE_REVISION': { color: 'bg-yellow-100 text-yellow-800', icon: Clock, text: 'Pendiente Revisión' },
            'CONFIRMADO': { color: 'bg-blue-100 text-blue-800', icon: CheckCircle, text: 'Confirmado' },
            'PRESENTADO': { color: 'bg-purple-100 text-purple-800', icon: FileText, text: 'Presentado' },
            'PAGADO': { color: 'bg-green-100 text-green-800', icon: CheckCircle, text: 'Pagado' },
            'VENCIDO': { color: 'bg-red-100 text-red-800', icon: XCircle, text: 'Vencido' }
        };

        const badge = badges[estado] || badges['CONFIRMADO'];
        const Icon = badge.icon;

        return (
            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                <Icon className="w-3 h-3" />
                {badge.text}
            </span>
        );
    };

    const getClasificacionBadge = (clasificacion) => {
        const badges = {
            'PAGO_REQUERIDO': 'bg-red-100 text-red-800 border-red-300',
            'INFORMATIVO': 'bg-gray-100 text-gray-800 border-gray-300',
            'INFORMATIVO_DEVOLUCION': 'bg-green-100 text-green-800 border-green-300',
            'INFORMATIVO_SIN_ACTIVIDAD': 'bg-blue-100 text-blue-800 border-blue-300'
        };

        return (
            <span className={`px-2 py-1 rounded text-xs font-medium border ${badges[clasificacion] || badges['INFORMATIVO']}`}>
                {clasificacion?.replace('_', ' ')}
            </span>
        );
    };

    const getTipoLabel = (tipo) => {
        const labels = {
            'MODELO_303': 'Modelo 303 - IVA',
            'MODELO_130': 'Modelo 130 - IRPF',
            'MODELO_131': 'Modelo 131 - IRPF Módulos',
            'MODELO_111': 'Modelo 111 - Retenciones',
            'MODELO_115': 'Modelo 115 - Alquileres',
            'MODELO_200': 'Modelo 200 - Sociedades',
            'MODELO_202': 'Modelo 202 - P.F. Sociedades',
            'MODELO_216': 'Modelo 216 - IRNR',
            'MODELO_296': 'Modelo 296 - Resumen IRNR',
            'MODELO_180': 'Modelo 180 - Anual Alquileres',
            'MODELO_190': 'Modelo 190 - Anual Retenciones',
            'MODELO_390': 'Modelo 390 - Resumen IVA',
            'CERTIFICADO_RETENCIONES': 'Certificado Retenciones',
            'APLAZAMIENTO_SOLICITUD': 'Aplazamiento - Solicitud',
            'APLAZAMIENTO_CONCESION': 'Aplazamiento - Concesión'
        };
        return labels[tipo] || tipo;
    };

    return (
        <div className="p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Documentos Fiscales</h1>
                    <p className="text-gray-600 mt-1">
                        Gestión de modelos fiscales con IA asistida
                    </p>
                </div>

                <a
                    href="/importar"
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
                >
                    <Upload size={20} />
                    Subir Documentos
                </a>
            </div>

            {/* Filtros */}
            <div className="bg-white rounded-lg shadow-md p-4 mb-6">
                <div className="flex items-center gap-2 mb-3">
                    <Filter className="w-5 h-5 text-gray-600" />
                    <h3 className="font-semibold text-gray-900">Filtros</h3>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Empresa */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Empresa</label>
                        <select
                            value={filtros.empresa_id}
                            onChange={(e) => setFiltros({ ...filtros, empresa_id: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Todas las empresas</option>
                            {empresas.map(emp => (
                                <option key={emp.id} value={emp.id}>{emp.nombre}</option>
                            ))}
                        </select>
                    </div>

                    {/* Ejercicio */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Ejercicio</label>
                        <input
                            type="number"
                            value={filtros.ejercicio}
                            onChange={(e) => setFiltros({ ...filtros, ejercicio: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {/* Tipo */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
                        <select
                            value={filtros.tipo}
                            onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Todos los tipos</option>
                            <option value="MODELO_303">Modelo 303 - IVA</option>
                            <option value="MODELO_130">Modelo 130 - IRPF</option>
                            <option value="MODELO_131">Modelo 131 - IRPF Módulos</option>
                            <option value="MODELO_111">Modelo 111 - Retenciones</option>
                            <option value="MODELO_115">Modelo 115 - Alquileres</option>
                            <option value="MODELO_200">Modelo 200 - Sociedades</option>
                            <option value="MODELO_202">Modelo 202 - P.F. Sociedades</option>
                            <option value="MODELO_216">Modelo 216 - IRNR</option>
                            <option value="MODELO_296">Modelo 296 - Resumen IRNR</option>
                            <option value="MODELO_180">Modelo 180 - Anual Alquileres</option>
                            <option value="MODELO_190">Modelo 190 - Anual Retenciones</option>
                            <option value="MODELO_390">Modelo 390 - Resumen IVA</option>
                            <option value="CERTIFICADO_RETENCIONES">Certificado Retenciones</option>
                            <option value="APLAZAMIENTO_SOLICITUD">Aplazamiento - Solicitud</option>
                            <option value="APLAZAMIENTO_CONCESION">Aplazamiento - Concesión</option>
                        </select>
                    </div>

                    {/* Estado */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                        <select
                            value={filtros.estado}
                            onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Todos los estados</option>
                            <option value="PENDIENTE_REVISION">Pendiente Revisión</option>
                            <option value="CONFIRMADO">Confirmado</option>
                            <option value="PRESENTADO">Presentado</option>
                            <option value="PAGADO">Pagado</option>
                            <option value="VENCIDO">Vencido</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* Tabla de Documentos */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                </div>
            ) : documentos.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <FileText size={48} className="mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                        No hay documentos fiscales
                    </h3>
                    <p className="text-gray-600">
                        Ve a <a href="/importar" className="text-primary hover:underline">Importar Documentos</a> → Documentos Fiscales para subir archivos
                    </p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow-md overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ejercicio</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Empresa</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Clasificación</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Importe</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vencimiento</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {documentos.map((doc) => (
                                <tr key={doc.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {getTipoLabel(doc.tipo_documento)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {doc.ejercicio_fiscal} {doc.periodo}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {doc.empresa_nombre}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {getClasificacionBadge(doc.clasificacion_confirmada || doc.clasificacion_sugerida)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        {getEstadoBadge(doc.estado)}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                        {doc.importe_pago ? `${doc.importe_pago.toFixed(2)}€` : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                                        {doc.fecha_limite_pago ? (
                                            <span className={doc.dias_hasta_vencimiento < 0 ? 'text-red-600 font-semibold' : ''}>
                                                {new Date(doc.fecha_limite_pago).toLocaleDateString()}
                                            </span>
                                        ) : '-'}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        {doc.requiere_confirmacion && (
                                            <button
                                                onClick={() => setDocumentoSeleccionado(doc)}
                                                className="text-blue-600 hover:text-blue-800 font-medium"
                                            >
                                                Revisar
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Modal de Confirmación */}
            {documentoSeleccionado && (
                <ConfirmarClasificacionModal
                    documento={documentoSeleccionado}
                    onClose={() => {
                        setDocumentoSeleccionado(null);
                        cargarDocumentos();
                    }}
                />
            )}
        </div>
    );
}
