// frontend/src/components/MesaTrabajo.jsx
import React, { useState, useEffect } from 'react';
import { useMesaTrabajo, useMesaTrabajoStats } from '../hooks/useMesaTrabajo';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../AuthContext';
import { Building2, Calendar, User, ChevronLeft, ChevronRight, Zap, ArrowRight, FileText, Clock, CheckCircle2, Loader2, Search, Square, CheckSquare, Eye, Trash2, Bell, X } from 'lucide-react';
import axios from '../utils/axiosConfig';
import toast from 'react-hot-toast';
import ModalProcesamientoUnificado from './ModalProcesamientoUnificado';
import MobilePDFViewer from './MobilePDFViewer';
import ConfirmModal from './ConfirmModal';
import NotifyDocumentButton from './NotifyDocumentButton';
import ScheduleNotificationModal from './ScheduleNotificationModal';
import ConfiguracionPerfilModal from './ConfiguracionPerfilModal';
import { Settings, Lock } from 'lucide-react';

export default function MesaTrabajo() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  // ✅ PRIMERO: Declarar states
  const [search, setSearch] = useState('');
  const [empresaFilter, setEmpresaFilter] = useState('');
  const [page, setPage] = useState(1);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isBatchDeleteModalOpen, setIsBatchDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // ✅ Fix: Estado local para loading de batch
  const [showBatchTemplateModal, setShowBatchTemplateModal] = useState(false);
  const [plantillas, setPlantillas] = useState([]);
  const [loadingPlantillas, setLoadingPlantillas] = useState(false);
  const [perfilSugerido, setPerfilSugerido] = useState(null);
  const [loadingPerfil, setLoadingPerfil] = useState(false);
  const [perfilesSistema, setPerfilesSistema] = useState([]);
  const [editingProfile, setEditingProfile] = useState(null); // ✅ Nuevo estado para modal config
  const [perfilAutoCreado, setPerfilAutoCreado] = useState(null); // Para perfil creado por auto-detección
  const [autoDetectando, setAutoDetectando] = useState(false);

  // ✅ DESPUÉS: React Query (usa las variables de arriba)
  const { data: docsData, isLoading, refetch: refetchDocs } = useMesaTrabajo(page, search, empresaFilter);
  const { data: statsData, refetch: refetchStats } = useMesaTrabajoStats();

  const documentos = docsData?.documentos || [];
  const totalPages = docsData?.total_pages || 1;
  const stats = statsData?.stats || {};
  const loading = isLoading;

  const handleUpdatedConfig = () => {
    cargarPlantillas(); // Recargar perfiles para actualizar estado visual
  };
  // ✅ LUEGO: Handlers
  const handleSelectDoc = (doc, index) => {
    setSelectedDoc(doc);
    setSelectedIndex(index);
  };

  const handleNext = () => {
    if (selectedIndex < documentos.length - 1) {
      const newIndex = selectedIndex + 1;
      setSelectedIndex(newIndex);
      setSelectedDoc(documentos[newIndex]);
    }
  };

  const handlePrev = () => {
    if (selectedIndex > 0) {
      const newIndex = selectedIndex - 1;
      setSelectedIndex(newIndex);
      setSelectedDoc(documentos[newIndex]);
    }
  };

  const toggleSelectDoc = (docId) => {
    const newSelected = new Set(selectedDocs);
    if (newSelected.has(docId)) {
      newSelected.delete(docId);
    } else {
      newSelected.add(docId);
    }
    setSelectedDocs(newSelected);
  };

  const handleAccionCompletada = () => {
    refetchDocs();
    refetchStats();
    setShowModal(false);
  };

  const handleRemoveDocument = (e, doc) => {
    e.stopPropagation();
    setDocToDelete(doc);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    const { id: docId, empresa_id: empresaIdToDelete } = docToDelete;

    try {
      const response = await axios.delete(`/api/documentos/${docId}`);
      if (response.data.success) {
        toast.success('Documento eliminado correctamente');

        // Refrescar lista local
        queryClient.invalidateQueries({ queryKey: ['mesa-trabajo'] });

        // Refrescar CONTADORES globales
        queryClient.invalidateQueries({ queryKey: ['stats-mesa-trabajo'] });
        queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
        queryClient.invalidateQueries({ queryKey: ['empresas-stats'] });

        // Refrescar la empresa específica (si el backend nos da el ID o lo tenemos)
        const empresaId = response.data.empresa_id || empresaIdToDelete;
        if (empresaId) {
          queryClient.invalidateQueries({
            queryKey: ['empresa', String(empresaId)],
            exact: false
          });
        } else {
          // Si no sabemos qué empresa es, refrescamos todas para estar seguros
          queryClient.invalidateQueries({ queryKey: ['empresa'], exact: false });
        }

        if (selectedDoc?.id === docId) setSelectedDoc(null);
      } else {
        toast.error(response.data.error || 'Error al eliminar el documento');
      }
    } catch (error) {
      console.error('Error eliminando documento:', error);
      const msg = error.response?.data?.error || error.message;
      toast.error(`Error: ${msg}`);
    } finally {
      setDocToDelete(null);
      setIsDeleteModalOpen(false);
    }
  };

  const handleSelectAll = (e) => {
    e.stopPropagation();
    if (selectedDocs.size === documentosFiltrados.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(documentosFiltrados.map(d => d.id)));
    }
  };

  const handleBatchAutomation = async (opciones = null) => {
    if (selectedDocs.size === 0) return;

    let plantillaId = null;
    let perfilSistema = null;

    // Normalizar argumentos para compatibilidad
    if (typeof opciones === 'string' || typeof opciones === 'number') {
      plantillaId = opciones;
    } else if (opciones && typeof opciones === 'object' && opciones.perfil_sistema) {
      perfilSistema = opciones.perfil_sistema;
    }

    // Si no se pasó nada explícito y no hemos abierto el modal, cargamos y mostramos
    if (!plantillaId && !perfilSistema && !showBatchTemplateModal) {
      cargarPlantillas();
      setShowBatchTemplateModal(true);
      return;
    }

    // ✅ VALIDACIÓN MULTITENANT (NUEVO)
    if (perfilSistema) {
      const perfilObj = perfilesSistema.find(p => p.clase === perfilSistema);
      if (perfilObj) {
        const { categoria, departamento } = perfilObj.configuracion || {};

        // Si el perfil no tiene configuración válida de gestoría, bloqueamos y ofrecemos configurar
        if (!categoria || !departamento) {
          toast((t) => (
            <div className="flex items-center gap-2" onClick={() => toast.dismiss(t.id)}>
              <span>Perfil incompleto.</span>
              <button
                className="font-bold underline hover:text-blue-200"
                onClick={(e) => {
                  e.stopPropagation();
                  toast.dismiss(t.id);
                  setEditingProfile(perfilObj);
                }}
              >
                Configurar ahora
              </button>
            </div>
          ), {
            duration: 5000,
            position: 'top-center',
            style: { background: '#ef4444', color: '#fff' },
            icon: '🚫'
          });
          return;
        }
      }
    }

    try {
      setIsProcessing(true);

      const payload = {
        documento_ids: Array.from(selectedDocs),
        accion: 'automatizar',
        parametros: {
          plantilla_id: plantillaId,
          perfil_sistema: perfilSistema // Puede ser null
        }
      };

      const res = await axios.post('/api/mesa-trabajo/batch-process', payload);

      if (res.data.success) {
        toast.success(`Procesados ${res.data.resultados.length} documentos`);
        setSelectedDocs(new Set());
        setShowBatchTemplateModal(false); // Cerrar modal si estaba abierto
        refetchDocs();
        refetchStats();
      }
    } catch (err) {
      console.error('Error en batch process:', err);
      const msg = err.response?.data?.error || err.message || "Error desconocido";
      console.error(msg);
      toast.error(`Error: ${msg}`);
    } finally {
      setIsProcessing(false);
    }
  };

  /**
   * Flujo Autodetectar Sistema cuando no hay perfil coincidente:
   * 1. Llamar al endpoint que activa OCR + detecta emisor/tipo
   * 2. El backend crea un ConfiguracionPerfil automáticamente
   * 3. Abrimos ConfiguracionPerfilModal para que el usuario configure el destino
   * 4. Al guardar → ejecutamos la automatización con el nuevo perfil
   */
  const handleAutoDetectarYCrear = async () => {
    if (selectedDocs.size === 0) return;
    const docIds = Array.from(selectedDocs);
    // Solo funciona bien con un doc a la vez para la detección
    const docId = docIds[0];

    setAutoDetectando(true);
    try {
      const res = await axios.post('/api/configuracion-perfiles/auto-detectar', {
        doc_id: docId
      });

      if (res.data.success && res.data.perfil) {
        const perfil = res.data.perfil;

        if (perfil.pendiente_destino) {
          // Perfil creado pero sin destino → abrir modal de configuración
          toast.success(
            perfil.es_nuevo
              ? `✨ Perfil detectado: "${perfil.nombre}". Configura su destino.`
              : `🔄 Perfil: "${perfil.nombre}". Completa la configuración de destino.`,
            { duration: 4000 }
          );
          setPerfilAutoCreado(perfil);
          // Abrir ConfiguracionPerfilModal con los datos del perfil auto-creado
          setEditingProfile({
            clase: perfil.clave,
            nombre: perfil.nombre,
            icono: perfil.icono,
            color: 'violet'
          });
        } else {
          // Perfil ya tiene destino configurado → ejecutar directamente
          toast.success(`✅ Aplicando perfil "${perfil.nombre}" → ${perfil.categoria_actual}`);
          await handleBatchAutomation({ perfil_sistema: perfil.clave });
        }

        // Recargar lista de perfiles para que aparezca el nuevo
        cargarPlantillas();

      } else if (res.data.necesita_ocr) {
        toast.error('El documento no tiene texto extraído. Procésalo primero con OCR.', {
          duration: 4000
        });
      }
    } catch (err) {
      console.error('Error en auto-detección:', err);
      toast.error('Error al analizar el documento');
    } finally {
      setAutoDetectando(false);
    }
  };

  const cargarPlantillas = async () => {
    setLoadingPlantillas(true);
    try {
      // Cargar plantillas de usuario
      const resPlantillas = await axios.get('/api/plantillas', { withCredentials: true });
      if (resPlantillas.data.success) setPlantillas(resPlantillas.data.plantillas || []);

      // Cargar perfiles de sistema (NUEVO)
      const resPerfiles = await axios.get('/api/perfiles-sistema', { withCredentials: true });
      if (resPerfiles.data.perfiles) setPerfilesSistema(resPerfiles.data.perfiles);

    } catch (err) {
      console.error("Error cargando opciones de automatización:", err);
      toast.error("Error cargando opciones");
    } finally {
      setLoadingPlantillas(false);
    }
  };

  // Detectar perfil sugerido al abrir el modal con 1 documento seleccionado
  useEffect(() => {
    if (!showBatchTemplateModal) {
      setPerfilSugerido(null);
      return;
    }
    if (selectedDocs.size !== 1) return;

    const docId = Array.from(selectedDocs)[0];
    setLoadingPerfil(true);
    axios.get(`/api/documentos/${docId}/detectar-perfil`, { withCredentials: true })
      .then(res => setPerfilSugerido(res.data.perfil || null))
      .catch(() => setPerfilSugerido(null))
      .finally(() => setLoadingPerfil(false));
  }, [showBatchTemplateModal, selectedDocs]);

  // Auto-scroll al perfil sugerido
  useEffect(() => {
    if (showBatchTemplateModal && perfilSugerido) {
      setTimeout(() => {
        const sugeridoBtn = document.querySelector('.ring-emerald-200'); // Clase específica del sugerido
        if (sugeridoBtn) {
          sugeridoBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 500);
    }
  }, [showBatchTemplateModal, perfilSugerido]);

  const handleBatchDelete = async () => {
    if (selectedDocs.size === 0) return;
    try {
      setIsProcessing(true);
      const res = await axios.post('/api/mesa-trabajo/batch-process', {
        documento_ids: Array.from(selectedDocs),
        accion: 'eliminar'
      });
      if (res.data.success) {
        toast.success(`Eliminados ${res.data.resultados.length} documentos correctamente`);
        setSelectedDocs(new Set());
        setIsBatchDeleteModalOpen(false);
        refetchDocs();
        refetchStats();
        queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
      }
    } catch (err) {
      console.error('Error en batch delete:', err);
      toast.error("Error al eliminar documentos por lote");
    } finally {
      setIsProcessing(false);
    }
  };
  // Filtrar documentos
  const documentosFiltrados = documentos.filter(doc => {
    if (search && !doc.nombre_archivo.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    return true;
  });

  if (loading && documentos.length === 0) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 lg:px-6 py-3 lg:py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl lg:text-3xl font-bold text-gray-900 flex items-center gap-2 lg:gap-3">
              <Zap className="w-6 h-6 lg:w-8 lg:h-8 text-primary" />
              Mesa de Trabajo
            </h1>
            <p className="text-gray-500 mt-1 text-sm lg:text-base hidden sm:block">
              Procesa todos tus documentos pendientes desde un solo lugar
            </p>
          </div>

          {/* Stats Cards */}
          <div className="flex gap-2 lg:gap-4">
            <div className="bg-primary-light border border-primary-light rounded-lg px-2 lg:px-4 py-1 lg:py-2">
              <div className="text-xs text-primary font-medium">Pendientes</div>
              <div className="text-lg lg:text-2xl font-bold text-primary-hover">
                {stats.total_pendientes || 0}
              </div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg px-2 lg:px-4 py-1 lg:py-2">
              <div className="text-xs text-green-600 font-medium">Hoy</div>
              <div className="text-lg lg:text-2xl font-bold text-green-700">
                {stats.procesados_hoy || 0}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Lista de Documentos - Full width en móvil, 35% en desktop */}
        <div className="w-full lg:w-[35%] bg-white border-r border-gray-200 flex flex-col">
          {/* Search & Filters */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center gap-3 mb-3">
              <button
                onClick={handleSelectAll}
                className="flex-shrink-0 p-1 hover:bg-gray-100 rounded transition-colors"
                title={selectedDocs.size === documentosFiltrados.length ? "Deseleccionar todos" : "Seleccionar todos"}
              >
                {documentosFiltrados.length > 0 && selectedDocs.size === documentosFiltrados.length ? (
                  <CheckSquare className="w-5 h-5 text-primary" />
                ) : (
                  <Square className="w-5 h-5 text-gray-400" />
                )}
              </button>
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar documento..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            {selectedDocs.size > 0 && (
              <div className="flex flex-col gap-2 bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm shadow-sm animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                      {selectedDocs.size}
                    </span>
                    <span className="text-blue-700 font-medium">seleccionados</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsBatchDeleteModalOpen(true)}
                      className="p-1.5 bg-red-100 text-red-600 rounded-md hover:bg-red-200 transition-colors"
                      title="Eliminar seleccionados"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setSelectedDocs(new Set())}
                      className="p-1.5 bg-gray-200 text-gray-600 rounded-md hover:bg-gray-300 transition-colors text-[10px] font-bold uppercase"
                    >
                      Limpiar
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => handleBatchAutomation(null)}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-semibold text-xs shadow-sm shadow-blue-200"
                >
                  <Zap className="w-3.5 h-3.5 fill-current" />
                  Aplicar Automatización
                </button>
              </div>
            )}
          </div>

          {/* Lista */}
          <div className="flex-1 overflow-y-auto">
            {documentosFiltrados.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="font-medium">No hay documentos pendientes</p>
                <p className="text-sm">¡Excelente trabajo! 🎉</p>
              </div>
            ) : (
              documentosFiltrados.map((doc, index) => (
                <div
                  key={doc.id}
                  onClick={() => handleSelectDoc(doc, index)}
                  className={`p-3 lg:p-4 border-b border-gray-100 cursor-pointer transition-colors active:bg-gray-100 ${selectedDoc?.id === doc.id
                    ? 'bg-primary-light border-l-4 border-l-orange-500'
                    : 'hover:bg-gray-50'
                    }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox - Oculto en móvil */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelectDoc(doc.id);
                      }}
                      className="mt-1 hidden lg:block"
                    >
                      {selectedDocs.has(doc.id) ? (
                        <CheckSquare className="w-5 h-5 text-primary" />
                      ) : (
                        <Square className="w-5 h-5 text-gray-400" />
                      )}
                    </button>

                    {/* Icon */}
                    <div className={`p-2 rounded-lg flex-shrink-0 ${selectedDoc?.id === doc.id ? 'bg-primary-light' : 'bg-gray-100'
                      }`}>
                      <FileText className={`w-4 h-4 lg:w-5 lg:h-5 ${selectedDoc?.id === doc.id ? 'text-primary' : 'text-gray-600'
                        }`} />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h4 className={`font-medium text-sm truncate ${selectedDoc?.id === doc.id ? 'text-orange-900' : 'text-gray-900'
                        }`}>
                        {doc.nombre_archivo}
                      </h4>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                        <Building2 className="w-3 h-3" />
                        <span className="truncate">{doc.empresa?.nombre}</span>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {new Date(doc.fecha_creacion).toLocaleDateString('es-ES')}
                      </div>
                    </div>

                    {/* Indicator - Chevron en móvil, solo en seleccionado en desktop */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleRemoveDocument(e, doc)}
                        className="p-1 px-2 text-gray-400 hover:text-white hover:bg-red-500 rounded-md transition-all"
                        title="Eliminar físicamente"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ChevronRight className={`w-5 h-5 flex-shrink-0 lg:hidden text-gray-400`} />
                      {selectedDoc?.id === doc.id && (
                        <ChevronRight className="hidden lg:block w-5 h-5 text-primary" />
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Paginación */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-gray-200 flex items-center justify-between">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Anterior
              </button>
              <span className="text-sm text-gray-600">
                Página {page} de {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Siguiente
              </button>
            </div>
          )}
        </div>

        {/* Panel de Vista Previa - Oculto en móvil, visible en desktop */}
        <div className="hidden lg:flex flex-1 bg-gray-100 flex-col">
          {selectedDoc ? (
            <>
              {/* Header del documento */}
              <div className="bg-white border-b border-gray-200 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h2 className="text-xl font-bold text-gray-900 truncate mb-1">
                      {selectedDoc.nombre_archivo}
                    </h2>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="flex items-center gap-1">
                        <Building2 className="w-4 h-4" />
                        {selectedDoc.empresa?.nombre}
                      </span>
                      <span>
                        {new Date(selectedDoc.fecha_creacion).toLocaleString('es-ES')}
                      </span>
                    </div>
                  </div>

                  {/* Botones de Notificación (solo para Jefatura) */}
                  {(user?.departamento === 'Jefatura' || user?.departamento === 'Super Admin' || user?.rol === 'jefatura' || user?.rol === 'super_admin') && (
                    <div className="flex items-center gap-2">
                      <NotifyDocumentButton
                        document={selectedDoc}
                        company={selectedDoc.empresa}
                      />
                      <button
                        onClick={() => setShowScheduleModal(true)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium rounded-lg hover:from-purple-700 hover:to-purple-600 transition-all shadow-sm hover:shadow-md active:scale-95"
                        title="Programar recordatorios de vencimiento"
                      >
                        <Clock className="w-4 h-4" />
                        <span>Programar</span>
                      </button>
                    </div>
                  )}

                  {/* Navegación */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handlePrev}
                      disabled={selectedIndex === 0}
                      className="p-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      title="Anterior"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-sm text-gray-600 px-2">
                      {selectedIndex + 1} / {documentos.length}
                    </span>
                    <button
                      onClick={handleNext}
                      disabled={selectedIndex === documentos.length - 1}
                      className="p-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                      title="Siguiente"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-hidden">
                <MobilePDFViewer documentId={selectedDoc.id} />
              </div>

              {/* Botón de Acción Principal */}
              <div className="bg-white border-t border-gray-200 px-6 py-4">
                <button
                  onClick={() => setShowModal(true)}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 font-medium shadow-lg hover:shadow-xl transition-all"
                >
                  <Zap className="w-5 h-5" />
                  Procesar Documento
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Eye className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <p className="text-lg font-medium">Selecciona un documento</p>
                <p className="text-sm">Elige un documento de la lista para comenzar</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal de Procesamiento */}
      {showModal && selectedDoc && (
        <ModalProcesamientoUnificado
          documento={selectedDoc}
          onClose={() => {
            setShowModal(false);
            refetchDocs();
            refetchStats();
          }}
          onSuccess={handleAccionCompletada}
        />
      )}

      {/* Modal de Selección de Plantilla para Batch */}
      {showBatchTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl shadow-2xl max-w-6xl w-full overflow-hidden border border-gray-100 animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50">
              <h3 className="text-xl font-bold text-gray-900">Aplicar Automatización</h3>
              <button onClick={() => setShowBatchTemplateModal(false)} className="text-gray-400 hover:text-gray-600 transition-colors">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="flex flex-col lg:flex-row h-[70vh]">
              {/* Columna Izquierda: Controles */}
              <div className="w-full lg:w-1/2 flex flex-col border-r border-gray-100">
                <div className="p-6 flex-1 overflow-y-auto">
                  <p className="text-gray-600 text-sm mb-4">
                    Selecciona un perfil o regla para aplicar a los {selectedDocs.size} documentos seleccionados, o deja que el sistema lo detecte automáticamente.
                  </p>

                  {/* Banner de perfil sugerido */}
                  {loadingPerfil && (
                    <div className="flex items-center gap-2 p-3 mb-4 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-500">
                      <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      Analizando documento...
                    </div>
                  )}
                  {!loadingPerfil && perfilSugerido && (
                    <div className="flex items-center gap-3 p-3 mb-4 bg-emerald-50 border border-emerald-200 rounded-xl cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => handleBatchAutomation(null)}>
                      <span className="text-2xl">{perfilSugerido.icono}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold text-emerald-700 uppercase tracking-wide">Perfil detectado</p>
                        <p className="text-sm font-bold text-emerald-900 truncate">{perfilSugerido.nombre}</p>
                      </div>
                      <span className="text-[10px] bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full font-bold">SUGERIDO</span>
                    </div>
                  )}

                  <div className="space-y-3">
                    <button
                      onClick={handleAutoDetectarYCrear}
                      disabled={isProcessing || autoDetectando}
                      className="w-full flex items-center gap-3 p-4 bg-orange-50 border-2 border-orange-200 rounded-xl hover:bg-orange-100 transition-all text-left group disabled:opacity-60"
                    >
                      <div className="p-2 bg-orange-500 rounded-lg text-white">
                        {autoDetectando
                          ? <Loader2 className="w-5 h-5 animate-spin" />
                          : <Zap className="w-5 h-5 fill-current" />}
                      </div>
                      <div className="flex-1">
                        <span className="font-bold text-orange-900 block group-hover:text-orange-950">
                          {autoDetectando ? 'Analizando documento...' : 'Autodetectar Sistema'}
                        </span>
                        <span className="text-xs text-orange-700">
                          {autoDetectando
                            ? 'Leyendo OCR e identificando tipo de documento'
                            : 'Lee el OCR, detecta el tipo y crea el perfil automáticamente'}
                        </span>
                      </div>
                      {!autoDetectando && <ArrowRight className="w-5 h-5 text-orange-400 group-hover:translate-x-1 transition-transform" />}
                    </button>

                    {/* SECCIÓN: PERFILES DE SISTEMA (MANUAL) */}
                    <div className="relative py-2">
                      <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-gray-200"></span></div>
                      <div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-2 text-gray-400 font-bold tracking-widest">Selección Manual</span></div>
                    </div>

                    {perfilesSistema.map(perfil => {
                      const isSugerido = perfilSugerido?.clase === perfil.clase;
                      const isConfigured = perfil.configuracion?.categoria && perfil.configuracion?.departamento;

                      return (
                        <div key={perfil.clase} className="relative group/item">
                          <button
                            onClick={() => handleBatchAutomation({ perfil_sistema: perfil.clase })}
                            disabled={isProcessing}
                            className={`w-full flex items-center gap-3 p-3 border rounded-xl transition-all text-left relative pr-12
                                ${isSugerido
                                ? 'bg-emerald-50 border-emerald-500 ring-2 ring-emerald-200 shadow-sm z-10'
                                : 'bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                              }`}
                          >
                            {isSugerido && (
                              <div className="absolute -top-2.5 right-4 bg-emerald-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm flex items-center gap-1 z-20">
                                <Zap className="w-3 h-3 fill-current" />
                                SUGERIDO
                              </div>
                            )}
                            <div className={`relative flex items-center justify-center w-10 h-10 rounded-lg text-xl font-bold transition-colors
                                ${isSugerido ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 group-hover/item:bg-white'}`}>
                              {perfil.icono}
                              {!isConfigured && (
                                <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full border-2 border-white ring-1 ring-red-200"></div>
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`font-bold block truncate ${isSugerido ? 'text-emerald-900' : 'text-gray-900'} ${!isConfigured ? 'opacity-70' : ''}`}>
                                  {perfil.nombre}
                                </span>
                              </div>
                              <span className={`text-xs truncate block ${isSugerido ? 'text-emerald-700' : 'text-gray-500'}`}>
                                {!isConfigured ? (
                                  <span className="text-orange-600 font-bold flex items-center gap-1">
                                    ⚠️ Requiere configuración
                                  </span>
                                ) : (
                                  perfil.descripcion
                                )}
                              </span>
                            </div>
                          </button>

                          {/* Botón Configuración */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingProfile(perfil);
                            }}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 hover:bg-white rounded-full text-gray-400 hover:text-blue-600 transition-all z-20 shadow-sm hover:shadow-md bg-transparent"
                            title="Configurar automatización"
                          >
                            <Settings className={`w-4 h-4 ${!isConfigured ? 'text-orange-500 animate-pulse' : ''}`} />
                          </button>
                        </div>
                      )
                    })}

                    {/* SECCIÓN: PLANTILLAS USUARIO (SI EXISTEN) */}
                    {plantillas.length > 0 && (
                      <>
                        <div className="relative py-2">
                          <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-gray-200"></span></div>
                          <div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-2 text-gray-400 font-bold tracking-widest">Mis Reglas</span></div>
                        </div>
                        {plantillas.map(p => (
                          <button
                            key={p.id}
                            onClick={() => handleBatchAutomation(p.id)}
                            disabled={isProcessing}
                            className="w-full flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all text-left shadow-xs"
                          >
                            <div className="p-2 bg-blue-100 rounded-lg text-blue-600 text-xs font-mono font-bold capitalize">
                              {p.codigo.substring(0, 2)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <span className="font-bold text-gray-900 block truncate">{p.nombre}</span>
                              <span className="text-xs text-gray-500 truncate block">{p.descripcion}</span>
                            </div>
                          </button>
                        ))}
                      </>
                    )}
                  </div>
                </div>

                {/* Footer Columna Izquierda */}
                <div className="p-4 bg-gray-50 border-t border-gray-100 flex justify-end">
                  <button
                    onClick={() => setShowBatchTemplateModal(false)}
                    className="px-6 py-2 text-gray-600 font-bold hover:text-gray-800 transition-colors"
                  >
                    Cerrar
                  </button>
                </div>
              </div>

              {/* Columna Derecha: PDF Viewer (Solo Desktop) */}
              <div className="hidden lg:block w-1/2 bg-gray-100 h-full overflow-hidden border-l border-gray-200">
                {selectedDocs.size === 1 ? (
                  <MobilePDFViewer documentId={Array.from(selectedDocs)[0]} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-400 p-8 text-center">
                    <FileText className="w-16 h-16 mb-4 text-gray-300" />
                    <p className="font-medium">Selecciona un solo documento para ver la vista previa</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Confirmación para Batch Delete */}
      <ConfirmModal
        isOpen={isBatchDeleteModalOpen}
        onClose={() => setIsBatchDeleteModalOpen(false)}
        onConfirm={handleBatchDelete}
        title="¿Eliminar Lote Seleccionado?"
        message={`Estás a punto de borrar definitivamente ${selectedDocs.size} documentos. Se eliminarán tanto de la base de datos como del disco físico. Esta acción no se puede deshacer.`}
        confirmText="Sí, eliminar lote"
        cancelText="Cancelar"
      />

      {/* Modal de Configuración de Perfil (Multitenant) */}
      <ConfiguracionPerfilModal
        show={!!editingProfile}
        onClose={() => {
          setEditingProfile(null);
          setPerfilAutoCreado(null);
        }}
        perfil={editingProfile}
        onUpdated={async () => {
          handleUpdatedConfig(); // Recargar lista de perfiles
          // Si venimos del flujo de auto-detección, ejecutar automáticamente
          if (perfilAutoCreado) {
            const clave = perfilAutoCreado.clave;
            setEditingProfile(null);
            setPerfilAutoCreado(null);
            setShowBatchTemplateModal(false);
            // Pequeña pausa para que el modal se cierre antes de lanzar
            await new Promise(r => setTimeout(r, 300));
            toast.success('✅ Destino configurado — ejecutando automatización...');
            await handleBatchAutomation({ perfil_sistema: clave });
          }
        }}
      />


      {/* Modal de Documento para Móvil */}
      {selectedDoc && (
        <div className="lg:hidden fixed inset-0 bg-white z-50 flex flex-col">
          <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
            <button
              onClick={() => setSelectedDoc(null)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-6 h-6 text-gray-700" />
            </button>
            <div className="flex-1 min-w-0">
              <h2 className="font-semibold text-gray-900 truncate text-sm">
                {selectedDoc.nombre_archivo}
              </h2>
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Building2 className="w-3 h-3" />
                <span className="truncate">{selectedDoc.empresa?.nombre}</span>
              </div>
            </div>
            {/* Navegación móvil */}
            <div className="flex items-center gap-1">
              <button
                onClick={handlePrev}
                disabled={selectedIndex === 0}
                className="p-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed active:bg-gray-100"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-gray-600 px-1">
                {selectedIndex + 1}/{documentos.length}
              </span>
              <button
                onClick={handleNext}
                disabled={selectedIndex === documentos.length - 1}
                className="p-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed active:bg-gray-100"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* PDF Viewer */}
          <div className="flex-1 overflow-hidden bg-gray-100">
            <MobilePDFViewer documentId={selectedDoc.id} />
          </div>

          {/* Botón de Acción */}
          <div className="bg-white border-t border-gray-200 p-4">
            <button
              onClick={() => setShowModal(true)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium shadow-lg active:scale-95 transition-transform"
            >
              <Zap className="w-5 h-5" />
              Procesar Documento
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {/* Modal de Confirmación Premium */}
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="¿Eliminar físicamente?"
        message={`¿Estás seguro de que quieres eliminar "${docToDelete?.nombre_archivo || 'este documento'}"? Esta acción borrará el archivo del servidor y de la base de datos de forma permanente.`}
        confirmText="Confirmar eliminación"
        cancelText="Cancelar"
      />

      {/* Modal de Programación de Notificaciones */}
      {showScheduleModal && selectedDoc && (
        <ScheduleNotificationModal
          document={selectedDoc}
          onClose={() => setShowScheduleModal(false)}
        />
      )}
    </div>
  );
}
