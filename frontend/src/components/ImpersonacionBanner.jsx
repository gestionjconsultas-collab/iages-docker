import React, { useState } from 'react';
import { Eye, LogOut } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function ImpersonacionBanner({ gestoriaNombre, onTerminar }) {
  const [loading, setLoading] = useState(false);

  const terminar = async () => {
    setLoading(true);
    try {
      await axios.post('/api/impersonacion/terminar', {}, { withCredentials: true });
      toast.success('Sesión de soporte terminada');
      onTerminar();
    } catch {
      toast.error('Error al terminar sesión');
      setLoading(false);
    }
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-[9998] bg-gradient-to-r from-amber-500 to-orange-500 px-4 py-2 flex items-center justify-between shadow-lg">
      <div className="flex items-center gap-2 text-white">
        <Eye className="w-4 h-4" />
        <span className="text-sm font-semibold">
          Modo Soporte — Viendo: <strong>{gestoriaNombre}</strong>
        </span>
      </div>
      <button
        onClick={terminar}
        disabled={loading}
        className="flex items-center gap-1.5 bg-white/20 hover:bg-white/30 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
      >
        <LogOut className="w-4 h-4" />
        Terminar sesión
      </button>
    </div>
  );
}
