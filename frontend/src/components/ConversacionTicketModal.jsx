// frontend/src/components/ConversacionTicketModal.jsx
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { X, Send, Clock, CheckCircle, User, Headphones } from 'lucide-react';

const ConversacionTicketModal = ({ ticket, onClose }) => {
    const [mensajes, setMensajes] = useState([]);
    const [nuevoMensaje, setNuevoMensaje] = useState('');
    const [enviando, setEnviando] = useState(false);
    const [loading, setLoading] = useState(true);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        cargarMensajes();
    }, [ticket.id]);

    useEffect(() => {
        scrollToBottom();
    }, [mensajes]);

    const cargarMensajes = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/soporte/tickets/${ticket.id}/mensajes`, { withCredentials: true });

            if (response.data.success) {
                setMensajes(response.data.mensajes);
            }
        } catch (error) {
            console.error('Error cargando mensajes:', error);
            toast.error('Error al cargar mensajes');
        } finally {
            setLoading(false);
        }
    };

    const enviarMensaje = async (e) => {
        e.preventDefault();

        if (!nuevoMensaje.trim()) return;

        try {
            setEnviando(true);
            const response = await axios.post(
                `/api/soporte/tickets/${ticket.id}/mensajes`,
                { mensaje: nuevoMensaje },
                { withCredentials: true }
            );

            if (response.data.success) {
                setMensajes([...mensajes, response.data.mensaje]);
                setNuevoMensaje('');
            }
        } catch (error) {
            console.error('Error enviando mensaje:', error);
            toast.error('Error al enviar mensaje');
        } finally {
            setEnviando(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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

    const esAgente = (mensaje) => {
        return mensaje.usuario_rol === 'admin' || mensaje.usuario_rol === 'soporte';
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full h-[80vh] flex flex-col">
                {/* Header */}
                <div className="flex justify-between items-start p-6 border-b border-gray-200">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <span className="font-mono text-sm font-semibold text-gray-700">
                                {ticket.numero_ticket}
                            </span>
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${getEstadoColor(ticket.estado)}`}>
                                {ticket.estado}
                            </span>
                        </div>
                        <h2 className="text-xl font-bold text-gray-900 mb-2">{ticket.asunto}</h2>
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                            <span className="flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                {new Date(ticket.fecha_creacion).toLocaleDateString('es-ES', {
                                    year: 'numeric',
                                    month: 'long',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </span>
                            {ticket.asignado_a_nombre && (
                                <span className="flex items-center gap-1">
                                    <Headphones className="w-4 h-4" />
                                    Atendido por: {ticket.asignado_a_nombre}
                                </span>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Descripción inicial (si existe) */}
                {ticket.descripcion && (
                    <div className="p-4 bg-gray-50 border-b border-gray-200">
                        <p className="text-sm text-gray-700">{ticket.descripcion}</p>
                    </div>
                )}

                {/* Mensajes */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                    {loading ? (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="text-gray-600 mt-2 text-sm">Cargando conversación...</p>
                        </div>
                    ) : mensajes.length === 0 ? (
                        <div className="text-center py-8">
                            <p className="text-gray-500">No hay mensajes aún</p>
                            <p className="text-gray-400 text-sm mt-1">Escribe el primer mensaje para iniciar la conversación</p>
                        </div>
                    ) : (
                        mensajes.map((mensaje) => (
                            <div
                                key={mensaje.id}
                                className={`flex ${esAgente(mensaje) ? 'justify-start' : 'justify-end'}`}
                            >
                                <div className={`flex gap-3 max-w-[70%] ${esAgente(mensaje) ? 'flex-row' : 'flex-row-reverse'}`}>
                                    {/* Avatar */}
                                    <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${esAgente(mensaje) ? 'bg-blue-100' : 'bg-gray-200'
                                        }`}>
                                        {esAgente(mensaje) ? (
                                            <Headphones className="w-4 h-4 text-blue-600" />
                                        ) : (
                                            <User className="w-4 h-4 text-gray-600" />
                                        )}
                                    </div>

                                    {/* Mensaje */}
                                    <div className={`flex flex-col ${esAgente(mensaje) ? 'items-start' : 'items-end'}`}>
                                        <div className={`px-4 py-2 rounded-lg ${esAgente(mensaje)
                                                ? 'bg-white border border-gray-200'
                                                : 'bg-blue-600 text-white'
                                            }`}>
                                            <p className="text-sm font-medium mb-1">
                                                {mensaje.usuario_nombre}
                                            </p>
                                            <p className="text-sm whitespace-pre-wrap">{mensaje.mensaje}</p>
                                        </div>
                                        <span className="text-xs text-gray-500 mt-1">
                                            {new Date(mensaje.fecha_creacion).toLocaleTimeString('es-ES', {
                                                hour: '2-digit',
                                                minute: '2-digit'
                                            })}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input de mensaje */}
                <div className="p-4 border-t border-gray-200 bg-white">
                    {ticket.estado === 'Cerrado' ? (
                        <div className="text-center py-4 bg-gray-50 rounded-lg">
                            <CheckCircle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                            <p className="text-gray-600 font-medium">Este ticket está cerrado</p>
                            <p className="text-gray-500 text-sm mt-1">
                                No se pueden enviar más mensajes
                            </p>
                        </div>
                    ) : (
                        <form onSubmit={enviarMensaje} className="flex gap-3">
                            <input
                                type="text"
                                value={nuevoMensaje}
                                onChange={(e) => setNuevoMensaje(e.target.value)}
                                placeholder="Escribe tu mensaje..."
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                disabled={enviando}
                            />
                            <button
                                type="submit"
                                disabled={enviando || !nuevoMensaje.trim()}
                                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {enviando ? (
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                ) : (
                                    <Send className="w-4 h-4" />
                                )}
                                Enviar
                            </button>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ConversacionTicketModal;
