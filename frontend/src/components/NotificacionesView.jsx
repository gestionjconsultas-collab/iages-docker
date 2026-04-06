// frontend/src/components/NotificacionesView.jsx
import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useDocumentos } from '../hooks/useDocumentos';
import {
  ChevronLeft, FileText, Download, Eye, Clock, CheckCircle,
  AlertCircle, Loader2, Bot, FolderInput, FolderPlus, X, Trash2,
  Info, Zap, Search, Mail, Upload, LayoutGrid, List, FileType, CheckSquare,
  Globe, Plus, ShieldAlert, FileSearch, Banknote, Scale
} from 'lucide-react';
import DetalleNotificacionModal from './DetalleNotificacionModal';
import ClasificarModal from './ClasificarModal';
import StatusLectura from './StatusLectura';
import FiniquitosGestionView from './FiniquitosGestionView';
import toast from 'react-hot-toast';
import axios from 'axios';
import { useGruposDeDocumento } from '../hooks/useGruposDocumentos';
import GrupoBadge from './GrupoBadge';
import AgregarAGrupoModal from './AgregarAGrupoModal';
import MobilePDFViewer from './MobilePDFViewer';
import ConfirmModal from './ConfirmModal';
import EnviarDocumentosModal from './EnviarDocumentosModal';
import NuevaInspeccionModal from './NuevaInspeccionModal';
import EnviarEmailGrupoModal from './EnviarEmailGrupoModal';
import SubirInspeccionModal from './SubirInspeccionModal';

