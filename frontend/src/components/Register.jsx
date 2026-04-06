// frontend/src/components/Register.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../utils/axiosConfig';
import {
  Eye, EyeOff, Lock, Mail, User, ChevronLeft, AlertCircle,
  Loader2, CheckCircle, Building2, Shield, Briefcase,
  FileText, Users, Crown, UserMinus
} from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function Register() {
  const [formData, setFormData] = useState({
    nombre: '',
    email: '',
    password: '',
    confirmPassword: '',
    departamento_id: ''
  });
  const [departamentos, setDepartamentos] = useState([]);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingDepartamentos, setLoadingDepartamentos] = useState(true);
  const { user: currentUser } = useAuth();
  const esInvitado = currentUser?.departamento === 'Invitado';
  const esAdminGrupo = esInvitado && currentUser?.managed_group_ids?.length > 0;

  const navigate = useNavigate();

  // Iconos para cada departamento
  const departamentoIcons = {
    'General': Users,
    'Fiscal': FileText,
    'Laboral': Briefcase,
    'Administrativo': Building2,
    'Jefatura': Crown,
    'Invitado': UserMinus
  };

  // Colores para cada departamento
  const departamentoColors = {
    'General': 'from-gray-100 to-gray-200 text-gray-700 border-gray-300',
    'Fiscal': 'from-blue-100 to-blue-200 text-blue-700 border-blue-300',
    'Laboral': 'from-green-100 to-green-200 text-green-700 border-green-300',
    'Administrativo': 'from-purple-100 to-purple-200 text-purple-700 border-purple-300',
    'Jefatura': 'from-orange-100 to-orange-200 text-primary-hover border-orange-300',
    'Invitado': 'from-indigo-100 to-indigo-200 text-indigo-700 border-indigo-300'
  };

  useEffect(() => {
    cargarDepartamentos();
  }, []);

  const cargarDepartamentos = async () => {
    try {
      setLoadingDepartamentos(true);
      const response = await axios.get('/api/departamentos', {
        withCredentials: true
      });
      if (response.data.success) {
        let depts = response.data.departamentos || [];

        // Si es admin de grupo, filtrar solo "Invitado"
        if (esAdminGrupo) {
          depts = depts.filter(d => d.nombre === 'Invitado');
          if (depts.length > 0) {
            setFormData(prev => ({ ...prev, departamento_id: depts[0].id.toString() }));
          }
        }

        setDepartamentos(depts);
      }
    } catch (err) {
      console.error('Error al cargar departamentos:', err);
      setError('No se pudieron cargar los departamentos disponibles');
    } finally {
      setLoadingDepartamentos(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Limpiar errores al escribir
    setError('');
    setSuccess('');
  };

  const validateForm = () => {
    if (!formData.nombre.trim()) {
      setError('El nombre es obligatorio');
      return false;
    }
    if (!formData.email.trim()) {
      setError('El email es obligatorio');
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      setError('El email no es válido');
      return false;
    }
    if (formData.password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return false;
    }
    if (formData.password !== formData.confirmPassword) {
      setError('Las contraseñas no coinciden');
      return false;
    }
    if (!formData.departamento_id) {
      setError('Debe seleccionar un departamento/rol');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post('/api/auth/register', {
        nombre: formData.nombre,
        email: formData.email,
        password: formData.password,
        departamento_id: parseInt(formData.departamento_id)
      }, { withCredentials: true });

      if (response.data.success) {
        setSuccess(`Usuario ${formData.nombre} creado exitosamente`);
        // Limpiar formulario
        setFormData({
          nombre: '',
          email: '',
          password: '',
          confirmPassword: '',
          departamento_id: ''
        });
        // Opcionalmente redirigir después de 2 segundos
        setTimeout(() => {
          navigate('/');
        }, 2000);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || 'Error al crear el usuario';
      setError(errorMsg);
      console.error('Error de registro:', err);
    } finally {
      setLoading(false);
    }
  };

  const departamentoSeleccionado = departamentos.find(
    d => d.id.toString() === formData.departamento_id
  );

  return (
    <div className="min-h-screen flex">
      {/* Sección Izquierda - Formulario */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 bg-white">
        <div className="w-full max-w-2xl space-y-8 py-12">
          {/* Header con botón de volver */}
          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={() => navigate('/')}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-6 h-6 text-gray-600" />
            </button>
            <div className="flex-1">
              <h2 className="text-3xl font-bold text-gray-900">
                Registrar Nuevo Usuario
              </h2>
              <p className="text-gray-600 mt-1">
                Solo administradores pueden crear nuevos usuarios
              </p>
            </div>
          </div>

          {/* Formulario */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Error Alert */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 animate-shake">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              </div>
            )}

            {/* Success Alert */}
            {success && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm text-green-800">{success}</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Nombre Completo */}
              <div className="md:col-span-2">
                <label htmlFor="nombre" className="block text-sm font-medium text-gray-700 mb-2">
                  Nombre Completo *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="nombre"
                    name="nombre"
                    type="text"
                    required
                    value={formData.nombre}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg 
                             focus:ring-2 focus:ring-primary focus:border-transparent
                             placeholder-gray-400 text-gray-900 transition-all"
                    placeholder="Ej: Juan Pérez García"
                  />
                </div>
              </div>

              {/* Email */}
              <div className="md:col-span-2">
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Corporativo *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg 
                             focus:ring-2 focus:ring-primary focus:border-transparent
                             placeholder-gray-400 text-gray-900 transition-all"
                    placeholder="usuario@empresa.com"
                  />
                </div>
              </div>

              {/* Contraseña */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Contraseña *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={formData.password}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg 
                             focus:ring-2 focus:ring-primary focus:border-transparent
                             placeholder-gray-400 text-gray-900 transition-all"
                    placeholder="Mínimo 6 caracteres"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 
                             hover:text-gray-600 transition-colors"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Confirmar Contraseña */}
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                  Confirmar Contraseña *
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-400" />
                  </div>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="block w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg 
                             focus:ring-2 focus:ring-primary focus:border-transparent
                             placeholder-gray-400 text-gray-900 transition-all"
                    placeholder="Repite la contraseña"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 
                             hover:text-gray-600 transition-colors"
                  >
                    {showConfirmPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Selección de Departamento/Rol */}
            <div className="space-y-4">
              <label className="block text-sm font-medium text-gray-700">
                Departamento / Rol *
              </label>

              {loadingDepartamentos ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {departamentos.map(dept => {
                    const Icon = departamentoIcons[dept.nombre] || Shield;
                    const colorClass = departamentoColors[dept.nombre] || 'from-gray-100 to-gray-200 text-gray-700 border-gray-300';
                    const isSelected = formData.departamento_id === dept.id.toString();

                    return (
                      <button
                        key={dept.id}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, departamento_id: dept.id.toString() }))}
                        className={`relative p-5 rounded-xl border-2 transition-all
                          ${isSelected
                            ? 'bg-linear-to-br from-orange-500 to-red-500 text-white border-primary shadow-lg scale-105'
                            : `bg-linear-to-br ${colorClass} hover:shadow-md hover:scale-102`
                          }`}
                      >
                        <div className="flex flex-col items-center gap-3">
                          <div className={`p-3 rounded-lg ${isSelected ? 'bg-white bg-opacity-20' : 'bg-white'}`}>
                            <Icon className={`w-8 h-8 ${isSelected ? 'text-white' : ''}`} />
                          </div>
                          <div className="text-center">
                            <div className="font-semibold text-lg">
                              {dept.nombre}
                            </div>
                            <div className={`text-xs mt-1 ${isSelected ? 'text-orange-100' : 'opacity-60'}`}>
                              {dept.nombre === 'General' && 'Acceso básico'}
                              {dept.nombre === 'Fiscal' && 'Gestión fiscal'}
                              {dept.nombre === 'Laboral' && 'Gestión laboral'}
                              {dept.nombre === 'Administrativo' && 'Gestión administrativa'}
                              {dept.nombre === 'Jefatura' && 'Acceso completo'}
                              {dept.nombre === 'Invitado' && 'Acceso externo restringido'}
                            </div>
                          </div>
                          {isSelected && (
                            <div className="absolute top-2 right-2">
                              <CheckCircle className="w-6 h-6 text-white" />
                            </div>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Resumen de Selección */}
            {departamentoSeleccionado && (
              <div className="bg-linear-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-green-900">
                      Departamento seleccionado: {departamentoSeleccionado.nombre}
                    </p>
                    <p className="text-xs text-green-700 mt-1">
                      El usuario será asignado a este departamento
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 
                       bg-linear-to-r from-orange-500 to-red-500 
                       hover:from-orange-600 hover:to-red-600
                       text-white font-semibold rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98]
                       shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Creando usuario...
                </>
              ) : (
                <>
                  <User className="w-5 h-5" />
                  Crear Usuario
                </>
              )}
            </button>

            <p className="text-xs text-center text-gray-500">
              * Todos los campos son obligatorios
            </p>
          </form>
        </div>
      </div>



      {/* Animación CSS */}
      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
          20%, 40%, 60%, 80% { transform: translateX(5px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out;
        }
        .scale-102 {
          transform: scale(1.02);
        }
      `}</style>
    </div>
  );
}
