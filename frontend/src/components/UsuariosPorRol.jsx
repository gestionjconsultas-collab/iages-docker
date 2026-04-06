import React, { useState, useEffect } from 'react';
import { Users, Mail, Shield, Key, ChevronDown, ChevronUp, Search, Edit2, Save, X, Plus, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function UsuariosPorRol({ roles }) {
    const [usuariosPorRol, setUsuariosPorRol] = useState({});
    const [loading, setLoading] = useState(true);
    const [expandedRoles, setExpandedRoles] = useState({});
    const [searchTerm, setSearchTerm] = useState('');
    const [editingUser, setEditingUser] = useState(null);
    const [selectedRol, setSelectedRol] = useState(null);
    const [managingPermisosUser, setManagingPermisosUser] = useState(null);
    const [permisosDisponibles, setPermisosDisponibles] = useState([]);
    const [permisosIndividuales, setPermisosIndividuales] = useState([]);
    const [loadingPermisos, setLoadingPermisos] = useState(false);

    useEffect(() => {
        cargarUsuarios();
    }, [roles]);

    const cargarUsuarios = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/admin/usuarios', {
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                // Agrupar usuarios por rol
                const agrupados = {};

                data.users.forEach(user => {
                    const rolNombre = user.rol_nombre || 'Sin Rol';
                    if (!agrupados[rolNombre]) {
                        agrupados[rolNombre] = [];
                    }
                    agrupados[rolNombre].push(user);
                });

                setUsuariosPorRol(agrupados);

                // Expandir todos los roles por defecto
                const expanded = {};
                Object.keys(agrupados).forEach(rol => {
                    expanded[rol] = true;
                });
                setExpandedRoles(expanded);
            }
        } catch (error) {
            console.error('Error cargando usuarios:', error);
            toast.error('Error al cargar usuarios');
        } finally {
            setLoading(false);
        }
    };

    const toggleRol = (rolNombre) => {
        setExpandedRoles(prev => ({
            ...prev,
            [rolNombre]: !prev[rolNombre]
        }));
    };

    const filteredUsuariosPorRol = Object.entries(usuariosPorRol).reduce((acc, [rol, usuarios]) => {
        const usuariosFiltrados = usuarios.filter(user =>
            user.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
            user.email.toLowerCase().includes(searchTerm.toLowerCase())
        );
        if (usuariosFiltrados.length > 0) {
            acc[rol] = usuariosFiltrados;
        }
        return acc;
    }, {});

    const handleCambiarRol = async () => {
        if (!selectedRol) {
            toast.error('Selecciona un rol');
            return;
        }

        try {
            const response = await fetch(`/api/admin/usuarios/${editingUser.id}/rol`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ rol_id: selectedRol })
            });

            const data = await response.json();

            if (data.success) {
                toast.success('Rol actualizado correctamente');
                setEditingUser(null);
                setSelectedRol(null);
                cargarUsuarios(); // Recargar lista
            } else {
                toast.error(data.error || 'Error al cambiar rol');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al cambiar rol');
        }
    };

    const handleAbrirPermisosIndividuales = async (user) => {
        try {
            setLoadingPermisos(true);
            setManagingPermisosUser(user);

            // Cargar permisos disponibles y permisos individuales del usuario
            const [permisosRes, userPermisosRes] = await Promise.all([
                fetch('/api/admin/permisos', { credentials: 'include' }),
                fetch(`/api/admin/usuarios/${user.id}/permisos-individuales`, { credentials: 'include' })
            ]);

            const permisosData = await permisosRes.json();
            const userPermisosData = await userPermisosRes.json();

            if (permisosData.success) {
                setPermisosDisponibles(permisosData.permisos || []);
            }

            if (userPermisosData.success) {
                setPermisosIndividuales(userPermisosData.permisos_individuales || []);
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al cargar permisos');
        } finally {
            setLoadingPermisos(false);
        }
    };

    const handleAgregarPermisoIndividual = async (permisoId) => {
        try {
            const response = await fetch(`/api/admin/usuarios/${managingPermisosUser.id}/permisos-individuales/${permisoId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ notas: 'Asignado desde dashboard RBAC' })
            });

            const data = await response.json();

            if (data.success) {
                toast.success('Permiso individual asignado');
                handleAbrirPermisosIndividuales(managingPermisosUser);
                cargarUsuarios();
            } else {
                toast.error(data.error || 'Error al asignar permiso');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al asignar permiso');
        }
    };

    const handleRemoverPermisoIndividual = async (permisoId) => {
        try {
            const response = await fetch(`/api/admin/usuarios/${managingPermisosUser.id}/permisos-individuales/${permisoId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            const data = await response.json();

            if (data.success) {
                toast.success('Permiso individual removido');
                handleAbrirPermisosIndividuales(managingPermisosUser);
                cargarUsuarios();
            } else {
                toast.error(data.error || 'Error al remover permiso');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al remover permiso');
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
        <div className="space-y-6">
            {/* Header con búsqueda */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-gray-900">Usuarios por Rol</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        {Object.values(usuariosPorRol).reduce((sum, users) => sum + users.length, 0)} usuarios en total
                    </p>
                </div>
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Buscar usuario..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                </div>
            </div>

            {/* Lista de roles con usuarios */}
            <div className="space-y-4">
                {Object.entries(filteredUsuariosPorRol).map(([rolNombre, usuarios]) => {
                    const rol = roles.find(r => r.nombre === rolNombre);
                    const isExpanded = expandedRoles[rolNombre];

                    return (
                        <div key={rolNombre} className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
                            {/* Header del rol */}
                            <button
                                onClick={() => toggleRol(rolNombre)}
                                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center gap-4">
                                    <div className="bg-primary/10 p-3 rounded-lg">
                                        <Shield className="h-6 w-6 text-primary" />
                                    </div>
                                    <div className="text-left">
                                        <h3 className="text-lg font-semibold text-gray-900">{rolNombre}</h3>
                                        <div className="flex items-center gap-4 mt-1">
                                            <span className="text-sm text-gray-600">
                                                {usuarios.length} usuario{usuarios.length !== 1 ? 's' : ''}
                                            </span>
                                            {rol && (
                                                <span className="text-sm text-gray-500">
                                                    {rol.permisos_count} permiso{rol.permisos_count !== 1 ? 's' : ''}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {isExpanded ? (
                                    <ChevronUp className="h-5 w-5 text-gray-400" />
                                ) : (
                                    <ChevronDown className="h-5 w-5 text-gray-400" />
                                )}
                            </button>

                            {/* Lista de usuarios */}
                            {isExpanded && (
                                <div className="border-t border-gray-200">
                                    <div className="divide-y divide-gray-100">
                                        {usuarios.map(user => (
                                            <div
                                                key={user.id}
                                                className="px-6 py-4 hover:bg-gray-50 transition-colors"
                                            >
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center gap-4">
                                                        {/* Avatar */}
                                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-semibold">
                                                            {user.nombre.charAt(0).toUpperCase()}
                                                        </div>

                                                        {/* Info del usuario */}
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <h4 className="font-medium text-gray-900">{user.nombre}</h4>
                                                                {user.is_super_admin && (
                                                                    <span className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded">
                                                                        Super Admin
                                                                    </span>
                                                                )}
                                                                {!user.activo && (
                                                                    <span className="bg-gray-100 text-gray-800 text-xs px-2 py-0.5 rounded">
                                                                        Inactivo
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-4 mt-1">
                                                                <div className="flex items-center gap-1 text-sm text-gray-600">
                                                                    <Mail className="h-4 w-4" />
                                                                    {user.email}
                                                                </div>
                                                                {user.departamento && (
                                                                    <span className="text-sm text-gray-500">
                                                                        {user.departamento}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Botón editar y permisos */}
                                                    <div className="flex items-center gap-3">
                                                        {user.permisos && user.permisos.length > 0 && (
                                                            <div className="flex items-center gap-2">
                                                                <Key className="h-4 w-4 text-gray-400" />
                                                                <span className="text-sm text-gray-600">
                                                                    {user.permisos.length === 1 && user.permisos[0] === '*'
                                                                        ? 'Todos los permisos'
                                                                        : `${user.permisos.length} permisos`
                                                                    }
                                                                </span>
                                                            </div>
                                                        )}
                                                        <button
                                                            onClick={() => {
                                                                setEditingUser(user);
                                                                setSelectedRol(user.rol_id);
                                                            }}
                                                            className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                                                            title="Cambiar rol"
                                                        >
                                                            <Edit2 className="h-4 w-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => handleAbrirPermisosIndividuales(user)}
                                                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                                            title="Gestionar permisos individuales"
                                                        >
                                                            <Plus className="h-4 w-4" />
                                                        </button>
                                                    </div>
                                                </div>

                                                {/* Mostrar permisos específicos si no es super-admin */}
                                                {user.permisos && user.permisos.length > 0 && user.permisos[0] !== '*' && (
                                                    <div className="mt-3 flex flex-wrap gap-1">
                                                        {user.permisos.slice(0, 10).map((permiso, idx) => (
                                                            <span
                                                                key={idx}
                                                                className="bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded font-mono"
                                                            >
                                                                {permiso}
                                                            </span>
                                                        ))}
                                                        {user.permisos.length > 10 && (
                                                            <span className="text-xs text-gray-500 px-2 py-1">
                                                                +{user.permisos.length - 10} más
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Mensaje si no hay resultados */}
            {Object.keys(filteredUsuariosPorRol).length === 0 && (
                <div className="text-center py-12">
                    <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                        No se encontraron usuarios
                    </h3>
                    <p className="text-gray-600">
                        {searchTerm
                            ? 'Intenta con otro término de búsqueda'
                            : 'No hay usuarios asignados a roles'
                        }
                    </p>
                </div>
            )}

            {/* Modal Cambiar Rol */}
            {editingUser && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
                        <h2 className="text-xl font-bold mb-4">
                            Cambiar Rol de Usuario
                        </h2>

                        <div className="space-y-4">
                            {/* Info del usuario */}
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-semibold">
                                        {editingUser.nombre.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900 text-sm">{editingUser.nombre}</h3>
                                        <p className="text-xs text-gray-600">{editingUser.email}</p>
                                    </div>
                                </div>
                            </div>

                            {/* Selector de rol */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Nuevo Rol
                                </label>
                                <select
                                    value={selectedRol || ''}
                                    onChange={(e) => setSelectedRol(parseInt(e.target.value))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                                >
                                    <option value="">Selecciona un rol...</option>
                                    {roles.map(rol => (
                                        <option key={rol.id} value={rol.id}>
                                            {rol.nombre} ({rol.permisos_count} permisos)
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">
                                    Rol actual: <span className="font-medium">{editingUser.rol_nombre || 'Sin rol'}</span>
                                </p>
                            </div>

                            {/* Advertencia si es super-admin */}
                            {editingUser.is_super_admin && (
                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                                    <p className="text-xs text-yellow-800">
                                        ⚠️ Este usuario es <strong>Super Admin</strong>. Cambiar su rol eliminará sus privilegios de super-administrador.
                                    </p>
                                </div>
                            )}
                        </div>

                        {/* Botones - Siempre visibles */}
                        <div className="flex gap-2 mt-6 pt-4 border-t border-gray-200">
                            <button
                                onClick={handleCambiarRol}
                                className="flex-1 bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark flex items-center justify-center gap-2 font-medium"
                            >
                                <Save className="h-5 w-5" />
                                Guardar Cambios
                            </button>
                            <button
                                onClick={() => {
                                    setEditingUser(null);
                                    setSelectedRol(null);
                                }}
                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center justify-center"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Gestionar Permisos Individuales */}
            {managingPermisosUser && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-bold">
                                Permisos Individuales: {managingPermisosUser.nombre}
                            </h2>
                            <button
                                onClick={() => {
                                    setManagingPermisosUser(null);
                                    setPermisosIndividuales([]);
                                    setPermisosDisponibles([]);
                                }}
                                className="p-2 hover:bg-gray-100 rounded-lg"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>

                        {loadingPermisos ? (
                            <div className="flex items-center justify-center py-12">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {/* Permisos del Rol */}
                                {managingPermisosUser.rol_nombre && (
                                    <div>
                                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                                            <Shield className="h-5 w-5 text-primary" />
                                            Permisos del Rol: {managingPermisosUser.rol_nombre}
                                        </h3>
                                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                            <div className="flex flex-wrap gap-2">
                                                {managingPermisosUser.permisos && managingPermisosUser.permisos.length > 0 ? (
                                                    managingPermisosUser.permisos[0] === '*' ? (
                                                        <span className="bg-blue-600 text-white px-3 py-1 rounded-lg text-sm font-medium">
                                                            ⭐ Todos los permisos (Super Admin)
                                                        </span>
                                                    ) : (
                                                        permisosDisponibles
                                                            .filter(p => managingPermisosUser.permisos.includes(p.codigo))
                                                            .map(permiso => (
                                                                <span key={permiso.id} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-lg text-sm font-mono">
                                                                    {permiso.codigo}
                                                                </span>
                                                            ))
                                                    )
                                                ) : (
                                                    <span className="text-blue-700 text-sm">Sin permisos de rol</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Permisos individuales asignados */}
                                <div>
                                    <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                                        <Plus className="h-5 w-5 text-green-600" />
                                        Permisos Adicionales Individuales
                                    </h3>
                                    {permisosIndividuales.length > 0 ? (
                                        <div className="space-y-2">
                                            {permisosIndividuales.map(permiso => (
                                                <div key={permiso.id} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg">
                                                    <div>
                                                        <p className="font-medium text-gray-900">{permiso.permiso_nombre}</p>
                                                        <p className="text-sm text-gray-600 font-mono">{permiso.permiso_codigo}</p>
                                                        {permiso.notas && (
                                                            <p className="text-xs text-gray-500 mt-1">{permiso.notas}</p>
                                                        )}
                                                    </div>
                                                    <button
                                                        onClick={() => handleRemoverPermisoIndividual(permiso.permiso_id)}
                                                        className="p-2 text-red-600 hover:bg-red-100 rounded-lg"
                                                        title="Remover permiso"
                                                    >
                                                        <Trash2 className="h-4 w-4" />
                                                    </button>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p className="text-gray-500 text-sm bg-gray-50 p-3 rounded-lg">No tiene permisos individuales asignados</p>
                                    )}
                                </div>

                                {/* Agregar nuevos permisos */}
                                <div>
                                    <h3 className="text-lg font-semibold mb-3">Agregar Permiso Individual</h3>
                                    <p className="text-sm text-gray-600 mb-3">
                                        Solo se muestran permisos que no tiene asignados por su rol
                                    </p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto border border-gray-200 rounded-lg p-3">
                                        {permisosDisponibles
                                            .filter(p => {
                                                // Excluir permisos ya asignados individualmente
                                                const yaAsignadoIndividual = permisosIndividuales.some(pi => pi.permiso_id === p.id);
                                                // Excluir permisos del rol
                                                const yaEnRol = managingPermisosUser.permisos &&
                                                    (managingPermisosUser.permisos[0] === '*' || managingPermisosUser.permisos.includes(p.codigo));
                                                return !yaAsignadoIndividual && !yaEnRol;
                                            })
                                            .map(permiso => (
                                                <button
                                                    key={permiso.id}
                                                    onClick={() => handleAgregarPermisoIndividual(permiso.id)}
                                                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors text-left"
                                                >
                                                    <div>
                                                        <p className="font-medium text-sm text-gray-900">{permiso.nombre}</p>
                                                        <p className="text-xs text-gray-600 font-mono">{permiso.codigo}</p>
                                                    </div>
                                                    <Plus className="h-4 w-4 text-blue-600" />
                                                </button>
                                            ))}
                                        {permisosDisponibles.filter(p => {
                                            const yaAsignadoIndividual = permisosIndividuales.some(pi => pi.permiso_id === p.id);
                                            const yaEnRol = managingPermisosUser.permisos &&
                                                (managingPermisosUser.permisos[0] === '*' || managingPermisosUser.permisos.includes(p.codigo));
                                            return !yaAsignadoIndividual && !yaEnRol;
                                        }).length === 0 && (
                                                <p className="col-span-2 text-center text-gray-500 text-sm py-4">
                                                    No hay permisos adicionales disponibles
                                                </p>
                                            )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
