import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Check, TrendingUp, ShieldCheck, Zap, Mail, Globe, Lock } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ChangePlanModal({ gestoria, onClose, onSave }) {
    const [planes, setPlanes] = useState([]);
    const [selectedPlanId, setSelectedPlanId] = useState(gestoria.plan_actual?.plan_id || null);
    const [loading, setLoading] = useState(false);
    const [loadingPlanes, setLoadingPlanes] = useState(true);

    useEffect(() => {
        cargarPlanes();
    }, []);

    const cargarPlanes = async () => {
        try {
            const response = await axios.get('/api/super-admin/planes');
            if (response.data.success) {
                // Ordenar planes por ID o precio para consistencia
                const sortedPlanes = response.data.planes.sort((a, b) => a.precio_mensual - b.precio_mensual);
                setPlanes(sortedPlanes);
            }
        } catch (error) {
            console.error('Error cargando planes:', error);
            toast.error('Error al cargar planes');
        } finally {
            setLoadingPlanes(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!selectedPlanId) {
            toast.error('Selecciona un plan');
            return;
        }

        if (selectedPlanId === gestoria.plan_actual?.plan_id) {
            toast.error('El plan seleccionado es el mismo que el actual');
            return;
        }

        setLoading(true);

        try {
            const response = await axios.post(
                `/api/super-admin/gestorias/${gestoria.id}/cambiar-plan`,
                { plan_id: selectedPlanId }
            );

            if (response.data.success) {
                toast.success(response.data.message || 'Plan cambiado correctamente');
                onSave();
            }
        } catch (error) {
            console.error('Error cambiando plan:', error);
            toast.error(error.response?.data?.error || 'Error al cambiar plan');
        } finally {
            setLoading(false);
        }
    };

    if (loadingPlanes) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-xl p-8 shadow-2xl">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-black bg-opacity-60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gray-50/50">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Cambiar Plan de Suscripción</h2>
                        <p className="text-sm text-gray-500 mt-1">
                            Gestoría: <span className="font-semibold text-blue-600">{gestoria.nombre}</span>
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-200 rounded-full transition-colors"
                    >
                        <X className="w-6 h-6 text-gray-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {/* Plan Actual Info */}
                    {gestoria.plan_actual && (
                        <div className="mb-8 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="p-3 bg-white rounded-lg shadow-sm">
                                    <ShieldCheck className="w-6 h-6 text-blue-600" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-blue-600 uppercase tracking-wider">Plan Actual</p>
                                    <h3 className="text-lg font-bold text-gray-900 capitalize">{gestoria.plan_actual.plan.nombre}</h3>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-xl font-black text-gray-900">€{gestoria.plan_actual.plan.precio_mensual}</p>
                                <p className="text-xs text-gray-500">al mes</p>
                            </div>
                        </div>
                    )}

                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4">Selecciona un nuevo plan</h3>

                    {/* Planes Grid */}
                    <div className="grid grid-cols-1 gap-4">
                        {planes.map((plan) => {
                            const isCurrent = plan.id === gestoria.plan_actual?.plan_id;
                            const isSelected = selectedPlanId === plan.id;

                            return (
                                <div
                                    key={plan.id}
                                    onClick={() => !isCurrent && setSelectedPlanId(plan.id)}
                                    className={`relative p-5 border-2 rounded-2xl transition-all duration-200 cursor-pointer ${isCurrent
                                            ? 'border-gray-100 bg-gray-50 cursor-not-allowed opacity-75'
                                            : isSelected
                                                ? 'border-blue-500 bg-blue-50/30 ring-4 ring-blue-50 shadow-lg'
                                                : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                                        }`}
                                >
                                    {/* Selected Badge */}
                                    {isSelected && !isCurrent && (
                                        <div className="absolute -top-2 -right-2 bg-blue-600 text-white rounded-full p-1 shadow-lg ring-4 ring-white">
                                            <Check className="w-4 h-4" />
                                        </div>
                                    )}

                                    {/* Header Plan */}
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <h4 className="text-xl font-black text-gray-900 capitalize">{plan.nombre}</h4>
                                                {isCurrent && (
                                                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded uppercase">Actual</span>
                                                )}
                                            </div>
                                            <p className="text-sm text-gray-500 mt-1">{plan.descripcion}</p>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <div className="flex items-baseline justify-end gap-1">
                                                <span className="text-2xl font-black text-gray-900">€{plan.precio_mensual}</span>
                                                <span className="text-sm text-gray-500">/mes</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Límites Grid */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-4 border-b border-gray-100">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-gray-400 uppercase mb-1">Usuarios</span>
                                            <div className="flex items-center gap-1.5 font-bold text-gray-700">
                                                <TrendingUp className="w-3.5 h-3.5 text-gray-400" />
                                                {plan.max_usuarios || '∞'}
                                            </div>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-gray-400 uppercase mb-1">Empresas</span>
                                            <div className="flex items-center gap-1.5 font-bold text-gray-700">
                                                <Globe className="w-3.5 h-3.5 text-gray-400" />
                                                {plan.max_empresas || '∞'}
                                            </div>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-gray-400 uppercase mb-1">Certificados</span>
                                            <div className="flex items-center gap-1.5 font-bold text-blue-600">
                                                <ShieldCheck className="w-3.5 h-3.5" />
                                                {plan.max_certificados || plan.certificados_max || 0}
                                            </div>
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-bold text-gray-400 uppercase mb-1">IA Mensual</span>
                                            <div className="flex items-center gap-1.5 font-bold text-purple-600">
                                                <Zap className="w-3.5 h-3.5" />
                                                {(plan.max_tokens_mes / 1000).toFixed(0)}K
                                            </div>
                                        </div>
                                    </div>

                                    {/* Features */}
                                    <div className="flex flex-wrap gap-x-6 gap-y-2 mt-4">
                                        <div className="flex items-center gap-2 text-xs font-medium text-gray-600">
                                            <Check className="w-3.5 h-3.5 text-green-500" />
                                            Soporte: <span className="text-gray-900 capitalize">{plan.soporte_nivel}</span>
                                        </div>

                                        <div className={`flex items-center gap-2 text-xs font-medium ${plan.features?.smtp_personalizado ? 'text-gray-600' : 'text-gray-400'}`}>
                                            {plan.features?.smtp_personalizado ? (
                                                <Check className="w-3.5 h-3.5 text-green-500" />
                                            ) : (
                                                <X className="w-3.5 h-3.5 text-gray-300" />
                                            )}
                                            <Mail className="w-3.5 h-3.5 opacity-50" />
                                            SMTP Personalizado
                                        </div>

                                        <div className={`flex items-center gap-2 text-xs font-medium ${plan.features?.api_access ? 'text-gray-600' : 'text-gray-400'}`}>
                                            {plan.features?.api_access ? (
                                                <Check className="w-3.5 h-3.5 text-green-500" />
                                            ) : (
                                                <X className="w-3.5 h-3.5 text-gray-300" />
                                            )}
                                            <Lock className="w-3.5 h-3.5 opacity-50" />
                                            Acceso API
                                        </div>

                                        {plan.permite_branding && (
                                            <div className="flex items-center gap-2 text-xs font-medium text-gray-600">
                                                <Check className="w-3.5 h-3.5 text-green-500" />
                                                Branding Propio
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-6 py-2.5 text-gray-600 font-bold hover:bg-gray-100 rounded-xl transition-all"
                        disabled={loading}
                    >
                        Cancelar
                    </button>
                    <button
                        type="button"
                        onClick={handleSubmit}
                        className={`px-8 py-2.5 text-white font-bold rounded-xl transition-all shadow-lg flex items-center gap-2 ${loading || !selectedPlanId || selectedPlanId === gestoria.plan_actual?.plan_id
                                ? 'bg-gray-400 cursor-not-allowed shadow-none'
                                : 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 hover:-translate-y-0.5 shadow-blue-200'
                            }`}
                        disabled={loading || !selectedPlanId || selectedPlanId === gestoria.plan_actual?.plan_id}
                    >
                        {loading ? (
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        ) : (
                            <Zap className="w-4 h-4" />
                        )}
                        Cambiar a Nuevo Plan
                    </button>
                </div>
            </div>
        </div>
    );
}
