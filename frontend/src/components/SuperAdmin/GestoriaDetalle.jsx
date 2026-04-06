import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Building, Users, Briefcase, TrendingUp, Calendar, AlertCircle, Edit, RefreshCw } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import EditGestoriaModal from './EditGestoriaModal';
import ChangePlanModal from './ChangePlanModal';
import ConfiguracionGestoriaModal from '../ConfiguracionGestoriaModal';
import { Settings } from 'lucide-react';

export default function GestoriaDetalle() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [gestoria, setGestoria] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showEditModal, setShowEditModal] = useState(false);
    const [showChangePlanModal, setShowChangePlanModal] = useState(false);
    const [showConfigModal, setShowConfigModal] = useState(false);

    useEffect(() => {
        cargarGestoria();
    }, [id]);

    const cargarGestoria = async () => {
        try {
            const response = await axios.get(`/api/super-admin/gestorias/${id}`);
            if (response.data.success) {
                setGestoria(response.data.gestoria);
            }
        } catch (error) {
            console.error('Error cargando gestoría:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!gestoria) {
        return (
            <div className="p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-800">Gestoría no encontrada</p>
                </div>
            </div>
        );
    }

    // Preparar datos para gráficos
    const usoHistorico = gestoria.uso_historico || [];
    const chartData = usoHistorico.map(uso => ({
        periodo: uso.periodo,
        tokens_ia: uso.tokens_ia_usados,
        documentos: uso.documentos_procesados,
        usuarios: uso.usuarios_activos
    })).reverse();

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => navigate('/super-admin/gestorias')}
                            className="p-2 hover:bg-gray-200 rounded-lg transition"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">{gestoria.nombre}</h1>
                            <p className="text-gray-600">ID: {gestoria.id}</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowChangePlanModal(true)}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition flex items-center gap-2"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Cambiar Plan
                        </button>
                        <button
                            onClick={() => setShowConfigModal(true)}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition flex items-center gap-2"
                        >
                            <Settings className="w-4 h-4" />
                            Configurar Branding
                        </button>
                        <button
                            onClick={() => setShowEditModal(true)}
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center gap-2"
                        >
                            <Edit className="w-4 h-4" />
                            Editar
                        </button>
                    </div>
                </div>

                {/* Estado y Plan */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-lg font-bold mb-4">Información General</h2>
                        <div className="space-y-3">
                            <div className="flex justify-between">
                                <span className="text-gray-600">Estado:</span>
                                <span className={`px-2 py-1 rounded-full text-sm font-medium ${gestoria.activa ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }`}>
                                    {gestoria.activa ? 'Activa' : 'Inactiva'}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-600">Plan Actual:</span>
                                <span className={`px-2 py-1 rounded-full text-sm font-medium ${gestoria.plan_actual?.plan?.nombre === 'premium' ? 'bg-purple-100 text-purple-800' :
                                    gestoria.plan_actual?.plan?.nombre === 'plus' ? 'bg-blue-100 text-blue-800' :
                                        'bg-gray-100 text-gray-800'
                                    }`}>
                                    {gestoria.plan_actual?.plan?.nombre || 'Sin plan'}
                                </span>
                            </div>
                            {gestoria.plan_actual && (
                                <>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Precio:</span>
                                        <span className="font-medium">€{gestoria.plan_actual.plan.precio_mensual}/mes</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Fecha Inicio:</span>
                                        <span className="font-medium">
                                            {new Date(gestoria.plan_actual.fecha_inicio).toLocaleDateString()}
                                        </span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-lg font-bold mb-4">Límites del Plan</h2>
                        {gestoria.plan_actual?.plan && (
                            <div className="space-y-3">
                                <LimitItem
                                    label="Usuarios"
                                    current={gestoria.plan_actual.plan.max_usuarios || gestoria.plan_actual.plan.usuarios_max || '∞'}
                                    icon={<Users className="w-4 h-4" />}
                                />
                                <LimitItem
                                    label="Empresas"
                                    current={gestoria.plan_actual.plan.max_empresas || gestoria.plan_actual.plan.empresas_max || '∞'}
                                    icon={<Briefcase className="w-4 h-4" />}
                                />
                                <LimitItem
                                    label="Certificados Conecta"
                                    current={gestoria.plan_actual.plan.max_certificados === -1 || gestoria.plan_actual.plan.max_certificados === null ? '∞' : gestoria.plan_actual.plan.max_certificados}
                                    icon={<Briefcase className="w-4 h-4" />}
                                />
                                <LimitItem
                                    label="Almacenamiento"
                                    current={`${gestoria.plan_actual.plan.max_storage_gb || gestoria.plan_actual.plan.almacenamiento_gb} GB`}
                                    icon={<Building className="w-4 h-4" />}
                                />
                                <LimitItem
                                    label="Tokens IA/mes"
                                    current={((gestoria.plan_actual.plan.max_tokens_mes || gestoria.plan_actual.plan.tokens_ia_mes) / 1000).toFixed(0) + 'K'}
                                    icon={<TrendingUp className="w-4 h-4" />}
                                />
                            </div>
                        )}
                    </div>
                </div>

                {/* Gráficos de Uso Histórico */}
                {chartData.length > 0 && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                        {/* Gráfico de Tokens IA */}
                        <div className="bg-white rounded-lg shadow p-6">
                            <h2 className="text-lg font-bold mb-4">Uso de Tokens IA (Últimos 6 meses)</h2>
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="periodo" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Line type="monotone" dataKey="tokens_ia" stroke="#8b5cf6" strokeWidth={2} name="Tokens IA" />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Gráfico de Documentos */}
                        <div className="bg-white rounded-lg shadow p-6">
                            <h2 className="text-lg font-bold mb-4">Documentos Procesados (Últimos 6 meses)</h2>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="periodo" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="documentos" fill="#3b82f6" name="Documentos" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}

                {/* Alertas Recientes */}
                {gestoria.alertas_recientes && gestoria.alertas_recientes.length > 0 && (
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-yellow-600" />
                            Alertas Recientes
                        </h2>
                        <div className="space-y-2">
                            {gestoria.alertas_recientes.map((alerta) => (
                                <div
                                    key={alerta.id}
                                    className={`p-3 rounded-lg border ${alerta.nivel === 'critical' ? 'bg-red-50 border-red-200' :
                                        alerta.nivel === 'warning' ? 'bg-yellow-50 border-yellow-200' :
                                            'bg-blue-50 border-blue-200'
                                        }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="font-medium">{alerta.titulo}</p>
                                            <p className="text-sm text-gray-600">{alerta.mensaje}</p>
                                        </div>
                                        <span className="text-xs text-gray-500">
                                            {new Date(alerta.fecha_creacion).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Modales */}
            {showEditModal && (
                <EditGestoriaModal
                    gestoria={gestoria}
                    onClose={() => setShowEditModal(false)}
                    onSave={() => {
                        setShowEditModal(false);
                        cargarGestoria();
                    }}
                />
            )}

            {showChangePlanModal && (
                <ChangePlanModal
                    gestoria={gestoria}
                    onClose={() => setShowChangePlanModal(false)}
                    onSave={() => {
                        setShowChangePlanModal(false);
                        cargarGestoria();
                    }}
                />
            )}

            {showConfigModal && (
                <ConfiguracionGestoriaModal
                    gestoria={gestoria}
                    onClose={() => setShowConfigModal(false)}
                    onSave={() => {
                        setShowConfigModal(false);
                        cargarGestoria();
                    }}
                />
            )}
        </div>
    );
}

function LimitItem({ label, current, icon }) {
    return (
        <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
                <div className="text-gray-400">{icon}</div>
                <span className="text-gray-600">{label}:</span>
            </div>
            <span className="font-medium">{current}</span>
        </div>
    );
}
