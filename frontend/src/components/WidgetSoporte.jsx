// frontend/src/components/WidgetSoporte.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { MessageCircle, X, Plus, List, Clock } from 'lucide-react';
import ChatSoporte from './ChatSoporte';
import NotificationManager from '../utils/NotificationManager';
import toast from 'react-hot-toast';
import socket from '../socket';
import { useAuth } from '../AuthContext';
import { devLog, devError } from '../utils/logger';

const WidgetSoporte = () => {
    const navigate = useNavigate();
    const [mostrarWidget, setMostrarWidget] = useState(false);
    const [ticketsRecientes, setTicketsRecientes] = useState([]);
    const [mensajesSinLeer, setMensajesSinLeer] = useState(0);
    const [loading, setLoading] = useState(false);
    const [chatAbierto, setChatAbierto] = useState(false);
    const [ticketSeleccionado, setTicketSeleccionado] = useState(null);
    const { user } = useAuth();

    // Refs para que el socket listener siempre vea el estado actual (evita stale closures)
    const chatAbiertoRef = useRef(false);
    const ticketSeleccionadoRef = useRef(null);
    const mostrarWidgetRef = useRef(false);

    useEffect(() => { chatAbiertoRef.current = chatAbierto; }, [chatAbierto]);
    useEffect(() => { ticketSeleccionadoRef.current = ticketSeleccionado; }, [ticketSeleccionado]);
    useEffect(() => { mostrarWidgetRef.current = mostrarWidget; }, [mostrarWidget]);

    // Polling para notificaciones cada 60 segundos (reducido para evitar rate limiting)
    useEffect(() => {
        cargarNotificaciones();
        const interval = setInterval(cargarNotificaciones, 60000); // 60s en lugar de 30s

        // Escuchar evento de apertura del chat IA
        const handleAIChatOpen = () => {
            setMostrarWidget(false);
        };

        window.addEventListener('ai-chat-opened', handleAIChatOpen);

        // ⭐ Listener global de WebSocket para notificaciones
        devLog('🔧 [WidgetSoporte] Registrando listener de WebSocket...');
        // ✅ Guardar referencia para poder limpiar solo ESTE handler (evita quitar los de ChatSoporte/SoporteView)
        const handleNuevoMensajeSoporte = (data) => {
            devLog('🔔 Widget recibió mensaje:', data);

            const nombreUsuario = data.mensaje.usuario_nombre || 'Soporte';
            const preview = data.mensaje.mensaje.substring(0, 50);
            const previewText = `${preview}${data.mensaje.mensaje.length > 50 ? '...' : ''}`;

            // ❌ NO mostrar toast si el mensaje es mío
            if (user && Number(data.mensaje.usuario_id) === Number(user.id)) {
                devLog('🚫 Saltando toast: el mensaje es propio');
                return;
            }

            // ❌ NO mostrar toast si ya tengo ese chat abierto (usar refs para evitar stale closure)
            if (chatAbiertoRef.current && ticketSeleccionadoRef.current?.id === data.ticket_id) {
                devLog('🚫 Saltando toast: chat ya está abierto');
                return;
            }

            // ⭐ Mostrar toast consolidado por ticket_id
            toast.success(
                `💬 ${nombreUsuario}: ${previewText}`,
                {
                    id: `ticket_${data.ticket_id}`, // Evita que se amontonen varios del mismo ticket
                    duration: 5000,
                    onClick: () => abrirChatDesdeNotificacion(data.ticket_id)
                }
            );

            // Solo mostrar browser notification y sonido si el widget está cerrado
            // O si el chat abierto no es del ticket actual
            if (!mostrarWidgetRef.current || !chatAbiertoRef.current || ticketSeleccionadoRef.current?.id !== data.ticket_id) {
                // 1. Browser Notification
                NotificationManager.show(
                    `Nuevo mensaje de ${nombreUsuario}`,
                    data.mensaje.mensaje.substring(0, 100),
                    { ticket_id: data.ticket_id }
                );

                // 2. Sonido Global
                playNotificationSound();

                // 3. Actualizar badge
                cargarNotificaciones();
            }

            // 4. Actualizar contador del ticket en la lista INSTANTÁNEAMENTE
            setTicketsRecientes(prevTickets =>
                prevTickets.map(ticket =>
                    ticket.id === data.ticket_id
                        ? { ...ticket, mensajes_sin_leer: (ticket.mensajes_sin_leer || 0) + 1 }
                        : ticket
                )
            );
        };
        socket.on('nuevo_mensaje_soporte', handleNuevoMensajeSoporte);
        devLog('✅ [WidgetSoporte] Listener registrado correctamente');

        // Listener para abrir chat desde notificación del navegador
        const handleOpenChat = (event) => {
            const { ticketId } = event.detail;
            abrirChatDesdeNotificacion(ticketId);
        };

        window.addEventListener('open-ticket-chat', handleOpenChat);

        return () => {
            clearInterval(interval);
            window.removeEventListener('ai-chat-opened', handleAIChatOpen);
            window.removeEventListener('open-ticket-chat', handleOpenChat);
            socket.off('nuevo_mensaje_soporte', handleNuevoMensajeSoporte); // ✅ Solo elimina ESTE handler
        };
    }, []); // ⭐ Sin dependencias para que siempre escuche

    // Cargar tickets recientes cuando se abre el widget
    useEffect(() => {
        if (mostrarWidget) {
            cargarTicketsRecientes();
            // Notificar al chat IA que se cierre
            window.dispatchEvent(new Event('soporte-widget-opened'));
        }
    }, [mostrarWidget]);

    const cargarNotificaciones = async () => {
        try {
            const response = await axios.get('/api/soporte/notificaciones', { withCredentials: true });
            if (response.data.success) {
                setMensajesSinLeer(response.data.mensajes_sin_leer);
            }
        } catch (error) {
            console.error('Error cargando notificaciones:', error);
        }
    };

    const cargarTicketsRecientes = async () => {
        try {
            setLoading(true);
            devLog('🔍 Cargando tickets recientes...');
            // Cargar tickets Abiertos y En Proceso
            const response = await axios.get('/api/soporte/tickets', { withCredentials: true });
            devLog('📊 Respuesta de tickets:', response.data);
            if (response.data.success) {
                // Filtrar solo Abiertos y En Proceso, mostrar los 3 más recientes
                const ticketsActivos = response.data.tickets.filter(
                    t => t.estado === 'Abierto' || t.estado === 'En Proceso'
                ).slice(0, 3);
                devLog('✅ Tickets cargados:', ticketsActivos.length, ticketsActivos);
                setTicketsRecientes(ticketsActivos);
            }
        } catch (error) {
            console.error('❌ Error cargando tickets:', error);
        } finally {
            setLoading(false);
        }
    };

    const irASoporte = () => {
        setMostrarWidget(false);
        navigate('/soporte');
    };

    // Abrir chat de un ticket (mantener widget visible)
    const abrirChat = async (ticket) => {
        setTicketSeleccionado(ticket);
        setChatAbierto(true);

        // Resetear contador INSTANTÁNEAMENTE en la UI
        setTicketsRecientes(prevTickets =>
            prevTickets.map(t =>
                t.id === ticket.id
                    ? { ...t, mensajes_sin_leer: 0 }
                    : t
            )
        );

        // Llamar al endpoint para marcar mensajes como leídos
        try {
            const response = await axios.post(`/api/soporte/tickets/${ticket.id}/marcar-leido`);
            if (response.data.success) {
                devLog(`✅ ${response.data.mensajes_marcados} mensajes marcados como leídos`);
                // Actualizar contador de notificaciones
                cargarNotificaciones();
            }
        } catch (error) {
            console.error('Error marcando mensajes como leídos:', error);
        }
    };

    // ⭐ NUEVO: Cerrar chat
    const cerrarChat = () => {
        setChatAbierto(false);
        setTicketSeleccionado(null);
        cargarNotificaciones(); // Actualizar contador
    };

    // Abrir chat desde notificación
    const abrirChatDesdeNotificacion = async (ticketId) => {
        try {
            // Cargar datos del ticket
            const response = await axios.get(`/api/soporte/tickets/${ticketId}`, { withCredentials: true });
            if (response.data.success) {
                setTicketSeleccionado(response.data.ticket);
                setChatAbierto(true);
                setMostrarWidget(true); // Abrir widget si está cerrado
            }
        } catch (error) {
            console.error('Error cargando ticket:', error);
            toast.error('Error al abrir el chat');
        }
    };

    // Reproducir sonido de notificación
    const playNotificationSound = () => {
        try {
            const audio = new AudioContext();
            const oscillator = audio.createOscillator();
            const gainNode = audio.createGain();
            oscillator.connect(gainNode);
            gainNode.connect(audio.destination);
            oscillator.frequency.value = 800; // Tono más alto que el del chat
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.15, audio.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audio.currentTime + 0.3);
            oscillator.start(audio.currentTime);
            oscillator.stop(audio.currentTime + 0.3);
        } catch (error) {
            devError('No se pudo reproducir sonido:', error);
        }
    };

    const getEstadoColor = (estado) => {
        switch (estado) {
            case 'Abierto': return 'bg-blue-100 text-blue-800';
            case 'En Proceso': return 'bg-yellow-100 text-yellow-800';
            case 'Resuelto': return 'bg-green-100 text-green-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <>
            {/* Botón flotante */}
            <button
                onClick={() => setMostrarWidget(!mostrarWidget)}
                className="fixed bottom-24 right-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-110 z-50 flex items-center justify-center"
                title="Soporte"
            >
                {mostrarWidget ? (
                    <X className="w-6 h-6" />
                ) : (
                    <>
                        <MessageCircle className="w-6 h-6" />
                        {mensajesSinLeer > 0 && (
                            <span className="absolute -top-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white shadow-sm ring-2 ring-white">
                                {mensajesSinLeer > 9 ? '9+' : mensajesSinLeer}
                            </span>
                        )}
                    </>
                )}
            </button>

            {/* Widget desplegable */}
            {mostrarWidget && (
                <div className="fixed bottom-42 right-6 w-96 bg-white rounded-lg shadow-2xl z-50 overflow-hidden border border-gray-200">
                    {chatAbierto && ticketSeleccionado ? (
                        // Vista de Chat
                        <ChatSoporte
                            ticketId={ticketSeleccionado.id}
                            onClose={cerrarChat}
                            compact={true}
                        />
                    ) : (
                        // Vista de Lista de Tickets
                        <>
                            {/* Header */}
                            <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4 text-white">
                                <div className="flex items-center justify-between mb-2">
                                    <h3 className="text-lg font-bold">💬 Soporte</h3>
                                    {mensajesSinLeer > 0 && (
                                        <span className="px-2 py-1 bg-red-500 text-white text-xs font-bold rounded-full">
                                            {mensajesSinLeer} nuevo{mensajesSinLeer > 1 ? 's' : ''}
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-blue-100">¿Necesitas ayuda? Estamos aquí para ti</p>
                            </div>

                            {/* Acciones rápidas */}
                            <div className="p-4 border-b border-gray-200">
                                <div className="grid grid-cols-2 gap-3">
                                    <button
                                        onClick={irASoporte}
                                        className="flex items-center gap-2 px-4 py-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition text-sm font-medium"
                                    >
                                        <Plus className="w-4 h-4" />
                                        Nuevo Ticket
                                    </button>
                                    <button
                                        onClick={irASoporte}
                                        className="flex items-center gap-2 px-4 py-3 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition text-sm font-medium"
                                    >
                                        <List className="w-4 h-4" />
                                        Ver Todos
                                    </button>
                                </div>
                            </div>

                            {/* Tickets recientes */}
                            <div className="p-4">
                                <h4 className="text-sm font-semibold text-gray-700 mb-3">Tickets Abiertos</h4>

                                {loading ? (
                                    <div className="text-center py-6">
                                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                    </div>
                                ) : ticketsRecientes.length === 0 ? (
                                    <div className="text-center py-6">
                                        <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-2" />
                                        <p className="text-sm text-gray-500">No tienes tickets abiertos</p>
                                        <button
                                            onClick={irASoporte}
                                            className="mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
                                        >
                                            Crear tu primer ticket
                                        </button>
                                    </div>
                                ) : (
                                    <div className="space-y-2 max-h-64 overflow-y-auto">
                                        {ticketsRecientes.map((ticket) => {
                                            // SLA: tiempo desde última actualización
                                            const minsDesdeUpdate = ticket.fecha_actualizacion
                                                ? (Date.now() - new Date(ticket.fecha_actualizacion)) / 60000
                                                : null;
                                            const sla = minsDesdeUpdate === null ? null
                                                : minsDesdeUpdate < 60
                                                    ? { label: `${Math.round(minsDesdeUpdate)}m`, cls: 'text-green-600' }
                                                    : minsDesdeUpdate < 1440
                                                        ? { label: `${Math.round(minsDesdeUpdate / 60)}h`, cls: 'text-orange-500' }
                                                        : { label: `${Math.round(minsDesdeUpdate / 1440)}d`, cls: 'text-red-600' };

                                            const PRIORIDAD_COLORS = {
                                                Baja: 'bg-green-100 text-green-700',
                                                Media: 'bg-blue-100 text-blue-700',
                                                Alta: 'bg-orange-100 text-orange-700',
                                                Urgente: 'bg-red-100 text-red-700',
                                            };

                                            return (
                                                <div
                                                    key={ticket.id}
                                                    onClick={() => abrirChat(ticket)}
                                                    className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition"
                                                >
                                                    <div className="flex items-start justify-between mb-1">
                                                        <span className="font-mono text-xs font-semibold text-gray-700">
                                                            {ticket.numero_ticket}
                                                        </span>
                                                        <div className="flex items-center gap-1">
                                                            {/* Badge prioridad */}
                                                            {ticket.prioridad && ticket.prioridad !== 'Media' && (
                                                                <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${PRIORIDAD_COLORS[ticket.prioridad] || 'bg-gray-100 text-gray-700'}`}>
                                                                    {ticket.prioridad}
                                                                </span>
                                                            )}
                                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getEstadoColor(ticket.estado)}`}>
                                                                {ticket.estado}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <p className="text-sm font-medium text-gray-900 line-clamp-1">
                                                        {ticket.asunto}
                                                    </p>
                                                    {ticket.gestoria_nombre && (
                                                        <p className="text-xs text-gray-500 mt-1">
                                                            {ticket.gestoria_nombre} • {ticket.usuario_creador_nombre}
                                                        </p>
                                                    )}
                                                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
                                                        <Clock className="w-3 h-3" />
                                                        {new Date(ticket.fecha_creacion).toLocaleDateString('es-ES')}
                                                        {/* SLA badge */}
                                                        {sla && (
                                                            <span className={`font-semibold ${sla.cls}`}>
                                                                ⏱ {sla.label}
                                                            </span>
                                                        )}
                                                        {ticket.mensajes_sin_leer > 0 && (
                                                            <span className="ml-auto px-2 py-0.5 bg-red-500 text-white rounded-full font-bold">
                                                                {ticket.mensajes_sin_leer}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="p-3 bg-gray-50 border-t border-gray-200 text-center">
                                <button
                                    onClick={irASoporte}
                                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                                >
                                    Ver todos los tickets →
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}
        </>
    );
};

export default WidgetSoporte;
