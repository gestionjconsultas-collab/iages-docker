import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Bell, BellOff, Volume2, VolumeX, TestTube, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import useNotifications from '../hooks/useNotifications';

export default function NotificationSettings() {
    const { permission, supported, requestPermission } = useNotifications();
    const [preferences, setPreferences] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadPreferences();
    }, []);

    const loadPreferences = async () => {
        try {
            const res = await axios.get('/api/notifications/preferences', {
                withCredentials: true
            });
            setPreferences(res.data.preferences);
        } catch (error) {
            console.error('Error cargando preferencias:', error);
            toast.error('Error cargando preferencias');
        } finally {
            setLoading(false);
        }
    };

    const savePreferences = async (newPrefs) => {
        setSaving(true);
        try {
            await axios.put('/api/notifications/preferences', newPrefs, {
                withCredentials: true
            });
            setPreferences(newPrefs);
            toast.success('Preferencias guardadas');
        } catch (error) {
            console.error('Error guardando:', error);
            toast.error('Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    const handleToggle = (key) => {
        const newPrefs = { ...preferences, [key]: !preferences[key] };
        savePreferences(newPrefs);
    };

    const handleEnableNotifications = async () => {
        const granted = await requestPermission();
        if (granted) {
            const newPrefs = { ...preferences, enabled: true };
            savePreferences(newPrefs);
            toast.success('Notificaciones activadas');
        } else {
            toast.error('Permisos denegados. Verifica la configuración de tu navegador.');
        }
    };

    const sendTestNotification = async () => {
        try {
            await axios.post('/api/notifications/test', {}, {
                withCredentials: true
            });
            toast.success('Notificación de prueba enviada');
        } catch (error) {
            console.error('Error enviando notificación:', error);
            toast.error('Error enviando notificación');
        }
    };

    if (loading) {
        return (
            <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                <p className="text-gray-600 mt-2">Cargando preferencias...</p>
            </div>
        );
    }

    if (!supported) {
        return (
            <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start gap-3">
                    <XCircle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                        <h4 className="font-semibold text-yellow-900">Notificaciones no soportadas</h4>
                        <p className="text-yellow-800 text-sm mt-1">
                            Tu navegador no soporta notificaciones de escritorio.
                            Prueba con Chrome, Firefox o Edge.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                    <Bell className="w-5 h-5 text-primary" />
                    Notificaciones de Escritorio
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                    Recibe alertas incluso cuando la aplicación no esté abierta
                </p>
            </div>

            {/* Estado de permisos */}
            {permission !== 'granted' && (
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-start gap-3 mb-3">
                        <Bell className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <h4 className="font-semibold text-blue-900">Activa las notificaciones</h4>
                            <p className="text-blue-800 text-sm mt-1">
                                Necesitas activar los permisos de notificaciones en tu navegador para recibir alertas.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={handleEnableNotifications}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition"
                    >
                        Activar Notificaciones
                    </button>
                </div>
            )}

            {permission === 'granted' && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <div className="flex items-center gap-2 text-green-800">
                        <CheckCircle className="w-5 h-5" />
                        <span className="font-medium">Notificaciones activadas</span>
                    </div>
                </div>
            )}

            {/* Configuración general */}
            <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 className="font-semibold text-gray-900">Configuración General</h4>

                <div className="flex items-center justify-between">
                    <div>
                        <p className="font-medium text-gray-900">Notificaciones Activadas</p>
                        <p className="text-sm text-gray-600">Recibir notificaciones de escritorio</p>
                    </div>
                    <button
                        onClick={() => handleToggle('enabled')}
                        disabled={permission !== 'granted' || saving}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${preferences?.enabled ? 'bg-primary' : 'bg-gray-300'
                            } ${permission !== 'granted' || saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${preferences?.enabled ? 'translate-x-6' : 'translate-x-1'
                            }`} />
                    </button>
                </div>

                <div className="flex items-center justify-between">
                    <div>
                        <p className="font-medium text-gray-900">Sonido</p>
                        <p className="text-sm text-gray-600">Reproducir sonido con las notificaciones</p>
                    </div>
                    <button
                        onClick={() => handleToggle('sound_enabled')}
                        disabled={!preferences?.enabled || saving}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${preferences?.sound_enabled ? 'bg-primary' : 'bg-gray-300'
                            } ${!preferences?.enabled || saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${preferences?.sound_enabled ? 'translate-x-6' : 'translate-x-1'
                            }`} />
                    </button>
                </div>
            </div>

            {/* Tipos de notificaciones */}
            <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
                <h4 className="font-semibold text-gray-900">Tipos de Notificaciones</h4>

                {[
                    { key: 'documentos_procesados', label: 'Documentos Procesados', icon: '📄', description: 'Cuando un documento se procesa exitosamente' },
                    { key: 'errores_procesamiento', label: 'Errores en Procesamiento', icon: '❌', description: 'Cuando hay un error al procesar un documento' },
                    { key: 'vencimientos', label: 'Vencimientos Próximos', icon: '⏰', description: 'Alertas de documentos próximos a vencer' },
                    { key: 'tareas_asignadas', label: 'Tareas Asignadas', icon: '📋', description: 'Cuando te asignan una nueva tarea' },
                    { key: 'respuestas_soporte', label: 'Respuestas en Soporte', icon: '💬', description: 'Nuevas respuestas en tus tickets' },
                    { key: 'mantenimiento', label: 'Mantenimiento Programado', icon: '🛠️', description: 'Avisos de mantenimiento del sistema' }
                ].map(({ key, label, icon, description }) => (
                    <div key={key} className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-3 flex-1">
                            <span className="text-2xl flex-shrink-0">{icon}</span>
                            <div>
                                <p className="font-medium text-gray-900">{label}</p>
                                <p className="text-xs text-gray-600">{description}</p>
                            </div>
                        </div>
                        <button
                            onClick={() => handleToggle(key)}
                            disabled={!preferences?.enabled || saving}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition flex-shrink-0 ${preferences?.[key] ? 'bg-primary' : 'bg-gray-300'
                                } ${!preferences?.enabled || saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${preferences?.[key] ? 'translate-x-6' : 'translate-x-1'
                                }`} />
                        </button>
                    </div>
                ))}
            </div>

            {/* Botón de prueba */}
            <button
                onClick={sendTestNotification}
                disabled={!preferences?.enabled || permission !== 'granted'}
                className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-900 rounded-lg font-medium flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
                <TestTube className="w-5 h-5" />
                Enviar Notificación de Prueba
            </button>

            {saving && (
                <div className="text-center text-sm text-gray-600">
                    Guardando cambios...
                </div>
            )}
        </div>
    );
}
