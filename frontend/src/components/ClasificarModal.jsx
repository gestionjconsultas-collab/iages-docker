// frontend/src/components/ClasificarModal.jsx
import React, { useState, useEffect } from 'react';
import { X, FolderInput, Loader2, FileText, BrainCircuit, Plus, Settings } from 'lucide-react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';
import MobilePDFViewer from './MobilePDFViewer';

const categorias = [
  { value: "Notificaciones", label: "Notificaciones" },
  { value: "Nóminas", label: "Nóminas" },
  { value: "Impuestos", label: "Impuestos" },
  { value: "Seguros Sociales", label: "Seguros Sociales" },
  { value: "Contratos", label: "Contratos Trabajo" },
  { value: "Finiquitos", label: "Finiquitos" },
  { value: "Certificados de Retenciones 180", label: "Cert. Retenciones 180" },
  { value: "Certificados de Retenciones 190", label: "Cert. Retenciones 190" },
  { value: "Inspecciones", label: "Inspecciones" },
  { value: "Aplazamiento", label: "Aplazamiento" },
  { value: "Documentos Empresa", label: "Documentos Empresa" },
  { value: "Accidentes de Trabajo", label: "Accidentes de Trabajo", disabled: true }
];

export default function ClasificarModal({ documento, onClose, onClasificado }) {
  useEscapeKey(onClose);
  const [destino, setDestino] = useState('Notificaciones');
  const [plantillaSeleccionada, setPlantillaSeleccionada] = useState('notificacion_generica');
  const [loading, setLoading] = useState(false);

  // Estado para las plantillas dinámicas
  const [listaPlantillas, setListaPlantillas] = useState([]);
  const [loadingPlantillas, setLoadingPlantillas] = useState(true);

  const navigate = useNavigate();

  // URL del PDF
  const pdfUrl = `/api/documentos/${documento.id}/archivo`;

  // Cargar plantillas desde la Base de Datos al abrir el modal
  useEffect(() => {
    const fetchPlantillas = async () => {
      try {
        const res = await axios.get('/api/plantillas', { withCredentials: true });
        if (res.data.success) {
          setListaPlantillas(res.data.plantillas);
        }
      } catch (err) {
        console.error("Error cargando plantillas", err);
        // Fallback visual si falla la API
        setListaPlantillas([
          { codigo: 'notificacion_generica', nombre: 'Notificación Genérica' }
        ]);
      } finally {
        setLoadingPlantillas(false);
      }
    };
    fetchPlantillas();
  }, []);

  const handleMover = async () => {
    setLoading(true);
    try {
      const res = await axios.post(`/api/documentos/${documento.id}/mover`,
        {
          categoria_destino: destino,
          tipo_documento_asignado: plantillaSeleccionada
        },
        { withCredentials: true }
      );

      if (res.data.success) {
        onClasificado();
        onClose();
      }
    } catch (err) {
      toast.error("Error al mover: " + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  const irAGestionPlantillas = () => {
    // Cerramos el modal y navegamos a la gestión
    onClose();
    navigate('/plantillas');
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-light rounded-lg">
              <FolderInput className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Clasificar Documento</h3>
              <p className="text-xs text-gray-500 truncate max-w-md">{documento.nombre_archivo}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Body: Pantalla Dividida */}
        <div className="flex-1 flex overflow-hidden">

          {/* Izquierda: Visor PDF */}
          <div className="w-1/2 bg-gray-100 border-r border-gray-200 h-full">
            <MobilePDFViewer documentId={documento.id} />
          </div>

          {/* Derecha: Formulario */}
          <div className="w-1/2 p-8 overflow-y-auto bg-white">
            <div className="max-w-md mx-auto space-y-8">

              {/* 1. Selección de Carpeta */}
              <div>
                <label className="text-sm font-bold text-gray-700 mb-2 flex items-center gap-2">
                  <FolderInput className="w-4 h-4 text-blue-600" />
                  1. Carpeta de Destino
                </label>
                <select
                  value={destino}
                  onChange={(e) => setDestino(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg bg-gray-50 focus:ring-2 focus:ring-primary"
                >
                  {categorias.map(c => <option key={c.value} value={c.value} disabled={c.disabled}>{c.label} {c.disabled ? '(Próximamente)' : ''}</option>)}
                </select>
              </div>

              <hr className="border-gray-100" />

              {/* 2. Selección de Plantilla IA */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-sm font-bold text-gray-700 flex items-center gap-2">
                    <BrainCircuit className="w-4 h-4 text-purple-600" />
                    2. Plantilla de IA
                  </label>

                  {/* --- BOTÓN NUEVO PARA CREAR PLANTILLA --- */}
                  <button
                    onClick={irAGestionPlantillas}
                    className="text-xs flex items-center gap-1 text-primary hover:text-orange-800 font-semibold border border-primary-light px-2 py-1 rounded hover:bg-primary-light transition-colors"
                    title="Ir al gestor de plantillas"
                  >
                    <Plus className="w-3 h-3" /> Nueva / Gestionar
                  </button>
                  {/* ---------------------------------------- */}
                </div>

                <p className="text-xs text-gray-500 mb-3">Selecciona qué datos extraer.</p>

                {loadingPlantillas ? (
                  <div className="flex justify-center py-4"><Loader2 className="w-6 h-6 animate-spin text-purple-500" /></div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                    {listaPlantillas.map((p) => (
                      <label
                        key={p.id}
                        className={`
                            flex items-center p-3 border rounded-lg cursor-pointer transition-all
                            ${plantillaSeleccionada === p.codigo
                            ? 'border-purple-500 bg-purple-50 ring-1 ring-purple-500'
                            : 'border-gray-200 hover:border-purple-200 hover:bg-gray-50'}
                          `}
                      >
                        <input
                          type="radio"
                          name="plantilla"
                          value={p.codigo}
                          checked={plantillaSeleccionada === p.codigo}
                          onChange={(e) => setPlantillaSeleccionada(e.target.value)}
                          className="w-4 h-4 text-purple-600 focus:ring-purple-500 border-gray-300"
                        />
                        <div className="ml-3">
                          <span className="block text-sm font-medium text-gray-700">{p.nombre}</span>
                          {p.descripcion && <span className="block text-xs text-gray-400">{p.descripcion}</span>}
                        </div>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Acciones */}
              <div className="pt-6">
                <button
                  onClick={handleMover}
                  disabled={loading}
                  className="w-full py-3 px-4 bg-linear-to-r from-orange-600 to-red-600 text-white rounded-lg 
                           hover:from-orange-700 hover:to-red-700 font-semibold shadow-md hover:shadow-lg 
                           transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
                  Confirmar y Mover
                </button>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}