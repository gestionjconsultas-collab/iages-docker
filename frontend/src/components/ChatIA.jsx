// frontend/src/components/ChatIA.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { Send, Loader2, MessageSquare, Trash2, Plus, BarChart3, Headphones } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// 🆕 Utilidad para detectar y convertir nombres de archivos PDF en enlaces
const linkifyPDFNames = async (text, navigate) => {
    // Regex mejorado para detectar nombres de archivos PDF con espacios
    // Captura desde el inicio de palabra hasta .pdf
    const pdfRegex = /([A-Z0-9][A-Z0-9_\-\.\s]+\.pdf)/gi;

    const matches = text.match(pdfRegex);

    console.log('🔍 [PDF Links] Buscando PDFs en texto:', text.substring(0, 100));
    console.log('🔍 [PDF Links] Matches encontrados:', matches);

    if (!matches) return text;

    // Eliminar duplicados
    const uniqueMatches = [...new Set(matches)];
    console.log('🔍 [PDF Links] PDFs únicos:', uniqueMatches);

    let processedText = text;

    // Procesar cada nombre de archivo encontrado
    for (const pdfName of uniqueMatches) {
        try {
            console.log(`🔍 [PDF Links] Buscando documento: ${pdfName}`);

            // Buscar documento en el backend
            const res = await axios.post('/api/documentos/buscar-por-nombre', {
                nombre_archivo: pdfName
            }, { withCredentials: true });

            if (res.data.success) {
                const doc = res.data.documento;
                console.log(`✅ [PDF Links] Documento encontrado:`, doc);

                // Reemplazar nombre de archivo con enlace markdown
                const link = `[${pdfName}](${doc.url})`;
                processedText = processedText.replace(new RegExp(pdfName, 'g'), link);

                console.log(`✅ [PDF Links] Enlace creado: ${link}`);
            }
        } catch (error) {
            // Si no se encuentra el documento, dejar el nombre sin enlace
            console.log(`❌ [PDF Links] Documento no encontrado: ${pdfName}`, error.response?.data);
        }
    }

    console.log('📝 [PDF Links] Texto procesado:', processedText.substring(0, 200));
    return processedText;
};

