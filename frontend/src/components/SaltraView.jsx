// frontend/src/components/SaltraView.jsx
import React, { useState } from 'react';
import { useSaltraInbox, useSaltraEmpresas } from '../hooks/useSaltra';
import axios from 'axios';
import {
  ChevronLeft, FileText, Loader2, Eye, Download, Building2,
  Search, AlertTriangle, CheckCircle, RefreshCw, Filter,
  Calendar, Clock, ExternalLink, Check, X, Bell, LogOut
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import toast from 'react-hot-toast';
import SaltraConfigModal from './SaltraConfigModal';
import MobilePDFViewer from './MobilePDFViewer';


export default function SaltraView() {
  // Filtros (declarar PRIMERO)
  const [filtroNif, setFiltroNif] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('');
  const [filtroSinEmpresa, setFiltroSinEmpresa] = useState(false);
  // ✅ FASE 2: Nuevos filtros de búsqueda avanzada
  const [filtroIdentifier, setFiltroIdentifier] = useState('');
  const [filtroOrganismo, setFiltroOrganismo] = useState('');
  const [filtroFechaInicio, setFiltroFechaInicio] = useState('');
  const [filtroFechaFin, setFiltroFechaFin] = useState('');

  // ✅ Debounced values (valores que realmente se envían a la API)
  const [debouncedNif, setDebouncedNif] = useState('');
  const [debouncedIdentifier, setDebouncedIdentifier] = useState('');
  const [debouncedOrganismo, setDebouncedOrganismo] = useState('');

  const [page, setPage] = useState(1);

  // Debouncing: Actualizar valores debounced después de 500ms sin cambios
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedNif(filtroNif);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [filtroNif]);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedIdentifier(filtroIdentifier);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [filtroIdentifier]);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedOrganismo(filtroOrganismo);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [filtroOrganismo]);

  // React Query (usar filtros DESPUÉS de declararlos)
  const { data: inboxData, isLoading: loadingInbox, refetch } = useSaltraInbox(
    page,
    debouncedNif,
    filtroEstado,
    filtroSinEmpresa,
    debouncedIdentifier,
    debouncedOrganismo,
    filtroFechaInicio,
    filtroFechaFin
  );
  const { data: empresasData } = useSaltraEmpresas();
  const [syncing, setSyncing] = useState(false);

  const notificaciones = inboxData?.notificaciones || [];
  const total = inboxData?.total || 0;
  const stats = inboxData?.stats || {};
  const empresas = empresasData?.empresas || [];
  const loading = loadingInbox;

  // Selección
  const [seleccionada, setSeleccionada] = useState(null);
  const [empresaAsignar, setEmpresaAsignar] = useState('');
  const [filtroEmpresa, setFiltroEmpresa] = useState('');
  const [crearAlias, setCrearAlias] = useState(true);
  const [asignando, setAsignando] = useState(false);
  const [descargando, setDescargando] = useState(false);
  const [aceptando, setAceptando] = useState(false);
  const [descargaMasiva, setDescargaMasiva] = useState({ activa: false, progreso: 0, total: 0, actual: 0 });

  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.departamento === 'Jefatura';
  const limit = 50;

  // ✅ Detectar parámetro 'notif' en URL para auto-seleccionar notificación
  React.useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const notifId = params.get('notif');

    if (notifId && notificaciones.length > 0) {
      const notif = notificaciones.find(n => n.id === parseInt(notifId));
      if (notif) {
        setSeleccionada(notif);
        // Limpiar parámetro de URL
        window.history.replaceState({}, '', '/saltra');
      }
    }
  }, [notificaciones]);

  // Estado de configuración SALTRA
  const [saltraConfigured, setSaltraConfigured] = useState(null); // null = loading, true/false = estado
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showPdfModal, setShowPdfModal] = useState(null); // Notificación a mostrar en modal

  // ✅ MEJORA: Estadísticas en tiempo real desde API DEHU
  const [dehuStats, setDehuStats] = useState(null);
  const [loadingDehuStats, setLoadingDehuStats] = useState(false);

  // Función para obtener stats en tiempo real
  const fetchDehuStats = async () => {
    try {
      setLoadingDehuStats(true);
      const res = await axios.get('/api/saltra/dehu-stats', { withCredentials: true });
      if (res.data.success) {
        setDehuStats(res.data.stats);
      }
    } catch (err) {
      // Silenciar error - stats no es crítico para la funcionalidad
    } finally {
      setLoadingDehuStats(false);
    }
  };

  // Polling cada 30 segundos
  React.useEffect(() => {
    if (saltraConfigured) {
      fetchDehuStats(); // Primera carga
      const interval = setInterval(fetchDehuStats, 30000); // Cada 30 segundos
      return () => clearInterval(interval);
    }
  }, [saltraConfigured]);

  // Verificar configuración SALTRA al cargar
  React.useEffect(() => {
    const checkSaltraConfig = async () => {
      try {
        const res = await axios.get('/api/saltra/status', { withCredentials: true });
        if (res.data.success) {
          setSaltraConfigured(res.data.configured && res.data.enabled);
        }
      } catch (err) {
        console.error('Error checking SALTRA config:', err);
        setSaltraConfigured(false);
      }
    };
    checkSaltraConfig();
  }, []);

  // Handler para cuando se guarda la configuración
  const handleConfigSaved = async () => {
    // Recargar estado de configuración
    try {
      const res = await axios.get('/api/saltra/status', { withCredentials: true });
      if (res.data.success) {
        setSaltraConfigured(res.data.configured && res.data.enabled);
        // Recargar datos si ahora está configurado
        if (res.data.configured && res.data.enabled) {
          refetch();
        }
      }
    } catch (err) {
      console.error('Error reloading SALTRA config:', err);
    }
  };

  const handleSync = async () => {
    if (!isAdmin) return;
    setSyncing(true);

    const toastId = toast.loading('Sincronización iniciada...');

    try {
      await axios.post('/api/saltra/sync', {}, { withCredentials: true });

      // Esperar 30 segundos para que Celery procese (tiempo estimado)
      setTimeout(async () => {
        try {
          await refetch(); // Refrescar datos
          setSyncing(false);
          toast.success('Sincronización completada. Revisa las notificaciones actualizadas.', {
            id: toastId,
            duration: 4000
          });
        } catch (err) {
          setSyncing(false);
          toast.info('Sincronización completada. Refresca la página para ver cambios.', {
            id: toastId,
            duration: 4000
          });
        }
      }, 30000); // 30 segundos

    } catch (err) {
      setSyncing(false);
      toast.error('Error al iniciar sincronización: ' + (err.response?.data?.error || err.message), {
        id: toastId,
        duration: 5000
      });
    }
  };

  const handleLogout = async () => {
    if (!window.confirm('¿Estás seguro de cerrar sesión de SALTRA? Se eliminarán las credenciales guardadas.')) {
      return;
    }

    try {
      const res = await axios.post('/api/admin/saltra/logout', {}, { withCredentials: true });

      if (res.data.success) {
        toast.success('Sesión de SALTRA cerrada correctamente');
        setSaltraConfigured(false);
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al cerrar sesión');
    }
  };

  const handleAsignarEmpresa = async () => {
    if (!seleccionada || !empresaAsignar) return;
    setAsignando(true);
    try {
      await axios.post(`/api/saltra/notificaciones/${seleccionada.id}/asignar-empresa`, {
        empresa_id: parseInt(empresaAsignar),
        crear_alias: crearAlias
      }, { withCredentials: true });

      toast.success('Empresa asignada correctamente');
      setSeleccionada(null);
      setEmpresaAsignar('');
      refetch();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al asignar');
    } finally {
      setAsignando(false);
    }
  };

  const handleAceptarNotificacion = async (notif) => {
    if (!window.confirm('¿Aceptar esta notificación? Esta acción es irreversible.')) {
      return;
    }

    setAceptando(true);
    try {
      const res = await axios.post(`/api/saltra/notificaciones/${notif.id}/aceptar`, {}, { withCredentials: true });
      if (res.data.success) {
        toast.success('Notificación aceptada correctamente. Ya puedes descargar el resguardo.');
        refetch();
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al aceptar');
    } finally {
      setAceptando(false);
    }
  };

  const handleDescargarPDF = async (notif) => {
    setDescargando(true);
    try {
      const res = await axios.post(`/api/saltra/notificaciones/${notif.id}/descargar-pdf`, {}, { withCredentials: true });
      if (res.data.success) {
        toast.success(`PDF descargado: ${res.data.archivos.join(', ')}`);

        // Actualizar estado local de la notificación seleccionada
        setSeleccionada({
          ...seleccionada,
          pdf_descargado: true
        });

        // Refrescar lista completa
        refetch();
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al descargar PDF');
    } finally {
      setDescargando(false);
    }
  };

  const empresasFiltradas = empresas.filter(e =>
    e.nombre.toLowerCase().includes(filtroEmpresa.toLowerCase()) ||
    e.nif?.toLowerCase().includes(filtroEmpresa.toLowerCase())
  );

  const formatFecha = (fecha) => {
    if (!fecha) return '-';
    return new Date(fecha).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  };

  const totalPages = Math.ceil(total / limit);

  if (loading && notificaciones.length === 0) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  // Mostrar loading mientras se verifica configuración
  if (saltraConfigured === null) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-gray-600">Verificando configuración SALTRA...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Notificaciones DEHU</h1>
            <p className="text-gray-600 mt-1">Notificaciones electrónicas de Hacienda y otros organismos</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {(isAdmin || user?.is_super_admin) && saltraConfigured && (
            <>
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                {syncing ? 'Sincronizando...' : 'Sincronizar Ahora'}
              </button>

              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Cerrar Sesión SALTRA
              </button>
            </>
          )}
        </div>
      </div>

      {/* SALTRA No Configurado */}
      {saltraConfigured === false && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-amber-100 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-amber-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-amber-900 mb-2">
                SALTRA no configurado
              </h3>
              <p className="text-amber-800 mb-4">
                Esta gestoría no tiene credenciales SALTRA configuradas. Para poder sincronizar notificaciones electrónicas,
                necesitas configurar las credenciales de acceso a la API de SALTRA.
              </p>
              {(user?.departamento === 'Jefatura' || user?.is_super_admin) && (
                <button
                  onClick={() => setShowConfigModal(true)}
                  className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors font-medium"
                >
                  Configurar SALTRA
                </button>
              )}
              {!user?.is_super_admin && user?.departamento !== 'Jefatura' && (
                <p className="text-sm text-amber-700">
                  Contacta a un usuario de Jefatura para configurar SALTRA.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards - Solo si está configurado */}
      {saltraConfigured && stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Bell className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                  <p className="text-sm text-gray-600">Total</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Building2 className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.con_empresa}</p>
                  <p className="text-sm text-gray-600">Con Empresa</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-amber-100 rounded-lg">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.sin_empresa}</p>
                  <p className="text-sm text-gray-600">Sin Empresa</p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Download className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">{stats.pdfs_descargados}</p>
                  <p className="text-sm text-gray-600">Descargados</p>
                </div>
              </div>
            </div>

            {/* Nueva tarjeta: Pendientes de descargar */}
            <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-xl p-4 shadow-sm border border-orange-200">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <Clock className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-orange-900">
                    {stats.descargables || 0}
                  </p>
                  <p className="text-sm text-orange-700 font-medium">Pendientes</p>
                </div>
              </div>
            </div>
          </div>

          {/* ✅ WIDGET: Estadísticas en Tiempo Real desde API DEHU */}
          {dehuStats && (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-5 shadow-md border-2 border-blue-200 mt-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="p-2 bg-blue-600 rounded-lg">
                    <Bell className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-blue-900">Estadísticas en Tiempo Real</h3>
                    <p className="text-xs text-blue-600">Actualizado desde AEAT</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {loadingDehuStats ? (
                    <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  ) : (
                    <div className="flex items-center gap-1 text-xs text-blue-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                      <span>En vivo</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-white/80 rounded-lg p-3 border border-blue-100">
                  <p className="text-xs text-gray-600 mb-1">Pendientes AEAT</p>
                  <p className="text-2xl font-bold text-blue-900">
                    {dehuStats.totalPendingNotifications || 0}
                  </p>
                </div>

                <div className="bg-white/80 rounded-lg p-3 border border-blue-100">
                  <p className="text-xs text-gray-600 mb-1">No Leídas</p>
                  <p className="text-2xl font-bold text-amber-900">
                    {dehuStats.totalNotReadCommunications || 0}
                  </p>
                </div>

                <div className="bg-white/80 rounded-lg p-3 border border-blue-100">
                  <p className="text-xs text-gray-600 mb-1">Email Verificado</p>
                  <p className="text-lg font-bold text-green-900">
                    {dehuStats.userHasUnverifiedEmail === "0" ? "✓ Sí" : "✗ No"}
                  </p>
                </div>

                <div className="bg-white/80 rounded-lg p-3 border border-blue-100">
                  <p className="text-xs text-gray-600 mb-1">Contacto</p>
                  <p className="text-lg font-bold text-green-900">
                    {dehuStats.userHasNotContact === "0" ? "✓ Sí" : "✗ No"}
                  </p>
                </div>
              </div>

              <p className="text-xs text-blue-600 mt-3 text-center">
                🔄 Se actualiza automáticamente cada 30 segundos
              </p>
            </div>
          )}

          {/* Barra de progreso y acción */}
          {stats.con_empresa > 0 && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-gray-900">Progreso de Descargas</h3>
                  <p className="text-sm text-gray-600">
                    {stats.pdfs_descargados} de {stats.con_empresa} notificaciones descargadas
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-blue-600">
                    {Math.round((stats.pdfs_descargados / stats.con_empresa) * 100)}%
                  </p>
                </div>
              </div>

              {/* Barra de progreso */}
              <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${(stats.pdfs_descargados / stats.con_empresa) * 100}%` }}
                ></div>
              </div>

              {/* Botón de descarga masiva */}
              {(stats.descargables || 0) > 0 && (isAdmin || user?.is_super_admin) && (
                <div className="space-y-3">
                  {/* Barra de progreso de descarga masiva */}
                  {descargaMasiva.activa && (
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-5 shadow-sm">
                      {/* Header con progreso */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                          <span className="text-sm font-semibold text-blue-900">
                            Descargando notificaciones...
                          </span>
                        </div>
                        <span className="text-sm font-bold text-blue-600">
                          {descargaMasiva.actual} / {descargaMasiva.total}
                        </span>
                      </div>

                      {/* Notificación actual */}
                      {descargaMasiva.notificacionActual && (
                        <div className="mb-3 p-3 bg-white rounded-lg border border-blue-100">
                          <p className="text-xs text-gray-500 mb-1">Descargando ahora:</p>
                          <p className="text-sm font-medium text-gray-900">
                            📄 {descargaMasiva.notificacionActual.identifier} - {descargaMasiva.notificacionActual.nombre}
                          </p>
                        </div>
                      )}

                      {/* Barra de progreso */}
                      <div className="w-full bg-blue-200 rounded-full h-3 mb-3 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-indigo-600 h-3 rounded-full transition-all duration-300 flex items-center justify-end pr-2"
                          style={{ width: `${descargaMasiva.progreso}%` }}
                        >
                          {descargaMasiva.progreso > 10 && (
                            <span className="text-xs font-bold text-white">{descargaMasiva.progreso}%</span>
                          )}
                        </div>
                      </div>

                      {/* Estadísticas en vivo */}
                      <div className="grid grid-cols-3 gap-3">
                        <div className="bg-green-50 rounded-lg p-2 border border-green-200">
                          <p className="text-xs text-green-600 font-medium">✅ Descargados</p>
                          <p className="text-lg font-bold text-green-700">{descargaMasiva.descargados || 0}</p>
                        </div>
                        <div className="bg-red-50 rounded-lg p-2 border border-red-200">
                          <p className="text-xs text-red-600 font-medium">❌ Errores</p>
                          <p className="text-lg font-bold text-red-700">{descargaMasiva.errores || 0}</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2 border border-gray-200">
                          <p className="text-xs text-gray-600 font-medium">⏳ Restantes</p>
                          <p className="text-lg font-bold text-gray-700">
                            {descargaMasiva.total - (descargaMasiva.descargados || 0) - (descargaMasiva.errores || 0)}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  <button
                    onClick={async () => {
                      const pendientes = stats.descargables || 0;
                      if (!window.confirm(`¿Descargar ${pendientes} notificaciones pendientes?`)) return;

                      setDescargaMasiva({ activa: true, progreso: 0, total: pendientes, actual: 0, taskId: null });

                      try {
                        // Iniciar tarea de Celery
                        const res = await axios.post('/api/saltra/sync-all', {}, { withCredentials: true });

                        if (res.data.success && res.data.task_id) {
                          const taskId = res.data.task_id;
                          setDescargaMasiva(prev => ({ ...prev, taskId }));

                          // Polling de progreso cada 500ms
                          const pollInterval = setInterval(async () => {
                            try {
                              const statusRes = await axios.get(`/api/saltra/sync-all/status/${taskId}`, {
                                withCredentials: true
                              });

                              const progress = statusRes.data;

                              setDescargaMasiva({
                                activa: progress.status === 'PROCESSING',
                                progreso: progress.progreso || 0,
                                total: progress.total || pendientes,
                                actual: progress.current || 0,
                                descargados: progress.descargados || 0,
                                errores: progress.errores || 0,
                                taskId: taskId,
                                notificacionActual: progress.notificacion_actual
                              });

                              // Si terminó, detener polling
                              if (progress.status === 'SUCCESS' || progress.status === 'FAILURE') {
                                clearInterval(pollInterval);

                                if (progress.status === 'SUCCESS') {
                                  toast.success(
                                    `✅ Descargadas: ${progress.descargados} | ❌ Errores: ${progress.errores}`,
                                    { duration: 5000 }
                                  );
                                  setTimeout(() => {
                                    setDescargaMasiva({ activa: false, progreso: 0, total: 0, actual: 0 });
                                    refetch();
                                  }, 2000);
                                } else {
                                  toast.error('Error en descarga masiva');
                                  setDescargaMasiva({ activa: false, progreso: 0, total: 0, actual: 0 });
                                }
                              }
                            } catch (pollErr) {
                              console.error('Error polling progress:', pollErr);
                              // Continuar polling aunque falle una consulta
                            }
                          }, 500);

                          // Limpiar interval si el componente se desmonta
                          return () => clearInterval(pollInterval);
                        }
                      } catch (err) {
                        toast.error('Error iniciando descarga masiva');
                        setDescargaMasiva({ activa: false, progreso: 0, total: 0, actual: 0 });
                      }
                    }}
                    disabled={descargaMasiva.activa}
                    className="w-full py-3 bg-gradient-to-r from-orange-600 to-red-600 text-white rounded-lg 
                             hover:from-orange-700 hover:to-red-700 transition-all font-bold 
                             flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {descargaMasiva.activa ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Descargando... {descargaMasiva.progreso}%
                      </>
                    ) : (
                      <>
                        <Download className="w-5 h-5" />
                        Descargar Todas las Pendientes ({stats.descargables || 0})
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Contenido principal - Solo si está configurado */}
      {saltraConfigured && (
        <>
          {/* Filtros */}
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">Filtros:</span>
              </div>

              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Buscar NIF..."
                  value={filtroNif}
                  onChange={(e) => setFiltroNif(e.target.value)}
                  className="pl-9 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none w-40"
                />
              </div>

              <select
                value={filtroEstado}
                onChange={(e) => { setFiltroEstado(e.target.value); setPage(1); }}
                className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none"
              >
                <option value="">Todos los estados</option>
                <option value="ACEPTADA">Aceptada</option>
                <option value="PENDIENTE">Pendiente</option>
                <option value="RECHAZADA">Rechazada</option>
              </select>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filtroSinEmpresa}
                  onChange={(e) => { setFiltroSinEmpresa(e.target.checked); setPage(1); }}
                  className="w-4 h-4 text-primary rounded focus:ring-primary"
                />
                <span className="text-sm text-gray-700">Solo sin empresa</span>
              </label>

              {/* ✅ FASE 2: Filtros avanzados */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="N° notificación..."
                  value={filtroIdentifier}
                  onChange={(e) => setFiltroIdentifier(e.target.value)}
                  className="pl-9 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none w-40"
                />
              </div>

              <input
                type="text"
                placeholder="Organismo..."
                value={filtroOrganismo}
                onChange={(e) => setFiltroOrganismo(e.target.value)}
                className="px-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none w-40"
              />

              <input
                type="date"
                value={filtroFechaInicio}
                onChange={(e) => { setFiltroFechaInicio(e.target.value); setPage(1); }}
                className="px-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none"
                title="Desde"
              />

              <input
                type="date"
                value={filtroFechaFin}
                onChange={(e) => { setFiltroFechaFin(e.target.value); setPage(1); }}
                className="px-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-primary outline-none"
                title="Hasta"
              />

              {/* Botón limpiar filtros */}
              {(filtroNif || filtroEstado || filtroSinEmpresa || filtroIdentifier || filtroOrganismo || filtroFechaInicio || filtroFechaFin) && (
                <button
                  onClick={() => {
                    setFiltroNif('');
                    setFiltroEstado('');
                    setFiltroSinEmpresa(false);
                    setFiltroIdentifier('');
                    setFiltroOrganismo('');
                    setFiltroFechaInicio('');
                    setFiltroFechaFin('');
                    setPage(1);
                  }}
                  className="px-3 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-1"
                  title="Limpiar filtros"
                >
                  <X className="w-4 h-4" />
                  Limpiar
                </button>
              )}

              <div className="ml-auto text-sm text-gray-500">
                Mostrando {notificaciones.length} de {total}
              </div>
            </div>
          </div>

          {/* Contenido principal */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Lista de Notificaciones */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col max-h-[600px]">
              <div className="p-4 border-b border-gray-100 bg-gray-50 rounded-t-xl">
                <h3 className="font-semibold text-gray-700">Notificaciones ({total})</h3>
              </div>

              <div className="overflow-y-auto flex-1">
                {notificaciones.length === 0 ? (
                  <div className="p-12 text-center">
                    <CheckCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">No hay notificaciones con estos filtros</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {notificaciones.map(n => (
                      <div
                        key={n.id}
                        onClick={() => setSeleccionada(n)}
                        className={`p-4 cursor-pointer transition-all hover:bg-gray-50
                      ${seleccionada?.id === n.id ? 'bg-primary-light border-l-4 border-primary' : ''}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-lg shrink-0 ${n.pdf_descargado ? 'bg-green-100' : 'bg-gray-100'}`}>
                            <FileText className={`w-5 h-5 ${n.pdf_descargado ? 'text-green-600' : 'text-gray-500'}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono text-sm font-bold text-gray-900">{n.nif_titular}</span>
                              {n.empresa_nombre ? (
                                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full truncate max-w-32">
                                  {n.empresa_nombre}
                                </span>
                              ) : (
                                <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                                  Sin empresa
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 truncate">{n.emitter_entity}</p>
                            <p className="text-xs text-gray-500 truncate mt-1">{n.concept}</p>
                            <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3" />
                                {formatFecha(n.availability_date)}
                              </span>
                              <span className={`px-2 py-0.5 rounded-full ${n.state === 'ACEPTADA' ? 'bg-green-100 text-green-700' :
                                n.state === 'PENDIENTE' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
                                }`}>
                                {n.state}
                              </span>

                              {/* ✅ Badge de Urgencia */}
                              {n.state === 'PENDIENTE' && (() => {
                                const hoy = new Date();
                                const vencimiento = new Date(n.expiration_date);
                                const diasRestantes = Math.ceil((vencimiento - hoy) / (1000 * 60 * 60 * 24));

                                if (diasRestantes <= 3 && diasRestantes >= 0) {
                                  return (
                                    <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-bold flex items-center gap-1">
                                      <AlertTriangle className="w-3 h-3" />
                                      {diasRestantes}d
                                    </span>
                                  );
                                } else if (diasRestantes <= 7 && diasRestantes > 3) {
                                  return (
                                    <span className="px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 flex items-center gap-1">
                                      <Clock className="w-3 h-3" />
                                      {diasRestantes}d
                                    </span>
                                  );
                                }
                                return null;
                              })()}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Paginación */}
              {totalPages > 1 && (
                <div className="p-4 border-t border-gray-100 flex items-center justify-between">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  <span className="text-sm text-gray-600">Página {page} de {totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                  >
                    Siguiente
                  </button>
                </div>
              )}
            </div>

            {/* Panel Detalle/Acciones */}
            <div>
              {seleccionada ? (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-4">

                  {/* Detalle */}
                  <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <h3 className="font-bold text-lg text-gray-900 mb-4">Detalle de Notificación</h3>

                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">NIF Titular:</span>
                        <span className="font-mono font-bold">{seleccionada.nif_titular}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Identificador:</span>
                        <span className="font-mono text-xs">{seleccionada.identifier}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Estado:</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${seleccionada.state === 'ACEPTADA' ? 'bg-green-100 text-green-700' :
                          seleccionada.state === 'PENDIENTE' ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-600'
                          }`}>
                          {seleccionada.state}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 block mb-1">Organismo:</span>
                        <span className="text-gray-900">{seleccionada.emitter_entity}</span>
                      </div>
                      <div>
                        <span className="text-gray-500 block mb-1">Concepto:</span>
                        <span className="text-gray-900 text-xs">{seleccionada.concept}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Fecha disponible:</span>
                        <span>{formatFecha(seleccionada.availability_date)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-500">Fecha límite:</span>
                        <span className="text-red-600 font-medium">{formatFecha(seleccionada.expiration_date)}</span>
                      </div>

                      {/* ✅ FASE 2: Nuevos campos */}
                      {(seleccionada.sia_code || seleccionada.name_receptor || seleccionada.cant_annexes > 0) && (
                        <div className="pt-3 border-t space-y-2">
                          {/* SIA Code Badge */}
                          {seleccionada.sia_code && (
                            <div className="flex justify-between items-center">
                              <span className="text-gray-500">Código SIA:</span>
                              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-mono font-bold">
                                {seleccionada.sia_code}
                              </span>
                            </div>
                          )}

                          {/* SIA Denomination */}
                          {seleccionada.sia_denomination && (
                            <div>
                              <span className="text-gray-500 block mb-1 text-xs">Denominación SIA:</span>
                              <span className="text-gray-900 text-xs">{seleccionada.sia_denomination}</span>
                            </div>
                          )}

                          {/* Receptor Info */}
                          {seleccionada.name_receptor && (
                            <div>
                              <span className="text-gray-500 block mb-1">Receptor:</span>
                              <div className="bg-gray-50 p-2 rounded">
                                <p className="text-sm font-medium text-gray-900">{seleccionada.name_receptor}</p>
                                {seleccionada.nif_receptor && (
                                  <p className="text-xs text-gray-600 font-mono mt-1">{seleccionada.nif_receptor}</p>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Annexes Indicator */}
                          {seleccionada.cant_annexes > 0 && (
                            <div className="flex items-center gap-2 bg-amber-50 p-2 rounded">
                              <FileText className="w-4 h-4 text-amber-600" />
                              <span className="text-sm text-amber-800">
                                {seleccionada.cant_annexes} anexo{seleccionada.cant_annexes > 1 ? 's' : ''} adjunto{seleccionada.cant_annexes > 1 ? 's' : ''}
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {seleccionada.empresa_nombre && (
                        <div className="pt-3 border-t">
                          <span className="text-gray-500">Empresa asignada:</span>
                          <div className="mt-1 flex items-center gap-2">
                            <Building2 className="w-4 h-4 text-green-600" />
                            <span className="font-medium text-green-700">{seleccionada.empresa_nombre}</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Botón Aceptar (solo si está PENDIENTE) */}
                    <div className="mt-6 pt-4 border-t space-y-3">
                      {seleccionada.state === 'PENDIENTE' && (
                        <div>
                          <button
                            onClick={() => handleAceptarNotificacion(seleccionada)}
                            disabled={aceptando}
                            className="w-full py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 
                                 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                          >
                            {aceptando ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                            Aceptar Notificación
                          </button>
                          <p className="text-xs text-gray-500 mt-2 text-center">
                            Debes aceptar la notificación antes de poder descargar el PDF
                          </p>
                        </div>
                      )}

                      {/* Botón Descargar PDF */}
                      {seleccionada.state === 'ACEPTADA' && (
                        seleccionada.pdf_descargado ? (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 text-green-600 justify-center">
                              <CheckCircle className="w-5 h-5" />
                              <span>PDF ya descargado</span>
                            </div>
                            {/* Botón Ver Notificación */}
                            <button
                              onClick={() => {
                                // Abrir modal con PDF embebido
                                setShowPdfModal(seleccionada);
                              }}
                              className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                                   transition-colors font-medium flex items-center justify-center gap-2"
                            >
                              <Eye className="w-5 h-5" />
                              Ver Notificación
                            </button>
                          </div>
                        ) : seleccionada.empresa_nombre ? (
                          <button
                            onClick={() => handleDescargarPDF(seleccionada)}
                            disabled={descargando}
                            className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 
                                 transition-colors font-medium flex items-center justify-center gap-2 disabled:opacity-50"
                          >
                            {descargando ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
                            Descargar PDF
                          </button>
                        ) : (
                          <p className="text-sm text-amber-600 text-center">
                            Asigna una empresa primero para descargar el PDF
                          </p>
                        )
                      )}
                    </div>
                  </div>

                  {/* Asignar Empresa (solo si no tiene) */}
                  {!seleccionada.empresa_nombre && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                      <h3 className="font-bold text-lg text-gray-900 mb-4">Asignar Empresa</h3>

                      <div className="relative mb-4">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                          type="text"
                          placeholder="Buscar empresa..."
                          value={filtroEmpresa}
                          onChange={(e) => setFiltroEmpresa(e.target.value)}
                          className="w-full pl-9 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                      </div>

                      <div className="max-h-48 overflow-y-auto border rounded-lg mb-4">
                        {empresasFiltradas.slice(0, 20).map(emp => (
                          <button
                            key={emp.id}
                            onClick={() => setEmpresaAsignar(emp.id.toString())}
                            className={`w-full p-3 text-left transition-all flex items-center justify-between text-sm
                          ${empresaAsignar === emp.id.toString() ? 'bg-primary-light' : 'hover:bg-gray-50'}`}
                          >
                            <div>
                              <div className="font-medium">{emp.nombre}</div>
                              <div className="text-xs text-gray-500 font-mono">{emp.nif}</div>
                            </div>
                            {empresaAsignar === emp.id.toString() && (
                              <Check className="w-4 h-4 text-primary" />
                            )}
                          </button>
                        ))}
                      </div>

                      <label className="flex items-center gap-2 mb-4 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={crearAlias}
                          onChange={(e) => setCrearAlias(e.target.checked)}
                          className="w-4 h-4 text-primary rounded"
                        />
                        <span className="text-sm text-gray-700">Crear alias NIF para futuras notificaciones</span>
                      </label>

                      <button
                        onClick={handleAsignarEmpresa}
                        disabled={asignando || !empresaAsignar}
                        className="w-full py-3 bg-linear-to-r from-orange-600 to-red-600 text-white rounded-lg 
                             hover:from-orange-700 hover:to-red-700 transition-all font-bold 
                             flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {asignando ? <Loader2 className="w-5 h-5 animate-spin" /> : <Check className="w-5 h-5" />}
                        Asignar Empresa
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-white rounded-xl p-12 shadow-sm border border-gray-100 text-center h-full flex flex-col justify-center items-center text-gray-400">
                  <div className="bg-gray-50 p-6 rounded-full mb-4">
                    <Bell className="w-16 h-16 text-gray-300" />
                  </div>
                  <h3 className="text-xl font-medium text-gray-900 mb-2">Selecciona una notificación</h3>
                  <p>Elige una notificación de la lista para ver sus detalles y acciones</p>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Modal de Configuración SALTRA */}
      <SaltraConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onSuccess={handleConfigSaved}
      />

      {/* Modal de PDF */}
      {showPdfModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Notificación SALTRA</h2>
                <p className="text-sm text-gray-600 font-mono">{showPdfModal.identifier}</p>
              </div>
              <button
                onClick={() => setShowPdfModal(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* PDF Viewer */}
            <div className="flex-1 overflow-hidden">
              <MobilePDFViewer
                pdfUrl={`/api/saltra/notificaciones/${showPdfModal.id}/ver-pdf`}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
