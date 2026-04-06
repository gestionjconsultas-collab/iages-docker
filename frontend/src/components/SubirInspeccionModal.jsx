// frontend/src/components/SubirInspeccionModal.jsx
import React, { useState, useRef, useEffect } from 'react';
import {
  X, Upload, ShieldAlert, FileSearch, Banknote, Scale, Loader2, Check, ChevronDown, Search
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { useGrupos } from '../hooks/useGruposDocumentos';

const TIPOS = [
  { id: 'inspeccion',       label: 'Inspección',                   Icon: ShieldAlert, color: 'red',    prefix: 'Inspección'      },
  { id: 'requerimiento',    label: 'Requerimiento de Información',  Icon: FileSearch,  color: 'blue',   prefix: 'Requerimiento'   },
  { id: 'embargo_salario',  label: 'Embargo de Salario',            Icon: Banknote,    color: 'orange', prefix: 'Embargo Salario' },
  { id: 'embargo_creditos', label: 'Embargo Créditos y Derechos',   Icon: Scale,       color: 'purple', prefix: 'Embargo Créditos'},
];

export default function SubirInspeccionModal({ empresaId, onClose, onSuccess }) {
  const año = new Date().getFullYear();
  const [archivos, setArchivos] = useState([]);
  const [destino, setDestino] = useState('existente');
  const [grupoId, setGrupoId] = useState('');
  const [tipoId, setTipoId] = useState(null);
  const [nombre, setNombre] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [busquedaGrupo, setBusquedaGrupo] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const fileRef = useRef();
  const dropdownRef = useRef();

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const { data: grupos = [] } = useGrupos(empresaId);
  const tipo = TIPOS.find(t => t.id === tipoId);

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

  const handleTipoSelect = (t) => {
    setTipoId(t.id);
    const esAutogenerado = TIPOS.some(tp => nombre === `${tp.prefix} - ${año}`);
    if (!nombre || esAutogenerado) setNombre(`${t.prefix} - ${año}`);
  };

  const handleSubmit = async () => {
    if (archivos.length === 0) { toast.error('Añade al menos un archivo'); return; }
    if (destino === 'existente' && !grupoId) { toast.error('Selecciona un expediente'); return; }
    if (destino === 'nuevo' && !tipoId) { toast.error('Selecciona el tipo de expediente'); return; }
    if (destino === 'nuevo' && !nombre.trim()) { toast.error('El nombre es obligatorio'); return; }

    setLoading(true);
    try {
      let targetGrupoId = grupoId;

      if (destino === 'nuevo') {
        const grupoRes = await axios.post('/api/grupos-documentos', {
          nombre: nombre.trim(),
          empresa_id: empresaId,
          color: tipo.color,
          descripcion: tipo.label,
        }, { withCredentials: true });
        if (!grupoRes.data.success) throw new Error(grupoRes.data.error);
        targetGrupoId = grupoRes.data.grupo.id;
      }

      const formData = new FormData();
      archivos.forEach(f => formData.append('files[]', f));
      formData.append('empresa_id', empresaId);
      formData.append('categoria', 'Inspecciones');
      const uploadRes = await axios.post('/api/subir-directo-multiple', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      const docIds = uploadRes.data.documento_ids || [];
      for (const docId of docIds) {
        await axios.post(`/api/grupos-documentos/${targetGrupoId}/documentos`,
          { documento_id: docId }, { withCredentials: true }
        );
      }

      toast.success(`${archivos.length} archivo(s) subido(s) correctamente`);
      onSuccess?.();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.error || err.message || 'Error al subir');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-orange-100 flex items-center justify-center">
              <Upload className="w-4 h-4 text-orange-600" />
            </div>
            <h2 className="text-lg font-bold text-gray-900">Subir documentos</h2>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-xl hover:bg-gray-100 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-5">

          {/* Drop zone */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-2">Archivos PDF</label>
            <div
              className={`border-2 border-dashed rounded-2xl p-5 text-center cursor-pointer transition-all ${
                isDragging ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => fileRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={e => { e.preventDefault(); setIsDragging(false); handleFiles(e.dataTransfer.files); }}
            >
              <input ref={fileRef} type="file" multiple accept="application/pdf" className="hidden" onChange={e => handleFiles(e.target.files)} />
              <Upload className={`w-7 h-7 mx-auto mb-2 transition-colors ${isDragging ? 'text-primary' : 'text-gray-300'}`} />
              <p className="text-sm text-gray-500">
                Arrastra PDFs aquí o <span className="text-primary font-semibold">selecciona archivos</span>
              </p>
            </div>

            {archivos.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {archivos.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-xl text-sm border border-gray-100">
                    <span className="text-[10px] font-bold text-red-600 bg-red-100 rounded px-1.5 py-0.5 shrink-0">PDF</span>
                    <span className="truncate flex-1 text-gray-700">{f.name}</span>
                    <span className="text-xs text-gray-400 shrink-0">{(f.size / 1024).toFixed(0)} KB</span>
                    <button
                      onClick={() => setArchivos(prev => prev.filter((_, idx) => idx !== i))}
                      className="text-gray-300 hover:text-red-500 shrink-0 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Destino */}
          <div>
            <label className="block text-sm font-semibold text-gray-800 mb-3">¿A qué expediente?</label>

            {/* Toggle */}
            <div className="flex gap-2 mb-4 p-1 bg-gray-100 rounded-xl">
              <button
                onClick={() => setDestino('existente')}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all ${
                  destino === 'existente' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Existente
              </button>
              <button
                onClick={() => setDestino('nuevo')}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all ${
                  destino === 'nuevo' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Nuevo expediente
              </button>
            </div>

            {/* Grupo existente — buscador */}
            {destino === 'existente' && (
              <div className="relative" ref={dropdownRef}>
                {/* Input buscador */}
                <div
                  className={`flex items-center gap-2 px-4 py-3 border rounded-xl bg-white cursor-text transition-all ${
                    dropdownOpen ? 'border-primary ring-2 ring-primary/20' : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setDropdownOpen(true)}
                >
                  <Search className="w-4 h-4 text-gray-400 shrink-0" />
                  <input
                    type="text"
                    value={dropdownOpen ? busquedaGrupo : (grupos.find(g => g.id == grupoId)?.nombre || '')}
                    onChange={e => { setBusquedaGrupo(e.target.value); setGrupoId(''); }}
                    onFocus={() => { setDropdownOpen(true); setBusquedaGrupo(''); }}
                    placeholder="Buscar expediente..."
                    className="flex-1 outline-none text-sm text-gray-700 bg-transparent placeholder-gray-400"
                  />
                  {grupoId && !dropdownOpen && (
                    <button onClick={(e) => { e.stopPropagation(); setGrupoId(''); setBusquedaGrupo(''); }} className="text-gray-300 hover:text-gray-500 transition-colors">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
                </div>

                {/* Dropdown */}
                {dropdownOpen && (
                  <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
                    {(() => {
                      const filtrados = grupos.filter(g =>
                        g.nombre.toLowerCase().includes(busquedaGrupo.toLowerCase())
                      );
                      if (filtrados.length === 0) {
                        return (
                          <div className="px-4 py-6 text-center">
                            <p className="text-sm text-gray-400">Sin resultados para "<span className="font-medium">{busquedaGrupo}</span>"</p>
                          </div>
                        );
                      }
                      return (
                        <ul className="max-h-52 overflow-y-auto py-1">
                          {filtrados.map(g => (
                            <li key={g.id}>
                              <button
                                onClick={() => { setGrupoId(g.id); setBusquedaGrupo(''); setDropdownOpen(false); }}
                                className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 transition-colors ${
                                  grupoId == g.id ? 'bg-primary/5 text-primary font-semibold' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                              >
                                <span className="flex-1 truncate">{g.nombre}</span>
                                {grupoId == g.id && <Check className="w-3.5 h-3.5 text-primary shrink-0" strokeWidth={3} />}
                              </button>
                            </li>
                          ))}
                        </ul>
                      );
                    })()}
                  </div>
                )}

                {grupos.length === 0 && (
                  <p className="mt-2 text-xs text-gray-400">No hay expedientes creados aún. Usa "Nuevo expediente".</p>
                )}
              </div>
            )}

            {/* Nuevo expediente */}
            {destino === 'nuevo' && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  {TIPOS.map(t => (
                    <button
                      key={t.id}
                      onClick={() => handleTipoSelect(t)}
                      className={`flex items-center gap-2 p-3 rounded-xl border-2 text-left transition-all ${
                        tipoId === t.id ? 'border-primary bg-primary/5' : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <t.Icon className={`w-4 h-4 shrink-0 ${tipoId === t.id ? 'text-primary' : 'text-gray-400'}`} />
                      <span className={`text-xs font-semibold leading-tight flex-1 ${tipoId === t.id ? 'text-primary' : 'text-gray-600'}`}>
                        {t.label}
                      </span>
                      {tipoId === t.id && <Check className="w-3 h-3 text-primary shrink-0" strokeWidth={3} />}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  value={nombre}
                  onChange={e => setNombre(e.target.value)}
                  placeholder="Nombre del expediente"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-primary focus:border-transparent outline-none bg-gray-50 focus:bg-white transition-all"
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex gap-3 border-t border-gray-100 pt-4">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-5 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50 shrink-0"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || archivos.length === 0}
            className="flex-1 py-2.5 bg-[#f97316] hover:bg-[#ea580c] text-white rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {loading
              ? <><Loader2 className="w-4 h-4 animate-spin" />Subiendo...</>
              : <><Upload className="w-4 h-4" />Subir archivos</>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
