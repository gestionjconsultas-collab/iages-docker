import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function GestoriasMetricsView() {
    const [metrics, setMetrics] = useState([]);
    const [iaGlobal, setIaGlobal] = useState(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        loadMetrics();
    }, []);

    const loadMetrics = async () => {
        try {
            const res = await axios.get('/api/admin/super-admin/gestorias/metrics');
            setMetrics(res.data.gestorias || res.data); // Compatibilidad con ambas estructuras
            setIaGlobal(res.data.ia_global || null);
        } catch (error) {
            console.error('Error cargando métricas:', error);
            alert('Error cargando métricas: ' + (error.response?.data?.error || error.message));
        } finally {
            setLoading(false);
        }
    };

    const filteredMetrics = metrics.filter(m =>
        m.nombre.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const getProgressColor = (porcentaje) => {
        if (porcentaje >= 90) return 'bg-red-500';
        if (porcentaje >= 80) return 'bg-yellow-500';
        return 'bg-green-500';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-xl">Cargando métricas...</div>
            </div>
        );
    }

    return (
        <div className="p-8 bg-gray-50 min-h-screen">
            <div className="mb-6">
                <h1 className="text-3xl font-bold mb-2">Dashboard de Gestorías</h1>
                <p className="text-gray-600">Métricas y uso de recursos por gestoría</p>
            </div>

            {/* Búsqueda */}
            <div className="mb-6">
                <input
                    type="text"
                    placeholder="Buscar gestoría..."
                    className="w-full md:w-96 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            {/* Resumen General */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="text-gray-500 text-sm mb-1">Total Gestorías</div>
                    <div className="text-3xl font-bold">{metrics.length}</div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="text-gray-500 text-sm mb-1">Gestorías Activas</div>
                    <div className="text-3xl font-bold text-green-600">
                        {metrics.filter(m => m.activa).length}
                    </div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="text-gray-500 text-sm mb-1">Total Empresas</div>
                    <div className="text-3xl font-bold">
                        {metrics.reduce((sum, m) => sum + m.empresas.usado, 0)}
                    </div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="text-gray-500 text-sm mb-1">Storage Total (GB)</div>
                    <div className="text-3xl font-bold">
                        {metrics.reduce((sum, m) => sum + m.storage.usado_gb, 0).toFixed(2)}
                    </div>
                </div>
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="text-gray-500 text-sm mb-1">Tokens IA (mes)</div>
                    <div className="text-3xl font-bold text-purple-600">
                        {(metrics.reduce((sum, m) => sum + (m.ia_usage?.tokens || 0), 0) / 1000).toFixed(1)}K
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        {metrics.reduce((sum, m) => sum + (m.ia_usage?.requests || 0), 0)} requests
                    </div>
                </div>
            </div>

            {/* Tabla de Métricas */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Gestoría
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Plan
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Empresas
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Usuarios
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Storage
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Uso IA
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Estado
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredMetrics.length === 0 ? (
                                <tr>
                                    <td colSpan="7" className="px-6 py-4 text-center text-gray-500">
                                        No se encontraron gestorías
                                    </td>
                                </tr>
                            ) : (
                                filteredMetrics.map((gestoria) => (
                                    <tr key={gestoria.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="font-medium text-gray-900">{gestoria.nombre}</div>
                                            <div className="text-sm text-gray-500">{gestoria.slug}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="px-3 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 capitalize">
                                                {gestoria.plan}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {gestoria.empresas.usado} / {gestoria.empresas.limite}
                                            </div>
                                            <div className="w-32 bg-gray-200 rounded-full h-2 mt-2">
                                                <div
                                                    className={`h-2 rounded-full transition-all ${getProgressColor(gestoria.empresas.porcentaje)}`}
                                                    style={{ width: `${Math.min(gestoria.empresas.porcentaje, 100)}%` }}
                                                />
                                            </div>
                                            <div className="text-xs text-gray-500 mt-1">
                                                {gestoria.empresas.porcentaje.toFixed(1)}%
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {gestoria.usuarios.usado} / {gestoria.usuarios.limite === -1 ? '∞' : gestoria.usuarios.limite}
                                            </div>
                                            {gestoria.usuarios.limite !== -1 && (
                                                <>
                                                    <div className="w-32 bg-gray-200 rounded-full h-2 mt-2">
                                                        <div
                                                            className={`h-2 rounded-full transition-all ${getProgressColor(gestoria.usuarios.porcentaje)}`}
                                                            style={{ width: `${Math.min(gestoria.usuarios.porcentaje, 100)}%` }}
                                                        />
                                                    </div>
                                                    <div className="text-xs text-gray-500 mt-1">
                                                        {gestoria.usuarios.porcentaje.toFixed(1)}%
                                                    </div>
                                                </>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {gestoria.storage.usado_gb.toFixed(2)} / {gestoria.storage.limite_gb} GB
                                            </div>
                                            <div className="w-32 bg-gray-200 rounded-full h-2 mt-2">
                                                <div
                                                    className={`h-2 rounded-full transition-all ${getProgressColor(gestoria.storage.porcentaje)}`}
                                                    style={{ width: `${Math.min(gestoria.storage.porcentaje, 100)}%` }}
                                                />
                                            </div>
                                            <div className="text-xs text-gray-500 mt-1">
                                                {gestoria.storage.porcentaje.toFixed(1)}%
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm">
                                                <div className="font-medium text-gray-900">
                                                    {((gestoria.ia_usage?.tokens || 0) / 1000).toFixed(1)}K tokens
                                                </div>
                                                <div className="text-xs text-gray-500 mt-1">
                                                    {gestoria.ia_usage?.requests || 0} requests
                                                </div>
                                                <div className="text-xs text-green-600 mt-1">
                                                    ✓ {gestoria.ia_usage?.success_rate || 100}% éxito
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col gap-2">
                                                {gestoria.activa ? (
                                                    <span className="px-3 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 inline-block">
                                                        ✓ Activa
                                                    </span>
                                                ) : (
                                                    <span className="px-3 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 inline-block">
                                                        ✗ Inactiva
                                                    </span>
                                                )}
                                                {gestoria.alertas.length > 0 && (
                                                    <span className="px-3 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 inline-block">
                                                        ⚠️ {gestoria.alertas.length} alerta(s)
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
