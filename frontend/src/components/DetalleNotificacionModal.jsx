// frontend/src/components/DetalleNotificacionModal.jsx
import React, { useState, useEffect } from 'react';
import { X, Mail, Loader2, RotateCcw, Archive, Save, Plus, Check, Users, User, RefreshCw } from 'lucide-react';
import axios from 'axios';
import ConfirmarEmailModal from './ConfirmarEmailModal';
import DatePicker from 'react-datepicker';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';
import MobilePDFViewer from './MobilePDFViewer';


export default function DetalleNotificacionModal({ documento, onClose, onStatusChange, isPreview = false }) {
  useEscapeKey(onClose);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [emailPreview, setEmailPreview] = useState({ subject: '', body: '' });
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [error, setError] = useState(null);
  const [empresa, setEmpresa] = useState(null);
  const [docInterno, setDocInterno] = useState(documento); // Estado local para permitir actualizaciones
  const [isPolling, setIsPolling] = useState(!documento.procesado);

  // Estados de Tarea
  const [estadoTarea, setEstadoTarea] = useState(docInterno.estado_tarea || 'Pendiente (General)');
  const [fechaPlazo, setFechaPlazo] = useState(docInterno.fecha_plazo ? new Date(docInterno.fecha_plazo) : null);

  // --- ASIGNACIÓN ESPECÍFICA ---
  const [usuariosDepto, setUsuariosDepto] = useState([]); // Lista de usuarios del depto seleccionado
  const [usuarioAsignado, setUsuarioAsignado] = useState(documento.asignado_a_id || ''); // ID seleccionado
  const [loadingUsers, setLoadingUsers] = useState(false);

  const [isAsignando, setIsAsignando] = useState(false);
  const [isMarkingPending, setIsMarkingPending] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Emails
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [showAddEmail, setShowAddEmail] = useState(false);
  const [newEmailInput, setNewEmailInput] = useState('');
  const [isAddingEmail, setIsAddingEmail] = useState(false);
  const [pollingCounter, setPollingCounter] = useState(0);

  const datosIA = docInterno.datos_extraidos || {};
  let pdfUrl = `/api/documentos/${documento.id}/archivo`;
  if (isPreview && documento.id === -1) pdfUrl = `/api/archivos-no-clasificados/${documento.nombre_archivo}`;

  // Cargar empresa
  useEffect(() => {
    if (!isPreview && docInterno.empresa_id) {
      // Pre-cargar destinatarios guardados desde Mesa de Trabajo (si existen)
      const destinatariosGuardados = docInterno.datos_extraidos?.email_preparado?.destinatarios;
      if (destinatariosGuardados?.length > 0) {
        setSelectedEmails(destinatariosGuardados);
      }

      axios.get(`/api/empresas/${docInterno.empresa_id}`, { withCredentials: true })
        .then(res => {
          if (res.data.success) {
            setEmpresa(res.data.empresa);
            // Solo usar email de la empresa si no había destinatarios pre-guardados
            if (res.data.empresa.email && selectedEmails.length === 0 && !destinatariosGuardados?.length) {
              setSelectedEmails([res.data.empresa.email]);
            }
          }
        }).catch(err => {
          console.error("Error cargando empresa:", err);
          setError("Error cargando empresa");
        });
    }
  }, [docInterno.empresa_id, isPreview]);

  // POLLING: Si el documento no está procesado, refrescarlo cada 3 segundos
  useEffect(() => {
    // Si ya está procesado o es una previsualización, no poll
    if (!isPolling || isPreview || docInterno.procesado) {
      if (isPolling) setIsPolling(false);
      return;
    }

    const intervalId = setInterval(async () => {
      try {
        const response = await axios.get(`/api/documentos/${docInterno.id}`, { withCredentials: true });
        if (response.data.success) {
          const updatedDoc = response.data.documento;

          // Si el estado en DB cambió a procesado, detenemos y actualizamos UI
          if (updatedDoc.procesado) {
            setDocInterno(updatedDoc);
            setIsPolling(false);
            // Actualizar estados de tarea si cambiaron durante el proceso
            if (updatedDoc.estado_tarea) setEstadoTarea(updatedDoc.estado_tarea);
            if (updatedDoc.fecha_plazo) setFechaPlazo(updatedDoc.fecha_plazo ? new Date(updatedDoc.fecha_plazo) : null);
            toast.success("✅ Análisis completado");
          } else {
            setPollingCounter(c => c + 1);
          }
        }
      } catch (err) {
        console.error("Error polling documento:", err);
      }
    }, 3000);

    // Timeout de 2 minutos para dejar de hacer polling ( OCR puede ser lento)
    const timeoutId = setTimeout(() => {
      if (isPolling) {
        setIsPolling(false);
        if (!docInterno.procesado) {
          toast.error("El proceso está tardando más de lo esperado. Reintentado manualmente...");
        }
      }
    }, 120000);

    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [isPolling, docInterno.id, isPreview, docInterno.procesado]);

  // Cargar usuarios al cambiar departamento
  useEffect(() => {
    if (estadoTarea) {
      setLoadingUsers(true);
      axios.post('/api/users/por-departamento', { nombre_departamento: estadoTarea }, { withCredentials: true })
        .then(res => {
          if (res.data.success) setUsuariosDepto(res.data.users);
        })
        .catch(console.error)
        .finally(() => setLoadingUsers(false));
    }
  }, [estadoTarea]);

  const handleAsignarTarea = async () => {
    setIsAsignando(true);

    // ✅ TOAST: Loading durante asignación
    const toastId = toast.loading('Asignando tarea...');

    try {
      await axios.post(`/api/documentos/${documento.id}/asignar-tarea`, {
        estado_tarea: estadoTarea,
        asignado_a_id: usuarioAsignado || null,
        fecha_plazo: fechaPlazo ? fechaPlazo.toISOString() : null
      }, { withCredentials: true });

      // ✅ TOAST: Éxito
      toast.success("✅ Tarea asignada correctamente", { id: toastId });

      // ✅ ESPERAR 800ms PARA QUE SE VEA EL TOAST, LUEGO CERRAR
      setTimeout(() => {
        onStatusChange();  // Recargar lista
        onClose();         // ← CERRAR MODAL (esto faltaba)
      }, 800);

    } catch (err) {
      // ✅ TOAST: Error
      toast.error("❌ Error al asignar tarea", { id: toastId });
      setError("Error asignando tarea");
    } finally {
      setIsAsignando(false);
    }
  };

  const handleAddEmail = async () => {
    if (!newEmailInput.includes('@')) {
      toast.error("Email inválido");
      return;
    }

    setIsAddingEmail(true);

    try {
      const res = await axios.post(`/api/empresas/${empresa.id}/agregar-email`, {
        email: newEmailInput
      }, { withCredentials: true });

      if (res.data.success) {
        setEmpresa(res.data.empresa);
        setSelectedEmails(prev => [...prev, newEmailInput]);
        setShowAddEmail(false);
        setNewEmailInput('');
        toast.success("Email agregado correctamente");
      }
    } catch {
      toast.error("Error al agregar email");
    } finally {
      setIsAddingEmail(false);
    }
  };

  const toggleEmail = (email) => {
    setSelectedEmails(prev =>
      prev.includes(email)
        ? prev.filter(e => e !== email)
        : [...prev, email]
    );
  };

  const handleOpenEmailPreview = async () => {
    if (selectedEmails.length === 0) {
      toast.error("Selecciona al menos un destinatario");
      return;
    }

    setIsPreviewLoading(true);

    try {
      const res = await axios.get(`/api/documentos/${documento.id}/previsualizar-email`, {
        withCredentials: true
      });

      if (res.data.success) {
        setEmailPreview({ ...res.data, destinatarios: selectedEmails });
        setShowConfirmModal(true);
      }
    } catch {
      setError("Error generando preview");
      toast.error("Error al generar preview del email");
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleMarcarPendiente = async () => {
    if (!window.confirm("¿Mover este documento a 'Por Procesar'?")) return;

    setIsMarkingPending(true);
    const toastId = toast.loading('Moviendo a Por Procesar...');

    try {
      await axios.post(`/api/documentos/${documento.id}/marcar-pendiente`, {}, {
        withCredentials: true
      });

      toast.success('Documento movido a Por Procesar', { id: toastId });

      setTimeout(() => {
        onStatusChange();
        onClose();
      }, 800);
    } catch {
      setError("Error al mover documento");
      toast.error('Error al mover documento', { id: toastId });
    } finally {
      setIsMarkingPending(false);
    }
  };

  const handleGuardar = async () => {
    if (!window.confirm("¿Archivar este documento?")) return;

    setIsSaving(true);
    const toastId = toast.loading('Archivando documento...');

    try {
      await axios.post(`/api/documentos/${documento.id}/guardar`, {}, {
        withCredentials: true
      });

      toast.success('Documento archivado correctamente', { id: toastId });

      setTimeout(() => {
        onStatusChange();
        onClose();
      }, 800);
    } catch {
      setError("Error al archivar");
      toast.error('Error al archivar documento', { id: toastId });
    } finally {
      setIsSaving(false);
    }
  };

  const emailsDisponibles = empresa
    ? [empresa.email, ...(empresa.emails_extra || [])].filter(Boolean)
    : [];

  const accionFinalRealizada = documento.email_enviado || documento.guardado;

  return (
    <>
      <div
        className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4"
        style={{ zIndex: 50 }}
        onClick={onClose}
      >
        <div
          className="bg-white rounded-lg shadow-2xl w-full max-w-6xl h-[90vh] overflow-hidden flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b bg-gray-50">
            <div className="flex items-center gap-3 min-w-0">
              <h2 className="text-xl font-semibold text-gray-900 truncate">
                {documento.nombre_archivo}
              </h2>
              {/* Badge: Pendiente de Envío */}
              {!documento.email_enviado && docInterno.datos_extraidos?.email_preparado?.listo_para_enviar && (
                <span className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700 border border-orange-200">
                  <Mail className="w-3 h-3" />
                  Pendiente de Envío
                </span>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Contenido */}
          <div className={`flex-1 grid gap-4 h-full overflow-hidden ${isPreview ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'
            }`}>
            {/* PDF Viewer */}
            <div className={`bg-gray-100 h-full ${isPreview ? 'col-span-1' : ''}`}>
              <MobilePDFViewer
                documentId={documento.id}
                pdfUrl={isPreview && documento.id === -1 ? pdfUrl : undefined}
              />
            </div>

            {/* Panel Derecho (solo si NO es preview) */}
            {!isPreview && (
              <div className="p-6 overflow-y-auto bg-white">

                {/* Datos Extraídos */}
                <h3 className="text-lg font-semibold text-blue-600 mb-4">
                  Datos Extraídos
                </h3>
                {isPolling ? (
                  <div className="flex flex-col items-center justify-center py-8 bg-white/50 rounded border border-dashed border-blue-200">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-2" />
                    <p className="text-sm font-medium text-blue-700">Analizando documento...</p>
                    <p className="text-[10px] text-blue-400 mt-1 italic">Extrayendo datos y destinatarios</p>
                  </div>
                ) : (
                  <>
                    {typeof docInterno.importe_pagar === 'number' && (
                      <div className="border-b border-blue-200 pb-1 mb-2">
                        <span className="text-xs text-blue-600 font-bold uppercase">
                          TOTAL A PAGAR (RLC)
                        </span>
                        <div className="text-lg font-bold text-blue-900">
                          {new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(docInterno.importe_pagar)}
                        </div>
                      </div>
                    )}
                    {Object.keys(datosIA).length > 0 ? (
                      Object.entries(datosIA).map(([k, v]) => {
                        const EXCLUIR = new Set(['_metadata', 'email_preparado']);
                        if (EXCLUIR.has(k)) return null;

                        // --- RENDERIZADO PERSONALIZADO PARA LISTAS (Ej: Trabajadores) ---
                        if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') {
                          return (
                            <div key={k} className="mt-4 mb-6">
                              <h4 className="text-sm font-bold text-gray-700 mb-2 capitalize flex items-center gap-2">
                                <Users className="w-4 h-4 text-blue-500" />
                                {k.replace(/_/g, ' ')}
                              </h4>
                              <div className="overflow-x-auto border border-blue-100 rounded-lg bg-gray-50 shadow-sm">
                                <table className="min-w-full divide-y divide-blue-200">
                                  <thead className="bg-blue-50">
                                    <tr>
                                      {Object.keys(v[0]).map(col => (
                                        <th key={col} className="px-3 py-2 text-left text-[10px] font-bold text-blue-600 uppercase tracking-wider">
                                          {col.replace(/_/g, ' ')}
                                        </th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-100">
                                    {v.map((item, idx) => (
                                      <tr key={idx} className="hover:bg-blue-50/30 transition-colors">
                                        {Object.values(item).map((val, i) => (
                                          <td key={i} className="px-3 py-2 whitespace-nowrap text-xs text-gray-700">
                                            {String(val || '—')}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          );
                        }

                        // --- RENDERIZADO ESTÁNDAR PARA CAMPOS SIMPLES ---
                        let valorRender;
                        if (v === null || v === undefined || v === '') {
                          valorRender = '—';
                        } else if (typeof v === 'object') {
                          valorRender = (
                            <pre className="text-xs whitespace-pre-wrap font-mono bg-gray-50 rounded p-1 border border-gray-100">
                              {JSON.stringify(v, null, 2)}
                            </pre>
                          );
                        } else {
                          valorRender = String(v);
                        }

                        return (
                          <div key={k} className="border-b border-blue-50 py-2 group hover:bg-blue-50/20 transition-colors px-1">
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
                              {k.replace(/_/g, ' ')}
                            </span>
                            <div className="text-sm font-medium text-gray-800 break-words">{valorRender}</div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="flex flex-col items-center py-4">
                        <p className="text-sm text-gray-400 italic mb-3">No se han extraído datos aún.</p>
                        <button
                          onClick={() => {
                            // Usar el mismo endpoint que el botón IA
                            axios.post(`/api/documentos/${docInterno.id}/procesar`, {}, { withCredentials: true })
                              .then(() => setIsPolling(true)) // Reiniciar polling
                              .catch(err => console.error("Error al reintentar:", err));
                          }}
                          className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-blue-600 border border-blue-200 rounded hover:bg-blue-50 transition-colors"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Reintentar / Forzar Análisis OCR
                        </button>
                      </div>
                    )}
                  </>
                )}

                <hr className="my-6 border-gray-200" />

                {/* SECCIÓN ASIGNACIÓN */}
                <h3 className="text-lg font-semibold text-yellow-800 mb-4">
                  Asignar Tarea
                </h3>
                <div className="space-y-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">

                  {/* 1. Departamento */}
                  <div>
                    <label className="text-xs font-bold text-gray-500 uppercase mb-1 block">
                      Departamento
                    </label>
                    <select
                      value={estadoTarea}
                      onChange={(e) => setEstadoTarea(e.target.value)}
                      className="w-full p-2 border rounded text-sm bg-white"
                    >
                      <option>Pendiente (General)</option>
                      <option>Pendiente (Fiscal)</option>
                      <option>Pendiente (Laboral)</option>
                      <option>Pendiente (Administrativo)</option>
                    </select>
                  </div>

                  {/* 2. Usuario Específico */}
                  <div>
                    <label className="text-xs font-bold text-gray-500 uppercase mb-1 flex justify-between">
                      Asignar a Persona (Opcional)
                      {loadingUsers && <Loader2 className="w-3 h-3 animate-spin" />}
                    </label>
                    <div className="relative">
                      <User className="absolute left-2 top-2.5 w-4 h-4 text-gray-400" />
                      <select
                        value={usuarioAsignado}
                        onChange={(e) => setUsuarioAsignado(e.target.value)}
                        className="w-full pl-8 p-2 border rounded text-sm bg-white disabled:bg-gray-100"
                        disabled={loadingUsers || usuariosDepto.length === 0}
                      >
                        <option value="">-- Cualquiera del equipo --</option>
                        {usuariosDepto.map(u => (
                          <option key={u.id} value={u.id}>{u.nombre}</option>
                        ))}
                      </select>
                    </div>
                    {usuariosDepto.length === 0 && !loadingUsers && (
                      <p className="text-[10px] text-primary mt-1">
                        No se encontraron usuarios en este departamento.
                      </p>
                    )}
                  </div>

                  {/* 3. Fecha Límite */}
                  <div>
                    <label className="text-xs font-bold text-gray-500 uppercase mb-1 block">
                      Fecha Límite
                    </label>
                    <DatePicker
                      selected={fechaPlazo}
                      onChange={setFechaPlazo}
                      placeholderText="Sin fecha límite"
                      className="w-full p-2 border rounded text-sm bg-white"
                      dateFormat="dd/MM/yyyy"
                    />
                  </div>

                  {/* Botón Guardar Tarea */}
                  <button
                    onClick={handleAsignarTarea}
                    disabled={isAsignando}
                    className="w-full py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700 flex justify-center items-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {isAsignando ? (
                      <Loader2 className="animate-spin w-4 h-4" />
                    ) : (
                      <Save className="w-4 h-4" />
                    )}
                    Guardar Tarea
                  </button>
                </div>

                <hr className="my-6 border-gray-200" />

                {/* Acciones Finales */}
                <h3 className="text-lg font-semibold text-gray-800 mb-4">
                  Acciones Finales
                </h3>
                <div className={`space-y-4 ${accionFinalRealizada ? 'opacity-50 pointer-events-none' : ''
                  }`}>

                  {/* Destinatarios */}
                  <div className="bg-gray-50 p-3 rounded border border-gray-200">
                    <div className="flex justify-between items-center mb-2">
                      <label className="text-sm font-medium flex items-center gap-2">
                        <Users className="w-4 h-4" /> Destinatarios:
                      </label>
                      {!showAddEmail && (
                        <button
                          onClick={() => setShowAddEmail(true)}
                          className="text-xs text-blue-600 flex items-center gap-1 hover:underline"
                        >
                          <Plus className="w-3 h-3" /> Nuevo
                        </button>
                      )}
                    </div>

                    {/* Input para agregar email */}
                    {showAddEmail && (
                      <div className="flex gap-2 mb-3">
                        <input
                          className="flex-1 p-1 text-sm border rounded"
                          placeholder="email@ejemplo.com"
                          value={newEmailInput}
                          onChange={(e) => setNewEmailInput(e.target.value)}
                        />
                        <button
                          onClick={handleAddEmail}
                          disabled={isAddingEmail}
                          className="p-1 bg-green-600 text-white rounded"
                        >
                          {isAddingEmail ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Check className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => setShowAddEmail(false)}
                          className="p-1 bg-gray-300 rounded"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    )}

                    {/* Lista de emails */}
                    <div className="max-h-32 overflow-y-auto space-y-1 border border-gray-200 rounded p-2 bg-white">
                      {emailsDisponibles.length === 0 ? (
                        <p className="text-xs text-gray-400 italic">Sin emails configurados</p>
                      ) : (
                        emailsDisponibles.map((email, i) => (
                          <label
                            key={i}
                            className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded"
                          >
                            <input
                              type="checkbox"
                              checked={selectedEmails.includes(email)}
                              onChange={() => toggleEmail(email)}
                            />
                            <span className="text-sm text-gray-700">{email}</span>
                          </label>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Botones de acción */}
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={handleOpenEmailPreview}
                      disabled={selectedEmails.length === 0 || accionFinalRealizada || isPreviewLoading}
                      className="py-2.5 bg-green-600 text-white rounded hover:bg-green-700 flex justify-center gap-2 disabled:opacity-50"
                    >
                      {isPreviewLoading ? (
                        <Loader2 className="animate-spin w-4 h-4" />
                      ) : (
                        <Mail className="w-4 h-4" />
                      )}
                      Enviar Email
                    </button>

                    <button
                      onClick={handleGuardar}
                      disabled={accionFinalRealizada || isSaving}
                      className="py-2.5 bg-blue-600 text-white rounded hover:bg-blue-700 flex justify-center gap-2 disabled:opacity-50"
                    >
                      {isSaving ? (
                        <Loader2 className="animate-spin w-4 h-4" />
                      ) : (
                        <Archive className="w-4 h-4" />
                      )}
                      Archivar
                    </button>
                  </div>
                </div>

                {/* Botón Revertir */}
                <div className="mt-4 pt-4 border-t">
                  <button
                    onClick={handleMarcarPendiente}
                    disabled={isMarkingPending}
                    className="w-full py-2 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 flex justify-center gap-2 disabled:opacity-50"
                  >
                    {isMarkingPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RotateCcw className="w-4 h-4" />
                    )}
                    Revertir a Pendiente
                  </button>
                </div>

                {/* Error */}
                {error && (
                  <div className="mt-3 bg-red-50 text-red-600 p-3 rounded text-sm text-center">
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal de Confirmación de Email */}
      {showConfirmModal && (
        <div style={{ position: 'relative', zIndex: 9999 }}>
          <ConfirmarEmailModal
            documento={documento}
            emailPreview={emailPreview}
            onClose={() => setShowConfirmModal(false)}
            onEmailSent={() => {
              setShowConfirmModal(false);
              onStatusChange();
            }}
          />
        </div>
      )}
    </>
  );
}