// frontend/src/components/EnviarEmailGrupoModal.jsx
import React, { useState, useMemo } from 'react';
import { X, Mail, FileText, Plus, AlertCircle, Eye, Edit3, Sparkles } from 'lucide-react';
import { useEnviarEmailMasivo } from '../hooks/useGruposDocumentos';
import toast from 'react-hot-toast';

// Plantillas predefinidas
const PLANTILLAS = {
    fiscal: {
        nombre: 'Documentación Fiscal',
        asunto: 'Documentación Fiscal - {empresa}',
        mensaje: 'Estimado/a,\n\nAdjuntamos la documentación fiscal correspondiente al periodo solicitado.\n\nQuedamos a su disposición para cualquier aclaración.\n\nSaludos cordiales,'
    },
    inspeccion: {
        nombre: 'Inspección',
        asunto: 'Documentos para Inspección - {empresa}',
        mensaje: 'Estimado/a,\n\nEn respuesta a su solicitud, adjuntamos la documentación requerida para la inspección.\n\nSi necesita información adicional, no dude en contactarnos.\n\nAtentamente,'
    },
    mensual: {
        nombre: 'Documentación Mensual',
        asunto: 'Documentación Mensual - {empresa} - {fecha}',
        mensaje: 'Estimado/a,\n\nAdjuntamos la documentación correspondiente al mes en curso.\n\nSaludos cordiales,'
    },
    generica: {
        nombre: 'Genérica',
        asunto: 'Documentos - {empresa}',
        mensaje: 'Estimado/a,\n\nAdjuntamos la documentación solicitada.\n\nQuedamos a su disposición.\n\nSaludos,'
    }
};

