// frontend/src/components/SuperAdmin/BillingAdminView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Building2,
    CreditCard,
    CheckCircle,
    AlertCircle,
    Download,
    Eye,
    Search,
    Filter,
    Settings
} from 'lucide-react';
import BillingConfigAdmin from './BillingConfigAdmin';

const BillingAdminView = () => {
    const [suscripciones, setSuscripciones] = useState([]);
    const [facturas, setFacturas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filtroEstado, setFiltroEstado] = useState('todas');
    const [busqueda, setBusqueda] = useState('');
    const [activeTab, setActiveTab] = useState('facturacion'); // 'facturacion' o 'config'

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const [suscripcionesRes, facturasRes] = await Promise.all([
                axios.get('/api/admin/suscripciones'),
                axios.get('/api/admin/facturas')
            ]);

            setSuscripciones(suscripcionesRes.data.suscripciones || []);
            setFacturas(facturasRes.data.facturas || []);
        } catch (error) {
            console.error('Error cargando datos:', error);
        } finally {
            setLoading(false);
        }
    };

    const marcarComoPagada = async (facturaId) => {
        if (!confirm('¿Marcar esta factura como pagada?')) return;

        try {
            await axios.post(`/api/facturas/${facturaId}/marcar-pagada`, {
                metodo_pago: 'transferencia'
            });
            alert('✅ Factura marcada como pagada');
            cargarDatos();
        } catch (error) {
            alert('❌ Error: ' + (error.response?.data?.error || 'Error desconocido'));
        }
    };

    const descargarPDF = async (facturaId, numeroFactura) => {
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
        }
    };

    const facturasFiltradas = facturas.filter(f => {
        const coincideBusqueda = f.gestoria_nombre?.toLowerCase().includes(busqueda.toLowerCase()) ||
            f.numero_factura?.toLowerCase().includes(busqueda.toLowerCase());

        const coincideEstado = filtroEstado === 'todas' || f.estado === filtroEstado;

        return coincideBusqueda && coincideEstado;
    });

    const stats = {
        totalSuscripciones: suscripciones.length,
        suscripcionesActivas: suscripciones.filter(s => s.estado === 'activa' || s.estado === 'trial').length,
        totalFacturas: facturas.length,
        facturasPendientes: facturas.filter(f => f.estado === 'pendiente').length,
        facturasPagadas: facturas.filter(f => f.estado === 'pagada').length,
        totalPendiente: facturas
            .filter(f => f.estado === 'pendiente')
            .reduce((sum, f) => sum + parseFloat(f.total), 0),
        totalCobrado: facturas
            .filter(f => f.estado === 'pagada')
            .reduce((sum, f) => sum + parseFloat(f.total), 0)
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">
                        Gestión de Facturación
                    </h1>
                    <div className="flex items-center justify-between">
                        <p className="text-gray-600">
                            Vista de super-admin para gestionar todas las suscripciones y facturas
                        </p>
                        <div className="flex bg-white rounded-xl p-1 shadow-sm border border-gray-100">
                            <button
                                onClick={() => setActiveTab('facturacion')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'facturacion' ? 'bg-orange-500 text-white shadow-md' : 'text-gray-500 hover:bg-gray-50'}`}
                            >
                                <CreditCard className="w-4 h-4" />
                                FACTURACIÓN
                            </button>
                            <button
                                onClick={() => setActiveTab('config')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${activeTab === 'config' ? 'bg-orange-500 text-white shadow-md' : 'text-gray-500 hover:bg-gray-50'}`}
                            >
                                <Settings className="w-4 h-4" />
                                CONFIGURACIÓN IAGES
                            </button>
                        </div>
                    </div>
                </div>

                {activeTab === 'facturacion' ? (
                    <>
                        {/* Stats */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium text-gray-600">Suscripciones Activas</h3>
                                    <Building2 className="w-5 h-5 text-green-500" />
                                </div>
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.suscripcionesActivas}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">
                                    de {stats.totalSuscripciones} total
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium text-gray-600">Facturas Pendientes</h3>
                                    <AlertCircle className="w-5 h-5 text-yellow-500" />
                                </div>
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.facturasPendientes}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">
                                    €{stats.totalPendiente.toFixed(2)}
                                </div>
                            </div>

                            <div className="bg-white rounded-lg shadow p-6">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium text-gray-600">Facturas Pagadas</h3>
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                </div>
                                <div className="text-3xl font-bold text-gray-900">
                                    {stats.facturasPagadas}
                                </div>
                                <div className="text-sm text-gray-500 mt-1">
                                    €{stats.totalCobrado.toFixed(2)}
                                </div>
                            </div>

                            <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow p-6 text-white">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-sm font-medium opacity-90">Total Facturado</h3>
                                    <CreditCard className="w-5 h-5 opacity-75" />
                                </div>
                                <div className="text-3xl font-bold">
                                    €{(stats.totalCobrado + stats.totalPendiente).toFixed(2)}
                                </div>
                                <div className="text-sm opacity-90 mt-1">
                                    Este mes
                                </div>
                            </div>
                        </div>

                        {/* Filtros */}
                        <div className="bg-white rounded-lg shadow p-4 mb-6">
                            <div className="flex flex-col md:flex-row gap-4">
                                <div className="flex-1">
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                                        <input
                                            type="text"
                                            value={busqueda}
                                            onChange={(e) => setBusqueda(e.target.value)}
                                            placeholder="Buscar por gestoría o número de factura..."
                                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    {['todas', 'pendiente', 'pagada', 'vencida'].map(estado => (
                                        <button
                                            key={estado}
                                            onClick={() => setFiltroEstado(estado)}
                                            className={`
                    px-4 py-2 rounded-lg font-medium transition-all capitalize
                    ${filtroEstado === estado
                                                    ? 'bg-orange-500 text-white'
                                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                                }
                  `}
                                        >
                                            {estado}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Tabla de Facturas */}
                        <div className="bg-white rounded-lg shadow overflow-hidden">
                            <div className="px-6 py-4 border-b border-gray-200">
                                <h2 className="text-lg font-semibold text-gray-900">
                                    Facturas ({facturasFiltradas.length})
                                </h2>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="w-full">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Factura
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Gestoría
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Fecha
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Importe
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Estado
                                            </th>
                                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                Acciones
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {facturasFiltradas.map(factura => (
                                            <tr key={factura.id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="font-medium text-gray-900">
                                                        {factura.numero_factura}
                                                    </div>
                                                    <div className="text-sm text-gray-500">
                                                        {factura.concepto}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="flex items-center">
                                                        <Building2 className="w-4 h-4 text-gray-400 mr-2" />
                                                        <span className="text-sm text-gray-900">
                                                            {factura.gestoria_nombre || `ID: ${factura.gestoria_id}`}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {new Date(factura.fecha_emision).toLocaleDateString('es-ES')}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <div className="text-sm font-semibold text-gray-900">
                                                        €{factura.total}
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap">
                                                    <span className={`
                        inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                        ${factura.estado === 'pagada' ? 'bg-green-100 text-green-800' :
                                                            factura.estado === 'pendiente' ? 'bg-yellow-100 text-yellow-800' :
                                                                'bg-red-100 text-red-800'}
                      `}>
                                                        {factura.estado === 'pagada' ? '✓ Pagada' :
                                                            factura.estado === 'pendiente' ? '⏳ Pendiente' :
                                                                '⚠️ Vencida'}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                    <div className="flex items-center justify-end gap-2">
                                                        <button
                                                            onClick={() => descargarPDF(factura.id, factura.numero_factura)}
                                                            className="text-blue-600 hover:text-blue-900"
                                                            title="Descargar PDF"
                                                        >
                                                            <Download className="w-4 h-4" />
                                                        </button>
                                                        {factura.estado === 'pendiente' && (
                                                            <button
                                                                onClick={() => marcarComoPagada(factura.id)}
                                                                className="text-green-600 hover:text-green-900"
                                                                title="Marcar como pagada"
                                                            >
                                                                <CheckCircle className="w-4 h-4" />
                                                            </button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {facturasFiltradas.length === 0 && (
                                <div className="text-center py-12">
                                    <p className="text-gray-500">No se encontraron facturas</p>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <BillingConfigAdmin />
                )}
            </div>
        </div>
    );
};

export default BillingAdminView;
