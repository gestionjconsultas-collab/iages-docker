import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { CheckCircle, Clock, DollarSign, FileText, Download, RefreshCw, Trash2, X, Bot } from 'lucide-react';
import toast from 'react-hot-toast';
import ConfirmModal from './ConfirmModal';
import MobilePDFViewer from './MobilePDFViewer';

const FiniquitosView = () => {
  const [stats, setStats] = useState(null);
  const [documentos, setDocumentos] = useState([]);
  const [todasLineas, setTodasLineas] = useState([]);
  const [vistaActual, setVistaActual] = useState('documentos'); // 'documentos' o 'lineas'
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('todos'); // 'todos', 'pendiente', 'pagado'
  
  // Estados para modales
  const [pdfViewerDoc, setPdfViewerDoc] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);

  useEffect(() => {
    cargarDatos();
  }, []);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [statsRes, docsRes, lineasRes] = await Promise.all([
        axios.get('/api/finiquitos/stats'),
        axios.get('/api/finiquitos/documentos'),
        axios.get('/api/finiquitos/todas-lineas')
      ]);
      
      setStats(statsRes.data.stats);
      setDocumentos(docsRes.data.documentos);
      setTodasLineas(lineasRes.data.lineas);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error al cargar datos de finiquitos');
    } finally {
      setLoading(false);
    }
  };

  const procesarFiniquito = async (docId) => {
    try {
      const res = await axios.post(`/api/finiquitos/documentos/${docId}/procesar`);
      const taskId = res.data.task_id;
      
      toast.success('Procesamiento iniciado...');
      
      // Polling del estado de la tarea
      const checkTaskStatus = async () => {
        try {
          const statusRes = await axios.get(`/api/tasks/${taskId}`);
          const { state, progress } = statusRes.data;
          
          if (state === 'SUCCESS') {
            toast.success('¡Finiquito procesado correctamente!');
            cargarDatos(); // Recargar datos
            return true;
          } else if (state === 'FAILURE') {
            toast.error('Error al procesar finiquito');
            return true;
          } else {
            // Aún procesando
            return false;
          }
        } catch (error) {
          console.error('Error verificando estado:', error);
          return false;
        }
      };
      
      // Polling cada 2 segundos hasta que termine
      const pollInterval = setInterval(async () => {
        const isFinished = await checkTaskStatus();
        if (isFinished) {
          clearInterval(pollInterval);
        }
      }, 2000);
      
      // Timeout de seguridad de 60 segundos
      setTimeout(() => {
        clearInterval(pollInterval);
        cargarDatos(); // Recargar de todas formas
      }, 60000);
      
    } catch (error) {
      toast.error('Error al procesar finiquito');
      console.error(error);
    }
  };

  const handleDeleteDocument = (doc) => {
    setDocToDelete(doc);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;

    try {
      const res = await axios.delete(`/api/documentos/${docToDelete.id}`);
      if (res.data.success) {
        toast.success('Documento eliminado correctamente');
        cargarDatos();
      } else {
        toast.error(res.data.error || 'Error al eliminar');
      }
    } catch (error) {
      console.error('Error al eliminar:', error);
      toast.error('Error al eliminar el documento');
    } finally {
      setIsDeleteModalOpen(false);
      setDocToDelete(null);
    }
  };

  const cambiarEstadoLinea = async (lineaId, nuevoEstado) => {
    try {
      await axios.put(`/api/finiquitos/lineas/${lineaId}/estado`, { estado: nuevoEstado });
      toast.success(`Marcado como ${nuevoEstado}`);
      cargarDatos();
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  const lineasFiltradas = todasLineas.filter(linea => {
    if (filtroEstado === 'todos') return true;
    return linea.estado === filtroEstado;
  });

  if (loading) {
    return <div className="p-8 text-center">Cargando finiquitos...</div>;
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      {/* Header con Estadísticas */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 mb-4">Gestión de Finiquitos</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Documentos</p>
                <p className="text-2xl font-bold text-gray-800">{stats?.total_documentos || 0}</p>
              </div>
              <FileText className="text-blue-500" size={32} />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Líneas Pendientes</p>
                <p className="text-2xl font-bold text-primary">{stats?.pendientes || 0}</p>
              </div>
              <Clock className="text-primary" size={32} />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Líneas Pagadas</p>
                <p className="text-2xl font-bold text-green-600">{stats?.pagados || 0}</p>
              </div>
              <CheckCircle className="text-green-500" size={32} />
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Pendiente</p>
                <p className="text-2xl font-bold text-red-600">€{stats?.total_pendiente?.toFixed(2) || '0.00'}</p>
              </div>
              <DollarSign className="text-red-500" size={32} />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setVistaActual('documentos')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              vistaActual === 'documentos'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            Por Documentos
          </button>
          <button
            onClick={() => setVistaActual('lineas')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              vistaActual === 'lineas'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            Todas las Líneas
          </button>
          <button
            onClick={cargarDatos}
            className="ml-auto px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg flex items-center gap-2"
          >
            <RefreshCw size={16} />
            Actualizar
          </button>
        </div>
      </div>

      {/* Vista por Documentos */}
      {vistaActual === 'documentos' && (
        <div className="bg-white rounded-lg shadow overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Documento</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Empresa</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Total Líneas</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Pendientes</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Pagadas</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Importe Pendiente</th>
                <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {documentos.map(doc => (
                <tr key={doc.id} className="border-t hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-sm">
                    <button
                      onClick={() => setPdfViewerDoc(doc)}
                      className="text-primary hover:text-primary-hover font-medium text-left transition-colors"
                    >
                      {doc.nombre_archivo}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-sm">{doc.empresa_nombre}</td>
                  <td className="px-4 py-3 text-center text-sm">{doc.total_lineas}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="px-2 py-1 bg-primary-light text-primary-hover rounded text-sm">
                      {doc.lineas_pendientes}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                      {doc.lineas_pagadas}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-semibold">
                    €{doc.importe_pendiente.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      {doc.total_lineas === 0 && (
                        <button
                          onClick={() => procesarFiniquito(doc.id)}
                          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm flex items-center gap-1"
                        >
                          <Bot size={14} />
                          Procesar
                        </button>
                      )}
                      <a
                        href={`/api/documentos/${doc.id}/archivo?download=1`}
                        className="inline-flex items-center px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded text-sm transition-colors"
                        title="Descargar PDF"
                      >
                        <Download size={14} className="mr-1" />
                        PDF
                      </a>
                      <button
                        onClick={() => handleDeleteDocument(doc)}
                        className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Vista de Todas las Líneas */}
      {vistaActual === 'lineas' && (
        <>
          {/* Filtros */}
          <div className="mb-4 flex gap-2">
            <button
              onClick={() => setFiltroEstado('todos')}
              className={`px-4 py-2 rounded ${
                filtroEstado === 'todos' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
              }`}
            >
              Todos ({todasLineas.length})
            </button>
            <button
              onClick={() => setFiltroEstado('pendiente')}
              className={`px-4 py-2 rounded ${
                filtroEstado === 'pendiente' ? 'bg-primary text-white' : 'bg-white text-gray-700'
              }`}
            >
              Pendientes ({todasLineas.filter(l => l.estado === 'pendiente').length})
            </button>
            <button
              onClick={() => setFiltroEstado('pagado')}
              className={`px-4 py-2 rounded ${
                filtroEstado === 'pagado' ? 'bg-green-600 text-white' : 'bg-white text-gray-700'
              }`}
            >
              Pagados ({todasLineas.filter(l => l.estado === 'pagado').length})
            </button>
          </div>

          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-gray-700">Empresa</th>
                  <th className="px-3 py-3 text-left text-xs font-semibold text-gray-700">Documento</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-gray-700">Imp. Principal</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-gray-700">Recargo</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-gray-700">Total Deuda</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-gray-700">Intereses</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold text-gray-700">Total Plazo</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-700">Vencimiento</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold text-gray-700">Estado</th>
                </tr>
              </thead>
              <tbody>
                {lineasFiltradas.map(linea => (
                  <tr key={linea.id} className="border-t hover:bg-gray-50 transition-colors">
                    <td className="px-3 py-2 text-xs font-medium">{linea.empresa_nombre}</td>
                    <td className="px-3 py-2 text-xs truncate max-w-xs">{linea.nombre_archivo}</td>
                    <td className="px-3 py-2 text-right text-xs">€{linea.importe_principal?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-xs">€{linea.recargo_apremio?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-xs">€{linea.importe_total_deuda?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-xs">€{linea.importe_intereses?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right text-xs font-semibold">€{linea.importe_total_plazo?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-center text-xs">
                      {linea.fecha_vencimiento ? new Date(linea.fecha_vencimiento).toLocaleDateString('es-ES') : '-'}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <select
                        value={linea.estado}
                        onChange={(e) => cambiarEstadoLinea(linea.id, e.target.value)}
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          linea.estado === 'pagado'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-primary-light text-primary-hover'
                        }`}
                      >
                        <option value="pendiente">Pendiente</option>
                        <option value="pagado">Pagado</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Selector de PDF (Visor flotante) */}
      {pdfViewerDoc && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/95 animate-in fade-in duration-200">
          <div className="flex items-center justify-between p-4 bg-gray-900 text-white">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-primary/20 rounded-lg">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-bold truncate max-w-md">{pdfViewerDoc.nombre_archivo}</h3>
                <p className="text-sm text-gray-400">Previsualización de documento</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={`/api/documentos/${pdfViewerDoc.id}/archivo?download=1`}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Descargar
              </a>
              <button
                onClick={() => setPdfViewerDoc(null)}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                title="Cerrar"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <MobilePDFViewer documentId={pdfViewerDoc.id} />
          </div>
        </div>
      )}

      {/* Confirmación de Borrado */}
      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={confirmDelete}
        title="¿Eliminar finiquito?"
        message={`¿Estás seguro de que deseas eliminar "${docToDelete?.nombre_archivo}"? Esta acción es permanente.`}
      />
    </div>
  );
};

export default FiniquitosView;