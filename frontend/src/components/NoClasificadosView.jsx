// frontend/src/components/NoClasificadosView.jsx
import React, { useState, useEffect } from 'react';
import { useNoClasificados } from '../hooks/useNoClasificados';
import axios from 'axios';
import toast from 'react-hot-toast';
import {
  ChevronLeft, FileText, Loader2, Eye, Check, Building2,
  Search, AlertTriangle, Clock, CheckCircle, Sparkles, Plus, Trash2, X, CheckSquare, Square
} from 'lucide-react';
import DetalleNotificacionModal from './DetalleNotificacionModal';
import CrearEmpresaModal from './CrearEmpresaModal';
import { useNavigate } from 'react-router-dom';
import ConfirmModal from './ConfirmModal';
import { useQueryClient } from '@tanstack/react-query';

export default function NoClasificadosView() {
  const queryClient = useQueryClient();

  const [error, setError] = useState(null);
  const { data, isLoading, refetch } = useNoClasificados();
  const archivos = data?.files || [];
  const empresas = data?.empresas || [];
  const loading = isLoading;
  const [archivoSeleccionado, setArchivoSeleccionado] = useState(null);
  const [nifEncontrado, setNifEncontrado] = useState('Buscando...');
  const [empresaSeleccionadaId, setEmpresaSeleccionadaId] = useState('');
  const [filtroEmpresa, setFiltroEmpresa] = useState('');
  const [isAsignando, setIsAsignando] = useState(false);
  const [asignarError, setAsignarError] = useState(null);
  const [crearAlias, setCrearAlias] = useState(false);

  // Modales
  const [previewFile, setPreviewFile] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isBatchDeleteModalOpen, setIsBatchDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [isDeletingBatch, setIsDeletingBatch] = useState(false);

  const navigate = useNavigate();

  useEffect(() => {
    refetch();
  }, []);



  const handleSelectArchivo = async (archivo) => {
    setArchivoSeleccionado(archivo);
    setEmpresaSeleccionadaId('');
    setAsignarError(null);
    setIsAsignando(false);
    setNifEncontrado('Buscando NIF...');
    setCrearAlias(false);

    // ✅ TOAST: Loading durante detección de NIF
    const toastId = toast.loading(`Detectando NIF en ${archivo.nombre_archivo.substring(0, 30)}...`);

    try {
      const response = await axios.get(`/api/clasificar/obtener-nif-inbox/${archivo.nombre_archivo}`, {
        withCredentials: true
      });

      if (response.data.success) {
        const nifDetectado = response.data.nif_encontrado;
        setNifEncontrado(nifDetectado);

        // ✅ TOAST: NIF detectado o no
        if (nifDetectado && !nifDetectado.includes('No') && !nifDetectado.includes('Error')) {
          toast.success(`NIF detectado: ${nifDetectado}`, {
            id: toastId,
            icon: '🎯'
          });
          setCrearAlias(true);

          // Auto-seleccionar empresa si existe
          const empresaExistente = empresas.find(e => e.nif === nifDetectado);
          if (empresaExistente) {
            setEmpresaSeleccionadaId(empresaExistente.id.toString());
            toast.success(`Empresa encontrada: ${empresaExistente.nombre}`, { duration: 3000 });
          }
        } else {
          toast.error('No se pudo detectar un NIF válido', {
            id: toastId,
            duration: 3000
          });
        }
      } else {
        setNifEncontrado('No detectado');
        toast.error('No se pudo leer el documento', { id: toastId });
      }
    } catch (err) {
      setNifEncontrado('Error lectura');

      // ✅ TOAST: Error en detección
      toast.error('Error al detectar NIF en el documento', {
        id: toastId,
        duration: 4000
      });
    }
  };

  const handleAsignarNif = async () => {
    if (!empresaSeleccionadaId) {
      setAsignarError("Debes seleccionar una empresa.");

      // ✅ TOAST: Validación
      toast.error('Debes seleccionar una empresa', {
        icon: '⚠️',
        duration: 3000
      });
      return;
    }

    setIsAsignando(true);
    setAsignarError(null);

    const empresaSeleccionada = empresas.find(e => e.id.toString() === empresaSeleccionadaId);
    const nombreArchivo = archivoSeleccionado.nombre_archivo;

    // ✅ TOAST: Loading durante asignación
    const toastId = toast.loading(
      crearAlias && nifValido
        ? `Asignando a ${empresaSeleccionada?.nombre} y guardando alias...`
        : `Asignando a ${empresaSeleccionada?.nombre}...`
    );

    try {
      const response = await axios.post('/api/nif/asignar', {
        nif: nifEncontrado,
        empresa_id: parseInt(empresaSeleccionadaId),
        nombre_archivo: nombreArchivo,
        crear_alias: crearAlias
      }, { withCredentials: true });

      if (response.data.success) {
        // ✅ TOAST: Éxito al asignar (MEJORADO)
        toast.success(
          crearAlias && nifValido
            ? `✓ Asignado a ${empresaSeleccionada?.nombre} y alias guardado`
            : `✓ Asignado a ${empresaSeleccionada?.nombre}`,
          {
            id: toastId,
            duration: 3000
          }
        );

        // Refrescar datos de React Query
        refetch();
        setArchivoSeleccionado(null);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || "Error al asignar";
      setAsignarError(errorMsg);

      // ✅ TOAST: Error al asignar
      toast.error(`Error: ${errorMsg}`, {
        id: toastId,
        duration: 5000
      });
    } finally {
      setIsAsignando(false);
    }
  };

  const handleEliminarArchivo = (archivo, e) => {
    e?.stopPropagation();
    setDocToDelete(archivo);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    const archivo = docToDelete;

    const toastId = toast.loading(`Eliminando ${archivo.nombre_archivo.substring(0, 30)}...`);

    try {
      const response = await axios.delete(`/api/clasificar/eliminar-inbox/${archivo.nombre_archivo}`, {
        withCredentials: true
      });

      if (response.data.success) {
        toast.success('Archivo eliminado correctamente', {
          id: toastId,
          icon: '🗑️',
          duration: 3000
        });

        // Si era el archivo seleccionado, deseleccionarlo
        if (archivoSeleccionado?.nombre_archivo === archivo.nombre_archivo) {
          setArchivoSeleccionado(null);
        }

        // Refrescar lista
        refetch();
        queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || "Error al eliminar archivo";
      toast.error(`Error: ${errorMsg}`, {
        id: toastId,
        duration: 5000
      });
    } finally {
      setDocToDelete(null);
      setIsDeleteModalOpen(false);
    }
  };

  const handleEmpresaCreada = (nuevaEmpresa) => {
    // ✅ TOAST: Empresa creada
    toast.success(`✓ Empresa "${nuevaEmpresa.nombre}" creada exitosamente`, {
      duration: 3000,
      icon: '🏢'
    });

    refetch();
    setEmpresaSeleccionadaId(nuevaEmpresa.id.toString());
  };

  const handleSelectAll = () => {
    if (selectedFiles.size === archivos.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(archivos.map(a => a.nombre_archivo)));
    }
  };

  const toggleSelectFile = (e, filename) => {
    e.stopPropagation();
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filename)) {
      newSelected.delete(filename);
    } else {
      newSelected.add(filename);
    }
    setSelectedFiles(newSelected);
  };

  const handleBatchDelete = async () => {
    if (selectedFiles.size === 0) return;

    setIsDeletingBatch(true);
    const toastId = toast.loading(`Eliminando ${selectedFiles.size} archivos...`);

    try {
      const response = await axios.post('/api/clasificar/batch-delete', {
        filenames: Array.from(selectedFiles)
      }, { withCredentials: true });

      if (response.data.success) {
        toast.success(`Eliminados ${selectedFiles.size} archivos correctamente`, {
          id: toastId,
          icon: '🗑️'
        });
        setSelectedFiles(new Set());
        setIsBatchDeleteModalOpen(false);
        refetch();
        queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
      }
    } catch (err) {
      toast.error("Error al eliminar archivos por lote", { id: toastId });
    } finally {
      setIsDeletingBatch(false);
    }
  };

  const empresasFiltradas = empresas.filter(emp =>
    emp.nombre.toLowerCase().includes(filtroEmpresa.toLowerCase()) ||
    emp.nif?.toLowerCase().includes(filtroEmpresa.toLowerCase())
  );

  const empresaMostrada = empresas.find(e => e.id.toString() === empresaSeleccionadaId);

  const nifValido = nifEncontrado &&
    !nifEncontrado.includes('Buscando') &&
    !nifEncontrado.includes('No') &&
    !nifEncontrado.includes('Error');

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-gray-900">Archivos No Clasificados</h1>
              <span className="px-3 py-1 bg-red-100 text-red-700 text-sm font-semibold rounded-full">
                {archivos.length}
              </span>
            </div>
            <p className="text-gray-600 mt-1">Clasifica los archivos del INBOX asignándolos a empresas</p>
          </div>
        </div>

        {selectedFiles.size > 0 && (
          <div className="flex items-center gap-3 animate-in fade-in slide-in-from-right-4 duration-200">
            <span className="text-sm font-medium text-gray-500">
              {selectedFiles.size} seleccionados
            </span>
            <button
              onClick={() => setIsBatchDeleteModalOpen(true)}
              disabled={isDeletingBatch}
              className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors font-bold text-sm shadow-sm"
            >
              <Trash2 className="w-4 h-4" />
              Eliminar Lote
            </button>
            <button
              onClick={() => setSelectedFiles(new Set())}
              className="text-xs text-gray-400 hover:text-gray-600 underline font-bold"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>

      {/* Contenido principal - GRID DE 2 COLUMNAS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Columna Izquierda: Lista de Archivos */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 h-full max-h-[700px] flex flex-col">
            <div className="p-4 border-b border-gray-100 bg-gray-50 rounded-t-xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSelectAll}
                  className="flex items-center gap-2"
                  title={selectedFiles.size === archivos.length ? "Deseleccionar todos" : "Seleccionar todos"}
                >
                  {archivos.length > 0 && selectedFiles.size === archivos.length ? (
                    <CheckSquare className="w-5 h-5 text-primary" />
                  ) : (
                    <Square className="w-5 h-5 text-gray-400" />
                  )}
                </button>
                <h3 className="font-semibold text-gray-700">Archivos en INBOX</h3>
              </div>
              {selectedFiles.size > 0 && (
                <span className="text-xs font-bold text-primary bg-primary-light px-2 py-1 rounded-full">
                  {selectedFiles.size} seleccionados
                </span>
              )}
            </div>

            <div className="overflow-y-auto flex-1 p-2">
              {archivos.length === 0 ? (
                <div className="p-12 text-center">
                  <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">¡Inbox limpio!</h3>
                  <p className="text-gray-600">No hay archivos pendientes</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {archivos.map(archivo => (
                    <div
                      key={`${archivo.origen || 'inbox'}-${archivo.nombre_archivo}`}
                      onClick={() => handleSelectArchivo(archivo)}
                      className={`p-4 rounded-lg cursor-pointer transition-all group border
                        ${archivoSeleccionado?.nombre_archivo === archivo.nombre_archivo
                          ? 'bg-primary-light border-primary shadow-sm'
                          : 'border-transparent hover:bg-gray-50 hover:border-gray-200'
                        }`}
                    >
                      <div className="flex items-center gap-3">
                        {/* Checkbox */}
                        <div
                          className="flex-shrink-0"
                          onClick={(e) => toggleSelectFile(e, archivo.nombre_archivo)}
                        >
                          {selectedFiles.has(archivo.nombre_archivo) ? (
                            <CheckSquare className="w-5 h-5 text-primary" />
                          ) : (
                            <Square className="w-5 h-5 text-gray-300 group-hover:text-gray-400" />
                          )}
                        </div>

                        <div className={`p-2 rounded-lg transition-colors
                          ${archivoSeleccionado?.nombre_archivo === archivo.nombre_archivo
                            ? 'bg-primary-light' : 'bg-gray-100 group-hover:bg-white'
                          }`}
                        >
                          <FileText className={`w-5 h-5 
                            ${archivoSeleccionado?.nombre_archivo === archivo.nombre_archivo
                              ? 'text-primary' : 'text-gray-600'
                            }`}
                          />
                        </div>

                        <div className="flex-1 min-w-0">
                          <p className={`font-medium truncate text-sm
                            ${archivoSeleccionado?.nombre_archivo === archivo.nombre_archivo
                              ? 'text-orange-900' : 'text-gray-800'
                            }`}
                          >
                            {archivo.nombre_archivo}
                          </p>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewFile(archivo);
                            }}
                            className="p-2 hover:bg-white rounded-lg transition-colors shadow-sm border border-gray-100"
                            title="Vista previa"
                          >
                            <Eye className="w-4 h-4 text-gray-600 hover:text-primary" />
                          </button>

                          <button
                            onClick={(e) => handleEliminarArchivo(archivo, e)}
                            className="p-2 hover:bg-red-50 rounded-lg transition-colors shadow-sm border border-gray-100 hover:border-red-200"
                            title="Eliminar archivo"
                          >
                            <Trash2 className="w-4 h-4 text-gray-600 hover:text-red-600" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Columna Derecha: Panel de Asignación */}
        <div className="space-y-4">
          {archivoSeleccionado ? (
            <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-300">

              {/* Card: NIF Detectado */}
              <div className={`rounded-xl p-6 shadow-sm border ${nifValido ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                <label className={`text-xs font-bold uppercase tracking-wider block mb-2 ${nifValido ? 'text-green-700' : 'text-gray-500'}`}>
                  NIF/CIF Detectado
                </label>
                <div className="flex items-center gap-3">
                  <div className={`p-3 rounded-lg ${nifValido ? 'bg-green-100' : 'bg-gray-200'}`}>
                    {nifValido ? <Sparkles className="w-6 h-6 text-green-600" /> : <Clock className="w-6 h-6 text-gray-500" />}
                  </div>
                  <p className={`font-bold text-xl ${nifValido ? 'text-green-900' : 'text-gray-600'}`}>
                    {nifEncontrado}
                  </p>
                </div>

                {/* Checkbox Crear Alias */}
                {nifValido && (
                  <div className="mt-4 pt-4 border-t border-green-200">
                    <label className="flex items-center gap-3 cursor-pointer group select-none">
                      <input
                        type="checkbox"
                        checked={crearAlias}
                        onChange={(e) => setCrearAlias(e.target.checked)}
                        className="w-5 h-5 text-primary border-green-300 rounded focus:ring-primary cursor-pointer"
                      />
                      <span className="font-medium text-green-900 group-hover:text-green-700">
                        Guardar NIF como alias para futuras cargas
                      </span>
                    </label>
                  </div>
                )}
              </div>

              {/* Card: Seleccionar Empresa */}
              <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 flex flex-col h-[500px]">
                <h3 className="text-lg font-bold text-gray-900 mb-4">Seleccionar Empresa</h3>

                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Buscar empresa..."
                    value={filtroEmpresa}
                    onChange={(e) => setFiltroEmpresa(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none transition-all"
                  />
                </div>

                {/* Lista Scrollable */}
                <div className="flex-1 overflow-y-auto border border-gray-100 rounded-lg mb-4">
                  {empresasFiltradas.length === 0 ? (
                    <div className="p-8 text-center text-gray-500 flex flex-col items-center">
                      <Building2 className="w-8 h-8 text-gray-300 mb-2" />
                      No se encontraron empresas
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-100">
                      {empresasFiltradas.map(emp => (
                        <button
                          key={emp.id}
                          onClick={() => setEmpresaSeleccionadaId(emp.id.toString())}
                          className={`w-full p-3 text-left transition-all flex items-center justify-between
                            ${empresaSeleccionadaId === emp.id.toString()
                              ? 'bg-primary-light text-orange-900'
                              : 'bg-white hover:bg-gray-50'
                            }`}
                        >
                          <div className="min-w-0">
                            <div className="font-semibold truncate">{emp.nombre}</div>
                            <div className="text-xs text-gray-500 font-mono">{emp.nif}</div>
                          </div>
                          {empresaSeleccionadaId === emp.id.toString() && (
                            <div className="bg-primary-light p-1 rounded-full">
                              <Check className="w-4 h-4 text-primary" />
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* BOTÓN INTELIGENTE DE CREAR EMPRESA */}
                {nifValido && !empresaMostrada && (
                  <div className="mb-4 animate-in fade-in slide-in-from-bottom-2">
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="w-full py-3 border-2 border-dashed border-green-400 text-green-700 
                               bg-green-50 hover:bg-green-100 rounded-lg font-bold 
                               flex justify-center items-center gap-2 transition-colors"
                    >
                      <Plus className="w-5 h-5" />
                      Crear Empresa con NIF {nifEncontrado}
                    </button>
                  </div>
                )}

                {asignarError && (
                  <div className="bg-red-50 p-3 rounded-lg text-sm text-red-700 border border-red-200 mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" /> {asignarError}
                  </div>
                )}

                <button
                  onClick={handleAsignarNif}
                  disabled={isAsignando || !empresaSeleccionadaId}
                  className="w-full py-4 bg-linear-to-r from-orange-600 to-red-600 
                           text-white rounded-xl hover:from-orange-700 hover:to-red-700
                           transition-all font-bold text-lg flex items-center justify-center gap-2 
                           disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl
                           transform active:scale-[0.98]"
                >
                  {isAsignando ? <Loader2 className="w-6 h-6 animate-spin" /> : <Check className="w-6 h-6" />}
                  {crearAlias && nifValido ? 'Asignar y Guardar Alias' : 'Asignar Archivo'}
                </button>
              </div>

            </div>
          ) : (
            <div className="bg-white rounded-xl p-12 shadow-sm border border-gray-100 text-center h-full flex flex-col justify-center items-center text-gray-400">
              <div className="bg-gray-50 p-6 rounded-full mb-4">
                <FileText className="w-16 h-16 text-gray-300" />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-2">Selecciona un archivo</h3>
              <p>Elige un documento de la lista izquierda para comenzar a clasificar.</p>
            </div>
          )}
        </div>
      </div>

      {/* Modales */}
      {previewFile && (
        <DetalleNotificacionModal
          documento={{ ...previewFile, id: -1, nombre_archivo: previewFile.nombre_archivo }}
          onClose={() => setPreviewFile(null)}
          isPreview={true}
        />
      )}

      {showCreateModal && (
        <CrearEmpresaModal
          onClose={() => setShowCreateModal(false)}
          onEmpresaCreada={handleEmpresaCreada}
          initialNif={nifValido ? nifEncontrado : ''}
        />
      )}

      {/* Modal de Confirmación Premium */}
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="¿Eliminar definitivamente?"
        message={`Estás a punto de borrar "${docToDelete?.nombre_archivo}" del servidor. Esta acción es permanente.`}
        confirmText="Sí, eliminar"
        cancelText="Cancelar"
      />

      {/* Modal de Confirmación para Batch Delete */}
      <ConfirmModal
        isOpen={isBatchDeleteModalOpen}
        onClose={() => setIsBatchDeleteModalOpen(false)}
        onConfirm={handleBatchDelete}
        title="¿Eliminar Lote del Inbox?"
        message={`Vas a borrar definitivamente ${selectedFiles.size} archivos del inbox. Esta acción no se puede deshacer.`}
        confirmText="Sí, eliminar lote"
        cancelText="Cancelar"
      />
    </div>
  );
}