// frontend/src/components/ImportadorView.jsx
import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';
import {
  Upload, FileText, CheckCircle, XCircle, AlertCircle, Loader2,
  ChevronLeft, Trash2, Building2, Users, FileSignature, FileDown, X, Play, FileIcon, CheckCircle2
} from 'lucide-react';
import ModalEnvioCorreo from './ModalEnvioCorreo';
import ModalConfirmarDocumento from './ModalConfirmarDocumento';
import { useProcessingMonitor } from '../hooks/useProcessingMonitor';


export default function ImportadorView() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { startMonitoring, startMonitoringMultiple } = useProcessingMonitor();

  // Tab state
  const [activeTab, setActiveTab] = useState('individual'); // 'individual' | 'seguros' | 'nominas' | 'impuestos'

  // Individual documents state
  const [archivos, setArchivos] = useState([]);
  const [procesando, setProcesando] = useState(false);
  const [modalDoc, setModalDoc] = useState({
    isOpen: false,
    fileObj: null,
    detectedType: null,
    empresa: null,
    retryCallback: null
  });

  // Nuevo estado para Modo Empresa Única (independiente por pestaña)
  const [modoEmpresaUnicaSS, setModoEmpresaUnicaSS] = useState(false);
  const [modoEmpresaUnicaNominas, setModoEmpresaUnicaNominas] = useState(false);



  // Seguros Sociales state
  const [archivoRLC, setArchivoRLC] = useState(null);
  const [archivoRNT, setArchivoRNT] = useState(null);
  const [procesandoSS, setProcesandoSS] = useState(false);
  const [resultadosSS, setResultadosSS] = useState(null);

  // Nóminas state
  const [archivoNominas, setArchivoNominas] = useState(null);
  const [procesandoNominas, setProcesandoNominas] = useState(false);
  const [resultadosNominas, setResultadosNominas] = useState(null);
  const [periodoDetectadoNominas, setPeriodoDetectadoNominas] = useState(null);
  const [periodoTextoNominas, setPeriodoTextoNominas] = useState(null);
  const [periodoDetectadoRLC, setPeriodoDetectadoRLC] = useState(null);
  const [periodoTextoRLC, setPeriodoTextoRLC] = useState(null);
  const [periodoDetectadoRNT, setPeriodoDetectadoRNT] = useState(null);
  const [periodoTextoRNT, setPeriodoTextoRNT] = useState(null);



  // Periodo Seguros Sociales
  const [modoSS, setModoSS] = useState('automatico'); // 'automatico' | 'manual'
  const [mesSS, setMesSS] = useState(new Date().getMonth() + 1); // 1-12
  const [añoSS, setAñoSS] = useState(new Date().getFullYear());

  // Periodo Nóminas
  const [modoNominas, setModoNominas] = useState('automatico'); // 'automatico' | 'manual'
  const [mesNominas, setMesNominas] = useState(new Date().getMonth() + 1); // 1-12
  const [añoNominas, setAñoNominas] = useState(new Date().getFullYear());

  // Modal envío correo
  const [mostrarModalEnvio, setMostrarModalEnvio] = useState(false);
  const [nominasParaEnviar, setNominasParaEnviar] = useState([]);
  const [rntDisponible, setRntDisponible] = useState(null);

  // Impuestos state
  const [archivosImpuestos, setArchivosImpuestos] = useState([]);
  const [procesandoImpuestos, setProcesandoImpuestos] = useState(false);
  const [resultadosImpuestos, setResultadosImpuestos] = useState(null);

  // Certificados 190 state
  const [archivos190, setArchivos190] = useState([]);
  const [procesando190, setProcesando190] = useState(false);
  const [resultados190, setResultados190] = useState(null);
  const [periodo190, setPeriodo190] = useState(new Date().getFullYear().toString());

  // Certificados 180 state
  const [archivos180, setArchivos180] = useState([]);
  const [procesando180, setProcesando180] = useState(false);
  const [resultados180, setResultados180] = useState(null);
  const [periodo180, setPeriodo180] = useState(new Date().getFullYear().toString());

  // Altas state
  const [archivosAlta, setArchivosAlta] = useState([]);
  const [procesandoAlta, setProcesandoAlta] = useState(false);
  const [resultadosAlta, setResultadosAlta] = useState(null);

  // Contratos state
  const [archivosContrato, setArchivosContrato] = useState([]);
  const [procesandoContrato, setProcesandoContrato] = useState(false);
  const [resultadosContrato, setResultadosContrato] = useState(null);

  // Individual documents dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (acceptedFiles) => {
      // ⚠️ LÍMITE DE 100 ARCHIVOS
      const totalActual = archivos.length;
      const disponibles = 100 - totalActual;

      if (disponibles <= 0) {
        toast.error('Límite máximo de 100 archivos alcanzado.', { icon: '🚫' });
        return;
      }

      const filesToAdd = acceptedFiles.slice(0, disponibles);

      const nuevosArchivos = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36),
        estado: 'pendiente',
        mensaje: '',
        nif: null
      }));

      setArchivos(prev => [...prev, ...nuevosArchivos]);

      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, {
          duration: 5000,
          icon: '⚠️'
        });
      } else if (filesToAdd.length === 1) {
        toast.success(`Archivo agregado: ${filesToAdd[0].name}`);
      } else {
        toast.success(`${filesToAdd.length} archivos agregados`);
      }
    },
    onDropRejected: (rejectedFiles) => {
      const mensajes = rejectedFiles.map(r => r.file.name).join(', ');
      toast.error(`Archivos rechazados (solo PDF): ${mensajes}`, { duration: 5000 });
    }
  });

  // RLC dropzone
  const { getRootProps: getRootPropsRLC, getInputProps: getInputPropsRLC, isDragActive: isDragActiveRLC } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setArchivoRLC(acceptedFiles[0]);
        toast.success(`RLC cargado: ${acceptedFiles[0].name}`);
        previewRLC(acceptedFiles[0]);
      }
    }
  });

  // RNT dropzone
  const { getRootProps: getRootPropsRNT, getInputProps: getInputPropsRNT, isDragActive: isDragActiveRNT } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setArchivoRNT(acceptedFiles[0]);
        toast.success(`RNT cargado: ${acceptedFiles[0].name}`);
        previewRNT(acceptedFiles[0]);
      }
    }
  });

  // Nóminas dropzone
  const { getRootProps: getRootPropsNominas, getInputProps: getInputPropsNominas, isDragActive: isDragActiveNominas } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: false,
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setArchivoNominas(acceptedFiles[0]);
        toast.success(`Nóminas cargadas: ${acceptedFiles[0].name}`);
        previewNominas(acceptedFiles[0]);
      }
    }
  });

  // Preview de nóminas - detectar periodo
  const previewNominas = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/preview-nominas', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success && response.data.periodo_detectado) {
        const periodo = response.data.periodo_detectado;
        const periodoTexto = response.data.periodo_detectado_texto;

        setPeriodoDetectadoNominas(periodo);
        setPeriodoTextoNominas(periodoTexto);

        // Preseleccionar mes y año
        if (periodo.length === 6) {
          const año = parseInt(periodo.substring(0, 4));
          const mes = parseInt(periodo.substring(4, 6));
          setAñoNominas(año);
          setMesNominas(mes);
        }

        toast.success(`Periodo detectado: ${periodoTexto || periodo}`, {
          duration: 5000
        });
      }
    } catch (err) {
      console.error('Error en preview:', err);
    }
  };

  // Preview de RLC - detectar periodo
  const previewRLC = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/preview-nominas', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success && response.data.periodo_detectado) {
        const periodo = response.data.periodo_detectado;
        const periodoTexto = response.data.periodo_detectado_texto;

        setPeriodoDetectadoRLC(periodo);
        setPeriodoTextoRLC(periodoTexto);

        // Preseleccionar mes y año
        if (periodo.length === 6) {
          const año = parseInt(periodo.substring(0, 4));
          const mes = parseInt(periodo.substring(4, 6));
          setAñoSS(año);
          setMesSS(mes);
        }

        toast.success(`RLC - Periodo detectado: ${periodoTexto || periodo}`, {
          duration: 5000
        });
      }
    } catch (err) {
      console.error('Error en preview RLC:', err);
    }
  };

  // Preview de RNT - detectar periodo
  const previewRNT = async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post('/api/preview-nominas', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success && response.data.periodo_detectado) {
        const periodo = response.data.periodo_detectado;
        const periodoTexto = response.data.periodo_detectado_texto;

        setPeriodoDetectadoRNT(periodo);
        setPeriodoTextoRNT(periodoTexto);

        // Si ya hay periodo detectado del RLC, verificar discrepancia
        if (periodoDetectadoRLC && periodoDetectadoRLC !== periodo) {
          toast.error(`⚠️ DISCREPANCIA: RLC es ${periodoTextoRLC || periodoDetectadoRLC} pero RNT es ${periodoTexto || periodo}`, {
            duration: 10000
          });
        } else {
          // Si coinciden o no hay RLC aún, preseleccionar mes y año
          if (periodo.length === 6) {
            const año = parseInt(periodo.substring(0, 4));
            const mes = parseInt(periodo.substring(4, 6));
            setAñoSS(año);
            setMesSS(mes);
          }

          toast.success(`RNT - Periodo detectado: ${periodoTexto || periodo}`, {
            duration: 5000
          });
        }
      }
    } catch (err) {
      console.error('Error en preview RNT:', err);
    }
  };

  const eliminarArchivo = (id) => {
    const archivo = archivos.find(a => a.id === id);
    setArchivos(prev => prev.filter(a => a.id !== id));
    toast.success(`Eliminado: ${archivo.file.name}`, { duration: 2000 });
  };

  const procesarArchivos = async () => {
    if (archivos.length === 0) return;

    setProcesando(true);
    const toastId = toast.loading(`Subiendo ${archivos.length} archivo${archivos.length > 1 ? 's' : ''}...`);

    // Marcar todos como procesando en la UI
    setArchivos(prev => prev.map(a => ({ ...a, estado: 'procesando' })));

    try {
      const formData = new FormData();
      // Usar keys de array files[] para que el backend use getlist
      archivos.forEach(a => {
        formData.append('files[]', a.file);
      });

      const response = await axios.post('/api/clasificar-y-subir-multiple', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
        // Seguimiento de progreso (opcional pero profesional)
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          if (percentCompleted < 100) {
            toast.loading(`Subiendo: ${percentCompleted}%`, { id: toastId });
          } else {
            toast.loading('Guardando archivos en el servidor...', { id: toastId });
          }
        }
      });

      if (response.data.success) {
        const { detalles, exitosos, errores } = response.data;

        // Actualizar estados individuales basados en la respuesta del server
        setArchivos(prev => prev.map(a => {
          const resIndividual = detalles.find(d => d.filename === a.file.name);
          if (resIndividual) {
            return {
              ...a,
              estado: resIndividual.success ? 'exito' : 'error',
              mensaje: resIndividual.message
            };
          }
          return a;
        }));

        if (errores === 0) {
          toast.success(`¡Subida completada! ${exitosos} archivos procesados.`, { id: toastId, duration: 4000 });

          setTimeout(() => {
            queryClient.invalidateQueries();
            navigate('/empresas', { replace: true });
            window.location.reload();
          }, 2000);
        } else {
          toast.success(`Procesado: ${exitosos} éxitos, ${errores} errores.`, {
            id: toastId,
            duration: 5000,
            icon: '⚠️'
          });
        }
      } else {
        throw new Error(response.data.message || 'Error en la subida masiva');
      }
    } catch (err) {
      console.error('Error en procesarArchivos:', err);
      const msg = err.response?.data?.error || err.message || 'Error desconocido';
      toast.error(`Error: ${msg}`, { id: toastId, duration: 6000 });

      // Marcar todos como error en caso de fallo crítico de la petición
      setArchivos(prev => prev.map(a => ({
        ...a,
        estado: a.estado === 'procesando' ? 'error' : a.estado,
        mensaje: a.estado === 'procesando' ? msg : a.mensaje
      })));
    } finally {
      setProcesando(false);
    }
  };

  const procesarSeguros = async () => {
    if (!archivoRLC || !archivoRNT) {
      toast.error('Debes cargar ambos archivos (RLC y RNT)');
      return;
    }

    setProcesandoSS(true);
    setResultadosSS(null);

    const toastId = toast.loading('Procesando Seguros Sociales...');

    try {
      const formData = new FormData();
      formData.append('rlc', archivoRLC);
      formData.append('rnt', archivoRNT);

      if (modoSS === 'manual') {
        const periodo = `${añoSS}${mesSS.toString().padStart(2, '0')}`;
        formData.append('periodo', periodo);
      }

      // Enviar flag de empresa única
      formData.append('empresa_unica', modoEmpresaUnicaSS);

      const response = await axios.post('/api/procesar-seguros-sociales', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // ✅ NUEVA LÓGICA AQUÍ
      if (response.data.async && response.data.task_id) {
        // Archivo grande → procesamiento asíncrono
        toast.success('Archivos subidos. Procesando en segundo plano...', {
          id: toastId,
          duration: 3000
        });

        // 🎯 INICIAR MONITOREO
        const onFinished = () => setProcesandoSS(false);
        const onSuccess = (data) => setResultadosSS(data);

        if (response.data.is_split && response.data.tasks && response.data.tasks.length > 1) {
          startMonitoringMultiple(response.data.tasks, 'seguros', onFinished, onSuccess);
        } else {
          startMonitoring(response.data.task_id, 'seguros', onFinished, onSuccess);
        }

      } else if (response.data.success) {
        // Archivo pequeño → procesamiento inmediato
        setResultadosSS(response.data);
        toast.success('¡Seguros Sociales procesados correctamente!', {
          id: toastId,
          duration: 4000
        });

        setTimeout(() => {
          queryClient.invalidateQueries();
        }, 300);

        setProcesandoSS(false);
      } else {
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      const mensajeError = err.response?.data?.message || err.message || 'Error al procesar';
      toast.error(`Error: ${mensajeError}`, {
        id: toastId,
        duration: 5000
      });
      setProcesandoSS(false);
    }
  };

  const limpiarTodo = () => {
    const cantidad = archivos.length;
    setArchivos([]);
    toast.success(`${cantidad} archivo${cantidad > 1 ? 's' : ''} eliminado${cantidad > 1 ? 's' : ''}`, {
      duration: 2000
    });
  };

  const limpiarSeguros = () => {
    setArchivoRLC(null);
    setArchivoRNT(null);
    setResultadosSS(null);
    toast.success('Archivos de Seguros Sociales eliminados', { duration: 2000 });
  };

  const procesarNominas = async () => {
    if (!archivoNominas) {
      toast.error('Debes cargar el archivo consolidado de nóminas');
      return;
    }

    setProcesandoNominas(true);
    setResultadosNominas(null);

    const toastId = toast.loading('Procesando Nóminas...');

    try {
      const formData = new FormData();
      formData.append('file', archivoNominas);

      if (modoNominas === 'manual') {
        const periodo = `${añoNominas}${mesNominas.toString().padStart(2, '0')}`;
        formData.append('periodo', periodo);
      }

      // Enviar flag de empresa única
      formData.append('empresa_unica', modoEmpresaUnicaNominas);

      const response = await axios.post('/api/procesar-nominas', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // ✅ NUEVA LÓGICA AQUÍ
      if (response.data.async && response.data.task_id) {
        // Archivo grande → procesamiento asíncrono
        toast.success('Archivo subido. Procesando en segundo plano...', {
          id: toastId,
          duration: 3000
        });

        // 🎯 INICIAR MONITOREO con callback para resetear estado al terminar
        const onFinished = () => setProcesandoNominas(false);
        const onSuccess = (data) => setResultadosNominas(data);

        if (response.data.is_split && response.data.tasks && response.data.tasks.length > 1) {
          startMonitoringMultiple(response.data.tasks, 'nominas', onFinished, onSuccess);
        } else {
          startMonitoring(response.data.task_id, 'nominas', onFinished, onSuccess);
        }

      } else if (response.data.success) {
        // Archivo pequeño → procesamiento inmediato
        setResultadosNominas(response.data);
        toast.success('¡Nóminas procesadas correctamente!', {
          id: toastId,
          duration: 4000
        });

        // Preparar modal de correo (código existente)
        // Solo abrir si NO estamos en modo empresa única (para evitar molestar en subidas rápidas)
        if (!modoEmpresaUnicaNominas && response.data.detalles && response.data.detalles.length > 0) {
          const nominas = response.data.detalles
            .filter(d => d.documento_id)
            .map(d => ({
              id: d.documento_id,
              nombre: d.nombre_trabajador || 'N/A',
              periodo: response.data.periodo || 'N/A'
            }));

          setNominasParaEnviar(nominas);
          setRntDisponible(response.data.rnt_disponible || null);
          setMostrarModalEnvio(true);
        }

        setTimeout(() => {
          queryClient.invalidateQueries();
        }, 300);

        setProcesandoNominas(false);
      } else {
        // Si hay detalles (errores capturados), mostrarlos
        if (response.data.detalles) {
          setResultadosNominas(response.data);
        }
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        setModalDoc({
          isOpen: true,
          fileObj: { file: archivoNominas, id: 'nomina' },
          detectedType: err.response.data.detectado,
          empresa: err.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             limpiarNominas();
          }
        });
        return;
      }
      
      const mensajeError = err.response?.data?.message || err.message || 'Error al procesar';
      toast.error(`Error: ${mensajeError}`, {
        id: toastId,
        duration: 5000
      });
      setProcesandoNominas(false);
    }
  };

  const limpiarNominas = () => {
    setArchivoNominas(null);
    setResultadosNominas(null);
    toast.success('Archivo de Nóminas eliminado', { duration: 2000 });
  };

  // Impuestos dropzone
  const { getRootProps: getRootPropsImpuestos, getInputProps: getInputPropsImpuestos, isDragActive: isDragActiveImpuestos } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (acceptedFiles) => {
      // Límite de 100 archivos
      const totalActual = archivosImpuestos.length;
      const disponibles = 100 - totalActual;

      if (disponibles <= 0) {
        toast.error('Límite máximo de 100 archivos alcanzado.', { icon: '🚫' });
        return;
      }

      const filesToAdd = acceptedFiles.slice(0, disponibles);

      const nuevos = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36),
        estado: 'pendiente'
      }));

      setArchivosImpuestos(prev => [...prev, ...nuevos]);

      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, {
          duration: 5000,
          icon: '⚠️'
        });
      } else if (filesToAdd.length === 1) {
        toast.success(`Archivo de impuesto agregado: ${filesToAdd[0].name}`);
      } else {
        toast.success(`${filesToAdd.length} archivos de impuestos agregados`);
      }
    }
  });

  const procesarImpuestos = async () => {
    if (archivosImpuestos.length === 0) {
      toast.error('Debes cargar al menos un archivo de impuesto');
      return;
    }

    setProcesandoImpuestos(true);
    setResultadosImpuestos(null);

    const toastId = toast.loading(`Procesando ${archivosImpuestos.length} archivo(s) de impuestos...`);

    try {
      const formData = new FormData();
      archivosImpuestos.forEach(a => {
        formData.append('files[]', a.file);
      });

      const response = await axios.post('/api/procesar-impuestos', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        setResultadosImpuestos(response.data);

        const { exitosos, errores } = response.data;
        if (errores === 0) {
          toast.success(`¡Procesados correctamente! ${exitosos} archivo(s)`, {
            id: toastId,
            duration: 4000
          });
        } else {
          toast.success(`Procesados: ${exitosos} éxitos, ${errores} errores`, {
            id: toastId,
            duration: 5000,
            icon: '⚠️'
          });
        }

        setTimeout(() => {
          queryClient.invalidateQueries();
        }, 300);
      } else {
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivosImpuestos.find(a => a.file.name === err.response.data.filename) || archivosImpuestos[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: err.response.data.detectado,
          empresa: err.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivosImpuestos(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      const mensajeError = err.response?.data?.message || err.message || 'Error al procesar';
      toast.error(`Error: ${mensajeError}`, {
        id: toastId,
        duration: 5000
      });
    } finally {
      setProcesandoImpuestos(false);
    }
  };

  const limpiarImpuestos = () => {
    const cantidad = archivosImpuestos.length;
    setArchivosImpuestos([]);
    setResultadosImpuestos(null);
    toast.success(`${cantidad} archivo${cantidad > 1 ? 's' : ''} de impuestos eliminado${cantidad > 1 ? 's' : ''}`, {
      duration: 2000
    });
  };

  // Certificados 190 dropzone
  const { getRootProps: getRootProps190, getInputProps: getInputProps190, isDragActive: isDragActive190 } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (acceptedFiles) => {
      const totalActual = archivos190.length;
      const disponibles = 100 - totalActual;

      if (disponibles <= 0) {
        toast.error('Límite máximo de 100 archivos alcanzado.', { icon: '🚫' });
        return;
      }

      const filesToAdd = acceptedFiles.slice(0, disponibles);
      const nuevos = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36),
        estado: 'pendiente'
      }));

      setArchivos190(prev => [...prev, ...nuevos]);

      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, {
          duration: 5000,
          icon: '⚠️'
        });
      } else {
        toast.success(`${filesToAdd.length} archivos de Certificados 190 agregados`);
      }
    }
  });

  const procesar190 = async () => {
    if (archivos190.length === 0) return;
    setProcesando190(true);
    setResultados190(null);
    const toastId = toast.loading(`Procesando certificados 190...`);
    try {
      const formData = new FormData();
      archivos190.forEach(a => formData.append('files', a.file));
      formData.append('periodo', periodo190);

      const response = await axios.post('/api/procesar-modelo-190', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (response.data.success) {
        setResultados190(response.data);
        toast.success(response.data.message, { id: toastId, duration: 4000 });
        setTimeout(() => queryClient.invalidateQueries(), 1000);
      } else {
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivos190.find(a => a.file.name === err.response.data.filename) || archivos190[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: err.response.data.detectado,
          empresa: err.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivos190(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      const msg = err.response?.data?.message || err.message || 'Error desconocido';
      toast.error(`Error: ${msg}`, { id: toastId, duration: 5000 });
    } finally {
      setProcesando190(false);
    }
  };

  const limpiar190 = () => {
    setArchivos190([]);
    setResultados190(null);
    toast.success('Archivos de Modelo 190 eliminados');
  };

  // Certificados 180 dropzone
  const { getRootProps: getRootProps180, getInputProps: getInputProps180, isDragActive: isDragActive180 } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (acceptedFiles) => {
      const totalActual = archivos180.length;
      const disponibles = 100 - totalActual;
      if (disponibles <= 0) {
        toast.error('Límite máximo de 100 archivos alcanzado.', { icon: '🚫' });
        return;
      }
      const filesToAdd = acceptedFiles.slice(0, disponibles);
      const nuevos = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36),
        estado: 'pendiente'
      }));
      setArchivos180(prev => [...prev, ...nuevos]);
      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, { duration: 5000, icon: '⚠️' });
      } else {
        toast.success(`${filesToAdd.length} archivos de Certificados 180 agregados`);
      }
    }
  });

  const procesar180 = async () => {
    if (archivos180.length === 0) return;
    setProcesando180(true);
    setResultados180(null);
    const toastId = toast.loading(`Procesando certificados 180...`);
    try {
      const formData = new FormData();
      archivos180.forEach(a => formData.append('files', a.file));
      formData.append('periodo', periodo180);

      const response = await axios.post('/api/procesar-modelo-180', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (response.data.success) {
        setResultados180(response.data);
        toast.success(response.data.message, { id: toastId, duration: 4000 });
        setTimeout(() => queryClient.invalidateQueries(), 1000);
      } else {
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivos180.find(a => a.file.name === err.response.data.filename) || archivos180[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: err.response.data.detectado,
          empresa: err.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivos180(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      const msg = err.response?.data?.message || err.message || 'Error desconocido';
      toast.error(`Error: ${msg}`, { id: toastId, duration: 5000 });
    } finally {
      setProcesando180(false);
    }
  };

  const limpiar180 = () => {
    setArchivos180([]);
    setResultados180(null);
    toast.success('Archivos de Modelo 180 eliminados');
  };

  // Altas dropzone
  const { getRootProps: getRootPropsAlta, getInputProps: getInputPropsAlta, isDragActive: isDragActiveAlta } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
    onDrop: (acceptedFiles) => {
      const totalActual = archivosAlta.length;
      const disponibles = 100 - totalActual;
      if (disponibles <= 0) {
        toast.error('Límite máximo de 100 archivos alcanzado.', { icon: '🚫' });
        return;
      }
      const filesToAdd = acceptedFiles.slice(0, disponibles);
      const nuevos = filesToAdd.map(file => ({
        file,
        id: Math.random().toString(36),
        estado: 'pendiente'
      }));
      setArchivosAlta(prev => [...prev, ...nuevos]);
      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, { duration: 5000, icon: '⚠️' });
      } else {
        toast.success(`${filesToAdd.length} archivos de Altas/Bajas agregados`);
      }
    }
  });

  const procesarAlta = async () => {
    if (archivosAlta.length === 0) return;
    setProcesandoAlta(true);
    setResultadosAlta(null);
    const toastId = toast.loading(`Procesando altas/bajas de trabajadores...`);
    try {
      const formData = new FormData();
      archivosAlta.forEach(a => formData.append('files', a.file));

      const response = await axios.post('/api/procesar-alta', formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (response.data.success) {
        setResultadosAlta(response.data);
        toast.success(response.data.message, { id: toastId, duration: 4000 });
        setTimeout(() => queryClient.invalidateQueries(), 1000);
      } else {
        throw new Error(response.data.message || 'Error al procesar');
      }
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivosAlta.find(a => a.file.name === err.response.data.filename) || archivosAlta[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: err.response.data.detectado,
          empresa: err.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivosAlta(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      const msg = err.response?.data?.message || err.message || 'Error desconocido';
      toast.error(`Error: ${msg}`, { id: toastId, duration: 5000 });
    } finally {
      setProcesandoAlta(false);
    }
  };

  const limpiarAlta = () => {
    setArchivosAlta([]);
    setResultadosAlta(null);
    toast.success('Archivos de Altas/Bajas eliminados');
  };

  const [archivosFiniquito, setArchivosFiniquito] = useState([]);
  const [procesandoFiniquito, setProcesandoFiniquito] = useState(false);
  const [resultadosFiniquito, setResultadosFiniquito] = useState(null);

  const onDropFiniquito = useCallback((acceptedFiles) => {
    const totalActual = archivosFiniquito.length;
    const disponibles = 100 - totalActual;
    const filesToAdd = acceptedFiles.slice(0, disponibles).map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      nombre: file.name,
      estado: 'esperando'
    }));

    if (filesToAdd.length > 0) {
      setArchivosFiniquito(prev => [...prev, ...filesToAdd]);
      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, { duration: 5000, icon: '⚠️' });
      } else {
        toast.success(`${filesToAdd.length} archivos de Finiquitos agregados`);
      }
    }
  }, [archivosFiniquito]);

  const { getRootProps: getRootPropsFiniquito, getInputProps: getInputPropsFiniquito, isDragActive: isDragActiveFiniquito } = useDropzone({
    onDrop: onDropFiniquito,
    accept: { 'application/pdf': ['.pdf'] }
  });

  const procesarFiniquitos = async () => {
    if (archivosFiniquito.length === 0) return;
    setProcesandoFiniquito(true);
    setResultadosFiniquito(null);
    const toastId = toast.loading(`Procesando finiquitos...`);
    try {
      const formData = new FormData();
      archivosFiniquito.forEach(a => formData.append('files', a.file));
      const { data } = await axios.post('/api/finiquitos/upload', formData);
      if (data.success) {
        toast.success(data.message || 'Finiquitos procesados', { id: toastId });
        setResultadosFiniquito(data.results);
      } else {
        toast.error(data.message || 'Error al procesar', { id: toastId });
      }
    } catch (error) {
      if (error.response?.status === 400 && error.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivosFiniquito.find(a => a.file.name === error.response.data.filename) || archivosFiniquito[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: error.response.data.detectado,
          empresa: error.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivosFiniquito(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      console.error(error);
      toast.error('Error de conexión con el servidor', { id: toastId });
    } finally {
      setProcesandoFiniquito(false);
    }
  };

  const limpiarFiniquito = () => {
    setArchivosFiniquito([]);
    setResultadosFiniquito(null);
    toast.success('Archivos de Finiquitos eliminados');
  };

  // --------------------------------------------------------------------------
  // LÓGICA CONTRATOS
  // --------------------------------------------------------------------------
  const onDropContrato = useCallback((acceptedFiles) => {
    const totalActual = archivosContrato.length;
    const disponibles = 100 - totalActual;
    const filesToAdd = acceptedFiles.slice(0, disponibles).map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      nombre: file.name,
      estado: 'esperando'
    }));

    if (filesToAdd.length > 0) {
      setArchivosContrato(prev => [...prev, ...filesToAdd]);
      if (acceptedFiles.length > disponibles) {
        toast.error(`Solo se agregaron ${disponibles} archivos. Límite máximo: 100.`, { duration: 5000, icon: '⚠️' });
      } else {
        toast.success(`${filesToAdd.length} archivos de Contratos agregados`);
      }
    }
  }, [archivosContrato]);

  const { getRootProps: getRootPropsContrato, getInputProps: getInputPropsContrato, isDragActive: isDragActiveContrato } = useDropzone({
    onDrop: onDropContrato,
    accept: { 'application/pdf': ['.pdf'] }
  });

  const procesarContratos = async () => {
    if (archivosContrato.length === 0) return;
    setProcesandoContrato(true);
    setResultadosContrato(null);
    const toastId = toast.loading(`Procesando contratos...`);
    try {
      const formData = new FormData();
      archivosContrato.forEach(a => formData.append('files', a.file));
      const { data } = await axios.post('/api/contratos/upload', formData);
      if (data.success) {
        toast.success(data.message || 'Contratos procesados', { id: toastId });
        setResultadosContrato(data.results);
      } else {
        toast.error(data.message || 'Error al procesar', { id: toastId });
      }
    } catch (error) {
      if (error.response?.status === 400 && error.response?.data?.estado === 'confirmacion') {
        toast.dismiss(toastId);
        const conflictFile = archivosContrato.find(a => a.file.name === error.response.data.filename) || archivosContrato[0];
        setModalDoc({
          isOpen: true,
          fileObj: { file: conflictFile.file, id: conflictFile.id },
          detectedType: error.response.data.detectado,
          empresa: error.response.data.empresa_detectada,
          retryCallback: (id, newCategory) => {
             setArchivosContrato(prev => prev.filter(a => a.id !== id));
          }
        });
        return;
      }
      console.error(error);
      toast.error('Error de conexión con el servidor', { id: toastId });
    } finally {
      setProcesandoContrato(false);
    }
  };

  const limpiarContrato = () => {
    setArchivosContrato([]);
    setResultadosContrato(null);
    toast.success('Archivos de Contratos eliminados');
  };

  const getIconoEstado = (estado) => {
    if (estado === 'exito') return <CheckCircle className="w-5 h-5 text-green-600" />;
    if (estado === 'error') return <XCircle className="w-5 h-5 text-red-600" />;
    if (estado === 'procesando') return <Loader2 className="w-5 h-5 text-primary animate-spin" />;
    return <FileText className="w-5 h-5 text-gray-400" />;
  };

  const estadisticas = {
    total: archivos.length,
    exito: archivos.filter(a => a.estado === 'exito').length,
    error: archivos.filter(a => a.estado === 'error').length,
    pendiente: archivos.filter(a => a.estado === 'pendiente').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/empresas')}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft className="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Importar Documentos</h1>
            <p className="text-gray-600 mt-1">Arrastra archivos PDF o haz clic para seleccionar</p>
          </div>
        </div>

        {activeTab === 'individual' && archivos.length > 0 && (
          <button
            onClick={limpiarTodo}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar Todo
          </button>
        )}

        {activeTab === 'seguros' && (archivoRLC || archivoRNT) && (
          <button
            onClick={limpiarSeguros}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}

        {activeTab === 'nominas' && archivoNominas && (
          <button
            onClick={limpiarNominas}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}

        {activeTab === 'impuestos' && archivosImpuestos.length > 0 && (
          <button
            onClick={limpiarImpuestos}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}

        {activeTab === 'certificados180' && archivos180.length > 0 && (
          <button
            onClick={limpiar180}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}

        {activeTab === 'certificados190' && archivos190.length > 0 && (
          <button
            onClick={limpiar190}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}

        {activeTab === 'altas' && archivosAlta.length > 0 && (
          <button
            onClick={limpiarAlta}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" /> Limpiar
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('individual')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'individual'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Documentos Individuales
            </div>
          </button>
          <button
            onClick={() => setActiveTab('seguros')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'seguros'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5" />
              Seguros Sociales
            </div>
          </button>
          <button
            onClick={() => setActiveTab('nominas')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'nominas'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Nóminas
            </div>
          </button>
          <button
            onClick={() => setActiveTab('impuestos')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'impuestos'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Impuestos
            </div>
          </button>
          <button
            onClick={() => setActiveTab('certificados180')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'certificados180'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileSignature className="w-5 h-5" />
              Certificados 180
            </div>
          </button>
          <button
            onClick={() => setActiveTab('certificados190')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'certificados190'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileSignature className="w-5 h-5" />
              Certificados 190
            </div>
          </button>
          <button
            onClick={() => setActiveTab('altas')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'altas'
              ? 'border-primary text-primary'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              Altas / Bajas
            </div>
          </button>

          <button
            onClick={() => setActiveTab('finiquitos')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${activeTab === 'finiquitos'
              ? 'border-red-500 text-red-600 bg-red-50/50'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileDown className="w-5 h-5" />
              <span>Finiquitos</span>
            </div>
          </button>

          <button
            onClick={() => setActiveTab('contratos')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${activeTab === 'contratos'
              ? 'border-orange-500 text-orange-600 bg-orange-50/50'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            <div className="flex items-center gap-2">
              <FileSignature className="w-5 h-5" />
              <span>Contratos</span>
            </div>
          </button>

        </nav>
      </div>

      {/* Tab Content: Individual */}
      {activeTab === 'individual' && (
        <>
          {/* Estadísticas */}
          {archivos.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600">Total</p>
                <p className="text-2xl font-bold text-gray-900">{estadisticas.total}</p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600">Pendientes</p>
                <p className="text-2xl font-bold text-blue-600">{estadisticas.pendiente}</p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600">Exitosos</p>
                <p className="text-2xl font-bold text-green-600">{estadisticas.exito}</p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600">Errores</p>
                <p className="text-2xl font-bold text-red-600">{estadisticas.error}</p>
              </div>
            </div>
          )}

          {/* Área de drop */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActive
              ? 'border-primary bg-primary-light'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
              }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full transition-colors ${isDragActive ? 'bg-primary-light' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 transition-colors ${isDragActive ? 'text-primary' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActive ? '¡Suelta los archivos aquí!' : 'Arrastra archivos PDF aquí'}
                </p>
                <p className="text-sm text-gray-600 mt-1">o haz clic para seleccionar</p>
              </div>
            </div>
          </div>

          {/* Lista de archivos */}
          {archivos.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos ({archivos.length})</h2>

                {estadisticas.pendiente > 0 && !procesando && (
                  <button
                    onClick={procesarArchivos}
                    className="px-6 py-3 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg"
                  >
                    Procesar Archivos
                  </button>
                )}
              </div>

              <div className="space-y-3">
                {archivos.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-4">
                      <div className="shrink-0">{getIconoEstado(archivo.estado)}</div>

                      <div className="flex-1 min-w-0">
                        <h4 className="text-base font-semibold text-gray-900 truncate">{archivo.file.name}</h4>
                        <div className="flex items-center gap-4 mt-1 text-sm">
                          <span className="text-gray-500">{(archivo.file.size / 1024).toFixed(2)} KB</span>
                          {archivo.mensaje && (
                            <span
                              className={`font-medium ${archivo.estado === 'exito'
                                ? 'text-green-600'
                                : archivo.estado === 'error'
                                  ? 'text-red-600'
                                  : 'text-primary'
                                }`}
                            >
                              {archivo.mensaje}
                            </span>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => eliminarArchivo(archivo.id)}
                        className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                        disabled={archivo.estado === 'procesando'}
                      >
                        <Trash2 className="w-5 h-5 text-red-600" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Tab Content: Seguros Sociales */}
      {activeTab === 'seguros' && (
        <div className="space-y-6">
          {/* Instrucciones */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Procesamiento de Seguros Sociales</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Sube los archivos RLC y RNT del mismo período. El sistema los procesará automáticamente y distribuirá los documentos a las carpetas de cada empresa.
                </p>
              </div>
            </div>
          </div>

          {/* Selector de Periodo */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Periodo de los Documentos</h3>

            {/* Modo: Automático / Manual */}
            <div className="flex gap-4 mb-4">
              <button
                onClick={() => setModoSS('automatico')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${modoSS === 'automatico'
                  ? 'bg-primary-light0 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                🤖 Automático
              </button>
              <button
                onClick={() => setModoSS('manual')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${modoSS === 'manual'
                  ? 'bg-primary-light0 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                ✋ Manual
              </button>
            </div>

            {/* Selectores de Mes y Año (solo si es manual) */}
            {modoSS === 'manual' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Mes</label>
                  <select
                    value={mesSS}
                    onChange={(e) => setMesSS(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value={1}>Enero</option>
                    <option value={2}>Febrero</option>
                    <option value={3}>Marzo</option>
                    <option value={4}>Abril</option>
                    <option value={5}>Mayo</option>
                    <option value={6}>Junio</option>
                    <option value={7}>Julio</option>
                    <option value={8}>Agosto</option>
                    <option value={9}>Septiembre</option>
                    <option value={10}>Octubre</option>
                    <option value={11}>Noviembre</option>
                    <option value={12}>Diciembre</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Año</label>
                  <select
                    value={añoSS}
                    onChange={(e) => setAñoSS(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    {[...Array(5)].map((_, i) => {
                      const year = new Date().getFullYear() - i;
                      return <option key={year} value={year}>{year}</option>;
                    })}
                  </select>
                </div>
              </div>
            )}

            {/* Checkbox Modo Empresa Única */}
            <div className="flex items-center gap-2 mt-3 p-2 bg-blue-50 rounded-lg border border-blue-200">
              <input
                type="checkbox"
                id="empresaUnicaSS"
                checked={modoEmpresaUnicaSS}
                onChange={(e) => setModoEmpresaUnicaSS(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500 cursor-pointer"
              />
              <label htmlFor="empresaUnicaSS" className="text-sm font-medium text-blue-900 cursor-pointer">
                Modo Empresa Única
              </label>
              <div className="group relative">
                <AlertCircle className="w-4 h-4 text-purple-400 cursor-help" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  Si se activa, NO se separarán las nóminas. Todo el archivo irá a la empresa detectada en la primera página.
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-500 mt-3">
              {(periodoDetectadoRLC || periodoDetectadoRNT) ? (
                <span className="text-green-700 font-medium">
                  {periodoDetectadoRLC && `✓ RLC: ${periodoTextoRLC || periodoDetectadoRLC}`}
                  {periodoDetectadoRLC && periodoDetectadoRNT && ' | '}
                  {periodoDetectadoRNT && `RNT: ${periodoTextoRNT || periodoDetectadoRNT}`}
                </span>
              ) : modoSS === 'automatico' ? (
                '💡 El periodo se detectará automáticamente del nombre del archivo (ej: RLC_202412.pdf)'
              ) : (
                `💡 Periodo seleccionado: ${añoSS}${mesSS.toString().padStart(2, '0')}`
              )}
            </p>
          </div>

          {/* Dropzones RLC y RNT */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* RLC */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Archivo RLC <span className="text-red-500">*</span>
              </label>
              <div
                {...getRootPropsRLC()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${archivoRLC
                  ? 'border-green-500 bg-green-50'
                  : isDragActiveRLC
                    ? 'border-primary bg-primary-light'
                    : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
                  }`}
              >
                <input {...getInputPropsRLC()} />
                <div className="flex flex-col items-center gap-3">
                  {archivoRLC ? (
                    <>
                      <CheckCircle className="w-10 h-10 text-green-600" />
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{archivoRLC.name}</p>
                        <p className="text-xs text-gray-500 mt-1">{(archivoRLC.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-gray-400" />
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">RLC_YYYYMM.pdf</p>
                        <p className="text-xs text-gray-500 mt-1">Click o arrastra</p>
                      </div>
                    </>
                  )}
                </div>
              </div>
              {periodoDetectadoRLC && archivoRLC && (
                <p className="text-xs text-green-700 font-medium mt-2">
                  ✓ Periodo detectado: {periodoTextoRLC || periodoDetectadoRLC}
                </p>
              )}
            </div>

            {/* RNT */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Archivo RNT <span className="text-red-500">*</span>
              </label>
              <div
                {...getRootPropsRNT()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${archivoRNT
                  ? 'border-green-500 bg-green-50'
                  : isDragActiveRNT
                    ? 'border-primary bg-primary-light'
                    : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
                  }`}
              >
                <input {...getInputPropsRNT()} />
                <div className="flex flex-col items-center gap-3">
                  {archivoRNT ? (
                    <>
                      <CheckCircle className="w-10 h-10 text-green-600" />
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">{archivoRNT.name}</p>
                        <p className="text-xs text-gray-500 mt-1">{(archivoRNT.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <Upload className="w-10 h-10 text-gray-400" />
                      <div>
                        <p className="font-semibold text-gray-900 text-sm">RNT_YYYYMM.pdf</p>
                        <p className="text-xs text-gray-500 mt-1">Click o arrastra</p>
                      </div>
                    </>
                  )}
                </div>
              </div>
              {periodoDetectadoRNT && archivoRNT && (
                <p className="text-xs text-green-700 font-medium mt-2">
                  ✓ Periodo detectado: {periodoTextoRNT || periodoDetectadoRNT}
                </p>
              )}
            </div>
          </div>

          {/* Botón Procesar */}
          <div className="flex justify-center">
            <button
              onClick={procesarSeguros}
              disabled={!archivoRLC || !archivoRNT || procesandoSS}
              className="px-8 py-4 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3"
            >
              {procesandoSS ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Building2 className="w-5 h-5" />
                  Procesar Seguros Sociales
                </>
              )}
            </button>
          </div>

          {/* Resultados */}
          {resultadosSS && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
              <h3 className="text-xl font-bold text-gray-900">Resultados del Procesamiento</h3>

              {/* Stats */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600 font-medium">RLC Procesados</p>
                  <p className="text-3xl font-bold text-blue-900">{resultadosSS.rlc_procesados || 0}</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <p className="text-sm text-purple-600 font-medium">RNT Procesados</p>
                  <p className="text-3xl font-bold text-purple-900">{resultadosSS.rnt_procesados || 0}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600 font-medium">Empresas Asociadas</p>
                  <p className="text-3xl font-bold text-green-900">{resultadosSS.empresas_asociadas || 0}</p>
                  <p className="text-xs text-green-600 mt-1">
                    {resultadosSS.total_documentos ?
                      `${((resultadosSS.empresas_asociadas / resultadosSS.total_documentos) * 100).toFixed(1)}%`
                      : '0%'}
                  </p>
                </div>
                <div className="bg-primary-light rounded-lg p-4">
                  <p className="text-sm text-primary font-medium">No Encontradas</p>
                  <p className="text-3xl font-bold text-orange-900">{resultadosSS.empresas_no_encontradas || 0}</p>
                </div>
              </div>

              {/* Empresas no encontradas */}
              {resultadosSS.empresas_no_encontradas_lista && resultadosSS.empresas_no_encontradas_lista.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-primary" />
                    Empresas No Encontradas ({resultadosSS.empresas_no_encontradas_lista.length})
                  </h4>
                  <div className="bg-primary-light rounded-lg p-4 max-h-60 overflow-y-auto">
                    <ul className="space-y-2">
                      {resultadosSS.empresas_no_encontradas_lista.map((empresa, idx) => (
                        <li key={idx} className="text-sm text-orange-900 flex items-start gap-2">
                          <span className="text-primary">•</span>
                          <span>{empresa}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Mensaje de éxito */}
              {resultadosSS.documentos_creados > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex gap-3">
                    <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-green-900">
                        ¡Procesamiento completado!
                      </p>
                      <p className="text-sm text-green-700 mt-1">
                        Se crearon {resultadosSS.documentos_creados} documentos en la base de datos y se distribuyeron a las carpetas de las empresas.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* TABLA DE DETALLES (Seguros) */}
              {resultadosSS.detalles && resultadosSS.detalles.length > 0 && (
                <div className="overflow-hidden border border-gray-200 rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Archivo</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Empresa Detectada</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mensaje</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {resultadosSS.detalles.map((detalle, idx) => (
                        <tr key={idx}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getIconoEstado(detalle.estado)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {detalle.nombre_trabajador}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {detalle.empresa}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {detalle.mensaje || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

            </div>
          )}
        </div>
      )}

      {/* Tab Content: Nóminas */}
      {activeTab === 'nominas' && (
        <div className="space-y-6">
          {/* Instrucciones */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Procesamiento de Nóminas</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Sube el archivo consolidado de nóminas (NOMINAS_YYYYMM.pdf). El sistema lo procesará automáticamente, agrupará por empresa y distribuirá los documentos a las carpetas correspondientes.
                </p>
              </div>
            </div>
          </div>

          {/* Selector de Periodo */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Periodo de las Nóminas</h3>

            {/* Modo: Automático / Manual */}
            <div className="flex gap-4 mb-4">
              <button
                onClick={() => setModoNominas('automatico')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${modoNominas === 'automatico'
                  ? 'bg-primary-light0 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                🤖 Automático
              </button>
              <button
                onClick={() => setModoNominas('manual')}
                className={`flex-1 px-4 py-2 rounded-lg font-medium transition ${modoNominas === 'manual'
                  ? 'bg-primary-light0 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
              >
                ✋ Manual
              </button>
            </div>

            {/* Selectores de Mes y Año (solo si es manual) */}
            {modoNominas === 'manual' && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Mes</label>
                  <select
                    value={mesNominas}
                    onChange={(e) => setMesNominas(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    <option value={1}>Enero</option>
                    <option value={2}>Febrero</option>
                    <option value={3}>Marzo</option>
                    <option value={4}>Abril</option>
                    <option value={5}>Mayo</option>
                    <option value={6}>Junio</option>
                    <option value={7}>Julio</option>
                    <option value={8}>Agosto</option>
                    <option value={9}>Septiembre</option>
                    <option value={10}>Octubre</option>
                    <option value={11}>Noviembre</option>
                    <option value={12}>Diciembre</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Año</label>
                  <select
                    value={añoNominas}
                    onChange={(e) => setAñoNominas(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                  >
                    {[...Array(5)].map((_, i) => {
                      const year = new Date().getFullYear() - i;
                      return <option key={year} value={year}>{year}</option>;
                    })}
                  </select>
                </div>
              </div>
            )}

            {/* Checkbox Modo Empresa Única */}
            <div className="flex items-center gap-2 mt-3 p-2 bg-purple-50 rounded-lg border border-purple-200">
              <input
                type="checkbox"
                id="empresaUnicaNominas"
                checked={modoEmpresaUnicaNominas}
                onChange={(e) => setModoEmpresaUnicaNominas(e.target.checked)}
                className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 cursor-pointer"
              />
              <label htmlFor="empresaUnicaNominas" className="text-sm font-medium text-purple-900 cursor-pointer">
                Modo Empresa Única
              </label>
              <div className="group relative">
                <AlertCircle className="w-4 h-4 text-purple-400 cursor-help" />
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  Si se activa, NO se separarán las nóminas. Todo el archivo irá a la empresa detectada en la primera página.
                </div>
              </div>
            </div>

            <p className="text-xs text-gray-500 mt-3">
              {periodoDetectadoNominas ? (
                <span className="text-green-700 font-medium">
                  ✓ Periodo detectado: {periodoTextoNominas || periodoDetectadoNominas}
                </span>
              ) : modoNominas === 'automatico' ? (
                '💡 El periodo se detectará automáticamente del nombre del archivo (ej: NOMINAS_202412.pdf)'
              ) : (
                `💡 Periodo seleccionado: ${añoNominas}${mesNominas.toString().padStart(2, '0')}`
              )}
            </p>
          </div>

          {/* Dropzone Nóminas */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Archivo Consolidado de Nóminas <span className="text-red-500">*</span>
            </label>
            <div
              {...getRootPropsNominas()}
              className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${archivoNominas
                ? 'border-green-500 bg-green-50'
                : isDragActiveNominas
                  ? 'border-primary bg-primary-light'
                  : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
                }`}
            >
              <input {...getInputPropsNominas()} />
              <div className="flex flex-col items-center gap-4">
                {archivoNominas ? (
                  <>
                    <CheckCircle className="w-16 h-16 text-green-600" />
                    <div>
                      <p className="font-semibold text-gray-900 text-lg">{archivoNominas.name}</p>
                      <p className="text-sm text-gray-500 mt-1">{(archivoNominas.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </>
                ) : (
                  <>
                    <Upload className="w-16 h-16 text-gray-400" />
                    <div>
                      <p className="font-semibold text-gray-900 text-lg">NOMINAS_YYYYMM.pdf</p>
                      <p className="text-sm text-gray-500 mt-1">Click o arrastra el archivo consolidado</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Botón Procesar */}
          <div className="flex justify-center">
            <button
              onClick={procesarNominas}
              disabled={!archivoNominas || procesandoNominas}
              className="px-8 py-4 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-3"
            >
              {procesandoNominas ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Users className="w-5 h-5" />
                  Procesar Nóminas
                </>
              )}
            </button>
          </div>

          {/* Resultados */}
          {resultadosNominas && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
              <h3 className="text-xl font-bold text-gray-900">Resultados del Procesamiento</h3>

              {/* Stats */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600 font-medium">Total Empresas</p>
                  <p className="text-3xl font-bold text-blue-900">{resultadosNominas.total_empresas || 0}</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <p className="text-sm text-purple-600 font-medium">Total Trabajadores</p>
                  <p className="text-3xl font-bold text-purple-900">{resultadosNominas.total_trabajadores || 0}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600 font-medium">Empresas Clasificadas</p>
                  <p className="text-3xl font-bold text-green-900">{resultadosNominas.empresas_clasificadas || 0}</p>
                  <p className="text-xs text-green-600 mt-1">
                    {resultadosNominas.total_empresas ?
                      `${((resultadosNominas.empresas_clasificadas / resultadosNominas.total_empresas) * 100).toFixed(1)}%`
                      : '0%'}
                  </p>
                </div>
                <div className="bg-primary-light rounded-lg p-4">
                  <p className="text-sm text-primary font-medium">No Encontradas</p>
                  <p className="text-3xl font-bold text-orange-900">{resultadosNominas.empresas_no_encontradas || 0}</p>
                </div>
              </div>

              {/* Empresas no encontradas */}
              {resultadosNominas.no_encontradas && resultadosNominas.no_encontradas.length > 0 && (
                <div>
                  <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-primary" />
                    Empresas No Encontradas ({resultadosNominas.no_encontradas.length})
                  </h4>
                  <div className="bg-primary-light rounded-lg p-4 max-h-60 overflow-y-auto">
                    <ul className="space-y-2">
                      {resultadosNominas.no_encontradas.map((empresa, idx) => (
                        <li key={idx} className="text-sm text-orange-900 flex items-start gap-2">
                          <span className="text-primary">•</span>
                          <div>
                            <p className="font-medium">{empresa.razon_social}</p>
                            <p className="text-xs text-primary-hover">NIF: {empresa.nif} • {empresa.num_trabajadores} trabajadores</p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {/* Mensaje de éxito */}
              {resultadosNominas.documentos_creados > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex gap-3">
                    <CheckCircle className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-green-900">
                        ¡Procesamiento completado!
                      </p>
                      <p className="text-sm text-green-700 mt-1">
                        Se procesaron {resultadosNominas.total_trabajadores} nóminas de {resultadosNominas.total_empresas} empresas. Se crearon {resultadosNominas.documentos_creados} documentos en la base de datos y se distribuyeron a las carpetas de las empresas.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* TABLA DE DETALLES */}
              {resultadosNominas.detalles && resultadosNominas.detalles.length > 0 && (
                <div className="overflow-hidden border border-gray-200 rounded-lg">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Archivo / Trabajador</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Empresa</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mensaje</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {resultadosNominas.detalles.map((detalle, idx) => (
                        <tr key={idx}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {getIconoEstado(detalle.estado)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {detalle.nombre_trabajador}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {detalle.empresa}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {detalle.mensaje || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Impuestos */}
      {activeTab === 'impuestos' && (
        <div className="space-y-6">
          {/* Instrucciones */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Procesamiento de Impuestos</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Sube documentos de impuestos (Modelo 303, 111, 130, etc.).
                  El sistema detectará automáticamente el NIF, modelo, estado (NEGATIVA/SIN ACTIVIDAD/RESULTADO CERO) y calidad del declarante (Colaborador/Titular).
                  Los documentos se clasificarán automáticamente en la carpeta de la empresa correspondiente o en Inbox si no se encuentra el NIF.
                </p>
                <p className="text-sm text-blue-700 mt-2 font-medium">
                  Límite: 100 archivos por subida
                </p>
              </div>
            </div>
          </div>

          {/* Dropzone */}
          <div
            {...getRootPropsImpuestos()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActiveImpuestos
              ? 'border-primary bg-primary-light'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
              }`}
          >
            <input {...getInputPropsImpuestos()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActiveImpuestos ? 'bg-primary-light' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActiveImpuestos ? 'text-primary' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActiveImpuestos ? '¡Suelta los archivos aquí!' : 'Arrastra archivos de impuestos aquí'}
                </p>
                <p className="text-sm text-gray-600 mt-1">o haz clic para seleccionar (máx. 100 archivos)</p>
              </div>
            </div>
          </div>

          {/* Lista de archivos */}
          {archivosImpuestos.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">
                  Archivos ({archivosImpuestos.length}/100)
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={limpiarImpuestos}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" /> Limpiar
                  </button>
                  <button
                    onClick={procesarImpuestos}
                    disabled={procesandoImpuestos}
                    className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {procesandoImpuestos ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                        Procesando...
                      </>
                    ) : (
                      'Procesar Impuestos'
                    )}
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {archivosImpuestos.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-4">
                      <FileText className="w-5 h-5 text-gray-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-base font-semibold text-gray-900 truncate">{archivo.file.name}</h4>
                        <p className="text-sm text-gray-500">{(archivo.file.size / 1024).toFixed(2)} KB</p>
                      </div>
                      <button
                        onClick={() => setArchivosImpuestos(prev => prev.filter(a => a.id !== archivo.id))}
                        className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                        disabled={procesandoImpuestos}
                      >
                        <Trash2 className="w-5 h-5 text-red-600" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Resultados */}
          {resultadosImpuestos && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados del Procesamiento</h3>

              {/* Resumen */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600">Total</p>
                  <p className="text-2xl font-bold text-gray-900">{resultadosImpuestos.total}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600">Exitosos</p>
                  <p className="text-2xl font-bold text-green-600">{resultadosImpuestos.exitosos}</p>
                </div>
                <div className="bg-red-50 rounded-lg p-4">
                  <p className="text-sm text-red-600">Errores</p>
                  <p className="text-2xl font-bold text-red-600">{resultadosImpuestos.errores}</p>
                </div>
              </div>

              {/* Detalles */}
              <div className="space-y-2">
                {resultadosImpuestos.detalles.map((detalle, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-lg border ${detalle.success
                      ? 'bg-green-50 border-green-200'
                      : 'bg-red-50 border-red-200'
                      }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {detalle.success ? (
                            <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600 shrink-0" />
                          )}
                          <p className="font-medium text-gray-900">{detalle.filename}</p>
                        </div>

                        {detalle.success && (
                          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm ml-7">
                            <div>
                              <span className="text-gray-600">Empresa:</span>
                              <span className="ml-2 font-medium text-gray-900">{detalle.empresa}</span>
                            </div>
                            {detalle.nif && (
                              <div>
                                <span className="text-gray-600">NIF:</span>
                                <span className="ml-2 font-medium text-gray-900">{detalle.nif}</span>
                              </div>
                            )}
                            {detalle.modelo && (
                              <div>
                                <span className="text-gray-600">Modelo:</span>
                                <span className="ml-2 font-medium text-gray-900">{detalle.modelo}</span>
                              </div>
                            )}
                            {detalle.calidad && (
                              <div>
                                <span className="text-gray-600">Calidad:</span>
                                <span className="ml-2 font-medium text-gray-900">{detalle.calidad}</span>
                              </div>
                            )}
                            <div>
                              <span className="text-gray-600">Estado:</span>
                              <span className={`ml-2 font-medium ${detalle.clasificado ? 'text-green-600' : 'text-orange-600'}`}>
                                {detalle.clasificado ? 'Clasificado' : 'No clasificado (Inbox)'}
                              </span>
                            </div>
                          </div>
                        )}

                        {!detalle.success && (
                          <p className="text-sm text-red-600 ml-7">{detalle.error}</p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Certificados 190 */}
      {activeTab === 'certificados190' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Procesamiento de Certificados de Retenciones (C-190)</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Sube el archivo general en PDF del Modelo 190. El sistema dividirá los folios extrayendo el Nombre y NIF tanto del Pagador (Empresa) como del Perceptor (Trabajador) y guardará cada folio en la carpeta correspondiente de cada empresa de manera independiente.
                </p>
                <p className="text-sm text-blue-700 mt-2 font-medium">Límite: 100 archivos por subida</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Año del Periodo C-190</label>
            <input
              type="text"
              value={periodo190}
              onChange={(e) => setPeriodo190(e.target.value)}
              placeholder="Ej: 2024"
              className="w-full md:w-1/3 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>

          <div
            {...getRootProps190()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActive190
              ? 'border-primary bg-primary-light'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
              }`}
          >
            <input {...getInputProps190()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActive190 ? 'bg-primary-light' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActive190 ? 'text-primary' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActive190 ? '¡Suelta los archivos aquí!' : 'Arrastra archivos PDF de Certificados 190 aquí'}
                </p>
              </div>
            </div>
          </div>

          {archivos190.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos ({archivos190.length}/100)</h2>
                <div className="flex gap-2">
                  <button onClick={limpiar190} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2">
                    <Trash2 className="w-4 h-4" /> Limpiar
                  </button>
                  <button onClick={procesar190} disabled={procesando190} className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
                    {procesando190 ? <><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Procesando...</> : 'Procesar C-190'}
                  </button>
                </div>
              </div>
              <div className="space-y-3">
                {archivos190.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-4">
                      <FileSignature className="w-5 h-5 text-gray-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-base font-semibold text-gray-900 truncate">{archivo.file.name}</h4>
                        <p className="text-sm text-gray-500">{(archivo.file.size / 1024).toFixed(2)} KB</p>
                      </div>
                      <button onClick={() => setArchivos190(prev => prev.filter(a => a.id !== archivo.id))} className="p-2 hover:bg-red-50 rounded-lg transition-colors" disabled={procesando190}>
                        <Trash2 className="w-5 h-5 text-red-600" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resultados190 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados del Procesamiento</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600">Total Empresas</p>
                  <p className="text-2xl font-bold text-gray-900">{resultados190.total_empresas}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600">Total Trabajadores</p>
                  <p className="text-2xl font-bold text-green-600">{resultados190.total_trabajadores}</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <p className="text-sm text-purple-600">Archivos Generados</p>
                  <p className="text-2xl font-bold text-purple-600">{resultados190.documentos_creados}</p>
                </div>
              </div>
              <div className="space-y-2">
                {resultados190.detalles && resultados190.detalles.map((detalle, idx) => (
                  <div key={idx} className={`p-4 rounded-lg border ${detalle.estado === 'exito' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {detalle.estado === 'exito' ? <CheckCircle className="w-5 h-5 text-green-600 shrink-0" /> : <XCircle className="w-5 h-5 text-red-600 shrink-0" />}
                          <p className="font-medium text-gray-900">{detalle.nombre_trabajador}</p>
                        </div>
                        <p className="text-sm text-gray-600 ml-7">Empresa: {detalle.empresa}</p>
                        <p className={`text-sm ml-7 ${detalle.estado === 'exito' ? 'text-green-700' : 'text-red-600'}`}>Mensaje: {detalle.mensaje}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Certificados 180 */}
      {activeTab === 'certificados180' && (
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex gap-3">
              <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-blue-900">Procesamiento de Certificados de Retenciones de Alquileres (C-180)</h3>
                <p className="text-sm text-blue-700 mt-1">
                  Sube el archivo general en PDF del Modelo 180. El sistema dividirá los folios extrayendo el Nombre y NIF tanto del Pagador (Empresa) como del Perceptor (Arrendatario) y guardará cada folio en la carpeta correspondiente de cada empresa.
                </p>
                <p className="text-sm text-blue-700 mt-2 font-medium">Límite: 100 archivos por subida</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Año del Periodo C-180</label>
            <input
              type="text"
              value={periodo180}
              onChange={(e) => setPeriodo180(e.target.value)}
              placeholder="Ej: 2024"
              className="w-full md:w-1/3 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>

          <div
            {...getRootProps180()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActive180
              ? 'border-primary bg-primary-light'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
              }`}
          >
            <input {...getInputProps180()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActive180 ? 'bg-primary-light' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActive180 ? 'text-primary' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActive180 ? '¡Suelta los archivos aquí!' : 'Arrastra archivos PDF de Certificados 180 aquí'}
                </p>
              </div>
            </div>
          </div>

          {archivos180.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos ({archivos180.length}/100)</h2>
                <div className="flex gap-2">
                  <button onClick={limpiar180} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2">
                    <Trash2 className="w-4 h-4" /> Limpiar
                  </button>
                  <button onClick={procesar180} disabled={procesando180} className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed">
                    {procesando180 ? <><Loader2 className="w-4 h-4 animate-spin inline mr-2" />Procesando...</> : 'Procesar C-180'}
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {archivos180.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-4">
                      <FileSignature className="w-5 h-5 text-gray-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-base font-semibold text-gray-900 truncate">{archivo.file.name}</h4>
                        <p className="text-sm text-gray-500">{(archivo.file.size / 1024).toFixed(2)} KB</p>
                      </div>
                      <button
                        onClick={() => setArchivos180(prev => prev.filter(a => a.id !== archivo.id))}
                        className="p-2 hover:bg-red-50 rounded-lg transition-colors"
                        disabled={procesando180}
                      >
                        <Trash2 className="w-5 h-5 text-red-600" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resultados180 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados del Procesamiento (C-180)</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-blue-600">Total Empresas</p>
                  <p className="text-2xl font-bold text-gray-900">{resultados180.total_empresas}</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-sm text-green-600">Archivos Generados</p>
                  <p className="text-2xl font-bold text-green-600">{resultados180.total_archivos_generados}</p>
                </div>
              </div>
              <div className="space-y-2">
                {resultados180.results && resultados180.results.map((r, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${r.estado === 'exito' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-center gap-2 mb-1">
                      {getIconoEstado(r.estado)}
                      <p className="font-medium text-gray-900 truncate">
                        {r.nombre_trabajador || 'N/A'}
                      </p>
                    </div>
                    <p className="text-sm text-gray-600 ml-7">Empresa: {r.empresa}</p>
                    <p className={`text-sm ml-7 ${r.estado === 'exito' ? 'text-green-700' : 'text-red-600'}`}>Mensaje: {r.mensaje}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Altas */}
      {activeTab === 'altas' && (
        <div className="space-y-6">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="flex gap-3">
              <Users className="w-5 h-5 text-orange-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-orange-900">Importador de Altas / Bajas / I.D.C.</h3>
                <p className="text-sm text-orange-700 mt-1">
                  Sube documentos de alta o baja de la Seguridad Social (TA.2S) o Informes de Datos para la Cotización (I.D.C.). El sistema extraerá automáticamente el NIF del trabajador, su nombre y la empresa para organizarlos en la carpeta 'Laboral'.
                </p>
              </div>
            </div>
          </div>

          <div
            {...getRootPropsAlta()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActiveAlta
              ? 'border-primary bg-primary-light'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-primary-light/50'
              }`}
          >
            <input {...getInputPropsAlta()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActiveAlta ? 'bg-primary-light' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActiveAlta ? 'text-primary' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActiveAlta ? '¡Suelta los archivos aquí!' : 'Arrastra documentos de Alta / Baja / IDC aquí'}
                </p>
                <p className="text-sm text-gray-600 mt-1">Soporta múltiples archivos a la vez</p>
              </div>
            </div>
          </div>

          {archivosAlta.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos Preparados ({archivosAlta.length})</h2>
                <div className="flex gap-2">
                  {!procesandoAlta && (
                    <button onClick={limpiarAlta} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                      Limpiar
                    </button>
                  )}
                  <button onClick={procesarAlta} disabled={procesandoAlta} className="px-6 py-3 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-red-600 transition-all shadow-md disabled:opacity-50">
                    {procesandoAlta ? 'Procesando...' : 'Comenzar Importación'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {archivosAlta.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-lg p-3 border border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3 truncate">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <span className="text-sm font-medium truncate">{archivo.file.name}</span>
                    </div>
                    <button onClick={() => setArchivosAlta(prev => prev.filter(a => a.id !== archivo.id))} className="text-red-500 hover:bg-red-50 p-1 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resultadosAlta && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados de Importación</h3>
              <div className="space-y-2">
                {resultadosAlta.results.map((r, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${r.estado === 'exito' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-gray-900">{r.nombre_trabajador}</p>
                        <p className="text-xs text-gray-500">{r.empresa}</p>
                      </div>
                      <span className={`text-xs font-bold px-2 py-1 rounded-full ${r.estado === 'exito' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {r.estado.toUpperCase()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Finiquitos */}
      {activeTab === 'finiquitos' && (
        <div className="space-y-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex gap-3">
              <FileDown className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900">Importador de Finiquitos</h3>
                <p className="text-sm text-red-700 mt-1">
                  Sube documentos de finiquito. El sistema extraerá automáticamente el trabajador y la empresa para organizarlos en la carpeta 'Laboral'.
                </p>
              </div>
            </div>
          </div>

          <div
            {...getRootPropsFiniquito()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActiveFiniquito
              ? 'border-red-500 bg-red-50'
              : 'border-gray-300 bg-white hover:border-red-400 hover:bg-red-50/50'
              }`}
          >
            <input {...getInputPropsFiniquito()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActiveFiniquito ? 'bg-red-100' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActiveFiniquito ? 'text-red-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActiveFiniquito ? '¡Suelta los archivos aquí!' : 'Arrastra documentos de Finiquito aquí'}
                </p>
                <p className="text-sm text-gray-600 mt-1">Soporta múltiples archivos a la vez</p>
              </div>
            </div>
          </div>

          {archivosFiniquito.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos Preparados ({archivosFiniquito.length})</h2>
                <div className="flex gap-2">
                  {!procesandoFiniquito && (
                    <button onClick={limpiarFiniquito} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                      Limpiar
                    </button>
                  )}
                  <button onClick={procesarFiniquitos} disabled={procesandoFiniquito} className="px-6 py-3 bg-gradient-to-r from-red-500 to-orange-500 text-white rounded-lg font-medium hover:from-red-600 hover:to-orange-600 transition-all shadow-md disabled:opacity-50">
                    {procesandoFiniquito ? 'Procesando...' : 'Comenzar Importación'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {archivosFiniquito.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-lg p-3 border border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3 truncate">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <span className="text-sm font-medium truncate">{archivo.nombre}</span>
                    </div>
                    <button onClick={() => setArchivosFiniquito(prev => prev.filter(a => a.id !== archivo.id))} className="text-red-500 hover:bg-red-50 p-1 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resultadosFiniquito && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados de Importación</h3>
              <div className="space-y-2">
                {resultadosFiniquito.map((r, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${r.estado === 'exito' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-gray-900">{r.nombre_trabajador}</p>
                        <p className="text-xs text-gray-500">{r.empresa}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${r.estado === 'exito' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {r.estado.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{r.mensaje}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Contratos */}
      {activeTab === 'contratos' && (
        <div className="space-y-6">
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="flex gap-3">
              <FileSignature className="w-5 h-5 text-orange-600 shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-orange-900">Importador de Contratos</h3>
                <p className="text-sm text-orange-700 mt-1">
                  Sube contratos de trabajo. El sistema extraerá automáticamente el trabajador y la empresa para organizarlos en la carpeta 'Laboral'.
                </p>
              </div>
            </div>
          </div>

          <div
            {...getRootPropsContrato()}
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer ${isDragActiveContrato
              ? 'border-orange-500 bg-orange-50'
              : 'border-gray-300 bg-white hover:border-orange-400 hover:bg-orange-50/50'
              }`}
          >
            <input {...getInputPropsContrato()} />
            <div className="flex flex-col items-center gap-4">
              <div className={`p-4 rounded-full ${isDragActiveContrato ? 'bg-orange-100' : 'bg-gray-100'}`}>
                <Upload className={`w-12 h-12 ${isDragActiveContrato ? 'text-orange-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-lg font-semibold text-gray-900">
                  {isDragActiveContrato ? '¡Suelta los archivos aquí!' : 'Arrastra contratos aquí'}
                </p>
                <p className="text-sm text-gray-600 mt-1">Soporta múltiples archivos a la vez</p>
              </div>
            </div>
          </div>

          {archivosContrato.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-gray-900">Archivos Preparados ({archivosContrato.length})</h2>
                <div className="flex gap-2">
                  {!procesandoContrato && (
                    <button onClick={limpiarContrato} className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition flex items-center gap-2">
                      <Trash2 className="w-4 h-4" /> Limpiar
                    </button>
                  )}
                  <button onClick={procesarContratos} disabled={procesandoContrato} className="px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-lg font-medium hover:from-orange-600 hover:to-amber-600 transition-all shadow-md disabled:opacity-50">
                    {procesandoContrato ? 'Procesando...' : 'Comenzar Importación'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {archivosContrato.map(archivo => (
                  <div key={archivo.id} className="bg-white rounded-lg p-3 border border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-3 truncate">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <span className="text-sm font-medium truncate">{archivo.nombre}</span>
                    </div>
                    <button onClick={() => setArchivosContrato(prev => prev.filter(a => a.id !== archivo.id))} className="text-red-500 hover:bg-red-50 p-1 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {resultadosContrato && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Resultados de Importación</h3>
              <div className="space-y-2">
                {resultadosContrato.map((r, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${r.estado === 'exito' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-bold text-gray-900">{r.nombre_trabajador}</p>
                        <p className="text-xs text-gray-500">{r.empresa}</p>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${r.estado === 'exito' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                          {r.estado.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">{r.mensaje}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal de Envío de Correo */}
      {mostrarModalEnvio && (
        <ModalEnvioCorreo
          nominas={nominasParaEnviar}
          rntDisponible={rntDisponible}
          onClose={() => setMostrarModalEnvio(false)}
          onEnviado={() => {
            toast.success('Correo enviado exitosamente');
            setMostrarModalEnvio(false);
          }}
        />
      )}

      {/* Modal de Confirmación de Documento */}
      {modalDoc.isOpen && (
        <ModalConfirmarDocumento
          isOpen={modalDoc.isOpen}
          onClose={() => setModalDoc({ ...modalDoc, isOpen: false })}
          archivoObj={modalDoc.fileObj}
          detectedType={modalDoc.detectedType}
          empresaDetectada={modalDoc.empresa}
          onSuccess={(id, newCategory) => {
            if (modalDoc.retryCallback) {
              modalDoc.retryCallback(id, newCategory);
            }
          }}
        />
      )}
    </div>
  );
}
