// frontend/src/components/PlantillaTestBench.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import {
    Upload, Trash2, Play, CheckCircle2, XCircle, AlertCircle,
    FileText, Loader2, ChevronDown, ChevronUp, ToggleLeft, ToggleRight,
    Clock, BarChart2, Target, Zap, ArrowUpCircle
} from 'lucide-react';

// ─── Helpers ───────────────────────────────────────────────────────────────

function ScoreBadge({ score }) {
    const pct = Math.round((score || 0) * 100);
    const color = pct >= 90 ? 'bg-green-100 text-green-700 border-green-300'
        : pct >= 60 ? 'bg-yellow-100 text-yellow-700 border-yellow-300'
            : 'bg-red-100 text-red-700 border-red-300';
    const dot = pct >= 90 ? '🟢' : pct >= 60 ? '🟡' : '🔴';
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border ${color}`}>
            {dot} {pct}%
        </span>
    );
}

function ScoreGauge({ score }) {
    const pct = Math.round((score || 0) * 100);
    const color = pct >= 90 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444';
    return (
        <div className="flex flex-col items-center gap-1">
            <div className="relative w-20 h-20">
                <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                    <circle
                        cx="18" cy="18" r="15.9" fill="none"
                        stroke={color} strokeWidth="3"
                        strokeDasharray={`${pct} 100`}
                        strokeLinecap="round"
                        style={{ transition: 'stroke-dasharray 0.8s ease' }}
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-black" style={{ color }}>{pct}%</span>
                </div>
            </div>
            <span className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Score</span>
        </div>
    );
}

// ─── Componente Principal ──────────────────────────────────────────────────

export default function PlantillaTestBench({ plantilla, onScoreUpdate, onUpdateTemplate }) {
    const [testFiles, setTestFiles] = useState([]);
    const [results, setResults] = useState([]);
    const [running, setRunning] = useState(false);
    const [nPasadas, setNPasadas] = useState(5);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [lastRun, setLastRun] = useState(null);
    const [expandedResult, setExpandedResult] = useState(null);
    const [loadingFiles, setLoadingFiles] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [toggling, setToggling] = useState(false);
    const [localScore, setLocalScore] = useState(plantilla.score_confianza || 0);
    const [localActiva, setLocalActiva] = useState(plantilla.activa !== false);
    const [editingExpectedId, setEditingExpectedId] = useState(null);
    const [expectedValues, setExpectedValues] = useState({});
    const fileInputRef = useRef();

    const cargarTestFiles = useCallback(async () => {
        try {
            const res = await axios.get(`/api/plantillas/${plantilla.id}/test-files`, { withCredentials: true });
            setTestFiles(res.data.test_files || []);
        } catch {
            toast.error('Error al cargar archivos de prueba');
        } finally {
            setLoadingFiles(false);
        }
    }, [plantilla.id]);

    const cargarResultados = useCallback(async () => {
        try {
            const res = await axios.get(`/api/plantillas/${plantilla.id}/test-results?limit=20`, { withCredentials: true });
            setResults(res.data.results || []);
        } catch { /* silencioso */ }
    }, [plantilla.id]);

    useEffect(() => {
        cargarTestFiles();
        cargarResultados();
    }, [cargarTestFiles, cargarResultados]);

    // ── Subir archivo ──────────────────────────────────────────────────────
    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (!file.name.endsWith('.pdf')) { toast.error('Solo se permiten archivos PDF'); return; }

        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);
        formData.append('descripcion', file.name);

        try {
            await axios.post(`/api/plantillas/${plantilla.id}/test-files`, formData, {
                withCredentials: true,
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            toast.success('Archivo de prueba subido');
            cargarTestFiles();
        } catch {
            toast.error('Error al subir el archivo');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDeleteFile = async (fileId) => {
        if (!window.confirm('¿Eliminar este archivo de prueba?')) return;
        try {
            await axios.delete(`/api/plantillas/${plantilla.id}/test-files/${fileId}`, { withCredentials: true });
            setTestFiles(prev => prev.filter(f => f.id !== fileId));
            setSelectedFiles(prev => prev.filter(id => id !== fileId));
            toast.success('Archivo eliminado');
        } catch {
            toast.error('Error al eliminar el archivo');
        }
    };

    const handleRunTest = async () => {
        if (testFiles.length === 0) { toast.error('Sube al menos un PDF de prueba primero'); return; }
        setRunning(true);
        setLastRun(null);

        try {
            const payload = {
                n_pasadas: nPasadas,
                file_ids: selectedFiles.length > 0 ? selectedFiles : null
            };
            const res = await axios.post(`/api/plantillas/${plantilla.id}/run-test`, payload, { withCredentials: true });
            const data = res.data;
            setLastRun(data);
            setLocalScore(data.score_confianza || 0);
            setLocalActiva(data.activa !== false);
            cargarResultados();
            if (onScoreUpdate) onScoreUpdate(data.score_confianza, data.activa);

            const pct = Math.round((data.tasa_global || 0) * 100);
            if (pct >= 90) toast.success(`✅ Test completado: ${pct}% de éxito`);
            else if (pct >= 60) toast(`⚠️ Test completado: ${pct}% de éxito`, { icon: '🟡' });
            else toast.error(`❌ Test completado: ${pct}% de éxito`);

            if (!data.activa) {
                toast(`⚠️ Plantilla desactivada automáticamente (score bajo el umbral)`, { icon: '🔴', duration: 5000 });
            }
        } catch (err) {
            toast.error(err.response?.data?.error || 'Error al ejecutar el test');
        } finally {
            setRunning(false);
        }
    };

    const handleToggleActive = async () => {
        setToggling(true);
        try {
            const res = await axios.post(`/api/plantillas/${plantilla.id}/toggle-active`, {}, { withCredentials: true });
            setLocalActiva(res.data.activa);
            if (onScoreUpdate) onScoreUpdate(localScore, res.data.activa);
            toast.success(res.data.mensaje);
        } catch {
            toast.error('Error al cambiar el estado');
        } finally {
            setToggling(false);
        }
    };

    const toggleFileSelection = (id) => {
        setSelectedFiles(prev =>
            prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
        );
    };

    const handleEditExpected = (file) => {
        const base = {};
        const campos = plantilla.campos || {};
        Object.keys(campos).forEach(k => {
            const actuales = file.campos_esperados || {};
            base[k] = actuales[k] || "";
        });
        setExpectedValues(base);
        setEditingExpectedId(file.id);
    };

    const handleChangeExpected = (key, value) => {
        setExpectedValues(prev => ({ ...prev, [key]: value }));
    };

    const handleSaveExpected = async (file) => {
        try {
            const res = await axios.put(
                `/api/plantillas/${plantilla.id}/test-files/${file.id}/campos-esperados`,
                {
                    campos_esperados: expectedValues,
                    descripcion: file.descripcion || file.nombre_archivo
                },
                { withCredentials: true }
            );
            const updated = res.data?.test_file || null;
            if (updated) {
                setTestFiles(prev =>
                    prev.map(f => f.id === file.id ? { ...f, campos_esperados: updated.campos_esperados, descripcion: updated.descripcion } : f)
                );
            }
            toast.success("Campos esperados guardados");
            setEditingExpectedId(null);
        } catch {
            toast.error("Error al guardar los campos esperados");
        }
    };

    const pctGlobal = lastRun ? Math.round((lastRun.tasa_global || 0) * 100) : null;

    return (
        <div className="space-y-5">

            {/* ── Header con score y estado ── */}
            <div className="flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100">
                <div className="flex items-center gap-4">
                    <ScoreGauge score={localScore} />
                    <div>
                        <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Confianza Histórica</p>
                        <p className="text-sm text-gray-600 mt-0.5">
                            {plantilla.total_tests_ejecutados || 0} tests ejecutados
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                            Umbral: {Math.round((plantilla.umbral_activacion || 0.9) * 100)}%
                        </p>
                    </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                    <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${localActiva ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'
                        }`}>
                        {localActiva ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                        {localActiva ? 'ACTIVA' : 'INACTIVA'}
                    </div>
                    <button
                        onClick={handleToggleActive}
                        disabled={toggling}
                        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition"
                    >
                        {toggling ? <Loader2 size={12} className="animate-spin" /> : localActiva ? <ToggleRight size={14} className="text-green-500" /> : <ToggleLeft size={14} className="text-gray-400" />}
                        {localActiva ? 'Desactivar' : 'Activar'}
                    </button>
                </div>
            </div>

            {/* ── Archivos de prueba ── */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
                    <h3 className="text-sm font-bold text-gray-700 flex items-center gap-2">
                        <FileText size={14} className="text-blue-500" />
                        Archivos de Prueba ({testFiles.length})
                    </h3>
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition shadow-sm"
                    >
                        {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
                        {uploading ? 'Subiendo...' : 'Subir PDF'}
                    </button>
                    <input ref={fileInputRef} type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                </div>

                {loadingFiles ? (
                    <div className="p-6 flex justify-center"><Loader2 className="animate-spin text-blue-400" /></div>
                ) : testFiles.length === 0 ? (
                    <div
                        className="p-8 text-center border-2 border-dashed border-gray-200 m-3 rounded-xl cursor-pointer hover:border-blue-300 hover:bg-blue-50 transition"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <Upload className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                        <p className="text-sm text-gray-500 font-medium">Arrastra o haz clic para subir PDFs de prueba</p>
                        <p className="text-xs text-gray-400 mt-1">Sube 2-5 documentos representativos de esta plantilla</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-100">
                        {testFiles.map(f => (
                            <div key={f.id} className={`border-b last:border-b-0 ${selectedFiles.includes(f.id) ? 'bg-blue-50' : ''}`}>
                                <div
                                    className="flex items-center gap-3 px-4 py-2.5 hover:bg-gray-50 transition cursor-pointer"
                                    onClick={() => toggleFileSelection(f.id)}
                                >
                                    <input
                                        type="checkbox"
                                        checked={selectedFiles.includes(f.id)}
                                        onChange={() => toggleFileSelection(f.id)}
                                        onClick={e => e.stopPropagation()}
                                        className="w-3.5 h-3.5 text-blue-600 rounded"
                                    />
                                    <FileText size={14} className="text-blue-400 flex-shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs font-medium text-gray-700 truncate">{f.nombre_archivo}</p>
                                        {f.descripcion && f.descripcion !== f.nombre_archivo && (
                                            <p className="text-[10px] text-gray-400">{f.descripcion}</p>
                                        )}
                                    </div>
                                    <span className="text-[10px] text-gray-400 flex-shrink-0">
                                        {f.fecha_subida ? new Date(f.fecha_subida).toLocaleDateString('es-ES') : ''}
                                    </span>
                                    <button
                                        onClick={e => { e.stopPropagation(); handleEditExpected(f); }}
                                        className="text-[10px] px-2 py-1 rounded border border-blue-200 text-blue-600 hover:bg-blue-50 transition"
                                    >
                                        Editar esperados
                                    </button>
                                    <button
                                        onClick={e => { e.stopPropagation(); handleDeleteFile(f.id); }}
                                        className="text-gray-300 hover:text-red-500 transition p-1"
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                                {editingExpectedId === f.id && (
                                    <div className="px-4 pb-3">
                                        <div className="mt-1 mb-2 flex justify-between items-center">
                                            <span className="text-[10px] font-semibold text-gray-500">
                                                Valores esperados para este PDF
                                            </span>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto border border-gray-100 rounded-lg p-2 bg-gray-50">
                                            {Object.entries(plantilla.campos || {}).map(([key, desc]) => (
                                                <div key={key} className="flex flex-col gap-0.5">
                                                    <span className="text-[10px] text-gray-500 font-mono truncate">{key}</span>
                                                    <span className="text-[10px] text-gray-400 truncate">{String(desc)}</span>
                                                    <input
                                                        className="border border-gray-200 rounded px-2 py-1 text-[11px] text-gray-700"
                                                        value={expectedValues[key] ?? ''}
                                                        onChange={e => handleChangeExpected(key, e.target.value)}
                                                        placeholder="Valor esperado"
                                                    />
                                                </div>
                                            ))}
                                        </div>
                                        <div className="flex justify-end gap-2 mt-2">
                                            <button
                                                onClick={() => setEditingExpectedId(null)}
                                                className="px-3 py-1 text-xs rounded border border-gray-200 text-gray-600 hover:bg-gray-100 transition"
                                            >
                                                Cancelar
                                            </button>
                                            <button
                                                onClick={() => handleSaveExpected(f)}
                                                className="px-3 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 transition"
                                            >
                                                Guardar esperados
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* ── Configuración y ejecución ── */}
            <div className="bg-white rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
                    <Zap size={14} className="text-yellow-500" />
                    Ejecutar Test
                </h3>
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-2">
                        <label className="text-xs text-gray-500 font-semibold">Pasadas:</label>
                        <div className="flex gap-1">
                            {[3, 5, 10].map(n => (
                                <button
                                    key={n}
                                    onClick={() => setNPasadas(n)}
                                    className={`px-3 py-1 rounded-lg text-xs font-bold border transition ${nPasadas === n
                                        ? 'bg-blue-600 text-white border-blue-600'
                                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                                        }`}
                                >
                                    {n}×
                                </button>
                            ))}
                        </div>
                    </div>
                    {selectedFiles.length > 0 && (
                        <span className="text-xs text-blue-600 font-medium">
                            {selectedFiles.length} archivo{selectedFiles.length > 1 ? 's' : ''} seleccionado{selectedFiles.length > 1 ? 's' : ''}
                        </span>
                    )}
                    {selectedFiles.length === 0 && testFiles.length > 0 && (
                        <span className="text-xs text-gray-400">Todos los archivos</span>
                    )}
                    <button
                        onClick={handleRunTest}
                        disabled={running || testFiles.length === 0}
                        className="ml-auto flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-sm font-bold rounded-xl transition shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                        {running ? 'Ejecutando...' : 'Ejecutar Test'}
                    </button>
                </div>

                {/* Resultado de la última ejecución */}
                {lastRun && (
                    <div className={`mt-4 rounded-xl p-4 border ${pctGlobal >= 90 ? 'bg-green-50 border-green-200' :
                        pctGlobal >= 60 ? 'bg-yellow-50 border-yellow-200' :
                            'bg-red-50 border-red-200'
                        }`}>
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2">
                                {pctGlobal >= 90 ? <CheckCircle2 className="text-green-600" size={18} /> :
                                    pctGlobal >= 60 ? <AlertCircle className="text-yellow-600" size={18} /> :
                                        <XCircle className="text-red-600" size={18} />}
                                <span className="font-bold text-gray-800">
                                    Resultado: {pctGlobal}% de éxito global
                                </span>
                            </div>
                            <span className="text-xs text-gray-500">{lastRun.total_runs} ejecuciones</span>
                        </div>

                        {/* Resultados por archivo */}
                        <div className="space-y-2">
                            {(lastRun.resultados || []).map((r, i) => {
                                const filePct = Math.round((r.tasa_media || 0) * 100);
                                const isExpanded = expandedResult === i;
                                return (
                                    <div key={i} className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                        <button
                                            className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-50 transition"
                                            onClick={() => setExpandedResult(isExpanded ? null : i)}
                                        >
                                            <div className="flex items-center gap-2 min-w-0">
                                                <FileText size={12} className="text-gray-400 flex-shrink-0" />
                                                <span className="text-xs font-medium text-gray-700 truncate">{r.nombre_archivo}</span>
                                            </div>
                                            <div className="flex items-center gap-2 flex-shrink-0">
                                                <ScoreBadge score={r.tasa_media} />
                                                <span className="text-xs text-gray-400">{r.n_pasadas} pasadas</span>
                                                {onUpdateTemplate && r.tasa_media >= 0.5 && (
                                                    <button
                                                        onClick={async (e) => {
                                                            e.stopPropagation();
                                                            if (!window.confirm("¿Usar resultado de este test para configurar la plantilla y los valores esperados?")) {
                                                                return;
                                                            }
                                                            const bestPass = r.pasadas.find(p => p.tasa_exito > 0) || r.pasadas[0];
                                                            if (!bestPass || !bestPass.campos_extraidos || Object.keys(bestPass.campos_extraidos).length === 0) {
                                                                toast.error("No hay datos extraídos válidos en este test");
                                                                return;
                                                            }
                                                            onUpdateTemplate(bestPass.campos_extraidos);
                                                            const tf = testFiles.find(f => f.nombre_archivo === r.nombre_archivo);
                                                            if (tf) {
                                                                try {
                                                                    await axios.put(
                                                                        `/api/plantillas/${plantilla.id}/test-files/${tf.id}/campos-esperados`,
                                                                        {
                                                                            campos_esperados: bestPass.campos_extraidos,
                                                                            descripcion: tf.descripcion || tf.nombre_archivo
                                                                        },
                                                                        { withCredentials: true }
                                                                    );
                                                                } catch {
                                                                    toast.error("No se pudieron guardar los campos esperados para este archivo de prueba");
                                                                }
                                                            }
                                                        }}
                                                        className="p-1 hover:bg-blue-100 text-blue-600 rounded-full transition"
                                                        title="Usar como Modelo para la Plantilla"
                                                    >
                                                        <ArrowUpCircle size={16} />
                                                    </button>
                                                )}
                                                {isExpanded ? <ChevronUp size={12} className="text-gray-400" /> : <ChevronDown size={12} className="text-gray-400" />}
                                            </div>
                                        </button>

                                        {isExpanded && (
                                            <div className="border-t border-gray-100 p-3 space-y-2">
                                                {(r.pasadas || []).map((p, j) => (
                                                    <div key={j} className="bg-gray-50 rounded-lg p-2">
                                                        <div className="flex items-center justify-between mb-1">
                                                            <span className="text-[10px] font-bold text-gray-500">Pasada {p.pasada}</span>
                                                            <div className="flex items-center gap-2">
                                                                {/* Solo mostrar chip de patrón si el backend indica que hubo chequeo de patrón (diferente de null/undefined y true por defecto) */
                                                                    /* NOTA: El backend ahora devuelve True si no hay patrón, así que para saber si MOSTRAR el chip, necesitaríamos saber si hay patrón definido.
                                                                       Como parche rápido visual: Si es TRUE, mostramos verde. Si es FALSE, rojo.
                                                                       Pero el usuario dice "no muestra resultado regex".
                                                                       Si es TRUE porque NO HAY patrón, confunde.
                                                                       Mejor: Solo mostrar si `plantilla.patron_deteccion` existe.
                                                                       Pasamos `plantilla` al componente padre, así que podemos usarlo.
                                                                    */
                                                                    (plantilla && plantilla.patron_deteccion && plantilla.patron_deteccion.trim()) && (
                                                                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${p.patron_detectado ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                                            Patrón {p.patron_detectado ? '✓' : '✗'}
                                                                        </span>
                                                                    )}
                                                                <ScoreBadge score={p.tasa_exito} />
                                                            </div>
                                                        </div>
                                                        {p.error ? (
                                                            <div className="text-red-600 bg-red-50 p-2 rounded text-[10px] font-mono mb-1">
                                                                <span className="font-bold">Error IA:</span> {p.error}
                                                            </div>
                                                        ) : (
                                                            <div className="grid grid-cols-2 gap-1 mt-1 mb-2">
                                                                {Object.entries(p.campos_extraidos || {}).slice(0, 6).map(([k, v]) => (
                                                                    <div key={k} className="flex gap-1 text-[9px]">
                                                                        <span className="text-gray-400 font-mono truncate">{k}:</span>
                                                                        <span className="text-gray-700 font-medium truncate">{String(v).slice(0, 30)}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {/* Visualizador de OCR Raw */}
                                                        {p.texto_completo && (
                                                            <div className="mt-2">
                                                                <p className="text-[9px] font-bold text-gray-500 mb-1 flex items-center gap-1">
                                                                    <FileText size={10} /> Texto Extraído (OCR):
                                                                </p>
                                                                <div className="p-2 bg-gray-100 rounded border border-gray-200">
                                                                    <pre className="text-[9px] text-gray-600 font-mono whitespace-pre-wrap h-32 overflow-y-auto w-full">
                                                                        {p.texto_completo}
                                                                    </pre>
                                                                </div>
                                                                {(!p.campos_extraidos || Object.keys(p.campos_extraidos).length === 0) && (
                                                                    <p className="text-[9px] text-orange-600 mt-1 italic">
                                                                        * No se extrajeron campos. Define Reglas Regex en la plantilla para capturar datos de este texto.
                                                                    </p>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>

            {/* ── Historial de tests ── */}
            {results.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                    <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                        <h3 className="text-sm font-bold text-gray-700 flex items-center gap-2">
                            <Clock size={14} className="text-gray-400" />
                            Historial Reciente
                        </h3>
                    </div>
                    <div className="divide-y divide-gray-100 max-h-48 overflow-y-auto">
                        {results.map(r => (
                            <div key={r.id} className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50">
                                <ScoreBadge score={r.tasa_exito} />
                                <span className="text-xs text-gray-600 truncate flex-1">{r.nombre_archivo}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${r.patron_detectado ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                    {r.patron_detectado ? 'Patrón ✓' : 'Sin patrón'}
                                </span>
                                <span className="text-[10px] text-gray-400 flex-shrink-0">
                                    {r.fecha_ejecucion ? new Date(r.fecha_ejecucion).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
