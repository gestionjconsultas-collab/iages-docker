import React, { useState } from 'react';
import { useGrupos, useCrearGrupo, useActualizarGrupo, useEliminarGrupo, useAsignarEmpresas, useImportarGruposExcel, descargarPlantillaGrupos } from '../hooks/useGruposEmpresas';
import { useEmpresasListadoSimple } from '../hooks/useEmpresas';
import {
    Users, Plus, Search, Edit2, Trash2, ChevronRight,
    Building2, Mail, Info, ExternalLink, Filter, X, CheckCircle2
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import ConfirmModal from './ConfirmModal';

export default function GruposEmpresasView() {
    const { data: grupos, isLoading: isLoadingGrupos } = useGrupos();
    const { data: todasEmpresas } = useEmpresasListadoSimple();

    const crearGrupoMutation = useCrearGrupo();
    const actualizarGrupoMutation = useActualizarGrupo();
    const eliminarGrupoMutation = useEliminarGrupo();
    const asignarEmpresasMutation = useAsignarEmpresas();

    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingGrupo, setEditingGrupo] = useState(null);
    const [showAssignModal, setShowAssignModal] = useState(null);
    const [selectedEmpresas, setSelectedEmpresas] = useState([]);
    const [assignSearchTerm, setAssignSearchTerm] = useState('');
    const [showConfirmDelete, setShowConfirmDelete] = useState(false);
    const [grupoToDelete, setGrupoToDelete] = useState(null);
    const [isImporting, setIsImporting] = useState(false);
    
    const importMutation = useImportarGruposExcel();
    const fileInputRef = React.useRef(null);

    // Form state
    const [formData, setFormData] = useState({
        nombre: '',
        descripcion: '',
        email_notificaciones: '',
        usar_email_grupo: false
    });

    const handleOpenModal = (grupo = null) => {
        if (grupo) {
            setEditingGrupo(grupo);
            setFormData({
                nombre: grupo.nombre,
                descripcion: grupo.descripcion || '',
                email_notificaciones: grupo.email_notificaciones || '',
                usar_email_grupo: grupo.usar_email_grupo || false
            });
        } else {
            setEditingGrupo(null);
            setFormData({
                nombre: '',
                descripcion: '',
                email_notificaciones: '',
                usar_email_grupo: false
            });
        }
        setShowModal(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (editingGrupo) {
            await actualizarGrupoMutation.mutateAsync({ id: editingGrupo.id, ...formData });
        } else {
            await crearGrupoMutation.mutateAsync(formData);
        }
        setShowModal(false);
    };

    const handleDelete = (id) => {
        setGrupoToDelete(id);
        setShowConfirmDelete(true);
    };

    const confirmDelete = () => {
        if (grupoToDelete) {
            eliminarGrupoMutation.mutate(grupoToDelete);
            setGrupoToDelete(null);
        }
    };

    const handleOpenAssign = (grupo) => {
        setShowAssignModal(grupo);
        setAssignSearchTerm('');
        // Pre-seleccionar empresas que ya están en el grupo
        const yaAsignadas = todasEmpresas?.filter(e => e.grupo_id === grupo.id).map(e => e.id) || [];
        setSelectedEmpresas(yaAsignadas);
    };

    const handleFileImport = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsImporting(true);
        try {
            await importMutation.mutateAsync(file);
            if (fileInputRef.current) fileInputRef.current.value = '';
        } catch (error) {
            console.error('Error importing groups:', error);
        } finally {
            setIsImporting(false);
        }
    };

    const handleSaveAssignment = async () => {
        await asignarEmpresasMutation.mutateAsync({
            id: showAssignModal.id,
            empresa_ids: selectedEmpresas
        });
        setShowAssignModal(null);
    };

    const filteredGrupos = grupos?.filter(g =>
        g.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
        g.descripcion?.toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

    if (isLoadingGrupos) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-7xl mx-auto animate-fade-in">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Users className="text-orange-500" />
                        Agrupaciones de Empresas
                    </h1>
                    <p className="text-gray-500 text-sm mt-1">
                        Gestiona tus holdings y grupos empresariales para centralizar notificaciones y reportes.
                    </p>
                    <div className="mt-3 inline-flex items-center gap-2 bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg text-xs font-semibold border border-blue-100">
                        <Info size={14} className="text-blue-500" />
                        Contraseña temporal clientes importados: <span className="font-bold tracking-wider select-all">Iages2026*</span>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => descargarPlantillaGrupos()}
                        className="hidden md:flex items-center gap-2 text-gray-600 hover:text-orange-600 px-4 py-2.5 rounded-xl transition-all border border-gray-100 hover:border-orange-100 bg-white"
                        title="Descargar Plantilla Excel"
                    >
                        <Mail size={18} className="rotate-12" />
                        Descargar Plantilla
                    </button>
                    
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={isImporting}
                        className="flex items-center gap-2 bg-white hover:bg-gray-50 text-gray-700 px-4 py-2.5 rounded-xl transition-all border border-gray-200 shadow-sm active:scale-95 disabled:opacity-50"
                    >
                        <Search size={20} className="text-gray-400" />
                        {isImporting ? 'Importando...' : 'Importar Excel'}
                    </button>
                    
                    <input
                        type="file"
                        ref={fileInputRef}
                        className="hidden"
                        accept=".xlsx,.xls,.csv"
                        onChange={handleFileImport}
                    />

                    <button
                        onClick={() => handleOpenModal()}
                        className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-4 py-2.5 rounded-xl transition-all shadow-md active:scale-95"
                    >
                        <Plus size={20} />
                        Nueva Agrupación
                    </button>
                </div>
            </div>

            {/* Search & Stats */}
            <div className="bg-white p-4 rounded-2xl shadow-xs border border-gray-100 mb-6 flex flex-col md:flex-row gap-4 items-center">
                <div className="relative flex-1 w-full">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                        type="text"
                        placeholder="Buscar por nombre o descripción..."
                        className="w-full pl-10 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-2 focus:ring-orange-500/20 text-sm transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span className="bg-orange-50 text-orange-600 px-3 py-1 rounded-full font-medium">
                        {grupos?.length || 0} Grupos
                    </span>
                    <span className="bg-blue-50 text-blue-600 px-3 py-1 rounded-full font-medium">
                        {grupos?.reduce((acc, g) => acc + g.num_empresas, 0)} Empresas agrupadas
                    </span>
                </div>
            </div>

            {/* Grid de Grupos */}
            {filteredGrupos.length === 0 ? (
                <div className="text-center py-20 bg-white rounded-3xl border-2 border-dashed border-gray-100">
                    <div className="bg-gray-50 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Users size={32} className="text-gray-300" />
                    </div>
                    <h3 className="text-gray-900 font-semibold mb-1">No hay agrupaciones</h3>
                    <p className="text-gray-500 text-sm mb-6">Comienza creando tu primer grupo de empresas para organizar mejor tu trabajo.</p>
                    <button
                        onClick={() => handleOpenModal()}
                        className="text-orange-500 font-medium hover:underline flex items-center gap-1 mx-auto"
                    >
                        Crear mi primer grupo <ChevronRight size={16} />
                    </button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredGrupos.map(grupo => (
                        <div
                            key={grupo.id}
                            className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-all group overflow-hidden"
                        >
                            {/* Card Content */}
                            <div className="p-5">
                                <div className="flex justify-between items-start mb-4">
                                    <div className="bg-orange-50 p-2.5 rounded-xl group-hover:bg-orange-100 transition-colors">
                                        <Building2 className="text-orange-600" size={24} />
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => handleOpenModal(grupo)}
                                            className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-blue-600 transition-colors"
                                            title="Editar"
                                        >
                                            <Edit2 size={16} />
                                        </button>
                                        <button
                                            onClick={() => handleDelete(grupo.id)}
                                            className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-red-600 transition-colors"
                                            title="Eliminar"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                </div>

                                <h3 className="font-bold text-gray-900 text-lg mb-1">{grupo.nombre}</h3>
                                {grupo.descripcion && (
                                    <p className="text-gray-500 text-xs mb-4 line-clamp-2 leading-relaxed">
                                        {grupo.descripcion}
                                    </p>
                                )}

                                {/* Tags/Stats */}
                                <div className="flex flex-wrap gap-2 mb-6">
                                    <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 rounded-lg text-xs font-medium text-gray-600 border border-gray-100">
                                        <Building2 size={14} />
                                        {grupo.num_empresas} Empresas
                                    </div>
                                    {grupo.usar_email_grupo && (
                                        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 rounded-lg text-xs font-medium text-green-600 border border-green-100">
                                            <Mail size={14} />
                                            Email Centralizado
                                        </div>
                                    )}
                                </div>

                                {/* Actions Bottom */}
                                <div className="pt-4 border-t border-gray-50 flex items-center justify-between">
                                    <div className="flex flex-col">
                                        <span className="text-[10px] text-gray-400 uppercase tracking-wider font-bold">Email de Grupo</span>
                                        <span className="text-sm font-medium text-gray-700 truncate max-w-[150px]">
                                            {grupo.email_notificaciones || 'No configurado'}
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => handleOpenAssign(grupo)}
                                        className="text-xs font-bold text-orange-600 hover:text-orange-700 bg-orange-50 hover:bg-orange-100 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
                                    >
                                        Gestionar Empresas
                                        <ExternalLink size={12} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Modal de Creación/Edición */}
            {showModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden animate-scale-in">
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                {editingGrupo ? <Edit2 size={20} className="text-orange-500" /> : <Plus size={20} className="text-orange-500" />}
                                {editingGrupo ? 'Editar Agrupación' : 'Nueva Agrupación'}
                            </h2>
                            <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                                <X size={20} className="text-gray-500" />
                            </button>
                        </div>

                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            <div>
                                <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Nombre de la Agrupación</label>
                                <input
                                    type="text"
                                    required
                                    className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all font-medium"
                                    placeholder="Ej: Grupo Martínez, Holding Inversiones, etc."
                                    value={formData.nombre}
                                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Descripción (Opcional)</label>
                                <textarea
                                    className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm min-h-[100px]"
                                    placeholder="Describe brevemente el propósito de este grupo..."
                                    value={formData.descripcion}
                                    onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                                />
                            </div>

                            <div className="p-4 bg-blue-50/50 rounded-2xl border border-blue-100">
                                <h4 className="text-sm font-bold text-blue-800 flex items-center gap-2 mb-3">
                                    <Mail size={16} /> Configuración de Notificaciones
                                </h4>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-bold text-blue-700 mb-1.5">Email del Grupo</label>
                                        <input
                                            type="email"
                                            className="w-full px-4 py-2 bg-white border-blue-200 border rounded-xl focus:ring-2 focus:ring-blue-500/20 text-sm"
                                            placeholder="email@delgrupo.com"
                                            value={formData.email_notificaciones}
                                            onChange={(e) => setFormData({ ...formData, email_notificaciones: e.target.value })}
                                        />
                                    </div>

                                    <label className="flex items-center gap-3 cursor-pointer group">
                                        <div className="relative">
                                            <input
                                                type="checkbox"
                                                className="sr-only peer"
                                                checked={formData.usar_email_grupo}
                                                onChange={(e) => setFormData({ ...formData, usar_email_grupo: e.target.checked })}
                                            />
                                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
                                        </div>
                                        <span className="text-sm font-medium text-gray-700 group-hover:text-orange-600 transition-colors">
                                            Usar este email para todas las notificaciones del grupo
                                        </span>
                                    </label>
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 py-3 text-sm font-bold text-gray-500 hover:bg-gray-100 rounded-2xl transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 py-3 text-sm font-bold text-white bg-orange-500 hover:bg-orange-600 rounded-2xl transition-all shadow-lg active:scale-95"
                                >
                                    {editingGrupo ? 'Guardar Cambios' : 'Crear Agrupación'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Modal de Asignación de Empresas */}
            {showAssignModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden animate-scale-in flex flex-col max-h-[90vh]">
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                    <Building2 size={20} className="text-orange-500" />
                                    Asignar Empresas
                                </h2>
                                <p className="text-xs text-gray-500 mt-0.5">Selecciona las empresas que pertenecen a <b>{showAssignModal.nombre}</b></p>
                            </div>
                            <button onClick={() => setShowAssignModal(null)} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                                <X size={20} className="text-gray-500" />
                            </button>
                        </div>

                        <div className="px-6 py-4 border-b border-gray-100 bg-white">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                                <input
                                    type="text"
                                    placeholder="Buscar empresa por nombre o NIF..."
                                    className="w-full pl-9 pr-4 py-2 bg-gray-50 border-none rounded-xl focus:ring-2 focus:ring-orange-500/20 text-sm"
                                    value={assignSearchTerm}
                                    onChange={(e) => setAssignSearchTerm(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="p-6 overflow-y-auto custom-scrollbar">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {todasEmpresas?.filter(e =>
                                    e.nombre.toLowerCase().includes(assignSearchTerm.toLowerCase()) ||
                                    e.nif?.toLowerCase().includes(assignSearchTerm.toLowerCase())
                                ).map(empresa => {
                                    const isSelected = selectedEmpresas.includes(empresa.id);
                                    const isOtherGroup = empresa.grupo_id && empresa.grupo_id !== showAssignModal.id;

                                    return (
                                        <div
                                            key={empresa.id}
                                            onClick={() => {
                                                if (isSelected) {
                                                    setSelectedEmpresas(selectedEmpresas.filter(id => id !== empresa.id));
                                                } else {
                                                    setSelectedEmpresas([...selectedEmpresas, empresa.id]);
                                                }
                                            }}
                                            className={`p-4 rounded-2xl border transition-all cursor-pointer flex items-center gap-3 ${isSelected
                                                ? 'bg-orange-50 border-orange-200 ring-2 ring-orange-500/10'
                                                : 'bg-white border-gray-100 hover:border-orange-200'
                                                }`}
                                        >
                                            <div className={`p-2 rounded-lg ${isSelected ? 'bg-orange-500 text-white' : 'bg-gray-100 text-gray-400'}`}>
                                                {isSelected ? <CheckCircle2 size={16} /> : <Building2 size={16} />}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-bold text-gray-900 truncate">{empresa.nombre}</p>
                                                <p className="text-[10px] text-gray-500 font-medium">NIF: {empresa.nif}</p>
                                                {isOtherGroup && (
                                                    <span className="text-[9px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded mt-1 inline-block font-bold">
                                                        ⚠️ Ya en otro grupo
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="p-6 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                            <span className="text-sm font-semibold text-gray-600">
                                {selectedEmpresas.length} seleccionadas
                            </span>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setShowAssignModal(null)}
                                    className="px-6 py-2.5 text-sm font-bold text-gray-500 hover:bg-gray-200 rounded-xl transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    onClick={handleSaveAssignment}
                                    className="px-6 py-2.5 text-sm font-bold text-white bg-orange-500 hover:bg-orange-600 rounded-xl transition-all shadow-md active:scale-95"
                                >
                                    Guardar Cambios
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Confirmación de Eliminación */}
            <ConfirmModal
                isOpen={showConfirmDelete}
                onClose={() => setShowConfirmDelete(false)}
                onConfirm={confirmDelete}
                title="Eliminar Agrupación"
                message="¿Estás seguro de eliminar esta agrupación? Las empresas no se borrarán, pero dejarán de pertenecer al grupo."
                confirmText="Eliminar"
                cancelText="Cancelar"
                isDanger={true}
            />
        </div>
    );
}
