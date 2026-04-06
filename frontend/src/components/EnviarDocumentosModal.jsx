import React, { useState } from 'react';
import { Mail, Loader2, X, FileText, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../utils/axiosConfig';

export default function EnviarDocumentosModal({
    isOpen,
    onClose,
    documentosSeleccionados,
    onSuccess,
    destinatarioInicial = ''
}) {
    const [destinatariosStr, setDestinatariosStr] = useState(destinatarioInicial);
    const [asunto, setAsunto] = useState('Documentación Compartida');
    const [mensaje, setMensaje] = useState('Adjunto la documentación solicitada. Saludos.');
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Actualizar el valor si cambia la prop
    React.useEffect(() => {
        if (isOpen) {
            setDestinatariosStr(destinatarioInicial || '');
        }
    }, [isOpen, destinatarioInicial]);

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Parse emails manually from comma separated string
        const emailList = destinatariosStr.split(',')
            .map(e => e.trim())
            .filter(e => e && e.includes('@'));

        if (emailList.length === 0) {
            toast.error('Introduce al menos un correo electrónico válido');
            return;
        }

        if (documentosSeleccionados.length === 0) {
            toast.error('No hay documentos seleccionados');
            return;
        }

        // Extraer IDs enteros — cada ítem tiene 'doc_id' (int) e 'id' (string como "doc_1")
        const docIds = documentosSeleccionados
            .map(d => d.doc_id)
            .filter(id => id != null && !isNaN(Number(id)));

        if (docIds.length === 0) {
            toast.error('Los documentos seleccionados no tienen un identificador válido.');
            return;
        }

        setIsSubmitting(true);
        try {
            const response = await api.post('/api/documentos/enviar-multiples', {
                document_ids: docIds,
                destinatarios: emailList,
                asunto,
                mensaje
            });

            toast.success(response.data.message || 'Documentos enviados con éxito');
            setDestinatariosStr('');
            setMensaje('Adjunto la documentación solicitada. Saludos.');
            if (onSuccess) onSuccess();
            onClose();
        } catch (err) {
            console.error("Error al enviar correos:", err);
            const errorMsg = err.response?.data?.error || err.message || 'Error al enviar los documentos.';
            toast.error(errorMsg);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm"
                onClick={onClose}
            ></div>

            {/* Modal Content */}
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg overflow-hidden relative z-10 animate-in fade-in zoom-in-95 border border-slate-200">
                <div className="flex items-center justify-between p-4 border-b border-slate-200">
                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                        <Mail className="h-6 w-6 text-primary" />
                        Enviar Documentos a Terceros
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-full bg-slate-100 hover:bg-slate-200 transition-colors"
                    >
                        <X className="w-5 h-5 text-slate-600" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-5 space-y-6">
                    {/* Alerta de Documentos */}
                    <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
                        <div className="flex flex-col gap-2">
                            <h4 className="font-bold text-blue-900 flex items-center gap-2">
                                <FileText className="h-5 w-5 text-blue-600" />
                                Archivos adjuntos ({documentosSeleccionados.length})
                            </h4>
                            <ul className="text-sm text-blue-800 font-medium space-y-1 ml-7">
                                {documentosSeleccionados.slice(0, 3).map((doc, idx) => (
                                    <li key={idx} className="truncate">📎 {doc.titulo}</li>
                                ))}
                                {documentosSeleccionados.length > 3 && (
                                    <li className="font-bold mt-1 text-xs">...y {documentosSeleccionados.length - 3} documentos más.</li>
                                )}
                            </ul>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="space-y-1.5">
                            <label className="text-sm font-bold text-slate-700">Para (Correos Electrónicos)</label>
                            <input
                                type="text"
                                placeholder="ejemplo@banco.com, asesor@empresa.com"
                                value={destinatariosStr}
                                onChange={(e) => setDestinatariosStr(e.target.value)}
                                className="w-full flex h-10 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-medium"
                                required
                            />
                            <p className="text-xs font-semibold text-slate-500">Separa múltiples correos con comas.</p>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-sm font-bold text-slate-700">Asunto</label>
                            <input
                                type="text"
                                placeholder="Asunto del correo"
                                value={asunto}
                                onChange={(e) => setAsunto(e.target.value)}
                                className="w-full flex h-10 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-medium"
                                required
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-sm font-bold text-slate-700">Mensaje (Cuerpo del correo)</label>
                            <textarea
                                placeholder="Escribe tu mensaje aquí..."
                                value={mensaje}
                                onChange={(e) => setMensaje(e.target.value)}
                                className="w-full min-h-[120px] rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent font-medium resize-y"
                            />
                        </div>
                    </div>

                    <div className="pt-4 border-t border-slate-200 flex justify-end gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={isSubmitting}
                            className="inline-flex h-10 items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100 transition-colors"
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            disabled={isSubmitting || !destinatariosStr || documentosSeleccionados.length === 0}
                            className="inline-flex h-10 items-center justify-center rounded-md bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 text-sm font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed gap-2 shadow-sm"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Enviando...
                                </>
                            ) : (
                                <>
                                    <Send className="h-4 w-4" />
                                    Enviar Correos
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
