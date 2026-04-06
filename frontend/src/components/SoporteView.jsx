// frontend/src/components/SoporteView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { MessageCircle, Plus, Search, Filter, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import CrearTicketModal from './CrearTicketModal';
import ChatSoporte from './ChatSoporte';
import socket from '../socket';
import { devLog } from '../utils/logger';

const SoporteView = () => {
    const [tickets, setTickets] = useState([]);
    const [filteredTickets, setFilteredTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [mostrarCrearModal, setMostrarCrearModal] = useState(false);
    const [ticketSeleccionado, setTicketSeleccionado] = useState(null);
    const [mostrarConversacion, setMostrarConversacion] = useState(false);

    // Filtros
    const [filtroEstado, setFiltroEstado] = useState('todos');
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        cargarTickets();
    }, []);

    useEffect(() => {
        aplicarFiltros();
    }, [tickets, filtroEstado, searchTerm]);

    // Listener de WebSocket para actualizar tickets en tiempo real
    useEffect(() => {
        const handleNuevoMensaje = (data) => {
            devLog('📨 [SoporteView] Nuevo mensaje recibido, actualizando contador...');

            // Actualizar contador del ticket específico INSTANTÁNEAMENTE
            setTickets(prevTickets =>
                prevTickets.map(ticket =>
                    ticket.id === data.ticket_id
                        ? { ...ticket, mensajes_sin_leer: (ticket.mensajes_sin_leer || 0) + 1 }
                        : ticket
                )
            );
        };

        socket.on('nuevo_mensaje_soporte', handleNuevoMensaje);

        return () => {
            socket.off('nuevo_mensaje_soporte', handleNuevoMensaje);
        };
    }, []);

    const cargarTickets = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/soporte/tickets', { withCredentials: true });

            if (response.data.success) {
                setTickets(response.data.tickets);
            }
        } catch (error) {
            console.error('Error cargando tickets:', error);
            toast.error('Error al cargar tickets');
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

        // Filtro por búsqueda
        if (searchTerm) {
            filtered = filtered.filter(t =>
                t.numero_ticket.toLowerCase().includes(searchTerm.toLowerCase()) ||
                t.asunto.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        setFilteredTickets(filtered);
    };

    const abrirConversacion = async (ticket) => {
        setTicketSeleccionado(ticket);
        setMostrarConversacion(true);

        // Resetear contador INSTANTÁNEAMENTE en la UI
        setTickets(prevTickets =>
            prevTickets.map(t =>
                t.id === ticket.id
                    ? { ...t, mensajes_sin_leer: 0 }
                    : t
            )
        );

        // Llamar al endpoint para marcar mensajes como leídos en el backend
        try {
            const response = await axios.post(`/api/soporte/tickets/${ticket.id}/marcar-leido`);
            if (response.data.success) {
                devLog(`✅ ${response.data.mensajes_marcados} mensajes marcados como leídos`);
            }
        } catch (error) {
            console.error('Error marcando mensajes como leídos:', error);
        }
    };

    const cerrarConversacion = () => {
        setMostrarConversacion(false);
        setTicketSeleccionado(null);
        cargarTickets(); // Recargar para actualizar contadores
    };

    const getEstadoIcon = (estado) => {
        switch (estado) {
            case 'Abierto':
                return <Clock className="w-5 h-5 text-blue-500" />;
            case 'En Proceso':
                return <AlertCircle className="w-5 h-5 text-yellow-500" />;
            case 'Resuelto':
                return <CheckCircle className="w-5 h-5 text-green-500" />;
            case 'Cerrado':
                return <XCircle className="w-5 h-5 text-gray-500" />;
            default:
                return <MessageCircle className="w-5 h-5 text-gray-400" />;
        }
    };

    const getEstadoColor = (estado) => {
        switch (estado) {
            case 'Abierto':
                return 'bg-blue-100 text-blue-800';
            case 'En Proceso':
                return 'bg-yellow-100 text-yellow-800';
            case 'Resuelto':
                return 'bg-green-100 text-green-800';
            case 'Cerrado':
                return 'bg-gray-100 text-gray-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getCategoriaColor = (categoria) => {
        switch (categoria) {
            case 'Bug':
                return 'bg-red-100 text-red-800';
            case 'Consulta':
                return 'bg-blue-100 text-blue-800';
            case 'Mejora':
                return 'bg-purple-100 text-purple-800';
            case 'Urgente':
                return 'bg-primary-light text-orange-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="p-6">
            {/* Header */}
            <div className="mb-6">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">💬 Soporte</h1>
                        <p className="text-gray-600 mt-1">Gestiona tus tickets de soporte</p>
                    </div>
                    <button
                        onClick={() => setMostrarCrearModal(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                        <Plus className="w-5 h-5" />
                        Nuevo Ticket
                    </button>
                </div>

                {/* Filtros */}
                <div className="flex gap-4 items-center bg-white p-4 rounded-lg shadow-sm">
                    {/* Búsqueda */}
                    <div className="flex-1 relative">
                        <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
                        <input
                            type="text"
                            placeholder="Buscar por número o asunto..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {/* Filtro por estado */}
                    <div className="flex items-center gap-2">
                        <Filter className="w-5 h-5 text-gray-400" />
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
                    </div>
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
                    <p className="text-gray-600 text-lg">No hay tickets</p>
                    <p className="text-gray-400 mt-2">Crea tu primer ticket de soporte</p>
                    <button
                        onClick={() => setMostrarCrearModal(true)}
                        className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                        Crear Ticket
                    </button>
                </div>
            ) : (
                <div className="grid gap-4">
                    {filteredTickets.map((ticket) => (
                        <div
                            key={ticket.id}
                            onClick={() => abrirConversacion(ticket)}
                            className="bg-white p-6 rounded-lg shadow-sm hover:shadow-md transition cursor-pointer border border-gray-200"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-start gap-4 flex-1">
                                    {/* Icono de estado */}
                                    <div className="mt-1">
                                        {getEstadoIcon(ticket.estado)}
                                    </div>

                                    {/* Información del ticket */}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-3 mb-2">
                                            <span className="font-mono text-sm font-semibold text-gray-700">
                                                {ticket.numero_ticket}
                                            </span>
                                            <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getEstadoColor(ticket.estado)} `}>
                                                {ticket.estado}
                                            </span>
                                            <span className={`px - 2 py - 1 rounded - full text - xs font - medium ${getCategoriaColor(ticket.categoria)} `}>
                                                {ticket.categoria}
                                            </span>
                                        </div>

                                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                                            {ticket.asunto}
                                        </h3>

                                        {ticket.descripcion && (
                                            <p className="text-gray-600 text-sm line-clamp-2">
                                                {ticket.descripcion}
                                            </p>
                                        )}

                                        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                                            <span>
                                                Creado: {new Date(ticket.fecha_creacion).toLocaleDateString('es-ES')}
                                            </span>
                                            {ticket.asignado_a_nombre && (
                                                <span>
                                                    Asignado a: <span className="font-medium">{ticket.asignado_a_nombre}</span>
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Contador de mensajes */}
                                <div className="flex flex-col items-end gap-2">
                                    {ticket.mensajes_count > 0 && (
                                        <div className="flex items-center gap-2">
                                            <MessageCircle className="w-4 h-4 text-gray-400" />
                                            <span className="text-sm text-gray-600">{ticket.mensajes_count}</span>
                                        </div>
                                    )}
                                    {ticket.mensajes_sin_leer > 0 && (
                                        <span className="px-2 py-1 bg-red-500 text-white text-xs font-bold rounded-full">
                                            {ticket.mensajes_sin_leer} nuevo{ticket.mensajes_sin_leer > 1 ? 's' : ''}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Modales */}
            {mostrarCrearModal && (
                <CrearTicketModal
                    onClose={() => setMostrarCrearModal(false)}
                    onTicketCreado={cargarTickets}
                />
            )}

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

export default SoporteView;