export default function EnviarEmailGrupoModal({ grupo, onClose }) {
    const [emails, setEmails] = useState([]);
    const [inputEmail, setInputEmail] = useState('');
    const [emailError, setEmailError] = useState('');
    const [asunto, setAsunto] = useState(`Documentos del grupo: ${grupo.nombre}`);
    const [mensaje, setMensaje] = useState('');
    const [activeTab, setActiveTab] = useState('editar'); // 'editar' | 'preview'
    const enviarEmail = useEnviarEmailMasivo();

    // Reemplazar variables en texto
    const reemplazarVariables = (texto) => {
        const fecha = new Date().toLocaleDateString('es-ES', { month: 'long', year: 'numeric' });
        return texto
            .replace(/{empresa}/g, grupo.empresa?.nombre || grupo.nombre)
            .replace(/{cantidad}/g, grupo.documentos?.length || 0)
            .replace(/{fecha}/g, fecha);
    };

    // Aplicar plantilla
    const aplicarPlantilla = (plantillaKey) => {
        const plantilla = PLANTILLAS[plantillaKey];
        setAsunto(reemplazarVariables(plantilla.asunto));
        setMensaje(reemplazarVariables(plantilla.mensaje));
        toast.success(`Plantilla "${plantilla.nombre}" aplicada`);
    };

    // Validar formato de email
    const validateEmail = (email) => {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email.trim());
    };

    // Agregar email
    const addEmail = (e) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            const email = inputEmail.trim();

            if (!email) return;

            if (!validateEmail(email)) {
                setEmailError('Email inválido');
                return;
            }

            if (emails.includes(email)) {
                setEmailError('Email ya agregado');
                return;
            }

            setEmails([...emails, email]);
            setInputEmail('');
            setEmailError('');
        }
    };

    // Eliminar email
    const removeEmail = (emailToRemove) => {
        setEmails(emails.filter(e => e !== emailToRemove));
    };

    // Agregar email de empresa
    const addCompanyEmail = () => {
        const empresaEmail = grupo.empresa?.email;
        if (!empresaEmail) {
            toast.error('La empresa no tiene email configurado');
            return;
        }

        if (emails.includes(empresaEmail)) {
            toast.error('Email de empresa ya agregado');
            return;
        }

        setEmails([...emails, empresaEmail]);
        toast.success('Email de empresa agregado');
    };

    // Calcular tamaño total de adjuntos (estimado)
    const totalSize = useMemo(() => {
        if (!grupo.documentos) return 0;
        return (grupo.documentos.length * 0.5).toFixed(2);
    }, [grupo.documentos]);

    // Generar preview HTML
    const previewHTML = useMemo(() => {
        const mensajeHTML = mensaje.replace(/\n/g, '<br>');
        const docsHTML = grupo.documentos?.map((doc, i) => `
      <tr>
        <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;">
          <div style="display: flex; align-items: center;">
            <span style="color: #f97316; margin-right: 8px;">📄</span>
            <span style="color: #374151; font-size: 14px;">${doc.nombre_archivo}</span>
          </div>
        </td>
      </tr>
    `).join('') || '';

        return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>
      <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 20px 0;">
          <tr>
            <td align="center">
              <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <tr>
                  <td style="background: linear-gradient(90deg, #f97316 0%, #ef4444 100%); padding: 30px 40px; text-align: center;">
                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">IAGES</h1>
                    <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 14px; opacity: 0.9;">Gestión Documental</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding: 40px;">
                    <h2 style="margin: 0 0 20px 0; color: #111827; font-size: 20px; font-weight: 600;">${grupo.empresa?.nombre || grupo.nombre}</h2>
                    <div style="color: #374151; font-size: 15px; line-height: 1.6; margin-bottom: 30px;">
                      ${mensajeHTML || '<p>Adjuntamos la documentación solicitada.</p>'}
                    </div>
                    <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-top: 30px;">
                      <h3 style="margin: 0 0 15px 0; color: #111827; font-size: 16px; font-weight: 600;">📎 Documentos Adjuntos (${grupo.documentos?.length || 0})</h3>
                      <table width="100%" cellpadding="0" cellspacing="0">${docsHTML}</table>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="background-color: #f9fafb; padding: 30px 40px; border-top: 1px solid #e5e7eb;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="text-align: center;">
                          <p style="margin: 0 0 8px 0; color: #111827; font-size: 14px; font-weight: 600;">Victor Cisneros Müller</p>
                          <p style="margin: 0 0 4px 0; color: #6b7280; font-size: 13px;">Tel: 932687082</p>
                          <p style="margin: 0; color: #9ca3af; font-size: 12px;">© 2025 IAGES - Gestión Documental</p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
      </html>
    `;
    }, [mensaje, grupo]);

    const handleEnviar = async (e) => {
        e.preventDefault();

        if (emails.length === 0) {
            toast.error('Debes agregar al menos un destinatario');
            return;
        }

        if (!grupo.documentos || grupo.documentos.length === 0) {
            toast.error('El grupo no tiene documentos para enviar');
            return;
        }

        try {
            await enviarEmail.mutateAsync({
                grupoId: grupo.id,
                destinatarios: emails,
                asunto,
                mensaje
            });
            onClose();
        } catch (error) {
            console.error('Error al enviar email:', error);
        }
    };

    const isLargeAttachment = parseFloat(totalSize) > 10;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10002] p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                        <Mail className="text-green-600" size={24} />
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                            Enviar por Email
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-200 dark:border-gray-700 px-6">
                    <button
                        onClick={() => setActiveTab('editar')}
                        className={`px-4 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'editar'
                            ? 'border-blue-600 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                            }`}
                    >
                        <Edit3 size={16} />
                        Editar
                    </button>
                    <button
                        onClick={() => setActiveTab('preview')}
                        className={`px-4 py-3 font-medium text-sm flex items-center gap-2 border-b-2 transition-colors ${activeTab === 'preview'
                            ? 'border-blue-600 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                            }`}
                    >
                        <Eye size={16} />
                        Preview
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto">
                    {activeTab === 'editar' ? (
                        <form onSubmit={handleEnviar} className="p-6 space-y-4">
                            {/* Plantillas */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                                    <Sparkles size={16} className="text-purple-600" />
                                    Plantillas Rápidas
                                </label>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                    {Object.entries(PLANTILLAS).map(([key, plantilla]) => (
                                        <button
                                            key={key}
                                            type="button"
                                            onClick={() => aplicarPlantilla(key)}
                                            className="px-3 py-2 text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-800 transition-colors"
                                        >
                                            {plantilla.nombre}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Destinatarios con Chips */}
                            <div>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                        Destinatarios * ({emails.length})
                                    </label>
                                    {grupo.empresa?.email && (
                                        <button
                                            type="button"
                                            onClick={addCompanyEmail}
                                            className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors flex items-center gap-1"
                                        >
                                            <Plus size={12} />
                                            Usar email empresa
                                        </button>
                                    )}
                                </div>

                                {/* Chips de emails */}
                                <div className="flex flex-wrap gap-2 mb-2 min-h-[40px] p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700">
                                    {emails.map((email) => (
                                        <div
                                            key={email}
                                            className="inline-flex items-center gap-1 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm font-medium"
                                        >
                                            <span>{email}</span>
                                            <button
                                                type="button"
                                                onClick={() => removeEmail(email)}
                                                className="hover:bg-green-200 dark:hover:bg-green-800 rounded-full p-0.5"
                                            >
                                                <X size={14} />
                                            </button>
                                        </div>
                                    ))}
                                </div>

                                {/* Input para agregar emails */}
                                <input
                                    type="text"
                                    value={inputEmail}
                                    onChange={(e) => {
                                        setInputEmail(e.target.value);
                                        setEmailError('');
                                    }}
                                    onKeyDown={addEmail}
                                    placeholder="Escribe un email y presiona Enter o coma"
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                                />
                                {emailError && (
                                    <p className="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
                                        <AlertCircle size={12} />
                                        {emailError}
                                    </p>
                                )}
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                    Presiona Enter o coma (,) para agregar cada email
                                </p>
                            </div>

                            {/* Asunto */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Asunto *
                                </label>
                                <input
                                    type="text"
                                    value={asunto}
                                    onChange={(e) => setAsunto(e.target.value)}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                                    required
                                />
                            </div>

                            {/* Mensaje */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    Mensaje
                                </label>
                                <textarea
                                    value={mensaje}
                                    onChange={(e) => setMensaje(e.target.value)}
                                    rows={6}
                                    placeholder="Escribe un mensaje opcional..."
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white resize-none"
                                />
                            </div>

                            {/* Preview de documentos con tamaño */}
                            <div className={`border rounded-lg p-4 ${isLargeAttachment ? 'bg-primary-light dark:bg-orange-900/20 border-primary-light dark:border-orange-800' : 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'}`}>
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className={`text-sm font-medium flex items-center gap-2 ${isLargeAttachment ? 'text-orange-900 dark:text-orange-300' : 'text-blue-900 dark:text-blue-300'}`}>
                                        <FileText size={16} />
                                        Documentos adjuntos ({grupo.documentos?.length || 0})
                                    </h3>
                                    <div className="text-right">
                                        <p className={`text-xs font-medium ${isLargeAttachment ? 'text-primary-hover dark:text-orange-400' : 'text-blue-700 dark:text-blue-400'}`}>
                                            ~{totalSize} MB
                                        </p>
                                        {isLargeAttachment && (
                                            <p className="text-xs text-primary dark:text-orange-400 flex items-center gap-1 mt-1">
                                                <AlertCircle size={12} />
                                                Archivo grande
                                            </p>
                                        )}
                                    </div>
                                </div>
                                <div className="space-y-1 max-h-32 overflow-y-auto">
                                    {grupo.documentos?.map((doc) => (
                                        <div key={doc.id} className={`text-xs flex items-center gap-1 ${isLargeAttachment ? 'text-primary-hover dark:text-orange-400' : 'text-blue-700 dark:text-blue-400'}`}>
                                            <span className={`w-1 h-1 rounded-full ${isLargeAttachment ? 'bg-primary dark:bg-orange-400' : 'bg-blue-600 dark:bg-blue-400'}`}></span>
                                            {doc.nombre_archivo}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </form>
                    ) : (
                        /* Preview Tab */
                        <div className="p-6">
                            <div className="bg-gray-100 dark:bg-gray-900 rounded-lg p-4 mb-4">
                                <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                                    <strong>Asunto:</strong> {asunto}
                                </p>
                                <p className="text-xs text-gray-600 dark:text-gray-400">
                                    <strong>Para:</strong> {emails.join(', ') || 'Sin destinatarios'}
                                </p>
                            </div>
                            <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden" style={{ height: '500px' }}>
                                <iframe
                                    srcDoc={previewHTML}
                                    className="w-full h-full border-0"
                                    title="Preview del email"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer con Progress */}
                <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                    {/* Progress bar durante envío */}
                    {enviarEmail.isPending && (
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                            <div className="bg-green-600 h-full rounded-full animate-pulse" style={{ width: '100%' }}></div>
                        </div>
                    )}

                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={enviarEmail.isPending}
                            className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleEnviar}
                            disabled={enviarEmail.isPending || emails.length === 0}
                            className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {enviarEmail.isPending ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Enviando...
                                </>
                            ) : (
                                <>
                                    <Mail size={18} />
                                    Enviar Email
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
