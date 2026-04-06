import React, { useState } from 'react';
import axios from 'axios';
import { X, Save, Building, Mail, Phone, MapPin, Globe, CreditCard, Shield } from 'lucide-react';
import toast from 'react-hot-toast';

export default function EditGestoriaModal({ gestoria, onClose, onSave }) {
    const [formData, setFormData] = useState({
        nombre: gestoria.nombre || '',
        slug: gestoria.slug || '',
        email: gestoria.email || '',
        telefono: gestoria.telefono || '',
        direccion: gestoria.direccion || '',
        cif: gestoria.cif || '',
        activa: gestoria.activa !== undefined ? gestoria.activa : true,
        max_certificados: gestoria.max_certificados || 5
    });
    const [loading, setLoading] = useState(false);

    const handleNombreChange = (nombre) => {
        if (!formData.slug || formData.slug === gestoria.slug) {
            const slug = nombre
                .toLowerCase()
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .replace(/[^a-z0-9\s-]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-')
                .replace(/^-|-$/g, '');
            setFormData({ ...formData, nombre, slug });
        } else {
            setFormData({ ...formData, nombre });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);

        try {
            const response = await axios.put(`/api/super-admin/gestorias/${gestoria.id}`, formData);

            if (response.data.success) {
                toast.success('Gestoría actualizada correctamente');
                onSave();
            }
        } catch (error) {
            console.error('Error actualizando gestoría:', error);
            toast.error(error.response?.data?.error || 'Error al actualizar gestoría');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gray-50/50 sticky top-0 z-10">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">Editar Gestoría</h2>
                        <p className="text-sm text-gray-500">ID: {gestoria.id} — Modifica los datos principales de la entidad</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-200 rounded-lg transition"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6">
                    <div className="space-y-8">
                        {/* Sección: Información Básica */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                                <Building className="w-4 h-4 text-blue-600" />
                                <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wider">Información Básica</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Nombre de la Gestoría *</label>
                                    <input
                                        type="text"
                                        value={formData.nombre}
                                        onChange={(e) => handleNombreChange(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">CIF / NIF</label>
                                    <div className="relative">
                                        <CreditCard className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            value={formData.cif}
                                            onChange={(e) => setFormData({ ...formData, cif: e.target.value.toUpperCase() })}
                                            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="B12345678"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Slug (URL)</label>
                                    <div className="relative">
                                        <Globe className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            value={formData.slug}
                                            onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
                                            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="mi-gestoria"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Sección: Contacto */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                                <Mail className="w-4 h-4 text-orange-600" />
                                <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wider">Contacto y Ubicación</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Email de Contacto</label>
                                    <div className="relative">
                                        <Mail className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                        <input
                                            type="email"
                                            value={formData.email}
                                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="info@gestoria.com"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                                    <div className="relative">
                                        <Phone className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            value={formData.telefono}
                                            onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                                            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="+34 900 000 000"
                                        />
                                    </div>
                                </div>

                                <div className="md:col-span-2">
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Dirección Completa</label>
                                    <div className="relative">
                                        <MapPin className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            value={formData.direccion}
                                            onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                                            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none transition"
                                            placeholder="Calle Ejemplo 123, 28001 Madrid"
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Sección: Estado de la Cuenta */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                                <Shield className="w-4 h-4 text-purple-600" />
                                <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wider">Estado de la Cuenta</h3>
                            </div>

                            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                                <label className="flex items-center gap-3 cursor-pointer group">
                                    <div className="relative flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={formData.activa}
                                            onChange={(e) => setFormData({ ...formData, activa: e.target.checked })}
                                            className="w-6 h-6 text-blue-600 border-gray-300 rounded-lg focus:ring-blue-500 cursor-pointer transition-all"
                                        />
                                    </div>
                                    <div className="flex flex-col">
                                        <span className="text-sm font-bold text-gray-700 group-hover:text-gray-900 transition">Gestoría Activa</span>
                                        <span className="text-[10px] text-gray-400 uppercase leading-none mt-1">
                                            Interruptor manual para permitir o denegar el acceso total al sistema
                                        </span>
                                    </div>
                                </label>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 mt-10 pt-6 border-t border-gray-100">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2 text-gray-700 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg font-medium transition"
                            disabled={loading}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition flex items-center gap-2 disabled:opacity-50 shadow-lg shadow-blue-200"
                            disabled={loading}
                        >
                            {loading ? (
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            ) : (
                                <Save className="w-4 h-4" />
                            )}
                            Guardar Cambios
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
