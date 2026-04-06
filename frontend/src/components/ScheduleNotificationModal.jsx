import React, { useState } from 'react';
import { Clock, X, Calendar, Check } from 'lucide-react';
import axios from '../utils/axiosConfig';
import { toast } from 'react-hot-toast';

export default function ScheduleNotificationModal({ document, onClose }) {
    const [reminderDays, setReminderDays] = useState([7, 1]); // Por defecto: 7 días y 1 día antes
    const [deadline, setDeadline] = useState('');
    const [scheduling, setScheduling] = useState(false);

    const toggleReminderDay = (days) => {
        if (reminderDays.includes(days)) {
            setReminderDays(reminderDays.filter(d => d !== days));
        } else {
            setReminderDays([...reminderDays, days].sort((a, b) => b - a));
        }
    };

    const handleSchedule = async () => {
        if (!deadline) {
            toast.error('Por favor, selecciona una fecha de vencimiento');
            return;
        }

        if (reminderDays.length === 0) {
            toast.error('Selecciona al menos un recordatorio');
            return;
        }

        setScheduling(true);
        try {
            console.log('📅 Programando recordatorios:', {
                documentId: document.id,
                deadline,
                reminderDays
            });

            const response = await axios.post(`/api/documents/${document.id}/schedule-notification`, {
                deadline: deadline,
                reminder_days: reminderDays
            });

            console.log('✅ Respuesta del servidor:', response.data);

            if (response.data.success) {
                toast.success(`✅ ${response.data.notifications_created} recordatorio(s) programado(s)`);
                onClose();
            } else {
                toast.error(response.data.error || 'Error al programar recordatorios');
            }
        } catch (error) {
            console.error('❌ Error programando recordatorios:', error);
            console.error('Detalles:', error.response?.data);
            toast.error(error.response?.data?.error || 'Error al programar recordatorios');
        } finally {
            setScheduling(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm transition-all duration-300">
            <div
                className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden transform transition-all scale-100 animate-in fade-in zoom-in duration-200"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="p-6 pb-4 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-full bg-purple-50 text-purple-600">
                                <Clock className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Programar recordatorios</h3>
                                <p className="text-sm text-gray-500">Notificaciones automáticas de vencimiento</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-all"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6 space-y-5">
                    {/* Información del documento */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <p className="text-xs font-medium text-gray-500 uppercase mb-1">Documento</p>
                        <p className="text-sm font-medium text-gray-900 truncate">
                            {document.nombre_archivo}
                        </p>
                    </div>

                    {/* Fecha de vencimiento */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-gray-400" />
                            Fecha de vencimiento
                        </label>
                        <input
                            type="date"
                            value={deadline}
                            onChange={(e) => setDeadline(e.target.value)}
                            min={new Date().toISOString().split('T')[0]}
                            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                        />
                    </div>

                    {/* Opciones de recordatorio */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Enviar recordatorios
                        </label>
                        <div className="space-y-2">
                            {[
                                { days: 7, label: '7 días antes del vencimiento' },
                                { days: 3, label: '3 días antes del vencimiento' },
                                { days: 1, label: '1 día antes del vencimiento' },
                                { days: 0, label: 'El día del vencimiento' }
                            ].map(({ days, label }) => (
                                <label
                                    key={days}
                                    className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${reminderDays.includes(days)
                                        ? 'border-purple-500 bg-purple-50'
                                        : 'border-gray-200 hover:border-gray-300 bg-white'
                                        }`}
                                >
                                    <div className="relative flex items-center justify-center">
                                        <input
                                            type="checkbox"
                                            checked={reminderDays.includes(days)}
                                            onChange={() => toggleReminderDay(days)}
                                            className="sr-only"
                                        />
                                        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${reminderDays.includes(days)
                                            ? 'bg-purple-600 border-purple-600'
                                            : 'border-gray-300'
                                            }`}>
                                            {reminderDays.includes(days) && (
                                                <Check className="w-3 h-3 text-white" />
                                            )}
                                        </div>
                                    </div>
                                    <span className={`text-sm font-medium ${reminderDays.includes(days) ? 'text-purple-900' : 'text-gray-700'
                                        }`}>
                                        {label}
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Info adicional */}
                    <div className="bg-blue-50 border border-blue-100 rounded-lg p-3">
                        <p className="text-xs text-blue-800 leading-relaxed">
                            💡 Los recordatorios se enviarán automáticamente a todos los usuarios activos de la empresa
                            en las fechas seleccionadas.
                        </p>
                    </div>
                </div>

                {/* Actions */}
                <div className="p-6 bg-gray-50/50 flex gap-3">
                    <button
                        onClick={onClose}
                        disabled={scheduling}
                        className="flex-1 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSchedule}
                        disabled={scheduling || !deadline || reminderDays.length === 0}
                        className="flex-1 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-purple-500 text-white font-semibold rounded-xl shadow-md hover:from-purple-700 hover:to-purple-600 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {scheduling ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>Programando...</span>
                            </>
                        ) : (
                            <>
                                <Clock className="w-4 h-4" />
                                <span>Programar recordatorios</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
