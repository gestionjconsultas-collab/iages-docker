import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Power, Settings, AlertTriangle, Save, Clock, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import ConfirmModal from './ConfirmModal';

export default function MaintenanceModeControl() {
    const [enabled, setEnabled] = useState(false);
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [delayOption, setDelayOption] = useState('5'); // '0', '5', '15', '30', 'custom'
    const [customDateTime, setCustomDateTime] = useState('');
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [modalConfig, setModalConfig] = useState({ title: '', message: '', onConfirm: () => { } });

    // Mensajes sugeridos según el delay
    const suggestedMessages = {
        '0': 'El sistema entrará en mantenimiento inmediatamente. Por favor, guarda tu trabajo.',
        '5': 'Mantenimiento programado en 5 minutos. Por favor, finaliza tus tareas pendientes.',
        '15': 'El sistema entrará en mantenimiento en 15 minutos. Guarda tu trabajo y cierra sesión.',
        '30': 'Mantenimiento programado para dentro de 30 minutos. Tienes tiempo para finalizar tus tareas.',
        'custom': 'Mantenimiento programado. Recibirás una notificación antes de que comience.'
    };

    useEffect(() => {
        loadStatus();
    }, []);

    // Actualizar mensaje sugerido cuando cambia el delay
    useEffect(() => {
        if (!enabled && delayOption in suggestedMessages) {
            setMessage(suggestedMessages[delayOption]);
        }
    }, [delayOption, enabled]);

    const loadStatus = async () => {
        try {
            const res = await axios.get('/api/super-admin/maintenance/status', {
                withCredentials: true
            });

            setEnabled(res.data.maintenance_mode);
            setMessage(res.data.message || '');
        } catch (err) {
            console.error('Error cargando estado:', err);
            toast.error('Error cargando estado de mantenimiento');
        }
    };

    const calculateDelayMinutes = () => {
        if (delayOption === 'custom') {
            if (!customDateTime) {
                toast.error('Por favor selecciona una fecha y hora');
                return null;
            }
            const scheduledTime = new Date(customDateTime);
            const now = new Date();
            const diffMs = scheduledTime - now;

            if (diffMs <= 0) {
                toast.error('La fecha debe ser futura');
                return null;
            }

            return Math.ceil(diffMs / 60000); // Convertir a minutos
        }
        return parseInt(delayOption);
    };

    const toggleMaintenance = async () => {
        const newState = !enabled;

        if (newState) {
            const delayMinutes = calculateDelayMinutes();
            if (delayMinutes === null) return;

            // Mensaje de confirmación personalizado
            let confirmMsg = '¿Estás seguro de activar el modo de mantenimiento?';
            if (delayMinutes === 0) {
                confirmMsg += '\n\n⚠️ Se activará INMEDIATAMENTE. Los usuarios serán desconectados al instante.';
            } else {
                const hours = Math.floor(delayMinutes / 60);
                const mins = delayMinutes % 60;
                const timeStr = hours > 0 ? `${hours}h ${mins}min` : `${mins} minutos`;
                confirmMsg += `\n\n⏰ Los usuarios recibirán una advertencia y tendrán ${timeStr} para guardar su trabajo.`;
            }

            setModalConfig({
                title: 'Confirmar Activación',
                message: confirmMsg,
                confirmText: 'Activa Mantenimiento',
                onConfirm: () => executeToggle(true, delayMinutes)
            });
            setShowConfirmModal(true);
            return;
        }

        executeToggle(false, 0);
    };

    const executeToggle = async (newState, delayMinutes) => {
        const action = newState ? 'activar' : 'desactivar';
        setLoading(true);
        try {
            const res = await axios.post('/api/super-admin/maintenance/toggle', {
                enabled: newState,
                delay_minutes: delayMinutes
            }, {
                withCredentials: true
            });

            setEnabled(newState);

            if (newState && delayMinutes > 0) {
                toast.success(`Mantenimiento programado. Los usuarios serán notificados.`, {
                    duration: 5000,
                    icon: '⏰'
                });
            } else {
                toast.success(res.data.message || `Modo de mantenimiento ${action}do`);
            }
        } catch (err) {
            console.error('Error cambiando modo:', err);
            toast.error(`Error al ${action} modo de mantenimiento`);
        } finally {
            setLoading(false);
        }
    };

    const updateMessage = async () => {
        if (!message.trim()) {
            toast.error('El mensaje no puede estar vacío');
            return;
        }

        setSaving(true);
        try {
            await axios.put('/api/super-admin/maintenance/message', {
                message: message.trim()
            }, {
                withCredentials: true
            });

            toast.success('Mensaje actualizado');
        } catch (err) {
            console.error('Error actualizando mensaje:', err);
            toast.error('Error actualizando mensaje');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold flex items-center gap-2 text-gray-900">
                    <Settings className="w-6 h-6 text-blue-600" />
                    Modo de Mantenimiento
                </h3>
            </div>

            {/* Banner de estado */}
            {enabled && (
                <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border-l-4 border-yellow-500 rounded-lg p-4 mb-6 shadow-sm">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" />
                        <div>
                            <h4 className="font-bold text-yellow-900 mb-1">
                                ⚠️ Sistema en Modo de Mantenimiento
                            </h4>
                            <p className="text-sm text-yellow-800">
                                Los usuarios normales no pueden acceder al sistema. Solo los super-admins tienen acceso.
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Opciones de delay (solo mostrar si NO está activado) */}
            {!enabled && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Tiempo de Advertencia
                    </h4>

                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
                        <button
                            onClick={() => setDelayOption('0')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${delayOption === '0'
                                ? 'bg-red-600 text-white shadow-md'
                                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                                }`}
                        >
                            Inmediato
                        </button>
                        <button
                            onClick={() => setDelayOption('5')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${delayOption === '5'
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                                }`}
                        >
                            5 min
                        </button>
                        <button
                            onClick={() => setDelayOption('15')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${delayOption === '15'
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                                }`}
                        >
                            15 min
                        </button>
                        <button
                            onClick={() => setDelayOption('30')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${delayOption === '30'
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                                }`}
                        >
                            30 min
                        </button>
                        <button
                            onClick={() => setDelayOption('custom')}
                            className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${delayOption === 'custom'
                                ? 'bg-purple-600 text-white shadow-md'
                                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-300'
                                }`}
                        >
                            <Calendar className="w-4 h-4 inline mr-1" />
                            Personalizado
                        </button>
                    </div>

                    {delayOption === 'custom' && (
                        <div className="mt-3">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Fecha y Hora de Activación
                            </label>
                            <input
                                type="datetime-local"
                                value={customDateTime}
                                onChange={(e) => setCustomDateTime(e.target.value)}
                                min={new Date().toISOString().slice(0, 16)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                            />
                        </div>
                    )}

                    <p className="text-xs text-blue-700 mt-3">
                        {delayOption === '0' && '⚠️ Los usuarios serán desconectados inmediatamente sin advertencia.'}
                        {delayOption !== '0' && delayOption !== 'custom' && `✓ Los usuarios recibirán una advertencia ${delayOption} minutos antes.`}
                        {delayOption === 'custom' && customDateTime && '✓ Los usuarios recibirán una advertencia en la fecha seleccionada.'}
                        {delayOption === 'custom' && !customDateTime && 'Selecciona una fecha y hora para continuar.'}
                    </p>
                </div>
            )}

            {/* Botón de toggle */}
            <button
                onClick={toggleMaintenance}
                disabled={loading}
                className={`w-full flex items-center justify-center gap-2 px-6 py-4 rounded-lg font-semibold transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed ${enabled
                    ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white shadow-lg'
                    : 'bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white shadow-lg'
                    }`}
            >
                {loading ? (
                    <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Procesando...
                    </>
                ) : (
                    <>
                        <Power className="w-5 h-5" />
                        {enabled ? 'Desactivar Mantenimiento' : 'Activar Mantenimiento'}
                    </>
                )}
            </button>

            {/* Editor de mensaje */}
            <div className="space-y-3 mt-6">
                <label className="block">
                    <span className="text-sm font-semibold text-gray-700 mb-2 block">
                        Mensaje para Usuarios
                    </span>
                    <textarea
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors resize-none"
                        rows={4}
                        placeholder="Ej: El sistema está en mantenimiento programado. Volveremos en 30 minutos."
                    />
                </label>

                <button
                    onClick={updateMessage}
                    disabled={saving || !message.trim()}
                    className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium shadow-sm"
                >
                    {saving ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Guardando...
                        </>
                    ) : (
                        <>
                            <Save className="w-4 h-4" />
                            Guardar Mensaje
                        </>
                    )}
                </button>
            </div>

            {/* Información adicional */}
            <div className="mt-6 pt-6 border-t border-gray-200">
                <h4 className="text-sm font-semibold text-gray-700 mb-2">ℹ️ Información</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                    <li>• Los super-admins siempre pueden acceder al sistema</li>
                    <li>• El cambio es instantáneo, no requiere reiniciar el servidor</li>
                    <li>• Los usuarios verán el mensaje personalizado en la página de mantenimiento</li>
                </ul>
            </div>

            <ConfirmModal
                isOpen={showConfirmModal}
                onClose={() => setShowConfirmModal(false)}
                onConfirm={modalConfig.onConfirm}
                title={modalConfig.title}
                message={modalConfig.message}
                confirmText={modalConfig.confirmText}
                isDanger={true}
            />
        </div>
    );
}
