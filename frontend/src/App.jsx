// frontend/src/App.jsx
import { lazy, Suspense, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { TenantProvider } from './contexts/TenantContext';
import { PermisosProvider } from './contexts/PermisosContext';
import socket from './socket';
import toast from 'react-hot-toast';
import NotificationManager from './utils/NotificationManager';
import useNotifications from './hooks/useNotifications';
import { useSocketConnection } from './hooks/useSocketConnection';

// ✅ Componentes que SIEMPRE se cargan (esenciales)
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import Login from './components/Login';
import Layout from './components/Layout';
import LoadingPage from './components/LoadingPage';
import ToastNotifications from './components/ToastNotifications';
import UpdatePrompt from './components/UpdatePrompt';
import ImpersonacionModal from './components/ImpersonacionModal';
import ImpersonacionBanner from './components/ImpersonacionBanner';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';

// ✅ Componentes LAZY (se cargan solo cuando se necesitan)
const EmpresasDashboard = lazy(() => import('./components/EmpresasDashboard'));
const NotificacionesView = lazy(() => import('./components/NotificacionesView'));
const ImportadorView = lazy(() => import('./components/ImportadorView'));
const NoClasificadosView = lazy(() => import('./components/NoClasificadosView'));
const CategoriasView = lazy(() => import('./components/CategoriasView'));
const Register = lazy(() => import('./components/Register'));
const UsuariosView = lazy(() => import('./components/UsuariosView'));
const CalendarioView = lazy(() => import('./components/CalendarioView'));
const ResetPassword = lazy(() => import('./components/ResetPassword'));
const DehuEspanaView = lazy(() => import('./views/DehuEspanaView'));
const PlantillasManager = lazy(() => import('./components/PlantillasManager'));
const SaltraView = lazy(() => import('./components/SaltraView'));
const SaltraAdminView = lazy(() => import('./components/SaltraAdminView'));
const AuditoriaView = lazy(() => import('./components/AuditoriaView'));
const FiniquitosView = lazy(() => import('./components/FiniquitosView'));
const MesaTrabajo = lazy(() => import('./components/MesaTrabajo'));
const DashboardGraficos = lazy(() => import('./components/Dashboard/DashboardGraficos'));
const BusquedaAvanzada = lazy(() => import('./components/BusquedaAvanzada'));
const GruposDocumentosView = lazy(() => import('./components/GruposDocumentosView'));
const ChatIA = lazy(() => import('./components/ChatIA'));
const ComprobarSegurosNominasView = lazy(() => import('./components/ComprobarSegurosNominasView'));
const DocumentosFiscalesView = lazy(() => import('./components/DocumentosFiscalesView'));
const ApiKeysMonitor = lazy(() => import('./components/ApiKeysMonitor'));
const GruposEmpresasView = lazy(() => import('./components/GruposEmpresasView'));
const SoporteView = lazy(() => import('./components/SoporteView'));
const GestionSoporteView = lazy(() => import('./components/GestionSoporteView'));
const GestoriasAdminView = lazy(() => import('./components/GestoriasAdminView'));
const RolesPermisosAdminView = lazy(() => import('./components/RolesPermisosAdminView'));
const GestoriasMetricsView = lazy(() => import('./components/GestoriasMetricsView'));
const ProductividadView = lazy(() => import('./components/ProductividadView'));
const BillingDashboard = lazy(() => import('./components/BillingDashboard'));
const GestionComunicados = lazy(() => import('./components/GestionComunicados'));
const AplazamientosView = lazy(() => import('./components/AplazamientosView'));
const EmailsPendientesView = lazy(() => import('./components/EmailsPendientesView'));

// ⭐ Super-Admin Components
const DashboardGlobal = lazy(() => import('./components/SuperAdmin/DashboardGlobal'));
const GestoriasTable = lazy(() => import('./components/SuperAdmin/GestoriasTable'));
const GestoriaDetalle = lazy(() => import('./components/SuperAdmin/GestoriaDetalle'));
const PlanesTable = lazy(() => import('./components/SuperAdmin/PlanesTable'));
const GestionUsuariosSistema = lazy(() => import('./components/SuperAdmin/GestionUsuariosSistema'));
const BillingAdminView = lazy(() => import('./components/SuperAdmin/BillingAdminView'));
const BillingConfigAdmin = lazy(() => import('./components/SuperAdmin/BillingConfigAdmin'));
const BannersManagement = lazy(() => import('./components/SuperAdmin/BannersManagement'));
const VersionManager = lazy(() => import('./components/SuperAdmin/VersionManager'));
const MonitoringDashboard = lazy(() => import('./components/MonitoringDashboard'));
const ClientesConectaView = lazy(() => import('./components/ClientesConectaView'));

// ⭐ Guest / Client Components
const TimelineInvitados = lazy(() => import('./components/TimelineInvitados'));

// Maintenance Page
const MaintenancePage = lazy(() => import('./components/MaintenancePage'));
const MaintenanceWarningBanner = lazy(() => import('./components/MaintenanceWarningBanner'));


// Componente interno que verifica si hay impersonación activa al cargar la app
function ImpersonacionEstadoChecker({ onImpersonacionActiva }) {
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;
    axios.get('/api/impersonacion/estado', { withCredentials: true })
      .then(res => {
        if (res.data.activa) {
          onImpersonacionActiva({
            gestoria_nombre: res.data.gestoria_nombre,
            gestoria_id: res.data.gestoria_id
          });
        }
      })
      .catch(() => {});
  }, [user]);

  return null;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (user?.preferencias?.vistaInicio === 'calendario') {
    return <Navigate to="/calendario" replace />;
  }

  // Rutas dedicadas por rol/departamento
  if (user?.is_super_admin) {
    return <Navigate to="/super-admin/dashboard" replace />;
  }

  if (user?.departamento === 'Soporte' && !user?.gestoria_id) {
    return <Navigate to="/gestion-soporte" replace />;
  }

  // Invitados no tienen acceso a Mesa de Trabajo, van directo al Muro de Novedades (Timeline)
  const isInvitado = user?.departamento === 'Invitado' || user?.rol_nombre === 'Invitado';
  if (isInvitado) {
    return <Navigate to="/inicio" replace />;
  }

  return <Navigate to="/mesa-trabajo" replace />;
}

