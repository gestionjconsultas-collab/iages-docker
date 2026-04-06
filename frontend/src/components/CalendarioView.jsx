// frontend/src/components/CalendarioView.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTareas } from '../hooks/useTareas';
import { useNotificacionesCalendario } from '../hooks/useSaltra';
import { useCalendarioTributario } from '../hooks/useCalendarioTributario';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { Calendar, Loader2, AlertTriangle, X, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import TaskOriginBadge from './TaskOriginBadge';
import socket from '../socket'; // ⭐ Import socket

export default function CalendarioView() {
  const navigate = useNavigate();
  const [selectedTarea, setSelectedTarea] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [selectedFechaTributaria, setSelectedFechaTributaria] = useState(null);
  const [showModalTributaria, setShowModalTributaria] = useState(false);

  // ✅ REACT QUERY: Usa el hook useTareas
  const { data, isLoading, error: queryError, refetch } = useTareas();
  const { data: notifData } = useNotificacionesCalendario(); // Todas las DEHU pendientes
  const { data: tributarioData } = useCalendarioTributario(); // 🆕 Fechas tributarias AEAT

  // ⭐ Auto-refresh: Escuchar evento stats_updated
  useEffect(() => {
    socket.on('stats_updated', () => {
      console.log('📅 Stats updated, refetching calendario data...');
      refetch(); // Refetch tareas
    });

    // Cleanup
    return () => {
      socket.off('stats_updated');
    };
  }, [refetch]);

  // Backend retorna eventos YA formateados
  const eventos = data?.eventos || [];

  console.log('📅 Datos del calendario:', data);
  console.log('📅 Eventos:', eventos);
  console.log('📅 Total eventos:', eventos.length);

  // ✅ Agregar TODAS las notificaciones DEHU pendientes al calendario
  const eventosDehu = (notifData?.notificaciones || []).map(notif => {
    const hoy = new Date();
    const vencimiento = new Date(notif.expiration_date);
    const diasRestantes = Math.ceil((vencimiento - hoy) / (1000 * 60 * 60 * 24));

    // Colores según urgencia
    let backgroundColor, borderColor;
    if (diasRestantes <= 3) {
      backgroundColor = '#dc2626'; // Rojo crítico
      borderColor = '#991b1b';
    } else if (diasRestantes <= 7) {
      backgroundColor = '#f59e0b'; // Naranja advertencia
      borderColor = '#d97706';
    } else {
      backgroundColor = '#8b5cf6'; // Morado normal
      borderColor = '#7c3aed';
    }

    // Título con NIF + nombre de empresa
    const nif = notif.nif_titular || 'Sin NIF';
    const empresa = notif.empresa_nombre || '';
    const titulo = empresa ? `🔔 ${nif} - ${empresa}` : `🔔 ${nif}`;

    return {
      id: `dehu-${notif.id}`,
      title: titulo,
      start: notif.expiration_date,
      backgroundColor,
      borderColor,
      textColor: '#ffffff',
      extendedProps: {
        tipo: 'dehu',
        notificacion: notif,
        diasRestantes
      }
    };
  });

  // 🆕 Agregar fechas tributarias AEAT al calendario
  const eventosTributarios = tributarioData?.eventos || [];

  // Combinar eventos de tareas y DEHU
  const todosLosEventos = [...eventos, ...eventosDehu, ...eventosTributarios];

  console.log('� Notificaciones DEHU:', notifData);
  console.log('🔔 Eventos DEHU generados:', eventosDehu);
  console.log('📊 Todos los eventos combinados:', todosLosEventos);



  const handleEventClick = (info) => {
    const eventType = info.event.extendedProps.tipo;

    if (eventType === 'dehu') {
      // Para notificaciones DEHU, redirigir a Saltra
      const notificacion = info.event.extendedProps.notificacion;
      navigate(`/saltra?notif=${notificacion.id}`);
    } else if (eventType === 'tributaria') {
      // 🆕 Para fechas tributarias, mostrar modal con detalles
      const data = info.event.extendedProps.data;
      if (data) {
        setSelectedFechaTributaria(data);
        setShowModalTributaria(true);
      }
    } else {
      // Para tareas, mostrar modal
      const tarea = info.event.extendedProps.data;
      if (tarea) {
        setSelectedTarea(tarea);
        setShowModal(true);
      }
    }
  };

  const marcarComoCompletada = async (tareaId) => {
    try {
      await axios.put(`/api/tareas/${tareaId}`, {
        estado: 'completada',
        fecha_completada: new Date().toISOString()
      }, { withCredentials: true });

      toast.success('Tarea marcada como completada');
      setShowModal(false);
      refetch(); // Recargar tareas
    } catch (error) {
      console.error('Error:', error);
      toast.error('Error al actualizar tarea');
    }
  };

  const getDiasVencida = (fechaVencimiento) => {
    if (!fechaVencimiento) return 0;
    const hoy = new Date();
    const vencimiento = new Date(fechaVencimiento);
    const diff = Math.floor((hoy - vencimiento) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
        <p className="text-gray-600">Cargando tareas...</p>
      </div>
    );
  }

  if (queryError) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-600">Error al cargar tareas: {queryError.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Calendar className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Calendario de Tareas</h1>
            <p className="text-gray-600 mt-1">
              {eventos.length} {eventos.length === 1 ? 'tarea programada' : 'tareas programadas'}
            </p>
          </div>
        </div>
      </div>

      {/* Advertencia de tareas sin fecha */}
      {data?.tareas_sin_fecha > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-yellow-900">
                {data.tareas_sin_fecha} {data.tareas_sin_fecha === 1 ? 'tarea no tiene' : 'tareas no tienen'} fecha de vencimiento
              </h3>
              <p className="text-sm text-yellow-700 mt-1">
                Estas tareas se muestran en la fecha de creación. Para programarlas correctamente,
                edítalas y asigna una fecha de vencimiento.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Leyenda de Colores */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-green-500"></div>
            <span className="text-gray-700">Tarea Completada</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-500"></div>
            <span className="text-gray-700">Tarea Vencida o Crítica (≤3d) / DEHU Crítico</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-yellow-500"></div>
            <span className="text-gray-700">Tarea Advertencia (4-7d) / DEHU Advertencia</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-blue-500"></div>
            <span className="text-gray-700">Tarea Pendiente (&gt;7d)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-purple-500"></div>
            <span className="text-gray-700">DEHU Normal (\u003e7d)</span>
          </div>
        </div>
      </div>

      {/* Calendario */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <FullCalendar
          plugins={[dayGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          locale={esLocale}
          events={todosLosEventos}
          eventClick={handleEventClick}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,dayGridWeek'
          }}
          buttonText={{
            today: 'Hoy',
            month: 'Mes',
            week: 'Semana'
          }}
          height="auto"
          eventTimeFormat={{
            hour: '2-digit',
            minute: '2-digit',
            meridiem: false
          }}
          eventDisplay="block"
          dayMaxEvents={3}
          moreLinkText="más"
        />
      </div>

      {/* Modal de Detalles de Tarea */}
      {showModal && selectedTarea && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            {/* Header del Modal */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Detalles de la Tarea</h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Contenido del Modal */}
            <div className="p-6 space-y-4">
              {/* Título */}
              <div>
                <h3 className="text-2xl font-bold text-gray-900">{selectedTarea.titulo}</h3>
              </div>

              {/* Estado */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${selectedTarea.estado === 'completada' ? 'bg-green-100 text-green-700' :
                  selectedTarea.estado === 'en_progreso' ? 'bg-blue-100 text-blue-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                  {selectedTarea.estado === 'completada' ? '✅ Completada' :
                    selectedTarea.estado === 'en_progreso' ? '🔄 En Progreso' :
                      '⏳ Pendiente'}
                </span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${selectedTarea.prioridad === 'alta' ? 'bg-red-100 text-red-700' :
                  selectedTarea.prioridad === 'media' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                  {selectedTarea.prioridad === 'alta' ? '🔴 Alta' :
                    selectedTarea.prioridad === 'media' ? '🟡 Media' :
                      '⚪ Baja'}
                </span>
                {/* Mostrar origen de la tarea */}
                <TaskOriginBadge
                  origen={selectedTarea.origen || 'manual'}
                  creado_por={selectedTarea.creado_por}
                  size="small"
                  showLabel={true}
                />
              </div>

              {/* Descripción */}
              {selectedTarea.descripcion && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Descripción</label>
                  <p className="text-gray-600">{selectedTarea.descripcion}</p>
                </div>
              )}

              {/* Fecha de Vencimiento */}
              {selectedTarea.fecha_vencimiento && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Fecha de Vencimiento</label>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-900">
                      {new Date(selectedTarea.fecha_vencimiento).toLocaleDateString('es-ES', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                  {getDiasVencida(selectedTarea.fecha_vencimiento) > 0 && selectedTarea.estado !== 'completada' && (
                    <div className="mt-2 flex items-center gap-2 text-red-600">
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">
                        Vencida hace {getDiasVencida(selectedTarea.fecha_vencimiento)} día(s)
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* Asignado a */}
              {selectedTarea.asignado_a && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Asignado a</label>
                  <p className="text-gray-900">{selectedTarea.asignado_a}</p>
                </div>
              )}

              {/* Empresa */}
              {selectedTarea.empresa && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Empresa</label>
                  <p className="text-gray-900">{selectedTarea.empresa}</p>
                </div>
              )}

              {/* ⭐ NUEVO: Botón para ir al documento */}
              {selectedTarea.documento_id && selectedTarea.empresa_id && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-blue-900 block mb-1">
                        📄 Documento Asociado
                      </label>
                      <p className="text-xs text-blue-700">
                        {selectedTarea.documento_categoria
                          ? `Ubicado en: ${selectedTarea.documento_categoria}`
                          : 'Esta tarea está vinculada a un documento'}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        // Redirigir a la carpeta donde está el documento
                        const categoria = selectedTarea.documento_categoria || 'Notificaciones';
                        window.location.href = `/empresa/${selectedTarea.empresa_id}/${categoria}`;
                      }}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 text-sm font-medium"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Ir al Documento
                    </button>
                  </div>
                </div>
              )}

              {/* Fecha de Completación */}
              {selectedTarea.fecha_completada && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Completada el</label>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-gray-900">
                      {new Date(selectedTarea.fecha_completada).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Footer con Acciones */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cerrar
              </button>
              {selectedTarea.estado !== 'completada' && (
                <button
                  onClick={() => marcarComoCompletada(selectedTarea.id)}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  Marcar como Completada
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 🆕 Modal para Fechas Tributarias */}
      {showModalTributaria && selectedFechaTributaria && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="bg-gradient-to-r from-purple-600 to-purple-700 px-6 py-4 flex justify-between items-center">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                📋 Fecha Tributaria AEAT
              </h2>
              <button
                onClick={() => setShowModalTributaria(false)}
                className="text-white hover:bg-purple-800 p-2 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* Título */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Título</label>
                <p className="text-gray-900 font-semibold text-lg">{selectedFechaTributaria.titulo}</p>
              </div>

              {/* Fecha */}
              <div>
                <label className="text-sm font-medium text-gray-700 block mb-1">Fecha de Vencimiento</label>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-purple-600" />
                  <span className="text-gray-900 font-medium">
                    {new Date(selectedFechaTributaria.fecha).toLocaleDateString('es-ES', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      weekday: 'long'
                    })}
                  </span>
                </div>
              </div>

              {/* Descripción */}
              {selectedFechaTributaria.descripcion && (
                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Descripción</label>
                  <p className="text-gray-700">{selectedFechaTributaria.descripcion}</p>
                </div>
              )}

              {/* Detalles en Grid */}
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
                {selectedFechaTributaria.tipo_impuesto && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Tipo de Impuesto</label>
                    <span className="inline-block px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                      {selectedFechaTributaria.tipo_impuesto}
                    </span>
                  </div>
                )}

                {selectedFechaTributaria.modelo && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Modelo</label>
                    <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                      Modelo {selectedFechaTributaria.modelo}
                    </span>
                  </div>
                )}

                {selectedFechaTributaria.periodicidad && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Periodicidad</label>
                    <span className="text-gray-900">{selectedFechaTributaria.periodicidad}</span>
                  </div>
                )}

                <div>
                  <label className="text-sm font-medium text-gray-700 block mb-1">Año</label>
                  <span className="text-gray-900">{selectedFechaTributaria.año}</span>
                </div>

                {selectedFechaTributaria.trimestre && (
                  <div>
                    <label className="text-sm font-medium text-gray-700 block mb-1">Trimestre</label>
                    <span className="text-gray-900">T{selectedFechaTributaria.trimestre}</span>
                  </div>
                )}
              </div>

              {/* Información adicional */}
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mt-4">
                <p className="text-sm text-purple-800">
                  <strong>Nota:</strong> Esta información proviene del calendario oficial del contribuyente de la Agencia Tributaria.
                  Verifica siempre las fechas en la sede electrónica de la AEAT.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => setShowModalTributaria(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
              >
                Cerrar
              </button>
              <a
                href={selectedFechaTributaria.fuente_url || 'https://sede.agenciatributaria.gob.es'}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Ver en AEAT
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}