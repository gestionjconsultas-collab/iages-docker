import React, { useState } from 'react';
import { Shield, Copy, Check, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function TwoFactorSetup({ onComplete, onCancel }) {
    const [step, setStep] = useState(1);
    const [qrCode, setQrCode] = useState('');
    const [secret, setSecret] = useState('');
    const [token, setToken] = useState('');
    const [backupCodes, setBackupCodes] = useState([]);
    const [copied, setCopied] = useState(false);
    const [loading, setLoading] = useState(false);

    const startSetup = async () => {
        setLoading(true);
        try {
            const response = await axios.post('/api/auth/2fa/setup', {}, { withCredentials: true });
            setQrCode(response.data.qr_code);
            setSecret(response.data.secret);
            setStep(2);
            toast.success('Escanea el código QR con tu app de autenticación');
        } catch (error) {
            toast.error('Error al iniciar configuración');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const verifyAndActivate = async () => {
        if (token.length !== 6) {
            toast.error('El código debe tener 6 dígitos');
            return;
        }

        setLoading(true);
        try {
            const response = await axios.post('/api/auth/2fa/verify-setup', { token }, { withCredentials: true });
            setBackupCodes(response.data.backup_codes);
            setStep(3);
            toast.success('¡2FA activado exitosamente!');
        } catch (error) {
            toast.error(error.response?.data?.error || 'Código inválido');
        } finally {
            setLoading(false);
        }
    };

    const copySecret = () => {
        navigator.clipboard.writeText(secret);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        toast.success('Código copiado al portapapeles');
    };

    const copyBackupCodes = () => {
        const text = backupCodes.join('\n');
        navigator.clipboard.writeText(text);
        toast.success('Códigos de respaldo copiados');
    };

    return (
        <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
            {/* Step 1: Intro */}
            {step === 1 && (
                <div className="text-center">
                    <Shield className="w-16 h-16 mx-auto text-orange-500 mb-4" />
                    <h2 className="text-2xl font-bold mb-4">Activar Autenticación de Dos Factores</h2>
                    <p className="text-gray-600 mb-6">
                        Añade una capa extra de seguridad a tu cuenta. Necesitarás una app como Google Authenticator o Authy.
                    </p>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                        <p className="text-sm text-blue-800">
                            <strong>Recomendado:</strong> Descarga Google Authenticator o Authy en tu teléfono antes de continuar.
                        </p>
                    </div>
                    <div className="flex gap-3 justify-center">
                        <button
                            onClick={startSetup}
                            disabled={loading}
                            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition disabled:opacity-50"
                        >
                            {loading ? 'Iniciando...' : 'Comenzar Configuración'}
                        </button>
                        {onCancel && (
                            <button
                                onClick={onCancel}
                                className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                            >
                                Cancelar
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Step 2: Scan QR */}
            {step === 2 && (
                <div>
                    <h3 className="text-xl font-bold mb-4">Escanea el código QR</h3>

                    <div className="bg-white p-6 rounded-lg border-2 border-gray-200 mb-4">
                        <img
                            src={`data:image/png;base64,${qrCode}`}
                            alt="QR Code"
                            className="mx-auto w-64 h-64"
                        />
                    </div>

                    <div className="mb-6">
                        <p className="text-sm text-gray-600 mb-2">O ingresa este código manualmente:</p>
                        <div className="flex items-center gap-2">
                            <code className="flex-1 bg-gray-100 p-3 rounded font-mono text-sm break-all">
                                {secret}
                            </code>
                            <button
                                onClick={copySecret}
                                className="p-3 bg-gray-200 hover:bg-gray-300 rounded transition"
                                title="Copiar código"
                            >
                                {copied ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5" />}
                            </button>
                        </div>
                    </div>

                    <div className="mb-6">
                        <label className="block text-sm font-medium mb-2">
                            Ingresa el código de 6 dígitos de tu app:
                        </label>
                        <input
                            type="text"
                            value={token}
                            onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
                            className="w-full p-3 border border-gray-300 rounded-lg text-center text-2xl tracking-widest font-mono"
                            placeholder="000000"
                            maxLength={6}
                            autoFocus
                        />
                    </div>

                    <button
                        onClick={verifyAndActivate}
                        disabled={token.length !== 6 || loading}
                        className="w-full py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? 'Verificando...' : 'Verificar y Activar'}
                    </button>
                </div>
            )}

            {/* Step 3: Backup Codes */}
            {step === 3 && (
                <div>
                    <div className="flex items-center gap-2 mb-4">
                        <AlertTriangle className="w-6 h-6 text-yellow-500" />
                        <h3 className="text-xl font-bold">Códigos de Respaldo</h3>
                    </div>

                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                        <p className="text-sm text-yellow-800">
                            <strong>¡Importante!</strong> Guarda estos códigos en un lugar seguro. Puedes usarlos para acceder a tu cuenta si pierdes tu dispositivo de autenticación.
                        </p>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg mb-4">
                        <div className="grid grid-cols-2 gap-2">
                            {backupCodes.map((code, idx) => (
                                <code key={idx} className="font-mono text-sm bg-white p-2 rounded border">
                                    {code}
                                </code>
                            ))}
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <button
                            onClick={copyBackupCodes}
                            className="flex-1 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center justify-center gap-2"
                        >
                            <Copy className="w-4 h-4" />
                            Copiar Códigos
                        </button>
                        <button
                            onClick={onComplete}
                            className="flex-1 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition"
                        >
                            Finalizar
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
