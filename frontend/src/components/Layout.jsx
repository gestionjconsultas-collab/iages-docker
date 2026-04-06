// frontend/src/components/Layout.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Outlet, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { useTenant } from '../contexts/TenantContext';
import { usePermisos } from '../contexts/PermisosContext';
import axios from 'axios';
import { BACKEND_URL } from '../utils/urls';
import {
  Building2, Home, Users, LogOut, Menu, X, Search, Bell,
  Calendar, ChevronDown, Briefcase, ShieldCheck, Info,
  LayoutTemplate, FileText, User, Settings, Inbox, Zap, TrendingUp, FileCheck, FolderOpen, Receipt, CreditCard, MessageSquare, Activity, MessageCircle,
  Phone, Mail, Facebook, Linkedin, Key, BarChart3, DollarSign, Megaphone, Monitor, Flag
} from 'lucide-react';
import { FaChartLine } from 'react-icons/fa';
import PerfilModal from './PerfilModal';
import PreferenciasModal from './PreferenciasModal';
import ThemeToggle from './ThemeToggle';
import useHotkeys from '../hooks/useHotkeys';
import ShortcutsHelp from './ShortcutsHelp';
import FloatingChatBubble from './FloatingChatBubble';
import WidgetSoporte from './WidgetSoporte';
import NotificationPermissionBanner from './NotificationPermissionBanner'; // ⭐ NUEVO
import socket from '../socket'; // ⭐ Import socket

