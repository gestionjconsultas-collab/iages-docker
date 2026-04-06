import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Edit, Trash2, Users, Building2, FileText, X, Save, Loader2, Settings, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import ConfiguracionGestoriaModal from './ConfiguracionGestoriaModal';
import { useAuth } from '../AuthContext';

export default function GestoriasAdminView() {
    const { user } = useAuth();
    const [gestorias, setGestorias] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingGestoria, setEditingGestoria] = useState(null);
    const [solicitudesPendientes, setSolicitudesPendientes] = useState({});
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
    const [saving, setSaving] = useState(false);
    const [showConfigModal, setShowConfigModal] = useState(false);
    const [configuringGestoria, setConfiguringGestoria] = useState(null);

    useEffect(() => {
        loadGestorias();
    }, []);

    const loadGestorias = async () => {
        try {
            const res = await axios.get('/api/admin/gestorias', { withCredentials: true });
            if (res.data.success) {
                setGestorias(res.data.gestorias);
            }
        } catch (error) {
            if (error.response?.status === 403) {
                toast.error('Acceso denegado. Solo super-administradores.');
            } else {
                toast.error('Error cargando gestorías');
            }
        } finally {
            setLoading(false);
        }
    };

    const solicitarAcceso = async (gestoriaId, gestoriaNombre) => {
        setSolicitudesPendientes(prev => ({ ...prev, [gestoriaId]: 'solicitando' }));
        try {
            await axios.post(`/api/impersonacion/solicitar/${gestoriaId}`, {}, { withCredentials: true });
            setSolicitudesPendientes(prev => ({ ...prev, [gestoriaId]: 'esperando' }));
            toast.success(`Solicitud enviada a ${gestoriaNombre}. Esperando respuesta...`);
        } catch {
            setSolicitudesPendientes(prev => { const n = { ...prev }; delete n[gestoriaId]; return n; });
            toast.error('Error al enviar solicitud');
        }
    };

    const handleCreate = () => {
        setEditingGestoria(null);
        setFormData({
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
        setShowModal(true);
    };

    const handleEdit = (gestoria) => {
        setEditingGestoria(gestoria);
        setFormData({
            nombre: gestoria.nombre,
            slug: gestoria.slug,
            email: gestoria.email || '',
            plan: gestoria.plan,
            activa: gestoria.activa
        });
        setShowModal(true);
    };

    const handleSave = async () => {
        // Validaciones
        if (!formData.nombre.trim()) {
            toast.error('El nombre es requerido');
            return;
        }
        if (!formData.slug.trim()) {
            toast.error('El slug es requerido');
            return;
        }

        // Validaciones de admin solo al crear
        if (!editingGestoria) {
            if (!formData.admin.nombre.trim()) {
                toast.error('El nombre del administrador es requerido');
                return;
            }
            if (!formData.admin.email.trim()) {
                toast.error('El email del administrador es requerido');
                return;
            }
            if (!formData.admin.password.trim()) {
                toast.error('La contraseña del administrador es requerida');
                return;
            }
            if (formData.admin.password.length < 6) {
                toast.error('La contraseña debe tener al menos 6 caracteres');
                return;
            }
        }

        setSaving(true);
        try {
            if (editingGestoria) {
                // Actualizar
                const res = await axios.put(
                    `/api/admin/gestorias/${editingGestoria.id}`,
                    formData,
                    { withCredentials: true }
                );
                if (res.data.success) {
                    toast.success('Gestoría actualizada exitosamente');
                    setShowModal(false);
                    loadGestorias();
                }
            } else {
                // Crear
                const res = await axios.post(
                    '/api/admin/gestorias',
                    formData,
                    { withCredentials: true }
                );
                if (res.data.success) {
                    toast.success(`Gestoría creada exitosamente. Usuario: ${res.data.admin.email}`);
                    setShowModal(false);
                    loadGestorias();
                }
            }
        } catch (error) {
            toast.error(error.response?.data?.error || 'Error guardando gestoría');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id, nombre) => {
        if (!confirm(`¿Desactivar la gestoría "${nombre}"?`)) return;

        try {
            const res = await axios.delete(`/api/admin/gestorias/${id}`, { withCredentials: true });
            if (res.data.success) {
                toast.success('Gestoría desactivada');
                loadGestorias();
            }
        } catch (error) {
            toast.error(error.response?.data?.error || 'Error desactivando gestoría');
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Gestión de Gestorías</h1>
                    <p className="text-gray-600">Administra todas las gestorías del sistema</p>
                </div>
                <button
                    onClick={handleCreate}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 transition-opacity"
                >
                    <Plus className="w-5 h-5" />
                    Nueva Gestoría
                </button>
            </div>

            {/* Grid de gestorías */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {gestorias.filter(g => g.activa).map(gestoria => (
                    <div key={gestoria.id} className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
                        {/* Header */}
                        <div className="flex justify-between items-start mb-4">
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-gray-900 truncate">{gestoria.nombre}</h3>
                                <p className="text-sm text-gray-500">@{gestoria.slug}</p>
                                {gestoria.email && (
                                    <p className="text-xs text-gray-400 mt-1 truncate">{gestoria.email}</p>
                                )}
                            </div>
                            <span className={`px-2 py-1 text-xs rounded-full shrink-0 ${gestoria.activa ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>
                                {gestoria.activa ? 'Activa' : 'Inactiva'}
                            </span>
                        </div>

                        {/* Plan */}
                        <div className="mb-4">
                            <span className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full">
                                Plan: {gestoria.plan}
                            </span>
                        </div>

                        {/* Métricas */}
                        <div className="grid grid-cols-3 gap-4 mb-4 pt-4 border-t border-gray-100">
                            <div className="text-center">
                                <Building2 className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                                <div className="text-xl font-bold text-gray-900">{gestoria.metricas.empresas}</div>
                                <div className="text-xs text-gray-500">Empresas</div>
                            </div>
                            <div className="text-center">
                                <FileText className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                                <div className="text-xl font-bold text-gray-900">{gestoria.metricas.documentos}</div>
                                <div className="text-xs text-gray-500">Docs</div>
                            </div>
                            <div className="text-center">
                                <Users className="w-5 h-5 text-gray-400 mx-auto mb-1" />
                                <div className="text-xl font-bold text-gray-900">{gestoria.metricas.usuarios}</div>
                                <div className="text-xs text-gray-500">Usuarios</div>
                            </div>
                        </div>

                        {/* Acciones */}
                        <div className="flex gap-2 flex-wrap">
                            <button
                                onClick={() => {
                                    setConfiguringGestoria(gestoria);
                                    setShowConfigModal(true);
                                }}
                                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors"
                                title="Configurar Branding"
                            >
                                <Settings className="w-4 h-4" />
                                Config
                            </button>
                            <button
                                onClick={() => handleEdit(gestoria)}
                                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                            >
                                <Edit className="w-4 h-4" />
                                Editar
                            </button>
                            {gestoria.id !== 1 && (
                                <button
                                    onClick={() => handleDelete(gestoria.id, gestoria.nombre)}
                                    className="px-3 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            )}
                            {(user?.is_super_admin || (user?.is_soporte && !user?.gestoria_id)) && (
                                <button
                                    onClick={() => solicitarAcceso(gestoria.id, gestoria.nombre)}
                                    disabled={!!solicitudesPendientes[gestoria.id]}
                                    className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors ${
                                        solicitudesPendientes[gestoria.id] === 'esperando'
                                            ? 'bg-amber-100 text-amber-700 cursor-wait'
                                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                                    } disabled:opacity-60`}
                                    title="Solicitar acceso temporal a esta gestoría"
                                >
                                    <Shield className="w-4 h-4" />
                                    {solicitudesPendientes[gestoria.id] === 'esperando' ? 'Esperando...' : 'Acceder'}
                                </button>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Modal de crear/editar */}
            {showModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        {/* Header */}
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold text-gray-900">
                                {editingGestoria ? 'Editar Gestoría' : 'Nueva Gestoría'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        {/* Formulario */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Nombre *
                                </label>
                                <input
                                    type="text"
                                    value={formData.nombre}
                                    onChange={(e) => {
                                        const nombre = e.target.value;
                                        const slug = nombre
                                            .toLowerCase()
                                            .normalize('NFD')
                                            .replace(/[\u0300-\u036f]/g, '') // Eliminar acentos
                                            .replace(/[^a-z0-9\s-]/g, '') // Solo letras, números, espacios y guiones
                                            .replace(/\s+/g, '-') // Reemplazar espacios con guiones
                                            .replace(/-+/g, '-') // Eliminar guiones duplicados
                                            .replace(/^-|-$/g, ''); // Eliminar guiones al inicio/final

                                        setFormData({ ...formData, nombre, slug });
                                    }}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                    placeholder="Nombre de la gestoría"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Slug * <span className="text-xs text-gray-500">(solo minúsculas, números y guiones)</span>
                                </label>
                                <input
                                    type="text"
                                    value={formData.slug}
                                    onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                    placeholder="mi-gestoria"
                                    disabled={editingGestoria?.id === 1}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Email
                                </label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                    placeholder="contacto@gestoria.com"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Plan
                                </label>
                                <select
                                    value={formData.plan}
                                    onChange={(e) => setFormData({ ...formData, plan: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                >
                                    <option value="basico">Básico (€99/mes)</option>
                                    <option value="plus">Plus (€199/mes)</option>
                                    <option value="premium">Premium (€399/mes)</option>
                                </select>
                            </div>

                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    id="activa"
                                    checked={formData.activa}
                                    onChange={(e) => setFormData({ ...formData, activa: e.target.checked })}
                                    className="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                                />
                                <label htmlFor="activa" className="ml-2 text-sm text-gray-700">
                                    Gestoría activa
                                </label>
                            </div>

                            {/* Campos de administrador solo al crear */}
                            {!editingGestoria && (
                                <>
                                    <div className="pt-4 border-t border-gray-200">
                                        <h3 className="text-sm font-semibold text-gray-900 mb-3">Usuario Administrador</h3>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Nombre del Admin *
                                        </label>
                                        <input
                                            type="text"
                                            value={formData.admin.nombre}
                                            onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, nombre: e.target.value } })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                            placeholder="Juan Pérez"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Email del Admin *
                                        </label>
                                        <input
                                            type="email"
                                            value={formData.admin.email}
                                            onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, email: e.target.value } })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                            placeholder="admin@gestoria.com"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Contraseña *
                                        </label>
                                        <input
                                            type="password"
                                            value={formData.admin.password}
                                            onChange={(e) => setFormData({ ...formData, admin: { ...formData.admin, password: e.target.value } })}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                            placeholder="Mínimo 6 caracteres"
                                        />
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Botones */}
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowModal(false)}
                                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                                disabled={saving}
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                            >
                                {saving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Guardando...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        Guardar
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de configuración */}
            {showConfigModal && configuringGestoria && (
                <ConfiguracionGestoriaModal
                    gestoria={configuringGestoria}
                    onClose={() => {
                        setShowConfigModal(false);
                        setConfiguringGestoria(null);
                    }}
                    onSave={(newConfig) => {
                        // Actualizar la gestoría en la lista
                        setGestorias(prev => prev.map(g =>
                            g.id === configuringGestoria.id
                                ? { ...g, configuracion: newConfig }
                                : g
                        ));
                        setShowConfigModal(false);
                        setConfiguringGestoria(null);
                    }}
                />
            )}
        </div>
    );
}
