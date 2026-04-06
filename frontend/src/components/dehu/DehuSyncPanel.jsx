// frontend/src/components/dehu/DehuSyncPanel.jsx
import React, { useState, useEffect } from 'react';
import { Download, Key, RefreshCw, Copy, Check, ExternalLink, Monitor, Cloud, Lock, Zap } from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const DehuSyncPanel = () => {
    const [credentials, setCredentials] = useState(null);
    const [loading, setLoading] = useState(true);
    const [copying, setCopying] = useState(false);
    const [rotating, setRotating] = useState(false);

    useEffect(() => {
        fetchCredentials();
    }, []);

    const fetchCredentials = async () => {
        try {
            setLoading(true);
            const response = await axios.get('/api/dehu-sync/credentials');
            setCredentials(response.data);
        } catch (error) {
            console.error('Error fetching credentials:', error);
            // Si el error es 403, probablemente no es jefatura
        } finally {
            setLoading(false);
        }
    };

    const handleRotateKey = async () => {
        if (!window.confirm('¿Estás seguro de que deseas generar una nueva API Key? La clave anterior dejará de funcionar inmediatamente.')) {
            return;
        }

        try {
            setRotating(true);
            const response = await axios.post('/api/dehu-sync/rotate-key');
            setCredentials({ ...credentials, api_key: response.data.api_key });
            toast.success('API Key regenerada con éxito');
        } catch (error) {
            toast.error('Error al regenerar la clave');
        } finally {
            setRotating(false);
        }
    };

    const copyToClipboard = () => {
        if (!credentials?.api_key) return;
        navigator.clipboard.writeText(credentials.api_key);
        setCopying(true);
        toast.success('API Key copiada al portapapeles');
        setTimeout(() => setCopying(false), 2000);
    };

    const handleDownloadApp = async () => {
        try {
            toast.loading('Obteniendo enlace de descarga...', { id: 'download' });
            // Fetch URL explicitly via API to prevent drop of session cookies on 302 redirects
            const response = await axios.get('/api/dehu-sync/download-app', {
                // Evitamos el seguimiento automático del redirect para extraer la URL manualmente
                maxRedirects: 0,
                validateStatus: function (status) {
                    return status >= 200 && status < 400; // Accept 302 as success
                }
            });

            // Si el backend devuelve JSON con la url directamente (mejor práctica)
            if (response.data && response.data.url) {
                window.location.assign(response.data.url);
                toast.success('Iniciando descarga del aplicativo...', { id: 'download' });
            }
            // Si el backend es un redirect puro (302)
            else if (response.headers.location) {
                window.location.assign(response.headers.location);
                toast.success('Iniciando descarga del aplicativo...', { id: 'download' });
            } else {
                toast.error('No se pudo obtener el enlace de descarga.', { id: 'download' });
            }
        } catch (error) {
            console.error("Error al descargar la app:", error);
            toast.error('Error al obtener el enlace de descarga.', { id: 'download' });
        }
    };

    if (loading) return null;
    if (!credentials) return null; // No mostrar nada si no hay acceso

    return (
        <div className="bg-white rounded-xl shadow-sm border border-blue-100 overflow-hidden mb-6">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-6 border-b border-blue-100">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h3 className="font-bold text-xl text-gray-900 flex items-center gap-2">
                            <span className="bg-blue-600 text-white p-1.5 rounded-lg">
                                <Monitor className="w-5 h-5" />
                            </span>
                            CONECTA
                        </h3>
                        <p className="text-gray-600 mt-1 font-medium">
                            La pasarela inteligente entre las Sedes Electrónicas y tu Panel de Gestión.
                        </p>
                    </div>
                    <button
                        onClick={handleDownloadApp}
                        className="flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors shadow-sm"
                    >
                        <Download className="w-4 h-4" />
                        <span>Descargar Aplicativo</span>
                    </button>
                </div>

                {/* SmartScreen warning notice */}
                <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 flex items-start gap-3">
                    <span className="text-amber-500 text-lg leading-none mt-0.5">⚠️</span>
                    <div>
                        <p className="text-sm font-semibold text-amber-800">¿Windows muestra una advertencia de seguridad?</p>
                        <p className="text-xs text-amber-700 mt-0.5">
                            Haz clic en <strong>"Más información"</strong> → <strong>"Ejecutar de todas formas"</strong>.
                            Esta alerta aparece porque el programa aún no dispone de firma digital de editor. Estamos en proceso de obtenerla.
                        </p>
                    </div>
                </div>

                <p className="text-sm text-gray-500 mt-4 max-w-3xl leading-relaxed">
                    <strong>Conecta</strong> es una herramienta de escritorio avanzada diseñada para centralizar y automatizar la gestión de notificaciones administrativas (DEHú y otros organismos). Permite a las gestorías y empresas manejar múltiples certificados digitales de forma segura, descargar documentos oficiales y sincronizarlos en tiempo real con la plataforma en la nube de IAGES.
                </p>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-5">
                    <div className="bg-white/60 p-3 rounded-lg border border-white/40">
                        <Monitor className="w-4 h-4 text-blue-500 mb-1" />
                        <h5 className="font-semibold text-xs text-gray-800">Automatización Total</h5>
                        <p className="text-[10px] text-gray-500 leading-tight mt-0.5">Conecta revisa y descarga tus notificaciones por ti.</p>
                    </div>
                    <div className="bg-white/60 p-3 rounded-lg border border-white/40">
                        <Key className="w-4 h-4 text-purple-500 mb-1" />
                        <h5 className="font-semibold text-xs text-gray-800">Firma Digital Integrada</h5>
                        <p className="text-[10px] text-gray-500 leading-tight mt-0.5">Firma PDFs legalmente usando tus certificados oficiales.</p>
                    </div>
                    <div className="bg-white/60 p-3 rounded-lg border border-white/40">
                        <Lock className="w-4 h-4 text-green-500 mb-1" />
                        <h5 className="font-semibold text-xs text-gray-800">Seguridad de Grado Bancario</h5>
                        <p className="text-[10px] text-gray-500 leading-tight mt-0.5">Certificados protegidos localmente con cifrado AES-128.</p>
                    </div>
                    <div className="bg-white/60 p-3 rounded-lg border border-white/40">
                        <Cloud className="w-4 h-4 text-sky-500 mb-1" />
                        <h5 className="font-semibold text-xs text-gray-800">Sincronización Transparente</h5>
                        <p className="text-[10px] text-gray-500 leading-tight mt-0.5">Documentos subidos a tu panel de IAGES automáticamente.</p>
                    </div>
                </div>
            </div>

            <div className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="md:col-span-1">
                        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                            <Key className="w-4 h-4 mr-2 text-blue-500" />
                            Tus Credenciales
                        </h4>
                        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                            <p className="text-xs text-gray-500 mb-1">X-Gestoria-Key (API Key)</p>
                            <div className="flex items-center space-x-2">
                                <code className="flex-1 bg-white px-3 py-2 rounded border border-gray-300 font-mono text-sm text-blue-700 break-all">
                                    {credentials.api_key || 'No generada'}
                                </code>
                                <button
                                    onClick={copyToClipboard}
                                    className="p-2 hover:bg-gray-200 rounded-md transition-colors"
                                    title="Copiar al portapapeles"
                                >
                                    {copying ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5 text-gray-600" />}
                                </button>
                                <button
                                    onClick={handleRotateKey}
                                    disabled={rotating}
                                    className={`p-2 hover:bg-gray-200 rounded-md transition-colors ${rotating ? 'animate-spin' : ''}`}
                                    title="Generar nueva clave"
                                >
                                    <RefreshCw className="w-5 h-5 text-gray-600" />
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="md:col-span-2 flex flex-col justify-center">
                        <div className="bg-blue-50/50 rounded-lg p-5 border border-blue-100">
                            <h4 className="text-sm font-bold text-blue-900 mb-3 flex items-center">
                                <Zap className="w-4 h-4 mr-2 text-blue-600" />
                                ¿Cómo vincular con la App?
                            </h4>
                            <ol className="text-sm text-gray-700 space-y-3 list-decimal ml-4">
                                <li className="pl-1">
                                    <strong>Descarga e Instala:</strong> Haz clic en el botón "Descargar Aplicativo" e instala Conecta en tu ordenador.
                                </li>
                                <li className="pl-1">
                                    <strong>Copia tu API Key:</strong> Copia la credencial <em>X-Gestoria-Key</em> que aparece a la izquierda de este panel.
                                </li>
                                <li className="pl-1">
                                    <strong>Inicia Sesión:</strong> Abre Conecta y pega tu clave en la pantalla de bienvenida. Esto vinculará tu PC con tu cuenta de IAGES de forma segura.
                                </li>
                                <li className="pl-1">
                                    <strong>Gestiona y Sincroniza:</strong> A partir de ahora, cualquier notificación que aceptes o descargues aparecerá automáticamente en este panel web con el distintivo "☁️ IAGES".
                                </li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DehuSyncPanel;
