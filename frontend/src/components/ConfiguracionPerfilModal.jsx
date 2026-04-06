import React, { useState, useEffect } from 'react';
import { X, Save, Shield, Folder, Bell, CheckCircle2, AlertTriangle, Briefcase, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

export default function ConfiguracionPerfilModal({ show, onClose, perfil, onUpdated }) {
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const [config, setConfig] = useState({
        categoria: '',
        prioridad_default: 'informativa',
        departamento: '',
        notificar_cliente: false,
        activo: true
    });

    const [opciones, setOpciones] = useState({
        categorias: [],
        departamentos: []
    });

    useEffect(() => {
        if (show && perfil) {
            cargarConfiguracion();
        }
    }, [show, perfil]);

    const cargarConfiguracion = async () => {
        setLoading(true);
        try {
            // Cargamos opciones y config actual desde el endpoint centralizado
            // NOTA: Podríamos optimizar cargando opciones una sola vez en el padre, 
            // pero aquí aseguramos tener lo más fresco.
            const res = await axios.get('/api/configuracion-perfiles');

            setOpciones(res.data.opciones);

            // Buscar si ya existe config para este perfil
            if (res.data.configuraciones && res.data.configuraciones[perfil.clase]) {
                const current = res.data.configuraciones[perfil.clase];
                setConfig({
                    categoria: current.categoria || '',
                    prioridad_default: current.prioridad_default || 'informativa',
                    departamento: current.departamento || '',
                    notificar_cliente: current.notificar_cliente || false,
                    activo: current.activo !== undefined ? current.activo : true
                });
            } else {
                // Valores por defecto
                setConfig({
                    categoria: '',
                    prioridad_default: 'informativa',
                    departamento: '',
                    notificar_cliente: false,
                    activo: true
                });
            }
        } catch (error) {
            console.error("Error cargando configuración:", error);
            toast.error("Error al cargar configuración");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!config.categoria || !config.departamento) {
            toast.error("Categoría y Departamento son obligatorios para automatizar");
            return;
        }

        setSaving(true);
        try {
            await axios.post('/api/configuracion-perfiles', {
                perfil_clave: perfil.clase,
                ...config
            });

            toast.success("Configuración guardada correctamente");
            if (onUpdated) onUpdated(); // Recargar lista padre
            onClose();
        } catch (error) {
            console.error("Error guardando:", error);
            toast.error("Error al guardar configuración");
        } finally {
            setSaving(false);
        }
    };

    if (!show || !perfil) return null;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">

                {/* Header */}
                <div className={`p-4 border-b flex justify-between items-center ${perfil.color ? `bg-${perfil.color}-50` : 'bg-gray-50'}`}>
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg bg-white shadow-sm text-2xl`}>
                            {perfil.icono}
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-900">{perfil.nombre}</h3>
                            <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Configuración de Automatización</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-black/5 rounded-full transition-colors">
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 overflow-y-auto space-y-6">

                    {loading ? (
                        <div className="flex justify-center py-10"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
                    ) : (
                        <>
                            {/* Alerta si está incompleto */}
                            {(!config.categoria || !config.departamento) && (
                                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3 text-amber-800">
                                    <AlertTriangle className="w-5 h-5 shrink-0" />
                                    <div className="text-sm">
                                        <p className="font-bold">Perfil Incompleto</p>
                                        <p>Debes asignar una categoría y departamento para poder utilizar este perfil en la mesa de trabajo.</p>
                                    </div>
                                </div>
                            )}

                            <div className="grid gap-6">
                                {/* Categoría */}
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-gray-700 flex items-center gap-2">
                                        <Folder className="w-4 h-4 text-blue-500" />
                                        Categoría Destino
                                    </label>
                                    <select
                                        value={config.categoria}
                                        onChange={e => setConfig({ ...config, categoria: e.target.value })}
                                        className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                                    >
                                        <option value="">-- Seleccionar Categoría --</option>
                                        {opciones.categorias.map(cat => (
                                            <option key={cat} value={cat}>{cat}</option>
                                        ))}
                                    </select>
                                </div>

                                {/* Prioridad de Notificación */}
                                {config.categoria === 'Notificaciones' && (
                                    <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                                        <label className="text-sm font-bold text-gray-700 flex items-center gap-2">
                                            <AlertCircle className="w-4 h-4 text-orange-500" />
                                            Prioridad
                                        </label>
                                        <select
                                            value={config.prioridad_default}
                                            onChange={e => setConfig({ ...config, prioridad_default: e.target.value })}
                                            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 outline-none transition-all"
                                        >
                                            <option value="informativa">Informativas</option>
                                            <option value="importante">Importantes</option>
                                            <option value="urgente">Urgentes</option>
                                        </select>
                                    </div>
                                )}

                                {/* Departamento */}
                                <div className="space-y-2">
                                    <label className="text-sm font-bold text-gray-700 flex items-center gap-2">
                                        <Briefcase className="w-4 h-4 text-purple-500" />
                                        Departamento Asignado
                                    </label>
                                    <select
                                        value={config.departamento}
                                        onChange={e => setConfig({ ...config, departamento: e.target.value })}
                                        className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none transition-all"
                                    >
                                        <option value="">-- Seleccionar Departamento --</option>
                                        {opciones.departamentos.map(dep => (
                                            <option key={dep} value={dep}>{dep}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="border-t border-gray-100 my-2"></div>

                                {/* Notificaciones */}
                                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-100">
                                    <div className="flex gap-3">
                                        <div className="p-2 bg-white rounded-lg shadow-sm text-orange-500">
                                            <Bell className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <p className="font-bold text-gray-900 text-sm">Notificar al Cliente</p>
                                            <p className="text-xs text-gray-500">Crear alerta en el panel del cliente</p>
                                        </div>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={config.notificar_cliente}
                                            onChange={e => setConfig({ ...config, notificar_cliente: e.target.checked })}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-orange-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange-500"></div>
                                    </label>
                                </div>

                                {/* Activo (Switch) */}
                                <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                    <div className="flex gap-3">
                                        <div className="p-2 bg-white rounded-lg shadow-sm text-emerald-500">
                                            <ZapIcon className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <p className="font-bold text-gray-900 text-sm">Automatización Activa</p>
                                            <p className="text-xs text-gray-500">Si está activo, se aplica automáticamente</p>
                                        </div>
                                    </div>
                                    <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={config.activo}
                                            onChange={e => setConfig({ ...config, activo: e.target.checked })}
                                            className="sr-only peer"
                                        />
                                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
                                    </label>
                                </div>
                            </div>
                        </>
                    )}

                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-gray-50 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium transition-colors"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving || loading}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold shadow-lg shadow-blue-200 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {saving ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                Guardando...
                            </>
                        ) : (
                            <>
                                <Save className="w-4 h-4" />
                                Guardar Configuración
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}

// Icono auxiliar (ya que Zap no se importó arriba pero se usa)
function ZapIcon({ className }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
        </svg>
    )
}
