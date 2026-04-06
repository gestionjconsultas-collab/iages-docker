import React, { useState } from 'react';
import { Shield, Key, Copy, Check, AlertTriangle, RefreshCw, XCircle } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function BackupCodesModal({ codes, onClose }) {
    const [copied, setCopied] = useState(false);

    const copyAllCodes = () => {
        const text = codes.join('\n');
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
        toast.success('Códigos copiados al portapapeles');
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Key className="w-6 h-6 text-orange-500" />
                        <h3 className="text-xl font-bold text-gray-800">Códigos de Respaldo</h3>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <XCircle className="w-6 h-6" />
                    </button>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                    <div className="flex items-start gap-2">
                        <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-yellow-800">
                            <strong>¡Importante!</strong> Guarda estos códigos en un lugar seguro. Cada código solo se puede usar una vez.
                        </p>
                    </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4 mb-4">
                    <div className="grid grid-cols-2 gap-2">
                        {codes.map((code, idx) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded p-2 text-center">
                                <code className="font-mono text-sm font-semibold text-gray-800">{code}</code>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={copyAllCodes}
                        className="flex-1 py-2 px-4 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition flex items-center justify-center gap-2"
                    >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        {copied ? 'Copiado' : 'Copiar Todos'}
                    </button>
                    <button
                        onClick={onClose}
                        className="flex-1 py-2 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                    >
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    );
}
