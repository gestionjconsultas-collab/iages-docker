import { useState } from 'react';
import toast from 'react-hot-toast';
import { CheckCircle } from 'lucide-react';
import socket from '../socket'; // ✅ Usar singleton global — evita doble conexión WebSocket

/**
 * Hook para monitorear procesamiento de nóminas/seguros en tiempo real
 */
export const useProcessingMonitor = () => {
  const [activeToasts, setActiveToasts] = useState({});

  // Helper para mostrar el toast de éxito detallado y devolver resultados
  const showSuccessToast = (data, tid, ttype, onSuccess = null) => {
    // Normalizar resultados para que sean compatibles con el dashboard (ImportadorView.jsx)
    const formattedResult = {
      ...data,
      success: true,
      total_empresas: data.total_empresas || data.empresas_procesadas || 0,
      total_trabajadores: data.total_trabajadores || 0,
      periodo: data.periodo || '',
      detalles: data.detalles || []
    };

    // Mapear claves específicas según el tipo
    if (ttype === 'nominas') {
      // 🔧 FIX: Expandir detalles de empresa a detalles de trabajadores
      // Backend envía 1 objeto por empresa con array 'trabajadores'
      // Frontend necesita 1 objeto por trabajador para la tabla
      const detallesExpandidos = [];
      (data.detalles || []).forEach(empresa => {
        if (empresa.trabajadores && empresa.trabajadores.length > 0) {
          // Crear un objeto por cada trabajador
          empresa.trabajadores.forEach(nombreTrabajador => {
            detallesExpandidos.push({
              estado: empresa.empresa_id ? 'success' : 'warning',
              nombre_trabajador: nombreTrabajador,
              empresa: empresa.empresa_bd_nombre || empresa.razon_social || 'Desconocida',
              empresa_id: empresa.empresa_id,
              nif: empresa.nif,
              periodo: empresa.periodo,
              mensaje: empresa.empresa_id ? 'Clasificado correctamente' : 'Pendiente de clasificar'
            });
          });
        } else {
          // Si no hay trabajadores individuales, usar el objeto de empresa
          detallesExpandidos.push({
            estado: empresa.empresa_id ? 'success' : 'warning',
            nombre_trabajador: `${empresa.num_trabajadores || 0} trabajadores`,
            empresa: empresa.empresa_bd_nombre || empresa.razon_social || 'Desconocida',
            empresa_id: empresa.empresa_id,
            nif: empresa.nif,
            periodo: empresa.periodo,
            mensaje: empresa.empresa_id ? 'Clasificado correctamente' : 'Pendiente de clasificar'
          });
        }
      });

      formattedResult.detalles = detallesExpandidos;
      formattedResult.no_encontradas = (data.detalles || []).filter(d => !d.empresa_id);
      formattedResult.empresas_clasificadas = (data.detalles || []).filter(d => d.empresa_id).length;
      formattedResult.empresas_no_encontradas = formattedResult.no_encontradas.length;
      formattedResult.documentos_creados = formattedResult.empresas_clasificadas;
    } else if (ttype === 'seguros') {
      // Los detalles ya vienen normalizados con: estado, nombre_trabajador, empresa, mensaje
      // Calcular contadores desde los campos normalizados
      const detallesSS = data.detalles || [];
      formattedResult.rlc_procesados = data.rlc_procesados || detallesSS.filter(d => (d.nombre_trabajador || '').toUpperCase().startsWith('RLC')).length;
      formattedResult.rnt_procesados = data.rnt_procesados || detallesSS.filter(d => (d.nombre_trabajador || '').toUpperCase().startsWith('RNT')).length;
      formattedResult.empresas_asociadas = data.empresas_asociadas || detallesSS.filter(d => d.estado === 'exito' || d.estado === 'success').length;
      formattedResult.empresas_no_encontradas = data.empresas_no_encontradas || detallesSS.filter(d => d.estado === 'advertencia' || d.estado === 'warning').length;
      formattedResult.empresas_no_encontradas_lista = data.empresas_no_encontradas_lista || detallesSS.filter(d => d.estado === 'advertencia' || d.estado === 'warning').map(d => d.empresa || d.nombre_trabajador);
      formattedResult.documentos_creados = data.documentos_creados || formattedResult.empresas_asociadas;
    }

    // Evitar duplicados
    setActiveToasts(prev => {
      // Si el tid no existe o el toast ya fue reemplazado, no hacemos nada
      // Pero si tid es 'aggregated', siempre intentamos mostrarlo
      if (!prev[tid] && tid !== 'aggregated') return prev;

      toast.success((t) => (
        <div className="flex flex-col gap-3 min-w-[300px]">
          <div className="font-semibold text-green-800 flex items-center gap-2">
            <CheckCircle className="w-5 h-5" />
            Procesamiento completado
          </div>
          <div className="text-sm space-y-1">
            {ttype === 'seguros' ? (
              <>
                <div>📄 RLC: <strong>{formattedResult.rlc_procesados}</strong> | RNT: <strong>{formattedResult.rnt_procesados}</strong></div>
                <div>🏢 Empresas Asociadas: <strong>{formattedResult.empresas_asociadas}</strong></div>
              </>
            ) : (
              <>
                <div>📊 <strong>{formattedResult.total_empresas}</strong> empresas procesadas</div>
                <div>👥 <strong>{formattedResult.total_trabajadores}</strong> trabajadores</div>
                <div>✓ Clasificadas: <strong>{formattedResult.empresas_clasificadas}</strong></div>
              </>
            )}
            {formattedResult.periodo && <div>📅 Periodo: <strong>{formattedResult.periodo}</strong></div>}
            <div className="text-xs text-gray-500 italic mt-1 pt-1 border-t border-gray-200">
              {ttype === 'seguros'
                ? `Clasificadas: ${formattedResult.empresas_asociadas}`
                : `Clasificadas: ${formattedResult.empresas_clasificadas}`}
            </div>
          </div>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded transition-colors shadow-sm text-sm"
          >
            Aceptar
          </button>
        </div>
      ), {
        duration: Infinity,
        position: 'bottom-right'
      });

      const newToasts = { ...prev };
      delete newToasts[tid];
      return newToasts;
    });

    // Llamar al callback con los resultados formateados
    if (onSuccess) {
      console.log('📤 Enviando resultados al componente:', formattedResult);
      onSuccess(formattedResult);
    }
  };

  const startMonitoring = (taskId, tipo = 'nominas', onFinished = null, onSuccess = null) => {
    console.log('🚀 Iniciando monitoreo de tarea:', taskId, 'tipo:', tipo);

    if (!socket.connected) {
      console.error('❌ Socket no conectado');
      toast.error('Error: Socket.IO no conectado. Recarga la página.');
      return;
    }

    const startTime = Date.now();
    const progressEvent = tipo === 'nominas' ? 'nomina_progress' : 'seguro_progress';
    const completionEvent = tipo === 'nominas' ? 'nomina_completed' : 'seguro_completed';

    // Toast de procesamiento inicial
    const toastId = toast.loading(
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="font-semibold">Procesando {tipo}...</span>
        </div>
        <div className="text-sm text-gray-600">
          Iniciando procesamiento...
        </div>
      </div>,
      {
        duration: Infinity,
        position: 'bottom-right'
      }
    );

    setActiveToasts(prev => ({ ...prev, [taskId]: toastId }));

    // Flag para evitar que progress/polling re-creen el toast tras completarse
    let isCompleted = false;

    // Helper para formatear tiempo
    const formatTime = (seconds) => {
      if (!isFinite(seconds) || seconds < 0) return 'Calculando...';
      if (seconds < 60) return `~${Math.round(seconds)} seg`;
      return `~${Math.round(seconds / 60)} min`;
    };

    // Helper de limpieza centralizado
    const cleanup = (isSuccess = false, resultData = null) => {
      if (isCompleted) return;  // guard: solo ejecutar una vez
      isCompleted = true;
      clearInterval(pollInterval);
      socket.off(completionEvent, onCompleted);
      socket.off(progressEvent, onProgress);
      socket.off('nomina_error', onError);
      socket.off('seguro_error', onError);
      toast.dismiss(toastId);
      if (onFinished) onFinished();
      if (isSuccess && resultData !== null) {
        showSuccessToast(resultData, taskId, tipo, onSuccess);
      }
    };

    // Polling del progreso cada 2 segundos
    const pollInterval = setInterval(async () => {
      if (isCompleted) return;  // no seguir si ya terminó
      try {
        const response = await fetch(`/api/task-status/${taskId}`, {
          credentials: 'include'
        });

        if (!response.ok) return;

        const data = await response.json();

        if (isCompleted) return;  // check again tras el await

        if (data.state === 'PROGRESS') {
          const percent = data.percentage || data.percent || 0;
          const elapsed = (Date.now() - startTime) / 1000;
          const eta = percent > 5 ? (elapsed / (percent / 100)) - elapsed : null;

          toast.loading(
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="font-semibold">Procesando {tipo}...</span>
              </div>
              <div className="text-sm text-gray-600">
                {data.status || `${data.current}/${data.total} páginas (${percent}%)`}
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${percent}%` }}
                ></div>
              </div>
              {eta && (
                <div className="text-[10px] text-gray-500 text-right">
                  Tiempo restante: {formatTime(eta)}
                </div>
              )}
            </div>,
            { id: toastId }
          );
        } else if (data.state === 'SUCCESS') {
          cleanup(true, data.result || data);
        } else if (data.state === 'FAILURE') {
          cleanup();
          toast.error(`Error al procesar ${tipo}`);
        }
      } catch (error) {
        console.error('❌ Error en polling:', error);
      }
    }, 2000);

    // --- Listeners de Socket.IO ---

    const onCompleted = (data) => {
      if (data.task_id === taskId) {
        cleanup(true, data.result || data);
      }
    };

    const onError = (data) => {
      console.error('❌ Error recibido vía Socket.IO:', data);
      if (data.task_id === taskId) {
        cleanup();
        toast.error(`Error: ${data.error || 'Desconocido'}`);
      }
    };

    const onProgress = (data) => {
      if (isCompleted) return;  // no actualizar toast si ya terminó
      if (data.task_id === taskId) {
        const percent = data.percentage || data.percent || 0;
        const elapsed = (Date.now() - startTime) / 1000;
        const eta = percent > 5 ? (elapsed / (percent / 100)) - elapsed : null;

        toast.loading(
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="font-semibold">Procesando {tipo}...</span>
            </div>
            <div className="text-sm text-gray-600">
              {data.status || `${data.current}/${data.total} páginas (${percent}%)`}
            </div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${percent}%` }}
              ></div>
            </div>
            {eta && (
              <div className="text-[10px] text-gray-500 text-right">
                Tiempo restante: {formatTime(eta)}
              </div>
            )}
          </div>,
          { id: toastId }
        );
      }
    };

    socket.on(completionEvent, onCompleted);
    socket.on(progressEvent, onProgress);
    socket.on('nomina_error', onError);
    socket.on('seguro_error', onError);

    // Timeout de seguridad: 1 hora
    setTimeout(() => cleanup(), 3600000);
  };

  /**
   * Monitorear múltiples tareas (para PDFs divididos)
   * Muestra un solo toast con progreso agregado
   */
  const startMonitoringMultiple = (tasks, tipo = 'nominas', onFinished = null, onSuccess = null) => {
    if (!tasks || tasks.length === 0) {
      console.error('❌ No hay tareas para monitorear');
      return;
    }

    console.log(`🚀 Iniciando monitoreo de ${tasks.length} tareas:`, tasks);

    if (!socket.connected) {
      console.error('❌ Socket no conectado');
      toast.error('Error: Socket.IO no conectado. Recarga la página.');
      return;
    }

    const startTime = Date.now();
    const totalParts = tasks.length;
    const taskIds = tasks.map(t => t.task_id);
    const progressEvent = tipo === 'nominas' ? 'nomina_progress' : 'seguro_progress';
    const completionEvent = tipo === 'nominas' ? 'nomina_completed' : 'seguro_completed';

    // Toast de procesamiento inicial
    const toastId = toast.loading(
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="font-semibold">Procesando {tipo}...</span>
        </div>
        <div className="text-sm text-gray-600">
          Iniciando procesamiento de {totalParts} {totalParts > 1 ? 'partes' : 'parte'}...
        </div>
      </div>,
      {
        duration: Infinity,
        position: 'bottom-right'
      }
    );

    setActiveToasts(prev => ({ ...prev, ['aggregated']: toastId }));

    // Estado de cada tarea (local variable for closure)
    let currentTaskStates = {};
    taskIds.forEach(id => {
      currentTaskStates[id] = { state: 'PENDING', current: 0, total: 1, percent: 0 };
    });

    let totalResults = {
      total_empresas: 0,
      total_trabajadores: 0,
      periodo: null,
      empresas_clasificadas: 0,
      rlc_procesados: 0,
      rnt_procesados: 0,
      detalles: [],
      processed_tasks: new Set()
    };

    // --- listeners de Socket.IO ---

    const onProgress = (data) => {
      if (taskIds.includes(data.task_id)) {
        const existing = currentTaskStates[data.task_id];
        const newPercent = data.percentage || data.percent || 0;

        if (newPercent >= existing.percent) {
          currentTaskStates[data.task_id] = {
            ...existing,
            state: 'PROGRESS',
            percent: newPercent,
            status: data.status
          };
          updateAggregatedUI();
        }
      }
    };

    const onCompletedSocket = (data) => {
      if (taskIds.includes(data.task_id)) {
        currentTaskStates[data.task_id].state = 'SUCCESS';
        currentTaskStates[data.task_id].percent = 100;

        // Agregar resultados una sola vez por tarea
        const res = data.result || data;
        console.log('🔍 [DEBUG] Tarea completada:', data.task_id);
        console.log('🔍 [DEBUG] res.detalles:', res.detalles);
        console.log('🔍 [DEBUG] totalResults.detalles ANTES:', totalResults.detalles.length);

        if (!totalResults.processed_tasks.has(data.task_id)) {
          totalResults.processed_tasks.add(data.task_id);
          totalResults.total_empresas += res.total_empresas || res.empresas_procesadas || 0;
          totalResults.total_trabajadores += res.total_trabajadores || 0;
          totalResults.empresas_clasificadas += res.empresas_clasificadas || 0;
          totalResults.rlc_procesados += res.rlc_procesados || 0;
          totalResults.rnt_procesados += res.rnt_procesados || 0;
          if (res.detalles) totalResults.detalles = [...totalResults.detalles, ...res.detalles];
          if (!totalResults.periodo && res.periodo) totalResults.periodo = res.periodo;

          console.log('🔍 [DEBUG] totalResults.detalles DESPUÉS:', totalResults.detalles.length);
        }

        updateAggregatedUI();
      }
    };

    const onErrorSocket = (data) => {
      if (taskIds.includes(data.task_id)) {
        currentTaskStates[data.task_id].state = 'FAILURE';
        updateAggregatedUI();
      }
    };

    socket.on(progressEvent, onProgress);
    socket.on(completionEvent, onCompletedSocket);
    socket.on('nomina_error', onErrorSocket);
    socket.on('seguro_error', onErrorSocket);

    // --- Lógica de UI ---

    const updateAggregatedUI = () => {
      const states = Object.values(currentTaskStates);
      const completedCount = states.filter(s => s.state === 'SUCCESS').length;
      const failedCount = states.filter(s => s.state === 'FAILURE').length;
      const progressList = states.map(s => s.percent || 0);

      // Calcular progreso total real sumando porcentajes
      const totalProgress = progressList.reduce((sum, p) => sum + p, 0) / totalParts;

      // Si todo terminó (éxito o fallo)
      if (completedCount + failedCount === totalParts) {
        cleanup();
        if (onFinished) onFinished();

        if (failedCount === 0) {
          showSuccessToast(totalResults, 'aggregated', tipo, onSuccess);
        } else {
          toast.error(`Error al procesar ${tipo} (${failedCount}/${totalParts} partes fallaron)`, {
            duration: 8000,
            position: 'bottom-right'
          });
        }
        return;
      }

      // Cálculo de ETA
      const elapsed = (Date.now() - startTime) / 1000;
      const eta = totalProgress > 5 ? (elapsed / (totalProgress / 100)) - elapsed : null;

      const formatTime = (seconds) => {
        if (!isFinite(seconds) || seconds < 0) return 'Calculando...';
        if (seconds < 60) return `~${Math.round(seconds)} seg`;
        return `~${Math.round(seconds / 60)} min`;
      };

      // Actualizar carga con estado actual
      toast.loading(
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="font-semibold">Procesando {tipo}...</span>
          </div>
          <div className="text-sm text-gray-600">
            Parte {Math.min(completedCount + 1, totalParts)}/{totalParts} ({Math.round(totalProgress)}%)
          </div>
          <div className="w-full bg-gray-200 rounded-full h-1.5">
            <div
              className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${totalProgress}%` }}
            ></div>
          </div>
          {eta && (
            <div className="text-[10px] text-gray-500 text-right">
              Tiempo restante: {formatTime(eta)}
            </div>
          )}
        </div>,
        { id: toastId }
      );
    };

    const cleanup = () => {
      clearInterval(pollInterval);
      toast.dismiss(toastId);
      socket.off(progressEvent, onProgress);
      socket.off(completionEvent, onCompletedSocket);
      socket.off('nomina_error', onErrorSocket);
      socket.off('seguro_error', onErrorSocket);
    };

    // Polling del progreso cada 4 segundos (fallback robusto)
    const pollInterval = setInterval(async () => {
      try {
        const responses = await Promise.all(
          taskIds.map(async (id) => {
            if (currentTaskStates[id].state === 'SUCCESS' || currentTaskStates[id].state === 'FAILURE') {
              return { id, data: currentTaskStates[id] };
            }
            try {
              const r = await fetch(`/api/task-status/${id}`, { credentials: 'include' });
              if (!r.ok) return { id, data: currentTaskStates[id] };
              const data = await r.json();
              return { id, data };
            } catch (e) {
              return { id, data: currentTaskStates[id] };
            }
          })
        );

        responses.forEach(({ id, data }) => {
          const existing = currentTaskStates[id];
          if (data.state === 'SUCCESS' && existing.state !== 'SUCCESS') {
            currentTaskStates[id] = { ...data, percent: 100 };
            const res = data.result || data;
            if (!totalResults.processed_tasks.has(id)) {
              totalResults.processed_tasks.add(id);
              totalResults.total_empresas += res.total_empresas || res.empresas_procesadas || 0;
              totalResults.total_trabajadores += res.total_trabajadores || 0;
              totalResults.empresas_clasificadas += res.empresas_clasificadas || 0;
              totalResults.rlc_procesados += res.rlc_procesados || 0;
              totalResults.rnt_procesados += res.rnt_procesados || 0;
              if (res.detalles) totalResults.detalles = [...totalResults.detalles, ...res.detalles];
              if (!totalResults.periodo) totalResults.periodo = res.periodo;
            }
          } else if (data.state === 'PROGRESS') {
            const newPercent = data.percentage || data.percent || 0;
            if (newPercent > existing.percent) {
              currentTaskStates[id] = { ...data, percent: newPercent };
            }
          } else if (data.state === 'FAILURE') {
            currentTaskStates[id] = data;
          }
        });

        updateAggregatedUI();
      } catch (error) {
        console.error('❌ Error en polling múltiple:', error);
      }
    }, 4000);

    // Timeout de seguridad: 1 h
    setTimeout(cleanup, 3600000);
  };

  return { startMonitoring, startMonitoringMultiple };
};
