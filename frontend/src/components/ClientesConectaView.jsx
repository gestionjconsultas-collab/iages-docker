import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  UserPlus, 
  Mail, 
  Lock, 
  Key, 
  ShieldCheck, 
  Users, 
  CheckCircle2, 
  XCircle, 
  Copy, 
  ExternalLink,
  ChevronRight,
  Plus,
  Pencil
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function ClientesConectaView() {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    plan: 'basico',
    iages_active: false,
    max_certificados: 5
  });
  const [isEditing, setIsEditing] = useState(false);
  const [editTargetId, setEditTargetId] = useState(null);

  const fetchClientes = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/super-admin/clientes-conecta', { withCredentials: true });
      if (res.data.success) {
        setClientes(res.data.clientes);
      }
    } catch (err) {
      toast.error('Error al cargar clientes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClientes();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const url = isEditing 
        ? `/api/super-admin/clientes-conecta/${editTargetId}`
        : '/api/super-admin/clientes-conecta';
      
      const method = isEditing ? 'put' : 'post';
      
      const res = await axios[method](url, formData, { withCredentials: true });
      if (res.data.success) {
        toast.success(isEditing ? 'Cliente actualizado correctamente' : 'Cliente creado correctamente');
        handleCloseModal();
        fetchClientes();
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error en la operación');
    }
  };

  const handleEdit = (cliente) => {
    setEditTargetId(cliente.id);
    setIsEditing(true);
    setFormData({
      email: cliente.email,
      password: '', // No editar password desde aquí por seguridad
      plan: cliente.plan,
      iages_active: cliente.iages_active,
      max_certificados: cliente.max_certificados
    });
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setIsEditing(false);
    setEditTargetId(null);
    setFormData({
      email: '',
      password: '',
      plan: 'basico',
      iages_active: false,
      max_certificados: 5
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copiado al portapapeles');
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Gestión de Clientes Conecta & IAGES</h1>
          <p className="text-gray-500">Administra accesos y planes de suscripción independientes.</p>
        </div>
        <button
          onClick={() => {
            handleCloseModal(); // Reset state
            setShowModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-orange-200/50"
        >
          <Plus className="w-5 h-5 transition-transform group-hover:rotate-90" />
          <span className="font-semibold">Nuevo Cliente</span>
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cliente / Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IAGES</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Límite</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">API Key</th>
                 <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                 <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider text-right">Acciones</th>
               </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {clientes.map((cliente) => (
                <tr key={cliente.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col">
                      <span className="text-sm font-bold text-gray-900">{cliente.nombre || 'Sin nombre'}</span>
                      <span className="text-xs text-gray-500">{cliente.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      cliente.plan === 'premium' ? 'bg-purple-100 text-purple-700' : 
                      cliente.plan === 'plus' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                    }`}>
                      {cliente.plan.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {cliente.iages_active ? (
                      <span className="flex items-center gap-1 text-green-600 text-sm font-medium">
                        <CheckCircle2 className="w-4 h-4" /> Activo
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-gray-400 text-sm">
                        <XCircle className="w-4 h-4" /> Inactivo
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{cliente.max_certificados} cert.</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2 text-xs font-mono bg-gray-50 px-2 py-1 rounded border border-gray-100 max-w-[150px] overflow-hidden truncate">
                      {cliente.api_key}
                      <button onClick={() => copyToClipboard(cliente.api_key)} className="text-gray-400 hover:text-indigo-600">
                        <Copy className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                       <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        cliente.activa ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                       }`}>
                       {cliente.activa ? 'ACTIVO' : 'EXPIRADO'}
                       </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button 
                      onClick={() => handleEdit(cliente)}
                      className="p-1 hover:bg-orange-50 text-gray-400 hover:text-orange-500 rounded transition-colors"
                      title="Editar suscripción"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {clientes.length === 0 && (
                <tr>
                   <td colSpan="7" className="px-6 py-12 text-center text-gray-500 italic">
                    No hay clientes registrados en esta modalidad.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="bg-linear-to-r from-orange-500 to-red-500 p-8 text-white text-center relative">
              <div className="mx-auto w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-4 backdrop-blur-sm">
                <ShieldCheck className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-bold">{isEditing ? 'Editar Suscripción' : 'Nuevo Acceso Conecta'}</h2>
              <p className="text-orange-50 text-sm opacity-90">
                {isEditing ? 'Actualiza los límites y módulos del cliente.' : 'Crea las credenciales y la API Key en un clic.'}
              </p>
              <button 
                onClick={handleCloseModal}
                className="absolute top-4 right-4 text-white/80 hover:text-white transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-8 space-y-5">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Identidad / Email Acceso</label>
                <div className="relative group">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 group-focus-within:text-orange-500 transition-colors" />
                  <input
                    type="email"
                    required
                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none transition-all font-medium"
                    placeholder="ej: cliente@gestoria.com"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Plan</label>
                  <select
                    className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none font-medium transition-all"
                    value={formData.plan}
                    onChange={(e) => setFormData({...formData, plan: e.target.value})}
                  >
                    <option value="basico">Básico</option>
                    <option value="plus">Plus</option>
                    <option value="premium">Premium</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Certificados</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none font-medium transition-all"
                    value={formData.max_certificados}
                    onChange={(e) => setFormData({...formData, max_certificados: parseInt(e.target.value)})}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-orange-50/50 rounded-2xl border border-orange-100/50">
                <div>
                  <h3 className="text-sm font-bold text-orange-900">Activar IAGES</h3>
                  <p className="text-[10px] text-orange-700/80">Habilita panel web de gestión documental.</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer"
                    checked={formData.iages_active}
                    onChange={(e) => setFormData({...formData, iages_active: e.target.checked})}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-linear-to-r peer-checked:from-orange-500 peer-checked:to-red-500"></div>
                </label>
              </div>

              {formData.iages_active && (
                <div className="space-y-1.5 animate-in slide-in-from-top-2 duration-300 bg-gray-50 p-4 rounded-2xl border border-gray-200">
                  <label className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                    <Lock className="w-3 h-3 text-orange-500" />
                    {isEditing ? 'Nueva Contraseña' : 'Establecer Contraseña'}
                  </label>
                  <p className="text-[10px] text-gray-400 mb-2">
                    {isEditing 
                      ? 'Déjala en blanco para no cambiarla.' 
                      : 'Necesaria para que el cliente entre al panel web.'}
                  </p>
                  <div className="relative group">
                    <input
                      type="password"
                      required={!isEditing}
                      className="w-full px-4 py-2.5 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 outline-none transition-all font-medium"
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={(e) => setFormData({...formData, password: e.target.value})}
                    />
                  </div>
                </div>
              )}

               <button
                type="submit"
                className="w-full py-4 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-2xl font-bold hover:from-orange-600 hover:to-red-600 transition-all shadow-lg hover:shadow-orange-200/50 flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <ShieldCheck className="w-5 h-5" />
                {isEditing ? 'Guardar Cambios' : 'Generar Clave de Acceso'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
