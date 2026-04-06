// frontend/src/components/EmpresasDashboard.jsx
import React, { useState, useEffect, useCallback, useRef as useRefReact } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useEmpresasStats } from '../hooks/useEmpresas';
import {
  Building2, Search, Filter, Upload, AlertTriangle, FileSpreadsheet,
  Loader2, FileText, Clock, CheckCircle, RefreshCw, FolderOpen, Edit, FileDown, ChevronDown, X, Megaphone, FileSearch, Eye, EyeOff
} from 'lucide-react';
import { useRef } from 'react';
import CrearEmpresaModal from './CrearEmpresaModal';
import EditarEmpresaModal from './EditarEmpresaModal';
import ImportarEmpresasModal from './ImportarEmpresasModal';
import ExportModal from './ExportModal';
import { useToast } from './Toast';
import { useGrupos } from '../hooks/useGruposEmpresas';
import axios from 'axios';
import MuroComunicados from './MuroComunicados';

export default function EmpresasDashboard() {
  // ✅ REACT QUERY: Reemplaza useState + useEffect
  const { data, isLoading, error: queryError, refetch } = useEmpresasStats();
  const { user } = useAuth();
  const esInvitado = user?.departamento === 'Invitado';
  const empresas = data?.empresas || [];

  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filtroPendientes, setFiltroPendientes] = useState(false);
  const [filtroGrupo, setFiltroGrupo] = useState('todos');

  // Búsqueda de documentos por OCR
  const [docsResultados, setDocsResultados] = useState([]);
  const [docsBuscando, setDocsBuscando] = useState(false);
  const [docsBusquedaActiva, setDocsBusquedaActiva] = useState(false);
  const debounceRef = useRefReact(null);

  // Estados para el selector de grupos personalizado (Combobox)
  const [isGroupDropdownOpen, setIsGroupDropdownOpen] = useState(false);
  const [groupSearchTerm, setGroupSearchTerm] = useState('');

  const { data: gruposData, isLoading: isLoadingGrupos } = useGrupos();
  const grupos = gruposData || [];

  const [noClasificadosCount, setNoClasificadosCount] = useState(0);
  const [isScanning, setIsScanning] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [empresaParaEditar, setEmpresaParaEditar] = useState(null);

  const navigate = useNavigate();
  const { showToast, ToastContainer } = useToast();
  const groupDropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (groupDropdownRef.current && !groupDropdownRef.current.contains(event.target)) {
        setIsGroupDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    cargarNoClasificados();
  }, []);

  const cargarNoClasificados = async () => {
    try {
      const response = await axios.get('/api/archivos-no-clasificados', { withCredentials: true });
      if (response.data.success) {
        setNoClasificadosCount(response.data.files.length);
      }
    } catch (err) {
      console.error("Error al cargar archivos no clasificados", err);
    }
  };

  const handleScanAndUpdate = async () => {
    setIsScanning(true);
    setError(null);
    try {
      const scanResponse = await axios.post('/api/escanear-raiz', {}, { withCredentials: true });
      showToast(scanResponse.data.mensaje, 'success');
      await refetch(); // ✅ Usar refetch de React Query
      await cargarNoClasificados();
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Error al escanear la carpeta raíz';
      showToast(errorMsg, 'error');
      setError(errorMsg);
      console.error(err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleToggleStatus = async (empresa) => {
    try {
      const response = await axios.post(`/api/empresas/${empresa.id}/toggle-status`, {}, { withCredentials: true });
      if (response.data.success) {
        showToast(response.data.message, 'success');
        refetch();
      }
    } catch (err) {
      showToast('Error al cambiar el estado de la empresa', 'error');
      console.error(err);
    }
  };

  // ✅ Filtrado robusto con defensive checks para evitar crash (pantalla blanca)
  const empresasFiltradas = React.useMemo(() => {
    const term = searchTerm.toLowerCase().trim();
    const grupoIdInt = filtroGrupo !== 'todos' ? parseInt(filtroGrupo) : null;

    return empresas.filter(empresa => {
      // Búsqueda por nombre o NIF (con safe access)
      const nombreMatch = (empresa.nombre || '').toLowerCase().includes(term);
      const nifMatch = (empresa.nif || '').toLowerCase().includes(term);
      const matchSearch = nombreMatch || nifMatch;

      // Filtro de Pendientes
      const matchFiltroPendientes = !filtroPendientes ||
        (empresa.notificaciones_pendientes_ia > 0 || empresa.notificaciones_pendientes_tarea > 0);

      // Filtro de Grupo
      const matchGrupo = !grupoIdInt || empresa.grupo_id === grupoIdInt;

      return matchSearch && matchFiltroPendientes && matchGrupo;
    });
  }, [empresas, searchTerm, filtroPendientes, filtroGrupo]);

  const { empresasActivas, empresasInactivas } = React.useMemo(() => {
    return {
      empresasActivas: empresasFiltradas.filter(e => e.activa !== false),
      empresasInactivas: empresasFiltradas.filter(e => e.activa === false)
    };
  }, [empresasFiltradas]);

  // Búsqueda de documentos OCR: se activa cuando no hay empresa que coincida
  useEffect(() => {
    const term = searchTerm.trim();

    // Cancelar debounce anterior
    if (debounceRef.current) clearTimeout(debounceRef.current);

    // Solo buscar si hay término suficiente Y no hay empresa coincidente
    if (term.length >= 3 && empresasFiltradas.length === 0) {
      setDocsBuscando(true);
      setDocsBusquedaActiva(true);
      debounceRef.current = setTimeout(async () => {
        try {
          const resp = await axios.get('/api/documentos/buscar', {
            params: { q: term, per_page: 10 },
            withCredentials: true,
          });
          setDocsResultados(resp.data.resultados || []);
        } catch (e) {
          setDocsResultados([]);
        } finally {
          setDocsBuscando(false);
        }
      }, 400);
    } else {
      // Resetear si hay resultados de empresa o término corto
      setDocsBusquedaActiva(false);
      setDocsResultados([]);
      setDocsBuscando(false);
    }

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [searchTerm, empresasFiltradas.length]);

  // Estadísticas Globales
  const totalEmpresas = empresas.length;
  const totalDocumentos = empresas.reduce((acc, emp) => acc + (emp.total_documentos || 0), 0);
  const totalPendientesIA = empresas.reduce((acc, emp) => acc + (emp.notificaciones_pendientes_ia || 0), 0);
  const totalPendientesTarea = empresas.reduce((acc, emp) => acc + (emp.notificaciones_pendientes_tarea || 0), 0);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <>
      <ToastContainer />
      <div className="space-y-6">
        {/* Header y Botones */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Mis Empresas</h1>
            <p className="text-gray-600 mt-1">Gestiona todas tus empresas y documentos</p>
          </div>

          <div className="flex items-center gap-3">
            {/* Botón Inbox - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={() => navigate('/no-clasificados')}
                className={`px-4 py-2 rounded-lg transition flex items-center gap-2 text-sm font-medium shadow-sm
                  ${noClasificadosCount > 0
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-white text-gray-600 border border-gray-300 hover:bg-gray-50'
                  }`}
              >
                {noClasificadosCount > 0 ? <AlertTriangle className="w-4 h-4" /> : <FolderOpen className="w-4 h-4" />}
                Inbox ({noClasificadosCount})
              </button>
            )}

            {/* Botón Nueva Empresa - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition 
                         flex items-center gap-2 text-sm font-medium shadow-sm"
              >
                <Building2 className="w-4 h-4" />
                Nueva
              </button>
            )}

            {/* Botón Importar Excel - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={() => setShowImportModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition 
                         flex items-center gap-2 text-sm font-medium shadow-sm"
                title="Importar empresas desde Excel"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Excel
              </button>
            )}

            {/* Botón Importar PDFs - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={() => navigate('/importar')}
                className="px-4 py-2 bg-primary text-gray-900 rounded-lg hover:bg-primary-hover transition 
                         flex items-center gap-2 text-sm font-medium shadow-sm"
                title="Importar PDFs de nóminas, seguros sociales, etc."
              >
                <Upload className="w-4 h-4" />
                PDFs
              </button>
            )}

            {/* Botón Escanear - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={handleScanAndUpdate}
                disabled={isScanning}
                className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition 
                         flex items-center gap-2 text-sm font-medium shadow-sm disabled:opacity-50"
              >
                {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Escanear
              </button>
            )}

            {/* Botón Exportar - Ocultar para invitados */}
            {!esInvitado && (
              <button
                onClick={() => setShowExportModal(true)}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition 
                         flex items-center gap-2 text-sm font-medium shadow-sm"
                title="Exportar documentos"
              >
                <FileDown className="w-4 h-4" />
                Exportar
              </button>
            )}
          </div>
        </div>

        {/* ⭐ MURO DE COMUNICADOS - Solo visible para Invitados (Clientes) */}
        {esInvitado && <MuroComunicados />}

        {/* Tarjetas de Estadísticas Globales */}
        {!esInvitado && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            {/* Card 1: Muro de Comunicados (Acceso Rápido) */}
            <div
              onClick={() => navigate('/admin/comunicados')}
              className="bg-white rounded-xl p-6 shadow-sm border border-orange-100 cursor-pointer hover:shadow-md transition-all active:scale-[0.98] group relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-bold text-orange-600 uppercase tracking-wider">Muro de Comunicados</p>
                  <p className="text-xs text-gray-500 mt-1">Anuncios y avisos importantes</p>
                </div>
                <div className="p-3 bg-orange-100 rounded-lg group-hover:bg-orange-200 transition-colors">
                  <Megaphone className="w-6 h-6 text-orange-600" />
                </div>
              </div>
              {/* Decoración sutil */}
              <div className="absolute top-0 right-0 w-16 h-16 bg-orange-50 -mr-8 -mt-8 rounded-full opacity-50 group-hover:scale-110 transition-transform"></div>
            </div>

            {/* Card 2: Pendientes IA (Mesa de Trabajo) */}
            <div
              onClick={() => navigate('/mesa-trabajo')}
              className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 cursor-pointer hover:shadow-md transition-shadow active:scale-[0.98] group"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Pendientes / Mesa de Trabajo</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{totalPendientesIA}</p>
                </div>
                <div className="p-3 bg-yellow-100 rounded-lg group-hover:bg-yellow-200 transition-colors">
                  <Clock className="w-6 h-6 text-yellow-600" />
                </div>
              </div>
            </div>

            {/* Card 3: Pendientes Tarea */}
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 group">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Pendientes Tareas</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{totalPendientesTarea}</p>
                </div>
                <div className="p-3 bg-green-100 rounded-lg group-hover:bg-green-200 transition-colors">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bloque de Control Consolidado (Buscador y Filtros) */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6">
          <div className="p-4 sm:p-6 lg:p-5 flex flex-col lg:flex-row items-center gap-4">
            {/* Buscador de Empresas (Left) - Grow */}
            <div className="flex-1 w-full relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5 pointer-events-none" />
              <input
                type="text"
                placeholder="Busca empresa por nombre, NIF, autónomo, cuenta cotización..."
                className="w-full pl-12 pr-10 py-3.5 bg-gray-50/50 border border-gray-100 rounded-xl focus:bg-white focus:ring-4 focus:ring-primary/10 focus:border-primary transition-all text-sm font-semibold shadow-xs"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-300 hover:text-red-500 rounded-lg transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>

            {/* Filtros a la derecha */}
            <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
              {/* Selector de Grupos Buscable */}
              <div className="relative min-w-[240px] flex-1 lg:flex-none" ref={groupDropdownRef}>
                <button
                  onClick={() => setIsGroupDropdownOpen(!isGroupDropdownOpen)}
                  className={`w-full flex items-center justify-between gap-3 px-4 py-3.5 rounded-xl border font-bold text-sm transition-all
                    ${isGroupDropdownOpen || filtroGrupo !== 'todos'
                      ? 'border-primary bg-primary/5 text-primary shadow-sm'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                    }`}
                >
                  <div className="flex items-center gap-2 truncate text-xs sm:text-sm">
                    <Filter className="w-4 h-4 opacity-70" />
                    <span className="truncate">
                      {filtroGrupo === 'todos'
                        ? 'Todas las agrupaciones'
                        : grupos.find(g => g.id.toString() === filtroGrupo.toString())?.nombre || 'Grupo...'}
                    </span>
                  </div>
                  <ChevronDown className={`w-4 h-4 opacity-50 transition-transform duration-300 ${isGroupDropdownOpen ? 'rotate-180 opacity-100' : ''}`} />
                </button>

                {isGroupDropdownOpen && (
                  <div className="absolute top-full right-0 w-full lg:w-80 mt-2 bg-white rounded-2xl shadow-2xl border border-gray-100 z-[200] animate-in fade-in slide-in-from-top-2 duration-200 overflow-hidden ring-1 ring-black/5 light-mode-dropdown">
                    <div className="p-3 bg-gray-50/50 border-b border-gray-100">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <input
                          type="text"
                          placeholder="Filtra grupos..."
                          className="w-full pl-9 pr-3 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all shadow-xs"
                          value={groupSearchTerm}
                          onChange={(e) => setGroupSearchTerm(e.target.value)}
                          autoFocus
                        />
                      </div>
                    </div>
                    <div className="max-h-64 overflow-y-auto p-1.5 custom-scrollbar bg-white">
                      <button
                        onClick={() => {
                          setFiltroGrupo('todos');
                          setIsGroupDropdownOpen(false);
                        }}
                        style={{
                          width: '100%',
                          textAlign: 'left',
                          padding: '10px 12px',
                          borderRadius: '12px',
                          fontSize: '14px',
                          marginBottom: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          backgroundColor: filtroGrupo === 'todos' ? '#f97316' : 'transparent',
                          color: filtroGrupo === 'todos' ? '#ffffff' : '#111827',
                          fontWeight: filtroGrupo === 'todos' ? 'bold' : 'normal',
                          border: 'none',
                          cursor: 'pointer'
                        }}
                      >
                        <Building2 style={{ width: '16px', height: '16px', color: filtroGrupo === 'todos' ? '#ffffff' : '#4b5563' }} />
                        <span style={{ color: filtroGrupo === 'todos' ? '#ffffff' : '#111827', fontWeight: filtroGrupo === 'todos' ? 'bold' : 'normal' }}>
                          Todas
                        </span>
                      </button>

                      {grupos
                        .filter(g => g.nombre.toLowerCase().includes(groupSearchTerm.toLowerCase()))
                        .map(g => (
                          <button
                            key={g.id}
                            onClick={() => {
                              setFiltroGrupo(g.id);
                              setIsGroupDropdownOpen(false);
                            }}
                            style={{
                              width: '100%',
                              textAlign: 'left',
                              padding: '10px 12px',
                              borderRadius: '12px',
                              fontSize: '14px',
                              marginBottom: '4px',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '10px',
                              backgroundColor: filtroGrupo.toString() === g.id.toString() ? '#f97316' : 'transparent',
                              color: filtroGrupo.toString() === g.id.toString() ? '#ffffff' : '#111827',
                              fontWeight: filtroGrupo.toString() === g.id.toString() ? 'bold' : 'normal',
                              border: 'none',
                              cursor: 'pointer'
                            }}
                          >
                            <FolderOpen style={{ width: '16px', height: '16px', color: filtroGrupo.toString() === g.id.toString() ? '#ffffff' : '#4b5563', flexShrink: 0 }} />
                            <span style={{
                              color: filtroGrupo.toString() === g.id.toString() ? '#ffffff' : '#111827',
                              fontWeight: filtroGrupo.toString() === g.id.toString() ? 'bold' : 'normal',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              flex: 1
                            }}>
                              {g.nombre}
                            </span>
                          </button>
                        ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Filtro de Pendientes */}
              <button
                onClick={() => setFiltroPendientes(!filtroPendientes)}
                className={`px-5 py-3.5 rounded-xl text-sm font-bold transition-all flex items-center gap-2 border shadow-sm
                  ${filtroPendientes
                    ? 'bg-orange-600 border-orange-600 text-white shadow-orange-100'
                    : 'bg-white border-gray-200 text-gray-700 hover:border-orange-200 hover:text-orange-600'
                  }`}
              >
                <AlertTriangle className={`w-4 h-4 ${filtroPendientes ? 'animate-pulse' : ''}`} />
                <span className="hidden sm:inline">Pendientes</span>
                <span className="sm:hidden">Pend.</span>
              </button>

              {/* Limpiar */}
              {(searchTerm || filtroGrupo !== 'todos' || filtroPendientes) && (
                <button
                  onClick={() => {
                    setSearchTerm('');
                    setFiltroGrupo('todos');
                    setFiltroPendientes(false);
                  }}
                  className="p-3.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all border border-transparent hover:border-red-100"
                  title="Limpiar filtros"
                >
                  <RefreshCw className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Lista de empresas */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
            {error}
          </div>
        )}

        {empresasFiltradas.length === 0 ? (
          <div>
            {/* Spinner / resultados de documentos OCR */}
            {docsBuscando && (
              <div className="bg-white rounded-xl p-8 text-center shadow-sm border border-gray-100">
                <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Buscando en documentos...</p>
              </div>
            )}

            {!docsBuscando && docsBusquedaActiva && docsResultados.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2 px-1 mb-4">
                  <FileSearch className="w-5 h-5 text-primary" />
                  <p className="text-sm font-semibold text-gray-700">
                    {docsResultados.length} documento{docsResultados.length !== 1 ? 's' : ''} encontrado{docsResultados.length !== 1 ? 's' : ''} con <span className="text-primary">&ldquo;{searchTerm}&rdquo;</span>
                  </p>
                </div>
                {docsResultados.map(doc => (
                  <div
                    key={doc.id}
                    onClick={() => navigate(`/empresa/${doc.empresa_id}`)}
                    className="bg-white rounded-xl px-5 py-4 shadow-sm border border-gray-100 cursor-pointer hover:shadow-md hover:border-primary-light transition-all group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="p-2 bg-orange-50 rounded-lg mt-0.5 shrink-0">
                          <FileText className="w-4 h-4 text-primary" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-gray-900 truncate group-hover:text-primary transition-colors">
                            {doc.empresa_nombre || 'Empresa desconocida'}
                          </p>
                          <p className="text-xs text-gray-500 truncate mt-0.5">{doc.nombre_archivo}</p>
                          {doc.tipo_documento && (
                            <span className="inline-block mt-1 px-2 py-0.5 bg-gray-100 text-gray-600 text-[10px] font-bold rounded-full uppercase tracking-wide">
                              {doc.tipo_documento}
                            </span>
                          )}
                          {doc.fragmento && (
                            <p className="mt-2 text-xs text-gray-500 leading-relaxed font-mono bg-gray-50 rounded px-2 py-1.5 border border-gray-100">
                              {doc.fragmento}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs text-gray-400">
                          {doc.fecha_creacion ? new Date(doc.fecha_creacion).toLocaleDateString('es-ES') : ''}
                        </p>
                        {doc.importe > 0 && (
                          <p className="text-sm font-bold text-gray-700 mt-1">{doc.importe.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!docsBuscando && docsBusquedaActiva && docsResultados.length === 0 && (
              <div className="bg-white rounded-xl p-12 text-center shadow-sm border border-gray-100">
                <FileSearch className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Sin resultados</h3>
                <p className="text-gray-500 text-sm">No se encontraron empresas ni documentos con &ldquo;{searchTerm}&rdquo;</p>
              </div>
            )}

            {!docsBusquedaActiva && (
              <div className="bg-white rounded-xl p-12 text-center shadow-sm border border-gray-100">
                <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No se encontraron empresas</h3>
                <p className="text-gray-600">
                  {searchTerm || filtroPendientes
                    ? 'Escribe al menos 3 caracteres para buscar también en documentos'
                    : 'Haz clic en "Escanear" para importar empresas'}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-10">
            {/* Sección Empresas Activas */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {empresasActivas.map(empresa => (
                <div
                  key={empresa.id}
                  onClick={() => navigate(`/empresa/${empresa.id}`)}
                  className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 
                           hover:shadow-md hover:border-primary-light transition-all cursor-pointer
                           group relative overflow-hidden"
                >
                  {/* Encabezado */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="p-3 bg-linear-to-br from-orange-100 to-red-100 rounded-lg
                                    group-hover:from-orange-200 group-hover:to-red-200 transition-colors">
                        <Building2 className="w-6 h-6 text-primary" />
                      </div>

                      {/* Botones de acción */}
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEmpresaParaEditar(empresa);
                            setShowEditModal(true);
                          }}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          title="Editar empresa"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleStatus(empresa);
                          }}
                          className="p-2 text-gray-500 hover:bg-gray-50 rounded-lg transition"
                          title="Desactivar empresa"
                        >
                          <EyeOff className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 text-green-700 text-[10px] font-bold uppercase rounded-full border border-green-100">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                        ACTIVA
                      </div>
                      {/* Badge de Pendientes */}
                      {(empresa.notificaciones_pendientes_ia > 0 || empresa.notificaciones_pendientes_tarea > 0) && (
                        <span className="px-2 py-1 bg-red-100 text-red-600 text-xs font-bold uppercase rounded-full border border-red-100 animate-pulse">
                          Pendientes
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Título y NIF */}
                  <h3 className="text-lg font-bold text-gray-900 mb-1 group-hover:text-primary 
                               transition-colors truncate pr-2">
                    {empresa.nombre}
                  </h3>
                  <p className="text-sm text-gray-500 mb-5 font-mono">
                    {empresa.nif || 'Sin NIF'}
                  </p>

                  {/* Footer de Estadísticas */}
                  <div className="grid grid-cols-3 gap-2 pt-4 border-t border-gray-100">
                    <div className="text-center">
                      <p className="text-lg font-bold text-gray-900">
                        {empresa.total_documentos || 0}
                      </p>
                      <p className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">
                        Docs
                      </p>
                    </div>

                    <div className="text-center border-l border-gray-100">
                      <p className="text-lg font-bold text-yellow-600">
                        {empresa.notificaciones_pendientes_ia || 0}
                      </p>
                      <p className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">
                        IA
                      </p>
                    </div>

                    <div className="text-center border-l border-gray-100">
                      <p className="text-lg font-bold text-primary">
                        {empresa.notificaciones_pendientes_tarea || 0}
                      </p>
                      <p className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">
                        Tareas
                      </p>
                    </div>
                  </div>

                  {/* Decoración Hover */}
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-linear-to-r from-orange-500 to-red-500 
                                transform scale-x-0 group-hover:scale-x-100 transition-transform origin-left"></div>
                </div>
              ))}
            </div>

            {/* Sección Empresas Inactivas */}
            {empresasInactivas.length > 0 && (
              <div className="pt-8 border-t border-gray-100">
                <div className="flex items-center gap-3 mb-6">
                  <EyeOff className="w-5 h-5 text-gray-400" />
                  <h2 className="text-xl font-bold text-gray-400 uppercase tracking-wider">Empresas Inactivas</h2>
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs font-bold rounded-full">
                    {empresasInactivas.length}
                  </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 opacity-60 grayscale-[0.5] hover:opacity-100 hover:grayscale-0 transition-all">
                  {empresasInactivas.map(empresa => (
                    <div
                      key={empresa.id}
                      onClick={() => navigate(`/empresa/${empresa.id}`)}
                      className="bg-gray-50 rounded-xl p-6 shadow-sm border border-gray-200 
                               hover:shadow-md transition-all cursor-pointer group"
                    >
                      {/* Encabezado Inactiva */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <div className="p-3 bg-gray-200 rounded-lg">
                            <Building2 className="w-6 h-6 text-gray-400" />
                          </div>
                          
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleToggleStatus(empresa);
                              }}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition"
                              title="Reactivar empresa"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 px-2 py-1 bg-red-50 text-red-700 text-[10px] font-bold uppercase rounded-full border border-red-100">
                          <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                          INACTIVA
                        </div>
                      </div>

                      <h3 className="text-lg font-bold text-gray-500 mb-1 truncate pr-2">
                        {empresa.nombre}
                      </h3>
                      <p className="text-sm text-gray-400 mb-5 font-mono">
                        {empresa.nif || 'Sin NIF'}
                      </p>

                      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-gray-200">
                        <div className="text-center">
                          <p className="text-lg font-bold text-gray-400">{empresa.total_documentos || 0}</p>
                          <p className="text-[10px] uppercase font-bold text-gray-300 tracking-wider">Docs</p>
                        </div>
                        <div className="text-center border-l border-gray-200">
                          <p className="text-lg font-bold text-gray-300">{empresa.notificaciones_pendientes_ia || 0}</p>
                          <p className="text-[10px] uppercase font-bold text-gray-300 tracking-wider">IA</p>
                        </div>
                        <div className="text-center border-l border-gray-200">
                          <p className="text-lg font-bold text-gray-300">{empresa.notificaciones_pendientes_tarea || 0}</p>
                          <p className="text-[10px] uppercase font-bold text-gray-300 tracking-wider">Tareas</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {showCreateModal && (
          <CrearEmpresaModal
            onClose={() => setShowCreateModal(false)}
            onEmpresaCreada={() => {
              refetch(); // ✅ Refrescar con React Query
            }}
          />
        )}

        {showEditModal && empresaParaEditar && (
          <EditarEmpresaModal
            empresa={empresaParaEditar}
            onClose={() => {
              setShowEditModal(false);
              setEmpresaParaEditar(null);
            }}
            onEmpresaActualizada={() => {
              refetch(); // ✅ Refrescar con React Query
              setShowEditModal(false);
              setEmpresaParaEditar(null);
            }}
          />
        )}

        {showImportModal && (
          <ImportarEmpresasModal
            isOpen={showImportModal}
            onClose={() => setShowImportModal(false)}
            onSuccess={() => {
              refetch();
              setShowImportModal(false);
            }}
          />
        )}

        {showExportModal && (
          <ExportModal
            empresas={empresas}
            onClose={() => setShowExportModal(false)}
          />
        )}
      </div>
    </>
  );
}