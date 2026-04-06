// frontend/src/components/UsageStats.jsx
import React from 'react';
import { Users, Building2, HardDrive, Zap, Mail, FileText } from 'lucide-react';

const UsageStats = ({ uso, suscripcion }) => {
    if (!uso || !suscripcion) {
        return (
            <div className="text-center py-12">
                <p className="text-gray-600">Cargando estadísticas de uso...</p>
            </div>
        );
    }

    const plan = suscripcion.plan;
    const limites = uso.limites || {};

    const recursos = [
        {
            icon: Users,
            label: 'Usuarios Activos',
            valor: limites.usuarios?.uso || 0,
            limite: limites.usuarios?.limite,
            porcentaje: limites.usuarios?.porcentaje || 0,
            color: 'blue'
        },
        {
            icon: Building2,
            label: 'Empresas',
            valor: limites.empresas?.uso || 0,
            limite: limites.empresas?.limite,
            porcentaje: limites.empresas?.porcentaje || 0,
            color: 'green'
        },
        {
            icon: HardDrive,
            label: 'Almacenamiento',
            valor: limites.storage?.uso || 0,
            limite: limites.storage?.limite,
            porcentaje: limites.storage?.porcentaje || 0,
            unidad: 'GB',
            color: 'purple'
        },
        {
            icon: Zap,
            label: 'Tokens IA',
            valor: uso.uso?.tokens_usados || 0,
            limite: plan.max_tokens_mes,
            porcentaje: ((uso.uso?.tokens_usados || 0) / plan.max_tokens_mes * 100),
            formato: (val) => `${(val / 1000).toFixed(0)}K`,
            color: 'orange'
        },
        {
            icon: FileText,
            label: 'Documentos Procesados',
            valor: uso.uso?.documentos_procesados || 0,
            limite: null,
            color: 'indigo'
        },
        {
            icon: Mail,
            label: 'Emails Enviados',
            valor: uso.uso?.emails_enviados || 0,
            limite: null,
            color: 'pink'
        }
    ];

    const getProgressColor = (porcentaje) => {
        if (porcentaje >= 90) return 'red';
        if (porcentaje >= 75) return 'yellow';
        return 'green';
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Uso del Mes Actual
                </h3>
                <p className="text-sm text-gray-600">
                    Período: {new Date().toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })}
                </p>
            </div>

            {/* Recursos */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {recursos.map((recurso, index) => {
                    const Icon = recurso.icon;
                    const porcentaje = recurso.porcentaje || 0;
                    const progressColor = getProgressColor(porcentaje);

                    return (
                        <div
                            key={index}
                            className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow"
                        >
                            {/* Icon y Label */}
                            <div className="flex items-center justify-between mb-4">
                                <div className={`w-10 h-10 rounded-lg bg-${recurso.color}-100 flex items-center justify-center`}>
                                    <Icon className={`w-5 h-5 text-${recurso.color}-600`} />
                                </div>
                                {recurso.limite && (
                                    <span className={`
                    text-xs font-medium px-2 py-1 rounded-full
                    ${porcentaje >= 90
                                            ? 'bg-red-100 text-red-700'
                                            : porcentaje >= 75
                                                ? 'bg-yellow-100 text-yellow-700'
                                                : 'bg-green-100 text-green-700'
                                        }
                  `}>
                                        {porcentaje.toFixed(0)}%
                                    </span>
                                )}
                            </div>

                            {/* Label */}
                            <div className="text-sm text-gray-600 mb-2">{recurso.label}</div>

                            {/* Valor */}
                            <div className="flex items-baseline gap-2 mb-3">
                                <span className="text-2xl font-bold text-gray-900">
                                    {recurso.formato ? recurso.formato(recurso.valor) : recurso.valor}
                                    {recurso.unidad && ` ${recurso.unidad}`}
                                </span>
                                {recurso.limite && (
                                    <span className="text-sm text-gray-500">
                                        / {recurso.formato ? recurso.formato(recurso.limite) : recurso.limite}
                                        {recurso.unidad && ` ${recurso.unidad}`}
                                    </span>
                                )}
                            </div>

                            {/* Progress Bar */}
                            {recurso.limite && (
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full transition-all bg-${progressColor}-500`}
                                        style={{ width: `${Math.min(porcentaje, 100)}%` }}
                                    />
                                </div>
                            )}

                            {/* Advertencia */}
                            {recurso.limite && porcentaje >= 90 && (
                                <div className="mt-3 text-xs text-red-600 font-medium">
                                    ⚠️ Cerca del límite
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Costos de IA */}
            {uso.uso && (
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 border border-orange-200 rounded-lg p-6">
                    <h4 className="font-semibold text-orange-900 mb-4">💰 Costos de IA</h4>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <div className="text-sm text-orange-700 mb-1">Costo IA</div>
                            <div className="text-2xl font-bold text-orange-900">
                                €{uso.uso.costo_ia || '0.00'}
                            </div>
                        </div>
                        <div>
                            <div className="text-sm text-orange-700 mb-1">Costo Storage</div>
                            <div className="text-2xl font-bold text-orange-900">
                                €{uso.uso.costo_storage || '0.00'}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Recomendación */}
            {limites.empresas?.porcentaje >= 80 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h4 className="font-semibold text-blue-900 mb-2">💡 Recomendación</h4>
                    <p className="text-sm text-blue-700">
                        Estás usando el {limites.empresas.porcentaje.toFixed(0)}% de tu límite de empresas.
                        Considera actualizar a un plan superior para tener más capacidad.
                    </p>
                </div>
            )}
        </div>
    );
};

export default UsageStats;
