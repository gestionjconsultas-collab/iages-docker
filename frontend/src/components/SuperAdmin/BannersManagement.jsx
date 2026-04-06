// frontend/src/components/SuperAdmin/BannersManagement.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import {
    Plus, Edit2, Trash2, ToggleLeft, ToggleRight,
    TrendingUp, MousePointerClick, X, Save
} from 'lucide-react';

const BannersManagement = () => {
    const [banners, setBanners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingBanner, setEditingBanner] = useState(null);
    const [cupones, setCupones] = useState([]);

    const [formData, setFormData] = useState({
        titulo: '',
        descripcion: '',
        icono: '🎉',
        color_fondo: '#8B5CF6',
        color_texto: '#FFFFFF',
        plan_objetivo: '',
        cupon_codigo: '',
        prioridad: 0,
        activo: true,
        fecha_inicio: '',
        fecha_fin: ''
    });

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const [bannersRes, cuponesRes] = await Promise.all([
                axios.get('/api/admin/banners'),
                axios.get('/api/admin/cupones')
            ]);

            setBanners(bannersRes.data.banners || []);
            setCupones(cuponesRes.data.cupones || []);
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error cargando datos');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        try {
            if (editingBanner) {
                await axios.put(`/api/admin/banners/${editingBanner.id}`, formData);
                toast.success('Banner actualizado exitosamente');
            } else {
                await axios.post('/api/admin/banners', formData);
                toast.success('Banner creado exitosamente');
            }

            setShowModal(false);
            resetForm();
            cargarDatos();
        } catch (error) {
            console.error('Error guardando banner:', error);
            toast.error(error.response?.data?.error || 'Error guardando banner');
        }
    };

    const handleToggle = async (bannerId) => {
        try {
            await axios.patch(`/api/admin/banners/${bannerId}/toggle`);
            toast.success('Estado actualizado');
            cargarDatos();
        } catch (error) {
            console.error('Error toggling banner:', error);
            toast.error('Error actualizando estado');
        }
    };

    const handleDelete = async (bannerId) => {
        if (!confirm('¿Estás seguro de eliminar este banner?')) return;

        try {
            await axios.delete(`/api/admin/banners/${bannerId}`);
            toast.success('Banner eliminado');
            cargarDatos();
        } catch (error) {
            console.error('Error eliminando banner:', error);
            toast.error('Error eliminando banner');
        }
    };

    const handleEdit = (banner) => {
        setEditingBanner(banner);
        setFormData({
            titulo: banner.titulo,
            descripcion: banner.descripcion || '',
            icono: banner.icono || '🎉',
            color_fondo: banner.color_fondo || '#8B5CF6',
            color_texto: banner.color_texto || '#FFFFFF',
            plan_objetivo: banner.plan_objetivo || '',
            cupon_codigo: banner.cupon_codigo || '',
            prioridad: banner.prioridad || 0,
            activo: banner.activo,
            fecha_inicio: banner.fecha_inicio || '',
            fecha_fin: banner.fecha_fin || ''
        });
        setShowModal(true);
    };

    const resetForm = () => {
        setEditingBanner(null);
        setFormData({
            titulo: '',
            descripcion: '',
            icono: '🎉',
            color_fondo: '#8B5CF6',
            color_texto: '#FFFFFF',
            plan_objetivo: '',
            cupon_codigo: '',
            prioridad: 0,
            activo: true,
            fecha_inicio: '',
            fecha_fin: ''
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Banners Promocionales</h1>
                    <p className="text-gray-600">Gestiona los banners que ven las gestorías</p>
                </div>
                <button
                    onClick={() => {
                        resetForm();
                        setShowModal(true);
                    }}
                    className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    <Plus className="w-5 h-5" />
                    Nuevo Banner
                </button>
            </div>

            {/* Tabla de Banners */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Banner</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan Objetivo</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cupón</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Analytics</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {banners.map((banner) => (
                            <tr key={banner.id} className="hover:bg-gray-50">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{banner.icono}</span>
                                        <div>
                                            <div className="font-medium text-gray-900">{banner.titulo}</div>
                                            <div className="text-sm text-gray-500">{banner.descripcion}</div>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                                        {banner.plan_objetivo || 'Todos'}
                                    </span>
                                </td>
                                <td className="px-6 py-4">
                                    <span className="font-mono text-sm">{banner.cupon_codigo || '-'}</span>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex gap-4 text-sm">
                                        <div className="flex items-center gap-1">
                                            <MousePointerClick className="w-4 h-4 text-gray-400" />
                                            <span>{banner.clicks || 0}</span>
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <TrendingUp className="w-4 h-4 text-green-500" />
                                            <span>{banner.conversiones || 0}</span>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <button
                                        onClick={() => handleToggle(banner.id)}
                                        className="flex items-center gap-2"
                                    >
                                        {banner.activo ? (
                                            <>
                                                <ToggleRight className="w-6 h-6 text-green-500" />
                                                <span className="text-sm text-green-600">Activo</span>
                                            </>
                                        ) : (
                                            <>
                                                <ToggleLeft className="w-6 h-6 text-gray-400" />
                                                <span className="text-sm text-gray-500">Inactivo</span>
                                            </>
                                        )}
                                    </button>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleEdit(banner)}
                                            className="p-2 text-blue-600 hover:bg-blue-50 rounded"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => handleDelete(banner.id)}
                                            className="p-2 text-red-600 hover:bg-red-50 rounded"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                {banners.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                        No hay banners creados. Crea el primero para empezar.
                    </div>
                )}
            </div>

            {/* Modal Crear/Editar */}
            {showModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="p-6">
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-xl font-bold">
                                    {editingBanner ? 'Editar Banner' : 'Nuevo Banner'}
                                </h2>
                                <button
                                    onClick={() => {
                                        setShowModal(false);
                                        resetForm();
                                    }}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    <X className="w-6 h-6" />
                                </button>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Título *
                                    </label>
                                    <input
                                        type="text"
                                        required
                                        value={formData.titulo}
                                        onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Descripción
                                    </label>
                                    <textarea
                                        value={formData.descripcion}
                                        onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                                        rows={3}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Icono (Emoji)
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.icono}
                                            onChange={(e) => setFormData({ ...formData, icono: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Prioridad
                                        </label>
                                        <input
                                            type="number"
                                            value={formData.prioridad}
                                            onChange={(e) => setFormData({ ...formData, prioridad: parseInt(e.target.value) })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Color de Fondo
                                        </label>
                                        <input
                                            type="color"
                                            value={formData.color_fondo}
                                            onChange={(e) => setFormData({ ...formData, color_fondo: e.target.value })}
                                            className="w-full h-10 border border-gray-300 rounded-lg"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Color de Texto
                                        </label>
                                        <input
                                            type="color"
                                            value={formData.color_texto}
                                            onChange={(e) => setFormData({ ...formData, color_texto: e.target.value })}
                                            className="w-full h-10 border border-gray-300 rounded-lg"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Plan Objetivo
                                    </label>
                                    <select
                                        value={formData.plan_objetivo}
                                        onChange={(e) => setFormData({ ...formData, plan_objetivo: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                    >
                                        <option value="">Todos los planes</option>
                                        <option value="basico">Básico</option>
                                        <option value="plus">Plus</option>
                                        <option value="premium">Premium</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Cupón
                                    </label>
                                    <select
                                        value={formData.cupon_codigo}
                                        onChange={(e) => setFormData({ ...formData, cupon_codigo: e.target.value })}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                    >
                                        <option value="">Sin cupón</option>
                                        {cupones.map((cupon) => (
                                            <option key={cupon.id} value={cupon.codigo}>
                                                {cupon.codigo} - {cupon.descuento_porcentaje}% off
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Fecha Inicio
                                        </label>
                                        <input
                                            type="date"
                                            value={formData.fecha_inicio}
                                            onChange={(e) => setFormData({ ...formData, fecha_inicio: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Fecha Fin
                                        </label>
                                        <input
                                            type="date"
                                            value={formData.fecha_fin}
                                            onChange={(e) => setFormData({ ...formData, fecha_fin: e.target.value })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                                        />
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        id="activo"
                                        checked={formData.activo}
                                        onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                                        className="w-4 h-4 text-orange-500 border-gray-300 rounded focus:ring-orange-500"
                                    />
                                    <label htmlFor="activo" className="text-sm font-medium text-gray-700">
                                        Banner activo
                                    </label>
                                </div>

                                <div className="flex gap-3 pt-4">
                                    <button
                                        type="submit"
                                        className="flex-1 flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white py-2 px-4 rounded-lg transition-colors"
                                    >
                                        <Save className="w-5 h-5" />
                                        {editingBanner ? 'Actualizar' : 'Crear'} Banner
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setShowModal(false);
                                            resetForm();
                                        }}
                                        className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                                    >
                                        Cancelar
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default BannersManagement;
