import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    X, Shield, Building2, LayoutGrid, Save, Loader2,
    Search, CheckCircle2, ChevronRight
} from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../AuthContext';

export default function GestionAccesosModal({ user, onClose, onSave }) {
    const { user: currentUser } = useAuth();
    const esInvitado = currentUser?.departamento === 'Invitado';
    const esAdminGrupo = esInvitado && currentUser?.managed_group_ids?.length > 0;

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [empresas, setEmpresas] = useState([]);
    const [grupos, setGrupos] = useState([]);
    const [selectedEmpresas, setSelectedEmpresas] = useState([]);
    const [selectedGrupos, setSelectedGrupos] = useState([]);
    const [gruposAdmin, setGruposAdmin] = useState({}); // {grupoId: boolean}
    const [searchEmpresa, setSearchEmpresa] = useState('');
    const [searchGrupo, setSearchGrupo] = useState('');

    useEffect(() => {
        fetchData();
    }, [user.id]);

    const fetchData = async () => {
        try {
            setLoading(true);
            // 1. Cargar lista completa de empresas y grupos de la gestoría
            const [empRes, grpRes, userAccRes] = await Promise.all([
                axios.get('/api/empresas/lista-simple'),
                axios.get('/api/grupos-empresas'),
                axios.get(`/api/admin/users/${user.id}/access`)
            ]);

            setEmpresas(empRes.data.empresas || []);
            setGrupos(grpRes.data.grupos || []);

            // 2. Marcar los que ya tiene asignados
            setSelectedEmpresas(userAccRes.data.empresas.map(e => e.id));

            const gruposAsignados = userAccRes.data.grupos || [];
            setSelectedGrupos(gruposAsignados.map(g => g.id));

            const adminMapping = {};
            gruposAsignados.forEach(g => {
                adminMapping[g.id] = g.es_admin_grupo;
            });
            setGruposAdmin(adminMapping);
        } catch (err) {
            toast.error("Error al cargar datos de acceso");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await axios.post(`/api/admin/users/${user.id}/access`, {
                empresa_ids: selectedEmpresas,
                grupos: selectedGrupos.map(id => ({
                    id,
                    es_admin_grupo: !!gruposAdmin[id]
                }))
            });
            toast.success("Accesos actualizados correctamente");
            onSave();
            onClose();
        } catch (err) {
            toast.error("Error al guardar accesos");
        } finally {
            setSaving(false);
        }
    };

    const toggleEmpresa = (id) => {
        setSelectedEmpresas(prev =>
            prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]
        );
    };

    const toggleGrupo = (id) => {
        setSelectedGrupos(prev => {
            if (prev.includes(id)) {
                // Si quitamos el grupo, también quitamos su status de admin
                const newAdminMapping = { ...gruposAdmin };
                delete newAdminMapping[id];
                setGruposAdmin(newAdminMapping);
                return prev.filter(g => g !== id);
            } else {
                return [...prev, id];
            }
        });
    };

    const toggleAdminGrupo = (e, id) => {
        e.stopPropagation(); // No activar el toggle del grupo
        setGruposAdmin(prev => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    const filteredEmpresas = empresas.filter(e =>
        e.nombre.toLowerCase().includes(searchEmpresa.toLowerCase()) ||
        e.nif.toLowerCase().includes(searchEmpresa.toLowerCase())
    );

    const filteredGrupos = grupos.filter(g =>
        g.nombre.toLowerCase().includes(searchGrupo.toLowerCase())
    );

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl p-8 flex flex-col items-center gap-4 shadow-2xl">
                    <Loader2 className="w-10 h-10 text-blue-600 animate-spin" />
                    <p className="text-gray-600 font-medium">Cargando catálogo de accesos...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-md z-50 flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col border border-white/20 animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 rounded-t-2xl">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-blue-600 rounded-xl shadow-lg shadow-blue-200">
                            <Shield className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Configurar Accesos</h2>
                            <p className="text-gray-500 text-sm">Usuario: <span className="font-semibold text-blue-600">{user.nombre}</span></p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                        <X className="w-6 h-6 text-gray-400" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-2 gap-8 bg-gray-50/30">

                    {/* Seccion Grupos (Holdings) */}
                    {(!esAdminGrupo || true) && ( // Siempre mostrar, pero el backend filtrará los grupos que ve
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                                    <LayoutGrid className="w-5 h-5 text-purple-600" />
                                    Grupos / Holdings
                                </h3>
                                <span className="text-xs bg-purple-100 text-purple-700 font-bold px-2 py-1 rounded-full">
                                    {selectedGrupos.length} seleccionados
                                </span>
                            </div>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Buscar grupo..."
                                    className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                                    value={searchGrupo}
                                    onChange={e => setSearchGrupo(e.target.value)}
                                />
                            </div>
                            <div className="bg-white border border-gray-100 rounded-xl max-h-[400px] overflow-y-auto shadow-inner p-2 space-y-1">
                                {filteredGrupos.length === 0 ? (
                                    <p className="text-center py-8 text-gray-400 text-sm italic">No se encontraron grupos</p>
                                ) : filteredGrupos.map(g => (
                                    <button
                                        key={g.id}
                                        onClick={() => toggleGrupo(g.id)}
                                        className={`w-full text-left p-3 rounded-xl transition flex items-center justify-between group ${selectedGrupos.includes(g.id)
                                            ? 'bg-purple-50 border-purple-200 text-purple-900'
                                            : 'hover:bg-gray-50 text-gray-700'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg ${selectedGrupos.includes(g.id) ? 'bg-purple-200' : 'bg-gray-100'}`}>
                                                <LayoutGrid className={`w-4 h-4 ${selectedGrupos.includes(g.id) ? 'text-purple-700' : 'text-gray-400'}`} />
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="font-medium text-sm">{g.nombre}</span>
                                                {selectedGrupos.includes(g.id) && (
                                                    <button
                                                        onClick={(e) => toggleAdminGrupo(e, g.id)}
                                                        className={`mt-1 text-[10px] uppercase font-bold px-2 py-0.5 rounded flex items-center gap-1 transition-colors ${gruposAdmin[g.id]
                                                            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                                                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                                                            }`}
                                                    >
                                                        <Shield className="w-3 h-3" />
                                                        {gruposAdmin[g.id] ? 'Administrador' : 'Hacer Administrador'}
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                        {selectedGrupos.includes(g.id) && <CheckCircle2 className="w-5 h-5 text-purple-600" />}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Seccion Empresas Individuales */}
                    <div className={`space-y-4 ${esAdminGrupo ? 'md:col-span-2' : ''}`}>
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                                <Building2 className="w-5 h-5 text-blue-600" />
                                Empresas Específicas
                            </h3>
                            <span className="text-xs bg-blue-100 text-blue-700 font-bold px-2 py-1 rounded-full">
                                {selectedEmpresas.length} seleccionadas
                            </span>
                        </div>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Buscar por nombre o NIF..."
                                className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                                value={searchEmpresa}
                                onChange={e => setSearchEmpresa(e.target.value)}
                            />
                        </div>
                        <div className="bg-white border border-gray-100 rounded-xl max-h-[400px] overflow-y-auto shadow-inner p-2 space-y-1">
                            {filteredEmpresas.length === 0 ? (
                                <p className="text-center py-8 text-gray-400 text-sm italic">No se encontraron empresas</p>
                            ) : filteredEmpresas.map(e => (
                                <button
                                    key={e.id}
                                    onClick={() => toggleEmpresa(e.id)}
                                    className={`w-full text-left p-3 rounded-xl transition flex items-center justify-between group ${selectedEmpresas.includes(e.id)
                                        ? 'bg-blue-50 border-blue-200 text-blue-900'
                                        : 'hover:bg-gray-50 text-gray-700'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg ${selectedEmpresas.includes(e.id) ? 'bg-blue-200' : 'bg-gray-100'}`}>
                                            <Building2 className={`w-4 h-4 ${selectedEmpresas.includes(e.id) ? 'text-blue-700' : 'text-gray-400'}`} />
                                        </div>
                                        <div>
                                            <p className="font-medium text-sm">{e.nombre}</p>
                                            <p className="text-xs text-gray-400 font-mono uppercase">{e.nif}</p>
                                        </div>
                                    </div>
                                    {selectedEmpresas.includes(e.id) && <CheckCircle2 className="w-5 h-5 text-blue-600" />}
                                </button>
                            ))}
                        </div>
                    </div>

                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 flex items-center justify-between bg-white rounded-b-2xl shadow-xl">
                    <div className="text-sm text-gray-500 italic max-w-md">
                        Nota: Al asignar un Grupo, el usuario tendrá acceso a todas las empresas que pertenezcan a dicho grupo automáticamente.
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="px-6 py-2.5 text-gray-700 font-bold hover:bg-gray-100 rounded-xl transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-8 py-2.5 bg-blue-600 text-white font-bold rounded-xl shadow-lg shadow-blue-200 hover:bg-blue-700 transition-all flex items-center gap-2 transform active:scale-95 disabled:opacity-50"
                        >
                            {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                            Guardar Cambios
                        </button>
                    </div>
                </div>
            </div>
        </div >
    );
}
