import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DollarSign, Users, Briefcase, HardDrive, TrendingUp, Edit, Check, X } from 'lucide-react';
import EditPlanModal from './EditPlanModal';

export default function PlanesTable() {
    const [planes, setPlanes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingPlan, setEditingPlan] = useState(null);

    useEffect(() => {
        cargarPlanes();
    }, []);

    const cargarPlanes = async () => {
        try {
            // Usar el endpoint de facturación en lugar del antiguo
            const response = await axios.get('/api/planes');
            if (response.data.success) {
                setPlanes(response.data.planes);
            }
        } catch (error) {
            console.error('Error cargando planes:', error);
        } finally {
            setLoading(false);
        }
    };

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
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-gray-900">Gestión de Planes</h1>
                    <p className="text-gray-600 mt-2">Administra precios y límites de los planes</p>
                </div>

                {/* Tabla de Planes */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {planes.map((plan) => (
                        <PlanCard
                            key={plan.id}
                            plan={plan}
                            onEdit={() => setEditingPlan(plan)}
                        />
                    ))}
                </div>

                {/* Modal de Edición */}
                {editingPlan && (
                    <EditPlanModal
                        plan={editingPlan}
                        onClose={() => setEditingPlan(null)}
                        onSave={() => {
                            setEditingPlan(null);
                            cargarPlanes();
                        }}
                    />
                )}
            </div>
        </div>
    );
}

function PlanCard({ plan, onEdit }) {
    const getPlanColor = (codigo) => {
        switch (codigo) {
            case 'enterprise':
                return 'from-purple-500 to-purple-700';
            case 'profesional':
                return 'from-orange-500 to-orange-700';
            case 'basico':
            default:
                return 'from-blue-500 to-blue-700';
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition">
            {/* Header con gradiente */}
            <div className={`bg-gradient-to-r ${getPlanColor(plan.codigo)} p-6 text-white`}>
                <h3 className="text-2xl font-bold capitalize">{plan.nombre}</h3>
                <p className="text-sm opacity-90 mt-1">{plan.descripcion}</p>
                <div className="mt-4">
                    <div className="flex items-baseline">
                        <span className="text-4xl font-bold">€{plan.precio_mensual}</span>
                        <span className="ml-2 text-lg opacity-90">/mes</span>
                    </div>
                </div>
            </div>

            {/* Límites */}
            <div className="p-6">
                <div className="space-y-3">
                    <LimitItem
                        icon={<Users className="w-5 h-5" />}
                        label="Usuarios"
                        value={plan.max_usuarios || '∞'}
                    />
                    <LimitItem
                        icon={<Briefcase className="w-5 h-5" />}
                        label="Empresas"
                        value={plan.max_empresas || '∞'}
                    />
                    <LimitItem
                        icon={<Briefcase className="w-5 h-5" />}
                        label="Certificados Máx en Conecta."
                        value={plan.max_certificados === -1 || plan.max_certificados === null ? 'Ilimitado' : plan.max_certificados}
                    />
                    <LimitItem
                        icon={<HardDrive className="w-5 h-5" />}
                        label="Almacenamiento"
                        value={`${plan.max_storage_gb} GB`}
                    />
                    <LimitItem
                        icon={<TrendingUp className="w-5 h-5" />}
                        label="Tokens IA/mes"
                        value={(plan.max_tokens_mes / 1000).toFixed(0) + 'K'}
                    />
                </div>

                {/* Características */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="space-y-2">
                        {plan.features?.smtp_personalizado && (
                            <FeatureItem
                                icon={<Check className="w-4 h-4 text-green-600" />}
                                text="SMTP personalizado"
                            />
                        )}
                        {plan.features?.api_access && (
                            <FeatureItem
                                icon={<Check className="w-4 h-4 text-green-600" />}
                                text="Acceso API"
                            />
                        )}
                        {!plan.features?.smtp_personalizado && (
                            <FeatureItem
                                icon={<X className="w-4 h-4 text-gray-400" />}
                                text="Sin SMTP personalizado"
                            />
                        )}
                    </div>
                </div>

                {/* Botón Editar */}
                <button
                    onClick={onEdit}
                    className="mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition flex items-center justify-center gap-2"
                >
                    <Edit className="w-4 h-4" />
                    Editar Plan
                </button>
            </div>
        </div>
    );
}

function LimitItem({ icon, label, value }) {
    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
                <div className="text-gray-400">{icon}</div>
                <span className="text-sm text-gray-600">{label}:</span>
            </div>
            <span className="font-semibold text-gray-900">{value}</span>
        </div>
    );
}

function FeatureItem({ icon, text }) {
    return (
        <div className="flex items-center gap-2">
            {icon}
            <span className="text-sm text-gray-700">{text}</span>
        </div>
    );
}
