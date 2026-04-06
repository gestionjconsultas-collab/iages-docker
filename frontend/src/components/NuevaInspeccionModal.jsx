// frontend/src/components/NuevaInspeccionModal.jsx
import React, { useState, useRef } from 'react';
import {
  X, ShieldAlert, FileSearch, Banknote, Scale,
  Upload, Plus, Loader2, Mail, Check
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

const TIPOS = [
  {
    id: 'inspeccion',
    label: 'Inspección',
    desc: 'Inspección laboral o tributaria',
    Icon: ShieldAlert,
    color: 'red',
    tw: {
      card: 'hover:border-red-200',
      cardSel: 'ring-2 ring-red-400 border-red-300 bg-red-50',
      iconBg: 'bg-red-100',
      iconColor: 'text-red-600',
      checkBg: 'bg-red-100 text-red-600',
    },
    gradient: 'linear-gradient(135deg, #dc2626, #9f1239)',
    btnClass: 'bg-red-600 hover:bg-red-700',
    prefix: 'Inspección',
  },
  {
    id: 'requerimiento',
    label: 'Requerimiento de Información',
    desc: 'Solicitud oficial de documentación',
    Icon: FileSearch,
    color: 'blue',
    tw: {
      card: 'hover:border-blue-200',
      cardSel: 'ring-2 ring-blue-400 border-blue-300 bg-blue-50',
      iconBg: 'bg-blue-100',
      iconColor: 'text-blue-600',
      checkBg: 'bg-blue-100 text-blue-600',
    },
    gradient: 'linear-gradient(135deg, #2563eb, #1e3a8a)',
    btnClass: 'bg-blue-600 hover:bg-blue-700',
    prefix: 'Requerimiento',
  },
  {
    id: 'embargo_salario',
    label: 'Embargo de Salario',
    desc: 'Embargo sobre retribuciones del trabajador',
    Icon: Banknote,
    color: 'orange',
    tw: {
      card: 'hover:border-orange-200',
      cardSel: 'ring-2 ring-orange-400 border-orange-300 bg-orange-50',
      iconBg: 'bg-orange-100',
      iconColor: 'text-orange-600',
      checkBg: 'bg-orange-100 text-orange-600',
    },
    gradient: 'linear-gradient(135deg, #ea580c, #9a3412)',
    btnClass: 'bg-orange-600 hover:bg-orange-700',
    prefix: 'Embargo Salario',
  },
  {
    id: 'embargo_creditos',
    label: 'Embargo Créditos y Derechos',
    desc: 'Embargo sobre bienes, créditos o derechos',
    Icon: Scale,
    color: 'purple',
    tw: {
      card: 'hover:border-purple-200',
      cardSel: 'ring-2 ring-purple-400 border-purple-300 bg-purple-50',
      iconBg: 'bg-purple-100',
      iconColor: 'text-purple-600',
      checkBg: 'bg-purple-100 text-purple-600',
    },
    gradient: 'linear-gradient(135deg, #7c3aed, #4c1d95)',
    btnClass: 'bg-purple-600 hover:bg-purple-700',
    prefix: 'Embargo Créditos',
  },
];

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function NuevaInspeccionModal({ empresaId, onClose, onSuccess }) {
  const año = new Date().getFullYear();
  const [tipoId, setTipoId] = useState(null);
  const [nombre, setNombre] = useState('');
  const [archivos, setArchivos] = useState([]);
  const [emails, setEmails] = useState([]);
  const [emailInput, setEmailInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef();

  const tipo = TIPOS.find(t => t.id === tipoId);

  const handleTipoSelect = (t) => {
    setTipoId(t.id);
    // Auto-rellena nombre solo si está vacío o tenía el nombre de un tipo anterior
    const esNombreAutogenerado = TIPOS.some(tp => nombre === `${tp.prefix} - ${año}`);
    if (!nombre || esNombreAutogenerado) {
      setNombre(`${t.prefix} - ${año}`);
    }
  };

  const handleFiles = (files) => {
    const pdfs = Array.from(files).filter(
      f => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    );
    if (pdfs.length < files.length) toast.error('Solo se admiten archivos PDF');
    setArchivos(prev => {
      const nombres = new Set(prev.map(f => f.name));
      return [...prev, ...pdfs.filter(f => !nombres.has(f.name))];
    });
  };

  const removeArchivo = (idx) => setArchivos(prev => prev.filter((_, i) => i !== idx));

  const addEmail = () => {
    const e = emailInput.trim().toLowerCase();
    if (!e) return;
    if (!EMAIL_REGEX.test(e)) { toast.error('Formato de email inválido'); return; }
    if (emails.includes(e)) { toast.error('Email ya añadido'); setEmailInput(''); return; }
    setEmails(prev => [...prev, e]);
    setEmailInput('');
  };

  const handleEmailKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addEmail(); }
  };

  const handleSubmit = async () => {
    if (!tipoId) { toast.error('Selecciona un tipo de expediente'); return; }
    if (!nombre.trim()) { toast.error('El nombre es obligatorio'); return; }

    setLoading(true);
    try {
      // 1. Crear grupo
      const grupoRes = await axios.post('/api/grupos-documentos', {
        nombre: nombre.trim(),
        empresa_id: empresaId,
        color: tipo.color,
        descripcion: tipo.label,
      }, { withCredentials: true });

      if (!grupoRes.data.success) throw new Error(grupoRes.data.error || 'Error al crear el expediente');
      const grupoId = grupoRes.data.grupo.id;

      // 2. Subir archivos si los hay
      if (archivos.length > 0) {
        const formData = new FormData();
        archivos.forEach(f => formData.append('files[]', f));
        formData.append('empresa_id', empresaId);
        formData.append('categoria', 'Inspecciones');

        const uploadRes = await axios.post('/api/subir-directo-multiple', formData, {
          withCredentials: true,
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        // 3. Asociar documentos al grupo
        const docIds = uploadRes.data.documento_ids || [];
        for (const docId of docIds) {
          await axios.post(`/api/grupos-documentos/${grupoId}/documentos`, {
            documento_id: docId,
          }, { withCredentials: true });
        }
      }

      // 4. Enviar emails si los hay
      if (emails.length > 0) {
        await axios.post(`/api/grupos-documentos/${grupoId}/enviar-email`, {
          destinatarios: emails,
          asunto: `${tipo.label} — ${nombre}`,
          mensaje: `Le informamos que se ha iniciado un expediente de tipo "${tipo.label}" bajo el nombre "${nombre}".\n\nAdjuntamos la documentación correspondiente para su revisión.\n\nQuedamos a su disposición para cualquier consulta.`,
        }, { withCredentials: true });
        toast.success(`Notificación enviada a ${emails.length} destinatario(s)`);
      }

      toast.success(`Expediente "${nombre}" creado correctamente`);
      onSuccess?.();
      onClose();
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error || err.message || 'Error al crear el expediente');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">

        {/* Header dinámico */}
        <div
          className="p-6 rounded-t-3xl transition-all duration-500"
          style={{ background: tipo ? tipo.gradient : 'linear-gradient(135deg, #1f2937, #111827)' }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                {tipo ? <tipo.Icon className="w-6 h-6 text-white" /> : <Scale className="w-6 h-6 text-white" />}
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Nuevo Expediente</h2>
                <p className="text-white/65 text-sm mt-0.5">
                  {tipo ? tipo.label : 'Selecciona el tipo de inspección'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-9 h-9 rounded-xl bg-white/15 flex items-center justify-center hover:bg-white/25 transition-colors"
            >
              <X className="w-4 h-4 text-white" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">

          {/* Selector de tipo */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-3">Tipo de expediente</label>
            <div className="grid grid-cols-2 gap-3">
              {TIPOS.map(t => (
                <button
                  key={t.id}
                  onClick={() => handleTipoSelect(t)}
                  className={`flex items-start gap-3 p-4 rounded-2xl border-2 text-left transition-all duration-200 group ${
                    tipoId === t.id
                      ? t.tw.cardSel
                      : `border-gray-100 bg-white ${t.tw.card}`
                  }`}
                >
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 transition-colors ${
                    tipoId === t.id ? t.tw.iconBg : 'bg-gray-100 group-hover:bg-gray-200'
                  }`}>
                    <t.Icon className={`w-4 h-4 transition-colors ${tipoId === t.id ? t.tw.iconColor : 'text-gray-500'}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm font-semibold leading-tight ${tipoId === t.id ? 'text-gray-900' : 'text-gray-700'}`}>
                      {t.label}
                    </p>
                    <p className="text-xs text-gray-400 mt-1 leading-tight">{t.desc}</p>
                  </div>
                  {tipoId === t.id && (
                    <div className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center ${t.tw.checkBg}`}>
                      <Check className="w-3 h-3" strokeWidth={3} />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Nombre del expediente */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-2">Nombre del expediente</label>
            <input
              type="text"
              value={nombre}
              onChange={e => setNombre(e.target.value)}
              placeholder="Ej: Inspección Hacienda — 2026"
              className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all bg-gray-50 focus:bg-white"
            />
          </div>

          {/* Archivos */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-2">
              Documentos{' '}
              <span className="text-gray-400 font-normal">(opcional)</span>
            </label>
            <div
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-200 ${
                isDragging
                  ? 'border-primary bg-primary/5 scale-[1.01]'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => fileRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={e => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
            >
              <input
                ref={fileRef}
                type="file"
                multiple
                accept="application/pdf"
                className="hidden"
                onChange={e => handleFiles(e.target.files)}
              />
              <Upload className={`w-8 h-8 mx-auto mb-2 transition-colors ${isDragging ? 'text-primary' : 'text-gray-300'}`} />
              <p className="text-sm font-medium text-gray-600">
                Arrastra PDFs aquí o <span className="text-primary font-semibold">selecciona archivos</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">Solo archivos PDF</p>
            </div>

            {archivos.length > 0 && (
              <div className="mt-3 space-y-2">
                {archivos.map((f, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2.5 bg-gray-50 rounded-xl border border-gray-100">
                    <div className="w-7 h-7 bg-red-100 rounded-lg flex items-center justify-center shrink-0">
                      <span className="text-red-600 text-[10px] font-bold">PDF</span>
                    </div>
                    <span className="text-sm text-gray-700 truncate flex-1">{f.name}</span>
                    <span className="text-xs text-gray-400 shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                    <button
                      onClick={() => removeArchivo(i)}
                      className="text-gray-300 hover:text-red-500 transition-colors shrink-0"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Emails */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-2">
              <Mail className="w-4 h-4 inline mr-1.5 text-gray-400 -mt-0.5" />
              Notificar por correo{' '}
              <span className="text-gray-400 font-normal">(opcional)</span>
            </label>
            <div className="flex gap-2">
              <input
                type="email"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                onKeyDown={handleEmailKeyDown}
                placeholder="inspector@hacienda.es"
                className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all bg-gray-50 focus:bg-white"
              />
              <button
                onClick={addEmail}
                className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5 shrink-0"
              >
                <Plus className="w-4 h-4" />
                Añadir
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">Presiona Enter o coma para añadir varios</p>

            {emails.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {emails.map((e, i) => (
                  <span
                    key={i}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 border border-blue-100 text-blue-700 rounded-full text-sm"
                  >
                    <Mail className="w-3.5 h-3.5 shrink-0" />
                    {e}
                    <button
                      onClick={() => setEmails(prev => prev.filter((_, idx) => idx !== i))}
                      className="hover:text-red-500 transition-colors ml-0.5"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex gap-3 border-t border-gray-100 pt-4">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-5 py-3 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50 shrink-0"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !tipoId || !nombre.trim()}
            className={`flex-1 py-3 rounded-xl text-sm font-bold text-white transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm ${
              tipo ? tipo.btnClass : 'bg-gray-800 hover:bg-gray-700'
            }`}
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Creando expediente...</>
            ) : (
              <>
                {tipo && <tipo.Icon className="w-4 h-4" />}
                Crear Expediente
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
