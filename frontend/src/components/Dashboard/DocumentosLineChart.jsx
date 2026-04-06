import React from 'react';
import { Line } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
} from 'chart.js';

// Registrar componentes de Chart.js
ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

const DocumentosLineChart = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-gray-500 py-8">
                No hay datos disponibles
            </div>
        );
    }

    // Ordenar por mes
    const sortedData = [...data].sort((a, b) => a.mes.localeCompare(b.mes));

    // Formatear mes (2025-06 -> Jun 2025)
    const formatMes = (mes) => {
        const [year, month] = mes.split('-');
        const meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
            'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
        return `${meses[parseInt(month) - 1]} ${year}`;
    };

    const chartData = {
        labels: sortedData.map(item => formatMes(item.mes)),
        datasets: [
            {
                label: 'Documentos Procesados',
                data: sortedData.map(item => item.total),
                borderColor: 'rgba(33, 150, 243, 1)',
                backgroundColor: 'rgba(33, 150, 243, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: 'rgba(33, 150, 243, 1)',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    font: {
                        size: 12,
                    },
                    padding: 15,
                },
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleFont: {
                    size: 14,
                },
                bodyFont: {
                    size: 13,
                },
                callbacks: {
                    label: function (context) {
                        return `Documentos: ${context.parsed.y}`;
                    },
                },
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0,
                    font: {
                        size: 11,
                    },
                },
                grid: {
                    color: 'rgba(0, 0, 0, 0.05)',
                },
            },
            x: {
                ticks: {
                    font: {
                        size: 11,
                    },
                },
                grid: {
                    display: false,
                },
            },
        },
    };

    return (
        <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-800">
                📈 Tendencia de Documentos (Últimos 6 Meses)
            </h3>
            <div style={{ height: '300px' }}>
                <Line data={chartData} options={options} />
            </div>
        </div>
    );
};

export default DocumentosLineChart;
