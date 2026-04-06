import React, { useEffect } from 'react';
import { X, Zap } from 'lucide-react';
import useEscapeKey from '../hooks/useEscapeKey';

const ShortcutsHelp = ({ onClose }) => {
    useEscapeKey(onClose);
  // Escuchar Esc para cerrar
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const shortcuts = [
    {
      category: '🧭 Navegación',
      items: [
        { keys: ['Ctrl', 'I'], description: 'Ir a Importar documentos' },
        { keys: ['Ctrl', 'B'], description: 'Ir a Empresas/Dashboard' },
        { keys: ['Ctrl', 'M'], description: 'Ir a Mesa de Trabajo' },
        { keys: ['Ctrl', 'K'], description: 'Focus en búsqueda' },
      ]
    },
    {
      category: '⚡ Acciones',
      items: [
        { keys: ['Esc'], description: 'Cerrar modal/menú abierto' },
        { keys: ['/'], description: 'Focus en búsqueda rápida' },
        { keys: ['?'], description: 'Mostrar esta ayuda' },
      ]
    }
  ];

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose} // Click fuera cierra el modal
    >
      <div 
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()} // Evitar cerrar al click dentro
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-linear-to-br from-orange-500 to-red-500 rounded-lg">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Atajos de Teclado
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Navega más rápido con estos shortcuts
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-8 max-h-[60vh] overflow-y-auto">
          {shortcuts.map((section, idx) => (
            <div key={idx}>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
                {section.category}
              </h3>
              <div className="space-y-3">
                {section.items.map((item, itemIdx) => (
                  <div
                    key={itemIdx}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  >
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {item.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {item.keys.map((key, keyIdx) => (
                        <React.Fragment key={keyIdx}>
                          <kbd className="px-3 py-1.5 text-xs font-semibold text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm">
                            {key}
                          </kbd>
                          {keyIdx < item.keys.length - 1 && (
                            <span className="text-gray-400 mx-0.5">+</span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-b-2xl border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-center text-gray-500 dark:text-gray-400">
            💡 Tip: Los shortcuts se desactivan automáticamente cuando escribes en campos de texto
          </p>
        </div>
      </div>
    </div>
  );
};

export default ShortcutsHelp;