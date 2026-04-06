// frontend/src/components/SaltraAdminView.jsx
import React, { useState, useEffect } from 'react';
import { Building2, Key, CheckCircle, XCircle, Settings, Loader2 } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import SaltraConfigModal from './SaltraConfigModal';

export default function SaltraAdminView() {
    const [gestorias, setGestorias] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedGestoria, setSelectedGestoria] = useState(null);
    const [showConfigModal, setShowConfigModal] = useState(false);

    useEffect(() => {
        cargarGestorias();
    }, []);

    const cargarGestorias = async () => {
        setLoading(true);
        try {
            const res = await axios.get('/api/admin/gestorias', { withCredentials: true });
            if (res.data.success) {
                // Obtener estado de configuración SALTRA para cada gestoría
                const gestoriasConEstado = await Promise.all(
                    res.data.gestorias.map(async (g) => {
                        try {
                            const statusRes = await axios.get(`/api/admin/gestoria/${g.id}/saltra-status`, {
                                withCredentials: true
                            });
                            return {
                                ...g,
                                saltra_configured: statusRes.data.configured || false,
                                saltra_enabled: statusRes.data.enabled || false
                            };
                        } catch (err) {
                            return { ...g, saltra_configured: false, saltra_enabled: false };
                        }
                    })
                );
                setGestorias(gestoriasConEstado);
            }
        } catch (err) {
            toast.error('Error al cargar gestorías');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleConfigurar = (gestoria) => {
        setSelectedGestoria(gestoria);
        setShowConfigModal(true);
    };

    const handleConfigSaved = () => {
        cargarGestorias(); // Recargar lista
        setSelectedGestoria(null);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary-light rounded-lg">
                        <Key className="w-8 h-8 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Administración SALTRA</h1>
                        <p className="text-gray-600 mt-1">Configurar credenciales SALTRA por gestoría</p>
                    </div>
                </div>
            </div>

            {/* Lista de Gestorías */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100">
                <div className="p-6 border-b border-gray-100">
                    <h2 className="text-xl font-semibold text-gray-900">Gestorías</h2>
                    <p className="text-sm text-gray-600 mt-1">
                        Configura las credenciales SALTRA para cada gestoría
                    </p>
                </div>

                <div className="divide-y divide-gray-100">
                    {gestorias.map((gestoria) => (
                        <div
                            key={gestoria.id}
                            className="p-6 hover:bg-gray-50 transition-colors"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="p-3 bg-gray-100 rounded-lg">
                                        <Building2 className="w-6 h-6 text-gray-600" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-gray-900">{gestoria.nombre}</h3>
                                        <p className="text-sm text-gray-600">Slug: {gestoria.slug}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    {/* Estado */}
                                    <div className="flex items-center gap-2">
                                        {gestoria.saltra_configured ? (
                                            <>
                                                {gestoria.saltra_enabled ? (
                                                    <>
                                                        <CheckCircle className="w-5 h-5 text-green-600" />
                                                        <span className="text-sm font-medium text-green-700">
                                                            Configurado y Activo
                                                        </span>
                                                    </>
                                                ) : (
                                                    <>
                                                        <XCircle className="w-5 h-5 text-amber-600" />
                                                        <span className="text-sm font-medium text-amber-700">
                                                            Configurado pero Deshabilitado
                                                        </span>
                                                    </>
                                                )}
                                            </>
                                        ) : (
                                            <>
                                                <XCircle className="w-5 h-5 text-gray-400" />
                                                <span className="text-sm font-medium text-gray-500">
                                                    No Configurado
                                                </span>
                                            </>
                                        )}
                                    </div>

                                    {/* Botón Configurar */}
                                    <button
                                        onClick={() => handleConfigurar(gestoria)}
                                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
                                    >
                                        <Settings className="w-4 h-4" />
                                        {gestoria.saltra_configured ? 'Editar' : 'Configurar'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Modal de Configuración */}
            <SaltraConfigModal
                isOpen={showConfigModal}
                onClose={() => {
                    setShowConfigModal(false);
                    setSelectedGestoria(null);
                }}
                onSuccess={handleConfigSaved}
                gestoriaId={selectedGestoria?.id}
                gestoriaNombre={selectedGestoria?.nombre}
            />
        </div>
    );
}
