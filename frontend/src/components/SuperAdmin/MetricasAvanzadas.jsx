import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, DollarSign, Users, Zap } from 'lucide-react';

const COLORS = {
    basico: '#6B7280',
    plus: '#3B82F6',
    premium: '#9333EA'
};

export default function MetricasAvanzadas() {
    const [metricas, setMetricas] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        cargarMetricas();
    }, []);

    const cargarMetricas = async () => {
        try {
            const response = await axios.get('/api/super-admin/metricas-avanzadas');
            if (response.data.success) {
                setMetricas(response.data);
            }
        } catch (error) {
            console.error('Error cargando métricas:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!metricas) {
        return null;
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-900">Métricas Avanzadas</h2>
                <button
                    onClick={cargarMetricas}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                    Actualizar
                </button>
            </div>

            {/* Grid de Gráficos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* 1. Ingresos Mensuales */}
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center gap-2 mb-4">
                        <DollarSign className="w-5 h-5 text-green-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Ingresos Mensuales</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={metricas.ingresos_mensuales}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="mes" />
                            <YAxis />
                            <Tooltip
                                formatter={(value) => `€${value.toLocaleString()}`}
                                labelFormatter={(label) => `Mes: ${label}`}
                            />
                            <Bar dataKey="ingresos" fill="#10B981" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* 2. Distribución de Planes */}
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingUp className="w-5 h-5 text-purple-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Distribución de Planes</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={metricas.distribucion_planes}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={({ plan, count, percent }) => `${plan}: ${count} (${(percent * 100).toFixed(0)}%)`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="count"
                            >
                                {metricas.distribucion_planes.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[entry.plan] || '#94A3B8'} />
                                ))}
                            </Pie>
                            <Tooltip />
                        </PieChart>
                    </ResponsiveContainer>
                    <div className="mt-4 flex justify-center gap-4">
                        {metricas.distribucion_planes.map((plan) => (
                            <div key={plan.plan} className="flex items-center gap-2">
                                <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: COLORS[plan.plan] || '#94A3B8' }}
                                ></div>
                                <span className="text-sm text-gray-600 capitalize">{plan.plan}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* 3. Crecimiento de Usuarios */}
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center gap-2 mb-4">
                        <Users className="w-5 h-5 text-blue-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Crecimiento de Usuarios</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={metricas.crecimiento_usuarios}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="mes" />
                            <YAxis />
                            <Tooltip />
                            <Line
                                type="monotone"
                                dataKey="usuarios"
                                stroke="#3B82F6"
                                strokeWidth={2}
                                dot={{ fill: '#3B82F6', r: 4 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* 4. Top 5 Uso de IA */}
                <div className="bg-white p-6 rounded-lg shadow">
                    <div className="flex items-center gap-2 mb-4">
                        <Zap className="w-5 h-5 text-yellow-600" />
                        <h3 className="text-lg font-semibold text-gray-900">Top 5 Uso de IA</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={metricas.top_uso_ia} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" />
                            <YAxis dataKey="gestoria" type="category" width={100} />
                            <Tooltip
                                formatter={(value) => `${value.toLocaleString()} tokens`}
                            />
                            <Bar dataKey="tokens" fill="#F59E0B" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
