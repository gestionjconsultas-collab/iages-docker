import React, { useState } from 'react';
import { Download } from 'lucide-react';

const ExportButton = ({ tipo, label, className = '' }) => {
    const [loading, setLoading] = useState(false);

    const handleExport = async () => {
        try {
            setLoading(true);

            const response = await fetch(`/api/export/${tipo}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Error al exportar');
            }

            // Obtener el blob
            const blob = await response.blob();

            // Crear URL temporal
            const url = window.URL.createObjectURL(blob);

            // Crear elemento <a> temporal
            const a = document.createElement('a');
            a.href = url;
            a.download = `${tipo}_${new Date().toISOString().split('T')[0]}.xlsx`;

            // Hacer click y limpiar
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

        } catch (error) {
            console.error('Error exportando:', error);
            alert('Error al exportar datos');
        } finally {
            setLoading(false);
        }
    };

    return (
        <button
            onClick={handleExport}
            disabled={loading}
            className={`
        inline-flex items-center gap-2 px-4 py-2 
        bg-green-600 hover:bg-green-700 
        text-white font-medium rounded-lg
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
        >
            <Download size={18} />
            {loading ? 'Exportando...' : label || 'Exportar a Excel'}
        </button>
    );
};

export default ExportButton;
