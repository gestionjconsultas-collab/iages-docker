import { useEffect } from 'react';

/**
 * Hook para manejar atajos de teclado globales
 */
export const useHotkeys = (shortcuts) => {
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Ignorar si el usuario está escribiendo en un input/textarea
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement.tagName
      );
      
      // Permitir Escape siempre, incluso en inputs
      if (event.key === 'Escape' && shortcuts['escape']) {
        event.preventDefault();
        shortcuts['escape'](event);
        return;
      }

      // Si está escribiendo, ignorar otros shortcuts
      if (isTyping) {
        return;
      }

      // Manejar el '?' especialmente (Shift + /)
      if (event.key === '?' && shortcuts['?']) {
        event.preventDefault();
        shortcuts['?'](event);
        return;
      }

      // Construir la combinación de teclas presionada
      const parts = [];
      if (event.ctrlKey) parts.push('ctrl');
      if (event.altKey) parts.push('alt');
      if (event.shiftKey && event.key !== 'Shift' && event.key !== '?') parts.push('shift');
      
      // Añadir la tecla principal (normalizada)
      const key = event.key.toLowerCase();
      if (!['control', 'alt', 'shift', 'meta'].includes(key)) {
        parts.push(key);
      }

      const combo = parts.join('+');

      // Ejecutar el handler si existe
      if (shortcuts[combo]) {
        event.preventDefault();
        shortcuts[combo](event);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
};

export default useHotkeys;