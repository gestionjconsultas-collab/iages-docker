import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle, Clock, DollarSign, FileText, Download, RefreshCw, ChevronLeft, Bot, Loader2, Trash2, X } from 'lucide-react';
import toast from 'react-hot-toast';
import RecordatoriosDashboard from './RecordatoriosDashboard';
import ConfirmModal from './ConfirmModal';
import MobilePDFViewer from './MobilePDFViewer';

const FiniquitosGestionView = ({ empresaId }) => {
  const navigate = useNavigate();
  const [documentos, setDocumentos] = useState([]);
  const [empresa, setEmpresa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [vistaDetalle, setVistaDetalle] = useState(null); // { tipo: 'fiscal'|'laboral', documento_id, datos }
  const [tabActiva, setTabActiva] = useState('documentos'); // 'documentos', 'recordatorios'

  // Estados para modales
  const [pdfViewerDoc, setPdfViewerDoc] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState(null);

  useEffect(() => {
    cargarDatos();
  }, [empresaId]);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [empRes, docsRes] = await Promise.all([
        axios.get(`/api/empresas/${empresaId}`),
        axios.get(`/api/empresas/${empresaId}/documentos?categoria=Finiquitos`)
      ]);

      setEmpresa(empRes.data.empresa);

      // Enriquecer documentos con información del tipo de finiquito
      const docsEnriquecidos = await Promise.all(
        (docsRes.data.documentos || []).map(async (doc) => {
          if (!doc.procesado) return { ...doc, tipo_finiquito: null };

          const tipo = doc.datos_extraidos?.tipo_finiquito;
          return { ...doc, tipo_finiquito: tipo };
        })
      );

      setDocumentos(docsEnriquecidos);
    } catch (error) {
      console.error('Error cargando datos:', error);
      toast.error('Error al cargar datos de finiquitos');
    } finally {
      setLoading(false);
    }
  };

  const [procesando, setProcesando] = useState(new Set());

  const procesarFiniquito = async (docId) => {
    // Agregar a la lista de documentos procesando
    setProcesando(prev => new Set([...prev, docId]));

    try {
      const res = await axios.post(`/api/finiquitos/documentos/${docId}/procesar`);
      const taskId = res.data.task_id;

      toast.loading('Procesando con IA...', { id: docId });

      // Polling del estado de la tarea
      const checkTaskStatus = async () => {
        try {
          const statusRes = await axios.get(`/api/tasks/${taskId}`);
          const { state, result } = statusRes.data;

          if (state === 'SUCCESS') {
            toast.success('✅ ¡Finiquito procesado!', { id: docId });
            setProcesando(prev => {
              const nuevo = new Set(prev);
              nuevo.delete(docId);
              return nuevo;
            });
            cargarDatos(); // Recargar datos
            return true;
          } else if (state === 'FAILURE') {
            toast.error('❌ Error al procesar', { id: docId });
            setProcesando(prev => {
              const nuevo = new Set(prev);
              nuevo.delete(docId);
              return nuevo;
            });
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
        setProcesando(prev => {
          const nuevo = new Set(prev);
          nuevo.delete(docId);
          return nuevo;
        });
        toast.dismiss(docId);
        cargarDatos(); // Recargar de todas formas
      }, 60000);

    } catch (error) {
      toast.error('Error al procesar finiquito');
      setProcesando(prev => {
        const nuevo = new Set(prev);
        nuevo.delete(docId);
        return nuevo;
      });
      console.error(error);
    }
  };

  const verDetalleFiniquito = async (doc) => {
    if (doc.tipo_finiquito === 'fiscal') {
      // Cargar líneas
      const res = await axios.get(`/api/finiquitos/documentos/${doc.id}/lineas`);
      setVistaDetalle({
        tipo: 'fiscal',
        documento: doc,
        lineas: res.data.lineas || []
      });
    } else if (doc.tipo_finiquito === 'laboral') {
      // Cargar finiquito laboral
      const res = await axios.get(`/api/finiquitos/documentos/${doc.id}/laboral`);
      setVistaDetalle({
        tipo: 'laboral',
        documento: doc,
        finiquito: res.data.finiquito
      });
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
      // Recargar vista de detalle
      verDetalleFiniquito(vistaDetalle.documento);
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  const cambiarEstadoLaboral = async (finiquitoId, nuevoEstado) => {
    try {
      await axios.put(`/api/finiquitos/finiquito-laboral/${finiquitoId}/estado`, { estado: nuevoEstado });
      toast.success(`Marcado como ${nuevoEstado}`);
      // Recargar vista de detalle
      verDetalleFiniquito(vistaDetalle.documento);
    } catch (error) {
      toast.error('Error al actualizar estado');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  // Vista de detalle de finiquito
  if (vistaDetalle) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <button onClick={() => setVistaDetalle(null)} className="p-2 hover:bg-gray-100 rounded-lg">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <h2 className="text-2xl font-bold">{vistaDetalle.documento.nombre_archivo}</h2>
            <p className="text-gray-600">
              {vistaDetalle.tipo === 'fiscal' ? 'Liquidación Fiscal' : 'Finiquito Laboral'}
            </p>
          </div>
        </div>

        {vistaDetalle.tipo === 'fiscal' && (
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-3 text-right text-xs font-semibold">Imp. Principal</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold">Recargo</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold">Total Deuda</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold">Intereses</th>
                  <th className="px-3 py-3 text-right text-xs font-semibold">Total Plazo</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold">Vencimiento</th>
                  <th className="px-3 py-3 text-center text-xs font-semibold">Estado</th>
                </tr>
              </thead>
              <tbody>
                {(vistaDetalle.lineas || []).map(linea => (
                  <tr key={linea.id} className="border-t hover:bg-gray-50 transition-colors">
                    <td className="px-3 py-2 text-right">€{linea.importe_principal?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">€{linea.recargo_apremio?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">€{linea.importe_total_deuda?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">€{linea.importe_intereses?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right font-semibold">€{linea.importe_total_plazo?.toFixed(2)}</td>
                    <td className="px-3 py-2 text-center">
                      {linea.fecha_vencimiento ? new Date(linea.fecha_vencimiento).toLocaleDateString('es-ES') : '-'}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <select
                        value={linea.estado}
                        onChange={(e) => cambiarEstadoLinea(linea.id, e.target.value)}
                        className={`px-2 py-1 rounded text-xs font-medium ${linea.estado === 'pagado' ? 'bg-green-100 text-green-700' : 'bg-primary-light text-primary-hover'
                          }`}
                      >
                        <option value="pendiente">Pendiente</option>
                        <option value="pagado">Pagado</option>
                      </select>
                    </td>
                  </tr>
                ))}

                {/* Fila de TOTAL GENERAL */}
                {vistaDetalle.documento.datos_extraidos?.total_general && (
                  <tr className="border-t-2 border-gray-300 bg-blue-50 font-bold">
                    <td className="px-3 py-3 text-right">
                      €{vistaDetalle.documento.datos_extraidos.total_general.importe_principal?.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      €{vistaDetalle.documento.datos_extraidos.total_general.recargo_apremio?.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      €{vistaDetalle.documento.datos_extraidos.total_general.importe_total_deuda?.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right">
                      €{vistaDetalle.documento.datos_extraidos.total_general.importe_intereses?.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-right text-lg">
                      €{vistaDetalle.documento.datos_extraidos.total_general.importe_total_plazo?.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 text-center text-sm font-bold">TOTAL GENERAL</td>
                    <td className="px-3 py-3 text-center">-</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {vistaDetalle.tipo === 'laboral' && vistaDetalle.finiquito && (
          <div className="bg-white rounded-lg shadow p-6 space-y-6">
            {/* Datos del trabajador */}
            <div className="grid grid-cols-2 gap-4 pb-4 border-b">
              <div>
                <p className="text-sm text-gray-600">Trabajador</p>
                <p className="font-semibold">{vistaDetalle.finiquito.nombre_trabajador}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">NIF</p>
                <p className="font-semibold">{vistaDetalle.finiquito.nif_trabajador}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Categoría</p>
                <p className="font-semibold">{vistaDetalle.finiquito.categoria}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Motivo Baja</p>
                <p className="font-semibold">{vistaDetalle.finiquito.motivo_baja}</p>
              </div>
            </div>
            {/* Devengos */}
            <div>
              <h3 className="font-semibold mb-2">Devengos</h3>
              <table className="w-full text-sm">
                <thead className="bg-green-50">
                  <tr>
                    <th className="px-3 py-2 text-left">Concepto</th>
                    <th className="px-3 py-2 text-right">Importe</th>
                  </tr>
                </thead>
                <tbody>
                  {(vistaDetalle.finiquito.conceptos_devengos || []).map((concepto, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="px-3 py-2">{concepto.concepto}</td>
                      <td className="px-3 py-2 text-right">€{concepto.importe?.toFixed(2)}</td>
                    </tr>
                  ))}
                  <tr className="border-t font-semibold bg-green-50">
                    <td className="px-3 py-2">TOTAL DEVENGOS</td>
                    <td className="px-3 py-2 text-right">€{vistaDetalle.finiquito.total_devengos?.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Deducciones */}
            <div>
              <h3 className="font-semibold mb-2">Deducciones</h3>
              <table className="w-full text-sm">
                <thead className="bg-red-50">
                  <tr>
                    <th className="px-3 py-2 text-left">Concepto</th>
                    <th className="px-3 py-2 text-right">Importe</th>
                  </tr>
                </thead>
                <tbody>
                  {(vistaDetalle.finiquito.conceptos_deducciones || []).map((concepto, idx) => (
                    <tr key={idx} className="border-t">
                      <td className="px-3 py-2">{concepto.concepto}</td>
                      <td className="px-3 py-2 text-right">€{concepto.importe?.toFixed(2)}</td>
                    </tr>
                  ))}
                  <tr className="border-t font-semibold bg-red-50">
                    <td className="px-3 py-2">TOTAL DEDUCCIONES</td>
                    <td className="px-3 py-2 text-right">€{vistaDetalle.finiquito.total_deducciones?.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Importe líquido y estado */}
            <div className="bg-blue-50 p-4 rounded-lg flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Importe Líquido a Percibir</p>
                <p className="text-3xl font-bold text-blue-600">€{vistaDetalle.finiquito.importe_liquido?.toFixed(2)}</p>
              </div>
              <div>
                <select
                  value={vistaDetalle.finiquito.estado}
                  onChange={(e) => cambiarEstadoLaboral(vistaDetalle.finiquito.id, e.target.value)}
                  className={`px-4 py-2 rounded font-medium ${vistaDetalle.finiquito.estado === 'pagado'
                    ? 'bg-green-100 text-green-700'
                    : 'bg-primary-light text-primary-hover'
                    }`}
                >
                  <option value="pendiente">Pendiente</option>
                  <option value="pagado">Pagado</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Vista lista de documentos
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(`/empresa/${empresaId}`)} className="p-2 hover:bg-gray-100 rounded-lg">
          <ChevronLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Finiquitos</h1>
          <p className="text-gray-600">{empresa?.nombre}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200">
        <button
          onClick={() => setTabActiva('documentos')}
          className={`px-4 py-2 font-medium transition ${tabActiva === 'documentos'
            ? 'text-primary border-b-2 border-primary'
            : 'text-gray-600 hover:text-gray-900'
            }`}
        >
          📄 Por Documentos
        </button>
        <button
          onClick={() => setTabActiva('recordatorios')}
          className={`px-4 py-2 font-medium transition ${tabActiva === 'recordatorios'
            ? 'text-primary border-b-2 border-primary'
            : 'text-gray-600 hover:text-gray-900'
            }`}
        >
          📧 Recordatorios
        </button>
      </div>

      {/* Contenido de tabs */}
      {tabActiva === 'documentos' && (
        <>
          <div className="bg-white p-4 rounded-lg shadow">
            <p className="text-sm text-gray-600">Total Documentos</p>
            <p className="text-3xl font-bold">{documentos.length}</p>
          </div>

          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Documento</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Tipo</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Estado</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">Acciones</th>
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
                    <td className="px-4 py-3 text-center text-sm">
                      {doc.tipo_finiquito === 'fiscal' ? (
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">Fiscal</span>
                      ) : doc.tipo_finiquito === 'laboral' ? (
                        <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">Laboral</span>
                      ) : (
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {doc.procesado ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">Procesado</span>
                      ) : (
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">Sin procesar</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        {!doc.procesado ? (
                          <button
                            onClick={() => procesarFiniquito(doc.id)}
                            disabled={procesando.has(doc.id)}
                            className="flex items-center gap-2 px-4 py-2 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                          >
                            {procesando.has(doc.id) ? (
                              <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Procesando...
                              </>
                            ) : (
                              <>
                                <Bot className="w-4 h-4" />
                                Procesar con IA
                              </>
                            )}
                          </button>
                        ) : (
                          <button
                            onClick={() => verDetalleFiniquito(doc)}
                            className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm transition-colors"
                          >
                            Ver Detalle
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
        </>
      )}

      {tabActiva === 'recordatorios' && (
        <RecordatoriosDashboard empresaId={empresaId} />
      )}

      {/* Visor de PDF */}
      {pdfViewerDoc && (
        <div className="fixed inset-0 z-[60] flex flex-col bg-black/95 animate-in fade-in duration-200">
          <div className="flex items-center justify-between p-4 bg-gray-900 text-white shadow-lg">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-primary/20 rounded-lg">
                <FileText className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h3 className="text-lg font-bold truncate max-w-md">{pdfViewerDoc.nombre_archivo}</h3>
                <p className="text-sm text-gray-400">Previsualización del documento</p>
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
        message={`¿Estás seguro de que deseas eliminar físicamente "${docToDelete?.nombre_archivo}"? Esta acción es irreversible.`}
      />
    </div>
  );
};

export default FiniquitosGestionView;