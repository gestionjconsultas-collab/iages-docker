{
    activeTab === 'security' && (
        <div className="p-6">
            {show2FASetup ? (
                <TwoFactorSetup
                    onComplete={() => {
                        setShow2FASetup(false);
                        toast.success('2FA configurado exitosamente');
                        setTimeout(() => window.location.reload(), 1500);
                    }}
                    onCancel={() => setShow2FASetup(false)}
                />
            ) : (
                <div className="space-y-6">
                    <div>
                        <h3 className="text-lg font-bold mb-2">Autenticación de Dos Factores (2FA)</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Añade una capa extra de seguridad a tu cuenta requiriendo un código de verificación además de tu contraseña.
                        </p>
                    </div>

                    {user?.two_factor_enabled ? (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                            <div className="flex items-start gap-3">
                                <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Settings className="w-5 h-5 text-green-600" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-green-900 mb-1">2FA Activado</p>
                                    <p className="text-sm text-green-700 mb-3">
                                        Tu cuenta está protegida con autenticación de dos factores.
                                    </p>
                                    <p className="text-xs text-green-600 mb-4">
                                        Códigos de respaldo disponibles: {user?.backup_codes_count || 0}
                                    </p>
                                    <button
                                        onClick={async () => {
                                            const password = prompt('Ingresa tu contraseña para desactivar 2FA:');
                                            if (!password) return;

                                            try {
                                                await axios.post('/api/auth/2fa/disable', { password }, { withCredentials: true });
                                                toast.success('2FA desactivado');
                                                setTimeout(() => window.location.reload(), 1000);
                                            } catch (error) {
                                                toast.error(error.response?.data?.error || 'Error al desactivar 2FA');
                                            }
                                        }}
                                        className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition text-sm"
                                    >
                                        Desactivar 2FA
                                    </button>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                            <div className="flex items-start gap-3">
                                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Settings className="w-5 h-5 text-orange-600" />
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-orange-900 mb-1">2FA Desactivado</p>
                                    <p className="text-sm text-orange-700 mb-4">
                                        Recomendamos activar 2FA para mayor seguridad.
                                    </p>
                                    <button
                                        onClick={() => setShow2FASetup(true)}
                                        className="px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition text-sm"
                                    >
                                        Activar 2FA
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}
