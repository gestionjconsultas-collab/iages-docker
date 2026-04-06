import React, { useState, useEffect } from 'react';
import { Shield, Plus, Edit2, Trash2, Save, X, Users, Key, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import MatrizPermisos from './MatrizPermisos';
import UsuariosPorRol from './UsuariosPorRol';

export default function RolesPermisosAdminView() {
    const [activeTab, setActiveTab] = useState('roles'); // 'roles', 'permisos', 'matriz'
    const [roles, setRoles] = useState([]);
    const [permisos, setPermisos] = useState([]);
    const [permisosPorModulo, setPermisosPorModulo] = useState({});
    const [loading, setLoading] = useState(true);
    const [modalRol, setModalRol] = useState(null);
    const [modalPermisos, setModalPermisos] = useState(null);
    const [permisosSeleccionados, setPermisosSeleccionados] = useState([]);

    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        try {
            setLoading(true);
            const [rolesRes, permisosRes] = await Promise.all([
                fetch('/api/admin/roles', { credentials: 'include' }),
                fetch('/api/admin/permisos', { credentials: 'include' })
            ]);

            const rolesData = await rolesRes.json();
            const permisosData = await permisosRes.json();

            if (rolesData.success) setRoles(rolesData.roles);
            if (permisosData.success) {
                setPermisos(permisosData.permisos);
                setPermisosPorModulo(permisosData.permisos_por_modulo || {});
            }
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error al cargar datos');
        } finally {
            setLoading(false);
        }
    };

    const handleGuardarRol = async () => {
        try {
            const url = modalRol.id
                ? `/api/admin/roles/${modalRol.id}`
                : '/api/admin/roles';

            const method = modalRol.id ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    nombre: modalRol.nombre,
                    descripcion: modalRol.descripcion,
                    gestoria_id: modalRol.gestoria_id || null
                })
            });

            const data = await response.json();

            if (data.success) {
                toast.success(modalRol.id ? 'Rol actualizado' : 'Rol creado');
                cargarDatos();
                setModalRol(null);
            } else {
                toast.error(data.error || 'Error al guardar rol');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al guardar rol');
        }
    };

    const handleEliminarRol = async (rolId) => {
        if (!confirm('¿Estás seguro de eliminar este rol?')) return;

        try {
            const response = await fetch(`/api/admin/roles/${rolId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                toast.success('Rol eliminado');
                cargarDatos();
            } else {
                toast.error(data.error || 'Error al eliminar rol');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al eliminar rol');
        }
    };

    const handleAbrirPermisos = async (rol) => {
        try {
            const response = await fetch(`/api/admin/roles/${rol.id}/permisos`, {
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                setModalPermisos(rol);
                setPermisosSeleccionados(data.permisos.map(p => p.id));
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al cargar permisos');
        }
    };

    const handleGuardarPermisos = async () => {
        try {
            const response = await fetch(`/api/admin/roles/${modalPermisos.id}/permisos/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    permisos_ids: permisosSeleccionados,
                    replace: true
                })
            });

            const data = await response.json();

            if (data.success) {
                toast.success('Permisos actualizados');
                cargarDatos();
                setModalPermisos(null);
                setPermisosSeleccionados([]);
            } else {
                toast.error(data.error || 'Error al guardar permisos');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al guardar permisos');
        }
    };

    const togglePermiso = (permisoId) => {
        setPermisosSeleccionados(prev =>
            prev.includes(permisoId)
                ? prev.filter(id => id !== permisoId)
                : [...prev, permisoId]
        );
    };

    const toggleModulo = (modulo) => {
        const permisosModulo = permisosPorModulo[modulo]?.map(p => p.id) || [];
        const todosSeleccionados = permisosModulo.every(id => permisosSeleccionados.includes(id));

        if (todosSeleccionados) {
            setPermisosSeleccionados(prev => prev.filter(id => !permisosModulo.includes(id)));
        } else {
            setPermisosSeleccionados(prev => [...new Set([...prev, ...permisosModulo])]);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
                    <Shield className="text-primary" />
                    Gestión de Roles y Permisos
                </h1>
                <p className="text-gray-600 mt-2">
                    Administra roles, permisos y asignaciones del sistema RBAC
                </p>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 mb-6">
                <nav className="-mb-px flex space-x-8">
                    <button
                        onClick={() => setActiveTab('roles')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'roles'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        <Users className="inline mr-2 h-5 w-5" />
                        Roles
                    </button>
                    <button
                        onClick={() => setActiveTab('permisos')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'permisos'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        <Key className="inline mr-2 h-5 w-5" />
                        Permisos
                    </button>
                    <button
                        onClick={() => setActiveTab('matriz')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'matriz'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        <Check className="inline mr-2 h-5 w-5" />
                        Matriz de Permisos
                    </button>
                    <button
                        onClick={() => setActiveTab('usuarios')}
                        className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'usuarios'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                            }`}
                    >
                        <Users className="inline mr-2 h-5 w-5" />
                        Usuarios por Rol
                    </button>
                </nav>
            </div>

            {/* Content */}
            {activeTab === 'roles' && (
                <div>
                    {/* Botón Nuevo Rol */}
                    <div className="mb-4">
                        <button
                            onClick={() => setModalRol({ nombre: '', descripcion: '', gestoria_id: null })}
                            className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark flex items-center gap-2"
                        >
                            <Plus className="h-5 w-5" />
                            Nuevo Rol
                        </button>
                    </div>

                    {/* Lista de Roles */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {roles.map(rol => (
                            <div key={rol.id} className="bg-white rounded-lg shadow p-6 border border-gray-200">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-lg font-semibold text-gray-900">{rol.nombre}</h3>
                                        <p className="text-sm text-gray-500">{rol.descripcion}</p>
                                    </div>
                                    {rol.es_sistema && (
                                        <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                                            Sistema
                                        </span>
                                    )}
                                </div>

                                <div className="space-y-2 mb-4">
                                    <div className="flex items-center text-sm text-gray-600">
                                        <Users className="h-4 w-4 mr-2" />
                                        {rol.usuarios_count} usuario(s)
                                    </div>
                                    <div className="flex items-center text-sm text-gray-600">
                                        <Key className="h-4 w-4 mr-2" />
                                        {rol.permisos_count} permiso(s)
                                    </div>
                                    <div className="flex items-center text-sm text-gray-600">
                                        <Shield className="h-4 w-4 mr-2" />
                                        {rol.gestoria_nombre}
                                    </div>
                                </div>

                                <div className="flex gap-2">
                                    <button
                                        onClick={() => handleAbrirPermisos(rol)}
                                        className="flex-1 bg-blue-50 text-blue-600 px-3 py-2 rounded hover:bg-blue-100 text-sm"
                                    >
                                        Permisos
                                    </button>
                                    {!rol.es_sistema && (
                                        <>
                                            <button
                                                onClick={() => setModalRol(rol)}
                                                className="bg-gray-50 text-gray-600 px-3 py-2 rounded hover:bg-gray-100"
                                            >
                                                <Edit2 className="h-4 w-4" />
                                            </button>
                                            <button
                                                onClick={() => handleEliminarRol(rol.id)}
                                                className="bg-red-50 text-red-600 px-3 py-2 rounded hover:bg-red-100"
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {activeTab === 'permisos' && (
                <div>
                    {/* Lista de Permisos por Módulo */}
                    {Object.entries(permisosPorModulo).map(([modulo, permisos]) => (
                        <div key={modulo} className="mb-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-3 capitalize">
                                {modulo}
                            </h3>
                            <div className="bg-white rounded-lg shadow overflow-x-auto"><table className="min-w-full divide-y divide-gray-200">
                                    <thead className="bg-gray-50">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                Código
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                Nombre
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                Descripción
                                            </th>
                                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                                                Acción
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="bg-white divide-y divide-gray-200">
                                        {permisos.map(permiso => (
                                            <tr key={permiso.id}>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                                                    {permiso.codigo}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                    {permiso.nombre}
                                                </td>
                                                <td className="px-6 py-4 text-sm text-gray-500">
                                                    {permiso.descripcion}
                                                </td>
                                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {permiso.accion}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {activeTab === 'matriz' && (
                <MatrizPermisos roles={roles} permisos={permisos} onReload={cargarDatos} />
            )}

            {activeTab === 'usuarios' && (
                <UsuariosPorRol roles={roles} />
            )}

            {/* Modal Crear/Editar Rol */}
            {modalRol && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md">
                        <h2 className="text-xl font-bold mb-4">
                            {modalRol.id ? 'Editar Rol' : 'Nuevo Rol'}
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Nombre *
                                </label>
                                <input
                                    type="text"
                                    value={modalRol.nombre}
                                    onChange={(e) => setModalRol({ ...modalRol, nombre: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                    placeholder="Nombre del rol"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Descripción
                                </label>
                                <textarea
                                    value={modalRol.descripcion}
                                    onChange={(e) => setModalRol({ ...modalRol, descripcion: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                    rows="3"
                                    placeholder="Descripción del rol"
                                />
                            </div>
                        </div>

                        <div className="flex gap-2 mt-6">
                            <button
                                onClick={handleGuardarRol}
                                className="flex-1 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark flex items-center justify-center gap-2"
                            >
                                <Save className="h-5 w-5" />
                                Guardar
                            </button>
                            <button
                                onClick={() => setModalRol(null)}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Asignar Permisos */}
            {modalPermisos && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                        <h2 className="text-xl font-bold mb-4">
                            Permisos de: {modalPermisos.nombre}
                        </h2>

                        <div className="space-y-4">
                            {Object.entries(permisosPorModulo).map(([modulo, permisos]) => {
                                const permisosModulo = permisos.map(p => p.id);
                                const todosSeleccionados = permisosModulo.every(id => permisosSeleccionados.includes(id));
                                const algunoSeleccionado = permisosModulo.some(id => permisosSeleccionados.includes(id));

                                return (
                                    <div key={modulo} className="border border-gray-200 rounded-lg p-4">
                                        <div className="flex items-center mb-3">
                                            <input
                                                type="checkbox"
                                                checked={todosSeleccionados}
                                                ref={input => {
                                                    if (input) input.indeterminate = algunoSeleccionado && !todosSeleccionados;
                                                }}
                                                onChange={() => toggleModulo(modulo)}
                                                className="h-5 w-5 text-primary rounded focus:ring-primary"
                                            />
                                            <label className="ml-3 text-lg font-semibold text-gray-900 capitalize">
                                                {modulo}
                                            </label>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 ml-8">
                                            {permisos.map(permiso => (
                                                <div key={permiso.id} className="flex items-center">
                                                    <input
                                                        type="checkbox"
                                                        checked={permisosSeleccionados.includes(permiso.id)}
                                                        onChange={() => togglePermiso(permiso.id)}
                                                        className="h-4 w-4 text-primary rounded focus:ring-primary"
                                                    />
                                                    <label className="ml-2 text-sm text-gray-700">
                                                        {permiso.nombre}
                                                        <span className="text-gray-500 ml-1">({permiso.codigo})</span>
                                                    </label>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        <div className="flex gap-2 mt-6">
                            <button
                                onClick={handleGuardarPermisos}
                                className="flex-1 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark flex items-center justify-center gap-2"
                            >
                                <Save className="h-5 w-5" />
                                Guardar Permisos
                            </button>
                            <button
                                onClick={() => {
                                    setModalPermisos(null);
                                    setPermisosSeleccionados([]);
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
