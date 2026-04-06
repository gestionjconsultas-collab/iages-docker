import React, { useState, useEffect } from 'react';
import { Check, X, Loader } from 'lucide-react';
import toast from 'react-hot-toast';

export default function MatrizPermisos({ roles, permisos, onReload }) {
    const [matrizData, setMatrizData] = useState({});
    const [loading, setLoading] = useState(true);
    const [filtroModulo, setFiltroModulo] = useState('todos');

    useEffect(() => {
        cargarMatriz();
    }, [roles]);

    const cargarMatriz = async () => {
        try {
            setLoading(true);
            const data = {};

            // Cargar permisos para cada rol
            for (const rol of roles) {
                const response = await fetch(`/api/admin/roles/${rol.id}/permisos`, {
                    credentials: 'include'
                });
                const result = await response.json();
                if (result.success) {
                    data[rol.id] = result.permisos.map(p => p.id);
                }
            }

            setMatrizData(data);
        } catch (error) {
            console.error('Error cargando matriz:', error);
            toast.error('Error al cargar matriz de permisos');
        } finally {
            setLoading(false);
        }
    };

    const togglePermiso = async (rolId, permisoId, tienePermiso) => {
        try {
            const url = `/api/admin/roles/${rolId}/permisos/${permisoId}`;
            const method = tienePermiso ? 'DELETE' : 'POST';

            const response = await fetch(url, {
                method,
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.success) {
                // Actualizar estado local
                setMatrizData(prev => ({
                    ...prev,
                    [rolId]: tienePermiso
                        ? prev[rolId].filter(id => id !== permisoId)
                        : [...(prev[rolId] || []), permisoId]
                }));
                toast.success(tienePermiso ? 'Permiso removido' : 'Permiso asignado');
                onReload();
            } else {
                toast.error(data.error || 'Error al actualizar permiso');
            }
        } catch (error) {
            console.error('Error:', error);
            toast.error('Error al actualizar permiso');
        }
    };

    // Obtener módulos únicos
    const modulos = ['todos', ...new Set(permisos.map(p => p.modulo).filter(Boolean))];

    // Filtrar permisos por módulo
    const permisosFiltrados = filtroModulo === 'todos'
        ? permisos
        : permisos.filter(p => p.modulo === filtroModulo);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader className="animate-spin h-8 w-8 text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Filtro por módulo */}
            <div className="flex items-center gap-2 mb-4">
                <label className="text-sm font-medium text-gray-700">Filtrar por módulo:</label>
                <select
                    value={filtroModulo}
                    onChange={(e) => setFiltroModulo(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                >
                    {modulos.map(modulo => (
                        <option key={modulo} value={modulo}>
                            {modulo === 'todos' ? 'Todos los módulos' : modulo.charAt(0).toUpperCase() + modulo.slice(1)}
                        </option>
                    ))}
                </select>
                <span className="text-sm text-gray-500">
                    ({permisosFiltrados.length} permisos)
                </span>
            </div>

            {/* Matriz */}
            <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="min-w-full">
                    <thead className="bg-gradient-to-r from-primary to-secondary">
                        <tr>
                            <th className="sticky left-0 bg-primary z-10 px-6 py-4 text-left text-sm font-semibold text-black">
                                Rol / Permiso
                            </th>
                            {permisosFiltrados.map(permiso => (
                                <th
                                    key={permiso.id}
                                    className="px-3 py-4 text-center min-w-[180px] max-w-[180px]"
                                    title={`${permiso.nombre} - ${permiso.descripcion}`}
                                >
                                    <div className="flex flex-col items-center gap-2">
                                        <span className="text-sm font-semibold text-black leading-tight">
                                            {permiso.nombre}
                                        </span>
                                        <span className="text-xs text-black/90 font-mono bg-black/10 px-2 py-1 rounded">
                                            {permiso.codigo}
                                        </span>
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {roles.map((rol, idx) => (
                            <tr
                                key={rol.id}
                                className={`hover:bg-gray-50 transition-colors ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                                    }`}
                            >
                                <td className="sticky left-0 bg-inherit z-10 px-6 py-4 border-r border-gray-200">
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1">
                                            <div className="font-semibold text-gray-900">{rol.nombre}</div>
                                            <div className="text-xs text-gray-500">{rol.descripcion}</div>
                                        </div>
                                        {rol.es_sistema && (
                                            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded">
                                                Sistema
                                            </span>
                                        )}
                                    </div>
                                </td>
                                {permisosFiltrados.map(permiso => {
                                    const tienePermiso = matrizData[rol.id]?.includes(permiso.id);
                                    const esEditable = !rol.es_sistema;

                                    return (
                                        <td
                                            key={permiso.id}
                                            className="px-4 py-4 text-center border-l border-gray-100"
                                        >
                                            <div className="flex justify-center">
                                                <button
                                                    onClick={() => esEditable && togglePermiso(rol.id, permiso.id, tienePermiso)}
                                                    disabled={!esEditable}
                                                    className={`
                                                        relative group
                                                        w-10 h-10 rounded-lg
                                                        flex items-center justify-center
                                                        transition-all duration-200
                                                        ${tienePermiso
                                                            ? 'bg-gradient-to-br from-green-400 to-green-600 shadow-lg shadow-green-500/30'
                                                            : 'bg-gray-200 hover:bg-gray-300'
                                                        }
                                                        ${esEditable ? 'cursor-pointer hover:scale-110' : 'cursor-not-allowed opacity-60'}
                                                    `}
                                                    title={`${rol.nombre} - ${permiso.nombre}: ${tienePermiso ? 'Tiene permiso' : 'No tiene permiso'}`}
                                                >
                                                    {tienePermiso ? (
                                                        <Check className="h-5 w-5 text-white" strokeWidth={3} />
                                                    ) : (
                                                        <X className="h-5 w-5 text-gray-400" strokeWidth={2} />
                                                    )}

                                                    {/* Tooltip on hover */}
                                                    {esEditable && (
                                                        <div className="absolute bottom-full mb-2 hidden group-hover:block z-20">
                                                            <div className="bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
                                                                {tienePermiso ? 'Click para remover' : 'Click para asignar'}
                                                            </div>
                                                        </div>
                                                    )}
                                                </button>
                                            </div>
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Leyenda */}
            <div className="flex items-center gap-6 text-sm text-gray-600 bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center">
                        <Check className="h-4 w-4 text-white" />
                    </div>
                    <span>Permiso asignado</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-gray-200 flex items-center justify-center">
                        <X className="h-4 w-4 text-gray-400" />
                    </div>
                    <span>Permiso no asignado</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded">
                        Sistema
                    </span>
                    <span>Roles del sistema (no editables)</span>
                </div>
            </div>

            {/* Estadísticas */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {roles.map(rol => {
                    const permisosAsignados = matrizData[rol.id]?.length || 0;
                    const porcentaje = Math.round((permisosAsignados / permisos.length) * 100);

                    return (
                        <div key={rol.id} className="bg-white rounded-lg shadow p-4 border border-gray-200">
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-semibold text-gray-900">{rol.nombre}</h4>
                                <span className="text-2xl font-bold text-primary">{porcentaje}%</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                                <div
                                    className="bg-gradient-to-r from-primary to-secondary h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${porcentaje}%` }}
                                />
                            </div>
                            <p className="text-xs text-gray-500">
                                {permisosAsignados} de {permisos.length} permisos
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
