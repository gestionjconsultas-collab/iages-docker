// frontend/src/components/SuperAdmin/VersionManager.jsx
import React, { useState, useEffect } from 'react';
import {
    Save, RefreshCw, UploadCloud, Monitor, Navigation, AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL,
    withCredentials: true
});

const VersionManager = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [exeFile, setExeFile] = useState(null);

    const [config, setConfig] = useState({
        conecta_version: '',
        conecta_url: '',
        conecta_notes: '',
        conecta_mandatory: false,
        conecta_sha256: '',
        webapp_version: ''
    });

    useEffect(() => {
        fetchConfig();
    }, []);

    const fetchConfig = async () => {
        try {
            setLoading(true);
            const response = await api.get('/api/super-admin/version-config');
            if (response.data.success) {
                setConfig(response.data.config);
            }
        } catch (error) {
            console.error('Error fetching version config:', error);
            toast.error('Error al cargar la configuración de versiones');
        } finally {
            setLoading(false);
        }
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setConfig(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleFileChange = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            const file = e.target.files[0];
            if (!file.name.endsWith('.exe')) {
                toast.error('El archivo debe ser un ejecutable (.exe)');
                e.target.value = '';
                return;
            }
            setExeFile(file);
        }
    };

    const handleUploadExe = async () => {
        if (!exeFile) return;

        const formData = new FormData();
        formData.append('file', exeFile);

        try {
            setUploading(true);
            const response = await api.post('/api/super-admin/upload-conecta-exe', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            if (response.data.success) {
                // Actualizar la URL y el hash en la configuración
                setConfig(prev => ({
                    ...prev,
                    conecta_url: response.data.url,
                    conecta_sha256: response.data.sha256 || prev.conecta_sha256
                }));
                toast.success('Instalador subido correctamente. La URL se ha actualizado.');
                setExeFile(null);
                // Reset file input
                const fileInput = document.getElementById('exe-upload');
                if (fileInput) fileInput.value = '';
            }
        } catch (error) {
            console.error('Error uploading exe:', error);
            toast.error(error.response?.data?.error || 'Error al subir el instalador');
        } finally {
            setUploading(false);
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        try {
            setSaving(true);
            const response = await api.post('/api/super-admin/version-config', config);
            if (response.data.success) {
                let msg = 'Configuración actualizada correctamente.';
                if (response.data.sw_updated) {
                    msg += ' El Service Worker ha sido inyectado con la nueva versión.';
                }
                toast.success(msg);
            }
        } catch (error) {
            console.error('Error saving version config:', error);
            toast.error('Error al guardar la configuración');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
        );
    }

    return (
        <div className="p-6 max-w-5xl mx-auto space-y-6">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                    <UploadCloud className="w-8 h-8 text-blue-600" />
                    Gestor Dinámico de Versiones
                </h1>
                <p className="text-gray-500 mt-2">
                    Administra las versiones de la Aplicación de Escritorio (Conecta) y de la PWA (Service Worker) sin necesidad de modificar el código fuente.
                </p>
            </div>

            <form onSubmit={handleSave} className="space-y-6">

                {/* ---------- WEB APP (PWA) ---------- */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="bg-blue-50/50 p-4 border-b border-gray-100 flex items-center gap-2">
                        <Navigation className="w-5 h-5 text-blue-600" />
                        <h2 className="text-lg font-semibold text-gray-800">Aplicación Web (PWA)</h2>
                    </div>
                    <div className="p-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Versión de Caché (sw.js)
                                </label>
                                <input
                                    type="text"
                                    name="webapp_version"
                                    value={config.webapp_version}
                                    onChange={handleChange}
                                    placeholder="Ej: 1.4.7"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    required
                                />
                                <p className="mt-2 text-xs text-gray-500">
                                    Al incrementar esta versión, los navegadores de los clientes detectarán el cambio e instalarán la versión más reciente del sistema automáticamente.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* ---------- DESKTOP APP (CONECTA) ---------- */}
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="bg-purple-50/50 p-4 border-b border-gray-100 flex items-center gap-2">
                        <Monitor className="w-5 h-5 text-purple-600" />
                        <h2 className="text-lg font-semibold text-gray-800">Aplicación de Escritorio (Conecta)</h2>
                    </div>
                    <div className="p-6 space-y-6">
                        {/* SECCIÓN DE CARGA DEL INSTALADOR */}
                        <div className="bg-gray-50 p-5 rounded-lg border border-gray-200">
                            <h3 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                <UploadCloud className="w-4 h-4 text-purple-600" />
                                Subir nuevo instalador (.exe)
                            </h3>
                            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                                <input
                                    type="file"
                                    id="exe-upload"
                                    accept=".exe"
                                    onChange={handleFileChange}
                                    className="block w-full text-sm text-gray-500
                                      file:mr-4 file:py-2 file:px-4
                                      file:rounded-full file:border-0
                                      file:text-sm file:font-semibold
                                      file:bg-purple-50 file:text-purple-700
                                      hover:file:bg-purple-100 cursor-pointer"
                                />
                                <button
                                    type="button"
                                    onClick={handleUploadExe}
                                    disabled={!exeFile || uploading}
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors whitespace-nowrap flex items-center gap-2"
                                >
                                    {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                                    Subir Instalador
                                </button>
                            </div>
                            <p className="text-xs text-gray-500 mt-2">
                                Al subir el archivo, el sistema actualizará automáticamente la URL de descarga y el hash SHA256 (si está disponible). Recuerde hacer clic en "Guardar Configuraciones" después.
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Versión de Lanzamiento
                                </label>
                                <input
                                    type="text"
                                    name="conecta_version"
                                    value={config.conecta_version}
                                    onChange={handleChange}
                                    placeholder="Ej: 1.2.0"
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                                    required
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    URL del Instalador (Setup .exe)
                                </label>
                                <input
                                    type="url"
                                    name="conecta_url"
                                    value={config.conecta_url}
                                    onChange={handleChange}
                                    placeholder="https://..."
                                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Hash SHA256 (Opcional, autocompletado al subir archivo)
                            </label>
                            <input
                                type="text"
                                name="conecta_sha256"
                                value={config.conecta_sha256 || ''}
                                onChange={handleChange}
                                placeholder="8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 font-mono text-xs"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Notas de la Versión (Changelog)
                            </label>
                            <textarea
                                name="conecta_notes"
                                value={config.conecta_notes}
                                onChange={handleChange}
                                rows="3"
                                placeholder="- Corrección de errores\n- Nuevas características..."
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                            ></textarea>
                            <p className="mt-2 text-xs text-gray-500">
                                Estas notas se mostrarán en la ventana emergente de actualización de Conecta.
                            </p>
                        </div>

                        <div className="flex items-center gap-3 bg-red-50 p-4 rounded-lg border border-red-100">
                            <input
                                type="checkbox"
                                id="conecta_mandatory"
                                name="conecta_mandatory"
                                checked={config.conecta_mandatory}
                                onChange={handleChange}
                                className="w-5 h-5 text-red-600 border-gray-300 rounded focus:ring-red-500"
                            />
                            <label htmlFor="conecta_mandatory" className="flex flex-col">
                                <span className="text-sm font-bold text-red-800 flex items-center gap-1">
                                    <AlertCircle className="w-4 h-4" />
                                    Actualización Obligatoria
                                </span>
                                <span className="text-xs text-red-600">
                                    Si está marcado, obligará a los usuarios a actualizar para poder seguir usando Conecta.
                                </span>
                            </label>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-4 border-t">
                    <button
                        type="submit"
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50"
                    >
                        {saving ? (
                            <RefreshCw className="w-5 h-5 animate-spin" />
                        ) : (
                            <Save className="w-5 h-5" />
                        )}
                        Guardar Configuraciones
                    </button>
                </div>
            </form>
        </div>
    );
};

export default VersionManager;
