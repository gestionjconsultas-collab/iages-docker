// frontend/src/components/AdminRoute.jsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { ShieldAlert, Home, LogOut } from 'lucide-react';

const AdminRoute = ({ children, requireSuperAdmin = false }) => {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Si no está autenticado
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Lógica de Acceso Administrativo
  const esInvitado = user.departamento === 'Invitado';
  const esAdminGrupo = esInvitado && user.managed_group_ids?.length > 0;

  const canAccessAdmin =
    user.is_super_admin ||
    user.rol_nombre === 'super-admin' ||
    user.rol_nombre === 'admin-gestoria' ||
    user.rol_nombre === 'jefatura' ||
    esAdminGrupo ||
    (user.departamento === 'Soporte' && !user.gestoria_id);

  // Si requiere explícitamente Super-Admin
  const hasSuperAdminAccess = user.is_super_admin || user.rol_nombre === 'super-admin';

  const isAuthorized = requireSuperAdmin ? hasSuperAdminAccess : canAccessAdmin;

  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center border border-red-100">
          <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <ShieldAlert className="w-10 h-10 text-red-600" />
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">Acceso Restringido</h1>
          <p className="text-gray-600 mb-6">
            {requireSuperAdmin
              ? "Esta sección es exclusiva para Super-Administradores del sistema."
              : "No tienes los permisos necesarios para acceder a esta sección de administración."}
          </p>

          <div className="bg-gray-50 rounded-xl p-4 mb-8 text-left space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Tu rol:</span>
              <span className="font-semibold text-gray-900 capitalize">{user.rol_nombre || 'Sin rol'}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Tu departamento:</span>
              <span className="font-semibold text-gray-900">{user.departamento || 'General'}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => window.location.href = '/'}
              className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl font-semibold hover:bg-gray-200 transition-colors"
            >
              <Home className="w-4 h-4" />
              Inicio
            </button>
            <button
              onClick={() => logout()}
              className="flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-xl font-semibold hover:bg-red-700 transition-colors shadow-lg shadow-red-200"
            >
              <LogOut className="w-4 h-4" />
              Salir
            </button>
          </div>

          <p className="mt-8 text-xs text-gray-400">
            Si crees que esto es un error, contacta con el equipo de soporte técnico.
          </p>
        </div>
      </div>
    );
  }

  return children;
};

export default AdminRoute;