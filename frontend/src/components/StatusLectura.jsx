import React from 'react';
import axios from 'axios';
import { FaEnvelopeOpen, FaEnvelope, FaEye, FaEyeSlash } from 'react-icons/fa';
import toast from 'react-hot-toast';

/**
 * Componente de Status de Lectura
 * Muestra si un documento ha sido leído y permite marcarlo
 */
const StatusLectura = ({ documento, onActualizar }) => {
  const marcarComoLeido = async () => {
    try {
      await axios.post(
        `/api/documentos/${documento.id}/marcar-leido`,
        {},
        { withCredentials: true }
      );

      if (onActualizar) {
        onActualizar();
      }
    } catch (error) {
      console.error('Error al marcar como leído:', error);
      toast.error('Error al marcar documento como leído');
    }
  };

  const marcarComoNoLeido = async () => {
    try {
      await axios.post(
        `/api/documentos/${documento.id}/marcar-no-leido`,
        {},
        { withCredentials: true }
      );

      if (onActualizar) {
        onActualizar();
      }
    } catch (error) {
      console.error('Error al marcar como no leído:', error);
      toast.error('Error al marcar documento como no leído');
    }
  };

  if (documento.leido) {
    return (
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <FaEnvelopeOpen className="mr-1" />
          Leído
        </span>

        {documento.leido_por && (
          <span className="text-xs text-gray-500">
            por {documento.leido_por}
          </span>
        )}

        {documento.fecha_lectura && (
          <span className="text-xs text-gray-500">
            {new Date(documento.fecha_lectura).toLocaleDateString()}
          </span>
        )}

        <button
          onClick={marcarComoNoLeido}
          className="text-gray-400 hover:text-gray-600 text-xs ml-2"
          title="Marcar como no leído"
        >
          <FaEyeSlash />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        <FaEnvelope className="mr-1" />
        No leído
      </span>

      <button
        onClick={marcarComoLeido}
        className="text-blue-600 hover:text-blue-800 text-xs flex items-center gap-1"
        title="Marcar como leído"
      >
        <FaEye />
        Marcar leído
      </button>
    </div>
  );
};

export default StatusLectura;

/**
 * USO EN OTROS COMPONENTES:
 * 
 * import StatusLectura from './StatusLectura';
 * 
 * // En tu tabla de documentos:
 * <td className="px-6 py-4">
 *   <StatusLectura 
 *     documento={doc} 
 *     onActualizar={cargarDocumentos} 
 *   />
 * </td>
 */