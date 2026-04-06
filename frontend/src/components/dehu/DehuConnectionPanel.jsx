// frontend/src/components/dehu/DehuConnectionPanel.jsx
import React, { useState } from 'react';
import { Upload, Lock, LogOut, CheckCircle, XCircle } from 'lucide-react';
import { useDehuConnection } from '../../hooks/useDehuConnection';

const DehuConnectionPanel = () => {
    const {
        isConnected,
        userInfo,
        connect,
        disconnect,
        isConnecting,
        isDisconnecting
    } = useDehuConnection();

    const [pfxFile, setPfxFile] = useState(null);
    const [passphrase, setPassphrase] = useState('');

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file && file.name.endsWith('.pfx')) {
            setPfxFile(file);
        } else {
            alert('Por favor selecciona un archivo .pfx válido');
        }
    };

    const handleConnect = (e) => {
        e.preventDefault();
        if (!pfxFile || !passphrase) {
            alert('Por favor completa todos los campos');
            return;
        }
        connect({ pfxFile, passphrase });
    };

    const handleDisconnect = () => {
        if (confirm('¿Estás seguro de cerrar la sesión?')) {
            disconnect();
            setPfxFile(null);
            setPassphrase('');
        }
    };

    if (isConnected) {
        return (
            <div className="bg-gradient-to-r from-blue-50 to-red-50 border border-blue-200 rounded-lg p-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className="bg-green-100 p-3 rounded-full">
                            <CheckCircle className="w-6 h-6 text-green-600" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900">Conectado a DEHú</h3>
                            <p className="text-sm text-gray-600">
                                {userInfo?.person?.fullName || 'Usuario autenticado'}
                            </p>
                            {userInfo?.person?.identifier && (
                                <p className="text-xs text-gray-500">
                                    NIF: {userInfo.person.identifier}
                                </p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={handleDisconnect}
                        disabled={isDisconnecting}
                        className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                    >
                        <LogOut className="w-4 h-4" />
                        <span>{isDisconnecting ? 'Cerrando...' : 'Cerrar Sesión'}</span>
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-center space-x-3 mb-6">
                <div className="bg-blue-100 p-3 rounded-full">
                    <Lock className="w-6 h-6 text-blue-600" />
                </div>
                <div>
                    <h3 className="font-semibold text-gray-900">Conectar a DEHú</h3>
                    <p className="text-sm text-gray-600">
                        Autenticación con certificado digital
                    </p>
                </div>
            </div>

            <form onSubmit={handleConnect} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Certificado Digital (.pfx)
                    </label>
                    <div className="relative">
                        <input
                            type="file"
                            accept=".pfx"
                            onChange={handleFileChange}
                            className="hidden"
                            id="pfx-upload"
                            disabled={isConnecting}
                        />
                        <label
                            htmlFor="pfx-upload"
                            className="flex items-center justify-center space-x-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-500 transition-colors"
                        >
                            <Upload className="w-5 h-5 text-gray-400" />
                            <span className="text-sm text-gray-600">
                                {pfxFile ? pfxFile.name : 'Seleccionar archivo .pfx'}
                            </span>
                        </label>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Contraseña del Certificado
                    </label>
                    <input
                        type="password"
                        value={passphrase}
                        onChange={(e) => setPassphrase(e.target.value)}
                        placeholder="Ingresa la contraseña"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={isConnecting}
                    />
                </div>

                <button
                    type="submit"
                    disabled={!pfxFile || !passphrase || isConnecting}
                    className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                    {isConnecting ? (
                        <>
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                            <span>Conectando...</span>
                        </>
                    ) : (
                        <>
                            <Lock className="w-5 h-5" />
                            <span>Conectar a DEHú</span>
                        </>
                    )}
                </button>
            </form>

            <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-800">
                    <strong>Nota:</strong> Tu certificado se procesa de forma segura y no se almacena en el servidor.
                </p>
            </div>
        </div>
    );
};

export default DehuConnectionPanel;
