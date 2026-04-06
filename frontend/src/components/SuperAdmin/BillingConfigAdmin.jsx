import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Save,
    Building2,
    CreditCard,
    Mail,
    MapPin,
    Phone,
    Globe,
    Shield,
    Loader2,
    CheckCircle2,
    AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

const BillingConfigAdmin = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [config, setConfig] = useState({
        nombre: '',
        cif: '',
        direccion: '',
        codigo_postal: '',
        ciudad: '',
        provincia: '',
        pais: 'España',
        telefono: '',
        email: '',
        web: '',
        iban: '',
        swift: '',
        banco: ''
    });

    useEffect(() => {
        cargarConfig();
    }, []);

    const cargarConfig = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/api/super-admin/billing-config');
            if (res.data.success && res.data.config) {
                setConfig({ ...config, ...res.data.config });
            }
        } catch (error) {
            console.error('Error cargando config:', error);
            toast.error('Error al cargar la configuración');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const res = await axios.put('/api/super-admin/billing-config', config);
            if (res.data.success) {
                toast.success('Configuración actualizada correctamente');
            }
        } catch (error) {
            console.error('Error guardando config:', error);
            toast.error(error.response?.data?.error || 'Error al guardar');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center p-12">
                <Loader2 className="w-8 h-8 text-orange-500 animate-spin mb-4" />
                <p className="text-gray-500 font-medium">Cargando configuración global...</p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto py-8 px-4">
            <form onSubmit={handleSave} className="space-y-8">
                {/* Entidad Section */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="bg-gradient-to-r from-orange-500/10 to-transparent px-6 py-4 border-b border-gray-100 flex items-center gap-3">
                        <Building2 className="w-5 h-5 text-orange-600" />
                        <h3 className="font-bold text-gray-800">Datos de la Entidad (IAGES)</h3>
                    </div>

                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Nombre de la Empresa</label>
                            <input
                                type="text"
                                value={config.nombre}
                                onChange={(e) => setConfig({ ...config, nombre: e.target.value })}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                placeholder="IAGES Platform"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">CIF / NIF</label>
                            <input
                                type="text"
                                value={config.cif}
                                onChange={(e) => setConfig({ ...config, cif: e.target.value })}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                placeholder="B12345678"
                                required
                            />
                        </div>
                        <div className="md:col-span-2 space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Dirección Fiscal</label>
                            <div className="relative">
                                <MapPin className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                                <textarea
                                    value={config.direccion}
                                    onChange={(e) => setConfig({ ...config, direccion: e.target.value })}
                                    className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                    placeholder="Calle Ejemplo 123, Planta 4"
                                    rows="2"
                                    required
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Ciudad</label>
                            <input
                                type="text"
                                value={config.ciudad}
                                onChange={(e) => setConfig({ ...config, ciudad: e.target.value })}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">País</label>
                            <input
                                type="text"
                                value={config.pais}
                                onChange={(e) => setConfig({ ...config, pais: e.target.value })}
                                className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                            />
                        </div>
                    </div>
                </div>

                {/* Contact Section */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="bg-gradient-to-r from-blue-500/10 to-transparent px-6 py-4 border-b border-gray-100 flex items-center gap-3">
                        <Mail className="w-5 h-5 text-blue-600" />
                        <h3 className="font-bold text-gray-800">Contacto y Web</h3>
                    </div>

                    <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Email de Facturación</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="email"
                                    value={config.email}
                                    onChange={(e) => setConfig({ ...config, email: e.target.value })}
                                    className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                    placeholder="facturacion@iages.es"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Teléfono</label>
                            <div className="relative">
                                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    value={config.telefono}
                                    onChange={(e) => setConfig({ ...config, telefono: e.target.value })}
                                    className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Bank Section */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="bg-gradient-to-r from-emerald-500/10 to-transparent px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <CreditCard className="w-5 h-5 text-emerald-600" />
                            <h3 className="font-bold text-gray-800">Datos Bancarios (Encriptados)</h3>
                        </div>
                        <span className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">
                            <Shield className="w-3 h-3" />
                            SECURE
                        </span>
                    </div>

                    <div className="p-6 space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-gray-700">Nombre del Banco</label>
                                <input
                                    type="text"
                                    value={config.banco}
                                    onChange={(e) => setConfig({ ...config, banco: e.target.value })}
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                    placeholder="Banco Santander, BBVA..."
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-semibold text-gray-700">Código SWIFT / BIC</label>
                                <input
                                    type="text"
                                    value={config.swift}
                                    onChange={(e) => setConfig({ ...config, swift: e.target.value })}
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all"
                                    placeholder="BSANESMMXXX"
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-gray-700">Número de Cuenta (IBAN)</label>
                            <div className="relative">
                                <CreditCard className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    value={config.iban}
                                    onChange={(e) => setConfig({ ...config, iban: e.target.value })}
                                    className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 outline-none transition-all font-mono"
                                    placeholder="ES21 0049 1234 56 7890123456"
                                />
                            </div>
                            <p className="text-[10px] text-gray-400 flex items-center gap-1">
                                <AlertCircle className="w-3 h-3" />
                                Estos datos se encriptan mediante Fernet (AES-128) antes de guardarse en la base de datos.
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button
                        type="submit"
                        disabled={saving}
                        className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-xl font-bold shadow-lg shadow-orange-500/30 hover:shadow-orange-500/40 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:translate-y-0"
                    >
                        {saving ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                GUARDANDO...
                            </>
                        ) : (
                            <>
                                <Save className="w-5 h-5" />
                                GUARDAR CONFIGURACIÓN
                            </>
                        )}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default BillingConfigAdmin;