export default function NotificacionesView() {
  const queryClient = useQueryClient();
  const { empresaId, categoria } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const esInvitado = user?.departamento === 'Invitado' || user?.rol_nombre === 'Invitado';

  // Estados para modal de borrado
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);

  // ✅ REACT QUERY: Reemplaza useState + useEffect
  const { data, isLoading, refetch } = useDocumentos(empresaId, categoria);
  const documentos = data?.documentos || [];
  const empresa = data?.empresa || null;

  const [documentoParaGrupo, setDocumentoParaGrupo] = useState(null);
  const [pdfViewerDoc, setPdfViewerDoc] = useState(null); // Nuevo estado para visor PDF
  const [plantillas, setPlantillas] = useState([]); // Lista de plantillas
  const [plantillaSeleccionada, setPlantillaSeleccionada] = useState(''); // Plantilla seleccionada en visor

  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docParaClasificar, setDocParaClasificar] = useState(null);
  const [procesandoId, setProcesandoId] = useState(null);

  // Estados nueva función: selección múltiple y correo
  const [selectedDocs, setSelectedDocs] = useState([]);
  const [isEmailModalOpen, setIsEmailModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState(categoria === 'Notificaciones' ? 'kanban' : 'list');
  const [selectedYear, setSelectedYear] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [isNuevaInspeccionOpen, setIsNuevaInspeccionOpen] = useState(false);
  const [isSubirInspeccionOpen, setIsSubirInspeccionOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [isReprocessing, setIsReprocessing] = useState(false);
  const [expandedAplazMain, setExpandedAplazMain] = useState({});

  // Funciones Selección Múltiple
  const toggleSelection = (doc, e) => {
    e?.stopPropagation();
    setSelectedDocs(prev => {
      const isSelected = prev.some(d => d.doc_id === doc.id);
      if (isSelected) {
        return prev.filter(d => d.doc_id !== doc.id);
      } else {
        return [...prev, { doc_id: doc.id, titulo: doc.nombre_archivo }];
      }
    });
  };

  const toggleSelectAll = (filteredDocs) => {
    if (selectedDocs.length === filteredDocs.length) {
      setSelectedDocs([]); // Deseleccionar todos
    } else {
      setSelectedDocs(filteredDocs.map(doc => ({ doc_id: doc.id, titulo: doc.nombre_archivo })));
    }
  };

  const clearSelection = () => setSelectedDocs([]);

  const handleVerDetalles = async (doc) => {
    // Abrir el modal inmediatamente, independientemente de si está procesado
    setSelectedDoc(doc);
    setPdfViewerDoc(null);
  };

  const pollTaskStatus = async (taskId, docOriginal) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/tasks/${taskId}`, { withCredentials: true });
        if (res.data.state === 'SUCCESS') {
          clearInterval(interval);
          setProcesandoId(null);
          await refetch(); // ✅ Refrescar con React Query
          setSelectedDoc({
            ...docOriginal,
            procesado: true,
            datos_extraidos: res.data.result.datos_extraidos
          });
        } else if (res.data.state === 'FAILURE') {
          clearInterval(interval);
          setProcesandoId(null);
          toast.error("Error en el análisis de IA");
        }
      } catch {
        clearInterval(interval);
        setProcesandoId(null);
      }
    }, 2000);
  };

  const handleDownload = (docId, fileName) => {
    const link = document.createElement('a');
    link.href = `/api/documentos/${docId}/archivo?download=1`;
    link.setAttribute('download', fileName || 'documento.pdf');
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast.success('Iniciando descarga...');
  };

  const handleDeleteDocument = async (doc) => {
    setDocToDelete(doc);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    const doc = docToDelete;

    try {
      const response = await axios.delete(`/api/documentos/${doc.id}`, { withCredentials: true });
      if (response.data.success) {
        toast.success('Documento eliminado correctamente');

        // Refrescar lista de la vista actual
        queryClient.invalidateQueries({ queryKey: ['documentos', empresaId, categoria] });

        // Refrescar CONTADORES (Fuerza bruta con prefijos para evitar problemas de tipos)
        queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
        queryClient.invalidateQueries({ queryKey: ['stats-mesa-trabajo'] });
        queryClient.invalidateQueries({ queryKey: ['empresas-stats'] });

        // Refrescar específicamente esta empresa (normalizando a string)
        queryClient.invalidateQueries({
          queryKey: ['empresa', String(empresaId)],
          exact: false
        });

      } else {
        toast.error(response.data.error || 'Error al intentar eliminar el archivo');
      }
    } catch (error) {
      console.error('Error al eliminar:', error);
      toast.error('Ocurrió un error al intentar eliminar el documento');
    } finally {
      setDocToDelete(null);
      setIsDeleteModalOpen(false);
    }
  };

  const handleFilesUpload = async (files) => {
    if (files.length === 0) return;
    const toastId = toast.loading(`Iniciando procesamiento de ${files.length} archivo(s)...`);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files[]', file));
      formData.append('empresa_id', empresaId);
      formData.append('categoria', categoria);

      // Decidir endpoint SEGÚN CATEGORÍA
      const categoriasConOCR = [
        'Altas de Trabajadores', 'Bajas de Trabajadores', 'Nóminas',
        'Seguros Sociales', 'Finiquitos', 'Contratos',
        'Certificados de Retenciones 190', 'Certificados de Retenciones 180',
        'Impuestos'
      ];

      const endpoint = categoriasConOCR.includes(categoria)
        ? '/api/subir-a-categoria'
        : '/api/subir-directo-multiple';

      const response = await axios.post(endpoint, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          // Si ya terminó de subir (100%), lo dejamos en 99% para indicar que se está PROCESANDO en el servidor
          setUploadProgress(percentCompleted < 100 ? percentCompleted : 99);
        }
      });

      setUploadProgress(100);

      if (response.data.success) {
        toast.success(`¡Completado! ${response.data.exitosos || files.length} documentos procesados en "${categoria}".`, { id: toastId });
        refetch();
        setSelectedDocs([]);
      } else {
        toast.error(response.data.message || 'Error en el procesamiento', { id: toastId });
      }
    } catch (err) {
      console.error('Error procesando archivos:', err);
      toast.error(`Error: ${err.response?.data?.error || err.message}`, { id: toastId });
    } finally {
      setUploadProgress(null);
    }
  };

  const handleReprocesar = async () => {
    if (!window.confirm(`¿Estás seguro de que deseas reprocesar TODOS los documentos de la categoría "${categoria}" para esta empresa? Esto usará la IA para volver a extraer los datos de los archivos existentes.`)) {
      return;
    }

    setIsReprocessing(true);
    const tid = toast.loading("Reprocesando documentos con IA...");
    try {
      const resp = await axios.post('/api/admin/documentos/reprocesar-categoria', {
        empresa_id: empresaId,
        categoria: categoria
      }, { withCredentials: true });

      if (resp.data.success) {
        toast.success(resp.data.message, { id: tid });
        refetch();
      } else {
        toast.error(resp.data.error || "Error al reprocesar", { id: tid });
      }
    } catch (err) {
      console.error("Error al reprocesar:", err);
      toast.error("Error de conexión al reprocesar", { id: tid });
    } finally {
      setIsReprocessing(false);
    }
  };

  const handleReprocesarGlobal = async () => {
    const msg = `¡ATENCIÓN! Vas a reprocesar TODOS los documentos de la categoría "${categoria}" en TODAS las empresas de la gestoría.\n\n` +
                `Esto procesará miles de archivos y consumirá tokens de IA significativos.\n\n` +
                `¿Deseas continuar con el reprocesamiento GLOBAL?`;

    if (!window.confirm(msg)) {
      return;
    }

    setIsReprocessing(true);
    const tid = toast.loading(`Iniciando reprocesamiento global de ${categoria}...`);
    try {
      const resp = await axios.post('/api/admin/documentos/reprocesar-categoria-global', {
        categoria: categoria
      }, { withCredentials: true });

      if (resp.data.success) {
        toast.success(resp.data.message, { id: tid, duration: 6000 });
      } else {
        toast.error(resp.data.error || "Error al iniciar reprocesamiento global", { id: tid });
      }
    } catch (err) {
      console.error("Error global:", err);
      toast.error("Error de conexión", { id: tid });
    } finally {
      setIsReprocessing(false);
    }
  };

  const MESES = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
  };

  const uniqueYears = React.useMemo(() => {
    const years = new Set();
    documentos.forEach(doc => {
      let year = null;
      if (doc.periodo) {
        year = doc.periodo.toString().substring(0, 4);
      } else if (doc.datos_extraidos && doc.datos_extraidos.ejercicio) {
        year = doc.datos_extraidos.ejercicio.toString();
      } else if (doc.fecha_creacion) {
        year = new Date(doc.fecha_creacion).getFullYear().toString();
      }
      if (year) years.add(year);
    });
    return Array.from(years).sort((a, b) => b - a); // Descendente
  }, [documentos]);

  const uniqueMonths = React.useMemo(() => {
    if (!['Nominas', 'Seguros Sociales'].includes(categoria)) return [];
    const months = new Set();
    documentos.forEach(doc => {
      if (doc.periodo && doc.periodo.toString().length >= 6) {
        const year = doc.periodo.toString().substring(0, 4);
        if (!selectedYear || year === selectedYear) {
          months.add(doc.periodo.toString().substring(4, 6));
        }
      }
    });
    return Array.from(months).sort();
  }, [documentos, categoria, selectedYear]);

  // Resetear mes al cambiar año o categoría
  React.useEffect(() => {
    setSelectedMonth('');
  }, [selectedYear, categoria]);

  const documentosFiltrados = documentos.filter(doc => {
    const term = searchTerm.toLowerCase();

    // Buscar por nombre de archivo
    let matchesSearch = doc.nombre_archivo.toLowerCase().includes(term);

    // Buscar también por nombre de empleado (si existe en datos_extraidos)
    if (!matchesSearch && doc.datos_extraidos?.nombre_empleado) {
      matchesSearch = doc.datos_extraidos.nombre_empleado.toLowerCase().includes(term);
    }

    let year = null;
    if (doc.periodo) {
      year = doc.periodo.toString().substring(0, 4);
    } else if (doc.datos_extraidos && doc.datos_extraidos.ejercicio) {
      year = doc.datos_extraidos.ejercicio.toString();
    } else if (doc.fecha_creacion) {
      year = new Date(doc.fecha_creacion).getFullYear().toString();
    }

    const matchesYear = selectedYear ? year === selectedYear : true;

    let month = null;
    if (doc.periodo && doc.periodo.toString().length >= 6) {
      month = doc.periodo.toString().substring(4, 6);
    }
    const matchesMonth = selectedMonth ? month === selectedMonth : true;

    return matchesSearch && matchesYear && matchesMonth;
  });

  // ✅ AGRUPACION VISUAL PARA ALTAS Y BAJAS
  const documentosVisuales = React.useMemo(() => {
    const categoriasConAgrupacion = ['Altas de Trabajadores', 'Bajas de Trabajadores'];
    if (!categoriasConAgrupacion.includes(categoria)) return documentosFiltrados;

    const result = [];
    const groupsMap = {};

    documentosFiltrados.forEach(doc => {
      const groupPrefix = categoria === 'Altas de Trabajadores' ? 'Alta - ' : 'Baja - ';
      const movementGroup = doc.grupos?.find(g => g.nombre.startsWith(groupPrefix));

      if (movementGroup) {
        if (!groupsMap[movementGroup.id]) {
          groupsMap[movementGroup.id] = {
            id: `group-${movementGroup.id}`,
            isGroup: true,
            grupo: movementGroup,
            docs: []
          };
          result.push(groupsMap[movementGroup.id]);
        }
        groupsMap[movementGroup.id].docs.push(doc);
      } else {
        result.push(doc);
      }
    });
    return result;
  }, [documentosFiltrados, categoria]);

  // Cargar plantillas
  const cargarPlantillas = async () => {
    try {
      const res = await axios.get('/api/plantillas', { withCredentials: true });
      if (res.data.success) {
        setPlantillas(res.data.plantillas || []);
      }
    } catch (err) {
      console.error("Error cargando plantillas", err);
    }
  };

  // Cargar plantillas al montar
  React.useEffect(() => {
    cargarPlantillas();
  }, []);

  // Actualizar plantilla seleccionada cuando se abre el visor
  React.useEffect(() => {
    if (pdfViewerDoc) {
      setPlantillaSeleccionada(pdfViewerDoc.tipo_documento_asignado || '');
    }
  }, [pdfViewerDoc]);

  // ✅ Auto-abrir documento si viene parámetro 'doc' en URL
  React.useEffect(() => {
    // Solo ejecutar si ya terminó de cargar y hay documentos
    if (isLoading || documentos.length === 0) return;

    const params = new URLSearchParams(window.location.search);
    const docId = params.get('doc');

    if (docId && !pdfViewerDoc) {
      const doc = documentos.find(d => d.id === parseInt(docId));
      if (doc) {
        console.log('📄 Auto-abriendo documento desde URL:', doc.nombre_archivo);
        setPdfViewerDoc(doc);
        // Limpiar parámetro de URL
        window.history.replaceState({}, '', window.location.pathname);
      } else {
        console.warn('⚠️ Documento no encontrado en la lista:', docId);
      }
    }
  }, [documentos, isLoading, pdfViewerDoc]);

  // Cambiar plantilla del documento
  const cambiarPlantilla = async () => {
    if (!plantillaSeleccionada || !pdfViewerDoc) return;

    try {
      await axios.put(
        `/api/documentos/${pdfViewerDoc.id}`,
        { tipo_documento_asignado: plantillaSeleccionada },
        { withCredentials: true }
      );

      toast.success('Plantilla actualizada correctamente');
      await refetch(); // Refrescar lista

      // Actualizar documento en el visor
      setPdfViewerDoc({
        ...pdfViewerDoc,
        tipo_documento_asignado: plantillaSeleccionada
      });
    } catch (err) {
      toast.error('Error al actualizar plantilla');
      console.error(err);
    }
  };

  const prioridades = [
    { id: 'informativa', label: 'Informativas', color: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: Info },
    { id: 'importante', label: 'Importantes', color: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', icon: Zap },
    { id: 'urgente', label: 'Urgentes', color: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: AlertCircle },
  ];

  const handleDragEnd = async (docId, nuevaPrioridad) => {
    try {
      await axios.put(`/api/documentos/${docId}`, { prioridad: nuevaPrioridad }, { withCredentials: true });
      toast.success(`Movido a ${nuevaPrioridad}`);
      await refetch();
    } catch (err) {
      toast.error("Error al mover documento");
    }
  };

  const renderKanbanView = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-250px)]">
      {prioridades.map(col => (
        <div
          key={col.id}
          className={`flex flex-col rounded-2xl border-2 ${col.border} ${col.color} p-4 overflow-hidden shadow-sm`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            const docId = e.dataTransfer.getData("docId");
            if (docId) handleDragEnd(docId, col.id);
          }}
        >
          {/* Column Header */}
          <div className="flex items-center justify-between mb-4 px-1">
            <div className="flex items-center gap-2">
              <col.icon className={`w-5 h-5 ${col.text}`} />
              <h2 className={`font-bold uppercase tracking-wider text-xs ${col.text}`}>{col.label}</h2>
            </div>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${col.text} bg-white/50 border ${col.border}`}>
              {/* Contar documentos reales, no solo los items visuales */}
              {documentosVisuales.filter(item => {
                const doc = item.isGroup ? item.docs[0] : item;
                return (doc.prioridad || 'informativa') === col.id;
              }).reduce((acc, item) => acc + (item.isGroup ? item.docs.length : 1), 0)}
            </span>
          </div>

          {/* Column Content */}
          <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
            {documentosVisuales
              .filter(item => {
                const doc = item.isGroup ? item.docs[0] : item;
                return (doc.prioridad || 'informativa') === col.id;
              })
              .map(item => {
                if (item.isGroup) {
                  return (
                    <GroupedKanbanCard
                      key={item.id}
                      item={item}
                      col={col}
                      selectedDocs={selectedDocs}
                      toggleSelection={toggleSelection}
                      setPdfViewerDoc={setPdfViewerDoc}
                      handleVerDetalles={handleVerDetalles}
                      handleDeleteDocument={handleDeleteDocument}
                      setDocumentoParaGrupo={setDocumentoParaGrupo}
                    />
                  );
                }
                const doc = item;
                const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
                return (
                  <div
                    key={doc.id}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData("docId", doc.id)}
                    onClick={() => {
                      // Al hacer clic en la tarjeta, si el modo seleccion global está activo o simplemente queremos abrir el visor
                      // Mantendremos abrir el visor como acción primaria si no hacen click exacto en el checkbox
                      // Aunque podemos habilitar toggleSelection si `selectedDocs.length > 0`
                      if (selectedDocs.length > 0) { toggleSelection(doc); }
                      else { setPdfViewerDoc(doc); }
                    }}
                    className={`rounded-xl p-4 shadow-sm border transition-all cursor-grab active:cursor-grabbing group relative ${isSelected
                      ? 'bg-blue-50 border-primary ring-1 ring-primary shadow-md'
                      : 'bg-white border-gray-100 hover:border-primary/30 hover:shadow-md'
                      }`}
                  >
                    {/* Badge lateral de importancia */}
                    <div className={`absolute left-0 top-4 bottom-4 w-1 rounded-r-full transition-all group-hover:w-1.5 ${col.id === 'urgente' ? 'bg-red-500' : col.id === 'importante' ? 'bg-orange-500' : 'bg-blue-500'}`} />

                    {/* Checkbox absoluto en la esquina */}
                    <div
                      className={`absolute top-3 right-3 z-10 ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} transition-opacity`}
                      onClick={(e) => toggleSelection(doc, e)}
                    >
                      <div className={`w-5 h-5 rounded flex items-center justify-center border transition-colors cursor-pointer ${isSelected ? 'bg-primary border-primary text-white' : 'bg-white border-gray-300 hover:border-primary'}`}>
                        {isSelected && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                      </div>
                    </div>

                    <div className="pl-2">
                      <div className="flex justify-between items-start mb-2">
                        <GrupoBadgesWrapper documentoId={doc.id} />
                        <div className="flex items-center gap-1">
                          {doc.procesado && <CheckCircle className="w-3 h-3 text-emerald-500" />}
                          {!doc.leido && <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />}
                        </div>
                      </div>

                      <button
                        onClick={(e) => { e.stopPropagation(); setPdfViewerDoc(doc); }}
                        className="text-sm font-bold text-gray-900 hover:text-primary leading-snug text-left w-[90%] line-clamp-2 mb-2"
                      >
                        {doc.nombre_archivo}
                      </button>

                      {(doc.datos_extraidos?.nombre_empleado || doc.datos_extraidos?.nombre_trabajador) && (
                        <div className="text-xs text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md inline-flex items-center gap-1 mb-3 font-semibold max-w-[90%] truncate">
                          👤 {doc.datos_extraidos.nombre_empleado || doc.datos_extraidos.nombre_trabajador}
                        </div>
                      )}

                      <div className="flex items-center justify-between text-[11px] text-gray-500">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {new Date(doc.fecha_creacion).toLocaleDateString()}
                        </span>

                        <div className="flex items-center gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => { e.stopPropagation(); setDocumentoParaGrupo(doc); }}
                            className="p-1.5 hover:bg-blue-50 rounded-lg text-gray-400 hover:text-blue-500 transition-colors"
                            title="Agregar a Grupo"
                          >
                            <FolderPlus className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleVerDetalles(doc); }}
                            className="p-1.5 hover:bg-primary/10 rounded-lg text-primary transition-colors"
                            title="Ver Detalles"
                          >
                            <Bot className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteDocument(doc); }}
                            className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
                            title="Eliminar"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })
            }

            {documentosVisuales.filter(item => {
              const doc = item.isGroup ? item.docs[0] : item;
              return (doc.prioridad || 'informativa') === col.id;
            }).length === 0 && (
                <div className="py-12 flex flex-col items-center justify-center border-2 border-dashed border-gray-200/50 rounded-2xl bg-white/30">
                  <div className="p-3 bg-gray-50 rounded-full mb-2">
                    <FileText className="w-6 h-6 text-gray-300" />
                  </div>
                  <p className="text-[10px] font-medium text-gray-400">Sin notificaciones</p>
                </div>
              )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderListView = () => (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/50 border-b border-gray-100">
              <th className="px-6 py-4 w-10">
                <div
                  className={`w-5 h-5 rounded flex items-center justify-center border transition-colors cursor-pointer ${selectedDocs.length > 0 && selectedDocs.length === documentosFiltrados.length ? 'bg-primary border-primary text-white' : 'bg-white border-gray-300 hover:border-primary'}`}
                  onClick={() => toggleSelectAll(documentosFiltrados)}
                >
                  {selectedDocs.length > 0 && selectedDocs.length === documentosFiltrados.length && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                  {selectedDocs.length > 0 && selectedDocs.length < documentosFiltrados.length && <div className="w-2.5 h-2.5 bg-primary rounded-sm" />}
                </div>
              </th>
              <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Documento</th>
              <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Fecha</th>
              <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Estado</th>
              <th className="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {documentosVisuales.map(item => {
              if (item.isGroup) {
                return (
                  <GroupedRow
                    key={item.id}
                    item={item}
                    selectedDocs={selectedDocs}
                    toggleSelection={toggleSelection}
                    setPdfViewerDoc={setPdfViewerDoc}
                    handleVerDetalles={handleVerDetalles}
                    handleDeleteDocument={handleDeleteDocument}
                    refetch={refetch}
                  />
                );
              }
              const doc = item;
              const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
              const isAplaz = !!doc.datos_extraidos?.is_aplazamiento;
              const aplazExpanded = expandedAplazMain[doc.id];
              const detalleLiq = doc.datos_extraidos?.detalle_liquidacion || [];
              return (
                <React.Fragment key={doc.id}>
                <tr
                  className={`hover:bg-gray-50/50 transition-all group border-l-4 ${isSelected
                    ? 'bg-blue-50 border-l-primary'
                    : isAplaz ? 'border-l-amber-400' : 'bg-transparent border-l-transparent'
                    }`}
                >
                  <td className="px-6 py-4">
                    <div
                      className={`w-5 h-5 rounded flex items-center justify-center border transition-colors cursor-pointer ${isSelected ? 'bg-primary border-primary text-white' : 'bg-white border-gray-300 hover:border-primary'}`}
                      onClick={(e) => toggleSelection(doc, e)}
                    >
                      {isSelected && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-blue-50 text-blue-600 rounded-lg group-hover:scale-110 transition-transform">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <button
                          onClick={() => setPdfViewerDoc(doc)}
                          className="text-sm font-bold text-gray-900 hover:text-primary transition-colors text-left truncate max-w-md"
                        >
                          {doc.nombre_archivo}
                        </button>
                        {(doc.datos_extraidos?.nombre_empleado || doc.datos_extraidos?.nombre_trabajador) && (
                          <div className="text-xs text-blue-600 font-semibold mt-0.5 mb-1 truncate max-w-md">
                            👤 {doc.datos_extraidos.nombre_empleado || doc.datos_extraidos.nombre_trabajador}
                          </div>
                        )}
                        <GrupoBadgesWrapper documentoId={doc.id} />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-4 h-4" />
                      {new Date(doc.fecha_creacion).toLocaleDateString()}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <StatusLectura documento={doc} onActualizar={refetch} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                      {isAplaz && (
                        <button
                          onClick={() => setExpandedAplazMain(prev => ({ ...prev, [doc.id]: !prev[doc.id] }))}
                          className="flex items-center gap-1 px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-700 rounded-lg text-xs font-bold transition-colors"
                          title="Ver detalle aplazamiento"
                        >
                          ⚡ {aplazExpanded ? '▲' : '▼'}
                        </button>
                      )}
                      <button
                        onClick={() => setDocumentoParaGrupo(doc)}
                        className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Agregar a Grupo"
                      >
                        <FolderPlus className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleVerDetalles(doc)}
                        className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                        title="Ver Detalles"
                      >
                        <Bot className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDownload(doc.id, doc.nombre_archivo)}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Descargar"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeleteDocument(doc)}
                        className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
                {isAplaz && aplazExpanded && (
                  <tr>
                    <td colSpan={5} className="px-6 pb-4 bg-amber-50">
                      {detalleLiq.length === 0 ? (
                        <p className="text-xs text-gray-500 italic py-2">Sin datos de liquidación extraídos.</p>
                      ) : (() => {
                          const totalGeneral = detalleLiq.reduce((sum, liq) =>
                            sum + (liq.plazos || []).reduce((s, p) => s + (p.importe_total_plazo || 0), 0), 0);
                          return (
                          <div className="space-y-3 pt-2">
                            {detalleLiq.map((liq, liqIdx) => (
                              <div key={liqIdx} className="border rounded-lg overflow-hidden bg-white shadow-sm">
                                <div className="bg-blue-50 px-3 py-1.5 border-b flex items-center gap-3">
                                  <span className="font-mono text-xs font-bold text-blue-800">{liq.numero_liquidacion}</span>
                                  {liq.concepto && <span className="text-xs text-blue-600">{liq.concepto}</span>}
                                  {liq.fecha_intereses && <span className="text-xs text-gray-400 ml-auto">Int. desde: {liq.fecha_intereses}</span>}
                                </div>
                                <div className="overflow-x-auto">
                                  <table className="w-full text-xs">
                                    <thead className="bg-gray-50">
                                      <tr>
                                        <th className="px-2 py-1 text-center font-semibold border-b border-r text-gray-600">#</th>
                                        <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Principal</th>
                                        <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Recargo</th>
                                        <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Total Deuda</th>
                                        <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Intereses</th>
                                        <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Total Plazo</th>
                                        <th className="px-2 py-1 text-center font-semibold border-b text-gray-600">Vencimiento</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {(liq.plazos || []).map((p, pIdx) => (
                                        <tr key={pIdx} className="border-t hover:bg-blue-50">
                                          <td className="px-2 py-1 text-center border-r text-gray-400">{pIdx + 1}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(p.importe_principal || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(p.recargo_apremio || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(p.importe_total_deuda || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r text-orange-600">€{(p.importe_intereses || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r font-semibold">€{(p.importe_total_plazo || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-center font-medium text-blue-700">{p.fecha_vencimiento || '—'}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                    {liq.subtotal && (
                                      <tfoot className="bg-gray-100 font-semibold border-t-2">
                                        <tr>
                                          <td className="px-2 py-1 text-center border-r text-gray-400">Sub</td>
                                          <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_principal || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.recargo_apremio || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_total_deuda || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r text-orange-600">€{(liq.subtotal.importe_intereses || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_total_plazo || 0).toFixed(2)}</td>
                                          <td className="px-2 py-1 text-center text-gray-400">Subtotal</td>
                                        </tr>
                                      </tfoot>
                                    )}
                                  </table>
                                </div>
                              </div>
                            ))}
                            <div className="flex justify-end pb-1">
                              <div className="bg-gray-800 text-white px-5 py-2 rounded-lg text-sm font-bold">
                                TOTAL GENERAL: €{totalGeneral.toFixed(2)}
                              </div>
                            </div>
                          </div>
                          );
                        })()}
                    </td>
                  </tr>
                )}
                </React.Fragment>
              )
            })}
          </tbody>
        </table>
        {documentosFiltrados.length === 0 && (
          <div className="py-20 text-center">
            <div className="inline-block p-4 bg-gray-50 rounded-full mb-4">
              <FileText className="w-12 h-12 text-gray-200" />
            </div>
            <p className="text-gray-400 font-medium">No se encontraron documentos</p>
          </div>
        )}
      </div>
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex justify-center h-96 items-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  const renderInspeccionesView = () => {
    const gruposMap = {};
    const sinGrupo = [];
    documentosFiltrados.forEach(doc => {
      if (doc.grupos && doc.grupos.length > 0) {
        const grupo = doc.grupos[0];
        if (!gruposMap[grupo.id]) gruposMap[grupo.id] = { grupo, docs: [] };
        gruposMap[grupo.id].docs.push(doc);
      } else {
        sinGrupo.push(doc);
      }
    });
    const grupos = Object.values(gruposMap);

    if (grupos.length === 0 && sinGrupo.length === 0) {
      return (
        <div className="py-28 flex flex-col items-center justify-center">
          <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
            <ShieldAlert className="w-8 h-8 text-gray-300" />
          </div>
          <p className="text-gray-500 font-semibold">No hay expedientes de inspección</p>
          <p className="text-gray-400 text-sm mt-1">Usa el botón "Nuevo" para crear uno</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {grupos.map(({ grupo, docs }) => (
          <InspeccionGrupoCard
            key={grupo.id}
            grupo={grupo}
            docs={docs}
            selectedDocs={selectedDocs}
            toggleSelection={toggleSelection}
            setPdfViewerDoc={setPdfViewerDoc}
            handleVerDetalles={handleVerDetalles}
            handleDeleteDocument={handleDeleteDocument}
            handleDownload={handleDownload}
            setDocumentoParaGrupo={setDocumentoParaGrupo}
            refetch={refetch}
          />
        ))}
        {sinGrupo.length > 0 && (
          <div className="bg-white rounded-2xl border border-dashed border-gray-200 shadow-sm overflow-hidden">
            <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
              <FolderInput className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-semibold text-gray-500">Sin expediente</span>
              <span className="ml-1 px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-bold rounded-full">{sinGrupo.length}</span>
            </div>
            <div className="divide-y divide-gray-50">
              {sinGrupo.map(doc => {
                const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
                return (
                  <div key={doc.id} className={`flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50 transition-colors ${isSelected ? 'bg-blue-50' : ''}`}>
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border cursor-pointer shrink-0 ${isSelected ? 'bg-primary border-primary text-white' : 'border-gray-300 hover:border-primary bg-white'}`}
                      onClick={(e) => toggleSelection(doc, e)}
                    >
                      {isSelected && <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                    </div>
                    <div className="p-1.5 bg-gray-100 rounded-lg shrink-0"><FileText className="w-4 h-4 text-gray-500" /></div>
                    <button onClick={() => setPdfViewerDoc(doc)} className="text-sm font-medium text-gray-800 hover:text-primary transition-colors truncate flex-1 text-left">{doc.nombre_archivo}</button>
                    <span className="text-xs text-gray-400 shrink-0 flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{new Date(doc.fecha_creacion).toLocaleDateString()}</span>
                    <StatusLectura documento={doc} onActualizar={refetch} />
                    <div className="flex items-center gap-1 shrink-0">
                      <button onClick={() => setDocumentoParaGrupo(doc)} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Agregar a expediente"><FolderPlus className="w-4 h-4" /></button>
                      <button onClick={() => handleDownload(doc.id, doc.nombre_archivo)} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="Descargar"><Download className="w-4 h-4" /></button>
                      <button onClick={() => handleDeleteDocument(doc)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Eliminar"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(`/empresa/${empresaId}`)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ChevronLeft className="w-6 h-6 text-gray-600" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-gray-900">{categoria}</h1>
              <span className="px-3 py-1 bg-[#fff7ed] text-[#9a3412] text-sm font-black rounded-full border-2 border-[#ffedd5] shadow-sm">
                {documentos.length}
              </span>
            </div>
            <p className="text-[#374151] font-bold text-base">{empresa?.nombre}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="file"
            id="direct-upload-input"
            className="hidden"
            multiple
            accept=".pdf"
            onChange={async (e) => {
              const files = Array.from(e.target.files || []);
              handleFilesUpload(files);
              e.target.value = ''; // Reset
            }}
          />

          {/* Handler de Subida */}
          <div className="relative group">
            <button
              onClick={() => categoria === 'Inspecciones'
                ? setIsSubirInspeccionOpen(true)
                : document.getElementById('direct-upload-input').click()
              }
              className="flex items-center gap-2 px-6 py-2.5 bg-[#f97316] text-white font-black rounded-xl hover:bg-[#ea580c] transition-all shadow-[0_4px_14px_0_rgba(249,115,22,0.39)] hover:shadow-[0_6px_20px_rgba(249,115,22,0.23)] active:scale-95 border-2 border-[#ea580c]/30"
              style={{ backgroundColor: '#f97316' }}
            >
              <Upload className="w-5 h-5 stroke-[3px]" />
              <span className="text-white">Subir</span>
            </button>

            {/* Tooltip de Advertencia */}
            <div className="absolute top-full right-0 mt-2 w-64 p-3 bg-gray-800 text-white text-xs rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 pointer-events-none">
              <div className="flex gap-2 items-start">
                <AlertCircle className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  <strong>Subida directa:</strong> Los archivos subidos aquí se guardarán inmediatamente <strong>sin extraer automáticamente</strong> los datos mediante Inteligencia Artificial (OCR).
                </p>
              </div>
            </div>
          </div>


          {categoria === 'Inspecciones' && !esInvitado && (
            <button
              onClick={() => setIsNuevaInspeccionOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white text-sm font-bold rounded-xl hover:bg-gray-700 transition-all active:scale-95"
            >
              <Plus className="w-4 h-4 stroke-[2.5px]" />
              Nuevo
            </button>
          )}

          <div className="flex bg-gray-100 p-1 rounded-xl shadow-inner">
            <button
              onClick={() => setViewMode('kanban')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'kanban' ? 'bg-white shadow-sm text-primary' : 'text-gray-500 hover:text-gray-700'}`}
              title="Vista Kanban"
            >
              <LayoutGrid className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white shadow-sm text-primary' : 'text-gray-500 hover:text-gray-700'}`}
              title="Vista Lista"
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>
        {/* Buscador y Filtros */}
        <div className="flex items-center gap-3">
          {['Impuestos', 'Certificados de Retenciones 190', 'Certificados de Retenciones 180'].includes(categoria) && uniqueYears.length > 0 && (
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all bg-white font-medium text-gray-700 h-[42px]"
            >
              <option value="">Años (Todos)</option>
              {uniqueYears.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          )}
          {['Nominas', 'Seguros Sociales'].includes(categoria) && uniqueYears.length > 0 && (
            <>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(e.target.value)}
                className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all bg-white font-medium text-gray-700 h-[42px]"
              >
                <option value="">Año (Todos)</option>
                {uniqueYears.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="px-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all bg-white font-medium text-gray-700 h-[42px]"
              >
                <option value="">Mes (Todos)</option>
                {uniqueMonths.map(m => (
                  <option key={m} value={m}>{MESES[m] || m}</option>
                ))}
              </select>
            </>
          )}
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Buscar notificación..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary focus:border-transparent outline-none text-sm transition-all"
            />
          </div>
        </div>
      </div>

      {/* Magic Drop Zone & View Content */}
      <div
        className={`relative min-h-[400px] transition-all duration-300 rounded-3xl ${isDragging ? 'bg-primary/5 ring-4 ring-primary ring-dashed ring-offset-4' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!esInvitado) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (esInvitado) return;
          const files = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
          if (files.length > 0) {
            handleFilesUpload(files);
          } else {
            toast.error("Solo se admiten archivos PDF");
          }
        }}
      >
        {/* Overlay de Arrastre Premium */}
        {isDragging && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm rounded-3xl animate-in fade-in zoom-in duration-300">
            <div className="w-24 h-24 bg-primary text-white rounded-full flex items-center justify-center shadow-2xl shadow-primary/40 animate-bounce mb-6">
              <Upload className="w-10 h-10 stroke-[3px]" />
            </div>
            <h2 className="text-3xl font-black text-gray-900 mb-2">¡Suelta los archivos aquí!</h2>
            <p className="text-lg text-gray-600 font-medium">Categoría: <span className="text-primary font-bold">{categoria}</span></p>
            <div className="mt-8 flex gap-3">
              <span className="px-4 py-2 bg-gray-100 rounded-full text-xs font-bold text-gray-500">Solo PDF</span>
              <span className="px-4 py-2 bg-gray-100 rounded-full text-xs font-bold text-gray-500">Multiselección activa</span>
            </div>
          </div>
        )}

        {/* Indicador de Progreso Global */}
        {uploadProgress !== null && (
          <div className="mb-6 bg-white border border-gray-100 rounded-2xl p-4 shadow-sm animate-in slide-in-from-top-4">
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-primary animate-spin" />
                <span className="text-sm font-bold text-gray-700">
                  {uploadProgress >= 99 ? 'Procesando en servidor (OCR)...' : `Subiendo documentos en ${categoria}...`}
                </span>
              </div>
              <span className="text-xs font-black text-primary">{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-100 h-2 rounded-full overflow-hidden">
              <div
                className="bg-primary h-full transition-all duration-300 ease-out"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
          </div>
        )}

        {categoria === 'Inspecciones'
          ? renderInspeccionesView()
          : viewMode === 'kanban' ? renderKanbanView() : renderListView()
        }
      </div>

      {/* Barra de Acciones Global (Multi-Select) */}
      {selectedDocs.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-white border border-gray-200 shadow-[0_8px_30px_rgb(0,0,0,0.12)] rounded-full px-6 py-3 flex items-center gap-6 animate-in slide-in-from-bottom-5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center">
              <span className="text-blue-700 font-bold text-sm">{selectedDocs.length}</span>
            </div>
            <span className="text-gray-800 font-bold text-sm">
              {selectedDocs.length === 1 ? 'Documento seleccionado' : 'Documentos seleccionados'}
            </span>
          </div>

          <div className="h-6 w-px bg-gray-200"></div>

          <div className="flex items-center gap-3">
            <button
              onClick={clearSelection}
              className="px-4 py-2 hover:bg-gray-100 text-gray-500 hover:text-gray-700 rounded-full text-sm font-bold transition-colors"
            >
              Cancelar
            </button>
            <button
              onClick={() => setIsEmailModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-full text-sm font-bold shadow-md shadow-blue-500/20 transition-all hover:scale-105 active:scale-95"
            >
              <Mail className="w-4 h-4" />
              Enviar por Correo
            </button>
          </div>
        </div>
      )}

      {/* Modales */}
      {docParaClasificar && (
        <ClasificarModal
          documento={docParaClasificar}
          onClose={() => setDocParaClasificar(null)}
          onClasificado={refetch} // ✅ Usar refetch
        />
      )
      }



      {
        selectedDoc && (
          <DetalleNotificacionModal
            documento={selectedDoc}
            onClose={() => setSelectedDoc(null)}
            onStatusChange={refetch} // ✅ Usar refetch
          />
        )
      }

      {
        documentoParaGrupo && (
          <AgregarAGrupoModal
            documentoId={documentoParaGrupo.id}
            empresaId={parseInt(empresaId)}
            onClose={() => setDocumentoParaGrupo(null)}
          />
        )
      }

      {/* Modal Visor PDF */}
      {
        pdfViewerDoc && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                  <FileText className="w-6 h-6 text-primary" />
                  <div>
                    <h3 className="font-bold text-gray-900">{pdfViewerDoc.nombre_archivo}</h3>
                    <p className="text-sm text-gray-500">{empresa?.nombre}</p>
                  </div>
                </div>
                <button
                  onClick={() => setPdfViewerDoc(null)}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6 text-gray-600" />
                </button>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-hidden">
                <MobilePDFViewer documentId={pdfViewerDoc.id} />
              </div>

              {/* Footer con botones - Ocultos para invitados */}
              {!esInvitado && (
                <div className="p-4 border-t border-gray-200 bg-gray-50">
                  <div className="flex items-center justify-between gap-4">
                    {/* Izquierda: Descargar y Plantilla */}
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleDownload(pdfViewerDoc.id, pdfViewerDoc.nombre_archivo)}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        Descargar
                      </button>

                      {/* Selector de Plantilla */}
                      <div className="flex items-center gap-2">
                        <FileType className="w-5 h-5 text-gray-600" />
                        <select
                          value={plantillaSeleccionada}
                          onChange={(e) => setPlantillaSeleccionada(e.target.value)}
                          className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-sm"
                        >
                          <option value="">Sin plantilla</option>
                          {plantillas.map(p => (
                            <option key={p.id} value={p.codigo}>
                              {p.nombre}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={cambiarPlantilla}
                          disabled={!plantillaSeleccionada || plantillaSeleccionada === pdfViewerDoc.tipo_documento_asignado}
                          className="px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                        >
                          Aplicar
                        </button>
                      </div>
                    </div>

                    {/* Centro: Revertir a Pendiente (solo si NO está en Por Procesar) */}
                    {categoria !== 'Por Procesar' && (
                      <button
                        onClick={async () => {
                          try {
                            await axios.post(`/api/documentos/${pdfViewerDoc.id}/marcar-pendiente`, {}, { withCredentials: true });
                            toast.success('Documento revertido a Por Procesar');
                            setPdfViewerDoc(null);
                            await refetch();
                          } catch (err) {
                            toast.error('Error al revertir documento');
                            console.error(err);
                          }
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-medium"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                        </svg>
                        Revertir a Pendiente
                      </button>
                    )}

                    {/* Derecha: Ver Detalles */}
                    <button
                      onClick={() => handleVerDetalles(pdfViewerDoc)}
                      className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-700 to-indigo-700 hover:from-blue-800 hover:to-indigo-800 text-white rounded-lg transition-colors font-bold shadow-md"
                    >
                      <Bot className="w-4 h-4" />
                      Ver Detalles
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )
      }

      {/* Modal de Enviar Correos */}
      <EnviarDocumentosModal
        isOpen={isEmailModalOpen}
        onClose={() => setIsEmailModalOpen(false)}
        documentosSeleccionados={selectedDocs}
        destinatarioInicial={empresa?.email || ''}
        onSuccess={() => {
          clearSelection();
          refetch();
        }}
      />

      {/* Modal de Confirmación de Borrado */}
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="¿Eliminar documento?"
        message={`Estás a punto de eliminar físicamente "${docToDelete?.nombre_archivo}". Esta acción es permanente y no se puede deshacer.`}
        confirmText="Sí, eliminar"
        cancelText="Cancelar"
      />

      {/* Modal Nuevo Expediente de Inspección */}
      {isNuevaInspeccionOpen && (
        <NuevaInspeccionModal
          empresaId={empresaId}
          onClose={() => setIsNuevaInspeccionOpen(false)}
          onSuccess={() => refetch()}
        />
      )}

      {isSubirInspeccionOpen && (
        <SubirInspeccionModal
          empresaId={empresaId}
          onClose={() => setIsSubirInspeccionOpen(false)}
          onSuccess={() => refetch()}
        />
      )}
    </div >
  );
}

// Componente para una fila agrupada (Expediente de Alta)
function GroupedRow({ item, selectedDocs, toggleSelection, setPdfViewerDoc, handleVerDetalles, handleDeleteDocument, refetch }) {
  const [isExpanded, setIsExpanded] = React.useState(true);
  const docs = item.docs;
  const grupo = item.grupo;
  const isBaja = grupo.nombre.startsWith('Baja');

  // El nombre del empleado suele estar en el primer documento procesado
  const nombreEmpleado =
    docs.find(d => d.datos_extraidos?.nombre_trabajador)?.datos_extraidos?.nombre_trabajador ||
    docs.find(d => d.datos_extraidos?.nombre_empleado)?.datos_extraidos?.nombre_empleado ||
    grupo.descripcion?.replace(/^Expediente de (Baja|Alta) para /i, '') ||
    "Trabajador";


  const colorClass = isBaja ? 'orange' : 'emerald';
  const bgClass = isBaja ? 'bg-orange-50/30' : 'bg-emerald-50/30';
  const borderClass = isBaja ? 'border-l-orange-500' : 'border-l-emerald-500';
  const textClass = isBaja ? 'text-orange-700' : 'text-emerald-700';
  const badgeClass = isBaja ? 'bg-orange-100 text-orange-700' : 'bg-emerald-100 text-emerald-700';
  const iconBgClass = isBaja ? 'bg-orange-500' : 'bg-emerald-500';

  return (
    <>
      <tr className={`${bgClass} border-l-4 ${borderClass} hover:opacity-80 transition-colors`}>
        <td className="px-6 py-3">
          <button onClick={() => setIsExpanded(!isExpanded)} className={`p-1 rounded transition-colors ${isBaja ? 'hover:bg-orange-100 text-orange-600' : 'hover:bg-emerald-100 text-emerald-600'}`}>
            {isExpanded ? <ChevronLeft className="w-4 h-4 -rotate-90 transition-transform" /> : <ChevronLeft className="w-4 h-4 transition-transform" />}
          </button>
        </td>
        <td className="px-6 py-3" colSpan={3}>
          <div className="flex items-center gap-3">
            <div className={`${iconBgClass} text-white p-1.5 rounded-lg`}>
              <FolderPlus className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-black text-gray-900">Expediente de {isBaja ? 'Baja' : 'Alta'}</span>
                <span className={`px-2 py-0.5 ${badgeClass} text-[10px] font-bold rounded-full uppercase`}>
                  {docs.length} documentos
                </span>
              </div>
              <div className={`text-xs ${textClass} font-bold`}>👤 {nombreEmpleado}</div>
            </div>
          </div>
        </td>
        <td className="px-6 py-3 text-right">
          <span className="text-[10px] text-gray-400 font-medium italic">Varios documentos vinculados</span>
        </td>
      </tr>

      {isExpanded && docs.map((doc, idx) => {
        const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
        const isLast = idx === docs.length - 1;

        return (
          <tr
            key={doc.id}
            className={`transition-all group border-l-4 ${isSelected
              ? 'bg-blue-50 border-l-primary'
              : isBaja ? 'bg-white border-l-orange-400' : 'bg-white border-l-emerald-500'
              } ${!isLast ? 'border-b border-gray-50' : isBaja ? 'border-b-2 border-orange-100' : 'border-b-2 border-emerald-100'}`}
          >
            <td className="px-6 py-4 pl-12">
              <div
                className={`w-5 h-5 rounded flex items-center justify-center border transition-colors cursor-pointer ${isSelected ? 'bg-primary border-primary text-white' : 'bg-white border-gray-300 hover:border-primary'}`}
                onClick={(e) => toggleSelection(doc, e)}
              >
                {isSelected && <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
              </div>
            </td>
            <td className="px-6 py-4">
              <div className="flex items-center gap-3">
                <div className={`w-1 h-4 ${isBaja ? 'bg-orange-200' : 'bg-emerald-200'} rounded-full`} />
                <div className="flex flex-col min-w-0">
                  <button
                    onClick={() => setPdfViewerDoc(doc)}
                    className="text-sm font-bold text-gray-900 hover:text-primary transition-colors text-left truncate max-w-md"
                  >
                    {doc.nombre_archivo}
                  </button>
                  <span className="text-[10px] text-gray-400 font-medium">
                    {doc.datos_extraidos?.tipo_especifico || (isBaja ? 'Documento de Baja' : 'Documento de Alta')}
                  </span>
                </div>
              </div>
            </td>
            <td className="px-6 py-4 text-sm text-gray-500">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                {new Date(doc.fecha_creacion).toLocaleDateString()}
              </span>
            </td>
            <td className="px-6 py-4">
              <StatusLectura documento={doc} onActualizar={refetch} />
            </td>
            <td className="px-6 py-4 text-right">
              <div className="flex items-center justify-end gap-2 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleVerDetalles(doc)}
                  className="p-2 text-primary hover:bg-primary/10 rounded-lg transition-colors"
                  title="Ver Detalles"
                >
                  <Bot className="w-5 h-5" />
                </button>
                  <button
                    onClick={() => handleDownload(doc.id, doc.nombre_archivo)}
                    className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Descargar"
                  >
                    <Download className="w-5 h-5" />
                  </button>
                <button
                  onClick={() => handleDeleteDocument(doc)}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title="Eliminar"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </td>
          </tr>
        );
      })}
    </>
  );
}

// Componente para una tarjeta agrupada en Kanban (Expediente de Alta)
function GroupedKanbanCard({ item, col, selectedDocs, toggleSelection, setPdfViewerDoc, handleVerDetalles, handleDeleteDocument, setDocumentoParaGrupo }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const docs = item.docs;
  const grupo = item.grupo;
  const isBaja = grupo.nombre.startsWith('Baja');
  const nombreEmpleado =
    docs.find(d => d.datos_extraidos?.nombre_trabajador)?.datos_extraidos?.nombre_trabajador ||
    docs.find(d => d.datos_extraidos?.nombre_empleado)?.datos_extraidos?.nombre_empleado ||
    grupo.descripcion?.replace(/^Expediente de (Baja|Alta) para /i, '') ||
    "Trabajador";


  const colorClass = isBaja ? 'orange' : 'emerald';
  const bgClass = isBaja ? 'bg-orange-50/50' : 'bg-emerald-50/50';
  const borderClass = isBaja ? 'border-orange-200' : 'border-emerald-200';
  const indicatorClass = isBaja ? 'bg-orange-500' : 'bg-emerald-500';
  const badgeClass = isBaja ? 'bg-orange-500' : 'bg-emerald-500';
  const textClass = isBaja ? 'text-orange-700' : 'text-emerald-700';

  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData("docId", docs[0].id)} // Arrastrar el primero mueve todo el grupo
      className={`rounded-xl shadow-sm border transition-all cursor-grab active:cursor-grabbing group relative ${bgClass} ${borderClass} overflow-hidden`}
    >
      {/* Indicador de expediente */}
      <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${indicatorClass}`} />

      <div className="p-4 pl-5">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center gap-1.5">
            <span className={`px-2 py-0.5 ${badgeClass} text-white text-[9px] font-black rounded-full uppercase`}>
              Expediente {isBaja ? 'Baja' : 'Alta'}
            </span>
            <span className={`text-[10px] ${textClass} font-bold uppercase truncate max-w-[100px]`}>
              {grupo.nombre}
            </span>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className={`p-1 rounded transition-colors ${isBaja ? 'hover:bg-orange-100 text-orange-600' : 'hover:bg-emerald-100 text-emerald-600'}`}
          >
            {isExpanded ? <ChevronLeft className="w-4 h-4 -rotate-90" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        <div className="mb-3">
          <div className="text-sm font-black text-gray-900 leading-tight mb-1">
            {nombreEmpleado}
          </div>
          <p className="text-[10px] text-gray-500 font-medium">
            {docs.length} documentos vinculados
          </p>
        </div>

        {/* Lista de documentos si está expandido */}
        {isExpanded && (
          <div className="space-y-2 mb-4 bg-white/50 p-2 rounded-lg border border-emerald-100/50">
            {docs.map(doc => {
              const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
              return (
                <div key={doc.id} className="flex items-center justify-between gap-2 p-1.5 hover:bg-white rounded transition-colors group/item">
                  <div className="flex items-center gap-2 min-w-0">
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border transition-colors cursor-pointer shrink-0 ${isSelected ? 'bg-primary border-primary text-white' : 'bg-white border-gray-300'}`}
                      onClick={(e) => toggleSelection(doc, e)}
                    >
                      {isSelected && <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                    </div>
                    <button
                      onClick={() => setPdfViewerDoc(doc)}
                      className="text-[11px] font-bold text-gray-700 hover:text-primary truncate transition-colors text-left"
                    >
                      {doc.nombre_archivo}
                    </button>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover/item:opacity-100 transition-opacity">
                    <button onClick={() => setPdfViewerDoc(doc)} className="p-1 text-gray-400 hover:text-primary"><Eye className="w-3.5 h-3.5" /></button>
                    <button onClick={() => handleVerDetalles(doc)} className="p-1 text-gray-400 hover:text-primary"><Bot className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-gray-500 pt-2 border-t border-emerald-100/50">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" /> {new Date(docs[0].fecha_creacion).toLocaleDateString()}
          </span>

          <div className="flex items-center gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={(e) => { e.stopPropagation(); setDocumentoParaGrupo(docs[0]); }}
              className="p-1.5 hover:bg-emerald-100 rounded-lg text-emerald-600 transition-colors"
              title="Gestionar Grupo"
            >
              <FolderPlus className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); handleDeleteDocument(docs[0]); }}
              className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
              title="Eliminar Expediente"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Mapa de colores para grupos de inspección ───────────────────────────────
const INSPECCION_COLOR_MAP = {
  red:    { headerBg: 'from-red-600 to-red-700',       border: 'border-red-200',    rowHover: 'hover:bg-red-50/40',    Icon: ShieldAlert },
  blue:   { headerBg: 'from-blue-600 to-blue-700',     border: 'border-blue-200',   rowHover: 'hover:bg-blue-50/40',   Icon: FileSearch  },
  orange: { headerBg: 'from-orange-500 to-orange-600', border: 'border-orange-200', rowHover: 'hover:bg-orange-50/40', Icon: Banknote    },
  purple: { headerBg: 'from-purple-600 to-purple-700', border: 'border-purple-200', rowHover: 'hover:bg-purple-50/40', Icon: Scale       },
  green:  { headerBg: 'from-green-600 to-green-700',   border: 'border-green-200',  rowHover: 'hover:bg-green-50/40',  Icon: CheckCircle },
  yellow: { headerBg: 'from-yellow-500 to-yellow-600', border: 'border-yellow-200', rowHover: 'hover:bg-yellow-50/40', Icon: AlertCircle },
  pink:   { headerBg: 'from-pink-500 to-pink-600',     border: 'border-pink-200',   rowHover: 'hover:bg-pink-50/40',   Icon: FileText    },
};

function InspeccionGrupoCard({
  grupo, docs, selectedDocs, toggleSelection,
  setPdfViewerDoc, handleVerDetalles, handleDeleteDocument,
  handleDownload, setDocumentoParaGrupo, refetch
}) {
  const [isExpanded, setIsExpanded] = React.useState(true);
  const [showEmailModal, setShowEmailModal] = React.useState(false);
  const [aplazamientoState, setAplazamientoState] = React.useState({});
  const [expandedAplaz, setExpandedAplaz] = React.useState({});
  const [editingName, setEditingName] = React.useState(false);
  const [nombreEdit, setNombreEdit] = React.useState(grupo.nombre);
  const colors = INSPECCION_COLOR_MAP[grupo.color] || INSPECCION_COLOR_MAP.blue;
  const TypeIcon = colors.Icon;

  const handleSaveName = async () => {
    if (!nombreEdit.trim() || nombreEdit === grupo.nombre) { setEditingName(false); return; }
    try {
      await axios.patch(`/api/grupos-documentos/${grupo.id}`, { nombre: nombreEdit }, { withCredentials: true });
      refetch();
    } catch { setNombreEdit(grupo.nombre); }
    setEditingName(false);
  };

  const handleAplazamiento = async (doc) => {
    if (aplazamientoState[doc.id] === 'loading') return;
    setAplazamientoState(prev => ({ ...prev, [doc.id]: 'loading' }));
    try {
      await axios.post(`/api/documentos/${doc.id}/procesar-aplazamiento`, {}, { withCredentials: true });
      setAplazamientoState(prev => ({ ...prev, [doc.id]: 'success' }));
      refetch();
      setTimeout(() => setAplazamientoState(prev => { const n = {...prev}; delete n[doc.id]; return n; }), 3000);
    } catch {
      setAplazamientoState(prev => ({ ...prev, [doc.id]: 'error' }));
      setTimeout(() => setAplazamientoState(prev => { const n = {...prev}; delete n[doc.id]; return n; }), 3000);
    }
  };

  const handleDownloadZip = () => {
    const link = document.createElement('a');
    link.href = `/api/grupos-documentos/${grupo.id}/download-zip`;
    link.setAttribute('download', `${grupo.nombre}.zip`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  return (
    <div className={`bg-white rounded-2xl border ${colors.border} shadow-sm overflow-hidden`}>
      {/* Header del expediente */}
      <div className={`bg-gradient-to-r ${colors.headerBg} px-5 py-4`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center shrink-0">
              <TypeIcon className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0 flex items-center gap-2">
              {editingName ? (
                <input
                  autoFocus
                  value={nombreEdit}
                  onChange={e => setNombreEdit(e.target.value)}
                  onBlur={handleSaveName}
                  onKeyDown={e => { if (e.key === 'Enter') handleSaveName(); if (e.key === 'Escape') { setNombreEdit(grupo.nombre); setEditingName(false); } }}
                  className="bg-white/20 text-white font-bold text-base rounded px-2 py-0.5 outline-none border border-white/50 min-w-0 w-48"
                />
              ) : (
                <h3
                  className="text-white font-bold text-base leading-tight truncate cursor-pointer hover:underline"
                  title="Clic para editar nombre"
                  onClick={() => setEditingName(true)}
                >
                  {grupo.nombre}
                </h3>
              )}
              {grupo.descripcion && !editingName && (
                <p className="text-white/65 text-xs mt-0.5">{grupo.descripcion}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="px-2.5 py-1 bg-white/20 text-white text-xs font-bold rounded-full">
              {docs.length} {docs.length === 1 ? 'doc' : 'docs'}
            </span>
            <button onClick={handleDownloadZip} className="p-1.5 rounded-lg bg-white/15 hover:bg-white/30 transition-colors" title="Descargar ZIP">
              <Download className="w-4 h-4 text-white" />
            </button>
            <button onClick={() => setShowEmailModal(true)} className="p-1.5 rounded-lg bg-white/15 hover:bg-white/30 transition-colors" title="Enviar por correo">
              <Mail className="w-4 h-4 text-white" />
            </button>
            <button
              onClick={async () => {
                if (!confirm(`¿Eliminar el expediente "${grupo.nombre}"? Los documentos no se borrarán.`)) return;
                try {
                  await axios.delete(`/api/grupos-documentos/${grupo.id}`, { withCredentials: true });
                  refetch();
                } catch { alert('Error al eliminar el expediente'); }
              }}
              className="p-1.5 rounded-lg bg-white/15 hover:bg-red-500/70 transition-colors"
              title="Eliminar expediente"
            >
              <Trash2 className="w-4 h-4 text-white" />
            </button>
            <button onClick={() => setIsExpanded(!isExpanded)} className="p-1.5 rounded-lg bg-white/15 hover:bg-white/30 transition-colors">
              <ChevronLeft className={`w-4 h-4 text-white transition-transform duration-200 ${isExpanded ? '-rotate-90' : 'rotate-0'}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Lista de documentos */}
      {isExpanded && (
        <div className="divide-y divide-gray-50">
          {docs.map((doc, idx) => {
            const isSelected = selectedDocs.some(d => d.doc_id === doc.id);
            const isAplazExpanded = expandedAplaz[doc.id];
            const detalleLiq = doc.datos_extraidos?.detalle_liquidacion || [];
            return (
              <div key={doc.id} className="border-b border-gray-50 last:border-0">
              <div
                className={`group flex items-center gap-4 px-5 py-3.5 transition-colors ${colors.rowHover} ${isSelected ? 'bg-blue-50' : ''}`}
              >
                {/* Checkbox */}
                <div
                  className={`w-4 h-4 rounded flex items-center justify-center border cursor-pointer shrink-0 transition-colors ${isSelected ? 'bg-primary border-primary text-white' : 'border-gray-300 hover:border-primary bg-white'}`}
                  onClick={(e) => toggleSelection(doc, e)}
                >
                  {isSelected && <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                </div>
                {/* Número */}
                <span className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center text-[10px] font-bold text-gray-500 shrink-0">{idx + 1}</span>
                {/* Icono PDF */}
                <div className="p-1.5 bg-gray-100 rounded-lg shrink-0"><FileText className="w-4 h-4 text-gray-500" /></div>
                {/* Nombre */}
                <button onClick={() => setPdfViewerDoc(doc)} className="text-sm font-medium text-gray-800 hover:text-primary transition-colors truncate flex-1 text-left">
                  {doc.nombre_archivo}
                </button>
                {/* Fecha */}
                <span className="text-xs text-gray-400 shrink-0 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {new Date(doc.fecha_creacion).toLocaleDateString()}
                </span>
                {/* Estado lectura */}
                <div className="shrink-0">
                  <StatusLectura documento={doc} onActualizar={refetch} />
                </div>
                {/* Acciones */}
                <div className="flex items-center gap-1 shrink-0">
                  <button onClick={() => handleDownload(doc.id, doc.nombre_archivo)} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="Descargar">
                    <Download className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleVerDetalles(doc)} className="p-1.5 text-gray-400 hover:text-primary hover:bg-primary/10 rounded-lg transition-colors" title="Ver detalles">
                    <Bot className="w-4 h-4" />
                  </button>
                  {/* Aplazamiento OCR button */}
                  {doc.datos_extraidos?.is_aplazamiento ? (
                    <button
                      onClick={() => setExpandedAplaz(prev => ({ ...prev, [doc.id]: !prev[doc.id] }))}
                      className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold bg-amber-100 text-amber-700 rounded-full shrink-0 hover:bg-amber-200 transition-colors"
                      title="Ver/ocultar detalle de aplazamiento"
                    >
                      ⚡ Aplazamiento {isAplazExpanded ? '▲' : '▼'}
                    </button>
                  ) : (
                    <button
                      onClick={() => handleAplazamiento(doc)}
                      disabled={aplazamientoState[doc.id] === 'loading'}
                      className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold transition-all shrink-0 ${
                        aplazamientoState[doc.id] === 'success' ? 'text-green-700 bg-green-50 opacity-100' :
                        aplazamientoState[doc.id] === 'error'   ? 'text-red-600 bg-red-50 opacity-100' :
                        aplazamientoState[doc.id] === 'loading' ? 'text-amber-600 bg-amber-50 opacity-100' :
                        'text-amber-600 bg-amber-50 hover:bg-amber-100 opacity-0 group-hover:opacity-100'
                      }`}
                      title="Detectar y vincular como aplazamiento"
                    >
                      {aplazamientoState[doc.id] === 'loading' ? (
                        <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Procesando...</>
                      ) : aplazamientoState[doc.id] === 'success' ? (
                        <><CheckCircle className="w-3.5 h-3.5" /> ¡Detectado!</>
                      ) : aplazamientoState[doc.id] === 'error' ? (
                        <><AlertCircle className="w-3.5 h-3.5" /> Error</>
                      ) : (
                        <><Zap className="w-3.5 h-3.5" /> Aplazamiento</>
                      )}
                    </button>
                  )}
                  <button onClick={() => handleDeleteDocument(doc)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Eliminar">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Acordeón de detalle de aplazamiento */}
              {doc.datos_extraidos?.is_aplazamiento && isAplazExpanded && (
                <div className="bg-amber-50 px-5 py-4 border-t border-amber-100">
                  {detalleLiq.length === 0 ? (
                    <p className="text-xs text-gray-500 italic">Sin datos de liquidación extraídos.</p>
                  ) : (
                    <div className="space-y-3">
                      {detalleLiq.map((liq, liqIdx) => (
                        <div key={liqIdx} className="border rounded-lg overflow-hidden bg-white shadow-sm">
                          <div className="bg-blue-50 px-3 py-1.5 border-b flex items-center gap-3">
                            <span className="font-mono text-xs font-bold text-blue-800">{liq.numero_liquidacion}</span>
                            {liq.concepto && <span className="text-xs text-blue-600">{liq.concepto}</span>}
                            {liq.fecha_intereses && <span className="text-xs text-gray-400 ml-auto">Int. desde: {liq.fecha_intereses}</span>}
                          </div>
                          <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                              <thead className="bg-gray-50">
                                <tr>
                                  <th className="px-2 py-1 text-center font-semibold border-b border-r text-gray-600">#</th>
                                  <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Principal</th>
                                  <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Recargo</th>
                                  <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Total Deuda</th>
                                  <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Intereses</th>
                                  <th className="px-2 py-1 text-right font-semibold border-b border-r text-gray-600">Total Plazo</th>
                                  <th className="px-2 py-1 text-center font-semibold border-b text-gray-600">Vencimiento</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(liq.plazos || []).map((p, pIdx) => (
                                  <tr key={pIdx} className="border-t hover:bg-blue-50">
                                    <td className="px-2 py-1 text-center border-r text-gray-400">{pIdx + 1}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(p.importe_principal || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(p.recargo_apremio || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(p.importe_total_deuda || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r text-orange-600">€{(p.importe_intereses || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r font-semibold">€{(p.importe_total_plazo || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-center font-medium text-blue-700">{p.fecha_vencimiento || '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                              {liq.subtotal && (
                                <tfoot className="bg-gray-100 font-semibold border-t-2">
                                  <tr>
                                    <td className="px-2 py-1 text-center border-r text-gray-400">Sub</td>
                                    <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_principal || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.recargo_apremio || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_total_deuda || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r text-orange-600">€{(liq.subtotal.importe_intereses || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-right border-r">€{(liq.subtotal.importe_total_plazo || 0).toFixed(2)}</td>
                                    <td className="px-2 py-1 text-center text-gray-400">Subtotal</td>
                                  </tr>
                                </tfoot>
                              )}
                            </table>
                          </div>
                        </div>
                      ))}
                      {(() => {
                        const totalGeneral = detalleLiq.reduce((sum, liq) =>
                          sum + (liq.plazos || []).reduce((s, p) => s + (p.importe_total_plazo || 0), 0), 0);
                        return (
                          <div className="flex justify-end pt-1">
                            <div className="bg-gray-800 text-white px-5 py-2 rounded-lg text-sm font-bold">
                              TOTAL GENERAL: €{totalGeneral.toFixed(2)}
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              )}
              </div>
            );
          })}
        </div>
      )}

      {showEmailModal && (
        <EnviarEmailGrupoModal grupo={{ ...grupo, documentos: docs }} onClose={() => setShowEmailModal(false)} />
      )}
    </div>
  );
}

// Componente auxiliar para mostrar badges de grupos
function GrupoBadgesWrapper({ documentoId }) {
  const { data: grupos } = useGruposDeDocumento(documentoId);

  if (!grupos || grupos.length === 0) return null;

  return (
    <div className="mb-2">
      <GrupoBadge grupos={grupos} />
    </div>
  );
}