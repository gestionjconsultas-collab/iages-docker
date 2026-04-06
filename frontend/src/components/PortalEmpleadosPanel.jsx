import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { UserCheck, UserX, Mail, RotateCcw, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * Panel de gestión del Portal del Empleado.
 * Se muestra en la ficha de empresa (pestaña "Portal Empleados").
 */
export default function PortalEmpleadosPanel({ empresaId }) {
  const [empleados, setEmpleados] = useState([]);
  const [loading, setLoading] = useState(true);
  const [invitando, setInvitando] = useState({});   // { empleadoId: email }
  const [emailInput, setEmailInput] = useState({}); // { empleadoId: string }

  const cargar = useCallback(async () => {
    try {
      const res = await axios.get(`/api/portal/empresas/${empresaId}/empleados`, {
        withCredentials: true,
      });
      setEmpleados(res.data.empleados || []);
    } catch {
      toast.error('Error cargando empleados');
    } finally {
      setLoading(false);
    }
  }, [empresaId]);

  useEffect(() => { cargar(); }, [cargar]);

  const handleInvitar = async (emp) => {
    const email = emailInput[emp.id]?.trim();
    if (!email) {
      toast.error('Introduce el email del empleado');
      return;
    }
    setInvitando(p => ({ ...p, [emp.id]: true }));
    try {
      await axios.post(
        `/api/portal/empleados/${emp.id}/invitar`,
        { email },
        { withCredentials: true }
      );
      toast.success(`Invitación enviada a ${email}`);
      setEmailInput(p => ({ ...p, [emp.id]: '' }));
      await cargar();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al enviar invitación');
    } finally {
      setInvitando(p => ({ ...p, [emp.id]: false }));
    }
  };

  const handleRevocar = async (emp) => {
    if (!confirm(`¿Revocar el acceso al portal de ${emp.nombre}?`)) return;
    try {
      await axios.delete(`/api/portal/empleados/${emp.id}/revocar`, {
        withCredentials: true,
      });
      toast.success('Acceso revocado');
      await cargar();
    } catch {
      toast.error('Error al revocar acceso');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  const activos = empleados.filter(e => e.portal?.activo).length;
  const pendientes = empleados.filter(e => e.portal && !e.portal.activo).length;

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex gap-4">
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          <CheckCircle className="w-4 h-4 text-green-600" />
          <span className="text-sm font-medium text-green-800">{activos} activos</span>
        </div>
        {pendientes > 0 && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
            <Clock className="w-4 h-4 text-amber-600" />
            <span className="text-sm font-medium text-amber-800">{pendientes} pendiente{pendientes !== 1 ? 's' : ''}</span>
          </div>
        )}
      </div>

      {/* Tabla */}
      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Empleado</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">NIF</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Estado portal</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Acciones</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {empleados.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                  <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  No hay empleados registrados en esta empresa
                </td>
              </tr>
            )}
            {empleados.map(emp => (
              <tr key={emp.id} className="hover:bg-gray-50 transition">
                <td className="px-4 py-3 font-medium text-gray-900">{emp.nombre}</td>
                <td className="px-4 py-3 text-gray-500 font-mono text-xs">{emp.nif}</td>
                <td className="px-4 py-3">
                  <EstadoBadge portal={emp.portal} />
                </td>
                <td className="px-4 py-3">
                  {emp.portal?.activo ? (
                    // Ya tiene acceso → revocar
                    <button
                      onClick={() => handleRevocar(emp)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                                 text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition border border-red-200"
                    >
                      <UserX className="w-3.5 h-3.5" />
                      Revocar
                    </button>
                  ) : emp.portal && !emp.portal.activo ? (
                    // Pendiente → reenviar
                    <button
                      onClick={() => handleInvitar(emp)}
                      disabled={!!invitando[emp.id]}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                                 text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-lg transition border border-amber-200"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reenviar
                    </button>
                  ) : (
                    // Sin acceso → invitar
                    <div className="flex items-center gap-2">
                      <input
                        type="email"
                        placeholder="email@ejemplo.com"
                        value={emailInput[emp.id] || ''}
                        onChange={e => setEmailInput(p => ({ ...p, [emp.id]: e.target.value }))}
                        onKeyDown={e => e.key === 'Enter' && handleInvitar(emp)}
                        className="text-xs px-2 py-1.5 border border-gray-300 rounded-lg
                                   focus:outline-none focus:ring-1 focus:ring-blue-500 w-44"
                      />
                      <button
                        onClick={() => handleInvitar(emp)}
                        disabled={!!invitando[emp.id]}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                                   text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition
                                   disabled:opacity-50"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        {invitando[emp.id] ? 'Enviando...' : 'Invitar'}
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EstadoBadge({ portal }) {
  if (!portal) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 text-xs font-medium">
        Sin acceso
      </span>
    );
  }
  if (portal.activo) {
    return (
      <div>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
          <CheckCircle className="w-3 h-3" />
          Activo
        </span>
        {portal.ultimo_acceso && (
          <p className="text-xs text-gray-400 mt-0.5">
            Último acceso: {new Date(portal.ultimo_acceso).toLocaleDateString('es-ES')}
          </p>
        )}
      </div>
    );
  }
  return (
    <div>
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium">
        <Clock className="w-3 h-3" />
        Pendiente activación
      </span>
      <p className="text-xs text-gray-400 mt-0.5">{portal.email}</p>
    </div>
  );
}
