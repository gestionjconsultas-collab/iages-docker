// frontend/src/components/SoporteMetricas.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, Award, Clock, Star } from 'lucide-react';

const SoporteMetricas = () => {
    const [metricas, setMetricas] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        cargarMetricas();
    }, []);

    const cargarMetricas = async () => {
        try {
            setLoading(true);
            const res = await axios.get('/api/soporte/metricas', {
                withCredentials: true
            });

            if (res.data.success) {
                setMetricas(res.data.metricas);
            }
        } catch (error) {
            console.error('Error cargando métricas:', error);
            if (window.toast) {
                window.toast.error('Error al cargar métricas');
            }
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <TrendingUp className="w-7 h-7 text-blue-600" />
                    Métricas de Soporte
                </h2>
                <p className="text-gray-600 mt-1">
                    Performance y valoraciones del equipo de soporte
                </p>
            </div>

            {metricas.length === 0 ? (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                    <Award className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">No hay métricas disponibles</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {metricas.map((metrica, index) => (
                        <div
                            key={metrica.agente_id}
                            className="bg-white rounded-xl shadow-md hover:shadow-lg transition-shadow p-6 border border-gray-200"
                        >
                            {/* Badge de posición */}
                            {index === 0 && (
                                <div className="flex justify-center mb-4">
                                    <div className="text-5xl">🏆</div>
                                </div>
                            )}

                            {/* Nombre del agente */}
                            <h3 className="font-bold text-xl text-gray-900 text-center mb-4">
                                {metrica.agente_nombre}
                            </h3>

                            {/* Métricas */}
                            <div className="space-y-3">
                                {/* Rating */}
                                <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                                        <span className="text-sm font-medium text-gray-700">Rating</span>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-bold text-lg text-gray-900">
                                            {metrica.promedio_rating.toFixed(1)} ⭐
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {metrica.total_valoraciones} valoraciones
                                        </div>
                                    </div>
                                </div>

                                {/* Tickets resueltos */}
                                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                                    <div className="flex items-center gap-2">
                                        <Award className="w-5 h-5 text-green-600" />
                                        <span className="text-sm font-medium text-gray-700">Resueltos</span>
                                    </div>
                                    <div className="font-bold text-lg text-gray-900">
                                        {metrica.tickets_resueltos}
                                    </div>
                                </div>

                                {/* Tiempo promedio */}
                                {metrica.tiempo_promedio_horas > 0 && (
                                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                                        <div className="flex items-center gap-2">
                                            <Clock className="w-5 h-5 text-blue-600" />
                                            <span className="text-sm font-medium text-gray-700">Tiempo Avg</span>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold text-lg text-gray-900">
                                                {metrica.tiempo_promedio_horas.toFixed(1)}h
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Badge de ranking */}
                            {index < 3 && (
                                <div className="mt-4 text-center">
                                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${index === 0 ? 'bg-yellow-100 text-yellow-800' :
                                            index === 1 ? 'bg-gray-100 text-gray-800' :
                                                'bg-orange-100 text-orange-800'
                                        }`}>
                                        {index === 0 ? '🥇 Top 1' : index === 1 ? '🥈 Top 2' : '🥉 Top 3'}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default SoporteMetricas;