export default function App() {
  const [maintenanceWarning, setMaintenanceWarning] = useState(null);
  const [solicitudImpersonacion, setSolicitudImpersonacion] = useState(null);
  const [impersonacionActiva, setImpersonacionActiva] = useState(null); // { gestoria_nombre, gestoria_id }

  // ✅ PRIMERO: Configurar React Query
  // ✅ FIX: usar useState(() => new QueryClient()) para que la instancia sea estable entre re-renders.
  // Antes: const queryClient = new QueryClient(...) dentro del componente creaba una nueva instancia
  // en cada render → QueryClientProvider recibía un cliente nuevo → caché borrada + el closure del
  // socket listener apuntaba a una instancia desactualizada, rompiendo la invalidación del query.
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
        refetchOnWindowFocus: false,
        refetchOnMount: false,
        refetchOnReconnect: false,
        retry: 1
      }
    }
  }));

  // ✅ Inicializar notificaciones push
  useNotifications();
  // ✅ Monitorizar estado de conexión Socket.IO
  useSocketConnection();

  // ✅ DESPUÉS: useEffect de notificaciones
  useEffect(() => {
    // Solicitar permisos de notificación del navegador
    NotificationManager.requestPermission();

    socket.on('nueva_notificacion', (notificacion) => {
      console.log('🔔 Notificación recibida:', notificacion);

      // Mostrar toast
      toast.success(notificacion.titulo, {
        description: notificacion.mensaje,
        duration: 5000,
      });

      // ✅ AGREGAR ESTA LÍNEA - Actualizar contador de notificaciones y feed
      queryClient.invalidateQueries({ queryKey: ['notificaciones'] });
      queryClient.invalidateQueries({ queryKey: ['novedades-timeline'] });
    });

    // 🚀 Update PWA global listener
    socket.on('pwa_update_available', (data) => {
      console.log('🔄 PWA Update Event:', data);
      toast(
        (t) => (
          <div className="flex flex-col gap-1">
            <span className="font-bold text-sm">{data.titulo || 'Actualización del Sistema'}</span>
            <span className="text-xs">{data.mensaje || 'Nueva versión disponible. Aplicando cambios...'}</span>
          </div>
        ),
        {
          icon: '🚀',
          duration: 10000,
          style: {
            background: '#f5f3ff',
            color: '#6d28d9',
            border: '1px solid #c4b5fd'
          }
        }
      );

      // Intentar disparar el prompt de recarga si el navegador lo soporta
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistration().then(registration => {
          if (registration) {
            registration.update();
          }
        });
      }
    });

    // 🛠️ Listeners de mantenimiento
    socket.on('maintenance_warning', (data) => {
      console.log('⚠️ Advertencia de mantenimiento:', data);
      setMaintenanceWarning(data);
    });

    socket.on('maintenance_activated', (data) => {
      console.log('🛠️ Mantenimiento activado:', data);
      // Redirigir a página de mantenimiento
      window.location.href = '/maintenance';
    });

    socket.on('maintenance_deactivated', () => {
      console.log('✅ Mantenimiento desactivado');
      setMaintenanceWarning(null);
    });

    // 🔄 Auto-refresco al completar tareas pesadas
    const handleTaskCompletion = (data) => {
      console.log('🔄 Tarea completada, refrescando datos:', data);

      // Invalidar múltiples queries para refrescar la UI
      const queriesToInvalidate = [
        ['notificaciones'],
        ['documentos-pendientes'],
        ['stats-mesa-trabajo'],
        ['empresas-stats'],
        ['no-clasificados'],
        ['historial-nominas'],
        ['historial-seguros']
      ];

      queriesToInvalidate.forEach(queryKey => {
        queryClient.invalidateQueries({ queryKey });
      });

      // Feedback visual adicional si es necesario
      if (data.status || data.message) {
        toast.success(data.status || data.message);
      }
    };

    socket.on('nomina_completed', handleTaskCompletion);
    socket.on('seguro_completed', handleTaskCompletion);

    // 🔐 Solicitud de acceso de soporte recibida (admins de gestoría)
    socket.on('solicitud_acceso_soporte', (data) => {
      setSolicitudImpersonacion(data);
    });

    // 🔐 Respuesta a solicitud de acceso recibida (agente de soporte)
    socket.on('respuesta_acceso_soporte', async (data) => {
      if (data.aceptado) {
        toast.success(`${data.aprobado_por} aceptó tu solicitud de acceso a ${data.gestoria_nombre}`);
        try {
          const res = await axios.post('/api/impersonacion/activar', { token: data.token }, { withCredentials: true });
          if (res.data.success) {
            setImpersonacionActiva({ gestoria_nombre: data.gestoria_nombre, gestoria_id: data.gestoria_id });
            // Redirigir al dashboard de la gestoría impersonada
            window.location.href = '/empresas';
          }
        } catch {
          toast.error('Error al activar impersonación');
        }
      } else {
        toast.error(`${data.aprobado_por} rechazó tu solicitud de acceso a ${data.gestoria_nombre}`);
      }
    });

    return () => {
      socket.off('nueva_notificacion');
      socket.off('pwa_update_available');
      socket.off('maintenance_warning');
      socket.off('maintenance_activated');
      socket.off('maintenance_deactivated');
      socket.off('nomina_completed');
      socket.off('seguro_completed');
      socket.off('solicitud_acceso_soporte');
      socket.off('respuesta_acceso_soporte');
    };
  }, [queryClient]); // ← Agregar queryClient como dependencia

  return (
    <>
      {/* ⚠️ Renderizar página de mantenimiento FUERA de providers para evitar API calls */}
      <Routes>
        <Route path="/maintenance" element={<MaintenancePage />} />
        <Route path="*" element={
          <AuthProvider>
            <QueryClientProvider client={queryClient}>
              <TenantProvider>
                <ThemeProvider>
                  <Toaster
                    position="top-right"
                    reverseOrder={false}
                    gutter={8}
                    toastOptions={{
                      duration: 4000,
                      style: {
                        borderRadius: '12px',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
                        padding: '16px',
                        fontSize: '14px',
                        fontWeight: '500',
                      },
                      success: {
                        duration: 3000,
                        style: {
                          background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
                          color: '#fff',
                        },
                        iconTheme: {
                          primary: '#fff',
                          secondary: '#10b981',
                        },
                      },
                      error: {
                        duration: 5000,
                        style: {
                          background: 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)',
                          color: '#fff',
                        },
                        iconTheme: {
                          primary: '#fff',
                          secondary: '#ef4444',
                        },
                      },
                      loading: {
                        style: {
                          background: 'linear-gradient(90deg, #f97316 0%, #ef4444 100%)',
                          color: '#fff',
                        },
                        iconTheme: {
                          primary: '#fff',
                          secondary: '#f97316',
                        },
                      },
                      blank: {
                        style: {
                          background: 'linear-gradient(90deg, #f59e0b 0%, #f97316 100%)',
                          color: '#fff',
                        },
                      },
                    }}
                  />
                  {/* ⭐ Toast Notifications para WebSocket */}
                  <ToastNotifications socket={socket} />

                  {/* 🔐 Banner de impersonación activa */}
                  {impersonacionActiva && (
                    <ImpersonacionBanner
                      gestoriaNombre={impersonacionActiva.gestoria_nombre}
                      onTerminar={() => { setImpersonacionActiva(null); window.location.href = '/super-admin/gestorias'; }}
                    />
                  )}

                  {/* 🔐 Modal de solicitud de acceso de soporte (para admins) */}
                  {solicitudImpersonacion && (
                    <ImpersonacionModal
                      solicitud={solicitudImpersonacion}
                      onClose={() => setSolicitudImpersonacion(null)}
                    />
                  )}

                  {/* 🔐 Verificar impersonación activa al cargar (dentro de AuthProvider) */}
                  <ImpersonacionEstadoChecker onImpersonacionActiva={setImpersonacionActiva} />

                  {/* 🛠️ Banner de advertencia de mantenimiento */}
                  {maintenanceWarning && (
                    <Suspense fallback={null}>
                      <MaintenanceWarningBanner
                        warningData={maintenanceWarning}

                      />
                    </Suspense>
                  )}

                  {/* ✅ PWA Update Prompt */}
                  <UpdatePrompt />

                  {/* ✅ Suspense envuelve todas las rutas lazy */}
                  <PermisosProvider>
                    <Suspense fallback={<LoadingPage />}>
                      <Routes>
                        <Route path="/login" element={<Login />} />
                        <Route path="/reset-password" element={<ResetPassword />} />
                        <Route path="/reset_password" element={<ResetPassword />} />

                        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>

                          <Route path="/" element={<HomeRedirect />} />
                          <Route path="/inicio" element={<TimelineInvitados />} />
                          <Route path="/empresas" element={<EmpresasDashboard />} />
                          <Route path="/importar" element={<ImportadorView />} />
                          <Route path="/no-clasificados" element={<NoClasificadosView />} />
                          <Route path="/empresa/:empresaId" element={<CategoriasView />} />
                          <Route path="/empresa/:empresaId/:categoria" element={<NotificacionesView />} />
                          <Route path="/calendario" element={<CalendarioView />} />
                          <Route path="/dehu-espana" element={<DehuEspanaView />} />
                          <Route path="/productividad" element={<ProductividadView />} />
                          <Route path="/saltra" element={<SaltraView />} />
                          <Route path="/mesa-trabajo" element={<MesaTrabajo />} />
                          <Route path="/emails-pendientes" element={<EmailsPendientesView />} />
                          <Route path="/auditoria" element={<AdminRoute><AuditoriaView /></AdminRoute>} />
                          <Route path="/finiquitos" element={<FiniquitosView />} />
                          <Route path="/register" element={<AdminRoute><Register /></AdminRoute>} />
                          <Route path="/usuarios" element={<AdminRoute><UsuariosView /></AdminRoute>} />
                          <Route path="/plantillas" element={<AdminRoute><PlantillasManager /></AdminRoute>} />
                          <Route path="/dashboard" element={<DashboardGraficos />} />
                          <Route path="/busqueda" element={<BusquedaAvanzada />} />
                          <Route path="/grupos" element={<GruposDocumentosView />} />
                          <Route path="/grupos-empresas" element={<GruposEmpresasView />} />
                          <Route path="/empresa/:empresaId/grupos" element={<GruposDocumentosView />} />
                          <Route path="/empresa/:empresaId/grupos/:grupoId" element={<GruposDocumentosView />} />
                          <Route path="/comprobar-seguros-nominas" element={<ComprobarSegurosNominasView />} />
                          <Route path="/soporte" element={<SoporteView />} />
                          <Route path="/gestion-soporte" element={<AdminRoute><GestionSoporteView /></AdminRoute>} />
                          <Route path="/admin/gestorias" element={<Navigate to="/super-admin/gestorias" replace />} />
                          <Route path="/admin/metrics" element={<AdminRoute><GestoriasMetricsView /></AdminRoute>} />
                          <Route path="/admin/saltra" element={<AdminRoute><SaltraAdminView /></AdminRoute>} />
                          <Route path="/admin/roles-permisos" element={<AdminRoute><RolesPermisosAdminView /></AdminRoute>} />
                          <Route path="/admin/comunicados" element={<AdminRoute><GestionComunicados /></AdminRoute>} />

                          {/* ⭐ Rutas Super-Admin */}
                          <Route path="/super-admin/dashboard" element={<AdminRoute requireSuperAdmin><DashboardGlobal /></AdminRoute>} />
                          <Route path="/super-admin/gestorias" element={<AdminRoute requireSuperAdmin><GestoriasTable /></AdminRoute>} />
                          <Route path="/super-admin/gestorias/:id" element={<AdminRoute requireSuperAdmin><GestoriaDetalle /></AdminRoute>} />
                          <Route path="/super-admin/gestorias/:id/editar" element={<AdminRoute requireSuperAdmin><GestoriaDetalle /></AdminRoute>} />
                          <Route path="/super-admin/planes" element={<AdminRoute requireSuperAdmin><PlanesTable /></AdminRoute>} />
                          <Route path="/super-admin/banners" element={<AdminRoute requireSuperAdmin><BannersManagement /></AdminRoute>} />
                          <Route path="/super-admin/usuarios-sistema" element={<AdminRoute requireSuperAdmin><GestionUsuariosSistema /></AdminRoute>} />
                          <Route path="/super-admin/billing" element={<AdminRoute requireSuperAdmin><BillingAdminView /></AdminRoute>} />
                          <Route path="/super-admin/versiones" element={<AdminRoute requireSuperAdmin><VersionManager /></AdminRoute>} />
                          <Route path="/super-admin/monitoring" element={<AdminRoute requireSuperAdmin><MonitoringDashboard /></AdminRoute>} />
                          <Route path="/super-admin/clientes-conecta" element={<AdminRoute requireSuperAdmin><ClientesConectaView /></AdminRoute>} />
                          <Route path="/admin/config" element={<AdminRoute requireSuperAdmin><BillingConfigAdmin /></AdminRoute>} />

                          {/* Rutas de Gestión Fiscal */}
                          <Route path="/fiscal/documentos" element={<DocumentosFiscalesView />} />
                          <Route path="/fiscal/obligaciones" element={<DocumentosFiscalesView />} />
                          <Route path="/aplazamientos" element={<AplazamientosView />} />

                          <Route path="/chat-ia" element={<ChatIA />} />
                          <Route path="/monitor-api" element={<ApiKeysMonitor />} />
                          <Route path="/billing" element={<BillingDashboard />} />

                          <Route path="*" element={<Navigate to="/login" replace />} />
                        </Route>
                      </Routes>

                    </Suspense>
                  </PermisosProvider>
                </ThemeProvider>
              </TenantProvider>
            </QueryClientProvider>
          </AuthProvider>
        } />
      </Routes>
    </>
  );
}