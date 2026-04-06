import React, { useState } from 'react';
import { Shield, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function TwoFactorVerify({ onSuccess }) {
    const [token, setToken] = useState('');
    const [loading, setLoading] = useState(false);
    const [showBackupInput, setShowBackupInput] = useState(false);

    const handleVerify = async (e) => {
        e.preventDefault();

        if (token.length < 6) {
            toast.error('Ingresa un código válido');
            return;
        }

        setLoading(true);

        try {
            const response = await axios.post('/api/auth/2fa/verify', { token }, { withCredentials: true });

            if (response.data.backup_code_used) {
                toast.success(`Acceso concedido. Códigos restantes: ${response.data.remaining_codes}`);
            } else {
                toast.success('¡Acceso concedido!');
            }

            onSuccess(response.data.user);
        } catch (error) {
            toast.error(error.response?.data?.error || 'Código inválido');
            setToken('');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-orange-100 p-4">
            <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8">
                <div className="text-center mb-6">
                    <Shield className="w-12 h-12 mx-auto text-orange-500 mb-4" />
                    <h2 className="text-2xl font-bold text-gray-800">Verificación de Dos Factores</h2>
                    <p className="text-gray-600 mt-2">
                        {showBackupInput
                            ? 'Ingresa un código de respaldo'
                            : 'Ingresa el código de 6 dígitos de tu app de autenticación'
                        }
                    </p>
                </div>

                <form onSubmit={handleVerify} className="space-y-4">
                    <div>
                        <input
                            type="text"
                            value={token}
                            onChange={(e) => setToken(e.target.value.replace(/\s/g, '').toUpperCase())}
                            className="w-full p-4 border-2 border-gray-300 rounded-lg text-center text-3xl tracking-widest font-mono focus:border-orange-500 focus:outline-none"
                            placeholder={showBackupInput ? "XXXXXXXX" : "000000"}
                            maxLength={showBackupInput ? 8 : 6}
                            autoFocus
                            autoComplete="off"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={token.length < 6 || loading}
                        className="w-full py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        {loading ? 'Verificando...' : 'Verificar'}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <button
                        onClick={() => setShowBackupInput(!showBackupInput)}
                        className="text-sm text-orange-600 hover:text-orange-700 underline"
                    >
                        {showBackupInput
                            ? '← Volver a código TOTP'
                            : '¿Perdiste tu dispositivo? Usa un código de respaldo'
                        }
                    </button>
                </div>

                <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-blue-800">
                            <strong>Consejo:</strong> El código cambia cada 30 segundos. Si no funciona, espera al siguiente código.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
