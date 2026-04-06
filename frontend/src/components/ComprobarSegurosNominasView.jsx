// frontend/src/components/ComprobarSegurosNominasView.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { FileCheck, Calendar, Building2, FileText, Eye, ChevronLeft, FolderPlus, Mail, Search } from 'lucide-react';
import ModalEnvioCorreo from './ModalEnvioCorreo';
import ModalEnvioCorreoGrupo from './ModalEnvioCorreoGrupo';

export default function ComprobarSegurosNominasView() {
    const currentDate = new Date();
    const [mes, setMes] = useState(currentDate.getMonth() + 1);
    const [anio, setAnio] = useState(currentDate.getFullYear());
    const [empresas, setEmpresas] = useState([]);
    const [loading, setLoading] = useState(false);
    const [empresaSeleccionada, setEmpresaSeleccionada] = useState(null);
    const [documentos, setDocumentos] = useState(null);
    const [loadingDocs, setLoadingDocs] = useState(false);
    const [pdfSeleccionado, setPdfSeleccionado] = useState(null);
    const [creandoGrupo, setCreandoGrupo] = useState(false);

    // Estados para envío de correo
    const [mostrarModalEnvio, setMostrarModalEnvio] = useState(false);
    const [empresaParaEnviar, setEmpresaParaEnviar] = useState(null);
    const [nominasParaEnviar, setNominasParaEnviar] = useState([]);
    const [rntDisponible, setRntDisponible] = useState(null);
    // Estados para envío masivo
    const [enviandoMasivo, setEnviandoMasivo] = useState(false);
    const [mostrarModalConfirmacion, setMostrarModalConfirmacion] = useState(false);
    const [mostrarModalResultados, setMostrarModalResultados] = useState(false);
    const [modoMasivo, setModoMasivo] = useState('NOMINAS');
    const [empresasConEmail, setEmpresasConEmail] = useState([]);
    const [empresasSinEmail, setEmpresasSinEmail] = useState([]);
    const [resultadosMasivo, setResultadosMasivo] = useState(null);

    const [activeTab, setActiveTab] = useState('empresas');
    const [grupos, setGrupos] = useState([]);
    const [loadingGrupos, setLoadingGrupos] = useState(false);
    const [grupoSeleccionado, setGrupoSeleccionado] = useState(null);
    const [grupoParaEnviar, setGrupoParaEnviar] = useState(null);
    const [mostrarModalGrupo, setMostrarModalGrupo] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');

    // Estados para búsqueda de documentos por periodo (envío masivo)
    const [mesMasivo, setMesMasivo] = useState(currentDate.getMonth() + 1);
    const [anioMasivo, setAnioMasivo] = useState(currentDate.getFullYear());
    const [tiposDocumentosMasivo, setTiposDocumentosMasivo] = useState({
        nominas: true,
        rnt: false,
        rlc: false
    });

    const meses = [
        { value: 1, label: 'Enero' },
        { value: 2, label: 'Febrero' },
        { value: 3, label: 'Marzo' },
        { value: 4, label: 'Abril' },
        { value: 5, label: 'Mayo' },
        { value: 6, label: 'Junio' },
        { value: 7, label: 'Julio' },
        { value: 8, label: 'Agosto' },
        { value: 9, label: 'Septiembre' },
        { value: 10, label: 'Octubre' },
        { value: 11, label: 'Noviembre' },
        { value: 12, label: 'Diciembre' }
    ];

    const anios = Array.from({ length: 5 }, (_, i) => currentDate.getFullYear() - i);

    useEffect(() => {
        if (activeTab === 'empresas') {
            cargarDatos();
        } else {
            cargarDatosGrupos();
        }
    }, [mes, anio, activeTab]);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/comprobar-seguros-nominas', {
                params: { mes, anio },
                withCredentials: true
            });

            if (response.data.success) {
                setEmpresas(response.data.empresas);
            }
        } catch (error) {
            console.error('Error cargando datos:', error);
            toast.error('Error al cargar datos');
        } finally {
            setLoading(false);
        }
    };

    const cargarDatosGrupos = async () => {
        setLoadingGrupos(true);
        try {
            const response = await axios.get('/api/comprobar-seguros-nominas/grupos', {
                params: { mes, anio },
                withCredentials: true
            });

            if (response.data.success) {
                setGrupos(response.data.grupos);
            }
        } catch (error) {
            console.error('Error cargando grupos:', error);
            toast.error('Error al cargar grupos');
        } finally {
            setLoadingGrupos(false);
        }
    };

    const verDetalles = async (empresa) => {
        setEmpresaSeleccionada(empresa);
        setLoadingDocs(true);

        try {
            const response = await axios.get(`/api/empresa/${empresa.id}/documentos-mes`, {
                params: { mes, anio },
                withCredentials: true
            });

            if (response.data.success) {
                setDocumentos(response.data);
            }
        } catch (error) {
            console.error('Error cargando documentos:', error);
            toast.error('Error al cargar documentos');
        } finally {
            setLoadingDocs(false);
        }
    };

    const cerrarDetalle = () => {
        setEmpresaSeleccionada(null);
        setDocumentos(null);
        setPdfSeleccionado(null);
    };

    const verPdf = (doc) => {
        setPdfSeleccionado(doc);
    };

    const getIndicadorColor = (count) => {
        return count >= 1
            ? 'text-green-600 bg-green-50 dark:bg-green-900/40 dark:text-green-300 status-badge'
            : 'text-red-600 bg-red-50 dark:bg-red-900/40 dark:text-red-300 status-badge';
    };

    const mesNombre = meses.find(m => m.value === mes)?.label || '';

    const crearGrupoAutomatico = async () => {
        if (!empresaSeleccionada || !documentos) return;

        // Obtener todos los IDs de documentos
        const todosLosDocumentos = [...documentos.nominas, ...documentos.seguros];

        if (todosLosDocumentos.length === 0) {
            toast.error('No hay documentos para agregar al grupo');
            return;
        }

        // Crear nombre del grupo: "EMPRESA - Mes Año - Nóminas y Seguros"
        const nombreGrupo = `${empresaSeleccionada.nombre} - ${mesNombre} ${anio} - Nóminas y Seguros`;

        setCreandoGrupo(true);
        try {
            // Crear el grupo
            const responseGrupo = await axios.post(
                '/api/grupos-documentos',
                {
                    nombre: nombreGrupo,
                    empresa_id: empresaSeleccionada.id,
                    descripcion: `Grupo automático de Nóminas y Seguros Sociales para ${mesNombre} ${anio}`
                },
                { withCredentials: true }
            );

            if (responseGrupo.data.success) {
                const grupoId = responseGrupo.data.grupo.id;

                // Agregar todos los documentos al grupo
                const promesas = todosLosDocumentos.map(doc =>
                    axios.post(
                        `/api/grupos-documentos/${grupoId}/documentos`,
                        { documento_id: doc.id },
                        { withCredentials: true }
                    )
                );

                await Promise.all(promesas);

                toast.success(`Grupo "${nombreGrupo}" creado con ${todosLosDocumentos.length} documentos`);
                cerrarDetalle();
            }
        } catch (error) {
            console.error('Error creando grupo:', error);
            toast.error('Error al crear el grupo');
        } finally {
            setCreandoGrupo(false);
        }
    };

    const abrirModalEnvioGrupo = (grupo) => {
        if (!grupo.email) {
            toast.error('Grupo sin email configurado');
            return;
        }
        setGrupoParaEnviar(grupo);
        setMostrarModalGrupo(true);
    };

    const enviarCorreoGrupo = async (grupo) => {
        // Lógica antigua de envío directo desactivada en favor del modal
        abrirModalEnvioGrupo(grupo);
    };

    const handleEnvioMasivo = () => {
        // Filtrar empresas con/sin email
        const conEmail = empresas.filter(e => e.email && e.email.trim() !== '');
        const sinEmail = empresas.filter(e => !e.email || e.email.trim() === '');

        setEmpresasConEmail(conEmail);
        setEmpresasSinEmail(sinEmail);
        setMostrarModalConfirmacion(true);
    };

    const confirmarEnvioMasivo = async () => {
        setMostrarModalConfirmacion(false);
        setEnviandoMasivo(true);

        const toastId = toast.loading('Iniciando envío masivo...');

        try {
            const response = await axios.post('/api/enviar-correos-masivo', {
                mes: mesMasivo,
                anio: anioMasivo,
                tipos_documentos: tiposDocumentosMasivo
            }, { withCredentials: true });

            if (response.data.success) {
                if (response.data.async) {
                    // ⚡ PROCESAMIENTO ASÍNCRONO (50+ empresas)
                    toast.success(
                        `Procesando ${response.data.total_empresas} empresas en segundo plano`,
                        { id: toastId, duration: 5000 }
                    );

                    // Iniciar polling para monitorear progreso
                    monitorearTareaAsincrona(response.data.task_id, toastId);
                } else {
                    // 🔄 PROCESAMIENTO SÍNCRONO (< 50 empresas)
                    const { resultados } = response.data;

                    toast.success(
                        `✅ ${resultados.enviados} enviados | ❌ ${resultados.errores} errores | ⚠️ ${resultados.omitidos} omitidos`,
                        { id: toastId, duration: 5000 }
                    );

                    setResultadosMasivo(resultados);
                    setMostrarModalResultados(true);
                    setEnviandoMasivo(false);
                }
            } else {
                toast.error('Error en envío masivo', { id: toastId });
                setEnviandoMasivo(false);
            }
        } catch (error) {
            toast.error(`Error: ${error.message}`, { id: toastId });
            setEnviandoMasivo(false);
        }
    };

    // Nueva función para monitorear tarea asíncrona
    const monitorearTareaAsincrona = async (taskId, toastId) => {
        const intervalo = setInterval(async () => {
            try {
                const response = await axios.get(
                    `/api/enviar-correos-masivo/status/${taskId}`,
                    { withCredentials: true }
                );

                const { state, current, total, empresa, enviados, errores, result } = response.data;

                if (state === 'PROGRESS') {
                    // Actualizar toast con progreso
                    toast.loading(
                        `📤 Enviando ${current}/${total} - ${empresa || ''}`,
                        { id: toastId }
                    );
                } else if (state === 'SUCCESS') {
                    // Tarea completada
                    clearInterval(intervalo);

                    toast.success(
                        `✅ ${result.enviados} enviados | ❌ ${result.errores} errores | ⚠️ ${result.omitidos} omitidos`,
                        { id: toastId, duration: 5000 }
                    );

                    setResultadosMasivo(result);
                    setMostrarModalResultados(true);
                    setEnviandoMasivo(false);
                } else if (state === 'FAILURE') {
                    // Error en la tarea
                    clearInterval(intervalo);
                    toast.error('Error en el envío masivo', { id: toastId });
                    setEnviandoMasivo(false);
                }
            } catch (error) {
                clearInterval(intervalo);
                toast.error('Error consultando estado', { id: toastId });
                setEnviandoMasivo(false);
            }
        }, 2000);
    };

    return (
        <div className="p-6">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center gap-3 mb-2">
                    <FileCheck className="w-8 h-8 text-primary" />
                    <h1 className="text-2xl font-bold text-gray-800">Comprobar Seguros y Nóminas</h1>
                </div>
                <p className="text-gray-600">Verificar documentos de Nóminas y Seguros Sociales por empresa o holding</p>
            </div>

            {/* Filtros */}
            <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <Calendar className="w-5 h-5 text-gray-500" />
                            <label className="font-medium text-gray-700">Mes:</label>
                            <select
                                value={mes}
                                onChange={(e) => setMes(parseInt(e.target.value))}
                                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                            >
                                {meses.map(m => (
                                    <option key={m.value} value={m.value}>{m.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <label className="font-medium text-gray-700">Año:</label>
                            <select
                                value={anio}
                                onChange={(e) => setAnio(parseInt(e.target.value))}
                                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                            >
                                {anios.map(a => (
                                    <option key={a} value={a}>{a}</option>
                                ))}
                            </select>
                        </div>

                        {/* Buscador */}
                        <div className="flex items-center gap-2 flex-1 max-w-md">
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="Buscar por nombre..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                                />
                                {searchTerm && (
                                    <button
                                        onClick={() => setSearchTerm('')}
                                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                                    >
                                        ×
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Botón Envío Masivo */}
                    <button
                        onClick={handleEnvioMasivo}
                        disabled={empresas.length === 0 || enviandoMasivo}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                    >
                        <Mail className="w-5 h-5" />
                        {enviandoMasivo ? 'Enviando...' : 'Enviar Correos Masivos'}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 mb-6">
                <button
                    onClick={() => setActiveTab('empresas')}
                    className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                        activeTab === 'empresas'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Empresas Individuales
                </button>
                <button
                    onClick={() => setActiveTab('grupos')}
                    className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                        activeTab === 'grupos'
                            ? 'border-primary text-primary'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    Grupos de Empresas
                </button>
            </div>

            {/* Tabla de empresas / grupos */}
            {activeTab === 'empresas' ? (
                loading ? (
                    <div className="flex justify-center items-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-sm overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Empresa
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Nóminas
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Seguros Sociales
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Acciones
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {empresas
                                    .filter(empresa => {
                                        if (!searchTerm) return true;
                                        const search = searchTerm.toLowerCase();
                                        return (
                                            empresa.nombre.toLowerCase().includes(search) ||
                                            (empresa.nif && empresa.nif.toLowerCase().includes(search))
                                        );
                                    })
                                    .map((empresa) => (
                                        <tr key={empresa.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center">
                                                    <Building2 className="w-5 h-5 text-gray-400 mr-2" />
                                                    <span className="text-sm font-medium text-gray-900">{empresa.nombre}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${getIndicadorColor(empresa.nominas_count)}`}>
                                                    {empresa.nominas_count}/1
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${getIndicadorColor(empresa.seguros_count)}`}>
                                                    {empresa.seguros_count}/1
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                <div className="flex items-center justify-center gap-2">
                                                    <button
                                                        onClick={() => verDetalles(empresa)}
                                                        className="inline-flex items-center px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                                                    >
                                                        <Eye className="w-4 h-4 mr-1" />
                                                        Ver
                                                    </button>
                                                    <button
                                                        onClick={() => abrirModalEnvio(empresa)}
                                                        disabled={empresa.nominas_count === 0 && empresa.seguros_count === 0}
                                                        className="inline-flex items-center px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                                        title="Enviar correo con nóminas y/o seguros sociales"
                                                    >
                                                        <Mail className="w-4 h-4 mr-1" />
                                                        Enviar
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                            </tbody>
                        </table>
                    </div>
                )
            ) : (
                loadingGrupos ? (
                    <div className="flex justify-center items-center h-64">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                    </div>
                ) : (
                    <div className="bg-white rounded-lg shadow-sm overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Grupo / Holding
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Estado Nóminas
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Estado Seguros
                                    </th>
                                    <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Acciones
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                    {grupos
                                        .filter(g => !searchTerm || g.nombre.toLowerCase().includes(searchTerm.toLowerCase()))
                                        .map((grupo) => (
                                            <React.Fragment key={grupo.id}>
                                                <tr className="hover:bg-gray-50 transition-colors">
                                                    <td className="px-6 py-4 whitespace-nowrap">
                                                        <div className="flex flex-col">
                                                            <div className="flex items-center">
                                                                <FolderPlus className={`w-5 h-5 mr-2 ${grupoSeleccionado?.id === grupo.id ? 'text-primary' : 'text-indigo-500'}`} />
                                                                <span className="text-sm font-bold text-gray-900">{grupo.nombre}</span>
                                                            </div>
                                                            <span className="text-xs text-gray-500 ml-7">{grupo.total_empresas} empresas</span>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                                        <div className="flex flex-col items-center gap-1">
                                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
                                                                grupo.empresas_con_nominas === grupo.total_empresas 
                                                                    ? 'text-green-600 bg-green-50' 
                                                                    : 'text-amber-600 bg-amber-50'
                                                            }`}>
                                                                {grupo.empresas_con_nominas} / {grupo.total_empresas}
                                                            </span>
                                                            <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                                <div 
                                                                    className="h-full bg-green-500 transition-all duration-500" 
                                                                    style={{ width: `${(grupo.empresas_con_nominas / grupo.total_empresas) * 100}%` }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                                        <div className="flex flex-col items-center gap-1">
                                                            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
                                                                grupo.empresas_con_seguros === grupo.total_empresas 
                                                                    ? 'text-green-600 bg-green-50' 
                                                                    : 'text-amber-600 bg-amber-50'
                                                            }`}>
                                                                {grupo.empresas_con_seguros} / {grupo.total_empresas}
                                                            </span>
                                                            <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                                                <div 
                                                                    className="h-full bg-blue-500 transition-all duration-500" 
                                                                    style={{ width: `${(grupo.empresas_con_seguros / grupo.total_empresas) * 100}%` }}
                                                                />
                                                            </div>
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 whitespace-nowrap text-center">
                                                        <div className="flex items-center justify-center gap-2">
                                                            <button
                                                                onClick={() => enviarCorreoGrupo(grupo)}
                                                                disabled={!grupo.email}
                                                                className={`p-2 rounded-lg transition-colors ${
                                                                    !grupo.email 
                                                                        ? 'text-gray-300 cursor-not-allowed' 
                                                                        : 'text-indigo-600 hover:bg-indigo-50'
                                                                }`}
                                                                title={!grupo.email ? "Grupo sin email configurado" : "Enviar correo agrupado al Holding"}
                                                            >
                                                                <Mail className="w-5 h-5" />
                                                            </button>
                                                            <button
                                                                onClick={() => setGrupoSeleccionado(grupoSeleccionado?.id === grupo.id ? null : grupo)}
                                                                className={`p-2 rounded-lg transition-colors ${
                                                                    grupoSeleccionado?.id === grupo.id 
                                                                        ? 'bg-primary text-white shadow-sm' 
                                                                        : 'text-gray-600 hover:bg-gray-50'
                                                                }`}
                                                                title={grupoSeleccionado?.id === grupo.id ? "Ocultar detalles" : "Ver detalles"}
                                                            >
                                                                <Eye className="w-5 h-5" />
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                                {grupoSeleccionado?.id === grupo.id && (
                                                    <tr className="bg-gray-50/50">
                                                        <td colSpan="4" className="px-8 py-4">
                                                            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-2 duration-300">
                                                                <table className="min-w-full divide-y divide-gray-100">
                                                                    <thead className="bg-gray-50">
                                                                        <tr>
                                                                            <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Empresa del Grupo</th>
                                                                            <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado Nóminas</th>
                                                                            <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado Seguros</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody className="divide-y divide-gray-100">
                                                                        {grupo.detalle.map((emp) => (
                                                                            <tr key={emp.id} className="hover:bg-gray-50/50 transition-colors">
                                                                                <td className="px-6 py-3 text-sm text-gray-700 font-medium">
                                                                                    <div className="flex items-center justify-between">
                                                                                        <div className="flex items-center gap-2">
                                                                                            <div className="w-2 h-2 rounded-full bg-indigo-400"></div>
                                                                                            {emp.nombre}
                                                                                        </div>
                                                                                        <button
                                                                                            onClick={() => verDetalles({ id: emp.id, nombre: emp.nombre })}
                                                                                            className="p-1 px-2 text-[10px] uppercase font-bold text-indigo-600 hover:bg-indigo-50 rounded border border-indigo-100 transition-colors flex items-center gap-1"
                                                                                            title="Ver documentos detallados"
                                                                                        >
                                                                                            <Eye className="w-3 h-3" /> Ver
                                                                                        </button>
                                                                                    </div>
                                                                                </td>
                                                                                <td className="px-6 py-3 text-center">
                                                                                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                                                                                        emp.nominas_count > 0 
                                                                                            ? 'text-green-700 bg-green-50 border border-green-100' 
                                                                                            : 'text-rose-500 bg-rose-50 border border-rose-100'
                                                                                    }`}>
                                                                                        <div className={`w-1.5 h-1.5 rounded-full ${emp.nominas_count > 0 ? 'bg-green-500' : 'bg-rose-500'}`}></div>
                                                                                        {emp.nominas_count > 0 ? 'Cargado' : 'Pendiente'}
                                                                                    </span>
                                                                                </td>
                                                                                <td className="px-6 py-3 text-center">
                                                                                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                                                                                        emp.seguros_count > 0 
                                                                                            ? 'text-blue-700 bg-blue-50 border border-blue-100' 
                                                                                            : 'text-rose-500 bg-rose-50 border border-rose-100'
                                                                                    }`}>
                                                                                        <div className={`w-1.5 h-1.5 rounded-full ${emp.seguros_count > 0 ? 'bg-blue-500' : 'bg-rose-500'}`}></div>
                                                                                        {emp.seguros_count > 0 ? 'Cargado' : 'Pendiente'}
                                                                                    </span>
                                                                                </td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                )}
                                            </React.Fragment>
                                        ))}
                            </tbody>
                        </table>
                    </div>
                )
            )}


            {/* Modal de detalles */}
            {empresaSeleccionada && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
                        {/* Header del modal */}
                        <div className="bg-linear-to-r from-orange-500 to-red-500 px-6 py-4 text-white">
                            <div className="flex items-center justify-between">
                                <div>
                                    <h2 className="text-xl font-bold">{empresaSeleccionada.nombre}</h2>
                                    <p className="text-orange-100 text-sm">{mesNombre} {anio}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={crearGrupoAutomatico}
                                        disabled={creandoGrupo || (!documentos?.nominas?.length && !documentos?.seguros?.length)}
                                        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <FolderPlus className="w-4 h-4" />
                                        {creandoGrupo ? 'Creando...' : 'Crear Grupo'}
                                    </button>
                                    <button
                                        onClick={cerrarDetalle}
                                        className="text-white hover:bg-red-800 rounded-lg p-2 transition-colors"
                                    >
                                        <ChevronLeft className="w-6 h-6" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Contenido del modal */}
                        <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
                            {loadingDocs ? (
                                <div className="flex justify-center items-center h-64">
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                                </div>
                            ) : documentos ? (
                                <>
                                    <div className="grid grid-cols-2 gap-6">
                                        {/* Columna Nóminas */}
                                        <div>
                                            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                                                <FileText className="w-5 h-5 mr-2 text-primary" />
                                                Nóminas ({documentos.nominas.length})
                                            </h3>
                                            <div className="space-y-2">
                                                {documentos.nominas.length > 0 ? (
                                                    documentos.nominas.map((doc) => (
                                                        <div
                                                            key={doc.id}
                                                            onClick={() => verPdf(doc)}
                                                            className="p-3 bg-gray-50 rounded-lg hover:bg-primary-light transition-colors cursor-pointer border-2 border-transparent hover:border-orange-300"
                                                        >
                                                            <p className="text-sm font-medium text-gray-900">{doc.nombre_archivo}</p>
                                                            <p className="text-xs text-gray-500 mt-1">
                                                                {new Date(doc.fecha_creacion).toLocaleDateString('es-ES')}
                                                            </p>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p className="text-gray-500 text-sm italic">No hay documentos</p>
                                                )}
                                            </div>
                                        </div>

                                        {/* Columna Seguros Sociales */}
                                        <div>
                                            <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
                                                <FileText className="w-5 h-5 mr-2 text-green-600" />
                                                Seguros Sociales ({documentos.seguros.length})
                                            </h3>
                                            <div className="space-y-2">
                                                {documentos.seguros.length > 0 ? (
                                                    documentos.seguros.map((doc) => (
                                                        <div
                                                            key={doc.id}
                                                            onClick={() => verPdf(doc)}
                                                            className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-green-50 dark:hover:bg-green-900/30 transition-colors cursor-pointer border-2 border-transparent hover:border-green-300 dark:hover:border-green-700"
                                                        >
                                                            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{doc.nombre_archivo}</p>
                                                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                                                {new Date(doc.fecha_creacion).toLocaleDateString('es-ES')}
                                                            </p>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <p className="text-gray-500 dark:text-gray-400 text-sm italic">No hay documentos</p>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Visor de PDF */}
                                    {pdfSeleccionado && (
                                        <div className="mt-6 border-t pt-6">
                                            <div className="flex items-center justify-between mb-4">
                                                <h3 className="text-lg font-semibold text-gray-800">Vista previa: {pdfSeleccionado.nombre_archivo}</h3>
                                                <button
                                                    onClick={() => setPdfSeleccionado(null)}
                                                    className="px-3 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors text-sm"
                                                >
                                                    Cerrar vista
                                                </button>
                                            </div>
                                            <iframe
                                                src={`/api/documentos/${pdfSeleccionado.id}/archivo`}
                                                className="w-full h-[600px] border rounded-lg"
                                                title="PDF Viewer"
                                            />
                                        </div>
                                    )}
                                </>
                            ) : null}
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Env�o de Correo */}
            {/* Modal de Envío de Correo */}
            {mostrarModalEnvio && (
                <ModalEnvioCorreo
                    nominas={nominasParaEnviar}
                    segurosSociales={rntDisponible}
                    empresa={empresaParaEnviar}
                    onClose={() => setMostrarModalEnvio(false)}
                    onEnviado={() => {
                        toast.success('Correo enviado exitosamente');
                        setMostrarModalEnvio(false);
                    }}
                />
            )}

            {/* Modal de Envío de Correo Grupal (Con Selección) */}
            {mostrarModalGrupo && grupoParaEnviar && (
                <ModalEnvioCorreoGrupo
                    grupo={grupoParaEnviar}
                    mes={mes}
                    anio={anio}
                    onClose={() => setMostrarModalGrupo(false)}
                    onEnviado={() => {
                        toast.success('Correo de grupo enviado correctamente');
                        setMostrarModalGrupo(false);
                        cargarDatosGrupos();
                    }}
                />
            )}

            {/* Modal Confirmación Envío Masivo */}
            {mostrarModalConfirmacion && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white dark:bg-slate-900 rounded-xl p-6 max-w-md w-full border border-gray-200 dark:border-slate-800 shadow-2xl modal-content">
                        <h3 className="text-xl font-bold mb-4 text-gray-900 dark:text-gray-100">Confirmar Envío Masivo</h3>

                        <div className="space-y-3 mb-6">
                            <div className="flex justify-between">
                                <span className="text-gray-700 dark:text-gray-300">Total empresas:</span>
                                <strong className="text-gray-900 dark:text-gray-100">{empresas.length}</strong>
                            </div>
                            <div className="flex justify-between text-green-600 dark:text-green-400">
                                <span>Con email (se enviarán):</span>
                                <strong>{empresasConEmail.length}</strong>
                            </div>
                            <div className="flex justify-between text-gray-500 dark:text-gray-400">
                                <span>Sin email (se omitirán):</span>
                                <strong>{empresasSinEmail.length}</strong>
                            </div>
                        </div>

                        {/* Selector de Periodo */}
                        <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-slate-800 dark:to-slate-800 rounded-lg border border-purple-200 dark:border-slate-700">
                            <h4 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">📅 Periodo de Documentos</h4>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Mes</label>
                                    <select
                                        value={mesMasivo}
                                        onChange={(e) => setMesMasivo(parseInt(e.target.value))}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100"
                                    >
                                        {meses.map(m => (
                                            <option key={m.value} value={m.value}>{m.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Año</label>
                                    <select
                                        value={anioMasivo}
                                        onChange={(e) => setAnioMasivo(parseInt(e.target.value))}
                                        className="w-full px-3 py-2 border border-gray-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-purple-500 bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100"
                                    >
                                        {anios.map(a => (
                                            <option key={a} value={a}>{a}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-2 text-center">
                                Periodo: <span className="font-mono font-semibold text-purple-700 dark:text-purple-400">{anioMasivo}{String(mesMasivo).padStart(2, '0')}</span>
                            </p>
                        </div>

                        {/* Tipos de Documentos */}
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Tipos de Documentos a Enviar:</label>
                            <div className="space-y-2">
                                {/* Nóminas */}
                                <label className="flex items-center gap-3 p-3 bg-primary-light dark:bg-slate-800 rounded-lg border border-primary-light dark:border-slate-700 cursor-pointer hover:bg-orange-50 dark:hover:bg-slate-700 transition">
                                    <input
                                        type="checkbox"
                                        checked={tiposDocumentosMasivo.nominas}
                                        onChange={(e) => setTiposDocumentosMasivo({ ...tiposDocumentosMasivo, nominas: e.target.checked })}
                                        className="w-4 h-4 text-primary rounded focus:ring-2 focus:ring-primary dark:bg-slate-700 dark:border-slate-600"
                                    />
                                    <span className="font-medium text-gray-900 dark:text-gray-100">📄 Nóminas</span>
                                </label>

                                {/* RNT */}
                                <label className="flex items-center gap-3 p-3 bg-green-50 dark:bg-slate-800 rounded-lg border border-green-200 dark:border-slate-700 cursor-pointer hover:bg-green-100 dark:hover:bg-slate-700 transition">
                                    <input
                                        type="checkbox"
                                        checked={tiposDocumentosMasivo.rnt}
                                        onChange={(e) => setTiposDocumentosMasivo({ ...tiposDocumentosMasivo, rnt: e.target.checked })}
                                        className="w-4 h-4 text-green-600 rounded focus:ring-2 focus:ring-green-500 dark:bg-slate-700 dark:border-slate-600"
                                    />
                                    <span className="font-medium text-gray-900 dark:text-gray-100">👥 RNT (Relación Nominal)</span>
                                </label>

                                {/* RLC */}
                                <label className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-slate-800 rounded-lg border border-blue-200 dark:border-slate-700 cursor-pointer hover:bg-blue-100 dark:hover:bg-slate-700 transition">
                                    <input
                                        type="checkbox"
                                        checked={tiposDocumentosMasivo.rlc}
                                        onChange={(e) => setTiposDocumentosMasivo({ ...tiposDocumentosMasivo, rlc: e.target.checked })}
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500 dark:bg-slate-700 dark:border-slate-600"
                                    />
                                    <span className="font-medium text-gray-900 dark:text-gray-100">💰 RLC (Relación de Cotización)</span>
                                </label>
                            </div>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setMostrarModalConfirmacion(false)}
                                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={confirmarEnvioMasivo}
                                disabled={empresasConEmail.length === 0}
                                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                            >
                                Enviar a {empresasConEmail.length} empresas
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Resultados Envío Masivo */}
            {mostrarModalResultados && resultadosMasivo && (
                <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
                    <div className="bg-white rounded-xl p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto">
                        <h3 className="text-2xl font-bold mb-6">Resultados del Envío Masivo</h3>

                        <div className="grid grid-cols-3 gap-4 mb-6">
                            <div className="bg-green-50 p-4 rounded-lg text-center border border-green-200">
                                <p className="text-3xl font-bold text-green-600">{resultadosMasivo.enviados}</p>
                                <p className="text-sm text-gray-600 mt-1">Enviados</p>
                            </div>
                            <div className="bg-red-50 p-4 rounded-lg text-center border border-red-200">
                                <p className="text-3xl font-bold text-red-600">{resultadosMasivo.errores}</p>
                                <p className="text-sm text-gray-600 mt-1">Errores</p>
                            </div>
                            <div className="bg-yellow-50 p-4 rounded-lg text-center border border-yellow-200">
                                <p className="text-3xl font-bold text-yellow-600">{resultadosMasivo.omitidos}</p>
                                <p className="text-sm text-gray-600 mt-1">Omitidos</p>
                            </div>
                        </div>

                        <div className="space-y-2 mb-6">
                            <h4 className="font-semibold text-lg mb-3">Detalles por Empresa:</h4>
                            <div className="max-h-96 overflow-y-auto space-y-2">
                                {resultadosMasivo.detalles.map((detalle, idx) => (
                                    <div key={idx} className={`p-3 rounded-lg border ${detalle.status === 'enviado' ? 'bg-green-50 border-green-200' :
                                        detalle.status === 'error' ? 'bg-red-50 border-red-200' :
                                            'bg-yellow-50 border-yellow-200'
                                        }`}>
                                        <div className="flex justify-between items-start">
                                            <div className="flex-1">
                                                <p className="font-medium text-gray-900">{detalle.empresa}</p>
                                                {detalle.email && (
                                                    <p className="text-sm text-gray-600">📧 {detalle.email}</p>
                                                )}
                                                {detalle.razon && (
                                                    <p className="text-sm text-gray-600 mt-1">💬 {detalle.razon}</p>
                                                )}
                                                {detalle.adjuntos && (
                                                    <p className="text-sm text-gray-600">📎 {detalle.adjuntos} adjunto(s)</p>
                                                )}
                                            </div>
                                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${detalle.status === 'enviado' ? 'bg-green-200 text-green-800' :
                                                detalle.status === 'error' ? 'bg-red-200 text-red-800' :
                                                    'bg-yellow-200 text-yellow-800'
                                                }`}>
                                                {detalle.status === 'enviado' ? '✓ Enviado' :
                                                    detalle.status === 'error' ? '✗ Error' : '⚠ Omitido'}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <button
                            onClick={() => setMostrarModalResultados(false)}
                            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
                        >
                            Cerrar
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

