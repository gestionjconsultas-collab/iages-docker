// frontend/src/components/AgregarAGrupoModal.jsx
import React, { useState } from 'react';
import { X, Plus, FolderPlus } from 'lucide-react';
import { useGrupos, useAgregarDocumentoAGrupo, useGruposDeDocumento } from '../hooks/useGruposDocumentos';
import CrearGrupoModal from './CrearGrupoModal';

export default function AgregarAGrupoModal({ documentoId, empresaId, onClose }) {
  const [mostrarCrear, setMostrarCrear] = useState(false);

  const { data: todosGrupos } = useGrupos(empresaId);
  const { data: gruposActuales } = useGruposDeDocumento(documentoId);
  const agregarDocumento = useAgregarDocumentoAGrupo();

  // Filtrar grupos donde el documento NO está
  const gruposDisponibles = todosGrupos?.filter(
    (grupo) => !gruposActuales?.some((g) => g.id === grupo.id)
  ) || [];

  const handleAgregar = async (grupoId) => {
    await agregarDocumento.mutateAsync({ grupoId, documentoId });
  };

  const colores = {
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    purple: 'bg-purple-100 text-purple-800',
    pink: 'bg-pink-100 text-pink-800',
    orange: 'bg-primary-light text-orange-800',
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-9999 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Agregar a Grupo
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X size={24} />
          </button>
        </div>

        {/* Contenido */}
        <div className="p-6">
          {gruposDisponibles.length === 0 ? (
            <div className="text-center py-8">
              <FolderPlus size={48} className="mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                No hay grupos disponibles o el documento ya está en todos los grupos
              </p>
              <button
                onClick={() => setMostrarCrear(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Crear Nuevo Grupo
              </button>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {gruposDisponibles.map((grupo) => (
                <button
                  key={grupo.id}
                  onClick={() => handleAgregar(grupo.id)}
                  disabled={agregarDocumento.isPending}
                  className="w-full flex items-center justify-between p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${colores[grupo.color] || colores.blue}`}>
                      {grupo.color}
                    </span>
                    <div className="text-left">
                      <p className="font-medium text-gray-900 dark:text-white">
                        {grupo.nombre}
                      </p>
                      {grupo.descripcion && (
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {grupo.descripcion}
                        </p>
                      )}
                    </div>
                  </div>
                  <Plus size={20} className="text-gray-400" />
                </button>
              ))}
            </div>
          )}

          {/* Grupos actuales */}
          {gruposActuales && gruposActuales.length > 0 && (
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Ya está en estos grupos:
              </p>
              <div className="flex flex-wrap gap-2">
                {gruposActuales.map((grupo) => (
                  <span
                    key={grupo.id}
                    className={`px-2 py-1 rounded text-xs font-medium ${colores[grupo.color] || colores.blue}`}
                  >
                    {grupo.nombre}
                  </span>
                ))}
              </div>
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

      {/* Modal de Crear Grupo */}
      {mostrarCrear && (
        <CrearGrupoModal
          empresaId={empresaId}
          onClose={() => setMostrarCrear(false)}
        />
      )}
    </div>
  );
}