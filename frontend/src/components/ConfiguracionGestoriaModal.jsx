import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BACKEND_URL } from '../utils/urls';
import toast from 'react-hot-toast';
import {
    X, Save, Upload, Palette, Phone, Mail, MapPin,
    Facebook, Linkedin, Code, Eye, AlertCircle, Image as ImageIcon
} from 'lucide-react';

export default function ConfiguracionGestoriaModal({ gestoria, onClose, onSave }) {
    const [activeTab, setActiveTab] = useState('branding');
    const [config, setConfig] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [validationErrors, setValidationErrors] = useState([]);

    // Cargar configuración actual
    useEffect(() => {
        loadConfig();
    }, [gestoria.id]);

    const loadConfig = async () => {
        try {
            const res = await axios.get(`/api/admin/gestorias/${gestoria.id}/configuracion`, {
                withCredentials: true
            });
            setConfig(res.data.configuracion);
        } catch (error) {
            toast.error('Error al cargar configuración');
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleColorChange = (colorKey, value) => {
        setConfig(prev => ({
            ...prev,
            branding: {
                ...prev.branding,
                colores: {
                    ...prev.branding.colores,
                    [colorKey]: value
                }
            }
        }));
    };

    const handleContactChange = (field, value) => {
        setConfig(prev => ({
            ...prev,
            contacto: {
                ...prev.contacto,
                [field]: value
            }
        }));
    };

    const handleSocialChange = (platform, value) => {
        setConfig(prev => ({
            ...prev,
            contacto: {
                ...prev.contacto,
                redes_sociales: {
                    ...prev.contacto.redes_sociales,
                    [platform]: value
                }
            }
        }));
    };

    const handleFileUpload = async (type) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = type === 'logo' ? 'image/png,image/jpeg,image/svg+xml' : '.ico,image/png';

        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            setUploading(true);
            try {
                const endpoint = type === 'logo' ? 'upload-logo' : 'upload-favicon';
                const res = await axios.post(
                    `/api/admin/gestorias/${gestoria.id}/${endpoint}`,
                    formData,
                    {
                        withCredentials: true,
                        headers: { 'Content-Type': 'multipart/form-data' }
                    }
                );

                const urlKey = type === 'logo' ? 'logo_url' : 'favicon_url';
                setConfig(prev => ({
                    ...prev,
                    branding: {
                        ...prev.branding,
                        [urlKey]: res.data[urlKey]
                    }
                }));

                toast.success(`${type === 'logo' ? 'Logo' : 'Favicon'} subido correctamente`);
            } catch (error) {
                toast.error(error.response?.data?.error || 'Error al subir archivo');
            } finally {
                setUploading(false);
            }
        };

        input.click();
    };

    const handleSave = async () => {
        setSaving(true);
        setValidationErrors([]);

        try {
            const res = await axios.put(
                `/api/admin/gestorias/${gestoria.id}/configuracion`,
                { configuracion: config },
                { withCredentials: true }
            );

            toast.success('Configuración guardada correctamente');
            onSave(res.data.configuracion);
            onClose();
        } catch (error) {
            if (error.response?.data?.validation_errors) {
                setValidationErrors(error.response.data.validation_errors);
                toast.error('Hay errores de validación');
            } else {
                toast.error('Error al guardar configuración');
            }
        } finally {
            setSaving(false);
        }
    };

    if (loading || !config) {
        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-xl p-8">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
                    <p className="mt-4 text-gray-600">Cargando configuración...</p>
                </div>
            </div>
        );
    }

    const tabs = [
        { id: 'branding', label: 'Branding', icon: Palette },
        { id: 'contacto', label: 'Contacto', icon: Phone },
        { id: 'avanzado', label: 'Avanzado', icon: Code },
        { id: 'preview', label: 'Vista Previa', icon: Eye }
    ];

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">
                            Configuración de {gestoria.nombre}
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                            Personaliza el branding y la información de contacto
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="w-6 h-6 text-gray-600" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b px-6">
                    {tabs.map(tab => {
                        const Icon = tab.icon;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${activeTab === tab.id
                                    ? 'border-primary text-primary'
                                    : 'border-transparent text-gray-600 hover:text-gray-900'
                                    }`}
                            >
                                <Icon className="w-4 h-4" />
                                <span className="font-medium">{tab.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* Validation Errors */}
                {validationErrors.length > 0 && (
                    <div className="mx-6 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <div className="flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                            <div className="flex-1">
                                <h4 className="font-semibold text-red-900">Errores de validación:</h4>
                                <ul className="mt-2 space-y-1">
                                    {validationErrors.map((error, idx) => (
                                        <li key={idx} className="text-sm text-red-700">• {error}</li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {activeTab === 'branding' && (
                        <BrandingTab
                            config={config}
                            onColorChange={handleColorChange}
                            onFileUpload={handleFileUpload}
                            uploading={uploading}
                        />
                    )}

                    {activeTab === 'contacto' && (
                        <ContactoTab
                            config={config}
                            onContactChange={handleContactChange}
                            onSocialChange={handleSocialChange}
                        />
                    )}

                    {activeTab === 'avanzado' && (
                        <AvanzadoTab
                            config={config}
                            onChange={setConfig}
                        />
                    )}

                    {activeTab === 'preview' && (
                        <PreviewTab config={config} gestoria={gestoria} />
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="flex items-center gap-2 px-6 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50"
                    >
                        <Save className="w-4 h-4" />
                        {saving ? 'Guardando...' : 'Guardar Cambios'}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// TAB: BRANDING
// ============================================================================

function BrandingTab({ config, onColorChange, onFileUpload, uploading }) {
    const colores = config.branding?.colores || {};
    const logoUrl = config.branding?.logo_url;
    const faviconUrl = config.branding?.favicon_url;

    // Agregar prefijo del backend a las URLs
    const getImageUrl = (url) => {
        if (!url) return null;
        // Si ya tiene http, devolverla tal cual
        if (url.startsWith('http')) return url;
        // Si es ruta relativa, agregar el backend
        return `${BACKEND_URL}${url}`;
    };

    const logoFullUrl = getImageUrl(logoUrl);
    const faviconFullUrl = getImageUrl(faviconUrl);

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Colores</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <ColorPicker
                        label="Color Primario"
                        value={colores.primario || '#FF6B35'}
                        onChange={(value) => onColorChange('primario', value)}
                    />
                    <ColorPicker
                        label="Color Secundario"
                        value={colores.secundario || '#004E89'}
                        onChange={(value) => onColorChange('secundario', value)}
                    />
                    <ColorPicker
                        label="Color Acento"
                        value={colores.acento || '#F7B801'}
                        onChange={(value) => onColorChange('acento', value)}
                    />
                </div>
            </div>

            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Logo</h3>
                <div className="flex items-center gap-4">
                    <div className="w-32 h-32 border-2 border-gray-200 rounded-lg flex items-center justify-center bg-gray-50">
                        {logoFullUrl ? (
                            <img src={logoFullUrl} alt="Logo" className="max-w-full max-h-full object-contain p-2" />
                        ) : (
                            <div className="text-center text-gray-400">
                                <ImageIcon className="w-12 h-12 mx-auto mb-2" />
                                <p className="text-xs">Sin logo</p>
                            </div>
                        )}
                    </div>
                    <button
                        onClick={() => onFileUpload('logo')}
                        disabled={uploading}
                        className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary hover:bg-primary-light transition-colors disabled:opacity-50"
                    >
                        <Upload className="w-5 h-5" />
                        {uploading ? 'Subiendo...' : logoUrl ? 'Cambiar Logo' : 'Subir Logo'}
                    </button>
                    <div className="text-sm text-gray-600">
                        <p>PNG, JPG o SVG</p>
                        <p>Máximo 2MB</p>
                    </div>
                </div>
            </div>

            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Favicon</h3>
                <div className="flex items-center gap-4">
                    <div className="w-16 h-16 border-2 border-gray-200 rounded-lg flex items-center justify-center bg-gray-50">
                        {faviconFullUrl ? (
                            <img src={faviconFullUrl} alt="Favicon" className="max-w-full max-h-full object-contain" />
                        ) : (
                            <div className="text-center text-gray-400">
                                <ImageIcon className="w-8 h-8 mx-auto" />
                            </div>
                        )}
                    </div>
                    <button
                        onClick={() => onFileUpload('favicon')}
                        disabled={uploading}
                        className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary hover:bg-primary-light transition-colors disabled:opacity-50"
                    >
                        <Upload className="w-5 h-5" />
                        {uploading ? 'Subiendo...' : faviconUrl ? 'Cambiar Favicon' : 'Subir Favicon'}
                    </button>
                    <div className="text-sm text-gray-600">
                        <p>ICO o PNG (16x16, 32x32)</p>
                        <p>Máximo 500KB</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// TAB: CONTACTO
// ============================================================================

function ContactoTab({ config, onContactChange, onSocialChange }) {
    const contacto = config.contacto || {};
    const redes = contacto.redes_sociales || {};

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Información de Contacto</h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <Phone className="w-4 h-4 inline mr-2" />
                            Teléfono
                        </label>
                        <input
                            type="tel"
                            value={contacto.telefono || ''}
                            onChange={(e) => onContactChange('telefono', e.target.value)}
                            placeholder="+34 123 456 789"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <Mail className="w-4 h-4 inline mr-2" />
                            Email
                        </label>
                        <input
                            type="email"
                            value={contacto.email || ''}
                            onChange={(e) => onContactChange('email', e.target.value)}
                            placeholder="info@gestoria.com"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <MapPin className="w-4 h-4 inline mr-2" />
                            Dirección
                        </label>
                        <input
                            type="text"
                            value={contacto.direccion || ''}
                            onChange={(e) => onContactChange('direccion', e.target.value)}
                            placeholder="Calle Principal 123, Madrid"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>
                </div>
            </div>

            <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Redes Sociales</h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <Facebook className="w-4 h-4 inline mr-2" />
                            Facebook
                        </label>
                        <input
                            type="url"
                            value={redes.facebook || ''}
                            onChange={(e) => onSocialChange('facebook', e.target.value)}
                            placeholder="https://facebook.com/gestoria"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <Linkedin className="w-4 h-4 inline mr-2" />
                            LinkedIn
                        </label>
                        <input
                            type="url"
                            value={redes.linkedin || ''}
                            onChange={(e) => onSocialChange('linkedin', e.target.value)}
                            placeholder="https://linkedin.com/company/gestoria"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// TAB: AVANZADO
// ============================================================================

function AvanzadoTab({ config, onChange }) {
    const [jsonText, setJsonText] = useState(JSON.stringify(config, null, 2));
    const [jsonError, setJsonError] = useState(null);

    const handleJsonChange = (e) => {
        const newText = e.target.value;
        setJsonText(newText);

        try {
            const parsed = JSON.parse(newText);
            onChange(parsed);
            setJsonError(null);
        } catch (error) {
            setJsonError(error.message);
        }
    };

    return (
        <div className="space-y-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                    <AlertCircle className="w-4 h-4 inline mr-2" />
                    <strong>Avanzado:</strong> Edita la configuración JSON directamente. Ten cuidado con la sintaxis.
                </p>
            </div>

            {jsonError && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">
                        <strong>Error de sintaxis:</strong> {jsonError}
                    </p>
                </div>
            )}

            <textarea
                value={jsonText}
                onChange={handleJsonChange}
                className="w-full h-96 px-4 py-3 font-mono text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none"
                spellCheck={false}
            />
        </div>
    );
}

// ============================================================================
// TAB: PREVIEW
// ============================================================================

function PreviewTab({ config, gestoria }) {
    const colores = config.branding?.colores || {};
    const logoUrl = config.branding?.logo_url;
    const contacto = config.contacto || {};

    // Agregar prefijo del backend a las URLs
    const getImageUrl = (url) => {
        if (!url) return null;
        if (url.startsWith('http')) return url;
        return `${BACKEND_URL}${url}`;
    };

    const logoFullUrl = getImageUrl(logoUrl);

    return (
        <div className="space-y-6">
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Vista Previa del Header</h3>
                <div
                    className="bg-white rounded-lg shadow-lg p-4 flex items-center justify-between"
                    style={{ borderTop: `4px solid ${colores.primario}` }}
                >
                    <div className="flex items-center gap-4">
                        {logoFullUrl && (
                            <img src={logoFullUrl} alt="Logo" className="h-12 object-contain" />
                        )}
                        <div>
                            <h2 className="text-xl font-bold" style={{ color: colores.primario }}>
                                {gestoria.nombre}
                            </h2>
                            <p className="text-sm text-gray-600">{contacto.email}</p>
                        </div>
                    </div>
                    <button
                        className="px-4 py-2 rounded-lg text-white font-medium"
                        style={{ backgroundColor: colores.primario }}
                    >
                        Botón de Ejemplo
                    </button>
                </div>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Paleta de Colores</h3>
                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <div
                            className="h-24 rounded-lg shadow-md"
                            style={{ backgroundColor: colores.primario }}
                        ></div>
                        <p className="mt-2 text-sm font-medium text-gray-700">Primario</p>
                        <p className="text-xs text-gray-500">{colores.primario}</p>
                    </div>
                    <div>
                        <div
                            className="h-24 rounded-lg shadow-md"
                            style={{ backgroundColor: colores.secundario }}
                        ></div>
                        <p className="mt-2 text-sm font-medium text-gray-700">Secundario</p>
                        <p className="text-xs text-gray-500">{colores.secundario}</p>
                    </div>
                    <div>
                        <div
                            className="h-24 rounded-lg shadow-md"
                            style={{ backgroundColor: colores.acento }}
                        ></div>
                        <p className="mt-2 text-sm font-medium text-gray-700">Acento</p>
                        <p className="text-xs text-gray-500">{colores.acento}</p>
                    </div>
                </div>
            </div>

            <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Información de Contacto</h3>
                <div className="space-y-2 text-sm">
                    {contacto.telefono && (
                        <p><Phone className="w-4 h-4 inline mr-2" />{contacto.telefono}</p>
                    )}
                    {contacto.email && (
                        <p><Mail className="w-4 h-4 inline mr-2" />{contacto.email}</p>
                    )}
                    {contacto.direccion && (
                        <p><MapPin className="w-4 h-4 inline mr-2" />{contacto.direccion}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

// ============================================================================
// COMPONENT: COLOR PICKER
// ============================================================================

function ColorPicker({ label, value, onChange }) {
    return (
        <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
            <div className="flex items-center gap-3">
                <input
                    type="color"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-12 h-12 rounded-lg border-2 border-gray-300 cursor-pointer"
                />
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    placeholder="#FF6B35"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary outline-none font-mono text-sm"
                />
            </div>
        </div>
    );
}