export default function ChatIA() {
    const navigate = useNavigate();
    const [conversaciones, setConversaciones] = useState([]);
    const [conversacionActual, setConversacionActual] = useState(null);
    const [mensajes, setMensajes] = useState([]);
    const [pregunta, setPregunta] = useState('');
    const [enviando, setEnviando] = useState(false);
    const [cargando, setCargando] = useState(false);
    const [estadisticas, setEstadisticas] = useState(null);
    const [mostrarAutocomplete, setMostrarAutocomplete] = useState(false);
    const [rateLimitInfo, setRateLimitInfo] = useState({
        limite: 20,
        restante: 20,
        usado: 0,
        mostrar: false
    });
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
        cargarConversaciones();
        cargarEstadisticas();
        cargarRateLimitStatus();
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [mensajes]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const cargarConversaciones = async () => {
        try {
            const res = await axios.get('/api/chat/conversaciones', {
                withCredentials: true
            });
            if (res.data.success) {
                setConversaciones(res.data.conversaciones);
            }
        } catch (error) {
            console.error('Error cargando conversaciones:', error);
        }
    };

    const cargarEstadisticas = async () => {
        try {
            const res = await axios.get('/api/chat/estadisticas', {
                withCredentials: true
            });
            if (res.data.success) {
                setEstadisticas(res.data.estadisticas);
            }
        } catch (error) {
            console.error('Error cargando estadísticas:', error);
        }
    };

    const cargarRateLimitStatus = async () => {
        try {
            const res = await axios.get('/api/chat/rate-limit/status', {
                withCredentials: true
            });
            if (res.data.success) {
                const { limite, requests_usados, requests_restantes } = res.data.rate_limit;
                setRateLimitInfo({
                    limite,
                    usado: requests_usados,
                    restante: requests_restantes,
                    mostrar: true
                });
            }
        } catch (error) {
            console.error('Error cargando rate limit:', error);
        }
    };

    const cargarConversacion = async (id) => {
        setCargando(true);
        try {
            const res = await axios.get(`/api/chat/conversacion/${id}`, {
                withCredentials: true
            });
            if (res.data.success) {
                setConversacionActual(res.data.conversacion);
                setMensajes(res.data.conversacion.mensajes);
            }
        } catch (error) {
            toast.error('Error cargando conversación');
        } finally {
            setCargando(false);
        }
    };

    const nuevaConversacion = () => {
        setConversacionActual(null);
        setMensajes([]);
        setPregunta('');
    };

    // Cargar historial de comandos desde localStorage
    useEffect(() => {
        const historialGuardado = localStorage.getItem('chat_command_history');
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
            localStorage.setItem('chat_command_history', JSON.stringify(historialComandos));
        }
    }, [historialComandos]);

    const manejarTeclaHistorial = (e) => {
        // Solo procesar si hay historial
        if (historialComandos.length === 0) return;

        if (e.key === 'ArrowUp') {
            e.preventDefault();

            // Guardar input actual si es la primera vez
            if (indiceHistorial === -1) {
                setInputTemporal(pregunta);
            }

            // Navegar hacia atrás en el historial
            const nuevoIndice = indiceHistorial + 1;
            if (nuevoIndice < historialComandos.length) {
                setIndiceHistorial(nuevoIndice);
                const comando = historialComandos[historialComandos.length - 1 - nuevoIndice];
                setPregunta(comando);
                setMostrarAutocomplete(false);
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();

            // Navegar hacia adelante en el historial
            const nuevoIndice = indiceHistorial - 1;

            if (nuevoIndice >= 0) {
                setIndiceHistorial(nuevoIndice);
                const comando = historialComandos[historialComandos.length - 1 - nuevoIndice];
                setPregunta(comando);
                setMostrarAutocomplete(false);
            } else if (nuevoIndice === -1) {
                // Volver al input temporal
                setIndiceHistorial(-1);
                setPregunta(inputTemporal);
                setInputTemporal('');
                setMostrarAutocomplete(inputTemporal.startsWith('/'));
            }
        }
    };

    const enviarPregunta = async (e) => {
        e.preventDefault();

        if (!pregunta.trim()) return;

        setEnviando(true);

        // Agregar mensaje del usuario inmediatamente
        const mensajeUsuario = {
            rol: 'user',
            contenido: pregunta,
            fecha: new Date().toISOString()
        };

        setMensajes(prev => [...prev, mensajeUsuario]);
        const preguntaActual = pregunta;

        // Agregar al historial de comandos
        setHistorialComandos(prev => {
            // Evitar duplicados consecutivos
            if (prev[prev.length - 1] === preguntaActual.trim()) {
                return prev;
            }
            // Limitar a últimos 50 comandos
            const nuevoHistorial = [...prev, preguntaActual.trim()];
            return nuevoHistorial.slice(-50);
        });

        // Resetear índice de historial
        setIndiceHistorial(-1);
        setInputTemporal('');

        setPregunta('');
        setMostrarAutocomplete(false);

        try {
            const res = await axios.post('/api/chat/preguntar', {
                pregunta: preguntaActual,
                conversacion_id: conversacionActual?.id
            }, {
                withCredentials: true
            });

            // Actualizar rate limit desde headers
            const rateLimitHeader = res.headers['x-ratelimit-remaining'];
            const rateLimitTotal = res.headers['x-ratelimit-limit'];

            if (rateLimitHeader && rateLimitTotal) {
                const restante = parseInt(rateLimitHeader);
                const limite = parseInt(rateLimitTotal);
                setRateLimitInfo({
                    limite,
                    usado: limite - restante,
                    restante,
                    mostrar: true
                });

                // Advertencia cuando quedan pocas preguntas
                if (restante <= 5 && restante > 0) {
                    toast.warning(`⚠️ Te quedan ${restante} preguntas`, {
                        duration: 3000
                    });
                }
            }

            if (res.data.success) {
                // ✅ Procesar nombres de PDF en la respuesta
                let contenidoProcesado = res.data.respuesta;

                try {
                    contenidoProcesado = await linkifyPDFNames(res.data.respuesta, navigate);
                } catch (error) {
                    console.error('Error procesando nombres de PDF:', error);
                    // Si falla, usar respuesta original
                }

                // Agregar respuesta de Gemini
                const mensajeAsistente = {
                    rol: 'assistant',
                    contenido: contenidoProcesado,
                    fecha: new Date().toISOString(),
                    tokens_usados: res.data.tokens_usados,
                    tiempo_respuesta: res.data.tiempo_respuesta
                };

                setMensajes(prev => [...prev, mensajeAsistente]);

                // Actualizar conversación actual
                if (!conversacionActual) {
                    setConversacionActual({ id: res.data.conversacion_id });
                    cargarConversaciones();
                    cargarEstadisticas();
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

                // Actualizar info de rate limit
                if (errorData.rate_limit) {
                    setRateLimitInfo({
                        limite: errorData.rate_limit.limite,
                        usado: errorData.rate_limit.usado,
                        restante: errorData.rate_limit.restante,
                        mostrar: true
                    });
                }
            } else {
                toast.error('Error al enviar pregunta');
            }

            // Remover mensaje del usuario si hubo error
            setMensajes(prev => prev.slice(0, -1));
            setPregunta(preguntaActual);
        } finally {
            setEnviando(false);
        }
    };

    const handleInputChange = (e) => {
        const valor = e.target.value;
        setPregunta(valor);

        // Mostrar autocomplete si empieza con /
        setMostrarAutocomplete(valor.startsWith('/') && valor.length > 0);
    };

    const seleccionarComando = (comando) => {
        setPregunta(comando + ' ');
        setMostrarAutocomplete(false);
        inputRef.current?.focus();
    };

    const enviarComandoRapido = (comando) => {
        setPregunta(comando);
        // Simular envío después de un pequeño delay
        setTimeout(() => {
            const form = document.querySelector('form[onsubmit]');
            if (form) {
                form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
            }
        }, 100);
    };

    const eliminarConversacion = async (id, e) => {
        e.stopPropagation();

        if (!window.confirm('¿Eliminar esta conversación?')) return;

        try {
            const res = await axios.delete(`/api/chat/conversacion/${id}`, {
                withCredentials: true
            });

            if (res.data.success) {
                if (conversacionActual?.id === id) {
                    nuevaConversacion();
                }

                cargarConversaciones();
                cargarEstadisticas();
                toast.success('Conversación eliminada');
            }
        } catch (error) {
            toast.error('Error al eliminar');
        }
    };

    return (
        <div className="flex h-[calc(100vh-4rem)] gap-4">
            {/* Sidebar - Historial de conversaciones */}
            <div className="w-80 bg-white rounded-lg shadow-sm p-4 flex flex-col">
                <button
                    onClick={nuevaConversacion}
                    className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition mb-4"
                >
                    <Plus className="w-5 h-5" />
                    Nueva Conversación
                </button>

                {/* Estadísticas */}
                {estadisticas && (
                    <div className="bg-linear-to-r from-orange-50 to-red-50 rounded-lg p-3 mb-4">
                        <div className="flex items-center gap-2 mb-2">
                            <BarChart3 className="w-4 h-4 text-primary" />
                            <span className="text-sm font-medium text-gray-700">Estadísticas</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                                <div className="text-gray-500">Conversaciones</div>
                                <div className="font-bold text-gray-900">{estadisticas.total_conversaciones}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">Mensajes</div>
                                <div className="font-bold text-gray-900">{estadisticas.total_mensajes}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">Tokens</div>
                                <div className="font-bold text-gray-900">{estadisticas.tokens_totales.toLocaleString()}</div>
                            </div>
                            <div>
                                <div className="text-gray-500">Tiempo prom.</div>
                                <div className="font-bold text-gray-900">{estadisticas.tiempo_promedio_respuesta}s</div>
                            </div>
                        </div>
                    </div>
                )}

                <div className="flex-1 overflow-y-auto space-y-2">
                    {conversaciones.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">
                            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">No hay conversaciones</p>
                        </div>
                    ) : (
                        conversaciones.map(conv => (
                            <div
                                key={conv.id}
                                className={`p-3 rounded-lg cursor-pointer transition group ${conversacionActual?.id === conv.id
                                    ? 'bg-primary-light border border-primary-light'
                                    : 'hover:bg-gray-50 border border-transparent'
                                    }`}
                                onClick={() => cargarConversacion(conv.id)}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">
                                            {conv.titulo}
                                        </p>
                                        <p className="text-xs text-gray-500 mt-1">
                                            {conv.num_mensajes} mensajes
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => eliminarConversacion(conv.id, e)}
                                        className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700 transition ml-2"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Chat principal */}
            <div className="flex-1 bg-white rounded-lg shadow-sm flex flex-col">
                {/* Header */}
                <div className="px-6 py-4 border-b bg-linear-to-r from-orange-500 to-red-500">
                    <div className="flex items-center gap-2">
                        <MessageSquare className="w-6 h-6 text-white" />
                        <h1 className="text-xl font-bold text-white">
                            Asistente Inteligente
                        </h1>
                    </div>
                    <p className="text-sm text-orange-100 mt-1">
                        Pregunta sobre tus documentos, empresas y datos del sistema
                    </p>
                </div>

                {/* Mensajes */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                    {mensajes.length === 0 && (
                        <div className="text-center py-12">
                            <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                                ¡Hola! 👋 Soy tu asistente de IA
                            </h3>
                            <p className="text-gray-600 mb-4">
                                Puedo ayudarte con:
                            </p>
                            <ul className="text-left max-w-md mx-auto space-y-2 text-gray-600 mb-6">
                                <li>• Información sobre empresas y documentos</li>
                                <li>• Cálculos de importes a pagar</li>
                                <li>• Estadísticas del sistema</li>
                            </ul>
                            <div className="max-w-lg mx-auto bg-blue-50 dark:bg-slate-800 border border-blue-200 dark:border-slate-700 rounded-lg p-4 mb-4 shadow-sm modal-content">
                                <p className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">⚡ Comandos rápidos disponibles:</p>
                                <ul className="text-left text-sm text-blue-800 dark:text-blue-300 space-y-1">
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/empresas</code> - Ver todas las empresas</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/docs [empresa]</code> - Documentos de una empresa</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/total [empresa]</code> - Total a pagar</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/nominas [empresa]</code> - Últimas nóminas</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/fiscal [empresa]</code> - Documentos fiscales</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/stats</code> - Estadísticas</li>
                                    <li><code className="bg-blue-100 dark:bg-blue-800/50 px-2 py-0.5 rounded">/help</code> - Ver todos los comandos</li>
                                </ul>
                                <p className="text-xs text-blue-700 dark:text-blue-400 mt-3">💡 Estos comandos no gastan tokens</p>
                            </div>
                            <p className="text-sm text-gray-500">
                                O simplemente pregúntame en lenguaje natural 💬
                            </p>
                        </div>
                    )}

                    {mensajes.map((mensaje, index) => (
                        <div
                            key={index}
                            className={`flex ${mensaje.rol === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-3xl px-4 py-3 rounded-lg ${mensaje.rol === 'user'
                                    ? 'bg-linear-to-r from-orange-600 to-red-600 text-white'
                                    : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                                    }`}
                            >
                                {mensaje.rol === 'assistant' ? (
                                    <div>
                                        <div className="prose prose-sm max-w-none">
                                            <ReactMarkdown
                                                components={{
                                                    // 🆕 Interceptar clics en enlaces para navegación interna
                                                    a: ({ node, children, href, ...props }) => (
                                                        <a
                                                            href={href}
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                // Si es un enlace interno (empieza con /)
                                                                if (href && href.startsWith('/')) {
                                                                    // Usar URL completa con origin para evitar duplicación
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
                                        {mensaje.tiempo_respuesta > 0 && (
                                            <div className="text-xs text-gray-400 mt-2">
                                                {mensaje.tiempo_respuesta}s
                                                {mensaje.tokens_usados > 0 && ` • ${mensaje.tokens_usados} tokens`}
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
                                )}
                            </div>
                        </div>
                    ))}

                    {enviando && (
                        <div className="flex justify-start">
                            <div className="bg-white px-4 py-3 rounded-lg shadow-sm border border-gray-200">
                                <div className="flex items-center gap-2">
                                    <Loader2 className="w-5 h-5 animate-spin text-primary" />
                                    <span className="text-sm text-gray-600">Pensando...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="px-6 py-4 border-t bg-white">
                    <form onSubmit={enviarPregunta} className="flex gap-2">
                        <div className="flex-1 relative">
                            {/* Autocomplete dropdown */}
                            {mostrarAutocomplete && (
                                <div className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto z-50">
                                    <div className="p-2 bg-gray-50 border-b border-gray-200">
                                        <span className="text-xs text-gray-600 font-medium">Comandos disponibles:</span>
                                    </div>
                                    {comandosDisponibles
                                        .filter(c => c.cmd.toLowerCase().startsWith(pregunta.toLowerCase()))
                                        .map((comando, idx) => (
                                            <button
                                                key={idx}
                                                type="button"
                                                onClick={() => seleccionarComando(comando.cmd)}
                                                className="w-full text-left px-3 py-2 hover:bg-blue-50 transition-colors flex items-start gap-2"
                                            >
                                                <span className="font-mono text-sm text-blue-600 font-medium">{comando.cmd}</span>
                                                <span className="text-xs text-gray-500 mt-0.5">- {comando.desc}</span>
                                            </button>
                                        ))
                                    }
                                    {comandosDisponibles.filter(c => c.cmd.toLowerCase().startsWith(pregunta.toLowerCase())).length === 0 && (
                                        <div className="p-3 text-sm text-gray-500 text-center">
                                            No se encontraron comandos. Escribe /help para ver todos.
                                        </div>
                                    )}
                                </div>
                            )}

                            <input
                                ref={inputRef}
                                type="text"
                                value={pregunta}
                                onChange={handleInputChange}
                                onKeyDown={manejarTeclaHistorial}
                                placeholder="Escribe tu pregunta o usa comandos: /empresas, /docs, /total..."
                                disabled={enviando}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary disabled:bg-gray-100"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={enviando || !pregunta.trim()}
                            className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
                        >
                            {enviando ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Enviando
                                </>
                            ) : (
                                <>
                                    <Send className="w-5 h-5" />
                                    Enviar
                                </>
                            )}
                        </button>
                    </form>

                    {/* Command chips */}
                    <div className="flex gap-2 flex-wrap mt-3">
                        <button
                            onClick={() => enviarComandoRapido('/empresas')}
                            type="button"
                            className="px-3 py-1.5 bg-linear-to-r from-blue-50 to-blue-100 dark:bg-slate-800 hover:from-blue-100 hover:to-blue-200 text-blue-700 dark:text-blue-200 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 border border-transparent dark:border-blue-700/50 ia-chat-chip"
                        >
                            <span>📋</span>
                            <span>Ver empresas</span>
                        </button>
                        <button
                            onClick={() => enviarComandoRapido('/stats')}
                            type="button"
                            className="px-3 py-1.5 bg-linear-to-r from-purple-50 to-purple-100 dark:bg-slate-800 hover:from-purple-100 hover:to-purple-200 text-purple-700 dark:text-purple-200 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 border border-transparent dark:border-purple-700/50 ia-chat-chip"
                        >
                            <span>📊</span>
                            <span>Estadísticas</span>
                        </button>
                        <button
                            onClick={() => enviarComandoRapido('/help')}
                            type="button"
                            className="px-3 py-1.5 bg-linear-to-r from-gray-50 to-gray-100 dark:bg-slate-800 hover:from-gray-100 hover:to-gray-200 text-gray-700 dark:text-gray-200 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 border border-transparent dark:border-gray-600 ia-chat-chip"
                        >
                            <span>❓</span>
                            <span>Ayuda</span>
                        </button>
                        <button
                            onClick={() => {
                                navigate('/soporte');
                                toast.success('Abriendo sistema de soporte...');
                            }}
                            type="button"
                            className="px-3 py-1.5 bg-gradient-to-r from-orange-50 to-orange-100 dark:from-orange-900/40 dark:to-red-900/40 hover:from-orange-100 hover:to-orange-200 dark:hover:from-orange-800/60 dark:hover:to-red-800/60 text-primary-hover dark:text-orange-200 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 border border-transparent dark:border-orange-700/50"
                            title="¿La IA no pudo ayudarte? Contacta con soporte humano"
                        >
                            <Headphones className="w-4 h-4" />
                            <span>Contactar Soporte</span>
                        </button>
                    </div>

                    <p className="text-xs text-gray-500 mt-2">
                        Powered by Gemini 2.5 Flash • Respuestas en tiempo real
                    </p>
                </div>
            </div>
        </div>
    );
}
