// frontend/src/components/GestionComunicados.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Plus, Megaphone, Trash2, Calendar, Filter,
    Building2, Users, Globe, Send, X, AlertTriangle,
    ChevronRight, CheckCircle, Info, FileText, Bell
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import { useEmpresasListadoSimple } from '../hooks/useEmpresas';
import { useGrupos } from '../hooks/useGruposEmpresas';

const GestionComunicados = () => {
    const [comunicados, setComunicados] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const { data: todasEmpresas } = useEmpresasListadoSimple();
    const { data: grupos } = useGrupos();

    // Form state
    const [formData, setFormData] = useState({
        titulo: '',
        contenido: '',
        tipo: 'general',
        prioridad: 'media',
        alcance: 'global',
        filtro_id: ''
    });

    useEffect(() => {
        fetchComunicados();
    }, []);

    const fetchComunicados = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/comunicados');
            if (response.data.success) {
                setComunicados(response.data.comunicados);
            }
        } catch (error) {
            console.error("Error al cargar comunicados:", error);
            toast.error("Error al cargar comunicados");
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        try {
            const dataToSubmit = { ...formData };
            if (dataToSubmit.alcance === 'global') dataToSubmit.filtro_id = null;
            if (dataToSubmit.filtro_id) dataToSubmit.filtro_id = parseInt(dataToSubmit.filtro_id);

            const response = await axios.post('/api/admin/comunicados', dataToSubmit);
            if (response.data.success) {
                toast.success("Comunicado publicado correctamente");
                setShowModal(false);
                setFormData({
                    titulo: '',
                    contenido: '',
                    tipo: 'general',
                    prioridad: 'media',
                    alcance: 'global',
                    filtro_id: ''
                });
                fetchComunicados();
            }
        } catch (error) {
            console.error("Error al publicar comunicado:", error);
            toast.error("Error al publicar comunicado");
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("¿Estás seguro de que deseas eliminar este comunicado?")) return;
        try {
            const response = await axios.delete(`/api/admin/comunicados/${id}`);
            if (response.data.success) {
                toast.success("Comunicado eliminado");
                fetchComunicados();
            }
        } catch (error) {
            console.error("Error al eliminar:", error);
            toast.error("Error al eliminar comunicado");
        }
    };

    const getIcon = (tipo) => {
        switch (tipo) {
            case 'impuestos': return <FileText className="w-5 h-5 text-blue-500" />;
            case 'nominas': return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'seguros': return <Bell className="w-5 h-5 text-purple-500" />;
            case 'urgente': return <AlertTriangle className="w-5 h-5 text-red-500" />;
            default: return <Megaphone className="w-5 h-5 text-orange-500" />;
        }
    };

    const getPriorityStyles = (prioridad) => {
        switch (prioridad) {
            case 'alta': return 'border-red-500 bg-red-50/10 text-red-700';
            case 'media': return 'border-orange-400 bg-orange-50/10 text-orange-700';
            default: return 'border-blue-400 bg-blue-50/10 text-blue-700';
        }
    };

    const getScopeLabel = (com) => {
        if (com.alcance === 'global') return 'Global (Todos)';
        if (com.alcance === 'grupo') {
            const g = grupos?.find(g => g.id === com.filtro_id);
            return `Grupo: ${g?.nombre || 'Desconocido'}`;
        }
        if (com.alcance === 'empresa') {
            const e = todasEmpresas?.find(e => e.id === com.filtro_id);
            return `Empresa: ${e?.nombre || 'Desconocida'}`;
        }
        return com.alcance;
    };

    return (
        <div className="p-6 max-w-7xl mx-auto animate-fade-in">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Megaphone className="text-orange-500" />
                        Gestión del Muro de Comunicados
                    </h1>
                    <p className="text-gray-500 text-sm mt-1">
                        Publica avisos importantes para tus clientes segmentados por empresa o grupos.
                    </p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="flex items-center gap-2 bg-orange-500 hover:bg-orange-600 text-white px-5 py-3 rounded-2xl transition-all shadow-lg active:scale-95 font-bold"
                >
                    <Plus size={20} />
                    Publicar Comunicado
                </button>
            </div>

            {/* Lista de Comunicados */}
            <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-gray-50/50 border-b border-gray-50 text-gray-400 uppercase text-[10px] font-bold tracking-wider">
                                <th className="px-6 py-4">Comunicado</th>
                                <th className="px-6 py-4">Destinatarios</th>
                                <th className="px-6 py-4">Tipo/Prioridad</th>
                                <th className="px-6 py-4">Fecha</th>
                                <th className="px-6 py-4 text-right">Acciones</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {loading ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-12 text-center">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500 mx-auto"></div>
                                    </td>
                                </tr>
                            ) : comunicados.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-12 text-center text-gray-400 italic">
                                        No hay comunicados publicados aún.
                                    </td>
                                </tr>
                            ) : (
                                comunicados.map((com) => (
                                    <tr key={com.id} className="hover:bg-gray-50/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="p-2 bg-white rounded-lg shadow-sm border border-gray-100 shrink-0">
                                                    {getIcon(com.tipo)}
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-bold text-gray-900 truncate max-w-[250px]">{com.titulo}</p>
                                                    <p className="text-xs text-gray-500 truncate max-w-[250px]">{com.contenido}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-600 bg-gray-100/80 px-2.5 py-1 rounded-full w-fit">
                                                {com.alcance === 'global' && <Globe size={12} />}
                                                {com.alcance === 'grupo' && <Users size={12} />}
                                                {com.alcance === 'empresa' && <Building2 size={12} />}
                                                {getScopeLabel(com)}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex flex-col gap-1">
                                                <span className="text-[10px] uppercase font-bold text-gray-400">{com.tipo}</span>
                                                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border w-fit ${getPriorityStyles(com.prioridad)}`}>
                                                    {com.prioridad}
                                                </span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                                <Calendar size={14} />
                                                {new Date(com.fecha_creacion).toLocaleDateString()}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={() => handleDelete(com.id)}
                                                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                                                title="Eliminar"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal de Creación */}
            {showModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-sm animate-fade-in">
                    <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden animate-scale-in">
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                                <Send size={20} className="text-orange-500" />
                                Redactar Nuevo Comunicado
                            </h2>
                            <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                                <X size={20} className="text-gray-500" />
                            </button>
                        </div>

                        <form onSubmit={handleCreate} className="p-6 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {/* Título */}
                                <div className="md:col-span-2">
                                    <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Título del Aviso</label>
                                    <input
                                        type="text"
                                        required
                                        className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all font-bold"
                                        placeholder="Ej: Nuevos plazos para el IVA trimestral"
                                        value={formData.titulo}
                                        onChange={(e) => setFormData({ ...formData, titulo: e.target.value })}
                                    />
                                </div>

                                {/* Tipo */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Tipo de Información</label>
                                    <select
                                        className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm font-medium"
                                        value={formData.tipo}
                                        onChange={(e) => setFormData({ ...formData, tipo: e.target.value })}
                                    >
                                        <option value="general">Información General</option>
                                        <option value="impuestos">Impuestos / Fiscal</option>
                                        <option value="nominas">Nóminas / Laboral</option>
                                        <option value="seguros">Seguros Sociales</option>
                                        <option value="urgente">⚠️ Aviso Urgente</option>
                                    </select>
                                </div>

                                {/* Prioridad */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Prioridad Visual</label>
                                    <select
                                        className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm font-medium"
                                        value={formData.prioridad}
                                        onChange={(e) => setFormData({ ...formData, prioridad: e.target.value })}
                                    >
                                        <option value="baja">Baja (Informativo)</option>
                                        <option value="media">Media (Recomendado)</option>
                                        <option value="alta">Alta (Muy importante)</option>
                                    </select>
                                </div>

                                {/* Alcance */}
                                <div>
                                    <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">¿Quién debe verlo?</label>
                                    <select
                                        className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm font-medium"
                                        value={formData.alcance}
                                        onChange={(e) => setFormData({ ...formData, alcance: e.target.value, filtro_id: '' })}
                                    >
                                        <option value="global">Todos los clientes (Global)</option>
                                        <option value="grupo">Un Holding / Grupo específico</option>
                                        <option value="empresa">Una empresa única</option>
                                    </select>
                                </div>

                                {/* Filtro ID dinámico */}
                                {formData.alcance !== 'global' && (
                                    <div>
                                        <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">
                                            Seleccionar {formData.alcance === 'grupo' ? 'Grupo' : 'Empresa'}
                                        </label>
                                        <select
                                            required
                                            className="w-full px-4 py-3 bg-white border-2 border-orange-100 rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm font-medium"
                                            value={formData.filtro_id}
                                            onChange={(e) => setFormData({ ...formData, filtro_id: e.target.value })}
                                        >
                                            <option value="">Selecciona una opción...</option>
                                            {formData.alcance === 'grupo' ? (
                                                grupos?.map(g => <option key={g.id} value={g.id}>{g.nombre}</option>)
                                            ) : (
                                                todasEmpresas?.map(e => <option key={e.id} value={e.id}>{e.nombre}</option>)
                                            )}
                                        </select>
                                    </div>
                                )}
                            </div>

                            {/* Contenido */}
                            <div>
                                <label className="block text-sm font-semibold text-gray-700 mb-1.5 ml-1">Mensaje (Contenido)</label>
                                <textarea
                                    required
                                    className="w-full px-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-orange-500/20 transition-all text-sm min-h-[120px]"
                                    placeholder="Escribe aquí el contenido del comunicado. Soporta Markdown básico."
                                    value={formData.contenido}
                                    onChange={(e) => setFormData({ ...formData, contenido: e.target.value })}
                                />
                            </div>

                            {/* Acciones */}
                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 py-3.5 text-sm font-bold text-gray-500 hover:bg-gray-100 rounded-2xl transition-colors"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 py-3.5 text-sm font-bold text-white bg-orange-500 hover:bg-orange-600 rounded-2xl transition-all shadow-lg active:scale-95 flex items-center justify-center gap-2"
                                >
                                    <Send size={18} />
                                    Publicar Ahora
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default GestionComunicados;
