// frontend/src/components/AlertasVencimientoWidget.jsx
import React from 'react';
import { AlertTriangle, Clock } from 'lucide-react';

export default function AlertasVencimientoWidget({ alertas, onFiltrarUrgentes }) {
    if (!alertas) return null;

    const { criticas_count, advertencias_count } = alertas;
    const hayAlertas = criticas_count > 0 || advertencias_count > 0;

    if (!hayAlertas) return null;

    return (
        <div className="mb-4 bg-gradient-to-r from-red-50 via-orange-50 to-yellow-50 border border-red-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    {/* Críticas */}
                    {criticas_count > 0 && (
                        <div className="flex items-center gap-2">
                            <div className="p-2 bg-red-100 rounded-full">
                                <AlertTriangle className="w-5 h-5 text-red-600" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-red-900">
                                    {criticas_count} {criticas_count === 1 ? 'Crítica' : 'Críticas'}
                                </p>
                                <p className="text-xs text-red-700">Vencen en ≤3 días</p>
                            </div>
                        </div>
                    )}

                    {/* Advertencias */}
                    {advertencias_count > 0 && (
                        <div className="flex items-center gap-2">
                            <div className="p-2 bg-yellow-100 rounded-full">
                                <Clock className="w-5 h-5 text-yellow-600" />
                            </div>
                            <div>
                                <p className="text-sm font-bold text-yellow-900">
                                    {advertencias_count} {advertencias_count === 1 ? 'Advertencia' : 'Advertencias'}
                                </p>
                                <p className="text-xs text-yellow-700">Vencen en 4-7 días</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Botón filtrar urgentes */}
                <button
                    onClick={onFiltrarUrgentes}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium flex items-center gap-2"
                >
                    <AlertTriangle className="w-4 h-4" />
                    Ver Urgentes
                </button>
            </div>
        </div>
    );
}
