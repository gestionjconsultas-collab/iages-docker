// frontend/src/components/DetallesGrupoModal.jsx
import React, { useState } from 'react';
import toast from 'react-hot-toast';
import axios from '../utils/axiosConfig';
import { X, Trash2, Mail, Plus } from 'lucide-react';
import { useGrupo, useQuitarDocumentoDeGrupo } from '../hooks/useGruposDocumentos';
import AgregarDocumentosAGrupoModal from './AgregarDocumentosAGrupoModal';
import EnviarEmailGrupoModal from './EnviarEmailGrupoModal';
import MobilePDFViewer from './MobilePDFViewer';


export default function DetallesGrupoModal({ grupoId, onClose }) {
  const { data: grupo, isLoading } = useGrupo(grupoId);
  const quitarDocumento = useQuitarDocumentoDeGrupo();
  const [modalEmailAbierto, setModalEmailAbierto] = useState(false);
  const [modalAgregarDocsAbierto, setModalAgregarDocsAbierto] = useState(false);
  const [documentoViendoPDF, setDocumentoViendoPDF] = useState(null);

  const handleQuitarDocumento = async (documentoId) => {
    if (window.confirm('¿Quitar este documento del grupo?')) {
      await quitarDocumento.mutateAsync({ grupoId, documentoId });
    }
  };

  const handleEliminarFisico = async (doc) => {
    if (!window.confirm(`¿Estás seguro de que quieres eliminar FÍSICAMENTE el archivo "${doc.nombre_archivo}"? Esta acción no se puede deshacer.`)) return;

    try {
      const response = await axios.delete(`/api/documentos/${doc.id}`);
      if (response.data.success) {
        toast.success('Documento eliminado físicamente');
        // El documento se quita del grupo automáticamente al eliminarse de la BD
        // Invalida la query del grupo para refrescar
        onClose(); // Cerramos y que refresque el padre o forzamos refresh
      }
    } catch (error) {
      console.error('Error eliminando físicamente:', error);
      toast.error('Error al intentar eliminar el archivo');
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">
              {grupo?.nombre}
            </h2>
            {grupo?.descripcion && (
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                {grupo.descripcion}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X size={24} />
          </button>
        </div>

        {/* Acciones */}
        <div className="flex gap-2 p-4 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setModalEmailAbierto(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Mail size={18} />
            Enviar por Email
          </button>
          <button
            onClick={() => setModalAgregarDocsAbierto(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus size={18} />
            Agregar Documentos
          </button>
        </div>

        {/* Lista de Documentos */}
        <div className="flex-1 overflow-y-auto p-6">
          {!grupo?.documentos || grupo.documentos.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              <p>No hay documentos en este grupo</p>
              <button
                onClick={() => setModalAgregarDocsAbierto(true)}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Agregar Primer Documento
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {grupo.documentos.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                >
                  <div className="flex-1 cursor-pointer" onClick={() => setDocumentoViendoPDF(doc)}>
                    <h4 className="font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                      {doc.nombre_archivo}
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {doc.categoria}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleQuitarDocumento(doc.id)}
                      className="text-gray-400 hover:text-orange-600 p-2"
                      title="Quitar del grupo"
                    >
                      <Trash2 size={18} />
                    </button>
                    <button
                      onClick={() => handleEliminarFisico(doc)}
                      className="text-gray-400 hover:text-red-600 p-2"
                      title="ELIMINAR FÍSICAMENTE DEL SERVIDOR"
                    >
                      <Trash2 size={18} className="fill-current text-opacity-20" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>

      {/* Modal de Email */}
      {modalEmailAbierto && (
        <EnviarEmailGrupoModal
          grupo={grupo}
          onClose={() => setModalEmailAbierto(false)}
        />
      )}

      {/* Modal de Agregar Documentos */}
      {modalAgregarDocsAbierto && (
        <AgregarDocumentosAGrupoModal
          grupoId={grupoId}
          empresaId={grupo?.empresa_id}
          documentosActuales={grupo?.documentos || []}
          onClose={() => setModalAgregarDocsAbierto(false)}
        />
      )}

      {/* Visor de PDF */}
      {documentoViendoPDF && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-10001 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-6xl h-[90vh] flex flex-col">
            {/* Header del visor */}
            <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-bold text-gray-900 dark:text-white truncate">
                {documentoViendoPDF.nombre_archivo}
              </h3>
              <button
                onClick={() => setDocumentoViendoPDF(null)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X size={24} />
              </button>
            </div>
            {/* PDF Viewer */}
            <div className="flex-1 overflow-hidden">
              <MobilePDFViewer documentId={documentoViendoPDF.id} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}