export default function Layout() {
  const { user, logout } = useAuth();
  const { tenant } = useTenant();
  const { tienePermiso } = usePermisos();
  const navigate = useNavigate();
  const location = useLocation();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tareasCount, setTareasCount] = useState(0); // Keeping tareasCount as it's used later
  const [notificaciones, setNotificaciones] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0); // New state for unread count
  const [showNotifications, setShowNotifications] = useState(false); // Renamed from showNotificaciones

  // Menús y Modales
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showPerfilModal, setShowPerfilModal] = useState(false);
  const [showPreferenciasModal, setShowPreferenciasModal] = useState(false);
  const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);
  const [gestionDocumentalOpen, setGestionDocumentalOpen] = useState(false);
  const [gestionFiscalOpen, setGestionFiscalOpen] = useState(false);
  const [gestionAdministrativaOpen, setGestionAdministrativaOpen] = useState(false);
  const [zonaEmpresaOpen, setZonaEmpresaOpen] = useState(false);

  const notificationsRef = useRef(null); // Renamed from notifRef
  const userMenuRef = useRef(null);

  // Logo dinámico del tenant
  const getLogoUrl = () => {
    const logoPath = tenant?.configuracion?.branding?.logo_url;
    if (logoPath) {
      return `${BACKEND_URL}${logoPath}`;
    }
    return '/logo-light.png'; // Fallback
  };

  const logoUrl = getLogoUrl();
  const tenantName = tenant?.nombre || 'IAGES';

  // Función para fetch de contadores
  const fetchData = () => {
    axios.get('/api/tareas/conteo', { withCredentials: true })
      .then(res => {
        if (res.data.success) {
          setTareasCount(res.data.total || 0);
        }
      })
      .catch(err => {
        console.error('Error fetching tareas:', err);
        setTareasCount(0);
      });

    axios.get('/api/notificaciones', { withCredentials: true })
      .then(res => {
        if (res.data.success) {
          const notifs = Array.isArray(res.data.notificaciones) ? res.data.notificaciones : [];
          setNotificaciones(notifs);
          setUnreadCount(notifs.filter(n => !n.leida).length);
        }
      })
      .catch(err => {
        console.error('Error fetching notificaciones:', err);
        setNotificaciones([]);
        setUnreadCount(0);
      });
  };

  // ⭐ Función para actualizar título de pestaña con contador
  const updateTabTitle = (count) => {
    const baseTitle = tenantName || 'IAGES';
    document.title = count > 0 ? `(${count}) ${baseTitle}` : baseTitle;
  };

  // ⭐ Función para vibración móvil
  const vibrate = (pattern = [200]) => {
    // Respetar preferencias del usuario
    if (localStorage.getItem('vibrationEnabled') === 'false') return;

    if ('vibrate' in navigator) {
      navigator.vibrate(pattern);
    }
  };

  // ⭐ Función para mostrar notificación del navegador (Mejorada para móviles)
  const showBrowserNotification = async (titulo, mensaje, link) => {
    // Solo si está en segundo plano y tiene permiso
    if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
      try {
        // En móviles (Android) es obligatorio usar el Service Worker registration
        const registration = await navigator.serviceWorker.ready;
        if (registration && registration.showNotification) {
          registration.showNotification(titulo, {
            body: mensaje,
            icon: '/logo-light.png',
            badge: '/notification-badge.png',
            tag: 'iages-notification',
            data: { link }, // Guardar el link para el click
            vibrate: [200, 100, 200]
          });
        }
      } catch (err) {
        console.warn('Error al mostrar notificación via SW, intentando fallback:', err);
        // Fallback para navegadores antiguos (solo PC)
        try {
          new Notification(titulo, { body: mensaje, icon: '/logo-light.png' });
        } catch (e) {
          console.error('Notificaciones no soportadas en este dispositivo');
        }
      }
    }
  };

  useEffect(() => {
    // ⭐ FORZAR RESET DE PUSH (Solo una vez tras cambio de VAPID)
    const VAPID_VERSION = 'v2'; // Cambiar esto si se vuelven a regenerar llaves
    if (localStorage.getItem('vapid_version') !== VAPID_VERSION) {
      console.log('🔄 VAPID Key Change detected: Clearing old registration flags...');
      localStorage.removeItem('pushRegistered');
      localStorage.removeItem('notificationBannerDismissed');
      localStorage.setItem('vapid_version', VAPID_VERSION);
    }

    fetchData();
    const interval = setInterval(fetchData, 60000); // 60s en lugar de 30s para evitar rate limiting

    // ⭐ Auto-refresh: Escuchar evento stats_updated
    socket.on('stats_updated', () => {
      console.log('🔔 Stats updated, refetching counters...');
      fetchData();
    });

    // ⭐ Conectarse al room de la gestoría
    if (user?.gestoria_id && !user.is_invitado && user.departamento !== 'Invitado') {
      console.log(`🔌 Conectando a room: gestoria_staff_${user.gestoria_id}`);
      socket.emit('join_gestoria', { gestoria_id: user.gestoria_id, is_staff: true });
    }

    // ⭐ Conectarse al room de las empresas si es invitado
    if (user?.empresa_ids?.length > 0) {
      console.log(`🔌 Conectando a rooms de empresas: ${user.empresa_ids.join(', ')}`);
      socket.emit('join_empresas', { empresa_ids: user.empresa_ids });
    }

    // ⭐ NUEVO: Escuchar notificaciones en tiempo real con sistema anti-duplicados
    const renderedNotifs = new Set(); // Temporal en este mount para evitar re-procesar el mismo evento en milisegundos

    socket.on('nueva_notificacion', (notificacion) => {
      // Evitar procesar la misma notificación si llega por múltiples rooms (ej: user_id y gestoria_staff)
      const notifId = notificacion.id || `temp-${notificacion.fecha}-${notificacion.mensaje.length}`;
      if (renderedNotifs.has(notifId)) {
        console.log('🚫 Notificación duplicada omitida:', notifId);
        return;
      }
      renderedNotifs.add(notifId);

      console.log('📬 Nueva notificación recibida:', notificacion);

      // Agregar notificación a la lista
      setNotificaciones(prev => [notificacion, ...prev]);
      setUnreadCount(prev => prev + 1);

      // ⭐ Vibración móvil
      vibrate([200]);

      // ⭐ Notificación del navegador (si está en segundo plano)
      showBrowserNotification(
        notificacion.titulo,
        notificacion.mensaje,
        notificacion.link
      );

      // Mostrar toast notification (opcional)
      if (window.toast) {
        window.toast.info(`📬 ${notificacion.titulo}`);
      }
    });

    // Cleanup
    return () => {
      clearInterval(interval);
      socket.off('stats_updated');
      socket.off('nueva_notificacion');
    };
  }, [location.pathname, user]);

  // ⭐ Actualizar título de pestaña cuando cambia unreadCount
  useEffect(() => {
    updateTabTitle(unreadCount);
  }, [unreadCount, tenantName]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) setShowNotifications(false); // Updated ref and state
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) setShowUserMenu(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const marcarComoLeida = async (id, link, isComunicado = false) => {
    try {
      if (isComunicado) {
        // Extraer ID numérico de "com-123"
        const numericId = typeof id === 'string' ? id.split('-')[1] : id;
        await axios.post(`/api/comunicados/${numericId}/leer`, {}, { withCredentials: true });
      } else {
        await axios.post(`/api/notificaciones/${id}/leer`, {}, { withCredentials: true });
      }

      setNotificaciones(prev => prev.filter(n => n.id !== id));
      setUnreadCount(prev => Math.max(0, prev - 1));

      if (link) {
        navigate(link);
        setShowNotifications(false);
      }
    } catch (error) {
      console.error('Error al marcar como leída:', error);
    }
  };

  // Atajos de teclado globales
  useHotkeys({
    'ctrl+i': () => navigate('/importar'),
    'ctrl+b': () => navigate('/empresas'),
    'ctrl+m': () => navigate('/mesa-trabajo'),
    'escape': () => {
      setShowNotifications(false); // Updated state
      setShowUserMenu(false);
    },
    '?': () => setShowShortcutsHelp(true)
  });

  // ✅ CONSTRUCCIÓN DEL MENÚ BASADO EN TIPO DE USUARIO
  const menuItems = [];

  // Detectar tipo de usuario
  const esSoporte = user?.departamento === 'Soporte' && !user?.gestoria_id;
  const esSuperAdmin = user?.is_super_admin;
  const esUsuarioNormal = !esSoporte && !esSuperAdmin;
  const esInvitado = user?.departamento === 'Invitado';
  const esAdminGrupo = esInvitado && user?.managed_group_ids?.length > 0;

  // 🛠️ MENÚ PARA SOPORTE (solo gestión de soporte)
  if (esSoporte) {
    menuItems.push(
      { icon: MessageCircle, label: 'Gestión de Soporte', path: '/gestion-soporte', section: 'SOPORTE' }
    );
  }

  // 👑 MENÚ PARA SUPERADMIN
  else if (esSuperAdmin) {
    menuItems.push(
      // ⭐ Super-Admin Dashboard
      { icon: TrendingUp, label: 'Dashboard Global', path: '/super-admin/dashboard', section: 'SUPER ADMIN' },
      { icon: Monitor, label: 'Monitoreo del Sistema', path: '/super-admin/monitoring', section: 'SUPER ADMIN' },
      { icon: Building2, label: 'Gestión de Gestorías', path: '/super-admin/gestorias', section: 'SUPER ADMIN' },
      { icon: Users, label: 'Clientes Conecta', path: '/super-admin/clientes-conecta', section: 'SUPER ADMIN' },
      { icon: DollarSign, label: 'Gestión de Planes', path: '/super-admin/planes', section: 'SUPER ADMIN' },
      { icon: Megaphone, label: 'Banners Promocionales', path: '/super-admin/banners', section: 'SUPER ADMIN' },
      { icon: CreditCard, label: 'Facturación', path: '/super-admin/billing', section: 'SUPER ADMIN' },
      { icon: Zap, label: 'Gestor de Versiones', path: '/super-admin/versiones', section: 'SUPER ADMIN' },
      // Flower - Monitoreo de Tareas Celery
      {
        icon: Activity,
        label: 'Monitoreo de Tareas',
        path: '/flower/',
        section: 'SUPER ADMIN',
        isExternal: true  // Indica que es un enlace externo
      },

      // Administración
      { icon: MessageCircle, label: 'Gestión de Soporte', path: '/gestion-soporte', section: 'ADMINISTRACIÓN' },
      { icon: FaChartLine, label: 'Auditoría del Sistema', path: '/auditoria', section: 'ADMINISTRACIÓN' },
      { icon: ShieldCheck, label: 'Gestión Usuarios', path: '/super-admin/usuarios-sistema', section: 'ADMINISTRACIÓN' },
      { icon: ShieldCheck, label: 'Roles y Permisos', path: '/admin/roles-permisos', section: 'ADMINISTRACIÓN' },
      { icon: Settings, label: 'Configuración Global', path: '/admin/config', section: 'ADMINISTRACIÓN' }
    );
  }

  // 👤 MENÚ PARA USUARIO NORMAL (con gestoría)
  else if (esUsuarioNormal) {
    menuItems.push(
      ...(!esInvitado ? [
        { icon: Zap, label: 'Mesa de Trabajo', path: '/mesa-trabajo', section: 'PRINCIPAL' },
        { icon: Mail, label: 'Correos Pendientes', path: '/emails-pendientes', section: 'PRINCIPAL' }
      ] : [
        { icon: Home, label: 'Muro de Novedades', path: '/inicio', section: 'PRINCIPAL' }
      ]),
      {
        icon: Building2,
        label: 'Zona Empresa',
        path: '#zona-empresa',
        section: 'ZONA EMPRESA',
        isCollapsible: true,
        stateKey: 'zonaEmpresa',
        subItems: [
          { icon: Building2, label: 'Mis empresas', path: '/empresas' },
          ...(!esInvitado ? [
            { icon: Users, label: 'Agrupaciones', path: '/grupos-empresas' }
          ] : [])
        ]
      },
      ...(!esInvitado ? [
        { icon: Inbox, label: 'Notificaciones DEHU', path: '/saltra', section: 'DEHU' },
        { icon: Flag, logo: '/conecta-logo.png', label: 'Conecta', path: '/dehu-espana', section: 'DEHU' },
        {
          icon: FileText,
          label: 'Control y Gestión',
          path: '#control-gestion',
          section: 'DOCUMENTACIÓN',
          isCollapsible: true,
          stateKey: 'gestionDocumental',
          subItems: [
            { icon: FileCheck, label: 'Comprobar Seguros y Nóminas', path: '/comprobar-seguros-nominas' },
            { icon: FolderOpen, label: 'Grupos de Documentos', path: '/grupos' },
            { icon: CreditCard, label: 'Aplazamientos e Inspecciones', path: '/aplazamientos' }
          ]
        },
        { icon: Briefcase, label: 'Gestión Contable', path: '#', section: 'DOCUMENTACIÓN', disabled: true }
      ] : [])
    );
  }

  // ✅ MENÚS DINÁMICOS ADICIONALES BASADOS EN PERMISOS RBAC (solo para usuarios normales no invitados)
  // ⭐ EXCEPCIÓN: Admins de Grupo pueden ver Gestión Usuarios
  if (esUsuarioNormal && (!esInvitado || esAdminGrupo)) {

    // Auditoría del Sistema (permiso: audit.view)
    // Se movió a Gestión Administrativa

    // Gestión Administrativa Avanzada - construir dinámicamente según permisos
    const subItemsAdmin = [];

    // Dashboard Métricas y Dashboard General
    if (user?.is_super_admin) {
      subItemsAdmin.push({
        icon: Activity,
        label: 'Dashboard Métricas',
        path: '/admin/metrics'
      });
    }

    // Dashboard General para Jefatura/Admin
    if (!esInvitado) {
      subItemsAdmin.push({ icon: TrendingUp, label: 'Dashboard', path: '/dashboard' });
      subItemsAdmin.push({ icon: BarChart3, label: 'Productividad', path: '/productividad' });
      subItemsAdmin.push({ icon: MessageCircle, label: 'Soporte', path: '/soporte' });
      subItemsAdmin.push({ icon: CreditCard, label: 'Facturación', path: '/billing' });
    }

    // Auditoría del Sistema (permiso: audit.view)
    if (tienePermiso('audit.view') && !esInvitado) {
      subItemsAdmin.push({
        icon: FaChartLine,
        label: 'Auditoría',
        path: '/auditoria'
      });
    }

    // Gestión de Usuarios
    if (tienePermiso('users.view') || esAdminGrupo) {
      subItemsAdmin.push({
        icon: ShieldCheck,
        label: 'Gestión Usuarios',
        path: '/usuarios'
      });
    }

    // Plantillas IA
    if (tienePermiso('templates.view')) {
      subItemsAdmin.push({
        icon: LayoutTemplate,
        label: 'Plantillas IA',
        path: '/plantillas'
      });
    }

    // Chat IA
    if (tienePermiso('chat.view')) {
      subItemsAdmin.push({
        icon: MessageSquare,
        label: 'Chat IA',
        path: '/chat-ia'
      });
    }

    // API Monitor
    if (tienePermiso('api.view')) {
      subItemsAdmin.push({
        icon: Activity,
        label: 'API Monitor',
        path: '/monitor-api'
      });
    }

    // Gestión de Soporte
    if (tienePermiso('support.view')) {
      subItemsAdmin.push({
        icon: MessageCircle,
        label: 'Gestión de Soporte',
        path: '/gestion-soporte'
      });
    }

    // Solo agregar el menú si hay al menos un subitem
    if (subItemsAdmin.length > 0) {
      menuItems.push({
        icon: Settings,
        label: 'Gestión Administrativa',
        path: '#gestion-administrativa',
        section: 'ADMINISTRACIÓN',
        isCollapsible: true,
        stateKey: 'gestionAdministrativa',
        subItems: subItemsAdmin
      });
    }

    // ✅ GESTIÓN DE ROLES Y PERMISOS (permiso: roles.view)
    if (tienePermiso('roles.view')) {
      menuItems.push({
        icon: ShieldCheck,
        label: 'Roles y Permisos',
        path: '/admin/roles-permisos',
        section: 'SUPER ADMIN'
      });
    }

    // ✅ ADMINISTRACIÓN SALTRA (solo super-admin)
    if (user?.is_super_admin) {
      menuItems.push({
        icon: Key,
        label: 'Admin SALTRA',
        path: '/admin/saltra',
        section: 'SUPER ADMIN'
      });
    }
  } // ⭐ Cierre del bloque esUsuarioNormal

  const handleNavigation = (path, disabled, isCollapsible, stateKey, isExternal) => {
    if (disabled || path === '#') return;
    if (isCollapsible) {
      // Toggle el estado correcto según el stateKey
      if (stateKey === 'gestionDocumental') {
        setGestionDocumentalOpen(!gestionDocumentalOpen);
      } else if (stateKey === 'gestionFiscal') {
        setGestionFiscalOpen(!gestionFiscalOpen);
      } else if (stateKey === 'gestionAdministrativa') {
        setGestionAdministrativaOpen(!gestionAdministrativaOpen);
      } else if (stateKey === 'zonaEmpresa') {
        setZonaEmpresaOpen(!zonaEmpresaOpen);
      }
      return;
    }
    if (isExternal) {
      window.open(path, '_blank');
      return;
    }
    navigate(path);
    setSidebarOpen(false);
  };

  const isActive = (path) => {
    if (path === '/#' || path === '#gestion-documental' || path === '#gestion-fiscal' || path === '#gestion-administrativa') return false;
    return path === '/' ? location.pathname === '/' : location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ⭐ Banner de Permisos de Notificaciones */}
      <NotificationPermissionBanner />

      {/* SIDEBAR */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 flex flex-col ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Logo */}
        <div className="flex-shrink-0 h-36 flex items-center justify-center px-6 pt-3 border-b border-gray-200">
          <img
            src={logoUrl}
            alt={tenantName}
            className="h-34 w-auto object-contain max-w-full"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextElementSibling.style.display = 'flex';
            }}
          />
          <span className="text-xl font-bold text-gray-800" style={{ display: 'none' }}>
            {tenantName}
          </span>
          <div className="hidden items-center gap-2">
            <div className="text-2xl font-bold">
              <span className="text-gray-800">Spain</span>
              <span className="text-primary">Flow</span>
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* User Info */}
        <div className="flex-shrink-0 px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center text-white font-semibold">
              {user?.nombre?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {user?.nombre || 'Usuario'}
              </p>
              <p className="text-xs text-gray-500 truncate capitalize">
                {user?.rol_nombre || user?.departamento || 'Sin rol'}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto custom-scrollbar">
          {menuItems.map((item, index) => (
            <React.Fragment key={item.path}>
              {/* Section Header */}

              {/* Menu Item */}
              <button
                onClick={() => handleNavigation(item.path, item.disabled, item.isCollapsible, item.stateKey, item.isExternal)}
                disabled={item.disabled}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${isActive(item.path)
                  ? 'bg-linear-to-r from-orange-500 to-red-500 text-white shadow-md'
                  : item.disabled
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-gray-700 hover:bg-gray-100'
                  }`}
              >
                {item.logo ? (
                  <img src={item.logo} alt={item.label} className={`w-5 h-auto object-contain ${isActive(item.path) ? 'brightness-0 invert' : ''}`} />
                ) : (
                  <item.icon className={`w-5 h-5 ${isActive(item.path) ? 'text-white' : ''}`} />
                )}
                <span>{item.label}</span>
                {item.isCollapsible && (
                  <ChevronDown className={`ml-auto w-4 h-4 transition-transform ${item.stateKey === 'gestionDocumental' ? (gestionDocumentalOpen ? 'rotate-180' : '') :
                    item.stateKey === 'gestionFiscal' ? (gestionFiscalOpen ? 'rotate-180' : '') :
                      item.stateKey === 'gestionAdministrativa' ? (gestionAdministrativaOpen ? 'rotate-180' : '') :
                        item.stateKey === 'zonaEmpresa' ? (zonaEmpresaOpen ? 'rotate-180' : '') : ''
                    }`} />
                )}
                {item.disabled && (
                  <span className="ml-auto text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                    Próximamente
                  </span>
                )}
              </button>

              {/* Sub-items (if collapsible) */}
              {item.isCollapsible && item.subItems && (
                (item.stateKey === 'gestionDocumental' && gestionDocumentalOpen) ||
                (item.stateKey === 'gestionFiscal' && gestionFiscalOpen) ||
                (item.stateKey === 'gestionAdministrativa' && gestionAdministrativaOpen) ||
                (item.stateKey === 'zonaEmpresa' && zonaEmpresaOpen)
              ) && (
                  <div className="ml-8 mt-1 space-y-1">
                    {item.subItems.map((subItem, idx) => (
                      subItem.isHeader ? (
                        <div key={`header-${idx}`} className="px-3 pt-3 pb-1">
                          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest leading-none">
                            {subItem.label}
                          </span>
                        </div>
                      ) : (
                        <button
                          key={subItem.path}
                          onClick={() => handleNavigation(subItem.path, false, false)}
                          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${isActive(subItem.path)
                            ? 'bg-primary-light text-primary-hover'
                            : 'text-gray-600 hover:bg-gray-50'
                            }`}
                        >
                          <subItem.icon className="w-4 h-4" />
                          <span>{subItem.label}</span>
                        </button>
                      )
                    ))}
                  </div>
                )}
            </React.Fragment>
          ))}
        </nav>


        {/* Bottom Section: Footer + Logout */}
        <div className="flex-shrink-0 bg-white border-t border-gray-200">
          {/* Footer con info del tenant */}
          <div className="px-3 py-3 border-b border-gray-100 bg-gray-50/50">
            {tenant?.configuracion?.contacto && (
              <div className="space-y-2 text-xs text-gray-600 mb-3">
                {tenant.configuracion.contacto.telefono && (
                  <div className="flex items-center gap-2">
                    <Phone className="w-3 h-3 shrink-0" />
                    <span className="truncate">{tenant.configuracion.contacto.telefono}</span>
                  </div>
                )}
                {tenant.configuracion.contacto.email && (
                  <div className="flex items-center gap-2">
                    <Mail className="w-3 h-3 shrink-0" />
                    <span className="truncate">{tenant.configuracion.contacto.email}</span>
                  </div>
                )}
              </div>
            )}

            {/* Copyright */}
            <div className="text-[10px] text-gray-500 text-center mb-2">
              {tenant?.configuracion?.personalizacion?.texto_footer ||
                `© ${new Date().getFullYear()} ${tenant?.nombre || 'IAGES'}`}
            </div>

            {/* Redes sociales */}
            {tenant?.configuracion?.redes_sociales && (
              <div className="flex justify-center gap-3">
                {tenant.configuracion.redes_sociales.facebook && (
                  <a href={tenant.configuracion.redes_sociales.facebook}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-blue-600 transition-colors">
                    <Facebook className="w-4 h-4" />
                  </a>
                )}
                {tenant.configuracion.redes_sociales.linkedin && (
                  <a href={tenant.configuracion.redes_sociales.linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-400 hover:text-blue-700 transition-colors">
                    <Linkedin className="w-4 h-4" />
                  </a>
                )}
              </div>
            )}
          </div>

          {/* Logout Button */}
          <div className="p-3 bg-white">
            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              <LogOut className="w-5 h-5" />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="lg:pl-64">
        {/* Header */}
        <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              {/* Mobile Menu Button */}
              <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden p-2 rounded-lg hover:bg-gray-100"
              >
                <Menu className="w-6 h-6 text-gray-600" />
              </button>

              {/* Header Title (Optional) */}
              <div className="flex-1 px-4 lg:px-0">
                <h2 className="text-lg font-semibold text-gray-800 hidden sm:block">
                  {tenantName}
                </h2>
              </div>

              {/* Right Icons */}
              <div className="flex items-center gap-2">
                {/* Theme Toggle */}
                <ThemeToggle />
                {/* Calendar Button */}
                <button
                  onClick={() => navigate('/calendario')}
                  className="p-2 rounded-lg hover:bg-gray-100 relative hidden sm:block group"
                  title="Calendario de Tareas"
                >
                  <Calendar className="w-6 h-6 text-gray-600 group-hover:text-primary transition-colors" />
                  {tareasCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-white">
                      {tareasCount > 99 ? '99+' : tareasCount}
                    </span>
                  )}
                </button>

                {/* Notifications */}
                <div className="relative" ref={notificationsRef}>
                  <button
                    onClick={() => setShowNotifications(!showNotifications)}
                    className="p-2 rounded-lg hover:bg-gray-100 relative"
                  >
                    <Bell className="w-6 h-6 text-gray-600" />
                    {(notificaciones?.length || 0) > 0 && (
                      <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white"></span>
                    )}
                  </button>

                  {showNotifications && (
                    <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-100 py-2 z-50">
                      <div className="px-4 py-2 border-b border-gray-100 flex justify-between items-center">
                        <h3 className="font-semibold text-gray-900">Notificaciones</h3>
                        <span className="text-xs text-gray-500">{notificaciones?.length || 0} nuevas</span>

                      </div>
                      <div className="max-h-96 overflow-y-auto">
                        {(notificaciones?.length || 0) === 0 ? (

                          <div className="p-8 text-center text-gray-500 text-sm">
                            No tienes notificaciones nuevas
                          </div>
                        ) : (
                          notificaciones.map(noti => (
                            <div
                              key={noti.id}
                              onClick={() => marcarComoLeida(noti.id, noti.link, noti.is_comunicado)}
                              className={`px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-50 last:border-0 transition-colors ${noti.is_comunicado ? 'bg-orange-50/30' : ''}`}
                            >
                              <div className="flex items-start gap-3">
                                <div className="mt-1">
                                  {noti.is_comunicado ? (
                                    <Megaphone className="w-5 h-5 text-orange-500" />
                                  ) : (
                                    <Info className="w-5 h-5 text-blue-500" />
                                  )}
                                </div>
                                <div>
                                  <p className="text-sm font-medium text-gray-900">
                                    {noti.titulo}
                                  </p>
                                  <p className="text-xs text-gray-600 mt-0.5">
                                    {noti.mensaje}
                                  </p>
                                  <p className="text-[10px] text-gray-400 mt-2">
                                    {new Date(noti.fecha).toLocaleString()}
                                  </p>
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* User Menu */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="w-8 h-8 rounded-full bg-linear-to-br from-orange-400 to-red-500 flex items-center justify-center text-white text-sm font-bold shadow-sm">
                      {user?.nombre?.charAt(0) || 'U'}
                    </div>
                    <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform duration-200 hidden sm:block ${showUserMenu ? 'rotate-180' : ''
                      }`} />
                  </button>

                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                      <div className="px-4 py-3 border-b border-gray-100">
                        <p className="text-sm font-semibold text-gray-900 truncate">
                          {user?.nombre}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {user?.email}
                        </p>
                        <span className="mt-2 inline-block px-2 py-0.5 bg-primary-light text-primary-hover text-[10px] font-bold uppercase rounded-full border border-orange-100">
                          {user?.departamento}
                        </span>
                      </div>
                      <div className="py-1">
                        <button
                          onClick={() => {
                            setShowPerfilModal(true);
                            setShowUserMenu(false);
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary flex items-center gap-2"
                        >
                          <User className="w-4 h-4" /> Mi Perfil
                        </button>
                        <button
                          onClick={() => {
                            setShowPreferenciasModal(true);
                            setShowUserMenu(false);
                          }}
                          className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary flex items-center gap-2"
                        >
                          <Settings className="w-4 h-4" /> Preferencias
                        </button>
                      </div>
                      <div className="border-t border-gray-100 my-1"></div>
                      <button
                        onClick={logout}
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <LogOut className="w-4 h-4" /> Cerrar Sesión
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
            {/* Modals */}
            {showPerfilModal && <PerfilModal onClose={() => setShowPerfilModal(false)} />}
            {showPreferenciasModal && <PreferenciasModal onClose={() => setShowPreferenciasModal(false)} />}
            {showShortcutsHelp && <ShortcutsHelp onClose={() => setShowShortcutsHelp(false)} />}
          </div>
        </header>

        {/* Page Content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>

      {/* Modals */}
      {showPerfilModal && <PerfilModal onClose={() => setShowPerfilModal(false)} />}
      {showPreferenciasModal && <PreferenciasModal onClose={() => setShowPreferenciasModal(false)} />}

      {/* Floating Chat Bubble - Ocultar para invitados */}
      {!esInvitado && <FloatingChatBubble />}

      {/* Widget de Soporte - Ocultar para invitados */}
      {!esInvitado && <WidgetSoporte />}
    </div>
  );
}