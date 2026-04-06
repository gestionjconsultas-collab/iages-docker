// frontend/src/components/dehu/DehuNotificationCard.jsx
import React from 'react';
import { Calendar, Building2, FileText, Clock, AlertTriangle } from 'lucide-react';

const DehuNotificationCard = ({ notification, onClick, type = 'pending' }) => {
    const {
        identifier,
        emitterEntity,
        concept,
        availabilityDate,
        expirationDate,
        daysRemaining,
        state
    } = notification;

    // Determinar urgencia por días restantes
    const getUrgencyColor = () => {
        if (type === 'realized') return 'bg-green-50 border-green-200';
        if (daysRemaining === null || daysRemaining === undefined) return 'bg-gray-50 border-gray-200';
        if (daysRemaining <= 3) return 'bg-red-50 border-red-300';
        if (daysRemaining <= 7) return 'bg-orange-50 border-orange-200';
        return 'bg-blue-50 border-blue-200';
    };

    const getUrgencyBadge = () => {
        if (type === 'realized') {
            return (
                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                    ✓ Realizada
                </span>
            );
        }
        if (daysRemaining === null || daysRemaining === undefined) return null;
        if (daysRemaining <= 0) {
            return (
                <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center space-x-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>EXPIRADA</span>
                </span>
            );
        }
        if (daysRemaining <= 3) {
            return (
                <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center space-x-1">
                    <AlertTriangle className="w-3 h-3" />
                    <span>{daysRemaining}d restantes</span>
                </span>
            );
        }
        if (daysRemaining <= 7) {
            return (
                <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full">
                    {daysRemaining}d restantes
                </span>
            );
        }
        return (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                {daysRemaining}d restantes
            </span>
        );
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        try {
            return new Date(dateStr).toLocaleDateString('es-ES');
        } catch {
            return dateStr.substring(0, 10);
        }
    };

    return (
        <div
            onClick={onClick}
            className={`border rounded-lg p-4 cursor-pointer hover:shadow-md transition-all ${getUrgencyColor()}`}
        >
            <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                    <h3 className="font-semibold text-gray-900 mb-1">{identifier}</h3>
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                        <Building2 className="w-4 h-4" />
                        <span>{emitterEntity}</span>
                    </div>
                </div>
                {getUrgencyBadge()}
            </div>

            <div className="space-y-2">
                <div className="flex items-start space-x-2 text-sm text-gray-700">
                    <FileText className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <p className="line-clamp-2">{concept}</p>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-200">
                    <div className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3" />
                        <span>Disponible: {formatDate(availabilityDate)}</span>
                    </div>
                    {expirationDate && (
                        <div className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>Expira: {formatDate(expirationDate)}</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DehuNotificationCard;
