import React, { useState } from 'react';
import axios from 'axios';
import { X, Save, Loader2, User, Building } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CreateGestoriaModal({ onClose, onSave }) {
    const [formData, setFormData] = useState({
        nombre: '',
        slug: '',
        email: '',
        plan: 'basico',
        activa: true,
        admin: {
            nombre: '',
            email: '',
            password: ''
        }
    });
    const [loading, setLoading] = useState(false);

    const handleNombreChange = (nombre) => {
        const slug = nombre
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '') // Eliminar acentos
            .replace(/[^a-z0-9\s-]/g, '') // Solo letras, números, espacios y guiones
            .replace(/\s+/g, '-') // Reemplazar espacios con guiones
            .replace(/-+/g, '-') // Eliminar guiones duplicados
            .replace(/^-|-$/g, ''); // Eliminar guiones al inicio/final

        setFormData({ ...formData, nombre, slug });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validaciones simples
        if (!formData.nombre.trim()) return toast.error('El nombre es requerido');
        if (!formData.slug.trim()) return toast.error('El slug es requerido');
        if (!formData.admin.nombre.trim()) return toast.error('El nombre del administrador es requerido');
        if (!formData.admin.email.trim()) return toast.error('El email del administrador es requerido');
        if (!formData.admin.password.trim()) return toast.error('La contraseña es requerida');
        if (formData.admin.password.length < 6) return toast.error('La contraseña debe tener al menos 6 caracteres');

        setLoading(true);

        try {
            const response = await axios.post('/api/admin/gestorias', formData);

            if (response.data.success) {
                toast.success('Gestoría y administrador creados correctamente');
                onSave();
            }
        } catch (error) {
            console.error('Error creando gestoría:', error);
            toast.error(error.response?.data?.error || 'Error al crear la gestoría');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-gray-50/50">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900">Nueva Gestoría</h2>
                        <p className="text-sm text-gray-500">Crea una nueva gestoría y su usuario administrador inicial</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-200 rounded-lg transition"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Datos de la Gestoría */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                                <Building className="w-4 h-4 text-blue-600" />
                                <h3 className="font-semibold text-gray-900">Datos de la Empresa</h3>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                                <input
                                    type="text"
                                    value={formData.nombre}
                                    onChange={(e) => handleNombreChange(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="Nombre de la gestoría"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Slug (URL) *</label>
                                <input
                                    type="text"
                                    value={formData.slug}
                                    onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="mi-gestoria"
                                    required
                                />
                                <p className="text-[10px] text-gray-400 mt-1 uppercase font-bold">SOLO MINÚSCULAS Y GUIONES</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Email de contacto</label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="admin@gestoria.com"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Plan Inicial</label>
                                <select
                                    value={formData.plan}
                                    onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                >
                                    <option value="basico">Plan Básico</option>
                                    <option value="plus">Plan Plus</option>
                                    <option value="premium">Plan Premium</option>
                                </select>
                            </div>

                            <div className="pt-2">
                                <label className="flex items-center gap-2 cursor-pointer group">
                                    <input
                                        type="checkbox"
                                        checked={formData.activa}
                                        onChange={(e) => setFormData({ ...formData, activa: e.target.checked })}
                                        className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                    />
                                    <span className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition">Activar inmediatamente</span>
                                </label>
                            </div>
                        </div>

                        {/* Datos del Administrador */}
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
                                <User className="w-4 h-4 text-orange-600" />
                                <h3 className="font-semibold text-gray-900">Usuario Administrador</h3>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre completo *</label>
                                <input
                                    type="text"
                                    value={formData.admin.nombre}
                                    onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, nombre: e.target.value } })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="Juan Pérez"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Email de acceso *</label>
                                <input
                                    type="email"
                                    value={formData.admin.email}
                                    onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, email: e.target.value } })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="contacto@empresa.com"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña *</label>
                                <input
                                    type="password"
                                    value={formData.admin.password}
                                    onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, password: e.target.value } })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                                    placeholder="Mínimo 6 caracteres"
                                    required
                                />
                                <p className="text-[10px] text-gray-400 mt-1">ASEGÚRESE DE QUE SEA SEGURA</p>
                            </div>

                            <div className="bg-orange-50 p-4 rounded-lg border border-orange-100 mt-6">
                                <p className="text-xs text-orange-800 leading-relaxed">
                                    Este usuario tendrá permisos de <strong>Jefatura</strong> en su gestoría y será el responsable de configurar el sistema inicialmente.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Footer Actions */}
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
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition flex items-center gap-2 disabled:opacity-50"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Creando...
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    Crear Gestoría
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
