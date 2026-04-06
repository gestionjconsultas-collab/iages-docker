// frontend/src/components/FloatingChatBubble.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { MessageSquare, X, Send, Loader2, Minimize2, Headphones } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function FloatingChatBubble() {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [conversacionId, setConversacionId] = useState(null);
    const [mostrarAutocomplete, setMostrarAutocomplete] = useState(false);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Historial de comandos
    const [historialComandos, setHistorialComandos] = useState([]);
    const [indiceHistorial, setIndiceHistorial] = useState(-1);
    const [inputTemporal, setInputTemporal] = useState('');

    // Comandos disponibles
    const comandosDisponibles = [
        { cmd: '/empresas', desc: 'Lista todas las empresas' },
        { cmd: '/docs [empresa]', desc: 'Documentos de una empresa' },
        { cmd: '/total [empresa]', desc: 'Total a pagar de RLC' },
        { cmd: '/rlc [empresa]', desc: 'Últimos RLC' },
        { cmd: '/nominas [empresa]', desc: 'Últimas nóminas' },
        { cmd: '/fiscal [empresa]', desc: 'Documentos fiscales' },
        { cmd: '/stats', desc: 'Estadísticas del sistema' },
        { cmd: '/help', desc: 'Ver ayuda' }
    ];

    useEffect(() => {
        // Cargar conversación guardada
        const savedConvId = localStorage.getItem('floating_chat_conversation_id');
        if (savedConvId) {
            setConversacionId(parseInt(savedConvId));
            cargarConversacion(parseInt(savedConvId));
        }

        // Escuchar evento de apertura del widget de soporte
        const handleSoporteOpen = () => {
            setIsOpen(false);
            setIsMinimized(false);
        };

        window.addEventListener('soporte-widget-opened', handleSoporteOpen);
        return () => window.removeEventListener('soporte-widget-opened', handleSoporteOpen);
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Mensaje de bienvenida
    useEffect(() => {
        if (isOpen && conversacionId && messages.length === 0) {
            setMessages([{
                rol: 'assistant',
                contenido: `¡Hola! 👋 Soy tu asistente de IA.

**Comandos rápidos:**
\`/empresas\` - Ver empresas
\`/docs [empresa]\` - Documentos
\`/total [empresa]\` - Total a pagar
\`/help\` - Ver ayuda

O pregúntame en lenguaje natural 💬`,
                fecha: new Date().toISOString()
            }]);
        }
    }, [isOpen, conversacionId, messages.length]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const cargarConversacion = async (id) => {
        try {
            const res = await axios.get(`/api/chat/conversacion/${id}`, {
                withCredentials: true
            });
            if (res.data.success) {
                setMessages(res.data.conversacion.mensajes);
            }
        } catch (error) {
            // Si la conversación no existe (404), limpiar localStorage y empezar de nuevo
            if (error.response?.status === 404) {
                console.log('Conversación no encontrada, iniciando nueva');
                localStorage.removeItem('floating_chat_conversation_id');
                setConversacionId(null);
                setMessages([]);
            } else {
                console.error('Error cargando conversación:', error);
            }
        }
    };

    const toggleChat = () => {
        if (isOpen) {
            setIsOpen(false);
            setIsMinimized(false);
        } else {
            setIsOpen(true);
            setIsMinimized(false);
            // Notificar al widget de soporte que se cierre
            window.dispatchEvent(new Event('ai-chat-opened'));
        }
    };

    // Cargar historial de comandos desde localStorage
    useEffect(() => {
        const historialGuardado = localStorage.getItem('floating_chat_command_history');
        if (historialGuardado) {
            try {
                setHistorialComandos(JSON.parse(historialGuardado));
            } catch (e) {
                console.error('Error cargando historial:', e);
            }
        }
    }, []);

    // Guardar historial cuando cambie
    useEffect(() => {
        if (historialComandos.length > 0) {
            localStorage.setItem('floating_chat_command_history', JSON.stringify(historialComandos));
        }
    }, [historialComandos]);

    const manejarTeclaHistorial = (e) => {
        if (historialComandos.length === 0) return;

        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (indiceHistorial === -1) {
                setInputTemporal(inputText);
            }
            const nuevoIndice = indiceHistorial + 1;
            if (nuevoIndice < historialComandos.length) {
                setIndiceHistorial(nuevoIndice);
                const comando = historialComandos[historialComandos.length - 1 - nuevoIndice];
                setInputText(comando);
                setMostrarAutocomplete(false);
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nuevoIndice = indiceHistorial - 1;
            if (nuevoIndice >= 0) {
                setIndiceHistorial(nuevoIndice);
                const comando = historialComandos[historialComandos.length - 1 - nuevoIndice];
                setInputText(comando);
                setMostrarAutocomplete(false);
            } else if (nuevoIndice === -1) {
                setIndiceHistorial(-1);
                setInputText(inputTemporal);
                setInputTemporal('');
                setMostrarAutocomplete(inputTemporal.startsWith('/'));
            }
        }
    };

    const minimizeChat = () => {
        setIsMinimized(!isMinimized);
    };

    const enviarPregunta = async (e) => {
        e.preventDefault();

        if (!inputText.trim()) return;

        setIsLoading(true);

        const mensajeUsuario = {
            rol: 'user',
            contenido: inputText,
            fecha: new Date().toISOString()
        };

        setMessages(prev => [...prev, mensajeUsuario]);
        const preguntaActual = inputText;

        // Agregar al historial de comandos
        setHistorialComandos(prev => {
            if (prev[prev.length - 1] === preguntaActual.trim()) {
                return prev;
            }
            const nuevoHistorial = [...prev, preguntaActual.trim()];
            return nuevoHistorial.slice(-50);
        });

        setIndiceHistorial(-1);
        setInputTemporal('');

        setInputText('');
        setMostrarAutocomplete(false);

        try {
            const res = await axios.post('/api/chat/preguntar', {
                pregunta: preguntaActual,
                conversacion_id: conversacionId
            }, {
                withCredentials: true
            });

            // Actualizar rate limit desde headers
            const rateLimitHeader = res.headers['x-ratelimit-remaining'];
            const rateLimitTotal = res.headers['x-ratelimit-limit'];

            if (rateLimitHeader && rateLimitTotal) {
                const restante = parseInt(rateLimitHeader);

                // Advertencia cuando quedan pocas preguntas
                if (restante <= 5 && restante > 0) {
                    toast.warning(`⚠️ Te quedan ${restante} preguntas`, {
                        duration: 3000
                    });
                }
            }

            if (res.data.success) {
                const mensajeAsistente = {
                    rol: 'assistant',
                    contenido: res.data.respuesta,
                    fecha: new Date().toISOString(),
                    tokens_usados: res.data.tokens_usados,
                    tiempo_respuesta: res.data.tiempo_respuesta
                };

                setMessages(prev => [...prev, mensajeAsistente]);

                if (!conversacionId) {
                    setConversacionId(res.data.conversacion_id);
                    localStorage.setItem('floating_chat_conversation_id', res.data.conversacion_id);
                }
            }

        } catch (error) {
            // Manejar error de rate limit (429)
            if (error.response?.status === 429) {
                const errorData = error.response.data;
                toast.error(errorData.mensaje || 'Has alcanzado el límite de preguntas por hora', {
                    duration: 5000,
                    icon: '⏱️'
                });
            } else {
                toast.error('Error al enviar pregunta');
            }

            setMessages(prev => prev.slice(0, -1));
            setInputText(preguntaActual);
        } finally {
            setIsLoading(false);
        }
    };

    const handleInputChange = (e) => {
        const valor = e.target.value;
        setInputText(valor);
        setMostrarAutocomplete(valor.startsWith('/') && valor.length > 0);
    };

    const seleccionarComando = (comando) => {
        setInputText(comando + ' ');
        setMostrarAutocomplete(false);
        inputRef.current?.focus();
    };

    const enviarComandoRapido = (comando) => {
        setInputText(comando);
        setTimeout(() => {
            const form = document.querySelector('form[onsubmit]');
            if (form) {
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }, 100);
    };

    const nuevaConversacion = () => {
        setMessages([]);
        setConversacionId(null);
        localStorage.removeItem('floating_chat_conversation_id');
        toast.success('Nueva conversación iniciada');
    };

    return (
        <>
            {/* Botón Flotante */}
            {!isOpen && (
                <button
                    onClick={toggleChat}
                    className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-110 flex items-center justify-center z-[60] group"
                    aria-label="Abrir chat IA"
                >
                    <MessageSquare className="w-6 h-6" />
                    <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white animate-pulse"></span>
                </button>
            )}

            {/* Ventana de Chat - Estilo Messenger */}
            {isOpen && (
                <div
                    className={`fixed bottom-6 right-6 w-[350px] bg-white rounded-2xl shadow-2xl z-[60] flex flex-col overflow-hidden transition-all duration-300 ${isMinimized ? 'h-14' : 'h-[500px]'
                        }`}
                    style={{
                        boxShadow: '0 12px 28px 0 rgba(0,0,0,0.2), 0 2px 4px 0 rgba(0,0,0,0.1)'
                    }}
                >
                    {/* Header - Estilo Messenger */}
                    <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-4 py-3 flex items-center justify-between cursor-pointer">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                                <MessageSquare className="w-5 h-5" />
                            </div>
                            <div>
                                <div className="font-semibold text-sm">Asistente IA</div>
                                <div className="text-xs text-orange-100">Siempre activo</div>
                            </div>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={minimizeChat}
                                className="p-1.5 hover:bg-white/20 rounded-full transition"
                                aria-label="Minimizar"
                            >
                                <Minimize2 className="w-4 h-4" />
                            </button>
                            <button
                                onClick={toggleChat}
                                className="p-1.5 hover:bg-white/20 rounded-full transition"
                                aria-label="Cerrar"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>

                    {!isMinimized && (
                        <>
                            {/* Mensajes */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
                                {messages.length === 0 && (
                                    <div className="text-center py-8">
                                        <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                                        <h3 className="text-base font-medium text-gray-900 mb-2">
                                            ¡Hola! 👋 Soy tu asistente de IA
                                        </h3>
                                        <p className="text-xs text-gray-600 mb-3">
                                            Puedo ayudarte con:
                                        </p>
                                        <ul className="text-left max-w-xs mx-auto space-y-1 text-xs text-gray-600 mb-4">
                                            <li>• Información sobre empresas y documentos</li>
                                            <li>• Cálculos de importes a pagar</li>
                                            <li>• Estadísticas del sistema</li>
                                        </ul>
                                        <div className="max-w-xs mx-auto bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                                            <p className="text-xs font-semibold text-blue-900 mb-2">⚡ Comandos rápidos:</p>
                                            <ul className="text-left text-xs text-blue-800 space-y-1">
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/empresas</code> - Ver empresas</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/docs [empresa]</code> - Documentos</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/total [empresa]</code> - Total a pagar</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/nominas [empresa]</code> - Nóminas</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/fiscal [empresa]</code> - Fiscales</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/stats</code> - Estadísticas</li>
                                                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded text-xs">/help</code> - Ayuda</li>
                                            </ul>
                                            <p className="text-xs text-blue-700 mt-2">💡 Estos comandos no gastan tokens</p>
                                        </div>
                                        <p className="text-xs text-gray-500">
                                            O pregúntame en lenguaje natural 💬
                                        </p>
                                    </div>
                                )}

                                {messages.map((mensaje, index) => (
                                    <div
                                        key={index}
                                        className={`flex ${mensaje.rol === 'user' ? 'justify-end' : 'justify-start'}`}
                                    >
                                        <div
                                            className={`max-w-[80%] px-3 py-2 rounded-2xl text-sm ${mensaje.rol === 'user'
                                                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-br-sm'
                                                : 'bg-white text-gray-800 shadow-sm border border-gray-200 rounded-bl-sm'
                                                }`}
                                        >
                                            {mensaje.rol === 'assistant' ? (
                                                <div className="prose prose-sm max-w-none">
                                                    <ReactMarkdown
                                                        components={{
                                                            a: ({ node, children, href, ...props }) => (
                                                                <a
                                                                    href={href}
                                                                    onClick={(e) => {
                                                                        e.preventDefault();
                                                                        if (href && href.startsWith('/')) {
                                                                            // Usar URL completa con origin
                                                                            window.location.href = window.location.origin + href;
                                                                        } else if (href) {
                                                                            window.open(href, '_blank');
                                                                        }
                                                                    }}
                                                                    className="text-blue-600 hover:text-blue-800 underline cursor-pointer font-medium"
                                                                    {...props}
                                                                >
                                                                    {children}
                                                                </a>
                                                            )
                                                        }}
                                                    >
                                                        {mensaje.contenido}
                                                    </ReactMarkdown>
                                                </div>
                                            ) : (
                                                <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
                                            )}
                                        </div>
                                    </div>
                                ))}

                                {isLoading && (
                                    <div className="flex justify-start">
                                        <div className="bg-white px-3 py-2 rounded-2xl shadow-sm border border-gray-200 rounded-bl-sm">
                                            <div className="flex items-center gap-2">
                                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                                <span className="text-sm text-gray-600">Pensando...</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>

                            {/* Input - Estilo Messenger */}
                            <div className="p-3 bg-white border-t border-gray-200">
                                <form onSubmit={enviarPregunta} className="flex items-center gap-2">
                                    <div className="flex-1 relative">
                                        {/* Autocomplete dropdown */}
                                        {mostrarAutocomplete && (
                                            <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto z-50">
                                                <div className="p-2 bg-gray-50 border-b border-gray-200">
                                                    <span className="text-xs text-gray-600 font-medium">Comandos:</span>
                                                </div>
                                                {comandosDisponibles
                                                    .filter(c => c.cmd.toLowerCase().startsWith(inputText.toLowerCase()))
                                                    .map((comando, idx) => (
                                                        <button
                                                            key={idx}
                                                            type="button"
                                                            onClick={() => seleccionarComando(comando.cmd)}
                                                            className="w-full text-left px-2 py-1.5 hover:bg-blue-50 transition-colors flex flex-col gap-0.5"
                                                        >
                                                            <span className="font-mono text-xs text-blue-600 font-medium">{comando.cmd}</span>
                                                            <span className="text-xs text-gray-500">{comando.desc}</span>
                                                        </button>
                                                    ))
                                                }
                                            </div>
                                        )}

                                        <input
                                            ref={inputRef}
                                            type="text"
                                            value={inputText}
                                            onChange={handleInputChange}
                                            onKeyDown={manejarTeclaHistorial}
                                            placeholder="Mensaje o /comandos..."
                                            disabled={isLoading}
                                            className="w-full px-3 py-2 bg-gray-100 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-gray-50"
                                        />
                                    </div>
                                    <button
                                        type="submit"
                                        disabled={isLoading || !inputText.trim()}
                                        className="w-9 h-9 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-full flex items-center justify-center hover:shadow-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                                        aria-label="Enviar"
                                    >
                                        <Send className="w-4 h-4" />
                                    </button>
                                </form>

                                {/* Command chips */}
                                <div className="flex gap-1.5 flex-wrap mt-2">
                                    <button
                                        onClick={() => enviarComandoRapido('/empresas')}
                                        type="button"
                                        className="px-2 py-1 bg-gradient-to-r from-blue-50 to-blue-100 hover:from-blue-100 hover:to-blue-200 text-blue-700 rounded-full text-xs font-medium transition-all flex items-center gap-1"
                                    >
                                        <span>📋</span>
                                        <span>Empresas</span>
                                    </button>
                                    <button
                                        onClick={() => enviarComandoRapido('/stats')}
                                        type="button"
                                        className="px-2 py-1 bg-gradient-to-r from-purple-50 to-purple-100 hover:from-purple-100 hover:to-purple-200 text-purple-700 rounded-full text-xs font-medium transition-all flex items-center gap-1"
                                    >
                                        <span>📊</span>
                                        <span>Stats</span>
                                    </button>
                                    <button
                                        onClick={() => enviarComandoRapido('/help')}
                                        type="button"
                                        className="px-2 py-1 bg-gradient-to-r from-gray-50 to-gray-100 hover:from-gray-100 hover:to-gray-200 text-gray-700 rounded-full text-xs font-medium transition-all flex items-center gap-1"
                                    >
                                        <span>❓</span>
                                        <span>Ayuda</span>
                                    </button>
                                    <button
                                        onClick={() => {
                                            setIsOpen(false);
                                            navigate('/soporte');
                                            toast.success('Abriendo sistema de soporte...');
                                        }}
                                        type="button"
                                        className="px-2 py-1 bg-gradient-to-r from-orange-50 to-orange-100 hover:from-orange-100 hover:to-orange-200 text-primary-hover rounded-full text-xs font-medium transition-all flex items-center gap-1"
                                        title="¿La IA no pudo ayudarte? Contacta con soporte humano"
                                    >
                                        <Headphones className="w-3 h-3" />
                                        <span>Soporte</span>
                                    </button>
                                </div>

                                {messages.length > 0 && (
                                    <button
                                        onClick={nuevaConversacion}
                                        className="text-xs text-gray-500 hover:text-primary mt-2 transition"
                                    >
                                        + Nueva conversación
                                    </button>
                                )}
                            </div>
                        </>
                    )}
                </div>
            )}
        </>
    );
}
