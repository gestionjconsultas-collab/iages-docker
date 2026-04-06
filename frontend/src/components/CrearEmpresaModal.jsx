// frontend/src/components/CrearEmpresaModal.jsx
import React, { useState } from 'react';
import { X, Building2, Save, Loader2, FileText, Mail } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';

export default function CrearEmpresaModal({ onClose, onEmpresaCreada, initialNif = '' }) {
  useEscapeKey(onClose);
  const [formData, setFormData] = useState({ 
    nombre: '', 
    nif: initialNif || '', 
    email: '',
    codigo_empresa: '',
    telefono: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault(); setLoading(true); setError('');
    try {
      const res = await axios.post('/api/empresas/crear', formData, { withCredentials: true });
      if (res.data.success) {
        toast.success("✅ Empresa creada exitosamente.");
        onEmpresaCreada(res.data.empresa); 
        onClose();
      }
    } catch (err) {
      setError(err.response?.data?.error || "Error al crear");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4" style={{ zIndex: 100 }} onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center p-4 border-b bg-gray-50">
          <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2"><Building2 className="w-5 h-5 text-primary"/> Nueva Empresa</h3>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-500 hover:text-gray-700"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">NIF / CIF *</label>
            <div className="relative"><FileText className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" /><input required className="w-full pl-9 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none uppercase" placeholder="B12345678" value={formData.nif} onChange={e => setFormData({...formData, nif: e.target.value.toUpperCase()})}/></div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Razón Social *</label>
            <div className="relative"><Building2 className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" /><input required className="w-full pl-9 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none" placeholder="Nombre de la empresa" value={formData.nombre} onChange={e => setFormData({...formData, nombre: e.target.value})}/></div>
            <p className="text-[10px] text-gray-500 mt-1">Se creará una carpeta con este nombre.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email (Opcional)</label>
            <div className="relative"><Mail className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" /><input type="email" className="w-full pl-9 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none" placeholder="contacto@empresa.com" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})}/></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Código Empresa</label>
              <input className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none text-sm" placeholder="EMP-001" value={formData.codigo_empresa} onChange={e => setFormData({...formData, codigo_empresa: e.target.value})}/>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
              <input className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none text-sm" placeholder="600000000" value={formData.telefono} onChange={e => setFormData({...formData, telefono: e.target.value})}/>
            </div>
          </div>
          {error && <div className="p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-100">{error}</div>}
          <div className="pt-2"><button type="submit" disabled={loading} className="w-full py-2.5 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg font-bold shadow-md hover:shadow-lg transition-all flex justify-center items-center gap-2 disabled:opacity-50">{loading ? <Loader2 className="w-5 h-5 animate-spin"/> : <Save className="w-5 h-5"/>} Crear Empresa</button></div>
        </form>
      </div>
    </div>
  );
}