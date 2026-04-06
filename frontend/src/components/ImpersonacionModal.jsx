import React, { useState, useEffect } from 'react';
import { Shield, X, Check, Clock } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function ImpersonacionModal({ solicitud, onClose }) {
  const [segundos, setSegundos] = useState(300); // 5 min
  const [loading, setLoading] = useState(null);

  useEffect(() => {
    if (segundos <= 0) { onClose(); return; }
    const t = setInterval(() => setSegundos(s => s - 1), 1000);
    return () => clearInterval(t);
  }, [segundos]);

  const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

  const responder = async (accion) => {
    setLoading(accion);
    try {
      await axios.post('/api/impersonacion/responder', {
        request_id: solicitud.request_id,
        accion
      }, { withCredentials: true });
      toast.success(accion === 'aceptar' ? 'Acceso concedido' : 'Acceso denegado');
      onClose();
    } catch {
      toast.error('Error al responder');
      setLoading(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[9999] p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <Shield className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-white font-bold text-lg">Solicitud de Acceso</h2>
              <p className="text-white/80 text-sm">Soporte técnico</p>
            </div>
            <div className="ml-auto flex items-center gap-1.5 bg-white/20 px-3 py-1.5 rounded-full">
              <Clock className="w-4 h-4 text-white" />
              <span className="text-white font-mono text-sm font-bold">{formatTime(segundos)}</span>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6">
          <p className="text-gray-700 text-base mb-2">
            <span className="font-bold text-gray-900">{solicitud.soporte_nombre}</span> del equipo de soporte solicita acceso temporal a tu gestoría.
          </p>
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mt-4 text-sm text-amber-800">
            Si aceptas, el agente de soporte podrá ver y gestionar los datos de tu gestoría durante un máximo de <strong>30 minutos</strong>. Todo queda registrado en auditoría.
          </div>
        </div>

        {/* Acciones */}
        <div className="px-6 pb-6 flex gap-3">
          <button
            onClick={() => responder('rechazar')}
            disabled={!!loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 border-2 border-gray-200 text-gray-700 font-semibold rounded-xl hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" /> Rechazar
          </button>
          <button
            onClick={() => responder('aceptar')}
            disabled={!!loading}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-colors disabled:opacity-50"
          >
            {loading === 'aceptar' ? (
              <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />
            ) : (
              <Check className="w-5 h-5" />
            )}
            Aceptar
          </button>
        </div>
      </div>
    </div>
  );
}
