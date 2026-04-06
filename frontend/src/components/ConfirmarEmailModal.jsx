import React, { useState, useRef } from 'react';
import { X, Mail, Loader2, Send } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';

export default function ConfirmarEmailModal({ documento, emailPreview, onClose, onEmailSent }) {
  useEscapeKey(onClose);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [emailSubject, setEmailSubject] = useState(emailPreview.subject);
  const [emailBody, setEmailBody] = useState(emailPreview.body);
  
  const destinatarios = emailPreview.destinatarios || [];
  const textareaRef = useRef(null);
  const smtpUser = "gestionjconsultas@gmail.com";

  // --- RECUPERANDO LAS SUGERENCIAS (CHIPS) ---
  const datosIA = documento.datos_extraidos || {};
  const suggestions = Object.entries(datosIA)
    .filter(([k, v]) => k !== '_metadata' && v !== null && v !== '')
    .map(([k, v]) => ({ label: k.replace(/_/g, ' '), value: String(v) }));

  const handleSuggestionClick = (text) => {
    if (!textareaRef.current) return;
    const ta = textareaRef.current;
    const start = ta.selectionStart;
    const newText = emailBody.substring(0, start) + text + emailBody.substring(ta.selectionEnd);
    setEmailBody(newText);
    setTimeout(() => { ta.focus(); ta.setSelectionRange(start + text.length, start + text.length); }, 0);
  };

  const handleConfirmSend = async () => {
    setIsSending(true); setError(null);
    try {
      const res = await axios.post(`/api/documentos/${documento.id}/enviar-email`, 
        { subject: emailSubject, body: emailBody, destinatarios }, { withCredentials: true }
      );
      if (res.data.success) { toast.success('Email enviado'); onEmailSent(); }
    } catch (err) { setError(err.response?.data?.error || 'Error'); } 
    finally { setIsSending(false); }
  };

  return (
    // Z-INDEX 100 PARA ASEGURAR QUE ESTÉ ENCIMA DE TODO
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4" style={{ zIndex: 100 }} onClick={onClose}>
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-3xl flex flex-col max-h-[95vh]" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b bg-white rounded-t-lg">
          <h2 className="text-xl font-semibold text-gray-900">Confirmar envío de Email</h2>
          <button onClick={onClose}><X className="w-6 h-6 text-gray-500 hover:text-gray-700"/></button>
        </div>
        
        <div className="p-6 overflow-y-auto space-y-4 bg-gray-50">
          {/* Remitente y Destinatarios */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded border border-gray-200 shadow-sm">
              <span className="text-xs text-gray-500 font-bold uppercase block mb-1">De:</span>
              <div className="text-sm text-gray-800 font-medium truncate">{smtpUser}</div>
            </div>
            <div className="bg-white p-3 rounded border border-gray-200 shadow-sm">
              <span className="text-xs text-gray-500 font-bold uppercase block mb-1">Para:</span>
              <div className="flex flex-wrap gap-1">
                {destinatarios.map((e, i) => (
                  <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded-full text-xs font-medium border border-blue-200">
                    {e}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Asunto */}
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase mb-1 block">Asunto</label>
            <input type="text" value={emailSubject} onChange={(e) => setEmailSubject(e.target.value)} className="w-full p-3 border rounded bg-white font-semibold shadow-sm focus:ring-2 focus:ring-blue-500 outline-none" />
          </div>

          {/* SUGERENCIAS (CHIPS) */}
          {suggestions.length > 0 && (
            <div className="bg-white p-3 rounded border border-gray-200 shadow-sm">
              <label className="text-xs font-bold text-gray-500 uppercase mb-2 block">Sugerencias (Clic para insertar):</label>
              <div className="flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <button 
                    key={s.label} 
                    onClick={() => handleSuggestionClick(s.value)} 
                    className="group flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-primary-light border border-gray-200 hover:border-primary-light rounded text-xs transition-all"
                    title={s.value}
                  >
                    <span className="font-semibold text-gray-600 group-hover:text-primary-hover">{s.label}:</span> 
                    <span className="text-gray-800 max-w-[120px] truncate">{s.value}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Cuerpo */}
          <div>
            <label className="text-xs font-bold text-gray-500 uppercase mb-1 block">Cuerpo del Email</label>
            <textarea ref={textareaRef} value={emailBody} onChange={(e) => setEmailBody(e.target.value)} className="w-full h-64 p-4 border rounded bg-white text-sm font-mono shadow-sm focus:ring-2 focus:ring-blue-500 outline-none resize-y" />
          </div>

          {error && <div className="bg-red-50 text-red-700 p-3 rounded text-sm font-bold border border-red-200">{error}</div>}
        </div>

        <div className="flex justify-end gap-3 p-4 bg-white border-t rounded-b-lg">
          <button onClick={onClose} className="px-5 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded font-medium transition-colors" disabled={isSending}>Cancelar</button>
          <button onClick={handleConfirmSend} className="w-48 px-5 py-2 bg-green-600 text-white rounded hover:bg-green-700 flex items-center justify-center gap-2 font-bold shadow-md transition-colors" disabled={isSending}>
            {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />} 
            {isSending ? 'Enviando...' : 'Confirmar y Enviar'}
          </button>
        </div>
      </div>
    </div>
  );
}