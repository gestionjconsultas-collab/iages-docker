// frontend/src/components/Login.jsx - VERSIÓN LOGO EXTRA GRANDE
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../utils/axiosConfig';
import { useAuth } from '../AuthContext';
import { useTenant } from '../contexts/TenantContext';
import { Eye, EyeOff, Lock, Mail, AlertCircle, Loader2 } from 'lucide-react';
import TwoFactorVerify from './TwoFactorVerify';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const navigate = useNavigate();
  const auth = useAuth();
  const { tenant, loading: tenantLoading } = useTenant();

  // Estado para el modal de recuperación de contraseña
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState('');
  const [forgotError, setForgotError] = useState('');

  // Branding dinámico
  const logoUrl = tenant?.configuracion?.logo || '/logo-light.png';
  const logoWhiteUrl = tenant?.configuracion?.logo_white || '/logo-dark.png';
  const tenantName = tenant?.nombre || 'IAGES';
  const welcomeMessage = tenant?.configuracion?.mensaje_bienvenida || 'Bienvenido de vuelta';
  const subtitle = tenant?.configuracion?.subtitulo || 'Accede a tu panel de gestión';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const success = await auth.login(email, password);

      // Verificar si requiere 2FA
      if (success === 'requires_2fa') {
        setRequires2FA(true);
        setLoading(false);
        return;
      }

      if (success) {
        // Clear React Query cache before navigating (requires useQueryClient)
        // We'll dispatch a custom event or simply rely on window routing to force unmount,
        // but the best way without refactoring hooks is window.location for total reset if needed.
        // Or we can just let AuthContext trigger a re-render. Since we didn't inject useQueryClient here,
        // using window.location guarantees a clean state for a new user.
        window.location.href = '/';
      } else {
        setError('Credenciales incorrectas. Por favor, verifica tu email y contraseña.');
      }
    } catch (err) {
      setError('Error al iniciar sesión. Por favor, intenta de nuevo.');
      console.error('Error de login:', err);
    } finally {
      setLoading(false);
    }
  };

  const handle2FASuccess = (user) => {
    // Actualizar el usuario en AuthContext
    auth.setUser(user);
    // Redirigir al dashboard con recarga completa para limpiar caché
    window.location.href = '/';
  };

  // Si requiere 2FA, mostrar pantalla de verificación
  if (requires2FA) {
    return <TwoFactorVerify onSuccess={handle2FASuccess} />;
  }

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotError('');
    setForgotSuccess('');
    setForgotLoading(true);

    try {
      const res = await axios.post('/api/auth/forgot-password', { email: forgotEmail });

      setForgotSuccess(res.data.message || 'Instrucciones enviadas a tu correo.');
      setTimeout(() => {
        setShowForgotModal(false);
        setForgotSuccess('');
        setForgotEmail('');
      }, 3000);
    } catch (err) {
      setForgotError(err.response?.data?.error || 'Error al procesar la solicitud.');
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Sección Izquierda - Formulario */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-white">
        <div className="w-full max-w-md space-y-8">
          {/* Logo y Título - EXTRA GRANDE */}
          <div className="text-center">
            <img
              src={logoUrl}
              alt={tenantName}
              className="mx-auto h-40 w-auto mb-10 transition-transform hover:scale-105 drop-shadow-lg"
              onError={(e) => {
                // Fallback si no se encuentra el logo
                e.target.style.display = 'none';
                e.target.nextElementSibling.style.display = 'block';
              }}
            />
            {/* Fallback logo con texto */}
            <div className="hidden">
              <div className="inline-flex items-center gap-3 mb-10">
                <div className="text-6xl font-bold drop-shadow-md">
                  <span className="text-gray-800">Spain</span>
                  <span className="text-primary">Flow</span>
                </div>
              </div>
            </div>

            <h2 className="text-3xl font-bold text-gray-900 mb-2">
              {welcomeMessage}
            </h2>
            <p className="text-gray-600">
              {subtitle}
            </p>
          </div>

          {/* Formulario */}
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            {/* Error Alert */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 animate-shake">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            )}

            {/* Email Input */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                NIF / Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="text"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg 
                           focus:ring-2 focus:ring-primary focus:border-transparent
                           placeholder-gray-400 text-gray-900 transition-all"
                  placeholder="Introduce tu NIF o email"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Contraseña
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg 
                           focus:ring-2 focus:ring-primary focus:border-transparent
                           placeholder-gray-400 text-gray-900 transition-all"
                  placeholder="Introduce tu contraseña"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 
                           hover:text-gray-600 transition-colors"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 
                       bg-linear-to-r from-orange-500 to-red-500 
                       hover:from-orange-600 hover:to-red-600
                       text-white font-semibold rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]
                       shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Iniciando sesión...
                </>
              ) : (
                'Iniciar sesión'
              )}
            </button>

            {/* Registro */}
            <div className="text-center">
              <p className="text-sm text-gray-600">
                ¿Olvidaste tu contraseña?{' '}
                <button
                  type="button"
                  onClick={() => setShowForgotModal(true)}
                  className="font-medium text-orange-600 hover:text-orange-500 transition-colors"
                >
                  Recupérala aquí
                </button>
              </p>
            </div>
          </form>

          {/* Modal de Recuperación de Contraseña */}
          {showForgotModal && (
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full overflow-hidden border border-gray-100">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Recuperar Contraseña</h3>
                  <p className="text-sm text-gray-600 mb-6">
                    Introduce tu email y te enviaremos un enlace para crear una nueva.
                  </p>

                  {forgotSuccess && (
                    <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-lg text-sm border border-green-200">
                      {forgotSuccess}
                    </div>
                  )}
                  {forgotError && (
                    <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
                      {forgotError}
                    </div>
                  )}

                  <form onSubmit={handleForgotPassword}>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                        <div className="relative">
                          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                          <input
                            type="email"
                            required
                            value={forgotEmail}
                            onChange={(e) => setForgotEmail(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary outline-hidden text-sm"
                            placeholder="tu@email.com"
                          />
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 flex gap-3">
                      <button
                        type="button"
                        onClick={() => { setShowForgotModal(false); setForgotError(''); setForgotSuccess(''); }}
                        className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors text-sm font-semibold"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        disabled={forgotLoading}
                        className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors text-sm font-bold shadow-md disabled:opacity-50 flex justify-center items-center"
                      >
                        {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Enviar Enlace'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="text-center text-xs text-gray-500 mt-8">
            <p>© {new Date().getFullYear()} {tenantName}. Todos los derechos reservados.</p>
          </div>
        </div>
      </div>

      {/* Sección Derecha - Imagen/Branding */}
      <div className="hidden lg:flex lg:flex-1 relative bg-linear-to-br from-orange-400 via-red-400 to-orange-600 overflow-hidden">
        {/* Patrón de fondo */}
        <div className="absolute inset-0 bg-black opacity-20"></div>
        <div className="absolute inset-0" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }}></div>

        {/* Contenido */}
        <div className="relative z-10 flex flex-col items-center justify-center p-12 text-white w-full">
          {/* Logo grande - MUCHO MÁS GRANDE */}
          <div className="mb-16">
            <img
              src={logoWhiteUrl}
              alt={tenantName}
              className="h-48 w-auto drop-shadow-2xl mx-auto transition-transform hover:scale-110 animate-pulse-slow"
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.nextElementSibling.style.display = 'block';
              }}
            />
            {/* Fallback logo blanco */}
            <div className="hidden text-center">
              <div className="text-8xl font-bold drop-shadow-2xl">
                <span className="text-white">Spain</span>
                <span className="text-orange-200">Flow</span>
              </div>
            </div>
          </div>

          {/* Texto principal */}
          <div className="max-w-md text-center space-y-6">
            <h1 className="text-4xl font-bold drop-shadow-lg">
              Sistema de Gestión Documental
            </h1>
            <p className="text-xl text-orange-100 leading-relaxed drop-shadow">
              Gestiona todas tus notificaciones, documentos y tareas empresariales
              de forma centralizada y eficiente
            </p>

            {/* Features */}
            <div className="grid grid-cols-2 gap-4 mt-12">
              <div className="bg-opacity-10 backdrop-blur-sm rounded-lg p-4 
                            border border-white border-opacity-20 hover:bg-opacity-20 transition-all">
                <div className="text-3xl mb-2">📊</div>
                <div className="text-sm font-semibold">Dashboard Completo</div>
              </div>
              <div className="bg-opacity-10 backdrop-blur-sm rounded-lg p-4 
                            border border-white border-opacity-20 hover:bg-opacity-20 transition-all">
                <div className="text-3xl mb-2">🤖</div>
                <div className="text-sm font-semibold">IA Integrada</div>
              </div>
              <div className="bg-opacity-10 backdrop-blur-sm rounded-lg p-4 
                            border border-white border-opacity-20 hover:bg-opacity-20 transition-all">
                <div className="text-3xl mb-2">📧</div>
                <div className="text-sm font-semibold">Envío Automático</div>
              </div>
              <div className="bg-opacity-10 backdrop-blur-sm rounded-lg p-4 
                            border border-white border-opacity-20 hover:bg-opacity-20 transition-all">
                <div className="text-3xl mb-2">🔒</div>
                <div className="text-sm font-semibold">100% Seguro</div>
              </div>
            </div>
          </div>

          {/* Decoración inferior */}
          <div className="absolute bottom-0 left-0 right-0 h-32 bg-linear-to-t from-black to-transparent opacity-30"></div>
        </div>
      </div>

      {/* Animación CSS */}
      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
          20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.9; }
        }
        .animate-pulse-slow {
          animation: pulse-slow 3s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}