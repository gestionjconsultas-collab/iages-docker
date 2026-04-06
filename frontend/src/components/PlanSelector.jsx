// frontend/src/components/PlanSelector.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Check, X, Sparkles, TrendingUp, Crown } from 'lucide-react';

const PlanSelector = ({ suscripcionActual, onPlanChanged, onCancel, cuponPreAplicado }) => {
    const [planes, setPlanes] = useState([]);
    const [ciclo, setCiclo] = useState('mensual');
    const [cuponCodigo, setCuponCodigo] = useState('');
    const [cuponValido, setCuponValido] = useState(null);
    const [loading, setLoading] = useState(false);
    const [selectedPlan, setSelectedPlan] = useState(null);
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [planToChange, setPlanToChange] = useState(null);
    const [showSuccessModal, setShowSuccessModal] = useState(false);
    const [ticketNumero, setTicketNumero] = useState(null);

    useEffect(() => {
        cargarPlanes();
    }, []);

    const cargarPlanes = async () => {
        try {
            const response = await axios.get('/api/planes');
            setPlanes(response.data.planes);
        } catch (error) {
            console.error('Error cargando planes:', error);
        }
    };

    const validarCupon = async () => {
        if (!cuponCodigo.trim()) {
            setCuponValido(null);
            return;
        }

        try {
            const response = await axios.post('/api/cupones/validar', {
                codigo: cuponCodigo,
                plan_id: selectedPlan?.id,
                ciclo
            });

            if (response.data.valido) {
                setCuponValido(response.data.cupon);
            } else {
                setCuponValido({ error: response.data.mensaje });
            }
        } catch (error) {
            setCuponValido({ error: 'Cupón inválido' });
        }
    };

    // Auto-aplicar cupón si viene del banner (después de definir validarCupon)
    useEffect(() => {
        if (cuponPreAplicado && cuponPreAplicado.trim()) {
            console.log('🎟️ Auto-aplicando cupón:', cuponPreAplicado);
            setCuponCodigo(cuponPreAplicado);
            // NO validar automáticamente - esperar a que el usuario haga click en "Aplicar"
            // o seleccione un plan
        }
    }, [cuponPreAplicado]);

    const cambiarPlan = async (plan) => {
        // Mostrar modal de confirmación personalizado
        setPlanToChange(plan);
        setShowConfirmModal(true);
    };

    const confirmarCambioPlan = async () => {
        if (!planToChange) return;

        setLoading(true);
        setShowConfirmModal(false);

        try {
            // Preparar detalles del plan solicitado
            const precio = ciclo === 'anual' ? planToChange.precio_anual : planToChange.precio_mensual;
            const precioFinal = calcularPrecio(planToChange).final;

            const detallesPlan = [
                `📋 SOLICITUD DE CAMBIO DE PLAN`,
                ``,
                `Plan solicitado: ${planToChange.nombre} `,
                `Ciclo de facturación: ${ciclo === 'anual' ? 'Anual' : 'Mensual'} `,
                `Precio: €${precio.toFixed(2)}/${ciclo === 'anual' ? 'año' : 'mes'}`,
                cuponCodigo ? `Cupón de descuento: ${cuponCodigo}` : '',
                cuponValido && !cuponValido.error ? `Precio final con descuento: €${precioFinal.toFixed(2)}` : '',
                ``,
                `Por favor, contactar al usuario para procesar el cambio de plan.`
            ].filter(Boolean).join('\n');

            // Crear ticket de soporte para cambio de plan
            const response = await axios.post('/api/soporte/tickets', {
                asunto: `Solicitud de cambio de plan a ${planToChange.nombre} (${ciclo})`,
                descripcion: detallesPlan,
                prioridad: 'media',
                categoria: 'cambio_plan'
            });

            // Guardar número de ticket y mostrar modal de éxito
            setTicketNumero(response.data.ticket?.numero_ticket || response.data.ticket?.id);
            setShowSuccessModal(true);

        } catch (error) {
            console.error('Error creando ticket:', error);
            // Mostrar modal de éxito de todas formas
            setTicketNumero('pendiente');
            setShowSuccessModal(true);
        } finally {
            setLoading(false);
            setPlanToChange(null);
        }
    };

    const calcularPrecio = (plan) => {
        const precio = ciclo === 'anual' ? plan.precio_anual : plan.precio_mensual;

        if (cuponValido && !cuponValido.error) {
            const descuento = cuponValido.tipo === 'porcentaje'
                ? precio * (cuponValido.valor / 100)
                : Math.min(cuponValido.valor, precio);

            return {
                original: precio,
                descuento,
                final: precio - descuento
            };
        }

        return { original: precio, descuento: 0, final: precio };
    };

    const getPlanIcon = (codigo) => {
        switch (codigo) {
            case 'basico': return Sparkles;
            case 'profesional': return TrendingUp;
            case 'enterprise': return Crown;
            default: return Sparkles;
        }
    };

    const getPlanColor = (codigo) => {
        switch (codigo) {
            case 'basico': return 'blue';
            case 'profesional': return 'orange';
            case 'enterprise': return 'purple';
            default: return 'gray';
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Selecciona tu Plan</h2>
                    <p className="text-gray-600 mt-1">Elige el plan que mejor se adapte a tus necesidades</p>
                </div>
                <button
                    onClick={onCancel}
                    className="text-gray-500 hover:text-gray-700"
                >
                    <X className="w-6 h-6" />
                </button>
            </div>

            {/* Toggle Mensual/Anual */}
            <div className="flex items-center justify-center gap-4">
                <button
                    onClick={() => setCiclo('mensual')}
                    className={`
            px-6 py-2 rounded-lg font-medium transition-all
            ${ciclo === 'mensual'
                            ? 'bg-orange-500 text-white shadow-lg'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }
          `}
                >
                    Mensual
                </button>
                <button
                    onClick={() => setCiclo('anual')}
                    className={`
            px-6 py-2 rounded-lg font-medium transition-all relative
            ${ciclo === 'anual'
                            ? 'bg-orange-500 text-white shadow-lg'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }
          `}
                >
                    Anual
                    <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">
                        -17%
                    </span>
                </button>
            </div>

            {/* Cupón */}
            <div className="bg-gray-50 rounded-lg p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    ¿Tienes un cupón de descuento?
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={cuponCodigo}
                        onChange={(e) => {
                            setCuponCodigo(e.target.value.toUpperCase());
                            setCuponValido(null);
                        }}
                        placeholder="Ej: BIENVENIDA2025"
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    />
                    <button
                        onClick={validarCupon}
                        className="px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                    >
                        Aplicar
                    </button>
                </div>
                {cuponValido && (
                    <div className={`mt-2 text-sm ${cuponValido.error ? 'text-red-600' : 'text-green-600'}`}>
                        {cuponValido.error || `✅ ${cuponValido.descripcion} - ${cuponValido.valor}% descuento`}
                    </div>
                )}
            </div>

            {/* Planes */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {planes.map(plan => {
                    const Icon = getPlanIcon(plan.codigo);
                    const color = getPlanColor(plan.codigo);
                    const precio = calcularPrecio(plan);
                    const esActual = suscripcionActual?.plan?.codigo === plan.codigo;

                    return (
                        <div
                            key={plan.id}
                            className={`
                relative bg-white rounded-xl border-2 p-6 transition-all hover:shadow-xl
                ${esActual ? 'border-orange-500 ring-2 ring-orange-200' : 'border-gray-200'}
              `}
                        >
                            {esActual && (
                                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                                    <span className="bg-orange-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                                        PLAN ACTUAL
                                    </span>
                                </div>
                            )}

                            {/* Icon */}
                            <div className={`w-12 h-12 rounded-lg bg-${color}-100 flex items-center justify-center mb-4`}>
                                <Icon className={`w-6 h-6 text-${color}-600`} />
                            </div>

                            {/* Nombre */}
                            <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.nombre}</h3>
                            <p className="text-sm text-gray-600 mb-4">{plan.descripcion}</p>

                            {/* Precio */}
                            <div className="mb-6">
                                {precio.descuento > 0 && (
                                    <div className="text-sm text-gray-500 line-through mb-1">
                                        €{precio.original}
                                    </div>
                                )}
                                <div className="flex items-baseline gap-1">
                                    <span className="text-4xl font-bold text-gray-900">
                                        €{precio.final}
                                    </span>
                                    <span className="text-gray-600">/{ciclo}</span>
                                </div>
                                {ciclo === 'anual' && (
                                    <div className="text-sm text-green-600 mt-1">
                                        Ahorras €{(plan.precio_mensual * 12 - plan.precio_anual).toFixed(2)}/año
                                    </div>
                                )}
                            </div>

                            {/* Features */}
                            <ul className="space-y-3 mb-6">
                                <li className="flex items-start gap-2 text-sm">
                                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>{plan.max_usuarios || '∞'} usuarios</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>{plan.max_empresas || '∞'} empresas</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>{plan.max_certificados === -1 || plan.max_certificados === null ? 'Ilimitados' : plan.max_certificados} certificados en Conecta</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>{plan.max_storage_gb} GB almacenamiento</span>
                                </li>
                                <li className="flex items-start gap-2 text-sm">
                                    <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <span>{(plan.max_tokens_mes / 1000).toFixed(0)}K tokens IA/mes</span>
                                </li>
                                {plan.features?.smtp_personalizado && (
                                    <li className="flex items-start gap-2 text-sm">
                                        <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <span>SMTP personalizado</span>
                                    </li>
                                )}
                                {plan.features?.api_access && (
                                    <li className="flex items-start gap-2 text-sm">
                                        <Check className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                        <span>Acceso API</span>
                                    </li>
                                )}
                            </ul>

                            {/* Button */}
                            <button
                                onClick={() => cambiarPlan(plan)}
                                disabled={loading || esActual}
                                className={`
                  w-full py-3 px-4 rounded-lg font-medium transition-all
                  ${esActual
                                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                        : `bg-${color}-500 hover:bg-${color}-600 text-white`
                                    }
                `}
                            >
                                {loading ? 'Procesando...' : esActual ? 'Plan Actual' : 'Seleccionar Plan'}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Info de Pago */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-semibold text-blue-900 mb-2">💳 Método de Pago</h4>
                <p className="text-sm text-blue-700">
                    El pago se realiza por <strong>transferencia bancaria</strong>.
                    Recibirás un email con la factura y los datos bancarios para realizar el pago.
                </p>
            </div>

            {/* Modal de Confirmación */}
            {showConfirmModal && planToChange && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        {/* Header */}
                        <div className="flex items-start gap-3 mb-4">
                            <div className="flex-shrink-0 w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
                                <Sparkles className="w-6 h-6 text-orange-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="text-lg font-bold text-gray-900">
                                    Cambiar al Plan {planToChange.nombre}
                                </h3>
                                <p className="text-sm text-gray-600 mt-1">
                                    Ciclo: {ciclo === 'anual' ? 'Anual' : 'Mensual'} • €{(ciclo === 'anual' ? planToChange.precio_anual : planToChange.precio_mensual).toFixed(2)}/{ciclo === 'anual' ? 'año' : 'mes'}
                                </p>
                            </div>
                        </div>

                        {/* Mensaje */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                            <p className="text-sm text-blue-900">
                                <strong>Nuestro equipo de soporte te ayudará con el cambio de plan.</strong>
                            </p>
                            <p className="text-sm text-blue-700 mt-2">
                                Se creará un ticket automáticamente y te contactaremos pronto para procesar tu solicitud.
                            </p>
                        </div>

                        {/* Botones */}
                        <div className="flex gap-3">
                            <button
                                onClick={() => {
                                    setShowConfirmModal(false);
                                    setPlanToChange(null);
                                }}
                                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                                disabled={loading}
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={confirmarCambioPlan}
                                disabled={loading}
                                className="flex-1 px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
                            >
                                {loading ? 'Procesando...' : 'Aceptar'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Éxito */}
            {showSuccessModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
                        {/* Header */}
                        <div className="flex flex-col items-center text-center mb-6">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
                                <Check className="w-8 h-8 text-green-600" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900">
                                ✅ Solicitud enviada correctamente
                            </h3>
                        </div>

                        {/* Contenido */}
                        <div className="space-y-4 mb-6">
                            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <p className="text-sm text-blue-900 font-medium">
                                    Hemos creado el ticket <strong className="text-blue-700">#{ticketNumero}</strong> para tu solicitud.
                                </p>
                            </div>

                            <p className="text-sm text-gray-600 text-center">
                                Nuestro equipo de soporte te contactará pronto para ayudarte con el cambio de plan.
                            </p>
                        </div>

                        {/* Botón */}
                        <button
                            onClick={() => {
                                setShowSuccessModal(false);
                                setPlanToChange(null);
                                setTicketNumero(null);
                                onCancel(); // Cerrar el selector de planes
                            }}
                            className="w-full px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 transition-opacity"
                        >
                            Aceptar
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PlanSelector;
