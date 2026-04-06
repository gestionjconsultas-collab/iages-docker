// frontend/src/components/BillingDashboard.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    CreditCard,
    FileText,
    TrendingUp,
    AlertCircle,
    CheckCircle,
    Calendar,
    Download,
    RefreshCw,
    ShieldCheck
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import socket from '../socket';
import PlanSelector from './PlanSelector';
import InvoiceList from './InvoiceList';
import UsageStats from './UsageStats';
import BannerPromocional from './BannerPromocional';

const BillingDashboard = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [suscripcion, setSuscripcion] = useState(null);
    const [facturas, setFacturas] = useState([]);
    const [uso, setUso] = useState(null);
    const [banners, setBanners] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showPlanSelector, setShowPlanSelector] = useState(false);
    const [cuponPreAplicado, setCuponPreAplicado] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [ultimoPlanId, setUltimoPlanId] = useState(null);
    const [datosBancarios, setDatosBancarios] = useState(null);
    const [gestoriaNombre, setGestoriaNombre] = useState('');

    useEffect(() => {
        cargarDatos();
    }, []);

    // Polling automático cada 30 segundos para detectar cambios de plan
    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const res = await axios.get('/api/suscripcion');
                const nuevoPlanId = res.data.suscripcion?.plan_id;

                // Si el plan cambió, recargar datos y notificar
                if (ultimoPlanId && nuevoPlanId && nuevoPlanId !== ultimoPlanId) {
                    console.log(`📊 Plan actualizado: ${ultimoPlanId} → ${nuevoPlanId}`);
                    toast.info('Tu plan ha sido actualizado', {
                        id: 'plan_change_notification', // ID único compartido con WebSocket
                        icon: '🔄',
                        duration: 4000
                    });
                    await cargarDatos();
                }

                setUltimoPlanId(nuevoPlanId);
            } catch (error) {
                console.error('Error en polling:', error);
            }
        }, 30000); // 30 segundos

        return () => clearInterval(interval);
    }, [ultimoPlanId]);

    // WebSocket: Escuchar cambios de plan en tiempo real
    useEffect(() => {
        const gestoriaId = localStorage.getItem('gestoria_id');
        if (!gestoriaId) return;

        socket.emit('join_gestoria', { gestoria_id: gestoriaId });

        const handlePlanChanged = async (data) => {
            console.log('📡 Plan actualizado vía WebSocket:', data);
            toast.success(`Tu plan ha sido actualizado a ${data.new_plan}`, {
                id: 'plan_change_notification',
                icon: '✨',
                duration: 5000
            });
            await cargarDatos();
        };

        socket.on('plan_changed', handlePlanChanged);

        return () => {
            socket.off('plan_changed', handlePlanChanged);
            socket.emit('leave_gestoria', { gestoria_id: gestoriaId });
        };
    }, []);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const [suscripcionRes, facturasRes, usoRes, bannerRes, datosBancariosRes] = await Promise.allSettled([
                axios.get('/api/suscripcion'),
                axios.get('/api/facturas?limit=10'),
                axios.get('/api/uso-actual'),
                axios.get('/api/banners/activos'),
                axios.get('/api/datos-bancarios').catch(() => null)
            ]);

            // Manejar suscripción
            if (suscripcionRes.status === 'fulfilled') {
                setSuscripcion(suscripcionRes.value.data.suscripcion);
                setGestoriaNombre(suscripcionRes.value.data.gestoria_nombre || '');
            } else {
                console.error('Error cargando suscripción:', suscripcionRes.reason);
                setSuscripcion(null);
            }

            // Manejar facturas
            if (facturasRes.status === 'fulfilled') {
                setFacturas(facturasRes.value.data.facturas || []);
            } else {
                console.error('Error cargando facturas:', facturasRes.reason);
                setFacturas([]);
            }

            // Manejar uso
            if (usoRes.status === 'fulfilled') {
                setUso(usoRes.value.data);
            } else {
                console.error('Error cargando uso:', usoRes.reason);
                setUso(null);
            }

            // Manejar banners
            if (bannerRes.status === 'fulfilled') {
                setBanners(bannerRes.value.data.banners || []);
            } else {
                console.error('Error cargando banners:', bannerRes.reason);
                setBanners([]);
            }

            // Manejar datos bancarios
            if (datosBancariosRes?.status === 'fulfilled' && datosBancariosRes.value) {
                setDatosBancarios(datosBancariosRes.value.data.datos_bancarios);
            }
        } catch (error) {
            console.error('Error cargando datos:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handlePlanChanged = () => {
        setShowPlanSelector(false);
        cargarDatos();
    };

    const handleBannerClick = (cuponCodigo) => {
        setCuponPreAplicado(cuponCodigo);
        setShowPlanSelector(true);
    };

    const handleRefresh = async () => {
        setRefreshing(true);
        await cargarDatos();
        toast.success('Datos actualizados');
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <RefreshCw className="w-8 h-8 animate-spin text-orange-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8 flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 mb-2">
                            Facturación y Suscripción
                        </h1>
                        <p className="text-gray-600">
                            Gestiona tu plan, facturas y uso de recursos
                        </p>
                    </div>
                    <button
                        onClick={handleRefresh}
                        disabled={refreshing}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400 transition-all"
                        title="Actualizar datos"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                        Actualizar
                    </button>
                </div>

                {/* Banner Promocional */}
                {banners.length > 0 && (
                    <BannerPromocional
                        banners={banners}
                        onCambiarPlan={handleBannerClick}
                    />
                )}

                {/* Alert de Trial */}
                {suscripcion?.esta_en_trial && (
                    <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                        <div>
                            <h3 className="font-semibold text-blue-900">
                                Período de Prueba Activo
                            </h3>
                            <p className="text-sm text-blue-700 mt-1">
                                Te quedan {suscripcion.dias_restantes_trial} días de prueba gratuita.
                                Después se te facturará €{suscripcion.precio_actual}/mes.
                            </p>
                        </div>
                    </div>
                )}

                {/* Datos Bancarios para pagos pendientes */}
                {facturas.some(f => f.estado === 'pendiente') && datosBancarios && (
                    <div className="mb-6 bg-gradient-to-r from-orange-500/5 to-orange-600/5 border border-orange-200 rounded-2xl overflow-hidden shadow-sm">
                        <div className="bg-orange-50 px-6 py-3 border-b border-orange-100 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <ShieldCheck className="w-5 h-5 text-orange-600" />
                                <h3 className="font-bold text-orange-900">Instrucciones de Pago</h3>
                            </div>
                            <span className="text-[10px] font-bold text-orange-500 uppercase tracking-wider">Transferencia Bancaria</span>
                        </div>
                        <div className="p-6">
                            <p className="text-sm text-gray-700 mb-4">
                                Tienes facturas pendientes de pago. Por favor, realiza la transferencia a la siguiente cuenta:
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 bg-white p-4 rounded-xl border border-orange-100/50">
                                <div>
                                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Beneficiario</label>
                                    <p className="text-sm font-semibold text-gray-900">{datosBancarios.nombre}</p>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Banco</label>
                                    <p className="text-sm font-semibold text-gray-900">{datosBancarios.banco}</p>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">IBAN</label>
                                    <p className="text-sm font-mono font-bold text-orange-600 tracking-tight">{datosBancarios.iban}</p>
                                </div>
                                <div>
                                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">SWIFT / BIC</label>
                                    <p className="text-sm font-semibold text-gray-900">{datosBancarios.swift}</p>
                                </div>
                                <div className="md:col-span-2">
                                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Concepto recomendado</label>
                                    <p className="text-sm font-semibold text-orange-700 font-mono">
                                        Factura {facturas.find(f => f.estado === 'pendiente')?.numero_factura || '...'} - {gestoriaNombre || 'Su Gestoría'}
                                    </p>
                                </div>
                            </div>
                            <div className="mt-4 flex items-center gap-2 text-[11px] text-gray-500">
                                <AlertCircle className="w-3 h-3" />
                                <span>Una vez realizado el pago, nuestro equipo validará la transferencia y marcará la factura como pagada en un plazo de 24-48h.</span>
                            </div>
                        </div>
                    </div>
                )}

                {/* Tabs */}
                <div className="bg-white rounded-lg shadow-sm mb-6">
                    <div className="border-b border-gray-200">
                        <nav className="flex -mb-px">
                            {[
                                { id: 'overview', label: 'Resumen', icon: TrendingUp },
                                { id: 'plan', label: 'Mi Plan', icon: CreditCard },
                                { id: 'facturas', label: 'Facturas', icon: FileText },
                                { id: 'uso', label: 'Uso', icon: TrendingUp }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`
                    flex items-center gap-2 px-6 py-4 border-b-2 font-medium text-sm
                    ${activeTab === tab.id
                                            ? 'border-orange-500 text-orange-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                        }
                  `}
                                >
                                    <tab.icon className="w-4 h-4" />
                                    {tab.label}
                                </button>
                            ))}
                        </nav>
                    </div>

                    <div className="p-6">
                        {/* Overview Tab */}
                        {activeTab === 'overview' && (
                            <div className="space-y-6">
                                {/* Plan Actual */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg p-6 text-white">
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-sm font-medium opacity-90">Plan Actual</h3>
                                            <CreditCard className="w-5 h-5 opacity-75" />
                                        </div>
                                        <div className="text-3xl font-bold mb-1">
                                            {suscripcion?.plan?.nombre || 'Sin Plan'}
                                        </div>
                                        <div className="text-sm opacity-90">
                                            €{suscripcion?.precio_actual || 0}/{suscripcion?.ciclo || 'mes'}
                                        </div>
                                    </div>

                                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-sm font-medium text-gray-600">Próximo Pago</h3>
                                            <Calendar className="w-5 h-5 text-gray-400" />
                                        </div>
                                        <div className="text-2xl font-bold text-gray-900 mb-1">
                                            {suscripcion?.fecha_proximo_pago
                                                ? new Date(suscripcion.fecha_proximo_pago).toLocaleDateString('es-ES')
                                                : 'N/A'
                                            }
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            {suscripcion?.estado === 'trial' ? 'Fin del trial' : 'Renovación automática'}
                                        </div>
                                    </div>

                                    <div className="bg-white border border-gray-200 rounded-lg p-6">
                                        <div className="flex items-center justify-between mb-4">
                                            <h3 className="text-sm font-medium text-gray-600">Facturas Pendientes</h3>
                                            <FileText className="w-5 h-5 text-gray-400" />
                                        </div>
                                        <div className="text-2xl font-bold text-gray-900 mb-1">
                                            {facturas.filter(f => f.estado === 'pendiente').length}
                                        </div>
                                        <div className="text-sm text-gray-500">
                                            Total: €{facturas
                                                .filter(f => f.estado === 'pendiente')
                                                .reduce((sum, f) => sum + parseFloat(f.total), 0)
                                                .toFixed(2)
                                            }
                                        </div>
                                    </div>
                                </div>

                                {/* Últimas Facturas */}
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900 mb-4">
                                        Últimas Facturas
                                    </h3>
                                    <div className="space-y-3">
                                        {facturas.slice(0, 3).map(factura => (
                                            <div
                                                key={factura.id}
                                                className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                                            >
                                                <div className="flex items-center gap-4">
                                                    <div className={`
                            w-10 h-10 rounded-full flex items-center justify-center
                            ${factura.estado === 'pagada' ? 'bg-green-100' : 'bg-yellow-100'}
                          `}>
                                                        {factura.estado === 'pagada'
                                                            ? <CheckCircle className="w-5 h-5 text-green-600" />
                                                            : <AlertCircle className="w-5 h-5 text-yellow-600" />
                                                        }
                                                    </div>
                                                    <div>
                                                        <div className="font-medium text-gray-900">
                                                            {factura.numero_factura}
                                                        </div>
                                                        <div className="text-sm text-gray-500">
                                                            {new Date(factura.fecha_emision).toLocaleDateString('es-ES')}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className="font-semibold text-gray-900">
                                                        €{factura.total}
                                                    </div>
                                                    <div className={`
                            text-xs font-medium
                            ${factura.estado === 'pagada' ? 'text-green-600' : 'text-yellow-600'}
                          `}>
                                                        {factura.estado === 'pagada' ? 'Pagada' : 'Pendiente'}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Plan Tab */}
                        {activeTab === 'plan' && (
                            <div className="space-y-6">
                                <div className="bg-white border border-gray-200 rounded-lg p-6">
                                    <h3 className="text-xl font-bold text-gray-900 mb-4">
                                        Plan {suscripcion?.plan?.nombre}
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4 mb-6">
                                        <div>
                                            <div className="text-sm text-gray-600 mb-1">Precio</div>
                                            <div className="text-2xl font-bold text-orange-600">
                                                €{suscripcion?.precio_actual}
                                                <span className="text-sm text-gray-500">/{suscripcion?.ciclo}</span>
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-sm text-gray-600 mb-1">Estado</div>
                                            <div className="text-lg font-semibold text-green-600 capitalize">
                                                {suscripcion?.estado}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-3 mb-6">
                                        <h4 className="font-semibold text-gray-900">Límites del Plan</h4>
                                        {suscripcion?.plan && (
                                            <div className="grid grid-cols-2 gap-4 text-sm">
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Usuarios:</span>
                                                    <span className="font-medium">{suscripcion.plan.max_usuarios || '∞'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Empresas:</span>
                                                    <span className="font-medium">{suscripcion.plan.max_empresas || '∞'}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Certificados Conecta:</span>
                                                    <span className="font-medium">{suscripcion.plan.max_certificados === -1 || suscripcion.plan.max_certificados === null ? '∞' : suscripcion.plan.max_certificados}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Storage:</span>
                                                    <span className="font-medium">{suscripcion.plan.max_storage_gb} GB</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-gray-600">Tokens IA/mes:</span>
                                                    <span className="font-medium">{(suscripcion.plan.max_tokens_mes / 1000).toFixed(0)}K</span>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    <button
                                        onClick={() => setShowPlanSelector(true)}
                                        className="w-full bg-orange-500 hover:bg-orange-600 text-white font-medium py-3 px-4 rounded-lg transition-colors"
                                    >
                                        Cambiar Plan
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Facturas Tab */}
                        {activeTab === 'facturas' && (
                            <InvoiceList facturas={facturas} onRefresh={cargarDatos} />
                        )}

                        {/* Uso Tab */}
                        {activeTab === 'uso' && (
                            <UsageStats uso={uso} suscripcion={suscripcion} />
                        )}
                    </div>
                </div>

                {/* Modal de Selector de Planes (fuera de tabs) */}
                {showPlanSelector && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-lg max-w-7xl w-full max-h-[95vh] overflow-y-auto p-8">
                            <PlanSelector
                                suscripcionActual={suscripcion}
                                onPlanChanged={handlePlanChanged}
                                onCancel={() => setShowPlanSelector(false)}
                                cuponPreAplicado={cuponPreAplicado}
                            />
                        </div>
                    </div>
                )}
            </div>
        </div >
    );
};

export default BillingDashboard;
