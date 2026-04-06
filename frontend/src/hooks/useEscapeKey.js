import { useEffect } from 'react';

/**
 * Hook para cerrar componentes al presionar Escape
 * @param {Function} onEscape - Callback cuando se presiona Escape
 * @param {boolean} isActive - Si el hook debe estar activo (default: true)
 */
export const useEscapeKey = (onEscape, isActive = true) => {
  useEffect(() => {
    if (!isActive) return;

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        onEscape();
      }
    };

    // Usar capture phase para ejecutar antes que otros listeners
    document.addEventListener('keydown', handleEscape, true);
    
    return () => {
      document.removeEventListener('keydown', handleEscape, true);
    };
  }, [onEscape, isActive]);
};

export default useEscapeKey;