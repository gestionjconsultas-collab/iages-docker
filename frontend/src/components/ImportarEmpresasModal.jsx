import React, { useState } from 'react';
import axios from 'axios';
import { X, Upload, FileSpreadsheet, CheckCircle, XCircle, AlertCircle, Download, Eye, Check } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ImportarEmpresasModal({ isOpen, onClose, onSuccess }) {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [resultado, setResultado] = useState(null);
    const [detalles, setDetalles] = useState(null);
    const [dragActive, setDragActive] = useState(false);

    // Estados para preview
    const [showPreview, setShowPreview] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [loadingPreview, setLoadingPreview] = useState(false);

    // Estados para conflictos
    const [resoluciones, setResoluciones] = useState({});
    const [expandedRows, setExpandedRows] = useState({});

    if (!isOpen) return null;

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    };

    const handleFileSelect = (selectedFile) => {
        // Validar tamaño (5MB max)
        if (selectedFile.size > 5 * 1024 * 1024) {
            toast.error('Archivo muy grande. Máximo 5MB');
            return;
        }

        // Validar extensión
        const ext = selectedFile.name.split('.').pop().toLowerCase();
        if (!['xlsx', 'csv'].includes(ext)) {
            toast.error('Formato no soportado. Use .xlsx o .csv');
            return;
        }

        setFile(selectedFile);
        setResultado(null);
        setShowPreview(false);
        setPreviewData(null);
        setResoluciones({});
        setExpandedRows({});
    };

    // Nueva función: Previsualizar datos
    const handlePreview = async () => {
        if (!file) {
            toast.error('Selecciona un archivo primero');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        setLoadingPreview(true);
        try {
            const res = await axios.post('/api/admin/empresas/preview-excel', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                withCredentials: true
            });

            console.log('📊 Preview recibido:', res.data);

            if (res.data.success) {
                setPreviewData(res.data);
                
                // Pre-inicializar resoluciones por defecto a 'nuevo'
                const iniciales = {};
                res.data.datos.forEach(row => {
                    if (row.es_actualizacion && row.conflictos?.length > 0) {
                        iniciales[row.fila] = {};
                        row.conflictos.forEach(c => {
                            iniciales[row.fila][c.campo] = 'nuevo';
                        });
                    }
                });
                setResoluciones(iniciales);
                setExpandedRows({});
                
                setShowPreview(true);
                toast.success(`Vista previa generada: ${res.data.validos} válidos, ${res.data.invalidos} con errores`);
            } else {
                toast.error(res.data.error || 'Error generando vista previa');
            }
        } catch (err) {
            console.error('Error en preview:', err);
            toast.error('Error: ' + (err.response?.data?.error || err.message));
        } finally {
            setLoadingPreview(false);
        }
    };

    // Función actualizada: Confirmar importación
    const handleConfirmarImport = async () => {
        if (!file) {
            toast.error('No hay archivo seleccionado');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('resoluciones', JSON.stringify(resoluciones));

        setUploading(true);
        try {
            const res = await axios.post('/api/admin/empresas/importar-excel', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                },
                withCredentials: true
            });

            console.log('📊 Respuesta del servidor:', res.data);

            if (res.data.success) {
                setResultado({
                    exitosas: res.data.exitosas || 0,
                    actualizadas: res.data.actualizadas || 0,
                    duplicadas: res.data.duplicadas || 0,
                    errores: res.data.errores || 0
                });

                setDetalles({
                    exitosos: res.data.detalles?.exitosos || [],
                    actualizados: res.data.detalles?.actualizados || [],
                    duplicados: res.data.detalles?.duplicados || [],
                    errores: res.data.detalles?.errores || []
                });

                toast.success(`✅ Importación completada: ${res.data.exitosas} creadas, ${res.data.actualizadas || 0} actualizadas`);

                // Ocultar preview y mostrar resultado
                setShowPreview(false);

                // Recargar lista de empresas
                if (onSuccess) {
                    onSuccess();
                }
            } else {
                toast.error(res.data.error || 'Error en la importación');
            }
        } catch (err) {
            console.error('Error importando:', err);
            toast.error('Error: ' + (err.response?.data?.error || err.message));
        } finally {
            setUploading(false);
        }
    };

    const handleDescargarPlantilla = async () => {
        try {
            const res = await axios.get('/api/admin/empresas/plantilla-excel', {
                responseType: 'blob',
                withCredentials: true
            });

            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'plantilla_empresas.xlsx');
            document.body.appendChild(link);
            link.click();
            link.remove();

            toast.success('Plantilla descargada');
        } catch (err) {
            toast.error('Error descargando plantilla');
        }
    };

    const handleClose = () => {
        setFile(null);
        setResultado(null);
        setShowPreview(false);
        setPreviewData(null);
        onClose();
    };

    const handleCancelarPreview = () => {
        setShowPreview(false);
        setPreviewData(null);
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">

                {/* Header */}
                <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-6 py-4 text-white">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <FileSpreadsheet className="w-6 h-6" />
                            <h2 className="text-xl font-bold">
                                {showPreview ? 'Vista Previa - Importar Empresas' : 'Importar Empresas desde Excel'}
                            </h2>
                        </div>
                        <button
                            onClick={handleClose}
                            className="p-2 hover:bg-white hover:bg-opacity-20 rounded-lg transition-colors"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4">

                    {/* Instrucciones - Solo mostrar si no hay preview ni resultado */}
                    {!showPreview && !resultado && (
                        <>
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h3 className="font-semibold text-blue-900 mb-2">Formato del archivo:</h3>
                                <ul className="text-sm text-blue-800 space-y-1">
                                    <li>• Columnas (19): <strong>Codigo Empresa</strong>, <strong>NIF-NIE-CIF</strong>, <strong>Nombre Sociedad</strong>, <strong>Email</strong>, <strong>Telefono</strong>, <strong>Nombre Administrador</strong>, <strong>Apellido Administrador</strong>, <strong>NIF-NIE-CIF ADMINISTRADOR</strong>, <strong>Provincia</strong>, <strong>Municipio</strong>, <strong>Código Postal</strong>, <strong>Dirección</strong>, <strong>Dirección Centros Trabajo</strong>, <strong>Cuenta Cotizacion</strong>, <strong>Convenio Colectivo Número</strong>, <strong>Convenio Colectivo Nombre</strong>, <strong>EPIGRAFE IAE</strong>, <strong>CNAE 2009</strong>, <strong>CNAE 2025</strong></li>
                                    <li>• Campos múltiples (separar con <strong>;</strong>): Administradores (Nombre, Apellido, NIF), Direcciones (Centros), EPIGRAFE IAE, CNAE.</li>
                                    <li>• Formatos soportados: .xlsx, .csv</li>
                                    <li>• Máximo 500 empresas por archivo</li>
                                </ul>
                                <button
                                    onClick={handleDescargarPlantilla}
                                    className="mt-3 flex items-center gap-2 px-3 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                    <Download className="w-4 h-4" />
                                    Descargar Plantilla Excel (19 columnas)
                                </button>
                            </div>

                            {/* Drag & Drop Area */}
                            <div
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-300 bg-gray-50'
                                    }`}
                            >
                                <Upload className={`w-12 h-12 mx-auto mb-4 ${dragActive ? 'text-green-600' : 'text-gray-400'}`} />

                                {file ? (
                                    <div className="space-y-2">
                                        <p className="text-green-600 font-semibold">{file.name}</p>
                                        <p className="text-sm text-gray-600">
                                            {(file.size / 1024).toFixed(2)} KB
                                        </p>
                                        <button
                                            onClick={() => setFile(null)}
                                            className="text-sm text-red-600 hover:text-red-700"
                                        >
                                            Cambiar archivo
                                        </button>
                                    </div>
                                ) : (
                                    <div>
                                        <p className="text-gray-700 mb-2">
                                            Arrastra un archivo aquí o
                                        </p>
                                        <label className="inline-block px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 cursor-pointer transition-colors">
                                            Seleccionar Archivo
                                            <input
                                                type="file"
                                                accept=".xlsx,.csv"
                                                onChange={handleFileChange}
                                                className="hidden"
                                            />
                                        </label>
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* Vista Previa */}
                    {showPreview && previewData && (
                        <div className="space-y-4">
                            {/* Resumen */}
                            <div className="bg-gray-50 rounded-lg p-4">
                                <h3 className="font-semibold text-gray-900 mb-3">Resumen de Vista Previa:</h3>
                                <div className="grid grid-cols-3 gap-3">
                                    <div className="bg-green-100 border border-green-300 rounded-lg p-3 text-center">
                                        <CheckCircle className="w-6 h-6 text-green-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-green-700">{previewData.validos}</p>
                                        <p className="text-xs text-green-600">Válidos</p>
                                    </div>
                                    <div className="bg-red-100 border border-red-300 rounded-lg p-3 text-center">
                                        <XCircle className="w-6 h-6 text-red-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-red-700">{previewData.invalidos}</p>
                                        <p className="text-xs text-red-600">Con Errores</p>
                                    </div>
                                    <div className="bg-blue-100 border border-blue-300 rounded-lg p-3 text-center">
                                        <FileSpreadsheet className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-blue-700">{previewData.total}</p>
                                        <p className="text-xs text-blue-600">Total</p>
                                    </div>
                                </div>
                            </div>

                            {/* Tabla de Preview */}
                            <div className="border border-gray-200 rounded-lg overflow-hidden">
                                <div className="overflow-x-auto max-h-96">
                                    <table className="w-full text-sm">
                                        <thead className="bg-gray-100 sticky top-0">
                                            <tr>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Fila</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Estado</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Código</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">NIF</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Nombre</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Email</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Teléfono</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Administradores</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Provincia</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Convenio</th>
                                                <th className="px-3 py-2 text-left font-semibold text-gray-700">Errores/Advertencias</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {previewData.datos.map((row, idx) => (
                                                <React.Fragment key={idx}>
                                                <tr
                                                    className={`border-t ${row.validacion.valido ? (row.es_actualizacion ? 'bg-blue-50' : 'bg-white') : 'bg-red-50'}`}
                                                >
                                                    <td className="px-3 py-2 text-gray-600">
                                                        <div className="font-semibold">{row.fila}</div>
                                                        {row.conflictos?.length > 0 && (
                                                            <button 
                                                                onClick={() => setExpandedRows({...expandedRows, [row.fila]: !expandedRows[row.fila]})}
                                                                className="mt-1 block text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded border border-yellow-300 hover:bg-yellow-200"
                                                            >
                                                                {expandedRows[row.fila] ? 'Ocultar' : `Resolver ${row.conflictos.length}`}
                                                            </button>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-center text-xl">
                                                        {row.validacion.valido ? (
                                                            row.es_actualizacion ? 
                                                            <span title="Se actualizará">🔄</span> :
                                                            <span title="Nueva">✅</span>
                                                        ) : (
                                                            <span title="Error">❌</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-gray-800">{row.codigo_empresa || '-'}</td>
                                                    <td className="px-3 py-2 text-gray-800 font-mono text-xs">{row.nif}</td>
                                                    <td className="px-3 py-2 text-gray-800">{row.nombre}</td>
                                                    <td className="px-3 py-2 text-gray-600 text-xs">{row.email || '-'}</td>
                                                    <td className="px-3 py-2 text-gray-600">{row.telefono || '-'}</td>
                                                    <td className="px-3 py-2">
                                                        {row.administradores && row.administradores.length > 0 ? (
                                                            <div className="flex flex-col gap-1 max-w-[150px] max-h-[100px] overflow-y-auto">
                                                                {row.administradores.map((a, i) => (
                                                                    <div key={i} className="text-xs bg-gray-100 p-1 rounded">
                                                                        <strong>{a.nombre}</strong> {a.cif && `(${a.cif})`}
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        ) : (
                                                            <span className="text-gray-400 text-sm">-</span>
                                                        )}
                                                    </td>
                                                    <td className="px-3 py-2 text-gray-600 text-xs">{row.provincia || '-'}</td>
                                                    <td className="px-3 py-2 text-gray-600 text-xs">{row.convenio_nombre || '-'}</td>
                                                    <td className="px-3 py-2">
                                                        {row.validacion.errores.length > 0 && (
                                                            <div className="text-xs text-red-600 font-semibold mb-1">
                                                                {row.validacion.errores.join(', ')}
                                                            </div>
                                                        )}
                                                        {row.validacion.advertencias.length > 0 && (
                                                            <div className="text-xs text-yellow-600">
                                                                {row.validacion.advertencias.join(', ')}
                                                            </div>
                                                        )}
                                                    </td>
                                                </tr>
                                                
                                                {/* Expanded Conflict Row */}
                                                {expandedRows[row.fila] && row.conflictos?.length > 0 && (
                                                    <tr>
                                                        <td colSpan="11" className="bg-gradient-to-r from-yellow-50 to-orange-50 p-4 border-b border-yellow-200">
                                                            <h4 className="font-semibold text-yellow-800 mb-3 flex items-center gap-2">
                                                                <AlertCircle className="w-4 h-4" />
                                                                Resolver Conflictos de Actualización (Elige qué dato conservar)
                                                            </h4>
                                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                                {row.conflictos.map((c, i) => (
                                                                    <div key={i} className="bg-white p-3 rounded-lg border border-yellow-300 shadow-sm flex flex-col justify-between">
                                                                        <div className="font-bold text-sm text-gray-800 mb-3 border-b pb-2">{c.label}</div>
                                                                        <div className="flex flex-col gap-2 relative">
                                                                            
                                                                            {/* Opción Mantener (BD) */}
                                                                            <label className={`flex items-start gap-3 p-2 rounded-md cursor-pointer border transition-colors ${resoluciones[row.fila]?.[c.campo] === 'actual' ? 'bg-blue-50 border-blue-400 shadow-sm' : 'border-gray-200 hover:bg-gray-50'}`}>
                                                                                <input 
                                                                                    type="radio" 
                                                                                    name={`res_${row.fila}_${c.campo}`}
                                                                                    checked={resoluciones[row.fila]?.[c.campo] === 'actual'}
                                                                                    onChange={() => setResoluciones({...resoluciones, [row.fila]: {...resoluciones[row.fila], [c.campo]: 'actual'}})}
                                                                                    className="mt-1 flex-shrink-0"
                                                                                />
                                                                                <div className="break-all w-full">
                                                                                    <span className="block text-xs font-bold text-blue-700 uppercase tracking-wide mb-1">Mantener Actual en BD</span>
                                                                                    <span className="text-sm text-gray-700">{c.valor_actual || <span className="text-gray-400 italic">(Dato Vacío)</span>}</span>
                                                                                </div>
                                                                            </label>

                                                                            {/* Opción Sobrescribir (Excel) */}
                                                                            <label className={`flex items-start gap-3 p-2 rounded-md cursor-pointer border transition-colors ${resoluciones[row.fila]?.[c.campo] === 'nuevo' ? 'bg-green-50 border-green-400 shadow-sm' : 'border-gray-200 hover:bg-gray-50'}`}>
                                                                                <input 
                                                                                    type="radio" 
                                                                                    name={`res_${row.fila}_${c.campo}`}
                                                                                    checked={resoluciones[row.fila]?.[c.campo] === 'nuevo'}
                                                                                    onChange={() => setResoluciones({...resoluciones, [row.fila]: {...resoluciones[row.fila], [c.campo]: 'nuevo'}})}
                                                                                    className="mt-1 flex-shrink-0"
                                                                                />
                                                                                <div className="break-all w-full">
                                                                                    <span className="block text-xs font-bold text-green-700 uppercase tracking-wide mb-1">Sobrescribir con Excel</span>
                                                                                    <span className="text-sm text-gray-900 font-medium">{c.valor_nuevo || <span className="text-gray-400 italic">(Dato Vacío)</span>}</span>
                                                                                </div>
                                                                            </label>

                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                                </React.Fragment>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Resultado */}
                    {resultado && (
                        <div className="space-y-4">
                            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                                <h3 className="font-semibold text-gray-900">Resumen de Importación:</h3>

                                <div className="grid grid-cols-4 gap-3">
                                    <div className="bg-green-100 border border-green-300 rounded-lg p-3 text-center">
                                        <CheckCircle className="w-6 h-6 text-green-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-green-700">{resultado.exitosas || 0}</p>
                                        <p className="text-xs text-green-600">Nuevas</p>
                                    </div>
                                    
                                    <div className="bg-blue-100 border border-blue-300 rounded-lg p-3 text-center">
                                        <Check className="w-6 h-6 text-blue-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-blue-700">{resultado.actualizadas || 0}</p>
                                        <p className="text-xs text-blue-600">Actualizadas</p>
                                    </div>

                                    <div className="bg-yellow-100 border border-yellow-300 rounded-lg p-3 text-center">
                                        <AlertCircle className="w-6 h-6 text-yellow-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-yellow-700">{resultado.duplicadas || 0}</p>
                                        <p className="text-xs text-yellow-600">Rechazadas (Duplicadas)</p>
                                    </div>

                                    <div className="bg-red-100 border border-red-300 rounded-lg p-3 text-center">
                                        <XCircle className="w-6 h-6 text-red-600 mx-auto mb-1" />
                                        <p className="text-2xl font-bold text-red-700">{resultado.errores || 0}</p>
                                        <p className="text-xs text-red-600">Errores</p>
                                    </div>
                                </div>

                                {/* Detalles de errores */}
                                {detalles?.errores && detalles.errores.length > 0 && (
                                    <div className="mt-4">
                                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Errores encontrados:</h4>
                                        <div className="bg-white border border-red-200 rounded-lg p-3 max-h-40 overflow-y-auto">
                                            {detalles.errores.map((error, idx) => (
                                                <div key={idx} className="text-sm text-red-700 py-1">
                                                    Fila {error.fila}: {error.error} ({error.nif})
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={() => {
                                    setResultado(null);
                                    setFile(null);
                                }}
                                className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                            >
                                Importar Otro Archivo
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer */}
                {!resultado && (
                    <div className="bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-between">
                        <button
                            onClick={showPreview ? handleCancelarPreview : handleClose}
                            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            {showPreview ? 'Volver' : 'Cancelar'}
                        </button>

                        <div className="flex gap-3">
                            {!showPreview && (
                                <button
                                    onClick={handlePreview}
                                    disabled={!file || loadingPreview}
                                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                                >
                                    {loadingPreview ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Cargando...
                                        </>
                                    ) : (
                                        <>
                                            <Eye className="w-4 h-4" />
                                            Previsualizar Datos
                                        </>
                                    )}
                                </button>
                            )}

                            {showPreview && (
                                <button
                                    onClick={handleConfirmarImport}
                                    disabled={uploading || previewData?.validos === 0}
                                    className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
                                >
                                    {uploading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Importando...
                                        </>
                                    ) : (
                                        <>
                                            <Check className="w-4 h-4" />
                                            Confirmar Importación ({previewData?.validos} empresas)
                                        </>
                                    )}
                                </button>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
