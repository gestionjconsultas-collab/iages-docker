// frontend/src/components/UsuariosView.jsx
import React, { useState, useEffect } from 'react';
import { useUsuarios } from '../hooks/useUsuarios';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
  Users, UserPlus, Shield, CheckCircle, XCircle,
  Edit2, Loader2, AlertTriangle, Briefcase, Building2, AtSign, Key
} from 'lucide-react';
import toast from 'react-hot-toast';
import GestionAccesosModal from './GestionAccesosModal';
import { useAuth } from '../AuthContext';

export default function UsuariosView() {
  const { data, isLoading, refetch } = useUsuarios();
  const { user: currentUser } = useAuth();
  const esInvitado = currentUser?.departamento === 'Invitado';
  const esAdminGrupo = esInvitado && currentUser?.managed_group_ids?.length > 0;

  const users = data?.users || [];
  const departamentos = data?.departamentos || [];
  const [roles, setRoles] = useState([]);
  const [loadingRoles, setLoadingRoles] = useState(false);

  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    departamento_id: '',
    rol_id: '',
    password: ''
  });
  const [selectedUserForAccess, setSelectedUserForAccess] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    refetch();
    cargarRoles();
  }, []);

  const cargarRoles = async () => {
    try {
      setLoadingRoles(true);
      // Solo super-admin puede ver todos los roles, pero los gestores 
      // podrían necesitar ver roles de su gestoría. 
      // Por ahora usamos el endpoint de admin de roles si está disponible.
      const res = await axios.get('/api/admin/roles');
      setRoles(res.data.roles || []);
    } catch (err) {
      console.error("Error al cargar roles:", err);
    } finally {
      setLoadingRoles(false);
    }
  };

  const handleToggleStatus = async (userId) => {
    if (!window.confirm("¿Estás seguro de cambiar el estado de este usuario?")) return;
    try {
      await axios.post(`/api/users/${userId}/toggle-status`, {}, { withCredentials: true });
      toast.success("Estado actualizado");
      refetch();
    } catch (err) {
      toast.error(err.response?.data?.error || "Error al cambiar estado");
    }
  };

  const handleDisable2FA = async (userId) => {
    if (!window.confirm("¿Estás seguro de desactivar la Autenticación de Doble Factor (2FA) para este usuario? Esta acción borrará su configuración actual.")) return;
    try {
      await axios.post(`/api/users/${userId}/disable-2fa`, {}, { withCredentials: true });
      toast.success("2FA desactivado correctamente");
      refetch();
    } catch (err) {
      toast.error(err.response?.data?.error || "Error al desactivar 2FA");
    }
  };

  const handleOpenEdit = (user) => {
    setEditingUser(user.id);
    setFormData({
      departamento_id: user.departamento_id || '',
      rol_id: user.rol_id || '',
      password: ''
    });
  };

  const handleSaveEdit = async (userId) => {
    try {
      const updateData = {
        departamento_id: parseInt(formData.departamento_id) || null
      };

      if (formData.password?.trim()) {
        updateData.password = formData.password.trim();
      }

      // Actualización de depto y password
      await axios.put(`/api/users/${userId}`, updateData, { withCredentials: true });

      // Actualización de rol (vía endpoint RBAC)
      if (formData.rol_id) {
        await axios.put(`/api/admin/usuarios/${userId}/rol`, {
          rol_id: parseInt(formData.rol_id)
        });
      }

      toast.success("Usuario actualizado correctamente");
      setEditingUser(null);
      refetch();
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error || "Error al actualizar usuario");
    }
  };

  if (isLoading) return <div className="flex justify-center p-10"><Loader2 className="animate-spin w-10 h-10 text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Users className="w-8 h-8 text-blue-600" />
            Gestión de Usuarios
          </h1>
          <p className="text-gray-600 mt-1">Administra accesos y departamentos de tu equipo</p>
        </div>
        <button
          onClick={() => navigate('/register')}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center gap-2 shadow-sm"
        >
          <UserPlus className="w-5 h-5" />
          Registrar Nuevo
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Usuario</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Email</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Rol</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase">Departamento</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-center">Estado</th>
                <th className="px-6 py-4 text-xs font-bold text-gray-500 uppercase text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(user => (
                <tr key={user.id} className="hover:bg-gray-50 transition group">
                  <td className="px-6 py-4 font-medium text-gray-900">{user.nombre}</td>
                  <td className="px-6 py-4 text-gray-600 text-sm w-64">
                    <div className="truncate mb-1">{user.email}</div>
                    {editingUser === user.id && !esAdminGrupo && (
                      <input
                        type="password"
                        placeholder="Nueva contraseña (opcional)"
                        value={formData.password}
                        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                        className="mt-1 bg-white border border-gray-300 text-gray-900 text-xs rounded-md focus:ring-blue-500 focus:border-blue-500 block w-full p-1.5"
                        autoComplete="new-password"
                      />
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {editingUser === user.id ? (
                      esAdminGrupo ? (
                        <div className="text-sm text-gray-500 italic">No permitido</div>
                      ) : (
                        <select
                          className="bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2"
                          value={formData.rol_id}
                          onChange={(e) => setFormData({ ...formData, rol_id: e.target.value })}
                        >
                          <option value="">Sin Rol</option>
                          {roles.map(rol => (
                            <option key={rol.id} value={rol.id}>{rol.nombre}</option>
                          ))}
                        </select>
                      )
                    ) : (
                      <div className="flex items-center gap-1.5 capitalize text-sm text-gray-700">
                        <Briefcase className="w-3.5 h-3.5 text-gray-400" />
                        {user.rol_nombre || <span className="text-gray-400 italic font-normal">Sin rol</span>}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {editingUser === user.id ? (
                      esAdminGrupo ? (
                        <div className="text-sm text-gray-500 italic">No permitido</div>
                      ) : (
                        <select
                          className="bg-gray-50 border border-gray-200 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2"
                          value={formData.departamento_id}
                          onChange={(e) => setFormData({ ...formData, departamento_id: e.target.value })}
                        >
                          <option value="">Sin Depto</option>
                          {departamentos.map(dept => (
                            <option key={dept.id} value={dept.id}>{dept.nombre}</option>
                          ))}
                        </select>
                      )
                    ) : (
                      <div className="flex items-center gap-1.5 text-sm text-gray-700">
                        <Building2 className="w-3.5 h-3.5 text-gray-400" />
                        {user.departamento || <span className="text-gray-400 italic font-normal">Sin asignar</span>}
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center">
                    {user.activo ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-green-100 text-green-700 text-xs font-bold uppercase">
                        <CheckCircle className="w-3 h-3" /> Activo
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-100 text-red-700 text-xs font-bold uppercase">
                        <XCircle className="w-3 h-3" /> Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {editingUser === user.id ? (
                        <div className="flex gap-1">
                          <button onClick={() => handleSaveEdit(user.id)} className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-blue-700">Guardar</button>
                          <button onClick={() => setEditingUser(null)} className="bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-gray-200">X</button>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => handleOpenEdit(user)}
                            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setSelectedUserForAccess(user)}
                            className="p-2 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition"
                            title="Gestionar Accesos"
                          >
                            <Key className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleToggleStatus(user.id)}
                            className={`p-2 rounded-lg transition ${user.activo ? 'text-gray-400 hover:text-red-500 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'}`}
                            title={user.activo ? "Desactivar" : "Activar"}
                          >
                            {user.activo ? <Shield className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                          </button>
                          {user.two_factor_enabled && !esAdminGrupo && (
                            <button
                              onClick={() => handleDisable2FA(user.id)}
                              className="p-2 text-red-400 hover:text-white hover:bg-red-500 rounded-lg transition"
                              title="Forzar desactivación del 2FA (Seguridad Alta)"
                            >
                              <AlertTriangle className="w-4 h-4" />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Gestión de Accesos */}
      {selectedUserForAccess && (
        <GestionAccesosModal
          user={selectedUserForAccess}
          onClose={() => setSelectedUserForAccess(null)}
          onSave={() => refetch()}
        />
      )}
    </div>
  );
}