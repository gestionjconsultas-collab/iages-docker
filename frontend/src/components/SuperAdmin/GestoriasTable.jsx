import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Building, Users, Briefcase, TrendingUp, Edit, Eye, AlertCircle, Plus, Shield } from 'lucide-react';
import CreateGestoriaModal from './CreateGestoriaModal';
import toast from 'react-hot-toast';

export default function GestoriasTable() {
    const [gestorias, setGestorias] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filtro, setFiltro] = useState('todas'); // todas, activas, inactivas
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [solicitudesPendientes, setSolicitudesPendientes] = useState({});

    const solicitarAcceso = async (gestoriaId, gestoriaNombre) => {
        setSolicitudesPendientes(prev => ({ ...prev, [gestoriaId]: 'solicitando' }));
        try {
            await axios.post(`/api/impersonacion/solicitar/${gestoriaId}`, {}, { withCredentials: true });
            setSolicitudesPendientes(prev => ({ ...prev, [gestoriaId]: 'esperando' }));
            toast.success(`Solicitud enviada a ${gestoriaNombre}. Esperando respuesta del admin...`);
        } catch {
            setSolicitudesPendientes(prev => { const n = { ...prev }; delete n[gestoriaId]; return n; });
            toast.error('Error al enviar la solicitud');
        }
    };

    useEffect(() => {
        cargarGestorias();
    }, []);

    const cargarGestorias = async () => {
        try {
            const response = await axios.get('/api/super-admin/gestorias');
            if (response.data.success) {
                setGestorias(response.data.gestorias);
            }
        } catch (error) {
            console.error('Error cargando gestorías:', error);
        } finally {
            setLoading(false);
        }
    };

    const gestoriasFiltradas = gestorias.filter(g => {
        if (filtro === 'activas') return g.activa;
        if (filtro === 'inactivas') return !g.activa;
        return true;
    });

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Gestión de Gestorías</h1>
                        <p className="text-gray-600 mt-2">Administra todas las gestorías del sistema</p>
                    </div>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0"
                    >
                        <Plus className="w-5 h-5" />
                        Nueva Gestoría
                    </button>
                </div>

                {/* Filtros */}
                <div className="bg-white rounded-lg shadow p-4 mb-6">
                    <div className="flex gap-2">
                        <button
                            onClick={() => setFiltro('todas')}
                            className={`px-4 py-2 rounded-lg font-medium transition ${filtro === 'todas'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Todas ({gestorias.length})
                        </button>
                        <button
                            onClick={() => setFiltro('activas')}
                            className={`px-4 py-2 rounded-lg font-medium transition ${filtro === 'activas'
                                ? 'bg-green-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Activas ({gestorias.filter(g => g.activa).length})
                        </button>
                        <button
                            onClick={() => setFiltro('inactivas')}
                            className={`px-4 py-2 rounded-lg font-medium transition ${filtro === 'inactivas'
                                ? 'bg-gray-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                }`}
                        >
                            Inactivas ({gestorias.filter(g => !g.activa).length})
                        </button>
                    </div>
                </div>

                {/* Tabla */}
                <div className="bg-white rounded-lg shadow overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Gestoría
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Plan
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Usuarios
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Empresas
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Uso IA
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Certificados
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Estado
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Acciones
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {gestoriasFiltradas.map((g) => (
                                    <tr key={g.id} className="hover:bg-gray-50 transition">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                                                    <Building className="h-5 w-5 text-blue-600" />
                                                </div>
                                                <div className="ml-4">
                                                    <div className="text-sm font-medium text-gray-900">{g.nombre}</div>
                                                    <div className="text-sm text-gray-500">ID: {g.id}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${g.plan === 'enterprise' ? 'bg-purple-100 text-purple-800' :
                                                g.plan === 'premium' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-gray-100 text-gray-800'
                                                }`}>
                                                {g.plan || 'básico'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <UsageBar
                                                current={g.usuarios.actuales}
                                                max={g.usuarios.max}
                                                icon={<Users className="w-4 h-4" />}
                                            />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <UsageBar
                                                current={g.empresas.actuales}
                                                max={g.empresas.max}
                                                icon={<Briefcase className="w-4 h-4" />}
                                            />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {g.tokens_ia ? (
                                                <UsageBar
                                                    current={g.tokens_ia.usados}
                                                    max={g.tokens_ia.max}
                                                    icon={<TrendingUp className="w-4 h-4" />}
                                                    showNumbers={false}
                                                />
                                            ) : (
                                                <span className="text-sm text-gray-400">N/A</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                <Briefcase className="w-4 h-4 text-gray-400" />
                                                <span className="text-sm text-gray-600 font-medium">
                                                    {g.certificados?.max === -1 || g.certificados?.max === null ? 'Ilimitado' : g.certificados?.max}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${g.activa
                                                ? 'bg-green-100 text-green-800'
                                                : 'bg-red-100 text-red-800'
                                                }`}>
                                                {g.activa ? 'Activa' : 'Inactiva'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => solicitarAcceso(g.id, g.nombre)}
                                                    disabled={!!solicitudesPendientes[g.id]}
                                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                                                        solicitudesPendientes[g.id] === 'esperando'
                                                            ? 'bg-amber-100 text-amber-700 cursor-wait'
                                                            : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                                    }`}
                                                    title="Solicitar acceso temporal a esta gestoría"
                                                >
                                                    <Shield className="w-3.5 h-3.5" />
                                                    {solicitudesPendientes[g.id] === 'esperando' ? 'Esperando...' : 'Acceder'}
                                                </button>
                                                <button
                                                    onClick={() => window.location.href = `/super-admin/gestorias/${g.id}`}
                                                    className="text-blue-600 hover:text-blue-900 p-1 hover:bg-blue-50 rounded transition"
                                                    title="Ver detalle"
                                                >
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => window.location.href = `/super-admin/gestorias/${g.id}`}
                                                    className="text-gray-600 hover:text-gray-900 p-1 hover:bg-gray-50 rounded transition"
                                                    title="Editar"
                                                >
                                                    <Edit className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {gestoriasFiltradas.length === 0 && (
                        <div className="text-center py-12">
                            <AlertCircle className="mx-auto h-12 w-12 text-gray-400" />
                            <h3 className="mt-2 text-sm font-medium text-gray-900">No hay gestorías</h3>
                            <p className="mt-1 text-sm text-gray-500">
                                No se encontraron gestorías con los filtros seleccionados.
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Modals */}
            {showCreateModal && (
                <CreateGestoriaModal
                    onClose={() => setShowCreateModal(false)}
                    onSave={() => {
                        setShowCreateModal(false);
                        cargarGestorias();
                    }}
                />
            )}
        </div>
    );
}

function UsageBar({ current, max, icon, showNumbers = true }) {
    const percentage = max > 0 ? (current / max) * 100 : 0;

    const getColor = () => {
        if (percentage >= 90) return 'bg-red-500';
        if (percentage >= 80) return 'bg-yellow-500';
        if (percentage >= 50) return 'bg-blue-500';
        return 'bg-green-500';
    };

    return (
        <div className="flex items-center gap-2">
            <div className="text-gray-400">{icon}</div>
            <div className="flex-1 min-w-[80px]">
                <div className="flex justify-between text-xs text-gray-600 mb-1">
                    {showNumbers && (
                        <>
                            <span>{current}</span>
                            <span className="text-gray-400">/ {max}</span>
                        </>
                    )}
                    {!showNumbers && (
                        <span className="text-gray-500">{percentage.toFixed(0)}%</span>
                    )}
                </div>
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full transition-all ${getColor()}`}
                        style={{ width: `${Math.min(percentage, 100)}%` }}
                    />
                </div>
            </div>
        </div>
    );
}
