import React, { useState, useEffect } from 'react';
import { X, FileText, AlertTriangle, AlertCircle, RefreshCw, Send, CheckCircle2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

export default function ModalConfirmarDocumento({ 
  isOpen, 
  onClose, 
  archivoObj, 
  detectedType, 
  empresaDetectada, 
  onSuccess 
}) {
  const [fileUrl, setFileUrl] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(detectedType || 'alta_baja');
  const [procesando, setProcesando] = useState(false);

  const categoriasOptions = [
    { id: 'alta_baja', label: 'Altas / Bajas (TA/IDC)', endpoint: '/api/procesar-alta', fileParam: 'files' },
    { id: 'finiquito', label: 'Finiquitos', endpoint: '/api/finiquitos/upload', fileParam: 'files' },
    { id: 'contratos', label: 'Contratos', endpoint: '/api/contratos/upload', fileParam: 'files' },
    { id: 'nominas', label: 'Nóminas', endpoint: '/api/procesar-nominas', fileParam: 'file' },
    { id: 'impuestos', label: 'Impuestos', endpoint: '/api/procesar-impuestos', fileParam: 'files[]' },
    { id: 'certificados_180', label: 'Certificados 180', endpoint: '/api/procesar-modelo-180', fileParam: 'files' },
    { id: 'certificados_190', label: 'Certificados 190', endpoint: '/api/procesar-modelo-190', fileParam: 'files' }
  ];

  useEffect(() => {
    if (isOpen && archivoObj && archivoObj.file) {
      const url = URL.createObjectURL(archivoObj.file);
      setFileUrl(url);
      
      if (detectedType && categoriasOptions.find(c => c.id === detectedType)) {
        setSelectedCategory(detectedType);
      }
    }
    
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [isOpen, archivoObj, detectedType]);

  const handleProcesar = async () => {
    if (!selectedCategory) {
      toast.error('Selecciona una categoría para procesar el documento');
      return;
    }

    const categoryConf = categoriasOptions.find(c => c.id === selectedCategory);
    if (!categoryConf) return;

    setProcesando(true);
    const toastId = toast.loading('Re-procesando documento...');

    try {
      const formData = new FormData();
      formData.append(categoryConf.fileParam, archivoObj.file);
      formData.append('force', 'true');

      const response = await axios.post(categoryConf.endpoint, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.success) {
        toast.success(`Documento procesado correctamente como ${categoryConf.label}`, { id: toastId });
        if (onSuccess) {
          onSuccess(archivoObj.id, selectedCategory);
        }
        onClose();
      } else {
        throw new Error(response.data.message || 'Error al procesar el documento');
      }
    } catch (err) {
      const msg = err.response?.data?.message || err.message || 'Error desconocido';
      toast.error(`Error: ${msg}`, { id: toastId, duration: 5000 });
    } finally {
      setProcesando(false);
    }
  };

  if (!isOpen || !archivoObj) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />

      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-5xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-orange-50/50 rounded-t-2xl">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-orange-100 rounded-xl">
              <AlertTriangle className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Validación de Documento</h2>
              <p className="text-sm text-gray-600 mt-1">
                El sistema detectó que este documento podría no corresponder a la sección actual.
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-orange-100 rounded-full transition-colors"
          >
            <X className="w-6 h-6 text-gray-400 hover:text-gray-600" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden min-h-[500px]">
          
          {/* Left Column: PDF Preview */}
          <div className="w-full md:w-2/3 bg-gray-50 border-r border-gray-200 p-4 flex flex-col h-full">
            <div className="flex items-center gap-2 mb-3 px-2">
              <FileText className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700 truncate">
                {archivoObj.file?.name}
              </span>
              <span className="text-xs text-gray-400">
                ({(archivoObj.file?.size / 1024).toFixed(1)} KB)
              </span>
            </div>
            
            <div className="flex-1 rounded-xl flex flex-col overflow-hidden border border-gray-200 bg-white shadow-inner min-h-[50vh]">
              {fileUrl ? (
                <iframe 
                  src={fileUrl} 
                  className="flex-1 w-full h-full min-h-[50vh] border-none"
                  title="Previsualización PDF"
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-400 min-h-[50vh]">
                  Cargando previsualización...
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Controls */}
          <div className="w-full md:w-1/3 p-6 flex flex-col overflow-y-auto">
            
            <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 mb-6">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-blue-900 text-sm">Análisis del Sistema</h4>
                  <p className="text-sm text-blue-800 mt-2">
                    Parece ser un documento de tipo: <br/>
                    <span className="font-bold text-blue-900 bg-blue-100 px-2 py-1 rounded inline-block mt-1 uppercase text-xs">
                      {detectedType?.replace('_', ' ') || 'Desconocido'}
                    </span>
                  </p>
                  {empresaDetectada && (
                    <p className="text-xs text-blue-700 mt-2">
                      Empresa leída: <strong>{empresaDetectada}</strong>
                    </p>
                  )}
                </div>
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold text-gray-900 mb-3">
                Selecciona la categoría real
              </label>
              <div className="space-y-2">
                {categoriasOptions.map(cat => (
                  <label 
                    key={cat.id}
                    className={`flex items-center p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                      selectedCategory === cat.id 
                        ? 'border-orange-500 bg-orange-50' 
                        : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="categoria" 
                      value={cat.id} 
                      checked={selectedCategory === cat.id}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                      className="w-4 h-4 text-orange-600 focus:ring-orange-500 rounded-full border-gray-300"
                    />
                    <span className="ml-3 font-medium text-gray-900">{cat.label}</span>
                    {selectedCategory === cat.id && (
                      <CheckCircle2 className="w-5 h-5 ml-auto text-orange-600" />
                    )}
                  </label>
                ))}
              </div>
            </div>
            
            <div className="mt-auto pt-6">
              <button
                onClick={handleProcesar}
                disabled={procesando || !selectedCategory}
                className="w-full py-3.5 px-4 bg-gray-900 text-white rounded-xl font-medium hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {procesando ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Procesando...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Guardar como {categoriasOptions.find(c => c.id === selectedCategory)?.label || 'seleccionado'}
                  </>
                )}
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
