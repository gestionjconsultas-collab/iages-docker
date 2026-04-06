// frontend/src/components/ProductividadView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
    Clock, Users, BarChart3, Calendar
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ProductividadView() {
    const [estadisticas, setEstadisticas] = useState(null);
    const [tareasVencidas, setTareasVencidas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [usuarioSeleccionado, setUsuarioSeleccionado] = useState(null);

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const [statsRes, vencidasRes] = await Promise.all([
                axios.get('/api/tareas/estadisticas', { withCredentials: true }),
                axios.get('/api/tareas/vencidas', { withCredentials: true })
            ]);

            if (statsRes.data.success) {
                setEstadisticas(statsRes.data.estadisticas);
            }

            if (vencidasRes.data.success) {
                setTareasVencidas(vencidasRes.data.tareas_vencidas);
            }
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error al cargar estadísticas');
        } finally {
            setLoading(false);
        }
    };

    const marcarComoCompletada = async (tareaId) => {
        try {
            await axios.put(`/api/tareas/${tareaId}`, {
                estado: 'completada',
                fecha_completada: new Date().toISOString()
            }, { withCredentials: true });

            toast.success('Tarea marcada como completada');
            cargarDatos();
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al actualizar tarea');
        }
    };

    const getIndicadorColor = (tasa) => {
        if (tasa >= 80) return 'text-green-600 bg-green-50';
        if (tasa >= 50) return 'text-yellow-600 bg-yellow-50';
        return 'text-red-600 bg-red-50';
    };

    const getIndicadorEmoji = (tasa) => {
        if (tasa >= 80) return '🟢';
        if (tasa >= 50) return '🟡';
        return '🔴';
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    if (!estadisticas) {
        return <div className="p-6">Error cargando datos</div>;
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-2">
                    <BarChart3 className="w-8 h-8 text-primary" />
                    <h1 className="text-2xl font-bold text-gray-800">Productividad de Tareas</h1>
                </div>
                <p className="text-gray-600">Seguimiento y estadísticas de completitud de tareas</p>
            </div>

            {/* Tarjetas de Resumen */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Tareas */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Total Tareas</p>
                            <p className="text-3xl font-bold text-gray-900 mt-2">{estadisticas.total_tareas}</p>
                        </div>
                        <div className="p-3 bg-blue-50 rounded-lg">
                            <Calendar className="w-6 h-6 text-blue-600" />
                        </div>
                    </div>
                </div>

                {/* Tasa de Completitud */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Tasa de Completitud</p>
                            <p className="text-3xl font-bold text-green-600 mt-2">{estadisticas.tasa_completitud}%</p>
                        </div>
                        <div className="p-3 bg-green-50 rounded-lg">
                            <CheckCircle className="w-6 h-6 text-green-600" />
                        </div>
                    </div>
                    <div className="mt-3 flex items-center text-sm">
                        <span className="text-gray-600">{estadisticas.completadas} de {estadisticas.total_tareas} completadas</span>
                    </div>
                </div>

                {/* Tareas Vencidas */}
                <div className={`bg-white rounded-lg shadow-sm p-6 border ${estadisticas.vencidas > 0 ? 'border-red-200' : 'border-gray-100'}`}>
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Tareas Vencidas</p>
                            <p className={`text-3xl font-bold mt-2 ${estadisticas.vencidas > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                {estadisticas.vencidas}
                            </p>
                        </div>
                        <div className={`p-3 rounded-lg ${estadisticas.vencidas > 0 ? 'bg-red-50' : 'bg-gray-50'}`}>
                            <AlertTriangle className={`w-6 h-6 ${estadisticas.vencidas > 0 ? 'text-red-600' : 'text-gray-400'}`} />
                        </div>
                    </div>
                </div>

                {/* Promedio Días */}
                <div className="bg-white rounded-lg shadow-sm p-6 border border-gray-100">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-600">Promedio Días</p>
                            <p className="text-3xl font-bold text-gray-900 mt-2">{estadisticas.promedio_dias_completar}</p>
                        </div>
                        <div className="p-3 bg-purple-50 rounded-lg">
                            <Clock className="w-6 h-6 text-purple-600" />
                        </div>
                    </div>
                    <div className="mt-3 flex items-center text-sm text-gray-600">
                        Para completar tareas
                    </div>
                </div>
            </div>

            {/* Tabla de Usuarios */}
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center gap-2">
                        <Users className="w-5 h-5 text-gray-600" />
                        <h2 className="text-lg font-semibold text-gray-900">Productividad por Usuario</h2>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Usuario
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Total Tareas
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Completadas
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Vencidas
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Tasa Completitud
                                </th>
                                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Estado
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {estadisticas.por_usuario.map((usuario) => (
                                <tr key={usuario.usuario_id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="text-sm font-medium text-gray-900">{usuario.nombre}</div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className="text-sm text-gray-900">{usuario.total}</span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className="text-sm text-green-600 font-medium">{usuario.completadas}</span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className={`text-sm font-medium ${usuario.vencidas > 0 ? 'text-red-600' : 'text-gray-400'}`}>
                                            {usuario.vencidas}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getIndicadorColor(usuario.tasa_completitud)}`}>
                                            {usuario.tasa_completitud.toFixed(1)}%
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                        <span className="text-2xl">{getIndicadorEmoji(usuario.tasa_completitud)}</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Lista de Tareas Vencidas */}
            {tareasVencidas.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm overflow-hidden border border-red-200">
                    <div className="px-6 py-4 bg-red-50 border-b border-red-200">
                        <div className="flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5 text-red-600" />
                            <h2 className="text-lg font-semibold text-red-900">Tareas Vencidas ({tareasVencidas.length})</h2>
                        </div>
                    </div>
                    <div className="divide-y divide-gray-200">
                        {tareasVencidas.map((tarea) => (
                            <div key={tarea.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <h3 className="text-sm font-medium text-gray-900">{tarea.titulo}</h3>
                                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${tarea.prioridad === 'alta' ? 'bg-red-100 text-red-700' :
                                                    tarea.prioridad === 'media' ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-gray-100 text-gray-700'
                                                }`}>
                                                {tarea.prioridad}
                                            </span>
                                        </div>
                                        {tarea.descripcion && (
                                            <p className="text-sm text-gray-600 mt-1">{tarea.descripcion}</p>
                                        )}
                                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                                            <span>👤 {tarea.asignado_a}</span>
                                            <span>📅 Vencida hace {tarea.dias_vencida} día(s)</span>
                                            {tarea.empresa && <span>🏢 {tarea.empresa}</span>}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => marcarComoCompletada(tarea.id)}
                                        className="ml-4 px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
                                    >
                                        Marcar Completada
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
