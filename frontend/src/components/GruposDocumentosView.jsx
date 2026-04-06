// frontend/src/components/GruposDocumentosView.jsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useGrupos, useEliminarGrupo } from '../hooks/useGruposDocumentos';
import { FolderOpen, Plus, Trash2, Mail, FileText, Building2, ChevronDown, ChevronRight, Download } from 'lucide-react';
import CrearGrupoModal from './CrearGrupoModal';
import DetallesGrupoModal from './DetallesGrupoModal';
import axios from 'axios';

export default function GruposDocumentosView() {
  const { empresaId: empresaIdParam } = useParams();
  const empresaId = empresaIdParam ? parseInt(empresaIdParam) : null;
  const [modalCrearAbierto, setModalCrearAbierto] = useState(false);
  const [grupoSeleccionado, setGrupoSeleccionado] = useState(null);
  const [empresas, setEmpresas] = useState([]);
  const [empresasExpanded, setEmpresasExpanded] = useState({});
  const [gruposPorEmpresa, setGruposPorEmpresa] = useState({});
  const [loading, setLoading] = useState(true);

  const { data: grupos, isLoading } = useGrupos(empresaId);
  const eliminarGrupo = useEliminarGrupo();

  const colores = {
    blue: 'bg-blue-100 text-blue-800 border-blue-300',
    green: 'bg-green-100 text-green-800 border-green-300',
    red: 'bg-red-100 text-red-800 border-red-300',
    yellow: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    purple: 'bg-purple-100 text-purple-800 border-purple-300',
    pink: 'bg-pink-100 text-pink-800 border-pink-300',
    orange: 'bg-primary-light text-orange-800 border-orange-300',
  };

  // Cargar empresas y agrupar grupos por empresa
  useEffect(() => {
    const cargarDatos = async () => {
      try {
        // Cargar empresas
        const resEmpresas = await axios.get('/api/empresas', { withCredentials: true });
        if (resEmpresas.data.success) {
          setEmpresas(resEmpresas.data.empresas);
        }

        // Cargar todos los grupos
        const resGrupos = await axios.get('/api/grupos-documentos', { withCredentials: true });
        if (resGrupos.data.success) {
          // Agrupar por empresa_id
          const agrupados = {};
          resGrupos.data.grupos.forEach(grupo => {
            if (!agrupados[grupo.empresa_id]) {
              agrupados[grupo.empresa_id] = [];
            }
            agrupados[grupo.empresa_id].push(grupo);
          });
          setGruposPorEmpresa(agrupados);
        }
      } catch (error) {
        console.error('Error cargando datos:', error);
      } finally {
        setLoading(false);
      }
    };

    cargarDatos();
  }, []);

  const toggleEmpresa = (empresaId) => {
    setEmpresasExpanded(prev => ({
      ...prev,
      [empresaId]: !prev[empresaId]
    }));
  };

  const handleEliminar = async (grupoId) => {
    if (window.confirm('¿Eliminar este grupo? Los documentos no se eliminarán.')) {
      await eliminarGrupo.mutateAsync(grupoId);
      // Recargar datos
      window.location.reload();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const totalGrupos = Object.values(gruposPorEmpresa).reduce((acc, grupos) => acc + grupos.length, 0);

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-black">
            Grupos de Documentos
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Organiza y envía múltiples documentos juntos - {totalGrupos} grupo{totalGrupos !== 1 ? 's' : ''} en total
          </p>
        </div>
        <button
          onClick={() => setModalCrearAbierto(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          Crear Grupo
        </button>
      </div>

      {/* Lista de Empresas con Grupos */}
      {totalGrupos === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <FolderOpen size={48} className="mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No hay grupos creados
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            Crea tu primer grupo para organizar documentos relacionados
          </p>
          <button
            onClick={() => setModalCrearAbierto(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Crear Primer Grupo
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {empresas.map((empresa) => {
            const gruposEmpresa = gruposPorEmpresa[empresa.id] || [];
            if (gruposEmpresa.length === 0) return null;

            const isExpanded = empresasExpanded[empresa.id];

            return (
              <div key={empresa.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
                {/* Header de Empresa */}
                <button
                  onClick={() => toggleEmpresa(empresa.id)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Building2 className="w-6 h-6 text-primary" />
                    <div className="text-left">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {empresa.nombre}
                      </h3>
                      <p className="text-sm text-gray-500">
                        {gruposEmpresa.length} grupo{gruposEmpresa.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  )}
                </button>

                {/* Grupos de la Empresa */}
                {isExpanded && (
                  <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {gruposEmpresa.map((grupo) => (
                        <div
                          key={grupo.id}
                          className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow p-4 border-l-4"
                          style={{ borderLeftColor: `var(--color-${grupo.color}-500)` }}
                        >
                          {/* Header del grupo */}
                          <div className="flex justify-between items-start mb-3">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <span
                                  className={`px-2 py-1 rounded text-xs font-medium border ${colores[grupo.color] || colores.blue}`}
                                >
                                  {grupo.color}
                                </span>
                              </div>
                              <h4 className="text-base font-semibold text-gray-900 dark:text-white">
                                {grupo.nombre}
                              </h4>
                              {grupo.descripcion && (
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                  {grupo.descripcion}
                                </p>
                              )}
                            </div>
                            <button
                              onClick={() => handleEliminar(grupo.id)}
                              className="text-red-600 hover:text-red-700 p-1"
                              title="Eliminar grupo"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>

                          {/* Contador de documentos */}
                          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 mb-3">
                            <FileText size={14} />
                            <span className="text-xs">
                              {grupo.total_documentos} documento{grupo.total_documentos !== 1 ? 's' : ''}
                            </span>
                          </div>

                          {/* Acciones */}
                          <div className="flex gap-2">
                            <button
                              onClick={() => setGrupoSeleccionado(grupo)}
                              className="flex-1 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-200 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors text-xs font-medium"
                            >
                              Ver Detalles
                            </button>
                            <button
                              className="px-3 py-1.5 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-200 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
                              title="Enviar por email"
                            >
                              <Mail size={16} />
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  const response = await axios.get(`/api/grupos-documentos/${grupo.id}/download-zip`, {
                                    responseType: 'blob',
                                    withCredentials: true
                                  });

                                  // Crear URL del blob
                                  const url = window.URL.createObjectURL(new Blob([response.data]));
                                  const link = document.createElement('a');
                                  link.href = url;
                                  link.setAttribute('download', `grupo_${grupo.nombre}.zip`);
                                  document.body.appendChild(link);
                                  link.click();
                                  link.remove();
                                  window.URL.revokeObjectURL(url);
                                } catch (error) {
                                  console.error('Error descargando ZIP:', error);
                                  alert('Error al descargar el archivo ZIP');
                                }
                              }}
                              className="px-3 py-1.5 bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-200 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
                              title="Descargar ZIP"
                            >
                              <Download size={16} />
                            </button>
                          </div>

                          {/* Fecha de creación */}
                          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                            <p className="text-[10px] text-gray-500 dark:text-gray-500">
                              Creado: {new Date(grupo.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Modales */}
      {modalCrearAbierto && (
        <CrearGrupoModal
          empresaId={empresaId}
          onClose={() => setModalCrearAbierto(false)}
        />
      )}

      {grupoSeleccionado && (
        <DetallesGrupoModal
          grupoId={grupoSeleccionado.id}
          onClose={() => setGrupoSeleccionado(null)}
        />
      )}
    </div>
  );
}