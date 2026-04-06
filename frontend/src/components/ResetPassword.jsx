// frontend/src/components/ResetPassword.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTenant } from '../contexts/TenantContext';
import { Eye, EyeOff, Lock, AlertCircle, Loader2, CheckCircle } from 'lucide-react';
import axios from 'axios';

export default function ResetPassword() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get('token');

    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const navigate = useNavigate();
    const { tenant } = useTenant();

    // Branding dinámico
    const logoUrl = tenant?.configuracion?.logo || '/logo-light.png';
    const tenantName = tenant?.nombre || 'IAGES';

    const [tokenChecked, setTokenChecked] = useState(false);

    useEffect(() => {
        if (!token) {
            navigate('/login', { replace: true });
            return;
        }
        // Validate token with backend before showing the form
        axios.get(`/api/auth/validate-reset-token?token=${token}`)
            .then(() => {
                setTokenChecked(true);
            })
            .catch((err) => {
                const msg = err.response?.data?.error || 'El enlace de recuperación ha caducado o es inválido.';
                // Redirect to login — pass error message via state
                navigate('/login', { replace: true, state: { resetError: msg } });
            });
    }, [token, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Las contraseñas no coinciden.');
            return;
        }

        if (password.length < 8) {
            setError('La contraseña debe tener al menos 8 caracteres.');
            return;
        }

        setLoading(true);

        try {
            const res = await axios.post('/api/auth/reset-password', {
                token: token,
                password: password
            });

            setSuccess(res.data.message || 'Contraseña restablecida exitosamente');

            // Redirigir al login después de 3 segundos
            setTimeout(() => {
                navigate('/login');
            }, 3000);

        } catch (err) {
            setError(err.response?.data?.error || 'Error al restablecer la contraseña. Puede que el enlace haya expirado.');

            if (err.response?.data?.errors) {
                setError(err.response.data.errors.join('. '));
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8 bg-white p-10 rounded-2xl shadow-xl">
                <div className="text-center">
                    <img
                        src={logoUrl}
                        alt={tenantName}
                        className="mx-auto h-24 w-auto mb-6"
                        onError={(e) => { e.target.style.display = 'none'; }}
                    />
                    <h2 className="text-3xl font-bold text-gray-900 mb-2">
                        Restablecer Contraseña
                    </h2>
                    <p className="text-sm text-gray-600">
                        Ingresa tu nueva contraseña a continuación.
                    </p>
                </div>

                {/* Spinner mientras se valida el token con el backend */}
                {!tokenChecked ? (
                    <div className="flex flex-col items-center justify-center py-10 gap-3">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                        <p className="text-sm text-gray-500">Verificando enlace...</p>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
                                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                                <p className="text-sm text-red-800">{error}</p>
                            </div>
                        )}

                        {success ? (
                            <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center space-y-4">
                                <div className="flex justify-center">
                                    <CheckCircle className="w-12 h-12 text-green-500" />
                                </div>
                                <p className="text-green-800 font-medium">{success}</p>
                                <p className="text-sm text-green-600">Redirigiendo al inicio de sesión...</p>
                                <button
                                    onClick={() => navigate('/login')}
                                    className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 w-full transition-colors"
                                >
                                    Ir al Login ahora
                                </button>
                            </div>
                        ) : (
                            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Nueva Contraseña
                                        </label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                                <Lock className="h-5 w-5 text-gray-400" />
                                            </div>
                                            <input
                                                type={showPassword ? 'text' : 'password'}
                                                required
                                                value={password}
                                                onChange={(e) => setPassword(e.target.value)}
                                                className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-hidden"
                                                placeholder="Al menos 8 caracteres"
                                                disabled={loading}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowPassword(!showPassword)}
                                                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                                            >
                                                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                            </button>
                                        </div>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-2">
                                            Confirmar Nueva Contraseña
                                        </label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                                <Lock className="h-5 w-5 text-gray-400" />
                                            </div>
                                            <input
                                                type={showConfirmPassword ? 'text' : 'password'}
                                                required
                                                value={confirmPassword}
                                                onChange={(e) => setConfirmPassword(e.target.value)}
                                                className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-hidden"
                                                placeholder="Repite la contraseña"
                                                disabled={loading}
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                                            >
                                                {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition-all shadow-md disabled:opacity-50"
                                >
                                    {loading ? (
                                        <><Loader2 className="w-5 h-5 animate-spin" /> Guardando...</>
                                    ) : (
                                        'Guardar nueva contraseña'
                                    )}
                                </button>

                                <div className="text-center mt-4">
                                    <button
                                        type="button"
                                        onClick={() => navigate('/login')}
                                        className="text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
                                    >
                                        Volver al inicio de sesión
                                    </button>
                                </div>
                            </form>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
