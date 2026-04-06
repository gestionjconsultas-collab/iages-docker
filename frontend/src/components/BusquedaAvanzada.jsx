import React, { useState } from 'react';
import axios from 'axios';
import { Search, Filter, X, FileText, Building2, Calendar, Loader2, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function BusquedaAvanzada() {
  const [query, setQuery] = useState('');
  const [filtros, setFiltros] = useState({
    fecha_desde: '',
    fecha_hasta: '',
    categoria: '',
    departamento: ''
  });
  const [resultados, setResultados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [mostrarFiltros, setMostrarFiltros] = useState(false);

  const navigate = useNavigate();

  const buscar = async () => {
    if (!query && !filtros.categoria && !filtros.departamento) {
      toast.error('Ingresa un término de búsqueda o selecciona filtros');
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post('/api/buscar/avanzada', {
        query,
        filtros
      }, { withCredentials: true });

      if (res.data.success) {
        setResultados(res.data.resultados);
        
        const totalResultados = res.data.resultados.total_empresas + res.data.resultados.total_documentos;
        if (totalResultados === 0) {
          toast('No se encontraron resultados', { icon: '🔍' });
        } else {
          toast.success(`${totalResultados} resultados encontrados`);
        }
      }
    } catch (error) {
      console.error('Error en búsqueda:', error);
      toast.error('Error al buscar');
    } finally {
      setLoading(false);
    }
  };

  const limpiarFiltros = () => {
    setFiltros({
      fecha_desde: '',
      fecha_hasta: '',
      categoria: '',
      departamento: ''
    });
    setQuery('');
    setResultados(null);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      buscar();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <Search className="w-8 h-8 text-primary" />
          Búsqueda Avanzada
        </h1>
        <p className="text-gray-600 mt-1">Encuentra empresas y documentos con filtros precisos</p>
      </div>

      {/* Barra de búsqueda principal */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex gap-4 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Buscar por nombre, NIF, contenido..."
              className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-base"
            />
          </div>
          <button
            onClick={buscar}
            disabled={loading}
            className="px-8 py-3 bg-linear-to-r from-orange-500 to-red-500 text-white rounded-lg hover:from-orange-600 hover:to-red-600 font-medium disabled:opacity-50 flex items-center gap-2 shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Buscando...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Buscar
              </>
            )}
          </button>
          <button
            onClick={() => setMostrarFiltros(!mostrarFiltros)}
            className={`px-6 py-3 border rounded-lg font-medium flex items-center gap-2 transition ${
              mostrarFiltros
                ? 'bg-primary-light border-orange-300 text-primary-hover'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <Filter className="w-5 h-5" />
            Filtros
            <ChevronDown className={`w-4 h-4 transition-transform ${mostrarFiltros ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* Panel de filtros expandible */}
        {mostrarFiltros && (
          <div className="pt-4 border-t border-gray-200 animate-in fade-in slide-in-from-top-2">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Fecha desde */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Fecha desde
                </label>
                <input
                  type="date"
                  value={filtros.fecha_desde}
                  onChange={(e) => setFiltros({ ...filtros, fecha_desde: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {/* Fecha hasta */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Calendar className="w-4 h-4 inline mr-1" />
                  Fecha hasta
                </label>
                <input
                  type="date"
                  value={filtros.fecha_hasta}
                  onChange={(e) => setFiltros({ ...filtros, fecha_hasta: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>

              {/* Categoría */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Categoría
                </label>
                <select
                  value={filtros.categoria}
                  onChange={(e) => setFiltros({ ...filtros, categoria: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Todas</option>
                  <option value="Por Procesar">Por Procesar</option>
                  <option value="Notificaciones">Notificaciones</option>
                  <option value="Embargos">Embargos</option>
                  <option value="Nóminas">Nóminas</option>
                  <option value="Finiquitos">Finiquitos</option>
                </select>
              </div>

              {/* Departamento */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Departamento
                </label>
                <select
                  value={filtros.departamento}
                  onChange={(e) => setFiltros({ ...filtros, departamento: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Todos</option>
                  <option value="Fiscal">Fiscal</option>
                  <option value="Laboral">Laboral</option>
                  <option value="Administrativo">Administrativo</option>
                  <option value="Jefatura">Jefatura</option>
                </select>
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={limpiarFiltros}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                Limpiar filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Resultados */}
      {resultados && (
        <div className="space-y-6">
          {/* Empresas */}
          {resultados.empresas.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-primary" />
                Empresas ({resultados.total_empresas})
              </h3>
              <div className="space-y-3">
                {resultados.empresas.map((empresa) => (
                  <div
                    key={empresa.id}
                    onClick={() => navigate(empresa.link)}
                    className="p-4 border border-gray-200 rounded-lg hover:bg-primary-light hover:border-orange-300 cursor-pointer transition group"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-semibold text-gray-900 group-hover:text-primary-hover">
                          {empresa.nombre}
                        </p>
                        <p className="text-sm text-gray-600 mt-1">
                          NIF: {empresa.nif}
                        </p>
                        {empresa.email && (
                          <p className="text-xs text-gray-500 mt-1">
                            {empresa.email}
                          </p>
                        )}
                      </div>
                      <Building2 className="w-8 h-8 text-gray-300 group-hover:text-orange-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documentos */}
          {resultados.documentos.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                Documentos ({resultados.total_documentos})
              </h3>
              <div className="space-y-3">
                {resultados.documentos.map((doc) => (
                  <div
                    key={doc.id}
                    onClick={() => navigate(doc.link)}
                    className="p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 cursor-pointer transition group"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 group-hover:text-blue-700">
                          {doc.nombre_archivo}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                            {doc.empresa}
                          </span>
                          <span className={`text-xs px-2 py-1 rounded ${
                            doc.categoria === 'Por Procesar'
                              ? 'bg-primary-light text-primary-hover'
                              : doc.categoria === 'Notificaciones'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-gray-100 text-gray-700'
                          }`}>
                            {doc.categoria}
                          </span>
                          {doc.estado_tarea && (
                            <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">
                              {doc.estado_tarea}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(doc.fecha_creacion).toLocaleDateString('es-ES')}
                        </p>
                      </div>
                      <FileText className="w-8 h-8 text-gray-300 group-hover:text-blue-400" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sin resultados */}
          {resultados.empresas.length === 0 && resultados.documentos.length === 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-12 text-center">
              <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-600 text-lg font-medium">
                No se encontraron resultados
              </p>
              <p className="text-gray-500 text-sm mt-2">
                Prueba con otros términos o ajusta los filtros
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}