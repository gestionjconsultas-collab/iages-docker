import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Calendar, Mail, CheckCircle, XCircle, Clock, TrendingUp, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const RecordatoriosDashboard = ({ empresaId }) => {
  const [estadisticas, setEstadisticas] = useState(null);
  const [cuotasProximas, setCuotasProximas] = useState([]);
  const [historialRecordatorios, setHistorialRecordatorios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [vistaActual, setVistaActual] = useState('estadisticas'); // 'estadisticas', 'proximas', 'historial'

  useEffect(() => {
    cargarDatos();
  }, [empresaId]);

  const cargarDatos = async () => {
    setLoading(true);
    try {
      const [statsRes, cuotasRes, historialRes] = await Promise.all([
        axios.get('/api/finiquitos/estadisticas-recordatorios'),
        axios.get('/api/finiquitos/cuotas-proximas', { params: { empresa_id: empresaId } }),
        axios.get('/api/finiquitos/recordatorios', { params: { empresa_id: empresaId } })
      ]);

      setEstadisticas(statsRes.data.estadisticas);
      setCuotasProximas(cuotasRes.data.cuotas || []);
      setHistorialRecordatorios(historialRes.data.recordatorios || []);
    } catch (error) {
      console.error('Error cargando datos de recordatorios:', error);
      toast.error('Error al cargar datos de recordatorios');
    } finally {
      setLoading(false);
    }
  };

  const getDiasColor = (dias) => {
    if (dias <= 0) return 'text-red-600 bg-red-50';
    if (dias <= 3) return 'text-primary bg-primary-light';
    if (dias <= 7) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  const getEstadoBadge = (estado) => {
    const styles = {
      enviado: 'bg-blue-100 text-blue-700',
      confirmado: 'bg-green-100 text-green-700',
      ignorado: 'bg-gray-100 text-gray-700'
    };
    const labels = {
      enviado: 'Pendiente',
      confirmado: 'Confirmado',
      ignorado: 'Ignorado'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${styles[estado] || styles.enviado}`}>
        {labels[estado] || estado}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header con tabs */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">📧 Recordatorios de Pago</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setVistaActual('estadisticas')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              vistaActual === 'estadisticas'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Estadísticas
          </button>
          <button
            onClick={() => setVistaActual('proximas')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              vistaActual === 'proximas'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Próximas
          </button>
          <button
            onClick={() => setVistaActual('historial')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              vistaActual === 'historial'
                ? 'bg-primary text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Historial
          </button>
        </div>
      </div>

      {/* Vista: Estadísticas */}
      {vistaActual === 'estadisticas' && estadisticas && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Enviados</p>
                <p className="text-3xl font-bold text-gray-900">{estadisticas.total_enviados}</p>
              </div>
              <Mail className="w-12 h-12 text-blue-500" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Confirmados</p>
                <p className="text-3xl font-bold text-green-600">{estadisticas.confirmados}</p>
              </div>
              <CheckCircle className="w-12 h-12 text-green-500" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pendientes</p>
                <p className="text-3xl font-bold text-primary">{estadisticas.pendientes_respuesta}</p>
              </div>
              <Clock className="w-12 h-12 text-primary" />
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Tasa de Respuesta</p>
                <p className="text-3xl font-bold text-purple-600">{estadisticas.tasa_respuesta}%</p>
              </div>
              <TrendingUp className="w-12 h-12 text-purple-500" />
            </div>
          </div>
        </div>
      )}

      {/* Vista: Cuotas Próximas a Vencer */}
      {vistaActual === 'proximas' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 bg-gray-50 border-b">
            <h3 className="font-semibold text-gray-900">
              Cuotas que vencen en los próximos 30 días ({cuotasProximas.length})
            </h3>
          </div>
          
          {cuotasProximas.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Calendar className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>No hay cuotas próximas a vencer</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Empresa</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Documento</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">Importe</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">Vencimiento</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">Días Restantes</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">Recordatorios</th>
                  </tr>
                </thead>
                <tbody>
                  {cuotasProximas.map((cuota) => (
                    <tr key={cuota.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">{cuota.empresa.nombre}</td>
                      <td className="px-4 py-3 text-sm">{cuota.documento.nombre_archivo}</td>
                      <td className="px-4 py-3 text-sm text-right font-semibold">
                        €{cuota.importe_total_plazo?.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-sm text-center">
                        {new Date(cuota.fecha_vencimiento).toLocaleDateString('es-ES')}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${getDiasColor(cuota.dias_faltantes)}`}>
                          {cuota.dias_faltantes <= 0 ? 'VENCIDO' : `${cuota.dias_faltantes} días`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className="text-xs text-gray-600">
                          {cuota.recordatorios_enviados} enviado{cuota.recordatorios_enviados !== 1 ? 's' : ''}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Vista: Historial de Recordatorios */}
      {vistaActual === 'historial' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 bg-gray-50 border-b">
            <h3 className="font-semibold text-gray-900">
              Historial de Recordatorios Enviados (últimos 100)
            </h3>
          </div>
          
          {historialRecordatorios.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <Mail className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>No hay recordatorios enviados</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Fecha Envío</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Empresa</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600">Email</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">Tipo</th>
                    <th className="px-4 py-3 text-right text-xs font-semibold text-gray-600">Importe</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {historialRecordatorios.map((rec) => (
                    <tr key={rec.id} className="border-t hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm">
                        {new Date(rec.fecha_envio).toLocaleDateString('es-ES')} {new Date(rec.fecha_envio).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-4 py-3 text-sm">{rec.empresa.nombre}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{rec.email_enviado_a}</td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          rec.tipo_recordatorio === '7_dias' ? 'bg-blue-100 text-blue-700' :
                          rec.tipo_recordatorio === '3_dias' ? 'bg-primary-light text-primary-hover' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {rec.tipo_recordatorio === '7_dias' ? '7 días' :
                           rec.tipo_recordatorio === '3_dias' ? '3 días' :
                           'Vencimiento'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-right font-semibold">
                        €{rec.linea.importe_total_plazo?.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {getEstadoBadge(rec.estado)}
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
  );
};

export default RecordatoriosDashboard;