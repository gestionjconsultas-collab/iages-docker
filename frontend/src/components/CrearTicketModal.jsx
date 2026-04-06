// frontend/src/components/CrearTicketModal.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';
import { X, Send, AlertCircle } from 'lucide-react';

const CrearTicketModal = ({ onClose, onTicketCreado }) => {
    const [formData, setFormData] = useState({
        asunto: '',
        descripcion: '',
        categoria: 'Consulta'
    });
    const [enviando, setEnviando] = useState(false);

    const categorias = [
        { value: 'Consulta', label: '❓ Consulta', description: 'Pregunta sobre uso del sistema' },
        { value: 'Bug', label: '🐛 Bug / Error', description: 'Algo no funciona correctamente' },
        { value: 'Mejora', label: '💡 Mejora', description: 'Sugerencia de funcionalidad' },
        { value: 'Urgente', label: '🚨 Urgente', description: 'Problema crítico que requiere atención inmediata' }
    ];

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.asunto.trim()) {
            toast.error('El asunto es requerido');
            return;
        }

        try {
            setEnviando(true);
            const response = await axios.post('/api/soporte/tickets', formData, { withCredentials: true });

            if (response.data.success) {
                toast.success(response.data.message || 'Ticket creado exitosamente');
                onTicketCreado();
                onClose();
            }
        } catch (error) {
            console.error('Error creando ticket:', error);
            toast.error(error.response?.data?.error || 'Error al crear ticket');
        } finally {
            setEnviando(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-200">
                    <h2 className="text-2xl font-bold text-gray-900">Crear Nuevo Ticket</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6">
                    {/* Asunto */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Asunto <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={formData.asunto}
                            onChange={(e) => setFormData({ ...formData, asunto: e.target.value })}
                            placeholder="Describe brevemente el problema o consulta"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            maxLength={200}
                            required
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            {formData.asunto.length}/200 caracteres
                        </p>
                    </div>

                    {/* Categoría */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-3">
                            Categoría <span className="text-red-500">*</span>
                        </label>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {categorias.map((cat) => (
                                <label
                                    key={cat.value}
                                    className={`flex items-start gap-3 p-4 border-2 rounded-lg cursor-pointer transition ${formData.categoria === cat.value
                                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 dark:border-blue-400'
                                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800'
                                        }`}
                                >
                                    <input
                                        type="radio"
                                        name="categoria"
                                        value={cat.value}
                                        checked={formData.categoria === cat.value}
                                        onChange={(e) => setFormData({ ...formData, categoria: e.target.value })}
                                        className="mt-1"
                                    />
                                    <div className="flex-1">
                                        <p className="font-medium text-gray-900">{cat.label}</p>
                                        <p className="text-xs text-gray-600 mt-1">{cat.description}</p>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Descripción */}
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Descripción
                        </label>
                        <textarea
                            value={formData.descripcion}
                            onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
                            placeholder="Proporciona más detalles sobre tu consulta o problema..."
                            rows={6}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Incluye cualquier información relevante que pueda ayudarnos a resolver tu consulta
                        </p>
                    </div>

                    {/* Info Box */}
                    <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg flex gap-3">
                        <AlertCircle className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-blue-800 dark:text-blue-200">
                            <p className="font-medium mb-1">¿Qué sucede después?</p>
                            <ul className="list-disc list-inside space-y-1 text-blue-700 dark:text-blue-300">
                                <li>Recibirás un número de ticket único</li>
                                <li>Nuestro equipo revisará tu solicitud</li>
                                <li>Te responderemos por este mismo canal</li>
                                <li>Recibirás notificaciones por email</li>
                            </ul>
                        </div>
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-3 justify-end">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                            disabled={enviando}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={enviando}
                            className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {enviando ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Creando...
                                </>
                            ) : (
                                <>
                                    <Send className="w-4 h-4" />
                                    Crear Ticket
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CrearTicketModal;
