// frontend/src/components/Toast.jsx
import React, { useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';

export default function Toast({ message, type = 'info', onClose, duration = 4000 }) {
    useEffect(() => {
        if (duration > 0) {
            const timer = setTimeout(onClose, duration);
            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const icons = {
        success: <CheckCircle className="w-6 h-6" />,
        error: <XCircle className="w-6 h-6" />,
        warning: <AlertCircle className="w-6 h-6" />,
        info: <Info className="w-6 h-6" />
    };

    const styles = {
        success: 'bg-gradient-to-r from-green-500 to-emerald-600 text-white',
        error: 'bg-gradient-to-r from-red-500 to-rose-600 text-white',
        warning: 'bg-gradient-to-r from-amber-500 to-orange-600 text-white',
        info: 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
    };

    return (
        <div className={`
      ${styles[type]}
      min-w-[320px] max-w-md rounded-xl shadow-2xl p-4
      flex items-center gap-3
      animate-slide-in
      backdrop-blur-sm
      border border-white/20
    `}>
            <div className="shrink-0">
                {icons[type]}
            </div>
            <p className="flex-1 font-medium text-sm">
                {message}
            </p>
            <button
                onClick={onClose}
                className="shrink-0 p-1 hover:bg-white/20 rounded-lg transition-colors"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
}

// Hook personalizado para usar Toast
export function useToast() {
    const [toasts, setToasts] = React.useState([]);

    const showToast = React.useCallback((message, type = 'info', duration = 4000) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message, type, duration }]);
    }, []);

    const removeToast = React.useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const ToastContainer = React.useCallback(() => (
        <div className="fixed top-4 right-4 z-9999 space-y-3">
            {toasts.map(toast => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    duration={toast.duration}
                    onClose={() => removeToast(toast.id)}
                />
            ))}
        </div>
    ), [toasts, removeToast]);

    return { showToast, ToastContainer };
}
