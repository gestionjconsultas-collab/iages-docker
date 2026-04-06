import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import DocumentosPieChart from './DocumentosPieChart';
import DocumentosLineChart from './DocumentosLineChart';
import TareasBarChart from './TareasBarChart';
import TareasOrigenChart from './TareasOrigenChart';
import ExportButton from './ExportButton';
import socket from '../../socket'; // ⭐ Import socket

const DashboardGraficos = () => {
    const [stats, setStats] = useState(null);
    const [tendencias, setTendencias] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
        fetchTendencias();

        // ⭐ Auto-refresh: Escuchar evento stats_updated
        socket.on('stats_updated', () => {
            console.log('📊 Stats updated, refetching dashboard data...');
            fetchStats();
            fetchTendencias();
        });

        // Cleanup
        return () => {
            socket.off('stats_updated');
        };
    }, []);

    const fetchStats = async () => {
        try {
            const response = await fetch('/api/dashboard/stats-graficos');
            const data = await response.json();
            if (data.success) {
                setStats(data.data);
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchTendencias = async () => {
        try {
            const response = await fetch('/api/dashboard/tendencias');
            const data = await response.json();
            if (data.success) {
                setTendencias(data.data);
            }
        } catch (error) {
            console.error('Error fetching tendencias:', error);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="text-center text-gray-500 py-8">
                Error al cargar estadísticas
            </div>
        );
    }

    const getTendenciaIcon = () => {
        if (!tendencias) return null;

        if (tendencias.tendencia === 'subida') {
            return <TrendingUp className="text-green-600" size={20} />;
        } else if (tendencias.tendencia === 'bajada') {
            return <TrendingDown className="text-red-600" size={20} />;
        } else {
            return <Minus className="text-gray-600" size={20} />;
        }
    };

    const getTendenciaColor = () => {
        if (!tendencias) return 'text-gray-600';

        if (tendencias.tendencia === 'subida') {
            return 'text-green-600';
        } else if (tendencias.tendencia === 'bajada') {
            return 'text-red-600';
        } else {
            return 'text-gray-600';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header con botones de exportación */}
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-800">
                    📊 Dashboard Analítico
                </h2>
                <div className="flex gap-3">
                    <ExportButton tipo="documentos" label="Exportar Documentos" />
                    <ExportButton tipo="tareas" label="Exportar Tareas" />
                    <ExportButton tipo="empresas" label="Exportar Empresas" />
                </div>
            </div>

            {/* Resumen rápido */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Procesados Hoy */}
                <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg p-6 text-white">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-blue-100 text-sm font-medium">Procesados Hoy</p>
                            <p className="text-3xl font-bold mt-2">{stats.resumen.procesados_hoy}</p>
                        </div>
                        <div className="bg-white bg-opacity-20 rounded-full p-3">
                            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                                <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                        </div>
                    </div>
                </div>

                {/* Pendientes */}
                <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow-lg p-6 text-white">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-orange-100 text-sm font-medium">Pendientes</p>
                            <p className="text-3xl font-bold mt-2">{stats.resumen.pendientes}</p>
                        </div>
                        <div className="bg-white bg-opacity-20 rounded-full p-3">
                            <svg className="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                            </svg>
                        </div>
                    </div>
                </div>

                {/* Tendencia */}
                {tendencias && (
                    <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow-lg p-6 text-white">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-purple-100 text-sm font-medium">Tendencia Mensual</p>
                                <div className="flex items-center gap-2 mt-2">
                                    <p className="text-3xl font-bold">{tendencias.cambio_porcentaje}%</p>
                                    {getTendenciaIcon()}
                                </div>
                                <p className="text-purple-100 text-xs mt-1">
                                    {tendencias.mes_actual} docs este mes vs {tendencias.mes_anterior} mes anterior
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Gráficos principales */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <DocumentosPieChart data={stats.por_categoria} />
                <TareasBarChart data={stats.tareas_por_estado} />
                <TareasOrigenChart />
            </div>

            {/* Gráfico de tendencia (ancho completo) */}
            <DocumentosLineChart data={stats.por_mes} />

            {/* Top Empresas */}
            {stats.top_empresas && stats.top_empresas.length > 0 && (
                <div className="bg-white rounded-lg shadow p-6">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">
                        🏢 Top 5 Empresas con Más Documentos
                    </h3>
                    <div className="space-y-3">
                        {stats.top_empresas.map((empresa, index) => (
                            <div key={index} className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className={`
                    w-8 h-8 rounded-full flex items-center justify-center font-bold text-white
                    ${index === 0 ? 'bg-yellow-500' :
                                            index === 1 ? 'bg-gray-400' :
                                                index === 2 ? 'bg-orange-600' : 'bg-blue-500'}
                  `}>
                                        {index + 1}
                                    </div>
                                    <span className="font-medium text-gray-700">{empresa.nombre}</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="w-64 bg-gray-200 rounded-full h-2">
                                        <div
                                            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                                            style={{
                                                width: `${(empresa.total / stats.top_empresas[0].total) * 100}%`
                                            }}
                                        ></div>
                                    </div>
                                    <span className="font-bold text-gray-800 w-12 text-right">
                                        {empresa.total}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default DashboardGraficos;
