// frontend/src/components/AgregarDocumentosAGrupoModal.jsx
import React, { useState } from 'react';
import { X, Plus, Search, Eye } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { useAgregarDocumentoAGrupo } from '../hooks/useGruposDocumentos';

export default function AgregarDocumentosAGrupoModal({ grupoId, empresaId, documentosActuales, onClose }) {
    const [busqueda, setBusqueda] = useState('');
    const [documentoViendoPDF, setDocumentoViendoPDF] = useState(null);
    const agregarDocumento = useAgregarDocumentoAGrupo();

    // Obtener TODOS los documentos de la empresa
    const { data: todosDocumentos, isLoading } = useQuery({
        queryKey: ['documentos-empresa', empresaId],
        queryFn: async () => {
            const { data } = await axios.get(`/api/empresas/${empresaId}/documentos?categoria=all`);
            return data.documentos || [];
        },
        enabled: !!empresaId
    });

    // Filtrar documentos que NO están en el grupo
    const documentosDisponibles = todosDocumentos?.filter(
        (doc) => !documentosActuales.some((d) => d.id === doc.id)
    ) || [];

    // Aplicar búsqueda
    const documentosFiltrados = documentosDisponibles.filter((doc) =>
        doc.nombre_archivo.toLowerCase().includes(busqueda.toLowerCase())
    );

    const handleAgregar = async (documentoId) => {
        await agregarDocumento.mutateAsync({ grupoId, documentoId });
    };

    return (
        <>
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000] p-4">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] flex flex-col">
                    {/* Header */}
                    <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
                        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                            Agregar Documentos al Grupo
                        </h2>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                        >
                            <X size={24} />
                        </button>
                    </div>

                    {/* Búsqueda */}
                    <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                            <input
                                type="text"
                                value={busqueda}
                                onChange={(e) => setBusqueda(e.target.value)}
                                placeholder="Buscar documentos..."
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                            />
                        </div>
                    </div>

                    {/* Lista de documentos */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {isLoading ? (
                            <div className="text-center py-8 text-gray-500">Cargando documentos...</div>
                        ) : documentosFiltrados.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                                {busqueda ? 'No se encontraron documentos' : 'No hay documentos disponibles para agregar'}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {documentosFiltrados.map((doc) => (
                                    <div
                                        key={doc.id}
                                        className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        <div className="flex-1">
                                            <p className="font-medium text-gray-900 dark:text-white">
                                                {doc.nombre_archivo}
                                            </p>
                                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                                {doc.categoria}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => setDocumentoViendoPDF(doc)}
                                                className="px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center gap-2"
                                                title="Ver PDF"
                                            >
                                                <Eye size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleAgregar(doc.id)}
                                                disabled={agregarDocumento.isPending}
                                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                                            >
                                                <Plus size={18} />
                                                Agregar
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
            </div>

            {/* Visor de PDF */}
            {documentoViendoPDF && (
                <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[10001] p-4">
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
                            <iframe
                                src={`/api/documentos/${documentoViendoPDF.id}/archivo`}
                                className="w-full h-full border-0"
                                title={documentoViendoPDF.nombre_archivo}
                            />
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}