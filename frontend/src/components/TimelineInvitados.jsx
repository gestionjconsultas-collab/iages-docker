import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
    Bell, FileText, CheckCircle, Clock,
    Download, Eye, AlertTriangle, Building2, Search,
    Files, Mail, ChevronDown, X
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import api from '../utils/axiosConfig';
import socket from '../socket';
import LoadingPage from './LoadingPage';
import EnviarDocumentosModal from './EnviarDocumentosModal';
import { useEmpresasListadoSimple } from '../hooks/useEmpresas';

export default function TimelineInvitados() {
    const [filtro, setFiltro] = useState('TODAS');
    const [dias, setDias] = useState(10); // Por defecto 10 días
    const [empresaId, setEmpresaId] = useState('todas');
    const [searchTerm, setSearchTerm] = useState('');
    const [selecciones, setSelecciones] = useState([]);
    const [modalEnvioOpen, setModalEnvioOpen] = useState(false);

    // Estados para el selector de empresas
    const [isEmpresaDropdownOpen, setIsEmpresaDropdownOpen] = useState(false);
    const [empresaSearchTerm, setEmpresaSearchTerm] = useState('');
    const dropdownRef = useRef(null);

    const queryClient = useQueryClient();

    const { data: empresas = [] } = useEmpresasListadoSimple();

    const { data, isLoading, isError, error } = useQuery({
        queryKey: ['novedades-timeline', dias, empresaId],
        queryFn: async () => {
            const params = { dias };
            if (empresaId !== 'todas') params.empresa_id = empresaId;
            const res = await api.get('/api/empresas/novedades', { params });
            return res.data.novedades || [];
        }
    });

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsEmpresaDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // ✅ FIX: Listener propio de Socket.IO para actualizar el timeline en tiempo real
    useEffect(() => {
        const handleNuevaNotificacion = () => {
            queryClient.invalidateQueries({ queryKey: ['novedades-timeline'] });
        };
        socket.on('nueva_notificacion', handleNuevaNotificacion);
        return () => {
            socket.off('nueva_notificacion', handleNuevaNotificacion);
        };
    }, [queryClient]);

    const getPriorityColor = (prioridad) => {
        switch (prioridad?.toLowerCase()) {
            case 'urgente': return 'bg-red-50 text-red-600 border-red-200';
            case 'importante': return 'bg-orange-50 text-orange-600 border-orange-200';
            default: return 'bg-blue-50 text-blue-600 border-blue-200';
        }
    };

    const getIconForCategory = (categoria) => {
        if (!categoria) return <Bell className="w-5 h-5 text-gray-500" />;
        const cat = categoria.toUpperCase();
        if (cat.includes('NOTIFICACION')) return <Bell className="w-5 h-5 text-indigo-500" />;
        if (cat.includes('FISCAL') || cat.includes('IMPUESTO')) return <FileText className="w-5 h-5 text-emerald-500" />;
        if (cat.includes('NOMINAS') || cat.includes('LABORAL')) return <CheckCircle className="w-5 h-5 text-sky-500" />;
        if (cat.includes('COMUNICADO')) return <AlertTriangle className="w-5 h-5 text-amber-500" />;
        return <Files className="w-5 h-5 text-gray-500" />;
    };

    const categories = Array.from(new Set((data || []).map(item => item.categoria).filter(Boolean)));
    const allFilters = ['TODAS', 'URGENTES', 'NO LEIDAS', ...categories];

    const filteredData = (data || []).filter(item => {
        if (filtro === 'NO LEIDAS' && item.is_leido) return false;
        if (filtro === 'URGENTES' && item.prioridad !== 'urgente') return false;
        if (filtro !== 'TODAS' && filtro !== 'URGENTES' && filtro !== 'NO LEIDAS') {
            if (item.categoria !== filtro) return false;
        }

        if (searchTerm) {
            const p = searchTerm.toLowerCase();
            const tituloCoincide = item.titulo?.toLowerCase().includes(p);
            const empresaCoincide = item.empresa_nombre?.toLowerCase().includes(p);
            return tituloCoincide || empresaCoincide;
        }
        return true;
    });

    const toggleSeleccion = (item) => {
        if (item.tipo_evento === 'Comunicado') return;

        setSelecciones(prev => {
            const exists = prev.find(i => i.id === item.id);
            if (exists) {
                return prev.filter(i => i.id !== item.id);
            } else {
                return [...prev, item];
            }
        });
    };

    const isSelected = (id) => selecciones.some(i => i.id === id);
    const deseleccionarTodo = () => setSelecciones([]);

    if (isLoading) return <LoadingPage />;

    if (isError) {
        return (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center text-red-500">
                <AlertTriangle className="w-16 h-16 mb-4" />
                <h2 className="text-xl font-bold">Error al cargar novedades</h2>
                <p>{error?.message || "Ocurrió un error inesperado"}</p>
            </div>
        );
    }

    const selectedEmpresa = empresas.find(e => e.id === empresaId);

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-slate-900">
                        Muro de Novedades
                    </h1>
                    <p className="text-slate-500 mt-1 text-sm md:text-base">
                        Todos los documentos importantes y alertas de tus empresas.
                    </p>
                </div>
            </div>

            <div className="rounded-xl bg-white shadow-sm border border-slate-200">
                <div className="p-4">
                    <div className="flex flex-col xl:flex-row gap-4 items-center justify-between">
                        <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">
                            <div className="relative w-full sm:w-64">
                                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                                <input
                                    type="text"
                                    className="pl-9 bg-white h-10 w-full rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-900 placeholder:text-slate-400"
                                    placeholder="Buscar empresa o documento..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                />
                            </div>

                            {/* Selector de Empresa con Buscador */}
                            <div className="relative w-full sm:w-72" ref={dropdownRef}>
                                <button
                                    onClick={() => setIsEmpresaDropdownOpen(!isEmpresaDropdownOpen)}
                                    className={`w-full flex items-center justify-between gap-3 px-3.5 h-10 rounded-lg border text-sm font-bold transition-all
                                        ${isEmpresaDropdownOpen || empresaId !== 'todas'
                                            ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                                            : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
                                        }`}
                                >
                                    <div className="flex items-center gap-2 truncate">
                                        <Building2 className="w-4 h-4 opacity-70 shrink-0" />
                                        <span className="truncate">
                                            {empresaId === 'todas' ? 'Todas las empresas' : selectedEmpresa?.nombre || 'Empresa...'}
                                        </span>
                                    </div>
                                    <ChevronDown className={`w-4 h-4 opacity-50 transition-transform duration-200 ${isEmpresaDropdownOpen ? 'rotate-180 opacity-100' : ''}`} />
                                </button>

                                {isEmpresaDropdownOpen && (
                                    <div className="absolute top-full left-0 w-full mt-2 bg-white rounded-xl shadow-xl border border-slate-100 z-[100] animate-in fade-in slide-in-from-top-2 duration-200 overflow-hidden ring-1 ring-black/5">
                                        <div className="p-2 bg-slate-50 border-b border-slate-100">
                                            <div className="relative">
                                                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                                                <input
                                                    type="text"
                                                    placeholder="Filtrar empresa..."
                                                    className="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm"
                                                    value={empresaSearchTerm}
                                                    onChange={(e) => setEmpresaSearchTerm(e.target.value)}
                                                    autoFocus
                                                />
                                            </div>
                                        </div>
                                        <div className="max-h-60 overflow-y-auto p-1 custom-scrollbar">
                                            <button
                                                onClick={() => {
                                                    setEmpresaId('todas');
                                                    setIsEmpresaDropdownOpen(false);
                                                }}
                                                className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 flex items-center gap-2 transition-colors ${empresaId === 'todas'
                                                    ? 'bg-blue-600 text-white font-bold'
                                                    : 'text-slate-700 hover:bg-slate-100'
                                                    }`}
                                            >
                                                <Building2 className={`w-4 h-4 ${empresaId === 'todas' ? 'text-white' : 'text-slate-400'}`} />
                                                <span>Todas las empresas</span>
                                            </button>

                                            {empresas
                                                .filter(e => e.nombre.toLowerCase().includes(empresaSearchTerm.toLowerCase()))
                                                .map(e => (
                                                    <button
                                                        key={e.id}
                                                        onClick={() => {
                                                            setEmpresaId(e.id);
                                                            setIsEmpresaDropdownOpen(false);
                                                            setEmpresaSearchTerm('');
                                                        }}
                                                        className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 flex items-center gap-2 transition-colors ${empresaId === e.id
                                                            ? 'bg-blue-600 text-white font-bold'
                                                            : 'text-slate-700 hover:bg-slate-100'
                                                            }`}
                                                    >
                                                        <div className={`w-4 h-4 shrink-0 flex items-center justify-center ${empresaId === e.id ? 'text-white' : 'text-slate-400'}`}>
                                                            {empresaId === e.id ? <CheckCircle className="w-4 h-4" /> : <Building2 className="w-4 h-4" />}
                                                        </div>
                                                        <span className="truncate">{e.nombre}</span>
                                                    </button>
                                                ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Filtro de Tiempo */}
                            <div className="relative w-full sm:w-auto">
                                <Clock className="absolute left-2.5 top-3 h-4 w-4 text-slate-500" />
                                <select
                                    value={dias}
                                    onChange={(e) => setDias(Number(e.target.value))}
                                    className="pl-9 pr-9 bg-white h-10 w-full rounded-lg border border-slate-200 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-900 appearance-none cursor-pointer hover:bg-slate-50 transition-colors"
                                >
                                    <option value={10}>10 días</option>
                                    <option value={30}>30 días</option>
                                    <option value={90}>3 meses</option>
                                    <option value={0}>Todo</option>
                                </select>
                                <ChevronDown className="absolute right-2.5 top-3.5 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
                            </div>

                            <div className="flex bg-slate-100 p-1 rounded-full overflow-x-auto no-scrollbar border border-slate-200 w-full sm:w-auto">
                                {allFilters.map((key) => (
                                    <button
                                        key={key}
                                        onClick={() => setFiltro(key)}
                                        className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all shrink-0 ${filtro === key
                                            ? 'bg-white text-blue-600 shadow-sm border border-slate-200'
                                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
                                            }`}
                                    >
                                        {key.replace('_', ' ')}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {selecciones.length > 0 && (
                            <div className="flex flex-col sm:flex-row items-center gap-4 bg-blue-600 px-6 py-3 rounded-2xl animate-in fade-in slide-in-from-bottom-4 w-full xl:w-auto justify-between shadow-xl shadow-blue-500/20 border border-blue-400/30">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center text-white ring-4 ring-white/10">
                                        <CheckCircle className="w-5 h-5" />
                                    </div>
                                    <div>
                                        <span className="text-sm font-bold text-white block">
                                            {selecciones.length} documentos seleccionados
                                        </span>
                                        <span className="text-[10px] text-blue-100 font-medium uppercase tracking-wider">
                                            Acciones en bloque
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3 w-full sm:w-auto">
                                    <button
                                        onClick={deseleccionarTodo}
                                        className="flex-1 sm:flex-none h-11 px-6 text-sm font-bold rounded-xl text-white hover:bg-white/10 transition-all active:scale-95"
                                    >
                                        Limpiar
                                    </button>
                                    <button
                                        onClick={() => setModalEnvioOpen(true)}
                                        className="flex-1 sm:flex-none h-11 px-8 inline-flex items-center justify-center rounded-xl text-sm font-black bg-white text-blue-600 hover:bg-blue-50 gap-2 transition-all shadow-lg active:scale-95 whitespace-nowrap"
                                    >
                                        <Mail className="w-5 h-5 text-blue-600" />
                                        <span>ENVIAR A TERCEROS</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="space-y-4 relative pb-10">
                <div className="absolute left-8 top-4 bottom-0 w-px bg-slate-200 hidden sm:block z-0"></div>

                {filteredData.length === 0 ? (
                    <div className="text-center py-20 px-4 bg-white rounded-2xl border border-dashed border-slate-300 shadow-sm mt-4">
                        <div className="w-20 h-20 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-4">
                            <Files className="w-10 h-10 text-slate-400" />
                        </div>
                        <h3 className="text-lg font-semibold text-slate-700">Nada por aquí</h3>
                        <p className="text-slate-500 mt-1 max-w-sm mx-auto">
                            No hay novedades que coincidan con tu búsqueda actual.
                        </p>
                    </div>
                ) : (
                    filteredData.map((item, index) => {
                        const isSel = isSelected(item.id);
                        const canSelect = item.tipo_evento === 'Documento';
                        const fDate = parseISO(item.fecha);

                        return (
                            <div
                                key={item.id}
                                className={`flex gap-4 sm:gap-6 relative z-10 animate-in slide-in-from-bottom-4 fade-in`}
                                style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'both' }}
                                onClick={() => canSelect && toggleSeleccion(item)}
                            >
                                <div className="hidden sm:flex flex-col items-center mt-1 w-16 shrink-0">
                                    <div className={`w-10 h-10 rounded-full flex items-center justify-center border-4 border-white shadow-sm bg-white relative z-20 ${!item.is_leido ? 'ring-2 ring-primary/30 ring-offset-2' : ''}`}>
                                        {getIconForCategory(item.categoria)}
                                    </div>
                                    <span className="text-[10px] font-bold text-slate-500 mt-2 text-center uppercase tracking-wider">
                                        {format(fDate, 'dd MMM', { locale: es })}
                                    </span>
                                </div>

                                <div className={`rounded-xl w-full overflow-hidden transition-all duration-200 ${isSel
                                    ? 'ring-2 ring-primary border-transparent bg-primary/5 shadow-md scale-[1.01]'
                                    : 'hover:shadow-md hover:border-slate-300 cursor-pointer bg-white shadow-sm border border-slate-200'
                                    }`}>
                                    <div className="flex p-4 sm:p-5">
                                        {canSelect && (
                                            <div className="mr-4 mt-1">
                                                <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${isSel
                                                    ? 'bg-primary border-primary text-white'
                                                    : 'border-slate-300 text-transparent bg-white'
                                                    }`}>
                                                    <CheckCircle className="w-3.5 h-3.5" />
                                                </div>
                                            </div>
                                        )}

                                        <div className="flex-1 min-w-0">
                                            <div className="flex flex-wrap items-center gap-2 mb-2">
                                                {item.empresa_nombre && (
                                                    <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full truncate max-w-[150px] sm:max-w-xs">
                                                        <Building2 className="w-3.5 h-3.5 shrink-0 text-slate-400" />
                                                        <span className="truncate">{item.empresa_nombre}</span>
                                                    </span>
                                                )}
                                                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${getPriorityColor(item.prioridad)} shrink-0`}>
                                                    {item.prioridad}
                                                </span>
                                                {!item.is_leido && (
                                                    <span className="flex h-2.5 w-2.5 rounded-full bg-blue-600 shrink-0 ml-1 shadow-sm"></span>
                                                )}
                                            </div>

                                            <h3 className={`text-base sm:text-lg font-bold leading-tight mb-1 truncate ${!item.is_leido ? 'text-slate-900' : 'text-slate-700'}`}>
                                                {item.titulo}
                                            </h3>
                                            <p className="text-sm text-slate-600 line-clamp-2">
                                                {item.descripcion}
                                            </p>

                                            <div className="mt-3 flex items-center justify-between sm:justify-start gap-4">
                                                <div className="flex items-center text-xs text-slate-500 font-medium gap-1.5 sm:hidden">
                                                    <Clock className="w-3.5 h-3.5" />
                                                    {format(fDate, "d MMM, HH:mm")}
                                                </div>
                                                <div className="hidden sm:flex items-center text-xs text-slate-500 font-medium gap-1.5">
                                                    <Clock className="w-4 h-4" />
                                                    {format(fDate, "PPpp", { locale: es })}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="ml-4 flex justify-end gap-2 shrink-0">
                                            {item.link ? (
                                                <>
                                                    <button
                                                        className="inline-flex items-center justify-center h-10 w-10 md:w-auto md:px-4 md:h-9 rounded-md text-sm font-medium bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors shadow-sm"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            window.open(item.link, '_blank');
                                                        }}
                                                        title="Ver documento"
                                                    >
                                                        <Eye className="w-4 h-4 md:mr-2" />
                                                        <span className="hidden md:inline font-medium">Ver</span>
                                                    </button>
                                                    <button
                                                        className="inline-flex items-center justify-center h-10 w-10 md:w-auto md:px-4 md:h-9 rounded-md text-sm font-medium bg-blue-50 border border-blue-200 hover:bg-blue-100 text-blue-700 transition-colors shadow-sm"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            // Forzar descarga agregando parámetro a la URL si es necesario,
                                                            // o dejar que el navegador lo maneje si el content-disposition está seteado a attachment por el backend.
                                                            window.open(`${item.link}?download=true`, '_blank');
                                                        }}
                                                        title="Descargar documento"
                                                    >
                                                        <Download className="w-4 h-4 md:mr-2" />
                                                        <span className="hidden md:inline font-medium">Descargar</span>
                                                    </button>
                                                </>
                                            ) : (
                                                item.tipo_evento === 'Comunicado' && (
                                                    <button
                                                        className="inline-flex items-center justify-center h-10 w-10 md:w-auto md:px-4 md:h-9 rounded-md text-sm font-bold bg-blue-50 border border-blue-200 hover:bg-blue-100 text-blue-700 transition-colors shadow-sm"
                                                    >
                                                        <Eye className="w-4 h-4 md:mr-2" />
                                                        <span className="hidden md:inline">Leer</span>
                                                    </button>
                                                )
                                            )}
                                        </div>

                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {modalEnvioOpen && (
                <EnviarDocumentosModal
                    isOpen={modalEnvioOpen}
                    onClose={() => setModalEnvioOpen(false)}
                    documentosSeleccionados={selecciones}
                    onSuccess={() => {
                        setSelecciones([]);
                    }}
                />
            )}
        </div>
    );
}
