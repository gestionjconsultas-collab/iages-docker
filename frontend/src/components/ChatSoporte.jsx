// frontend/src/components/ChatSoporte.jsx
// v2: respuestas rápidas, notas internas, reconexión auto, agente online,
//     transferir ticket, paginación, adjuntos, read receipts RT
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, Send, Paperclip, Star, ChevronUp, UserCheck, Lock, Repeat2 } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../AuthContext';
import socket from '../socket';
import MensajeBurbuja from './MensajeBurbuja';
import toast from 'react-hot-toast';

// ---------------------------------------------------------------------------
// Respuestas rápidas predefinidas
// ---------------------------------------------------------------------------
const RESPUESTAS_RAPIDAS = [
    'Hola, un momento por favor, estoy revisando su caso.',
    'Hemos recibido su solicitud y la estamos procesando.',
    '¿Puede darme más detalles para ayudarle mejor?',
    'Le informamos que su consulta ha quedado registrada.',
    'Gracias por su paciencia, enseguida le atendemos.',
    'Su caso ha sido escalado al equipo correspondiente.',
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const ChatSoporte = ({ ticketId, onClose, compact = false }) => {
    const { user } = useAuth();

    // Estado principal
    const [ticket,             setTicket]             = useState(null);
    const [mensajes,           setMensajes]           = useState([]);
    const [nuevoMensaje,       setNuevoMensaje]       = useState('');
    const [usuarioEscribiendo, setUsuarioEscribiendo] = useState(null);
    const [mostrarRating,      setMostrarRating]      = useState(false);
    const [loading,            setLoading]            = useState(true);

    // Paginación
    const [page,        setPage]        = useState(1);
    const [hasMore,     setHasMore]     = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);

    // Extras agente
    const [esInterno,        setEsInterno]        = useState(false);
    const [mostrarRapidas,   setMostrarRapidas]   = useState(false);
    const [agenteOnline,     setAgenteOnline]     = useState(null); // true/false/null
    const [mostrarTransferir,setMostrarTransferir]= useState(false);
    const [agentes,          setAgentes]          = useState([]);

    const messagesEndRef   = useRef(null);
    const typingTimeoutRef = useRef(null);
    const fileInputRef     = useRef(null);
    const escribiendoRef   = useRef(false);

    // Helpers de rol
    const esSoporte  = user.departamento === 'Soporte' || user.is_super_admin;
    const esCreador  = ticket?.usuario_creador_id === user.id;
    const esAsignado = ticket?.asignado_a_id === user.id;

    // -----------------------------------------------------------------------
    // Scroll
    // -----------------------------------------------------------------------
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => { scrollToBottom(); }, [mensajes]);

    // -----------------------------------------------------------------------
    // Carga inicial de datos
    // -----------------------------------------------------------------------
    const cargarDatos = useCallback(async (pg = 1, append = false) => {
        try {
            if (!append) setLoading(true); else setLoadingMore(true);

            const [ticketRes, mensajesRes] = await Promise.all([
                axios.get(`/api/soporte/tickets/${ticketId}`,                           { withCredentials: true }),
                axios.get(`/api/soporte/tickets/${ticketId}/mensajes?page=${pg}&per_page=50`, { withCredentials: true }),
            ]);

            if (ticketRes.data.success)   setTicket(ticketRes.data.ticket);
            if (mensajesRes.data.success) {
                const nuevos = mensajesRes.data.mensajes;
                if (append) {
                    setMensajes(prev => [...nuevos, ...prev]);
                } else {
                    setMensajes(nuevos);
                    setTimeout(scrollToBottom, 50);
                }
                setHasMore(mensajesRes.data.has_next ?? false);
                setPage(pg);
            }
        } catch (err) {
            console.error('Error cargando datos:', err);
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [ticketId, scrollToBottom]);

    useEffect(() => { cargarDatos(1); }, [ticketId]);

    // -----------------------------------------------------------------------
    // Agente online
    // -----------------------------------------------------------------------
    useEffect(() => {
        if (!ticket?.asignado_a_id) return;
        axios.get(`/api/soporte/agente-online/${ticket.asignado_a_id}`, { withCredentials: true })
            .then(r => setAgenteOnline(r.data.online))
            .catch(() => setAgenteOnline(null));
    }, [ticket?.asignado_a_id]);

    // -----------------------------------------------------------------------
    // Cargar agentes para transferencia
    // -----------------------------------------------------------------------
    const cargarAgentes = async () => {
        try {
            const r = await axios.get('/api/soporte/agentes', { withCredentials: true });
            if (r.data.success) setAgentes(r.data.agentes.filter(a => a.id !== user.id));
        } catch (e) { console.error(e); }
    };

    const abrirTransferir = () => {
        cargarAgentes();
        setMostrarTransferir(true);
    };

    const transferirA = async (agenteId) => {
        try {
            const r = await axios.post(`/api/soporte/tickets/${ticketId}/transferir`,
                { agente_id: agenteId }, { withCredentials: true });
            if (r.data.success) {
                toast.success('Ticket transferido correctamente');
                setMostrarTransferir(false);
                cargarDatos(1);
            }
        } catch (e) { toast.error('Error al transferir'); }
    };

    // -----------------------------------------------------------------------
    // WebSocket
    // -----------------------------------------------------------------------
    useEffect(() => {
        let joined = false;
        const joinTimer = setTimeout(() => {
            socket.emit('join_ticket', { ticket_id: ticketId });
            joined = true;
        }, 100);

        // Handlers nombrados
        const handleNuevoMensaje = (data) => {
            if (Number(data.ticket_id) !== Number(ticketId)) return;
            setMensajes(prev => {
                if (prev.some(m => m.id === data.mensaje.id)) return prev;
                return [...prev, data.mensaje];
            });
            if (Number(data.mensaje.usuario_id) !== Number(user.id)) {
                _beep(600);
                window.dispatchEvent(new Event('nuevo_mensaje_soporte'));
            }
        };

        const handleMensajesLeidos = (data) => {
            if (Number(data.ticket_id) !== Number(ticketId)) return;
            if (Number(data.leido_por) === Number(user.id)) return;
            // Marcar todos los mensajes míos como leídos
            setMensajes(prev => prev.map(m =>
                Number(m.usuario_id) === Number(user.id) ? { ...m, leido: true } : m
            ));
        };

        const handleTicketAsignado = (data) => {
            if (Number(data.ticket_id) === Number(ticketId)) cargarDatos(1);
        };

        const handleTicketTransferido = (data) => {
            if (Number(data.ticket_id) === Number(ticketId)) {
                cargarDatos(1);
                toast.success(`Ticket transferido a ${data.nuevo_agente}`);
            }
        };

        const handleTicketFinalizado = (data) => {
            if (Number(data.ticket_id) === Number(ticketId)) {
                cargarDatos(1);
                setMostrarRating(true);
            }
        };

        const handleTicketValorado = (data) => {
            if (Number(data.ticket_id) === Number(ticketId)) cargarDatos(1);
        };

        const handleEscribiendo = (data) => {
            if (Number(data.ticket_id) !== Number(ticketId)) return;
            if (data.usuario_id === user.id) return;
            setUsuarioEscribiendo(data.usuario || 'Alguien');
            setTimeout(() => setUsuarioEscribiendo(null), 3000);
        };

        // Auto-rejoin al reconectar el socket
        const handleReconnect = () => {
            console.log('🔄 Socket reconectado, re-uniéndose al room...');
            socket.emit('join_ticket', { ticket_id: ticketId });
        };

        socket.on('nuevo_mensaje_soporte',    handleNuevoMensaje);
        socket.on('mensajes_leidos',          handleMensajesLeidos);
        socket.on('ticket_asignado',          handleTicketAsignado);
        socket.on('ticket_transferido',       handleTicketTransferido);
        socket.on('ticket_finalizado',        handleTicketFinalizado);
        socket.on('ticket_valorado',          handleTicketValorado);
        socket.on('usuario_escribiendo_soporte', handleEscribiendo);
        socket.on('reconnect',                handleReconnect);
        socket.on('connect',                  handleReconnect); // también en reconexiones

        return () => {
            clearTimeout(joinTimer);
            if (joined) socket.emit('leave_ticket', { ticket_id: ticketId });
            socket.off('nuevo_mensaje_soporte',       handleNuevoMensaje);
            socket.off('mensajes_leidos',             handleMensajesLeidos);
            socket.off('ticket_asignado',             handleTicketAsignado);
            socket.off('ticket_transferido',          handleTicketTransferido);
            socket.off('ticket_finalizado',           handleTicketFinalizado);
            socket.off('ticket_valorado',             handleTicketValorado);
            socket.off('usuario_escribiendo_soporte', handleEscribiendo);
            socket.off('reconnect',                   handleReconnect);
            socket.off('connect',                     handleReconnect);
        };
    }, [ticketId, user.id]);

    // -----------------------------------------------------------------------
    // Enviar mensaje
    // -----------------------------------------------------------------------
    const enviarMensaje = async () => {
        if (!nuevoMensaje.trim()) return;
        const texto = nuevoMensaje.trim();
        setNuevoMensaje('');
        setMostrarRapidas(false);

        try {
            const r = await axios.post(
                `/api/soporte/tickets/${ticketId}/mensajes`,
                { mensaje: texto, es_interno: esInterno },
                { withCredentials: true }
            );
            if (r.data.success) {
                const msj = r.data.mensaje;
                if (msj) {
                    setMensajes(prev =>
                        prev.some(m => m.id === msj.id) ? prev : [...prev, msj]
                    );
                }
            } else {
                setNuevoMensaje(texto);
                toast.error('Error al enviar mensaje');
            }
        } catch (e) {
            setNuevoMensaje(texto);
            toast.error('Error al enviar mensaje');
        }
    };

    // -----------------------------------------------------------------------
    // Adjuntos
    // -----------------------------------------------------------------------
    const subirAdjunto = async (e) => {
        const archivo = e.target.files?.[0];
        if (!archivo) return;
        const fd = new FormData();
        fd.append('archivo', archivo);
        try {
            const r = await axios.post(
                `/api/soporte/tickets/${ticketId}/adjuntos`,
                fd,
                { withCredentials: true, headers: { 'Content-Type': 'multipart/form-data' } }
            );
            if (!r.data.success) toast.error('Error subiendo adjunto');
        } catch (e) {
            toast.error('Error subiendo adjunto');
        }
        e.target.value = '';
    };

    // -----------------------------------------------------------------------
    // Typing
    // -----------------------------------------------------------------------
    const handleTyping = () => {
        if (!escribiendoRef.current) {
            escribiendoRef.current = true;
            socket.emit('typing_soporte', { ticket_id: ticketId });
        }
        clearTimeout(typingTimeoutRef.current);
        typingTimeoutRef.current = setTimeout(() => {
            escribiendoRef.current = false;
        }, 3000);
    };

    // -----------------------------------------------------------------------
    // Acciones agente
    // -----------------------------------------------------------------------
    const tomarTicket = async () => {
        try {
            await axios.post(`/api/soporte/tickets/${ticketId}/tomar`, {}, { withCredentials: true });
            toast.success('Ticket asignado correctamente');
        } catch (e) {
            toast.error(e.response?.data?.error || 'Error al tomar ticket');
        }
    };

    const finalizarTicket = async () => {
        try {
            await axios.post(`/api/soporte/tickets/${ticketId}/finalizar`, {}, { withCredentials: true });
            toast.success('Ticket finalizado');
        } catch (e) {
            toast.error('Error al finalizar ticket');
        }
    };

    const valorarTicket = async (estrellas) => {
        try {
            await axios.post(`/api/soporte/tickets/${ticketId}/valorar`,
                { valoracion: estrellas }, { withCredentials: true });
            toast.success('¡Gracias por su valoración!');
        } catch (e) {
            toast.error('Error al enviar valoración');
        }
    };

    // -----------------------------------------------------------------------
    // SLA: tiempo sin respuesta
    // -----------------------------------------------------------------------
    const calcularSLA = () => {
        if (!ticket?.fecha_actualizacion) return null;
        const mins = (Date.now() - new Date(ticket.fecha_actualizacion)) / 60000;
        if (mins < 60)    return { label: `${Math.round(mins)}m`, color: 'text-green-600' };
        if (mins < 1440)  return { label: `${Math.round(mins / 60)}h`, color: 'text-orange-500' };
        return { label: `${Math.round(mins / 1440)}d`, color: 'text-red-600' };
    };

    const sla = calcularSLA();

    // -----------------------------------------------------------------------
    // Prioridad
    // -----------------------------------------------------------------------
    const PRIORIDAD_COLORS = {
        Baja:    'bg-green-100 text-green-800',
        Media:   'bg-blue-100 text-blue-800',
        Alta:    'bg-orange-100 text-orange-800',
        Urgente: 'bg-red-100 text-red-800',
    };

    // -----------------------------------------------------------------------
    // Loading
    // -----------------------------------------------------------------------
    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
            </div>
        );
    }

    const containerClass = compact
        ? 'flex flex-col h-[500px] bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800'
        : 'fixed inset-0 bg-white dark:bg-slate-900 z-[60] flex flex-col';

    return (
        <div className={containerClass}>
            {/* ── Header ── */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4 flex items-center justify-between shadow-md">
                <div className="flex items-center gap-3">
                    <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-full transition">
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h3 className="font-bold text-lg flex items-center gap-2">
                            💬 Soporte
                            {/* Prioridad */}
                            {ticket?.prioridad && (
                                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${PRIORIDAD_COLORS[ticket.prioridad] || 'bg-gray-100 text-gray-800'}`}>
                                    {ticket.prioridad}
                                </span>
                            )}
                        </h3>
                        <p className="text-xs text-blue-100 flex items-center gap-2">
                            Ticket #{ticket?.numero_ticket} • {ticket?.estado}
                            {/* SLA */}
                            {sla && (
                                <span className={`font-semibold ${sla.color} bg-white/20 px-1.5 py-0.5 rounded text-xs`}>
                                    ⏱ {sla.label}
                                </span>
                            )}
                        </p>
                        {ticket?.gestoria_nombre && (
                            <p className="text-xs text-blue-200 mt-0.5 flex items-center gap-2">
                                {ticket.gestoria_nombre} • {ticket.usuario_creador_nombre}
                                {/* Agente online */}
                                {ticket?.asignado_a_nombre && (
                                    <span className="flex items-center gap-1">
                                        <span className={`w-2 h-2 rounded-full inline-block ${agenteOnline ? 'bg-green-400' : 'bg-gray-400'}`} />
                                        {ticket.asignado_a_nombre}
                                    </span>
                                )}
                            </p>
                        )}
                    </div>
                </div>
                {/* Botón transferir (solo agentes) */}
                {esSoporte && ticket?.asignado_a_id && (
                    <button onClick={abrirTransferir}
                        className="p-2 hover:bg-white/10 rounded-lg transition text-xs flex items-center gap-1"
                        title="Transferir ticket">
                        <Repeat2 className="w-4 h-4" />
                    </button>
                )}
            </div>

            {/* ── Modal Transferir ── */}
            {mostrarTransferir && (
                <div className="absolute inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-5">
                        <h4 className="font-bold text-gray-900 mb-4">Transferir ticket a:</h4>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {agentes.length === 0
                                ? <p className="text-sm text-gray-500">No hay otros agentes disponibles</p>
                                : agentes.map(a => (
                                    <button key={a.id} onClick={() => transferirA(a.id)}
                                        className="w-full text-left px-4 py-2 rounded-lg hover:bg-blue-50 text-sm text-gray-800 border border-gray-200 flex items-center gap-2">
                                        <UserCheck className="w-4 h-4 text-blue-500" />
                                        {a.nombre}
                                    </button>
                                ))
                            }
                        </div>
                        <button onClick={() => setMostrarTransferir(false)}
                            className="mt-4 w-full py-2 text-sm text-gray-500 hover:text-gray-700 border rounded-lg">
                            Cancelar
                        </button>
                    </div>
                </div>
            )}

            {/* ── Tomar Ticket ── */}
            {esSoporte && !ticket?.asignado_a_id && (
                <div className="p-4 bg-blue-50 border-b border-blue-100">
                    <button onClick={tomarTicket}
                        className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-semibold flex items-center justify-center gap-2 transition shadow-sm">
                        📋 Tomar Ticket
                    </button>
                </div>
            )}

            {/* ── Cargar más mensajes ── */}
            {hasMore && (
                <div className="flex justify-center p-2 border-b border-gray-100">
                    <button onClick={() => cargarDatos(page + 1, true)} disabled={loadingMore}
                        className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400">
                        <ChevronUp className="w-4 h-4" />
                        {loadingMore ? 'Cargando...' : 'Ver mensajes anteriores'}
                    </button>
                </div>
            )}

            {/* ── Mensajes ── */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 dark:bg-slate-950 pb-20 md:pb-4">
                {mensajes.map(m => (
                    <MensajeBurbuja key={m.id} mensaje={m} currentUserId={user.id} />
                ))}

                {usuarioEscribiendo && (
                    <div className="flex items-center gap-2 text-sm text-gray-500 italic">
                        <div className="flex gap-1">
                            {[0, 0.1, 0.2].map((d, i) => (
                                <span key={i} className="animate-bounce" style={{ animationDelay: `${d}s` }}>●</span>
                            ))}
                        </div>
                        {usuarioEscribiendo} está escribiendo...
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* ── Rating ── */}
            {mostrarRating && esCreador && !ticket?.valoracion && (
                <div className="p-4 bg-yellow-50 border-t border-yellow-200">
                    <p className="text-sm font-medium text-gray-800 mb-3 text-center">¿Cómo calificaría nuestro servicio?</p>
                    <div className="flex gap-2 justify-center">
                        {[1, 2, 3, 4, 5].map(s => (
                            <button key={s} onClick={() => valorarTicket(s)}
                                className="text-4xl hover:scale-125 transition-transform">⭐</button>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Finalizar ── */}
            {esAsignado && ticket?.estado !== 'Resuelto' && ticket?.estado !== 'Cerrado' && (
                <div className="p-3 bg-gray-50 border-t">
                    <button onClick={finalizarTicket}
                        className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-semibold flex items-center justify-center gap-2 transition">
                        ✅ Finalizar Ticket
                    </button>
                </div>
            )}

            {/* ── Input de mensaje ── */}
            {ticket?.estado !== 'Cerrado' && (
                <div className="p-3 bg-white dark:bg-slate-900 border-t border-gray-200 dark:border-slate-800 relative z-10">
                    {/* Toggle nota interna (solo agentes) */}
                    {esSoporte && (
                        <div className="flex items-center gap-2 mb-2">
                            <button onClick={() => setEsInterno(v => !v)}
                                className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full border transition ${esInterno
                                    ? 'bg-amber-100 border-amber-400 text-amber-700 font-semibold'
                                    : 'bg-gray-100 border-gray-300 text-gray-500'}`}>
                                <Lock className="w-3 h-3" />
                                {esInterno ? 'Nota interna' : 'Pública'}
                            </button>

                            {/* Respuestas rápidas */}
                            <button onClick={() => setMostrarRapidas(v => !v)}
                                className="text-xs px-2 py-1 rounded-full border bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200 transition">
                                ⚡ Rápidas
                            </button>
                        </div>
                    )}

                    {/* Desplegable respuestas rápidas */}
                    {mostrarRapidas && (
                        <div className="mb-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-36 overflow-y-auto">
                            {RESPUESTAS_RAPIDAS.map((r, i) => (
                                <button key={i}
                                    onClick={() => { setNuevoMensaje(r); setMostrarRapidas(false); }}
                                    className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-blue-50 border-b border-gray-100 last:border-0">
                                    {r}
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="flex items-center gap-2 max-w-4xl mx-auto w-full">
                        {/* Adjunto */}
                        <button onClick={() => fileInputRef.current?.click()}
                            className="p-2 text-gray-400 hover:text-gray-600 transition flex-shrink-0"
                            title="Adjuntar archivo">
                            <Paperclip className="w-5 h-5" />
                        </button>
                        <input ref={fileInputRef} type="file" className="hidden"
                            accept="image/png,image/jpeg,image/gif,image/webp"
                            onChange={subirAdjunto} />

                        <input
                            type="text"
                            value={nuevoMensaje}
                            onChange={e => { setNuevoMensaje(e.target.value); handleTyping(); }}
                            onKeyPress={e => e.key === 'Enter' && enviarMensaje()}
                            placeholder={esInterno ? '🔒 Nota interna (solo equipo)...' : 'Escribe un mensaje...'}
                            className={`flex-1 px-4 py-3 border rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm
                                ${esInterno
                                    ? 'border-amber-300 bg-amber-50 dark:bg-amber-900/20 text-gray-900 dark:text-gray-100'
                                    : 'border-gray-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100'}`}
                        />
                        <button onClick={enviarMensaje} disabled={!nuevoMensaje.trim()}
                            className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed transition shadow-md flex-shrink-0">
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

// ---------------------------------------------------------------------------
// Beep helper
// ---------------------------------------------------------------------------
function _beep(freq = 600) {
    try {
        const ctx  = new AudioContext();
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        osc.type = 'sine';
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.2);
    } catch (_) { /* no disponible */ }
}

export default ChatSoporte;
