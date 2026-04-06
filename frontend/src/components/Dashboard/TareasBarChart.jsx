import React from 'react';
import { Bar } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js';

// Registrar componentes de Chart.js
ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
);

const TareasBarChart = ({ data }) => {
    if (!data || data.length === 0) {
        return (
            <div className="text-center text-gray-500 py-8">
                No hay datos disponibles
            </div>
        );
    }

    // Mapear estados a labels legibles
    const estadoLabels = {
        'pendiente': 'Pendientes',
        'en_progreso': 'En Progreso',
        'completada': 'Completadas',
        'cancelada': 'Canceladas',
    };

    // Colores por estado
    const estadoColors = {
        'pendiente': 'rgba(255, 152, 0, 0.8)',      // Naranja
        'en_progreso': 'rgba(33, 150, 243, 0.8)',   // Azul
        'completada': 'rgba(76, 175, 80, 0.8)',     // Verde
        'cancelada': 'rgba(158, 158, 158, 0.8)',    // Gris
    };

    const estadoBorders = {
        'pendiente': 'rgba(255, 152, 0, 1)',
        'en_progreso': 'rgba(33, 150, 243, 1)',
        'completada': 'rgba(76, 175, 80, 1)',
        'cancelada': 'rgba(158, 158, 158, 1)',
    };

    const chartData = {
        labels: data.map(item => estadoLabels[item.estado] || item.estado),
        datasets: [
            {
                label: 'Tareas',
                data: data.map(item => item.total),
                backgroundColor: data.map(item => estadoColors[item.estado] || 'rgba(158, 158, 158, 0.8)'),
                borderColor: data.map(item => estadoBorders[item.estado] || 'rgba(158, 158, 158, 1)'),
                borderWidth: 2,
                borderRadius: 8,
                borderSkipped: false,
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false,
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
                        return `Total: ${context.parsed.y} tareas`;
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
                        size: 12,
                        weight: 'bold',
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
                📋 Tareas por Estado
            </h3>
            <div style={{ height: '300px' }}>
                <Bar data={chartData} options={options} />
            </div>
        </div>
    );
};

export default TareasBarChart;
