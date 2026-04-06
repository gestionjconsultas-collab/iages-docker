// frontend/src/components/GestionSoporteView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import {
    MessageCircle, Filter, Search, Clock, CheckCircle, XCircle,
    AlertCircle, TrendingUp, Users, Star, Activity
} from 'lucide-react';
import ChatSoporte from './ChatSoporte';

const GestionSoporteView = () => {
    const [tickets, setTickets] = useState([]);
    const [filteredTickets, setFilteredTickets] = useState([]);
    const [metricas, setMetricas] = useState(null);
    const [loading, setLoading] = useState(true);
    const [ticketSeleccionado, setTicketSeleccionado] = useState(null);
    const [mostrarConversacion, setMostrarConversacion] = useState(false);

    // Filtros
    const [filtroEstado, setFiltroEstado] = useState('todos');
    const [filtroCategoria, setFiltroCategoria] = useState('todos');
    const [filtroPrioridad, setFiltroPrioridad] = useState('todos');
    const [searchTerm, setSearchTerm] = useState('');
    const [soloMisTickets, setSoloMisTickets] = useState(false);

    useEffect(() => {
        cargarDatos();
    }, []);

    useEffect(() => {
        aplicarFiltros();
    }, [tickets, filtroEstado, filtroCategoria, filtroPrioridad, searchTerm, soloMisTickets]);

    const cargarDatos = async () => {
        try {
            setLoading(true);

            // Cargar tickets y métricas en paralelo
            const [ticketsRes, metricasRes] = await Promise.all([
                axios.get('/api/soporte/tickets', { withCredentials: true }),
                axios.get('/api/soporte/metricas', { withCredentials: true })
            ]);

            if (ticketsRes.data.success) {
                setTickets(ticketsRes.data.tickets);
            }

            if (metricasRes.data.success) {
                setMetricas(metricasRes.data.metricas);
            }
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error al cargar datos de soporte');
        } finally {
            setLoading(false);
        }
    };

    const aplicarFiltros = () => {
        let filtered = [...tickets];

        // Filtro por estado
        if (filtroEstado !== 'todos') {
            filtered = filtered.filter(t => t.estado === filtroEstado);
        }

        // Filtro por categoría
        if (filtroCategoria !== 'todos') {
            filtered = filtered.filter(t => t.categoria === filtroCategoria);
        }

        // Filtro por prioridad
        if (filtroPrioridad !== 'todos') {
            filtered = filtered.filter(t => t.prioridad === filtroPrioridad);
        }

        // Solo mis tickets
        if (soloMisTickets) {
            filtered = filtered.filter(t => t.asignado_a_id === parseInt(localStorage.getItem('user_id')));
        }

        // Búsqueda
        if (searchTerm) {
            filtered = filtered.filter(t =>
                t.numero_ticket.toLowerCase().includes(searchTerm.toLowerCase()) ||
                t.asunto.toLowerCase().includes(searchTerm.toLowerCase()) ||
                t.empresa_nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                t.gestoria_nombre?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                t.usuario_creador_nombre?.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        setFilteredTickets(filtered);
    };

    const abrirConversacion = (ticket) => {
        setTicketSeleccionado(ticket);
        setMostrarConversacion(true);
    };

    const cerrarConversacion = () => {
        setMostrarConversacion(false);
        setTicketSeleccionado(null);
        cargarDatos();
    };

    const getEstadoColor = (estado) => {
        switch (estado) {
            case 'Abierto': return 'bg-blue-100 text-blue-800';
            case 'En Proceso': return 'bg-yellow-100 text-yellow-800';
            case 'Resuelto': return 'bg-green-100 text-green-800';
            case 'Cerrado': return 'bg-gray-100 text-gray-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    const getPrioridadColor = (prioridad) => {
        switch (prioridad) {
            case 'Urgente': return 'bg-red-100 text-red-800';
            case 'Alta': return 'bg-primary-light text-orange-800';
            case 'Media': return 'bg-yellow-100 text-yellow-800';
            case 'Baja': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="p-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-gray-900">🎫 Gestión de Soporte</h1>
                <p className="text-gray-600 mt-1">Dashboard del equipo de soporte</p>
            </div>

            {/* Métricas */}
            {metricas && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    {/* Abiertos */}
                    <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-blue-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Abiertos</p>
                                <p className="text-3xl font-bold text-gray-900">{metricas.por_estado.abiertos}</p>
                            </div>
                            <Clock className="w-12 h-12 text-blue-500 opacity-20" />
                        </div>
                    </div>

                    {/* En Proceso */}
                    <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-yellow-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">En Proceso</p>
                                <p className="text-3xl font-bold text-gray-900">{metricas.por_estado.en_proceso}</p>
                            </div>
                            <Activity className="w-12 h-12 text-yellow-500 opacity-20" />
                        </div>
                    </div>

                    {/* Resueltos */}
                    <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-green-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Resueltos</p>
                                <p className="text-3xl font-bold text-gray-900">{metricas.por_estado.resueltos}</p>
                            </div>
                            <CheckCircle className="w-12 h-12 text-green-500 opacity-20" />
                        </div>
                    </div>

                    {/* Valoración */}
                    <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-purple-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-600 mb-1">Valoración</p>
                                <div className="flex items-center gap-2">
                                    <p className="text-3xl font-bold text-gray-900">{metricas.valoracion_promedio}</p>
                                    <Star className="w-6 h-6 text-yellow-500 fill-yellow-500" />
                                </div>
                            </div>
                            <TrendingUp className="w-12 h-12 text-purple-500 opacity-20" />
                        </div>
                    </div>
                </div>
            )}

            {/* Filtros */}
            <div className="bg-white p-4 rounded-lg shadow-sm mb-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {/* Búsqueda */}
                    <div className="lg:col-span-2 relative">
                        <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar por ticket, asunto o empresa..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {/* Estado */}
                    <select
                        value={filtroEstado}
                        onChange={(e) => setFiltroEstado(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="todos">Todos los estados</option>
                        <option value="Abierto">Abierto</option>
                        <option value="En Proceso">En Proceso</option>
                        <option value="Resuelto">Resuelto</option>
                        <option value="Cerrado">Cerrado</option>
                    </select>

                    {/* Categoría */}
                    <select
                        value={filtroCategoria}
                        onChange={(e) => setFiltroCategoria(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="todos">Todas las categorías</option>
                        <option value="Bug">Bug</option>
                        <option value="Consulta">Consulta</option>
                        <option value="Mejora">Mejora</option>
                        <option value="Urgente">Urgente</option>
                    </select>

                    {/* Prioridad */}
                    <select
                        value={filtroPrioridad}
                        onChange={(e) => setFiltroPrioridad(e.target.value)}
                        className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="todos">Todas las prioridades</option>
                        <option value="Urgente">Urgente</option>
                        <option value="Alta">Alta</option>
                        <option value="Media">Media</option>
                        <option value="Baja">Baja</option>
                    </select>
                </div>

                {/* Toggle Mis Tickets */}
                <div className="mt-4">
                    <label className="flex items-center gap-2 cursor-pointer w-fit">
                        <input
                            type="checkbox"
                            checked={soloMisTickets}
                            onChange={(e) => setSoloMisTickets(e.target.checked)}
                            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                        />
                        <span className="text-sm font-medium text-gray-700">Solo mis tickets asignados</span>
                    </label>
                </div>
            </div>

            {/* Lista de Tickets */}
            {loading ? (
                <div className="text-center py-12">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-gray-600 mt-4">Cargando tickets...</p>
                </div>
            ) : filteredTickets.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg shadow-sm">
                    <MessageCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-600 text-lg">No hay tickets que coincidan con los filtros</p>
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Ticket
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Gestoría / Usuario
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Asunto
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Estado
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Prioridad
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Asignado
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    Mensajes
                                </th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {filteredTickets.map((ticket) => (
                                <tr
                                    key={ticket.id}
                                    onClick={() => abrirConversacion(ticket)}
                                    className="hover:bg-gray-50 cursor-pointer transition"
                                >
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="font-mono text-sm font-semibold text-gray-900">
                                            {ticket.numero_ticket}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm font-medium text-gray-900">
                                            {ticket.gestoria_nombre || 'Sin gestoría'}
                                        </div>
                                        <div className="text-xs text-gray-500">
                                            {ticket.usuario_creador_nombre || 'Usuario desconocido'}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="text-sm text-gray-900 font-medium">{ticket.asunto}</div>
                                        <div className="text-xs text-gray-500 mt-1">
                                            {new Date(ticket.fecha_creacion).toLocaleDateString('es-ES')}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEstadoColor(ticket.estado)}`}>
                                            {ticket.estado}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPrioridadColor(ticket.prioridad)}`}>
                                            {ticket.prioridad}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <span className="text-sm text-gray-600">
                                            {ticket.asignado_a_nombre || 'Sin asignar'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            <MessageCircle className="w-4 h-4 text-gray-400" />
                                            <span className="text-sm text-gray-600">{ticket.mensajes_count}</span>
                                            {ticket.mensajes_sin_leer > 0 && (
                                                <span className="px-2 py-0.5 bg-red-500 text-white text-xs font-bold rounded-full">
                                                    {ticket.mensajes_sin_leer}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Modal de Conversación */}
            {mostrarConversacion && ticketSeleccionado && (
                <div className="fixed inset-0 z-50">
                    <ChatSoporte
                        ticketId={ticketSeleccionado.id}
                        onClose={cerrarConversacion}
                    />
                </div>
            )}
        </div>
    );
};

export default GestionSoporteView;
