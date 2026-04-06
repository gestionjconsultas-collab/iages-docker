import React from 'react';
import { Pie } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    ArcElement,
    Tooltip,
    Legend
} from 'chart.js';

// Registrar componentes de Chart.js
ChartJS.register(ArcElement, Tooltip, Legend);

const DocumentosPieChart = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-gray-500 py-8">
                No hay datos disponibles
            </div>
        );
    }

    const chartData = {
        labels: data.map(item => item.categoria),
        datasets: [
            {
                label: 'Documentos por Categoría',
                data: data.map(item => item.total),
                backgroundColor: [
                    'rgba(76, 175, 80, 0.8)',   // Verde - Nóminas
                    'rgba(33, 150, 243, 0.8)',  // Azul - Seguros Sociales
                    'rgba(255, 152, 0, 0.8)',   // Naranja - Fiscal
                    'rgba(156, 39, 176, 0.8)',  // Morado - Por Procesar
                    'rgba(244, 67, 54, 0.8)',   // Rojo - Notificaciones
                    'rgba(0, 188, 212, 0.8)',   // Cyan - DEHU
                    'rgba(255, 235, 59, 0.8)',  // Amarillo - RLC
                    'rgba(121, 85, 72, 0.8)',   // Marrón - RNT
                ],
                borderColor: [
                    'rgba(76, 175, 80, 1)',
                    'rgba(33, 150, 243, 1)',
                    'rgba(255, 152, 0, 1)',
                    'rgba(156, 39, 176, 1)',
                    'rgba(244, 67, 54, 1)',
                    'rgba(0, 188, 212, 1)',
                    'rgba(255, 235, 59, 1)',
                    'rgba(121, 85, 72, 1)',
                ],
                borderWidth: 2,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'right',
                labels: {
                    padding: 15,
                    font: {
                        size: 12,
                    },
                    generateLabels: (chart) => {
                        const data = chart.data;
                        if (data.labels.length && data.datasets.length) {
                            return data.labels.map((label, i) => {
                                const value = data.datasets[0].data[i];
                                const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);

                                return {
                                    text: `${label}: ${value} (${percentage}%)`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    hidden: false,
                                    index: i,
                                };
                            });
                        }
                        return [];
                    },
                },
            },
            tooltip: {
                callbacks: {
                    label: function (context) {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${label}: ${value} documentos (${percentage}%)`;
                    },
                },
            },
        },
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-800">
                📊 Documentos por Categoría
            </h3>
            <div style={{ height: '300px' }}>
                <Pie data={chartData} options={options} />
            </div>
        </div>
    );
};

export default DocumentosPieChart;
