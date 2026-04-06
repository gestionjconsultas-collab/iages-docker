import React, { useState } from 'react';
import axios from 'axios';
import { X, Save, DollarSign, Users, Briefcase, HardDrive, TrendingUp, MessageCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function EditPlanModal({ plan, onClose, onSave }) {
    const [formData, setFormData] = useState({
        precio_mensual: plan.precio_mensual || 0,
        max_usuarios: plan.max_usuarios || 0,
        max_empresas: plan.max_empresas || 0,
        max_storage_gb: plan.max_storage_gb || 0,
        max_tokens_mes: plan.max_tokens_mes || 0,
        certificados_max: plan.max_certificados !== undefined ? plan.max_certificados : 0,
        descripcion: plan.descripcion || '',
        soporte_nivel: plan.soporte_nivel || '',
        permite_branding: plan.permite_branding || false
    });
    const [loading, setLoading] = useState(false);
    const [updatingSubs, setUpdatingSubs] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const response = await axios.put(`/api/super-admin/planes/${plan.id}`, formData);

            if (response.data.success) {
                toast.success(response.data.message || 'Plan actualizado correctamente');
                onSave();
            }
        } catch (error) {
            console.error('Error actualizando plan:', error);
            toast.error(error.response?.data?.error || 'Error al actualizar plan');
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateSubscriptions = async () => {
        if (!confirm(`¿Actualizar el precio de TODAS las suscripciones existentes del plan ${plan.nombre} a €${formData.precio_mensual}/mes?`)) {
            return;
        }

        setUpdatingSubs(true);
        try {
            const response = await axios.post(`/api/admin/planes/${plan.id}/actualizar-suscripciones`);

            if (response.data.success) {
                toast.success(`${response.data.actualizadas} suscripciones actualizadas a €${response.data.nuevo_precio}/mes`);
            }
        } catch (error) {
            console.error('Error actualizando suscripciones:', error);
            toast.error(error.response?.data?.error || 'Error al actualizar suscripciones');
        } finally {
            setUpdatingSubs(false);
        }
    };

    const handleChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 capitalize">
                            Editar Plan: {plan.nombre}
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Los cambios afectarán a todas las gestorías con este plan
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6">
                    <div className="space-y-6">
                        {/* Precio */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <div className="flex items-center gap-2">
                                    <DollarSign className="w-4 h-4" />
                                    Precio Mensual (€)
                                </div>
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={formData.precio_mensual}
                                onChange={(e) => handleChange('precio_mensual', parseFloat(e.target.value))}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                required
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Precio que se cobrará mensualmente a las gestorías
                            </p>
                        </div>

                        {/* Descripción */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Descripción
                            </label>
                            <textarea
                                value={formData.descripcion}
                                onChange={(e) => handleChange('descripcion', e.target.value)}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                rows="2"
                                placeholder="Descripción del plan..."
                            />
                        </div>

                        {/* Límites */}
                        <div className="grid grid-cols-2 gap-4">
                            {/* Usuarios */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <Users className="w-4 h-4" />
                                        Usuarios Máximos
                                    </div>
                                </label>
                                <input
                                    type="number"
                                    value={formData.max_usuarios}
                                    onChange={(e) => handleChange('max_usuarios', parseInt(e.target.value))}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    min="1"
                                />
                            </div>

                            {/* Empresas */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <Briefcase className="w-4 h-4" />
                                        Empresas Máximas
                                    </div>
                                </label>
                                <input
                                    type="number"
                                    value={formData.max_empresas}
                                    onChange={(e) => handleChange('max_empresas', parseInt(e.target.value))}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    min="1"
                                />
                            </div>

                            {/* Almacenamiento */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <HardDrive className="w-4 h-4" />
                                        Almacenamiento (GB)
                                    </div>
                                </label>
                                <input
                                    type="number"
                                    value={formData.max_storage_gb}
                                    onChange={(e) => handleChange('max_storage_gb', parseInt(e.target.value))}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    min="1"
                                />
                            </div>

                            {/* Tokens IA */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="w-4 h-4" />
                                        Tokens IA/mes
                                    </div>
                                </label>
                                <input
                                    type="number"
                                    value={formData.max_tokens_mes}
                                    onChange={(e) => handleChange('max_tokens_mes', parseInt(e.target.value))}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    min="0"
                                />
                            </div>

                            {/* Certificados */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <div className="flex items-center gap-2">
                                        <Briefcase className="w-4 h-4" />
                                        Certificados Máx.
                                    </div>
                                </label>
                                <input
                                    type="number"
                                    value={formData.certificados_max}
                                    onChange={(e) => handleChange('certificados_max', parseInt(e.target.value))}
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    required
                                    min="-1"
                                />
                                <p className="text-[10px] text-gray-500 mt-1">
                                    -1 para ilimitado
                                </p>
                            </div>
                        </div>

                        {/* Soporte */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <div className="flex items-center gap-2">
                                    <MessageCircle className="w-4 h-4" />
                                    Nivel de Soporte
                                </div>
                            </label>
                            <select
                                value={formData.soporte_nivel}
                                onChange={(e) => handleChange('soporte_nivel', e.target.value)}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="email">Email</option>
                                <option value="chat">Chat</option>
                                <option value="email + chat">Email + Chat</option>
                                <option value="24/7">24/7</option>
                            </select>
                        </div>

                        {/* Branding */}
                        <div>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.permite_branding}
                                    onChange={(e) => handleChange('permite_branding', e.target.checked)}
                                    className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="text-sm font-medium text-gray-700">
                                    Permite Branding Personalizado
                                </span>
                            </label>
                            <p className="text-xs text-gray-500 mt-1 ml-6">
                                Permite a las gestorías personalizar logo y colores
                            </p>
                        </div>

                        {/* Warning */}
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                            <p className="text-sm text-yellow-800">
                                <strong>⚠️ Importante:</strong> Los cambios se aplicarán inmediatamente a todas las gestorías que tengan este plan asignado.
                            </p>
                        </div>

                        {/* Actualizar Suscripciones Existentes */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-blue-900 mb-1">
                                        💰 Actualizar Precio de Suscripciones Existentes
                                    </p>
                                    <p className="text-xs text-blue-700">
                                        Aplica el nuevo precio (€{formData.precio_mensual}/mes) a todas las suscripciones activas de este plan.
                                        Por defecto, las suscripciones mantienen su precio original.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={handleUpdateSubscriptions}
                                    disabled={updatingSubs || loading}
                                    className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition disabled:opacity-50 whitespace-nowrap"
                                >
                                    {updatingSubs ? 'Actualizando...' : 'Aplicar Ahora'}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-2 mt-6 pt-6 border-t border-gray-200">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition font-medium"
                            disabled={loading}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition font-medium flex items-center gap-2 disabled:opacity-50"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Guardando...
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    Guardar Cambios
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
