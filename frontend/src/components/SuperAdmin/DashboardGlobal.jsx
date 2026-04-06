import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Building, Users, FileText, AlertTriangle, TrendingUp, Activity, Download } from 'lucide-react';
import MetricasAvanzadas from './MetricasAvanzadas';
import ExportarReportes from './ExportarReportes';
import MaintenanceModeControl from '../MaintenanceModeControl';

export default function DashboardGlobal() {
    const [metricas, setMetricas] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showExportModal, setShowExportModal] = useState(false);

    useEffect(() => {
        cargarDashboard();
    }, []);

    const cargarDashboard = async () => {
        try {
            const response = await axios.get('/api/super-admin/dashboard-global');
            if (response.data.success) {
                setMetricas(response.data);
            }
        } catch (error) {
            console.error('Error cargando dashboard:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!metricas) {
        return (
            <div className="p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-800">Error al cargar el dashboard</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">Dashboard Super-Admin</h1>
                    <p className="text-gray-600 mt-2">Vista global del sistema multi-gestoría</p>
                </div>

                {/* Métricas Generales */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <MetricCard
                        icon={<Building className="w-6 h-6" />}
                        title="Gestorías"
                        value={metricas.metricas_generales.total_gestorias}
                        subtitle={`${metricas.metricas_generales.gestorias_activas} activas`}
                        color="blue"
                    />
                    <MetricCard
                        icon={<Users className="w-6 h-6" />}
                        title="Usuarios"
                        value={metricas.metricas_generales.total_usuarios}
                        subtitle={`${metricas.metricas_generales.usuarios_online} online`}
                        color="green"
                    />
                    <MetricCard
                        icon={<FileText className="w-6 h-6" />}
                        title="Empresas"
                        value={metricas.metricas_generales.total_empresas}
                        subtitle={`${metricas.metricas_generales.total_documentos} documentos`}
                        color="purple"
                    />
                    <MetricCard
                        icon={<AlertTriangle className="w-6 h-6" />}
                        title="Alertas"
                        value={metricas.alertas.total}
                        subtitle={`${metricas.alertas.criticas} críticas`}
                        color={metricas.alertas.criticas > 0 ? 'red' : 'gray'}
                    />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Gestorías Más Activas */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Activity className="w-5 h-5 text-blue-600" />
                            <h2 className="text-xl font-bold text-gray-900">Gestorías Más Activas Hoy</h2>
                        </div>
                        <div className="space-y-3">
                            {metricas.gestorias_activas_hoy.length > 0 ? (
                                metricas.gestorias_activas_hoy.map((g, i) => (
                                    <div key={i} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-600 rounded-full font-bold">
                                                {i + 1}
                                            </div>
                                            <span className="font-medium text-gray-900">{g.nombre}</span>
                                        </div>
                                        <span className="text-sm text-gray-600 font-medium">
                                            {g.documentos} docs
                                        </span>
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-500 text-center py-4">No hay actividad hoy</p>
                            )}
                        </div>
                    </div>

                    {/* Uso de IA */}
                    <div className="bg-white rounded-lg shadow p-6">
                        <div className="flex items-center gap-2 mb-4">
                            <TrendingUp className="w-5 h-5 text-purple-600" />
                            <h2 className="text-xl font-bold text-gray-900">Uso de IA Este Mes</h2>
                        </div>
                        <div className="space-y-4">
                            {metricas.uso_ia.length > 0 ? (
                                metricas.uso_ia.map((u, i) => (
                                    <div key={i}>
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="font-medium text-gray-900">{u.nombre}</span>
                                            <span className="text-sm text-gray-600">
                                                {u.porcentaje.toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2.5">
                                                <div
                                                    className={`h-2.5 rounded-full transition-all ${u.porcentaje >= 90 ? 'bg-red-500' :
                                                        u.porcentaje >= 80 ? 'bg-yellow-500' :
                                                            u.porcentaje >= 50 ? 'bg-blue-500' :
                                                                'bg-green-500'
                                                        }`}
                                                    style={{ width: `${Math.min(u.porcentaje, 100)}%` }}
                                                />
                                            </div>
                                        </div>
                                        <div className="flex justify-between mt-1">
                                            <span className="text-xs text-gray-500">
                                                {u.tokens_usados.toLocaleString()} tokens
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                Límite: {u.tokens_limite.toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <p className="text-gray-500 text-center py-4">No hay uso de IA registrado</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Modo de Mantenimiento */}
                <div className="mt-8">
                    <MaintenanceModeControl />
                </div>

                {/* Métricas Avanzadas */}
                <div className="mt-8">
                    <MetricasAvanzadas />
                </div>

                {/* Botones de Acción */}
                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                    <button
                        onClick={() => setShowExportModal(true)}
                        className="bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
                    >
                        <Download className="w-5 h-5" />
                        Exportar Reportes
                    </button>
                    <button
                        onClick={() => window.location.href = '/super-admin/gestorias'}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-6 rounded-lg transition flex items-center justify-center gap-2"
                    >
                        <Building className="w-5 h-5" />
                        Ver Todas las Gestorías
                    </button>
                </div>

                {/* Modal de Exportación */}
                {showExportModal && (
                    <ExportarReportes onClose={() => setShowExportModal(false)} />
                )}
            </div>
        </div>
    );
}

function MetricCard({ icon, title, value, subtitle, color }) {
    const colors = {
        blue: 'bg-blue-500',
        green: 'bg-green-500',
        purple: 'bg-purple-500',
        red: 'bg-red-500',
        gray: 'bg-gray-500'
    };

    const bgColors = {
        blue: 'bg-blue-50',
        green: 'bg-green-50',
        purple: 'bg-purple-50',
        red: 'bg-red-50',
        gray: 'bg-gray-50'
    };

    return (
        <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
            <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${bgColors[color]}`}>
                    <div className={`${colors[color].replace('bg-', 'text-')}`}>
                        {icon}
                    </div>
                </div>
            </div>
            <h3 className="text-gray-600 text-sm font-medium mb-1">{title}</h3>
            <p className="text-3xl font-bold text-gray-900 mb-1">{value?.toLocaleString() || 0}</p>
            {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
        </div>
    );
}
