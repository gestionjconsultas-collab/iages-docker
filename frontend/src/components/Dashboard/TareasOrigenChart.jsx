import React, { useEffect, useState } from 'react';
import { Pie } from 'react-chartjs-2';
import './TareasOrigenChart.css';

/**
 * Gráfico de pastel mostrando distribución de tareas por origen
 * Muestra qué % de tareas vienen del Chat IA vs manual vs otros
 */
const TareasOrigenChart = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const response = await fetch('/api/dashboard/tareas-por-origen', {
                credentials: 'include'
            });

            if (!response.ok) throw new Error('Error al cargar datos');

            const result = await response.json();

            // Configurar colores por origen
            const colorMap = {
                chat_ia: '#8b5cf6',
                manual: '#6b7280',
                auto_asignada: '#f59e0b',
                importada: '#3b82f6',
                calendario: '#10b981',
                documento: '#ec4899'
            };

            const labels = result.map(item => {
                const labelMap = {
                    chat_ia: '🤖 Chat IA',
                    manual: '✋ Manual',
                    auto_asignada: '⚡ Auto-asignada',
                    importada: '📥 Importada',
                    calendario: '📅 Calendario',
                    documento: '📄 Documento'
                };
                return labelMap[item.origen] || item.origen;
            });

            const values = result.map(item => item.total);
            const colors = result.map(item => colorMap[item.origen] || '#6b7280');

            setData({
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: '#ffffff',
                    borderWidth: 2,
                    hoverOffset: 8
                }]
            });

            setLoading(false);
        } catch (err) {
            console.error('Error fetching tareas por origen:', err);
            setError(err.message);
            setLoading(false);
        }
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 15,
                    font: {
                        size: 12,
                        family: "'Inter', sans-serif"
                    },
                    usePointStyle: true,
                    pointStyle: 'circle'
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleFont: {
                    size: 14,
                    weight: 'bold'
                },
                bodyFont: {
                    size: 13
                },
                callbacks: {
                    label: (context) => {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} tareas (${percentage}%)`;
                    }
                }
            }
        }
    };

    if (loading) {
        return (
            <div className="tareas-origen-chart">
                <h3 className="chart-title">Tareas por Origen</h3>
                <div className="chart-loading">
                    <div className="spinner"></div>
                    <p>Cargando datos...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="tareas-origen-chart">
                <h3 className="chart-title">Tareas por Origen</h3>
                <div className="chart-error">
                    <p>❌ {error}</p>
                </div>
            </div>
        );
    }

    if (!data || data.datasets[0].data.length === 0) {
        return (
            <div className="tareas-origen-chart">
                <h3 className="chart-title">Tareas por Origen</h3>
                <div className="chart-empty">
                    <p>No hay tareas para mostrar</p>
                </div>
            </div>
        );
    }

    return (
        <div className="tareas-origen-chart">
            <h3 className="chart-title">Tareas por Origen</h3>
            <div className="chart-container">
                <Pie data={data} options={options} />
            </div>

            {/* Estadísticas adicionales */}
            <div className="chart-stats">
                <div className="stat-item">
                    <span className="stat-label">Total tareas:</span>
                    <span className="stat-value">
                        {data.datasets[0].data.reduce((a, b) => a + b, 0)}
                    </span>
                </div>
                {data.labels.includes('🤖 Chat IA') && (
                    <div className="stat-item highlight">
                        <span className="stat-label">Creadas por IA:</span>
                        <span className="stat-value">
                            {data.datasets[0].data[data.labels.indexOf('🤖 Chat IA')]}
                            <span className="stat-percentage">
                                ({((data.datasets[0].data[data.labels.indexOf('🤖 Chat IA')] /
                                    data.datasets[0].data.reduce((a, b) => a + b, 0)) * 100).toFixed(1)}%)
                            </span>
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TareasOrigenChart;
