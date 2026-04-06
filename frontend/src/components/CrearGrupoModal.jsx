// frontend/src/components/CrearGrupoModal.jsx
import React, { useState, useEffect } from 'react';
import { X, Building2 } from 'lucide-react';
import { useCrearGrupo } from '../hooks/useGruposDocumentos';
import axios from 'axios';

export default function CrearGrupoModal({ empresaId, onClose }) {
  const [formData, setFormData] = useState({
    nombre: '',
    descripcion: '',
    color: 'blue',
    empresa_id: empresaId || ''
  });
  const [empresas, setEmpresas] = useState([]);
  const [loadingEmpresas, setLoadingEmpresas] = useState(false);

  const crearGrupo = useCrearGrupo();

  const colores = [
    { value: 'blue', label: 'Azul', class: 'bg-blue-500' },
    { value: 'green', label: 'Verde', class: 'bg-green-500' },
    { value: 'red', label: 'Rojo', class: 'bg-red-500' },
    { value: 'yellow', label: 'Amarillo', class: 'bg-yellow-500' },
    { value: 'purple', label: 'Morado', class: 'bg-purple-500' },
    { value: 'pink', label: 'Rosa', class: 'bg-pink-500' },
    { value: 'orange', label: 'Naranja', class: 'bg-primary-light0' },
  ];

  // Cargar empresas si no se proporciona empresaId
  useEffect(() => {
    if (!empresaId) {
      const cargarEmpresas = async () => {
        setLoadingEmpresas(true);
        try {
          const res = await axios.get('/api/empresas', { withCredentials: true });
          if (res.data.success) {
            setEmpresas(res.data.empresas);
          }
        } catch (error) {
          console.error('Error cargando empresas:', error);
        } finally {
          setLoadingEmpresas(false);
        }
      };
      cargarEmpresas();
    }
  }, [empresaId]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    await crearGrupo.mutateAsync({
      nombre: formData.nombre,
      descripcion: formData.descripcion,
      color: formData.color,
      empresa_id: empresaId || parseInt(formData.empresa_id)
    });

    onClose();
    // Recargar página para ver el nuevo grupo
    window.location.reload();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Crear Nuevo Grupo
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X size={24} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Selector de Empresa (solo si no hay empresaId) */}
          {!empresaId && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Empresa *
              </label>
              {loadingEmpresas ? (
                <div className="text-sm text-gray-500">Cargando empresas...</div>
              ) : (
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <select
                    value={formData.empresa_id}
                    onChange={(e) => setFormData({ ...formData, empresa_id: e.target.value })}
                    className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                    required
                  >
                    <option value="">Selecciona una empresa</option>
                    {empresas.map((empresa) => (
                      <option key={empresa.id} value={empresa.id}>
                        {empresa.nombre}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* Nombre */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Nombre del Grupo *
            </label>
            <input
              type="text"
              value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Ej: Inspección Hacienda 2024"
              required
            />
          </div>

          {/* Descripción */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Descripción (opcional)
            </label>
            <textarea
              value={formData.descripcion}
              onChange={(e) => setFormData({ ...formData, descripcion: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Describe el propósito de este grupo..."
              rows={3}
            />
          </div>

          {/* Color */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Color
            </label>
            <div className="grid grid-cols-7 gap-2">
              {colores.map((color) => (
                <button
                  key={color.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, color: color.value })}
                  className={`h-10 rounded-lg ${color.class} ${formData.color === color.value
                      ? 'ring-2 ring-offset-2 ring-gray-900 dark:ring-white'
                      : 'opacity-60 hover:opacity-100'
                    } transition-all`}
                  title={color.label}
                />
              ))}
            </div>
          </div>

          {/* Botones */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={crearGrupo.isPending || (!empresaId && !formData.empresa_id)}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {crearGrupo.isPending ? 'Creando...' : 'Crear Grupo'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
