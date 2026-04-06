// frontend/src/components/ModalProcesamientoUnificado.jsx
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  X, FolderInput, UserCheck, Bot, Mail, Zap,
  CheckCircle, Loader2, Sparkles, Calendar, Send,
  AlertCircle, ArrowRight, Building2, User, FileText,
  ShieldAlert, FileSearch, Banknote, Scale, Search, ChevronDown, Check
} from 'lucide-react';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';
import MobilePDFViewer from './MobilePDFViewer';
import { useGrupos } from '../hooks/useGruposDocumentos';

const TIPOS_INSPECCION = [
  { id: 'inspeccion',       label: 'Inspección',                  Icon: ShieldAlert, color: 'red',    prefix: 'Inspección'       },
  { id: 'requerimiento',    label: 'Requerimiento de Información', Icon: FileSearch,  color: 'blue',   prefix: 'Requerimiento'    },
  { id: 'embargo_salario',  label: 'Embargo de Salario',           Icon: Banknote,    color: 'orange', prefix: 'Embargo Salario'  },
  { id: 'embargo_creditos', label: 'Embargo Créditos y Derechos',  Icon: Scale,       color: 'purple', prefix: 'Embargo Créditos' },
];

export default function ModalProcesamientoUnificado({ documento, onClose, onSuccess }) {
  useEscapeKey(onClose);
  const [activeTab, setActiveTab] = useState('combinada');
  const [loading, setLoading] = useState(false);
  const [sugerencia, setSugerencia] = useState(null);
  const [loadingSugerencia, setLoadingSugerencia] = useState(false);
  const [error, setError] = useState(null);

  // Estados para documentos fiscales
  const [datosFiscales, setDatosFiscales] = useState({
    modelo_fiscal: '',
    ejercicio_fiscal: new Date().getFullYear(),
    periodo: ''
  });

  // Estados para expediente de inspección
  const [datosInspeccion, setDatosInspeccion] = useState({
    destino: 'existente',
    grupoId: '',
    tipoId: null,
    nombre: '',
  });
  const [busquedaGrupo, setBusquedaGrupo] = useState('');
  const [dropdownGrupoOpen, setDropdownGrupoOpen] = useState(false);
  const dropdownGrupoRef = useRef();

  const { data: grupos = [] } = useGrupos(documento?.empresa_id);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownGrupoRef.current && !dropdownGrupoRef.current.contains(e.target))
        setDropdownGrupoOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Estados del formulario
  const [formData, setFormData] = useState({
    mover_a_carpeta: '',
    asignar_tarea: {
      enabled: false,
      departamento: '',  // Nuevo: departamento seleccionado
      asignado_a_id: '',
      fecha_plazo: ''
    },
    procesar_ia: {
      enabled: false,
      tipo_plantilla: 'notificacion_generica'
    },
    preparar_email: {
      enabled: false,
      destinatarios: []
    }
  });

  // Datos auxiliares
  const [carpetas, setCarpetas] = useState([]);
  const [departamentos, setDepartamentos] = useState([]);
  const [plantillas, setPlantillas] = useState([]);
  const [usuariosFiltrados, setUsuariosFiltrados] = useState([]);

  // Emails de la empresa (para pre-cargar destinatarios)
  const [empresaEmails, setEmpresaEmails] = useState([]);
  const [nuevoEmailInput, setNuevoEmailInput] = useState('');
  const [agregarEmailLoading, setAgregarEmailLoading] = useState(false);

  useEffect(() => {
    cargarDatosIniciales();
    if (activeTab === 'combinada') {
      obtenerSugerencia();
    }
  }, [documento.id]);

  // Filtrar usuarios cuando cambia el departamento seleccionado
  useEffect(() => {
    if (formData.asignar_tarea.departamento) {
      const dept = departamentos.find(d => d.nombre === formData.asignar_tarea.departamento);
      if (dept && dept.usuarios) {
        setUsuariosFiltrados(dept.usuarios);
      } else {
        setUsuariosFiltrados([]);
      }
    } else {
      setUsuariosFiltrados([]);
    }
  }, [formData.asignar_tarea.departamento, departamentos]);

  const cargarDatosIniciales = async () => {
    try {
      setError(null);

      const [carpetasRes, deptosRes, plantillasRes, empresaRes] = await Promise.all([
        axios.get(`/api/empresas/${documento.empresa_id}/carpetas-destino`),
        axios.get('/api/departamentos'),
        axios.get('/api/plantillas'),
        axios.get(`/api/empresas/${documento.empresa_id}`)
      ]);

      console.log('📁 Respuesta carpetas-destino:', carpetasRes.data);
      if (carpetasRes.data.success) {
        console.log('✅ Carpetas recibidas:', carpetasRes.data.carpetas);
        setCarpetas(carpetasRes.data.carpetas || []);
      } else {
        console.error('❌ Error en carpetas-destino:', carpetasRes.data);
      }

      if (deptosRes.data.success) {
        console.log('Departamentos cargados:', deptosRes.data.departamentos);
        setDepartamentos(deptosRes.data.departamentos || []);
      }
      if (plantillasRes.data.success) setPlantillas(plantillasRes.data.plantillas || []);

      // Cargar emails de la empresa y pre-seleccionarlos como destinatarios
      if (empresaRes.data.empresa) {
        const emp = empresaRes.data.empresa;
        const emails = [emp.email, ...(emp.emails_extra || [])].filter(Boolean);
        setEmpresaEmails(emails);
        if (emails.length > 0) {
          setFormData(prev => ({
            ...prev,
            preparar_email: { ...prev.preparar_email, destinatarios: emails }
          }));
        }
      }

    } catch (err) {
      console.error('Error cargando datos iniciales:', err);
      console.error('Detalles del error:', err.response?.data);
      setError('Error cargando datos: ' + (err.response?.data?.error || err.message));
    }
  };

  const obtenerSugerencia = async () => {
    try {
      setLoadingSugerencia(true);
      const res = await axios.post('/api/mesa-trabajo/sugerir-clasificacion', {
        documento_id: documento.id
      });

      if (res.data.success) {
        setSugerencia(res.data);
        if (res.data.confianza > 0.7) {
          setFormData(prev => ({
            ...prev,
            mover_a_carpeta: res.data.sugerencia,
            asignar_tarea: {
              ...prev.asignar_tarea,
              enabled: res.data.departamento_sugerido ? true : prev.asignar_tarea.enabled,
              departamento: res.data.departamento_sugerido || prev.asignar_tarea.departamento
            },
            // ⭐ NUEVO: Pre-seleccionar Perfil de IA si se detectó
            procesar_ia: res.data.plantilla_codigo ? {
              enabled: true,
              tipo_plantilla: res.data.plantilla_codigo
            } : prev.procesar_ia
          }));
        }

        // Si es Impuestos y hay modelo sugerido, pre-llenarlo
        if (res.data.sugerencia === 'Impuestos' && res.data.modelo_fiscal_sugerido) {
          setDatosFiscales(prev => ({
            ...prev,
            modelo_fiscal: res.data.modelo_fiscal_sugerido
          }));
        }
      }
    } catch (err) {
      console.error('Error obteniendo sugerencia:', err);
    } finally {
      setLoadingSugerencia(false);
    }
  };

  // Activar/desactivar un email como destinatario
  const toggleEmailDestinatario = (email) => {
    setFormData(prev => ({
      ...prev,
      preparar_email: {
        ...prev.preparar_email,
        destinatarios: prev.preparar_email.destinatarios.includes(email)
          ? prev.preparar_email.destinatarios.filter(e => e !== email)
          : [...prev.preparar_email.destinatarios, email]
      }
    }));
  };

  // Guardar un nuevo email en la empresa Y añadirlo a los destinatarios seleccionados
  const agregarEmailEmpresa = async () => {
    const email = nuevoEmailInput.trim();
    if (!email || !email.includes('@')) return;
    setAgregarEmailLoading(true);
    try {
      const res = await axios.post(`/api/empresas/${documento.empresa_id}/agregar-email`, { email });
      if (res.data.success) {
        setEmpresaEmails(prev => [...prev, email]);
        setFormData(prev => ({
          ...prev,
          preparar_email: {
            ...prev.preparar_email,
            destinatarios: [...prev.preparar_email.destinatarios, email]
          }
        }));
        setNuevoEmailInput('');
        toast.success('Email guardado en la empresa');
      }
    } catch {
      toast.error('Error al guardar email');
    } finally {
      setAgregarEmailLoading(false);
    }
  };

  const ejecutarAccionCombinada = async () => {
    try {
      setLoading(true);
      setError(null);

      const payload = {
        documento_id: documento.id
      };

      if (formData.mover_a_carpeta) {
        payload.mover_a_carpeta = formData.mover_a_carpeta;
      }

      if (formData.asignar_tarea.enabled) {
        // Generar estado automáticamente
        let estado = '';
        if (formData.asignar_tarea.departamento) {
          estado = `Pendiente (${formData.asignar_tarea.departamento})`;
        }

        payload.asignar_tarea = {
          estado: estado,
          asignado_a_id: formData.asignar_tarea.asignado_a_id || null,
          fecha_plazo: formData.asignar_tarea.fecha_plazo || null
        };
      }

      if (formData.procesar_ia.enabled) {
        payload.procesar_ia = true;
        payload.tipo_plantilla = formData.procesar_ia.tipo_plantilla;
      }

      if (formData.preparar_email.enabled) {
        payload.preparar_email = true;
        payload.destinatarios = formData.preparar_email.destinatarios;
        // ⭐ AUTOMÁTICO: Si se prepara email, necesitamos la extracción OCR de datos
        payload.procesar_ia = true;
        if (!payload.tipo_plantilla) {
          payload.tipo_plantilla = formData.procesar_ia.tipo_plantilla || 'notificacion_generica';
        }
      }

      // --- PERSISTENCIA DE PESTAÑAS ---
      // Si el usuario está en una pestaña específica, forzar esa acción aunque no esté marcada en "Combinada"
      if (activeTab === 'asignar') {
        let estado = `Pendiente (${formData.asignar_tarea.departamento || 'General'})`;
        payload.asignar_tarea = {
          estado: estado,
          asignado_a_id: formData.asignar_tarea.asignado_a_id || null,
          fecha_plazo: formData.asignar_tarea.fecha_plazo || null
        };
      } else if (activeTab === 'ia') {
        payload.procesar_ia = true;
        payload.tipo_plantilla = formData.procesar_ia.tipo_plantilla;
      } else if (activeTab === 'email') {
        payload.preparar_email = true;
        payload.destinatarios = formData.preparar_email.destinatarios;
        payload.procesar_ia = true; // Requisito para email
      } else if (activeTab === 'clasificar') {
        // En la pestaña clasificar ya se usa el payload base mover_a_carpeta
      }

      // Si es Impuestos, usar endpoint especial
      if (formData.mover_a_carpeta === 'Impuestos') {
        if (!datosFiscales.modelo_fiscal || !datosFiscales.ejercicio_fiscal) {
          setError('Debes seleccionar el modelo fiscal y el ejercicio');
          setLoading(false);
          return;
        }

        try {
          const resFiscal = await axios.post('/api/mesa-trabajo/mover-a-fiscal', {
            documento_id: documento.id,
            modelo_fiscal: datosFiscales.modelo_fiscal,
            ejercicio_fiscal: datosFiscales.ejercicio_fiscal,
            periodo: datosFiscales.periodo || null
          });

          if (resFiscal.data.success) {
            toast.success('✅ Documento movido a Gestión Fiscal');
            onSuccess();
            return;
          }
        } catch (err) {
          const errorMsg = err.response?.data?.error || err.message;
          setError(errorMsg);
          toast.error('Error: ' + errorMsg);
          setLoading(false);
          return;
        }
      }
      const res = await axios.post('/api/mesa-trabajo/accion-combinada', payload);

      if (res.data.success) {
        // Si se movió a Inspecciones, asociar al grupo seleccionado/nuevo
        if (formData.mover_a_carpeta === 'Inspecciones') {
          try {
            let grupoTargetId = datosInspeccion.grupoId;
            if (datosInspeccion.destino === 'nuevo' && datosInspeccion.tipoId) {
              const tipoInfo = TIPOS_INSPECCION.find(t => t.id === datosInspeccion.tipoId);
              const grupoRes = await axios.post('/api/grupos-documentos', {
                nombre: datosInspeccion.nombre.trim() || `${tipoInfo.prefix} - ${new Date().getFullYear()}`,
                empresa_id: documento.empresa_id,
                color: tipoInfo.color,
                descripcion: tipoInfo.label,
              }, { withCredentials: true });
              if (grupoRes.data.success) grupoTargetId = grupoRes.data.grupo.id;
            }
            if (grupoTargetId) {
              await axios.post(`/api/grupos-documentos/${grupoTargetId}/documentos`,
                { documento_id: documento.id }, { withCredentials: true }
              );
            }
          } catch (e) {
            console.warn('No se pudo asociar al grupo de inspección:', e);
          }
        }

        toast.success(
          <div>
            <div className="font-bold mb-2">✅ {res.data.message}</div>
            <div className="text-sm space-y-1">
              {res.data.acciones.map((a, i) => (
                <div key={i}>• {a.tipo}</div>
              ))}
            </div>
          </div>,
          { duration: 4000 }
        );
        onSuccess();
      }
    } catch (err) {
      const errorMsg = err.response?.data?.error || err.message;
      setError(errorMsg);
      toast.error('Error: ' + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { id: 'combinada', label: 'Acción Combinada', icon: Zap },
    { id: 'clasificar', label: 'Clasificar', icon: FolderInput },
    { id: 'asignar', label: 'Asignar', icon: UserCheck },
    { id: 'ia', label: 'Procesar OCR', icon: Bot },
    { id: 'email', label: 'Email', icon: Mail }
  ];

  // Componente de Asignación con Dos Campos
  const AsignacionDosColumnas = ({ size = 'md' }) => {
    const textSize = size === 'sm' ? 'text-sm' : 'text-base';
    const padding = size === 'sm' ? 'px-3 py-2' : 'px-4 py-2';

    return (
      <div className="space-y-3">
        {/* Campo 1: Departamento */}
        <div>
          <label className="text-xs font-medium text-gray-700 mb-1 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-gray-500" />
            Departamento
          </label>
          <select
            value={formData.asignar_tarea.departamento}
            onChange={(e) => {
              setFormData(prev => ({
                ...prev,
                asignar_tarea: {
                  ...prev.asignar_tarea,
                  departamento: e.target.value,
                  asignado_a_id: '' // Reset usuario al cambiar departamento
                }
              }));
            }}
            className={`w-full ${padding} ${textSize} border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent`}
          >
            <option value="">Sin asignar (Por Procesar)</option>
            {departamentos && departamentos.map(dept => (
              <option key={dept.id} value={dept.nombre}>
                📁 {dept.nombre}
              </option>
            ))}
          </select>
          {formData.asignar_tarea.departamento && (
            <p className="text-xs text-gray-500 mt-1">
              Estado: Pendiente ({formData.asignar_tarea.departamento})
            </p>
          )}
        </div>

        {/* Campo 2: Usuario (solo si hay departamento seleccionado) */}
        {formData.asignar_tarea.departamento && (
          <div>
            <label className="text-xs font-medium text-gray-700 mb-1 flex items-center gap-2">
              <User className="w-4 h-4 text-gray-500" />
              Asignar a (opcional)
            </label>
            <select
              value={formData.asignar_tarea.asignado_a_id}
              onChange={(e) => {
                setFormData(prev => ({
                  ...prev,
                  asignar_tarea: {
                    ...prev.asignar_tarea,
                    asignado_a_id: e.target.value
                  }
                }));
              }}
              className={`w-full ${padding} ${textSize} border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent`}
            >
              <option value="">Todo el departamento</option>
              {usuariosFiltrados.map(user => (
                <option key={user.id} value={user.id}>
                  👤 {user.nombre}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {usuariosFiltrados.length} usuario{usuariosFiltrados.length !== 1 ? 's' : ''} en {formData.asignar_tarea.departamento}
            </p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-7xl max-h-[95vh] overflow-hidden flex flex-col">

        {/* Header */}
        <div className="bg-linear-to-r from-orange-500 to-red-500 px-6 py-4 text-white">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-bold truncate">
                {documento.nombre_archivo}
              </h2>
              <p className="text-orange-100 text-sm mt-1">
                {documento.empresa?.nombre || 'Sin empresa'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-800">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* SPLIT LAYOUT */}
        <div className="flex-1 flex overflow-hidden">

          {/* PDF VIEWER */}
          <div className="w-1/2 bg-gray-100 border-r border-gray-300 flex flex-col">
            <div className="flex-1 overflow-hidden">
              <MobilePDFViewer documentId={documento.id} />
            </div>
          </div>

          {/* TABS + CONTENT */}
          <div className="w-1/2 flex flex-col">

            {/* Tabs */}
            <div className="bg-gray-50 border-b border-gray-200 px-4">
              <div className="flex gap-1 overflow-x-auto">
                {tabs.map(tab => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`flex items-center gap-2 px-3 py-3 font-medium whitespace-nowrap transition-all ${activeTab === tab.id
                        ? 'text-primary border-b-2 border-primary'
                        : 'text-gray-600 hover:text-gray-900'
                        }`}
                    >
                      <Icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto p-6">

              {/* TAB: ACCIÓN COMBINADA */}
              {activeTab === 'combinada' && (
                <div className="space-y-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-3">
                    <Sparkles className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="font-semibold text-blue-900 text-sm mb-1">
                        Workflow Inteligente
                      </h3>
                      <p className="text-xs text-blue-700">
                        Combina múltiples acciones en un solo paso. Activa las que necesites.
                      </p>
                    </div>
                  </div>

                  {/* Sugerencia de IA */}
                  {sugerencia && (
                    <div className={`border rounded-lg p-3 ${sugerencia.confianza > 0.7
                      ? 'bg-green-50 border-green-200'
                      : 'bg-yellow-50 border-yellow-200'
                      }`}>
                      <div className="flex items-center gap-2 mb-2">
                        <Bot className={`w-4 h-4 ${sugerencia.confianza > 0.7 ? 'text-green-600' : 'text-yellow-600'
                          }`} />
                        <span className="font-semibold text-sm">
                          Sugerencia de IA
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${sugerencia.confianza > 0.7
                          ? 'bg-green-200 text-green-800'
                          : 'bg-yellow-200 text-yellow-800'
                          }`}>
                          {Math.round(sugerencia.confianza * 100)}% confianza
                        </span>
                      </div>
                      <p className="text-xs text-gray-700">
                        <strong>Carpeta sugerida:</strong> {sugerencia.sugerencia}
                      </p>
                      {sugerencia.plantilla_codigo && (
                        <p className="text-xs text-blue-700 mt-1 font-medium">
                          ✨ Perfil detectado: {plantillas.find(p => p.codigo === sugerencia.plantilla_codigo)?.nombre.replace('Perfil: ', '') || sugerencia.plantilla_codigo}
                        </p>
                      )}
                    </div>
                  )}

                  {/* 1. Clasificar */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <FolderInput className="w-4 h-4 text-primary" />
                      <h4 className="font-semibold text-sm text-gray-900">1. Clasificar</h4>
                      {formData.mover_a_carpeta && (
                        <CheckCircle className="w-4 h-4 text-green-600 ml-auto" />
                      )}
                    </div>
                    <select
                      value={formData.mover_a_carpeta}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        mover_a_carpeta: e.target.value
                      }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    >
                      <option value="">Mantener en Por Procesar</option>
                      {carpetas.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  {/* Expediente de Inspección (solo si es Inspecciones) */}
                  {formData.mover_a_carpeta === 'Inspecciones' && (
                    <SeccionGrupoInspeccion
                      grupos={grupos}
                      datosInspeccion={datosInspeccion}
                      setDatosInspeccion={setDatosInspeccion}
                      busquedaGrupo={busquedaGrupo}
                      setBusquedaGrupo={setBusquedaGrupo}
                      dropdownGrupoOpen={dropdownGrupoOpen}
                      setDropdownGrupoOpen={setDropdownGrupoOpen}
                      dropdownGrupoRef={dropdownGrupoRef}
                    />
                  )}

                  {/* Campos Fiscales (solo si es Impuestos) */}
                  {formData.mover_a_carpeta === 'Impuestos' && (
                    <div className="border border-blue-200 bg-blue-50 rounded-lg p-4 space-y-3">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="w-4 h-4 text-blue-600" />
                        <h4 className="font-semibold text-sm text-blue-900">
                          Datos del Documento Fiscal
                        </h4>
                      </div>

                      {/* Modelo Fiscal */}
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Modelo Fiscal *
                        </label>
                        <select
                          value={datosFiscales.modelo_fiscal}
                          onChange={(e) => setDatosFiscales(prev => ({
                            ...prev,
                            modelo_fiscal: e.target.value
                          }))}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="">Seleccionar modelo...</option>
                          <option value="MODELO_303">Modelo 303 - IVA</option>
                          <option value="MODELO_130">Modelo 130 - IRPF</option>
                          <option value="MODELO_131">Modelo 131 - IRPF Módulos</option>
                          <option value="MODELO_111">Modelo 111 - Retenciones</option>
                          <option value="MODELO_115">Modelo 115 - Alquileres</option>
                          <option value="MODELO_200">Modelo 200 - Sociedades</option>
                          <option value="MODELO_202">Modelo 202 - P.F. Sociedades</option>
                          <option value="MODELO_216">Modelo 216 - IRNR (No Residentes)</option>
                          <option value="MODELO_296">Modelo 296 - Resumen Anual IRNR</option>
                          <option value="MODELO_180">Modelo 180 - Anual Alquileres</option>
                          <option value="MODELO_190">Modelo 190 - Anual Retenciones</option>
                          <option value="MODELO_390">Modelo 390 - Resumen Anual IVA</option>
                          <option value="MODELO_347">Modelo 347 - Operaciones con Terceros</option>
                        </select>
                        {sugerencia?.modelo_fiscal_sugerido && (
                          <p className="text-xs text-blue-600 mt-1">
                            💡 IA sugiere: {sugerencia.modelo_fiscal_sugerido.replace('MODELO_', 'Modelo ')}
                          </p>
                        )}
                      </div>

                      {/* Ejercicio Fiscal */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Ejercicio *
                          </label>
                          <input
                            type="number"
                            value={datosFiscales.ejercicio_fiscal}
                            onChange={(e) => setDatosFiscales(prev => ({
                              ...prev,
                              ejercicio_fiscal: parseInt(e.target.value)
                            }))}
                            min="2020"
                            max="2030"
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Periodo (opcional)
                          </label>
                          <input
                            type="text"
                            value={datosFiscales.periodo}
                            onChange={(e) => setDatosFiscales(prev => ({
                              ...prev,
                              periodo: e.target.value
                            }))}
                            placeholder="T1, T2, 1P..."
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2. Asignar Tarea */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        checked={formData.asignar_tarea.enabled}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          asignar_tarea: {
                            ...prev.asignar_tarea,
                            enabled: e.target.checked
                          }
                        }))}
                        className="w-4 h-4 text-primary rounded"
                      />
                      <UserCheck className="w-4 h-4 text-blue-600" />
                      <h4 className="font-semibold text-sm text-gray-900">2. Asignar Tarea</h4>
                    </div>

                    {formData.asignar_tarea.enabled && (
                      <div className="ml-6">
                        <AsignacionDosColumnas size="sm" />
                        <div className="mt-3">
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Fecha límite
                          </label>
                          <input
                            type="date"
                            value={formData.asignar_tarea.fecha_plazo}
                            onChange={(e) => setFormData(prev => ({
                              ...prev,
                              asignar_tarea: {
                                ...prev.asignar_tarea,
                                fecha_plazo: e.target.value
                              }
                            }))}
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 3. Procesar con IA */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        checked={formData.procesar_ia.enabled}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          procesar_ia: {
                            ...prev.procesar_ia,
                            enabled: e.target.checked
                          }
                        }))}
                        className="w-4 h-4 text-primary rounded"
                      />
                      <Bot className="w-4 h-4 text-purple-600" />
                      <h4 className="font-semibold text-sm text-gray-900">3. Procesar con IA</h4>
                    </div>

                    {formData.procesar_ia.enabled && (
                      <div className="ml-6">
                        <select
                          value={formData.procesar_ia.tipo_plantilla}
                          onChange={(e) => setFormData(prev => ({
                            ...prev,
                            procesar_ia: {
                              ...prev.procesar_ia,
                              tipo_plantilla: e.target.value
                            }
                          }))}
                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                        >
                          {plantillas.map(p => (
                            <option key={p.codigo} value={p.codigo}>
                              {p.nombre}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  {/* 4. Preparar Email */}
                  <div className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="checkbox"
                        checked={formData.preparar_email.enabled}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          preparar_email: {
                            ...prev.preparar_email,
                            enabled: e.target.checked
                          }
                        }))}
                        className="w-4 h-4 text-primary rounded"
                      />
                      <Mail className="w-4 h-4 text-red-600" />
                      <h4 className="font-semibold text-sm text-gray-900">4. Preparar Email</h4>
                    </div>
                    {formData.preparar_email.enabled && (
                      <div className="ml-6 mt-2 space-y-2">
                        {/* Lista de emails de la empresa con checkboxes */}
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Destinatarios:
                        </label>
                        <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-36 overflow-y-auto">
                          {empresaEmails.length === 0 ? (
                            <p className="text-xs text-gray-400 italic px-3 py-2">
                              Sin emails configurados para esta empresa
                            </p>
                          ) : (
                            empresaEmails.map((email, i) => (
                              <label key={i} className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-50 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={formData.preparar_email.destinatarios.includes(email)}
                                  onChange={() => toggleEmailDestinatario(email)}
                                  className="w-3.5 h-3.5 text-red-500 rounded"
                                />
                                <span className="text-xs text-blue-600">{email}</span>
                              </label>
                            ))
                          )}
                        </div>
                        {/* Añadir nuevo email */}
                        <div className="flex gap-2">
                          <input
                            type="email"
                            placeholder="Añadir email..."
                            value={nuevoEmailInput}
                            onChange={(e) => setNuevoEmailInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && agregarEmailEmpresa()}
                            className="flex-1 px-2 py-1.5 text-xs border border-gray-300 rounded-lg focus:ring-1 focus:ring-red-400"
                          />
                          <button
                            type="button"
                            onClick={agregarEmailEmpresa}
                            disabled={agregarEmailLoading || !nuevoEmailInput.includes('@')}
                            className="px-2.5 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 disabled:opacity-50 whitespace-nowrap"
                          >
                            {agregarEmailLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : '+ Guardar'}
                          </button>
                        </div>
                        <div className="bg-red-50 p-2 rounded border border-red-100">
                          <p className="text-[11px] text-red-700 leading-tight">
                            📧 El documento aparecerá como <strong>Pendiente de Envío</strong> tras procesarse.
                            Podrás revisar y enviar el correo desde la sección de Documentos.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB: ASIGNAR */}
              {activeTab === 'asignar' && (
                <div className="space-y-3">
                  <h3 className="text-base font-semibold text-gray-900">
                    Asignar Tarea
                  </h3>
                  <AsignacionDosColumnas />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Fecha límite
                    </label>
                    <input
                      type="date"
                      value={formData.asignar_tarea.fecha_plazo}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        asignar_tarea: {
                          ...prev.asignar_tarea,
                          fecha_plazo: e.target.value
                        }
                      }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                  </div>
                </div>
              )}

              {/* Otros tabs */}
              {activeTab === 'clasificar' && (
                <div className="space-y-3">
                  <h3 className="text-base font-semibold text-gray-900">Clasificar Documento</h3>
                  <select
                    value={formData.mover_a_carpeta}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      mover_a_carpeta: e.target.value
                    }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  >
                    <option value="">Seleccionar carpeta...</option>
                    {carpetas.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {formData.mover_a_carpeta === 'Inspecciones' && (
                    <SeccionGrupoInspeccion
                      grupos={grupos}
                      datosInspeccion={datosInspeccion}
                      setDatosInspeccion={setDatosInspeccion}
                      busquedaGrupo={busquedaGrupo}
                      setBusquedaGrupo={setBusquedaGrupo}
                      dropdownGrupoOpen={dropdownGrupoOpen}
                      setDropdownGrupoOpen={setDropdownGrupoOpen}
                      dropdownGrupoRef={dropdownGrupoRef}
                    />
                  )}
                </div>
              )}

              {activeTab === 'ia' && (
                <div className="space-y-3">
                  <h3 className="text-base font-semibold text-gray-900">Procesar con IA</h3>
                  <select
                    value={formData.procesar_ia.tipo_plantilla}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      procesar_ia: {
                        ...prev.procesar_ia,
                        tipo_plantilla: e.target.value
                      }
                    }))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  >
                    {plantillas.map(p => (
                      <option key={p.codigo} value={p.codigo}>{p.nombre}</option>
                    ))}
                  </select>
                </div>
              )}

              {activeTab === 'email' && (
                <div className="space-y-3">
                  <h3 className="text-base font-semibold text-gray-900">Preparar Email</h3>

                  {/* Destinatarios con checkboxes */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-sm font-medium text-gray-700">Destinatarios:</label>
                      <span className="text-xs text-gray-400">
                        {formData.preparar_email.destinatarios.length} seleccionado(s)
                      </span>
                    </div>
                    <div className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-40 overflow-y-auto mb-2">
                      {empresaEmails.length === 0 ? (
                        <p className="text-xs text-gray-400 italic px-3 py-2">
                          Sin emails configurados para esta empresa
                        </p>
                      ) : (
                        empresaEmails.map((email, i) => (
                          <label key={i} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={formData.preparar_email.destinatarios.includes(email)}
                              onChange={() => {
                                toggleEmailDestinatario(email);
                                setFormData(prev => ({ ...prev, preparar_email: { ...prev.preparar_email, enabled: true } }));
                              }}
                              className="w-4 h-4 text-red-500 rounded"
                            />
                            <span className="text-sm text-blue-600">{email}</span>
                          </label>
                        ))
                      )}
                    </div>
                    {/* Añadir nuevo email a la empresa */}
                    <div className="flex gap-2">
                      <input
                        type="email"
                        placeholder="Añadir nuevo email..."
                        value={nuevoEmailInput}
                        onChange={(e) => setNuevoEmailInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && agregarEmailEmpresa()}
                        className="flex-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500"
                      />
                      <button
                        type="button"
                        onClick={agregarEmailEmpresa}
                        disabled={agregarEmailLoading || !nuevoEmailInput.includes('@')}
                        className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg text-gray-700 disabled:opacity-50 whitespace-nowrap"
                      >
                        {agregarEmailLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin inline" /> : '+ Guardar'}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Perfil de procesamiento IA
                    </label>
                    <select
                      value={formData.procesar_ia.tipo_plantilla}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        procesar_ia: { ...prev.procesar_ia, tipo_plantilla: e.target.value }
                      }))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    >
                      {plantillas.map(p => (
                        <option key={p.codigo} value={p.codigo}>{p.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div className="bg-red-50 p-3 rounded border border-red-100">
                    <p className="text-xs text-red-700 leading-tight">
                      📧 El documento aparecerá como <strong>Pendiente de Envío</strong> tras procesarse.
                      Podrás revisar y enviar el correo desde la sección de Documentos.
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="bg-gray-50 border-t border-gray-200 px-6 py-3 flex items-center justify-between">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg"
              >
                Cancelar
              </button>

              <button
                onClick={ejecutarAccionCombinada}
                disabled={
                  loading || (
                    activeTab === 'combinada' &&
                    !formData.mover_a_carpeta &&
                    !formData.asignar_tarea.enabled &&
                    !formData.procesar_ia.enabled &&
                    !formData.preparar_email.enabled
                  )
                }
                className="flex items-center gap-2 px-5 py-2 bg-linear-to-r from-orange-500 to-red-500 text-white text-sm rounded-lg hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Ejecutando Workflow...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 fill-current" />
                    EJECUTAR ACCIÓN
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sección de grupo de inspección (reutilizable en ambas pestañas) ──────────
function SeccionGrupoInspeccion({
  grupos, datosInspeccion, setDatosInspeccion,
  busquedaGrupo, setBusquedaGrupo,
  dropdownGrupoOpen, setDropdownGrupoOpen, dropdownGrupoRef
}) {
  const año = new Date().getFullYear();

  const handleTipoSelect = (t) => {
    const esAutogenerado = TIPOS_INSPECCION.some(tp =>
      datosInspeccion.nombre === `${tp.prefix} - ${año}`
    );
    setDatosInspeccion(prev => ({
      ...prev,
      tipoId: t.id,
      nombre: (!prev.nombre || esAutogenerado) ? `${t.prefix} - ${año}` : prev.nombre,
    }));
  };

  const grupoSeleccionado = grupos.find(g => g.id == datosInspeccion.grupoId);
  const gruposFiltrados = grupos.filter(g =>
    g.nombre.toLowerCase().includes(busquedaGrupo.toLowerCase())
  );

  return (
    <div className="border border-orange-200 bg-orange-50 rounded-lg p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 text-orange-600" />
        <h4 className="font-semibold text-sm text-orange-900">Asignar a expediente</h4>
        <span className="text-xs text-orange-500 font-normal">(opcional)</span>
      </div>

      {/* Toggle existente / nuevo */}
      <div className="flex gap-1.5 p-1 bg-orange-100 rounded-lg">
        <button
          onClick={() => setDatosInspeccion(prev => ({ ...prev, destino: 'existente' }))}
          className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-all ${
            datosInspeccion.destino === 'existente'
              ? 'bg-white shadow-sm text-gray-900'
              : 'text-orange-600 hover:text-orange-800'
          }`}
        >
          Expediente existente
        </button>
        <button
          onClick={() => setDatosInspeccion(prev => ({ ...prev, destino: 'nuevo' }))}
          className={`flex-1 py-1.5 rounded-md text-xs font-semibold transition-all ${
            datosInspeccion.destino === 'nuevo'
              ? 'bg-white shadow-sm text-gray-900'
              : 'text-orange-600 hover:text-orange-800'
          }`}
        >
          Nuevo expediente
        </button>
      </div>

      {/* Buscador de grupo existente */}
      {datosInspeccion.destino === 'existente' && (
        <div className="relative" ref={dropdownGrupoRef}>
          <div
            className={`flex items-center gap-2 px-3 py-2 border rounded-lg bg-white cursor-text transition-all ${
              dropdownGrupoOpen ? 'border-orange-400 ring-2 ring-orange-200' : 'border-gray-200 hover:border-gray-300'
            }`}
            onClick={() => setDropdownGrupoOpen(true)}
          >
            <Search className="w-3.5 h-3.5 text-gray-400 shrink-0" />
            <input
              type="text"
              value={dropdownGrupoOpen ? busquedaGrupo : (grupoSeleccionado?.nombre || '')}
              onChange={e => { setBusquedaGrupo(e.target.value); setDatosInspeccion(prev => ({ ...prev, grupoId: '' })); }}
              onFocus={() => { setDropdownGrupoOpen(true); setBusquedaGrupo(''); }}
              placeholder={grupos.length === 0 ? 'No hay expedientes aún' : 'Buscar expediente...'}
              disabled={grupos.length === 0}
              className="flex-1 outline-none text-xs text-gray-700 bg-transparent placeholder-gray-400 disabled:cursor-not-allowed"
            />
            {datosInspeccion.grupoId && !dropdownGrupoOpen && (
              <button onClick={(e) => { e.stopPropagation(); setDatosInspeccion(prev => ({ ...prev, grupoId: '' })); setBusquedaGrupo(''); }} className="text-gray-300 hover:text-gray-500">
                <X className="w-3 h-3" />
              </button>
            )}
            <ChevronDown className={`w-3.5 h-3.5 text-gray-400 shrink-0 transition-transform ${dropdownGrupoOpen ? 'rotate-180' : ''}`} />
          </div>

          {dropdownGrupoOpen && grupos.length > 0 && (
            <div className="absolute z-30 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
              {gruposFiltrados.length === 0 ? (
                <div className="px-3 py-4 text-center text-xs text-gray-400">
                  Sin resultados para "<span className="font-medium">{busquedaGrupo}</span>"
                </div>
              ) : (
                <ul className="max-h-40 overflow-y-auto py-1">
                  {gruposFiltrados.map(g => (
                    <li key={g.id}>
                      <button
                        onClick={() => { setDatosInspeccion(prev => ({ ...prev, grupoId: g.id })); setBusquedaGrupo(''); setDropdownGrupoOpen(false); }}
                        className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors ${
                          datosInspeccion.grupoId == g.id ? 'bg-orange-50 text-orange-700 font-semibold' : 'text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <span className="flex-1 truncate">{g.nombre}</span>
                        {datosInspeccion.grupoId == g.id && <Check className="w-3 h-3 text-orange-500 shrink-0" strokeWidth={3} />}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      {/* Nuevo expediente: tipo + nombre */}
      {datosInspeccion.destino === 'nuevo' && (
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-1.5">
            {TIPOS_INSPECCION.map(t => (
              <button
                key={t.id}
                onClick={() => handleTipoSelect(t)}
                className={`flex items-center gap-1.5 p-2 rounded-lg border-2 text-left transition-all ${
                  datosInspeccion.tipoId === t.id
                    ? 'border-orange-400 bg-orange-50'
                    : 'border-gray-100 hover:border-gray-200 bg-white'
                }`}
              >
                <t.Icon className={`w-3.5 h-3.5 shrink-0 ${datosInspeccion.tipoId === t.id ? 'text-orange-600' : 'text-gray-400'}`} />
                <span className={`text-[11px] font-semibold leading-tight ${datosInspeccion.tipoId === t.id ? 'text-orange-800' : 'text-gray-600'}`}>
                  {t.label}
                </span>
                {datosInspeccion.tipoId === t.id && <Check className="w-3 h-3 text-orange-500 ml-auto shrink-0" strokeWidth={3} />}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={datosInspeccion.nombre}
            onChange={e => setDatosInspeccion(prev => ({ ...prev, nombre: e.target.value }))}
            placeholder="Nombre del expediente"
            className="w-full px-3 py-2 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-orange-300 focus:border-transparent outline-none bg-white"
          />
        </div>
      )}
    </div>
  );
}