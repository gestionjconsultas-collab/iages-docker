import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Lock, Eye, EyeOff, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { authApi } from '../api/auth';

export default function Activar({ onActivado }) {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const isReset = searchParams.get('reset') === '1';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const strength = (() => {
    if (!password) return 0;
    let s = 0;
    if (password.length >= 8) s++;
    if (/[A-Z]/.test(password)) s++;
    if (/[0-9]/.test(password)) s++;
    if (/[^A-Za-z0-9]/.test(password)) s++;
    return s;
  })();

  const strengthLabel = ['', 'Débil', 'Regular', 'Buena', 'Fuerte'];
  const strengthColor = ['', 'bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirm) {
      setError('Las contraseñas no coinciden');
      return;
    }
    if (password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setLoading(true);
    try {
      const data = await authApi.activar(token, password);
      setSuccess(true);
      if (data.token && onActivado) {
        setTimeout(() => onActivado(data.empleado), 1500);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Enlace inválido o expirado');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div className="text-center">
          <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900">Enlace inválido</h2>
          <p className="text-gray-500 mt-2">Este enlace de activación no es válido.</p>
          <Link to="/login" className="mt-4 inline-block text-blue-600 hover:underline">
            Ir al inicio de sesión
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 shadow-lg mb-4">
            <span className="text-white text-2xl font-bold">P</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isReset ? 'Nueva contraseña' : 'Activar cuenta'}
          </h1>
          <p className="text-gray-500 mt-1">
            {isReset
              ? 'Escribe tu nueva contraseña'
              : 'Elige una contraseña para acceder al portal'}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          {success ? (
            <div className="text-center py-4">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-gray-900">
                {isReset ? '¡Contraseña actualizada!' : '¡Cuenta activada!'}
              </h3>
              <p className="text-gray-500 mt-2">Redirigiendo al portal...</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              {/* Nueva contraseña */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nueva contraseña
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    placeholder="Mínimo 8 caracteres"
                    className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {/* Indicador de fuerza */}
                {password && (
                  <div className="mt-2">
                    <div className="flex gap-1 h-1">
                      {[1, 2, 3, 4].map(i => (
                        <div
                          key={i}
                          className={`flex-1 rounded-full ${i <= strength ? strengthColor[strength] : 'bg-gray-200'}`}
                        />
                      ))}
                    </div>
                    <p className={`text-xs mt-1 ${strength >= 3 ? 'text-green-600' : 'text-gray-500'}`}>
                      Seguridad: {strengthLabel[strength]}
                    </p>
                  </div>
                )}
              </div>

              {/* Confirmar */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirmar contraseña
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={confirm}
                    onChange={e => setConfirm(e.target.value)}
                    required
                    placeholder="Repite la contraseña"
                    className={`w-full pl-10 pr-4 py-2.5 border rounded-lg
                                focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm
                                ${confirm && password !== confirm
                                  ? 'border-red-400 bg-red-50'
                                  : 'border-gray-300'}`}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4
                           bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
                           text-white font-semibold rounded-lg transition shadow-sm"
              >
                {loading && (
                  <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                )}
                {loading ? 'Guardando...' : isReset ? 'Cambiar contraseña' : 'Activar cuenta'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
