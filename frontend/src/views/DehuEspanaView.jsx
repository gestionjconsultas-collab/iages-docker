// frontend/src/views/DehuEspanaView.jsx
import React from 'react';
import { Flag } from 'lucide-react';
import DehuSyncPanel from '../components/dehu/DehuSyncPanel';

const DehuEspanaView = () => {
    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center space-x-4 mb-2">
                        <img
                            src="/conecta-logo.png"
                            alt="Conecta Logo"
                            className="h-16 w-auto"
                            onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'flex';
                            }}
                        />
                        <div className="hidden bg-gradient-to-r from-red-600 to-orange-500 p-3 rounded-lg items-center justify-center">
                            <Flag className="w-8 h-8 text-white" />
                        </div>
                        <div>
                            <h1 className="text-4xl font-black tracking-tight text-gray-900">CONECTA</h1>
                            <p className="text-gray-600 font-medium">Sincronización Inteligente de Notificaciones</p>
                        </div>
                    </div>
                </div>

                {/* Sincronización Escritorio */}
                <DehuSyncPanel />
            </div>
        </div>
    );
};

export default DehuEspanaView;
