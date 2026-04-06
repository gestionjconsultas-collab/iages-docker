import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react';
import { authApi } from '../api/auth';

export default function Recuperar() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authApi.recuperar(email);
      setSent(true);
    } catch {
      setError('Error al procesar la solicitud. Inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 shadow-lg mb-4">
            <span className="text-white text-2xl font-bold">P</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Recuperar acceso</h1>
          <p className="text-gray-500 mt-1">Te enviaremos un enlace para restablecer tu contraseña</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          {sent ? (
            <div className="text-center py-4">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-bold text-gray-900">Correo enviado</h3>
              <p className="text-gray-500 mt-2 text-sm">
                Si tu email está registrado, recibirás las instrucciones en breve.
                Revisa también la carpeta de spam.
              </p>
              <Link
                to="/login"
                className="mt-6 inline-flex items-center gap-2 text-blue-600 hover:underline text-sm"
              >
                <ArrowLeft className="w-4 h-4" />
                Volver al inicio de sesión
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Correo electrónico
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="tu@email.com"
                    className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg
                               focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
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
                {loading ? 'Enviando...' : 'Enviar enlace'}
              </button>

              <div className="text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  Volver al inicio de sesión
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
