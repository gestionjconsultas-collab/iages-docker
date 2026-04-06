// frontend/src/components/dehu/DehuNotificationsList.jsx
import React, { useState } from 'react';
import { Search, RefreshCw, Inbox, CheckCircle2 } from 'lucide-react';
import { useDehuNotifications } from '../../hooks/useDehuNotifications';
import DehuNotificationCard from './DehuNotificationCard';

const DehuNotificationsList = ({ onSelectNotification, isConnected }) => {
    const [activeTab, setActiveTab] = useState('pending');
    const [searchTerm, setSearchTerm] = useState('');

    const {
        notifications,
        total,
        isLoading,
        refetch
    } = useDehuNotifications(activeTab, { enabled: isConnected });

    const filteredNotifications = notifications.filter(n => {
        if (!searchTerm) return true;
        const search = searchTerm.toLowerCase();
        return (
            n.identifier?.toLowerCase().includes(search) ||
            n.concept?.toLowerCase().includes(search) ||
            n.emitterEntity?.toLowerCase().includes(search)
        );
    });

    if (!isConnected) {
        return (
            <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
                <div className="max-w-md mx-auto">
                    <div className="bg-gray-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                        <Inbox className="w-8 h-8 text-gray-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        No hay conexión activa
                    </h3>
                    <p className="text-gray-600">
                        Conecta con tu certificado digital para ver tus notificaciones de DEHú
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white border border-gray-200 rounded-lg">
            {/* Tabs */}
            <div className="border-b border-gray-200">
                <div className="flex items-center justify-between p-4">
                    <div className="flex space-x-1">
                        <button
                            onClick={() => setActiveTab('pending')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'pending'
                                    ? 'bg-blue-100 text-blue-700'
                                    : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            <div className="flex items-center space-x-2">
                                <Inbox className="w-4 h-4" />
                                <span>Pendientes</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setActiveTab('realized')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${activeTab === 'realized'
                                    ? 'bg-green-100 text-green-700'
                                    : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            <div className="flex items-center space-x-2">
                                <CheckCircle2 className="w-4 h-4" />
                                <span>Realizadas</span>
                            </div>
                        </button>
                    </div>

                    <button
                        onClick={() => refetch()}
                        disabled={isLoading}
                        className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                        title="Actualizar"
                    >
                        <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                {/* Search */}
                <div className="px-4 pb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Buscar por identificador, concepto u organismo..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>
                </div>
            </div>

            {/* Lista */}
            <div className="p-4">
                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                ) : filteredNotifications.length === 0 ? (
                    <div className="text-center py-12">
                        <Inbox className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                        <p className="text-gray-600">
                            {searchTerm ? 'No se encontraron resultados' : 'No hay notificaciones'}
                        </p>
                    </div>
                ) : (
                    <>
                        <div className="mb-4 text-sm text-gray-600">
                            Mostrando {filteredNotifications.length} de {total} notificaciones
                        </div>
                        <div className="space-y-3">
                            {filteredNotifications.map((notification) => (
                                <DehuNotificationCard
                                    key={notification.sentReference}
                                    notification={notification}
                                    type={activeTab}
                                    onClick={() => onSelectNotification(notification, activeTab)}
                                />
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default DehuNotificationsList;
