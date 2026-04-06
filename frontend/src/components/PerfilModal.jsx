// frontend/src/components/PerfilModal.jsx
import React, { useState } from 'react';
import { X, User, Lock, Save, Loader2, Shield } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../AuthContext';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';



export default function PerfilModal({ onClose }) {
  useEscapeKey(onClose);
  const { user, login } = useAuth(); // login se usa aquí para actualizar el estado local si es necesario
  const [nombre, setNombre] = useState(user?.nombre || '');
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);


  const handleSave = async () => {
    if (password && password !== confirmPassword) {
      toast.error("Las contraseñas no coinciden");
      return;
    }

    setLoading(true);
    try {
      const payload = { nombre, email };
      if (password) payload.password = password;

      const res = await axios.put('/api/users/me/update', payload, { withCredentials: true });

      if (res.data.success) {
        toast.success("Perfil actualizado correctamente");
        // Opcional: Forzar recarga para actualizar nombre en el header
        window.location.reload();
      }
    } catch (err) {
      toast.error("Error al actualizar: " + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-100 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
            <User className="w-6 h-6 text-primary" /> Mi Perfil
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X /></button>
        </div>

        <div className="space-y-4">
          {/* Email Modificable */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email de Acceso</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 flex justify-between items-center">
            <div>
              <p className="text-xs text-gray-500 uppercase font-bold">Departamento</p>
              <p className="text-gray-700">{user?.departamento}</p>
            </div>
            <Shield className="w-5 h-5 text-gray-400" />
          </div>

          <hr />

          {/* Edición */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Completo</label>
            <input
              type="text"
              value={nombre}
              onChange={e => setNombre(e.target.value)}
              className="w-full p-2 border rounded-lg focus:ring-2 focus:ring-primary outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nueva Contraseña (Opcional)</label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input
                type="password"
                placeholder="Dejar en blanco para mantener la actual"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full pl-9 p-2 border rounded-lg focus:ring-2 focus:ring-primary outline-none"
              />
            </div>
          </div>

          {password && (
            <div className="animate-fade-in">
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar Contraseña</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
                className={`w-full p-2 border rounded-lg outline-none ${password !== confirmPassword ? 'border-red-300 focus:ring-red-500' : 'border-green-300 focus:ring-green-500'}`}
              />
            </div>
          )}
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancelar</button>
          <button
            onClick={handleSave}
            disabled={loading || (password && password !== confirmPassword)}
            className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Guardar Cambios
          </button>
        </div>

      </div>
    </div>
  );
}