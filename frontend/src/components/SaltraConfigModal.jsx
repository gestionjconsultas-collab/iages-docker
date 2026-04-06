// frontend/src/components/SaltraConfigModal.jsx
import React, { useState } from 'react';
import { X, Key, Lock, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function SaltraConfigModal({ isOpen, onClose, onSuccess, gestoriaId, gestoriaNombre }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [certSecret, setCertSecret] = useState('');
    const [enabled, setEnabled] = useState(true);
    const [saving, setSaving] = useState(false);
    const [validating, setValidating] = useState(false);
    const [validated, setValidated] = useState(false);

    const handleTestLogin = async () => {
        if (!email.trim() || !password.trim()) {
            toast.error('Ingresa email y password primero');
            return;
        }

        setValidating(true);
        setValidated(false);

        try {
            const res = await axios.post('/api/admin/saltra/validate-credentials', {
                email: email.trim(),
                password: password.trim()
            }, { withCredentials: true });

            if (res.data.success) {
                setValidated(true);
                toast.success('✅ Credenciales validadas correctamente');
            }
        } catch (err) {
            setValidated(false);
            if (err.response?.status === 400) {
                const errorMsg = err.response?.data?.error || 'Credenciales inválidas';
                toast.error(`❌ ${errorMsg}`);
            } else {
                toast.error('Error al conectar con SALTRA');
            }
        } finally {
            setValidating(false);
        }
    };

    const handleSave = async () => {
        if (!email.trim() || !password.trim()) {
            toast.error('Email y Password son requeridos');
            return;
        }

        setSaving(true);

        try {
            // Si se proporciona gestoriaId, usar endpoint específico para super-admin
            const url = gestoriaId
                ? `/api/admin/gestoria/${gestoriaId}/saltra-config`
                : '/api/admin/gestoria/saltra-config';

            const payload = {
                email: email.trim(),
                password: password.trim(),
                enabled
            };

            // Incluir cert_secret solo si se proporcionó
            if (certSecret.trim()) {
                payload.cert_secret = certSecret.trim();
            }

            const res = await axios.put(url, payload, { withCredentials: true });

            if (res.data.success) {
                toast.success('✅ Configuración SALTRA guardada correctamente');
                onSuccess?.();
                onClose();
            }
        } catch (err) {
            if (err.response?.status === 400) {
                toast.error('❌ ' + (err.response.data.error || 'Credenciales inválidas'));
            } else {
                toast.error(err.response?.data?.error || 'Error al guardar configuración');
            }
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-primary-light rounded-lg">
                            <Key className="w-6 h-6 text-primary" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900">Configurar SALTRA</h2>
                            <p className="text-sm text-gray-600 mt-1">
                                {gestoriaNombre
                                    ? `Credenciales para: ${gestoriaNombre}`
                                    : 'Credenciales de acceso a la API de SALTRA'
                                }
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6 overflow-y-auto flex-1">
                    {/* Warning */}
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <div className="flex gap-3">
                            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-amber-800">
                                <p className="font-medium mb-1">Información Importante</p>
                                <p>Las credenciales se guardarán de forma segura en la base de datos. Solo los super-administradores pueden ver o modificar esta configuración.</p>
                            </div>
                        </div>
                    </div>

                    {/* Email SALTRA */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Email SALTRA *
                        </label>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="tu-email-saltra@ejemplo.com"
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            Email específico de tu cuenta SALTRA (diferente al de IAGES)
                        </p>
                    </div>

                    {/* Password SALTRA */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Password SALTRA *
                        </label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => {
                                    setPassword(e.target.value);
                                    setValidated(false);
                                    setCertSecret('');
                                }}
                                placeholder="Ingresa tu password de SALTRA"
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            Password de tu cuenta SALTRA (diferente al de IAGES)
                        </p>
                    </div>

                    {/* Botón Validar Credenciales */}
                    <div>
                        <button
                            type="button"
                            onClick={handleTestLogin}
                            disabled={validating || !email.trim() || !password.trim()}
                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            {validating ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Validando credenciales...
                                </>
                            ) : validated ? (
                                <>
                                    <CheckCircle className="w-5 h-5" />
                                    Credenciales validadas ✓
                                </>
                            ) : (
                                <>
                                    <Key className="w-5 h-5" />
                                    Validar Credenciales
                                </>
                            )}
                        </button>
                        <p className="text-xs text-gray-500 mt-2 text-center">
                            Valida tus credenciales antes de guardar
                        </p>
                    </div>

                    {/* Cert-Secret SALTRA (Opcional) */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Cert-Secret SALTRA (Opcional)
                        </label>
                        <div className="relative">
                            <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                value={certSecret}
                                onChange={(e) => setCertSecret(e.target.value)}
                                placeholder="Cert-secret compartido (opcional)"
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent"
                            />
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                            <strong>Opcional:</strong> Solo si tu gestoría tiene un certificado DEHU compartido para todas las empresas.
                            Si cada empresa tiene su propio certificado, déjalo vacío y configúralo individualmente por empresa.
                        </p>
                    </div>

                    {/* Info sobre cert-secret */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex gap-3">
                            <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-blue-800">
                                <p className="font-medium mb-1">Dos modos de configuración</p>
                                <ul className="list-disc list-inside space-y-1">
                                    <li><strong>Cert-Secret compartido:</strong> Ingrésalo aquí si tu gestoría tiene un solo certificado para todas las empresas</li>
                                    <li><strong>Cert-Secret individual:</strong> Déjalo vacío aquí y configúralo por empresa desde la vista de empresas</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    {/* Enabled Toggle */}
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div>
                            <p className="font-medium text-gray-900">Habilitar SALTRA</p>
                            <p className="text-sm text-gray-600">Activar sincronización de notificaciones</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                            <input
                                type="checkbox"
                                checked={enabled}
                                onChange={(e) => setEnabled(e.target.checked)}
                                className="sr-only peer"
                            />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                    </div>

                    {/* Info */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex gap-3">
                            <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                            <div className="text-sm text-blue-800">
                                <p className="font-medium mb-1">¿Dónde obtener las credenciales?</p>
                                <p className="mb-2">
                                    Estas son las credenciales de tu cuenta SALTRA (api.saltra.es),
                                    <strong> NO las de IAGES</strong>.
                                </p>
                                <p>
                                    Si no tienes cuenta SALTRA, contacta con el soporte de SALTRA
                                    para obtener tus credenciales. Necesitarás proporcionar el NIF de tu gestoría.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
                    <button
                        onClick={onClose}
                        disabled={saving}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || !email.trim() || !password.trim()}
                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        {saving ? 'Guardando...' : 'Guardar Configuración'}
                    </button>
                </div>
            </div>
        </div>
    );
}
