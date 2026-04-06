import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Users, UserPlus, Shield, CheckCircle, XCircle,
    Edit2, Loader2, Search, Building2, Briefcase,
    AtSign, Key, ExternalLink
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function GestionUsuariosSistema() {
    const [usuarios, setUsuarios] = useState([]);
    const [roles, setRoles] = useState([]);
    const [departamentos, setDepartamentos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);

    // Form state
    const [formData, setFormData] = useState({
        nombre: '',
        email: '',
        password: '',
        confirmPassword: '',
        rol_id: '',
        departamento_id: '',
        is_soporte: false
    });

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        try {
            setLoading(true);
            const [usersRes, rolesRes, deptsRes] = await Promise.all([
                axios.get('/api/admin/usuarios'), // Global users list (RBAC endpoint)
                axios.get('/api/admin/roles'),
                axios.get('/api/departamentos')
            ]);

            setUsuarios(usersRes.data.users || []);
            setRoles(rolesRes.data.roles || []);
            setDepartamentos(deptsRes.data.departamentos || []);
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error al cargar datos del sistema');
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (formData.password && formData.password !== formData.confirmPassword) {
            toast.error('Las contraseñas no coinciden');
            return;
        }

        try {
            if (editingUser) {
                // Actualizar usuario globalmente
                const payload = {
                    nombre: formData.nombre,
                    email: formData.email,
                    rol_id: parseInt(formData.rol_id) || null,
                    departamento_id: parseInt(formData.departamento_id) || null,
                    is_soporte: formData.is_soporte
                };

                if (formData.password) {
                    payload.password = formData.password;
                }

                await axios.put(`/api/super-admin/usuarios/${editingUser.id}`, payload);
                toast.success('Usuario actualizado correctamente');
            } else {
                // Crear usuario sistema (Legacy SysAdmin creation or use unified)
                // Usamos el endpoint existente de creación de sistema por ahora
                await axios.post('/api/super-admin/usuarios-sistema', {
                    nombre: formData.nombre,
                    email: formData.email,
                    password: formData.password,
                    rol: formData.rol_id === '1' ? 'super_admin' : 'soporte' // Mapeo temporal para legacy compatibility if needed
                });
                toast.success('Usuario creado correctamente');
            }

            setShowModal(false);
            setEditingUser(null);
            cargarDatos();
        } catch (error) {
            console.error('Error:', error);
            toast.error(error.response?.data?.error || 'Error al guardar usuario');
        }
    };

    const handleToggleStatus = async (usuario) => {
        const accion = usuario.activo ? 'desactivar' : 'activar';
        if (!window.confirm(`¿Estás seguro de ${accion} a ${usuario.nombre}?`)) return;

        try {
            // Usamos el endpoint que ya funciona para toggle
            await axios.post(`/api/users/${usuario.id}/toggle-status`);
            toast.success(`Usuario ${accion === 'desactivar' ? 'desactivado' : 'activado'} correctamente`);
            cargarDatos();
        } catch (error) {
            console.error('Error:', error);
            toast.error(error.response?.data?.error || `Error al ${accion} usuario`);
        }
    };

    const handleDisable2FA = async (usuario) => {
        if (!window.confirm(`¿Estás seguro de desactivar la Autenticación de Doble Factor (2FA) para ${usuario.nombre}? Esta acción borrará su configuración actual.`)) return;
        try {
            await axios.post(`/api/users/${usuario.id}/disable-2fa`);
            toast.success("2FA desactivado correctamente");
            cargarDatos();
        } catch (err) {
            toast.error(err.response?.data?.error || "Error al desactivar 2FA");
        }
    };

    const openEditModal = (usuario) => {
        setFormData({
            nombre: usuario.nombre || '',
            email: usuario.email || '',
            password: '',
            confirmPassword: '',
            rol_id: usuario.rol_id || '',
            departamento_id: usuario.departamento_id || '',
            is_soporte: usuario.is_soporte || false
        });
        setEditingUser(usuario);
        setShowModal(true);
    };

    const filteredUsers = usuarios.filter(u =>
        u.nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.gestoria_nombre?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Shield className="w-8 h-8 text-blue-600" />
                        Usuarios del Sistema
                    </h1>
                    <p className="text-gray-600 mt-1">Gestión global de accesos, roles y departamentos</p>
                </div>

                <div className="flex w-full md:w-auto gap-3">
                    <div className="relative flex-1 md:w-64">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Buscar usuario, email o gestoría..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden transition-all text-sm"
                        />
                    </div>
                </div>
            </div>

            {/* Tabla de Usuarios */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50/50 border-b border-gray-100">
                            <tr>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Usuario</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Organización</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider">Rol / Depto</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-center">Estado</th>
                                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase tracking-wider text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {filteredUsers.map(usuario => (
                                <tr key={usuario.id} className="hover:bg-blue-50/30 transition-colors group">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white
                                                ${usuario.is_super_admin ? 'bg-red-500' : 'bg-blue-500'}`}>
                                                {usuario.nombre?.charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="font-semibold text-gray-900 flex items-center gap-2">
                                                    {usuario.nombre}
                                                    {usuario.is_super_admin && (
                                                        <Shield className="w-3 h-3 text-red-500" title="Super-Admin" />
                                                    )}
                                                </div>
                                                <div className="text-xs text-gray-500 flex items-center gap-1">
                                                    <AtSign className="w-3 h-3" /> {usuario.email}
                                                </div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium text-gray-700 flex items-center gap-1">
                                                <Building2 className="w-3 h-3 text-gray-400" />
                                                {usuario.gestoria_nombre || 'SISTEMA'}
                                            </span>
                                            {usuario.is_soporte && (
                                                <span className="text-[10px] bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded w-fit mt-1 font-bold uppercase">
                                                    Soporte Externo
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="space-y-1">
                                            <div className="flex items-center gap-1.5">
                                                <Briefcase className="w-3 h-3 text-gray-400" />
                                                <span className="text-sm text-gray-700 capitalize">
                                                    {usuario.rol_nombre || <span className="text-gray-400 italic font-normal text-xs">Sin rol</span>}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                <Users className="w-3 h-3 text-gray-400" />
                                                <span className="text-xs text-gray-500">
                                                    {usuario.departamento || <span className="text-gray-400 italic font-normal">Sin depto</span>}
                                                </span>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        {usuario.activo ? (
                                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-green-50 text-green-700 text-[10px] font-bold uppercase">
                                                <CheckCircle className="w-3 h-3" /> Activo
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-50 text-red-700 text-[10px] font-bold uppercase">
                                                <XCircle className="w-3 h-3" /> Inactivo
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                onClick={() => openEditModal(usuario)}
                                                className="p-2 text-blue-600 hover:bg-blue-100 rounded-lg transition-colors"
                                                title="Configuración Avanzada"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => handleToggleStatus(usuario)}
                                                className={`p-2 rounded-lg transition-colors ${usuario.activo
                                                    ? 'text-red-500 hover:bg-red-50'
                                                    : 'text-green-600 hover:bg-green-50'
                                                    }`}
                                                disabled={usuario.id === 1} // Proteger usuario principal
                                                title={usuario.activo ? 'Desactivar' : 'Activar'}
                                            >
                                                {usuario.activo ? <XCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                                            </button>
                                            {usuario.two_factor_enabled && (
                                                <button
                                                    onClick={() => handleDisable2FA(usuario)}
                                                    className="p-2 text-red-500 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors border-l border-gray-100 ml-1 pl-3"
                                                    title="Forzar desactivación del 2FA (Seguridad Alta)"
                                                >
                                                    <Shield className="w-4 h-4" />
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal de Edición Avanzada */}
            {showModal && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-gray-100">
                        <div className="p-6 bg-linear-to-r from-blue-600 to-indigo-700 text-white flex justify-between items-center">
                            <div>
                                <h2 className="text-xl font-bold">
                                    Configuración de Usuario
                                </h2>
                                <p className="text-blue-100 text-xs mt-1">{formData.email}</p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="hover:rotate-90 transition-transform">
                                <XCircle className="w-6 h-6" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide px-1">Nombre</label>
                                    <div className="relative">
                                        <AtSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            value={formData.nombre}
                                            onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                                            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden transition-all text-sm"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide px-1">Rol de Sistema</label>
                                    <div className="relative">
                                        <Shield className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <select
                                            value={formData.rol_id}
                                            onChange={(e) => setFormData({ ...formData, rol_id: e.target.value })}
                                            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden transition-all text-sm appearance-none"
                                        >
                                            <option value="">Sin Rol Asignado</option>
                                            {roles.map(rol => (
                                                <option key={rol.id} value={rol.id}>{rol.nombre}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="space-y-1">
                                    <label className="text-xs font-bold text-gray-500 uppercase tracking-wide px-1">Departamento</label>
                                    <div className="relative">
                                        <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <select
                                            value={formData.departamento_id}
                                            onChange={(e) => setFormData({ ...formData, departamento_id: e.target.value })}
                                            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden transition-all text-sm appearance-none"
                                        >
                                            <option value="">Sin Departamento</option>
                                            {departamentos.map(dept => (
                                                <option key={dept.id} value={dept.id}>{dept.nombre}</option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 pt-6 px-2">
                                    <input
                                        type="checkbox"
                                        id="is_soporte"
                                        checked={formData.is_soporte}
                                        onChange={(e) => setFormData({ ...formData, is_soporte: e.target.checked })}
                                        className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                                    />
                                    <label htmlFor="is_soporte" className="text-sm font-medium text-gray-700 select-none">
                                        Soporte Externo
                                    </label>
                                </div>
                            </div>

                            <div className="pt-2 border-t border-gray-100 flex items-center gap-2 mb-2">
                                <Key className="w-4 h-4 text-gray-400" />
                                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Cambio de Contraseña (Opcional)</span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <input
                                    type="password"
                                    placeholder="Nueva contraseña"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden text-sm"
                                    minLength={8}
                                />
                                <input
                                    type="password"
                                    placeholder="Confirmar contraseña"
                                    value={formData.confirmPassword}
                                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-hidden text-sm"
                                    minLength={8}
                                />
                            </div>

                            <div className="flex justify-end gap-3 pt-6 border-t border-gray-100">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-6 py-2.5 text-sm font-semibold text-gray-600 bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="px-6 py-2.5 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-all shadow-lg shadow-blue-200 hover:shadow-blue-300 active:scale-95"
                                >
                                    Guardar Cambios
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
