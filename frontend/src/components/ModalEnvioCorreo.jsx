// frontend/src/components/ModalEnvioCorreo.jsx
import React, { useState } from 'react';
import { Mail, FileText, Send, X, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function ModalEnvioCorreo({
    nominas,
    segurosSociales = [],
    empresa = null,
    onClose,
    onEnviado
}) {
    const [email, setEmail] = useState('');
    const [modoEnvio, setModoEnvio] = useState('NOMINAS');
    const [segurosSeleccionados, setSegurosSeleccionados] = useState([]);
    const [nominasSeleccionadas, setNominasSeleccionadas] = useState([]);
    const [enviando, setEnviando] = useState(false);
    const [mostrarSugerencias, setMostrarSugerencias] = useState(false);

    // Periodo
    const [mes, setMes] = useState(new Date().getMonth() + 1);
    const [año, setAño] = useState(new Date().getFullYear());
    const [buscandoDocumentos, setBuscandoDocumentos] = useState(false);
    const [documentosCargados, setDocumentosCargados] = useState(false);

    // Documentos por tipo
    const [nominasDisponibles, setNominasDisponibles] = useState([]);
    const [rntDisponibles, setRntDisponibles] = useState([]);
    const [rlcDisponibles, setRlcDisponibles] = useState([]);

    // Tipos seleccionados
    const [tiposSeleccionados, setTiposSeleccionados] = useState({
        nominas: true,
        rnt: false,
        rlc: false
    });

    // Preparar sugerencias de emails
    const emailsSugeridos = empresa ? [
        empresa.email,
        ...(empresa.emails_extra || [])
    ].filter(e => e && e.trim() !== '') : [];

    const rntDisponible = segurosSociales.find(doc =>
        doc.nombre.toUpperCase().includes('RNT')
    );

    const buscarDocumentosPeriodo = async () => {
        if (!empresa || !empresa.id) {
            toast.error('No se ha seleccionado una empresa');
            return;
        }

        setBuscandoDocumentos(true);
        const periodo = `${año}${mes.toString().padStart(2, '0')}`;

        try {
            const response = await axios.get('/api/buscar-documentos-periodo', {
                params: {
                    empresa_id: empresa.id,
                    periodo: periodo
                }
            });

            if (response.data.success) {
                setNominasDisponibles(response.data.nominas || []);
                setRntDisponibles(response.data.rnt || []);
                setRlcDisponibles(response.data.rlc || []);
                setDocumentosCargados(true);

                const total = response.data.total || 0;
                toast.success(`✅ Encontrados ${total} documento(s) para ${mes}/${año}`);
            } else {
                toast.error(response.data.message || 'Error al buscar documentos');
            }
        } catch (error) {
            const errorMsg = error.response?.data?.message || 'Error al buscar documentos';
            toast.error(errorMsg);
        } finally {
            setBuscandoDocumentos(false);
        }
    };


    const handleEnviar = async () => {
        if (!email) {
            toast.error('Ingresa un correo electrónico');
            return;
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            toast.error('Ingresa un correo electrónico válido');
            return;
        }

        setEnviando(true);

        try {
            // Preparar IDs según el modo
            let nominas_ids = [];
            let seguros_ids = [];

            if (modoEnvio === 'PERSONALIZADO' && documentosCargados) {
                // Usar documentos del periodo seleccionado
                if (tiposSeleccionados.nominas) {
                    nominas_ids = nominasDisponibles.map(n => n.id);
                }
                if (tiposSeleccionados.rnt) {
                    seguros_ids = [...seguros_ids, ...rntDisponibles.map(d => d.id)];
                }
                if (tiposSeleccionados.rlc) {
                    seguros_ids = [...seguros_ids, ...rlcDisponibles.map(d => d.id)];
                }
            } else if (modoEnvio === 'PERSONALIZADO') {
                // Modo personalizado antiguo (sin periodo)
                nominas_ids = nominasSeleccionadas;
                seguros_ids = segurosSeleccionados;
            } else if (modoEnvio === 'NOMINAS') {
                nominas_ids = nominas.map(n => n.id);
            } else if (modoEnvio === 'NOMINAS_RNT') {
                nominas_ids = nominas.map(n => n.id);
                seguros_ids = rntDisponible ? [rntDisponible.id] : [];
            }

            const response = await axios.post('/api/enviar-correo-nominas', {
                email: email,
                modo: modoEnvio,
                nominas_ids: nominas_ids,
                seguros_ids: seguros_ids
            });

            if (response.data.success) {
                toast.success(`✅ Correo enviado a ${email}`);
                if (onEnviado) onEnviado();
                onClose();
            } else {
                toast.error(response.data.message || 'Error al enviar');
            }
        } catch (error) {
            const errorMsg = error.response?.data?.message || error.response?.data?.error || 'Error al enviar correo';
            toast.error(errorMsg);
        } finally {
            setEnviando(false);
        }
    };

    const toggleSeguro = (docId) => {
        setSegurosSeleccionados(prev =>
            prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
        );
    };

    const toggleNomina = (nominaId) => {
        setNominasSeleccionadas(prev =>
            prev.includes(nominaId) ? prev.filter(id => id !== nominaId) : [...prev, nominaId]
        );
    };

    const contarAdjuntos = () => {
        if (modoEnvio === 'NOMINAS') return nominas.length;
        if (modoEnvio === 'NOMINAS_RNT') return nominas.length + (rntDisponible ? 1 : 0);
        return nominasSeleccionadas.length + segurosSeleccionados.length;
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <Mail className="w-6 h-6 text-blue-600" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900">Enviar Correo</h2>
                            <p className="text-sm text-gray-500">Nóminas y Seguros Sociales</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Email Input */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Correo Electrónico de Destino <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            onFocus={() => setMostrarSugerencias(true)}
                            onBlur={() => setTimeout(() => setMostrarSugerencias(false), 200)}
                            placeholder="ejemplo@empresa.com"
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
                            autoFocus
                        />

                        {/* Sugerencias de emails */}
                        {mostrarSugerencias && emailsSugeridos.length > 0 && (
                            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg">
                                <div className="p-2">
                                    <p className="text-xs text-gray-500 mb-2 px-2">Emails registrados:</p>
                                    {emailsSugeridos.map((emailSug, idx) => (
                                        <button
                                            key={idx}
                                            type="button"
                                            onClick={() => {
                                                setEmail(emailSug);
                                                setMostrarSugerencias(false);
                                            }}
                                            className="w-full text-left px-3 py-2 hover:bg-blue-50 rounded transition text-sm"
                                        >
                                            {emailSug}
                                            {idx === 0 && <span className="ml-2 text-xs text-blue-600">(Principal)</span>}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Selector de Periodo */}
                <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        📅 Periodo de Documentos
                    </h3>

                    <div className="grid grid-cols-3 gap-3">
                        {/* Mes */}
                        <div className="col-span-2">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Mes</label>
                            <select
                                value={mes}
                                onChange={(e) => setMes(parseInt(e.target.value))}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                            >
                                <option value={1}>Enero</option>
                                <option value={2}>Febrero</option>
                                <option value={3}>Marzo</option>
                                <option value={4}>Abril</option>
                                <option value={5}>Mayo</option>
                                <option value={6}>Junio</option>
                                <option value={7}>Julio</option>
                                <option value={8}>Agosto</option>
                                <option value={9}>Septiembre</option>
                                <option value={10}>Octubre</option>
                                <option value={11}>Noviembre</option>
                                <option value={12}>Diciembre</option>
                            </select>
                        </div>

                        {/* Año */}
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Año</label>
                            <select
                                value={año}
                                onChange={(e) => setAño(parseInt(e.target.value))}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                            >
                                {[...Array(3)].map((_, i) => {
                                    const year = new Date().getFullYear() - i;
                                    return <option key={year} value={year}>{year}</option>;
                                })}
                            </select>
                        </div>
                    </div>

                    {/* Botón Buscar */}
                    <button
                        onClick={buscarDocumentosPeriodo}
                        disabled={buscandoDocumentos}
                        className="mt-3 w-full px-4 py-2.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium shadow-md"
                    >
                        {buscandoDocumentos ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Buscando...
                            </>
                        ) : (
                            <>
                                🔍 Buscar Documentos
                            </>
                        )}
                    </button>

                    <p className="text-xs text-gray-600 mt-2 text-center">
                        Periodo: <span className="font-mono font-semibold text-purple-700">{año}{mes.toString().padStart(2, '0')}</span>
                    </p>
                </div>

                {/* Modo de Envío */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-3">Modo de Envío</label>
                    <div className="grid grid-cols-3 gap-3">
                        <button
                            onClick={() => setModoEnvio('NOMINAS')}
                            className={`p-4 border-2 rounded-lg transition-all ${modoEnvio === 'NOMINAS'
                                ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-md'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                }`}
                        >
                            <FileText className={`w-6 h-6 mx-auto mb-2 ${modoEnvio === 'NOMINAS' ? 'text-blue-600' : 'text-gray-400'}`} />
                            <p className="font-medium text-sm">Solo Nóminas</p>
                            <p className="text-xs text-gray-500 mt-1">
                                {documentosCargados ? nominasDisponibles.length : nominas.length} archivo(s)
                            </p>
                        </button>

                        <button
                            onClick={() => setModoEnvio('NOMINAS_RNT')}
                            disabled={documentosCargados ? rntDisponibles.length === 0 : !rntDisponible}
                            className={`p-4 border-2 rounded-lg transition-all ${modoEnvio === 'NOMINAS_RNT'
                                ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-md'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                } ${(documentosCargados ? rntDisponibles.length === 0 : !rntDisponible) ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            <div className="relative">
                                <FileText className={`w-6 h-6 mx-auto mb-2 ${modoEnvio === 'NOMINAS_RNT' ? 'text-blue-600' : 'text-gray-400'}`} />
                                {(documentosCargados ? rntDisponibles.length > 0 : rntDisponible) && <CheckCircle className="w-4 h-4 text-green-500 absolute -top-1 -right-1" />}
                            </div>
                            <p className="font-medium text-sm">Nóminas + RNT</p>
                            <p className="text-xs text-gray-500 mt-1">
                                {documentosCargados
                                    ? (nominasDisponibles.length + rntDisponibles.length)
                                    : (nominas.length + (rntDisponible ? 1 : 0))
                                } archivo(s)
                            </p>
                        </button>

                        <button
                            onClick={() => setModoEnvio('PERSONALIZADO')}
                            className={`p-4 border-2 rounded-lg transition-all ${modoEnvio === 'PERSONALIZADO'
                                ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-md'
                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                }`}
                        >
                            <FileText className={`w-6 h-6 mx-auto mb-2 ${modoEnvio === 'PERSONALIZADO' ? 'text-blue-600' : 'text-gray-400'}`} />
                            <p className="font-medium text-sm">Personalizado</p>
                            <p className="text-xs text-gray-500 mt-1">
                                {documentosCargados ? 'Elige tipos' : 'Elige adjuntos'}
                            </p>
                        </button>
                    </div>
                </div>

                {/* Opciones Personalizadas - Tipos de Documentos */}
                {modoEnvio === 'PERSONALIZADO' && documentosCargados && (
                    <div className="mb-6 space-y-3">
                        <h3 className="font-semibold text-gray-900 mb-3">Seleccionar Tipos de Documentos</h3>

                        {/* Nóminas */}
                        <label className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition ${tiposSeleccionados.nominas ? 'border-primary bg-primary-light' : 'border-gray-200 hover:border-orange-300 hover:bg-primary-light/50'
                            }`}>
                            <input
                                type="checkbox"
                                checked={tiposSeleccionados.nominas}
                                onChange={(e) => setTiposSeleccionados({ ...tiposSeleccionados, nominas: e.target.checked })}
                                disabled={nominasDisponibles.length === 0}
                                className="w-5 h-5 text-primary rounded focus:ring-2 focus:ring-primary disabled:opacity-50"
                            />
                            <div className="flex-1">
                                <span className="font-medium text-gray-900">📄 Nóminas</span>
                                <p className="text-sm text-gray-600">{nominasDisponibles.length} disponible(s)</p>
                            </div>
                        </label>

                        {/* RNT */}
                        <label className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition ${tiposSeleccionados.rnt ? 'border-green-500 bg-green-50' : 'border-gray-200 hover:border-green-300 hover:bg-green-50/50'
                            } ${rntDisponibles.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}>
                            <input
                                type="checkbox"
                                checked={tiposSeleccionados.rnt}
                                onChange={(e) => setTiposSeleccionados({ ...tiposSeleccionados, rnt: e.target.checked })}
                                disabled={rntDisponibles.length === 0}
                                className="w-5 h-5 text-green-600 rounded focus:ring-2 focus:ring-green-500 disabled:opacity-50"
                            />
                            <div className="flex-1">
                                <span className="font-medium text-gray-900">👥 RNT (Relación Nominal)</span>
                                <p className="text-sm text-gray-600">{rntDisponibles.length} disponible(s)</p>
                            </div>
                        </label>

                        {/* RLC */}
                        <label className={`flex items-center gap-3 p-4 rounded-lg border-2 cursor-pointer transition ${tiposSeleccionados.rlc ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                            } ${rlcDisponibles.length === 0 ? 'opacity-50 cursor-not-allowed' : ''}`}>
                            <input
                                type="checkbox"
                                checked={tiposSeleccionados.rlc}
                                onChange={(e) => setTiposSeleccionados({ ...tiposSeleccionados, rlc: e.target.checked })}
                                disabled={rlcDisponibles.length === 0}
                                className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                            />
                            <div className="flex-1">
                                <span className="font-medium text-gray-900">💰 RLC (Relación de Cotización)</span>
                                <p className="text-sm text-gray-600">{rlcDisponibles.length} disponible(s)</p>
                            </div>
                        </label>

                    </div>
                )}

                {/* Opciones Personalizadas Antiguas (sin periodo) */}
                {modoEnvio === 'PERSONALIZADO' && !documentosCargados && (
                    <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <p className="text-sm text-yellow-800 text-center">
                            💡 Selecciona un periodo y haz clic en "Buscar Documentos" para elegir qué tipos enviar
                        </p>
                    </div>
                )}

                {/* Preview */}
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm font-medium text-blue-900 mb-2">Vista Previa:</p>
                    <ul className="text-sm text-blue-700 space-y-1">
                        <li className="flex items-center gap-2">
                            <Mail className="w-4 h-4" />
                            <span><strong>Destinatario:</strong> {email || '(sin especificar)'}</span>
                        </li>
                        <li className="flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            <span><strong>Adjuntos:</strong> {contarAdjuntos()} archivo(s)</span>
                        </li>
                        {modoEnvio === 'PERSONALIZADO' && (
                            <>
                                <li className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4" />
                                    <span><strong>Nóminas:</strong> {nominasSeleccionadas.length} seleccionada(s)</span>
                                </li>
                                <li className="flex items-center gap-2">
                                    <CheckCircle className="w-4 h-4" />
                                    <span><strong>Seguros Sociales:</strong> {segurosSeleccionados.length} seleccionado(s)</span>
                                </li>
                            </>
                        )}
                    </ul>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleEnviar}
                        disabled={!email || enviando}
                        className="flex-1 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 font-medium shadow-md hover:shadow-lg"
                    >
                        {enviando ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Enviando...
                            </>
                        ) : (
                            <>
                                <Send className="w-5 h-5" />
                                Enviar Correo
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
