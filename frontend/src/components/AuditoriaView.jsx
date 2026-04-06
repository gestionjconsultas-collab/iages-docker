// frontend/src/components/AuditoriaView.jsx
import React, { useState, useEffect } from 'react';
import { useAuditoria } from '../hooks/useAuditoria';
import axios from 'axios';
import {
  FaSearch,
  FaFilter,
  FaDownload,
  FaEye,
  FaUser,
  FaClock,
  FaChartLine,
  FaFileAlt,
  FaTimes
} from 'react-icons/fa';

const AuditoriaView = () => {
  const [filters, setFilters] = useState({});
  const { data, isLoading } = useAuditoria(filters);
  const logs = data?.logs || [];
  const loading = isLoading;
  const [stats, setStats] = useState({});
  const [usuarios, setUsuarios] = useState([]);
  const [tiposAccion, setTiposAccion] = useState([]);

  // Filtros
  const [filtros, setFiltros] = useState(() => {
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    return {
      user_id: '',
      accion: '',
      entidad_tipo: '',
      fecha_desde: thirtyDaysAgo.toISOString().split('T')[0],
      fecha_hasta: '',
      page: 1,
      per_page: 50
    };
  });

  const [totalPages, setTotalPages] = useState(0);
  const [totalLogs, setTotalLogs] = useState(0);

  // Modal de detalles
  const [logSeleccionado, setLogSeleccionado] = useState(null);
  const [mostrarDetalle, setMostrarDetalle] = useState(false);

  useEffect(() => {
    // Actualiza filtros cuando cambian
    setFilters(filtros);
  }, [filtros]);

  // Cargar estadísticas
  useEffect(() => {
    const cargarEstadisticas = async () => {
      try {
        const res = await axios.get('/api/auditoria/estadisticas', { withCredentials: true });
        setStats(res.data);
      } catch (error) {
        console.error('Error cargando estadísticas:', error);
      }
    };
    cargarEstadisticas();
  }, []);

  // Cargar usuarios y tipos de acción
  useEffect(() => {
    const cargarFiltros = async () => {
      try {
        // Cargar usuarios de la gestoría
        const usersRes = await axios.get('/api/users', { withCredentials: true });
        if (usersRes.data.success) {
          setUsuarios(usersRes.data.users || []);
        }

        // Cargar tipos de acción
        const accionesRes = await axios.get('/api/auditoria/tipos-accion', { withCredentials: true });
        if (accionesRes.data.acciones_en_uso) {
          setTiposAccion(accionesRes.data.acciones_en_uso);
        }
      } catch (error) {
        console.error('Error cargando filtros:', error);
      }
    };
    cargarFiltros();
  }, []);

  // Actualizar paginación cuando cambian los datos
  useEffect(() => {
    if (data) {
      setTotalPages(data.total_pages || 0);
      setTotalLogs(data.total || 0);
    }
  }, [data]);

  const handleFiltroChange = (key, value) => {
    setFiltros(prev => ({
      ...prev,
      [key]: value,
      page: 1 // Resetear a página 1 cuando cambian filtros
    }));
  };

  const limpiarFiltros = () => {
    setFiltros({
      user_id: '',
      accion: '',
      entidad_tipo: '',
      fecha_desde: '',
      fecha_hasta: '',
      page: 1,
      per_page: 50
    });
  };

  const exportarCSV = () => {
    const headers = ['Fecha', 'Usuario', 'Acción', 'Descripción', 'Entidad', 'IP'];
    const rows = logs.map(log => [
      new Date(log.fecha_creacion).toLocaleString('es-ES'),
      log.user_nombre,
      log.accion,
      log.descripcion || '',
      log.entidad_tipo ? `${log.entidad_tipo} #${log.entidad_id}` : '',
      log.ip_address || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `auditoria_${new Date().toISOString().split('T')[0]}.csv`);
    link.click();
  };

  const formatearAccion = (accion) => {
    return accion
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getAccionColor = (accion) => {
    if (accion.includes('creado') || accion.includes('login')) return 'text-green-600 bg-green-50';
    if (accion.includes('eliminado') || accion.includes('logout')) return 'text-red-600 bg-red-50';
    if (accion.includes('actualizado') || accion.includes('editado')) return 'text-blue-600 bg-blue-50';
    if (accion.includes('leido')) return 'text-purple-600 bg-purple-50';
    return 'text-gray-600 bg-gray-50';
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          📊 Auditoría del Sistema
        </h1>
        <p className="text-gray-600">
          Registro completo de todas las acciones realizadas en el sistema
        </p>
      </div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Registros</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.total_logs || 0}
              </p>
            </div>
            <FaFileAlt className="text-3xl text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Últimos 7 Días</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.logs_ultimos_7_dias || 0}
              </p>
            </div>
            <FaClock className="text-3xl text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Usuarios Activos</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.top_usuarios?.length || 0}
              </p>
            </div>
            <FaUser className="text-3xl text-purple-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Tipos de Acción</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.top_acciones?.length || 0}
              </p>
            </div>
            <FaChartLine className="text-3xl text-primary" />
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center gap-2 mb-4">
          <FaFilter className="text-gray-600" />
          <h2 className="text-lg font-semibold text-gray-900">Filtros</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Usuario
            </label>
            <select
              value={filtros.user_id}
              onChange={(e) => handleFiltroChange('user_id', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              {usuarios.map(user => (
                <option key={user.id} value={user.id}>
                  {user.nombre}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Acción
            </label>
            <select
              value={filtros.accion}
              onChange={(e) => handleFiltroChange('accion', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todas</option>
              {tiposAccion.map(tipo => (
                <option key={tipo.accion} value={tipo.accion}>
                  {formatearAccion(tipo.accion)} ({tipo.count})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de Entidad
            </label>
            <select
              value={filtros.entidad_tipo}
              onChange={(e) => handleFiltroChange('entidad_tipo', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Todos</option>
              <option value="documento">Documento</option>
              <option value="empresa">Empresa</option>
              <option value="tarea">Tarea</option>
              <option value="user">Usuario</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fecha Desde
            </label>
            <input
              type="date"
              value={filtros.fecha_desde}
              onChange={(e) => handleFiltroChange('fecha_desde', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fecha Hasta
            </label>
            <input
              type="date"
              value={filtros.fecha_hasta}
              onChange={(e) => handleFiltroChange('fecha_hasta', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button
            onClick={limpiarFiltros}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
          >
            Limpiar Filtros
          </button>
          <button
            onClick={exportarCSV}
            disabled={logs.length === 0}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <FaDownload />
            Exportar CSV
          </button>
        </div>
      </div>

      {/* Tabla de Logs */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-linear-to-r from-orange-500 to-red-500">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                  Usuario
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                  Acción
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
                  Descripción
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-white uppercase tracking-wider w-32">
                  Entidad
                </th>
                <th className="px-4 py-3 text-center text-xs font-medium text-white uppercase tracking-wider w-24">
                  Detalles
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="7" className="px-6 py-4 text-center">
                    <div className="flex justify-center items-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                    </div>
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-4 text-center text-gray-500">
                    No hay registros para mostrar
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {log.user_nombre}
                      </div>
                      <div className="text-xs text-gray-500">{log.user_email}</div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAccionColor(log.accion)}`}>
                        {formatearAccion(log.accion)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">
                      <div className="max-w-md truncate" title={log.descripcion}>
                        {log.descripcion || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {log.entidad_tipo ? (
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {log.entidad_tipo} #{log.entidad_id}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-center">
                      <button
                        onClick={() => {
                          setLogSeleccionado(log);
                          setMostrarDetalle(true);
                        }}
                        className="inline-flex items-center px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                      >
                        <FaEye className="mr-1" /> Ver
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => handleFiltroChange('page', Math.max(1, filtros.page - 1))}
                disabled={filtros.page === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                onClick={() => handleFiltroChange('page', Math.min(totalPages, filtros.page + 1))}
                disabled={filtros.page === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Mostrando <span className="font-medium">{(filtros.page - 1) * filtros.per_page + 1}</span> a{' '}
                  <span className="font-medium">{Math.min(filtros.page * filtros.per_page, totalLogs)}</span> de{' '}
                  <span className="font-medium">{totalLogs}</span> resultados
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => handleFiltroChange('page', Math.max(1, filtros.page - 1))}
                    disabled={filtros.page === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Anterior
                  </button>
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const pageNum = i + 1;
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handleFiltroChange('page', pageNum)}
                        className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${filtros.page === pageNum
                          ? 'z-10 bg-blue-50 border-blue-500 text-blue-600'
                          : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                          }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                  <button
                    onClick={() => handleFiltroChange('page', Math.min(totalPages, filtros.page + 1))}
                    disabled={filtros.page === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    Siguiente
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal de Detalles */}
      {mostrarDetalle && logSeleccionado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-bold text-gray-900">Detalles del Log</h3>
                <button
                  onClick={() => setMostrarDetalle(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <FaTimes />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Usuario</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {logSeleccionado.user_nombre} ({logSeleccionado.user_email})
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Acción</label>
                  <p className="mt-1">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getAccionColor(logSeleccionado.accion)}`}>
                      {formatearAccion(logSeleccionado.accion)}
                    </span>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Fecha/Hora</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {new Date(logSeleccionado.fecha_creacion).toLocaleString('es-ES')}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Descripción</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {logSeleccionado.descripcion || '-'}
                  </p>
                </div>

                {/* Mostrar pregunta si es una acción de chat */}
                {logSeleccionado.detalles?.pregunta && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <label className="block text-sm font-medium text-blue-900 mb-1">💬 Pregunta del Usuario</label>
                    <p className="text-sm text-blue-800 italic">
                      "{logSeleccionado.detalles.pregunta}"
                    </p>
                  </div>
                )}

                {logSeleccionado.entidad_tipo && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Entidad Afectada</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {logSeleccionado.entidad_tipo} #{logSeleccionado.entidad_id}
                    </p>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium text-gray-700">Dirección IP</label>
                  <p className="mt-1 text-sm text-gray-900">
                    {logSeleccionado.ip_address || '-'}
                  </p>
                </div>

                {logSeleccionado.user_agent && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Navegador/Dispositivo</label>
                    <p className="mt-1 text-sm text-gray-900 break-all">
                      {logSeleccionado.user_agent}
                    </p>
                  </div>
                )}

                {logSeleccionado.metodo_http && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Método HTTP</label>
                    <p className="mt-1 text-sm text-gray-900">
                      {logSeleccionado.metodo_http}
                    </p>
                  </div>
                )}

                {logSeleccionado.endpoint && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Endpoint</label>
                    <p className="mt-1 text-sm text-gray-900 font-mono bg-gray-100 p-2 rounded">
                      {logSeleccionado.endpoint}
                    </p>
                  </div>
                )}

                {logSeleccionado.detalles && Object.keys(logSeleccionado.detalles).length > 0 && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Detalles Adicionales
                    </label>
                    <pre className="mt-1 text-sm bg-gray-100 p-4 rounded overflow-x-auto">
                      {JSON.stringify(logSeleccionado.detalles, null, 2)}
                    </pre>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setMostrarDetalle(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditoriaView;