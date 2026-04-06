import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, TrendingUp, AlertTriangle, CheckCircle, Key, Zap } from 'lucide-react';

export default function ApiKeysMonitor() {
    const [stats, setStats] = useState(null);
    const [current, setCurrent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        cargarDatos();
        const interval = setInterval(cargarDatos, 30000);
        return () => clearInterval(interval);
    }, []);

    const cargarDatos = async () => {
        try {
            const [statsRes, currentRes] = await Promise.all([
                axios.get('/api/admin/api-keys/stats', { withCredentials: true }),
                axios.get('/api/admin/api-keys/current', { withCredentials: true })
            ]);

            setStats(statsRes.data);
            setCurrent(currentRes.data);
            setError(null);
        } catch (error) {
            console.error('Error cargando stats:', error);
            if (error.response?.status === 403) {
                setError('No tienes permisos para acceder a esta página. Solo usuarios de Jefatura pueden ver el monitoreo de API keys.');
            } else if (error.response?.status === 401) {
                setError('Debes iniciar sesión para acceder a esta página.');
            } else {
                setError('Error cargando datos del servidor. Por favor intenta de nuevo.');
            }
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-gray-500">Cargando estadísticas...</div>
            </div>
        );
    }

    if (!stats || !current || error) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-center max-w-md">
                    <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
                    <p className="text-gray-600">
                        {error || 'Error cargando datos'}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto">
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">Monitoreo de API Keys</h1>
                <p className="text-gray-600 mt-1">Gemini API - Uso y estadísticas</p>
            </div>

            {/* Tarjetas de resumen */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard
                    title="Requests Hoy"
                    value={stats.summary.total_requests}
                    icon={<Activity className="w-6 h-6" />}
                    color="blue"
                />
                <StatCard
                    title="Keys Activas"
                    value={`${stats.summary.available_keys || stats.summary.active_keys} / ${stats.summary.total_keys}`}
                    icon={<CheckCircle className="w-6 h-6" />}
                    color="green"
                />
                <StatCard
                    title="Tasa de Éxito"
                    value={`${stats.summary.success_rate}%`}
                    icon={<TrendingUp className="w-6 h-6" />}
                    color="purple"
                />
                <StatCard
                    title="Tokens Usados"
                    value={stats.summary.total_tokens.toLocaleString()}
                    icon={<Zap className="w-6 h-6" />}
                    color="orange"
                />
            </div>

            {/* Tabla de estado de keys */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">Estado de API Keys</h2>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    API Key
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Estado
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Requests
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Restantes
                                </th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Tokens
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Uso
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {current.keys.map(key => (
                                <tr key={key.key_name} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <Key className="w-4 h-4 text-gray-400 mr-2" />
                                            <span className="text-sm font-medium text-gray-900">
                                                {key.key_name}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <StatusBadge status={key.status} />
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                                        {key.requests_used}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                                        {key.requests_remaining}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900">
                                        {key.tokens_used.toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                                                <div
                                                    className="h-2 rounded-full"
                                                    style={{
                                                        width: `${Math.min(key.usage_percent, 100)}%`,
                                                        backgroundColor: key.status === 'available' ? '#10b981' :
                                                            key.status === 'warning' ? '#eab308' :
                                                                key.status === 'critical' ? '#f97316' : '#ef4444'
                                                    }}
                                                />
                                            </div>
                                            <span className="text-sm text-gray-600 w-12 text-right">
                                                {key.usage_percent}%
                                            </span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Alertas */}
            {current.available_keys === 0 && (
                <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <div className="flex items-start">
                        <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 mr-3" />
                        <div>
                            <h3 className="text-sm font-medium text-red-800">
                                Todas las API keys están agotadas
                            </h3>
                            <p className="text-sm text-red-700 mt-1">
                                Considera agregar más API keys o esperar hasta mañana para el reset diario.
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function StatusBadge({ status }) {
    const colors = {
        available: 'bg-green-100 text-green-800',
        warning: 'bg-yellow-100 text-yellow-800',
        critical: 'bg-primary-light text-orange-800',
        exhausted: 'bg-red-100 text-red-800'
    };

    const labels = {
        available: 'Disponible',
        warning: 'Advertencia',
        critical: 'Crítico',
        exhausted: 'Agotada'
    };

    return (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status]}`}>
            {labels[status]}
        </span>
    );
}

function StatCard({ title, value, icon, color }) {
    const colorClasses = {
        blue: 'bg-blue-50 text-blue-600',
        green: 'bg-green-50 text-green-600',
        purple: 'bg-purple-50 text-purple-600',
        orange: 'bg-primary-light text-primary'
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
                <div className="flex-1">
                    <p className="text-sm font-medium text-gray-600">{title}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-2">{value}</p>
                </div>
                <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
                    {icon}
                </div>
            </div>
        </div>
    );
}
