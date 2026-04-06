// frontend/src/components/ModalEnvioCorreoGrupo.jsx
import React, { useState, useEffect } from 'react';
import { Mail, FileText, Send, X, CheckCircle, ChevronDown, ChevronRight, Building2, User, Landmark } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

export default function ModalEnvioCorreoGrupo({
    grupo,
    mes,
    anio,
    onClose,
    onEnviado
}) {
    const [documentos, setDocumentos] = useState({ nominas: [], seguros: [], impuestos: [] });
    const [loading, setLoading] = useState(true);
    const [selectedIds, setSelectedIds] = useState([]);
    const [enviando, setEnviando] = useState(false);
    const [expandedCompanies, setExpandedCompanies] = useState({});

    useEffect(() => {
        cargarDocumentos();
    }, [grupo.id, mes, anio]);

    const cargarDocumentos = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`/api/grupo/${grupo.id}/documentos-mes`, {
                params: { mes, anio },
                withCredentials: true
            });
            if (response.data.success || response.data.nominas) {
                setDocumentos({
                    nominas: response.data.nominas || [],
                    seguros: response.data.seguros || [],
                    impuestos: response.data.impuestos || []
                });
                
                // Por defecto seleccionar todos
                const allIds = [
                    ...(response.data.nominas || []).map(d => d.id),
                    ...(response.data.seguros || []).map(d => d.id),
                    ...(response.data.impuestos || []).map(d => d.id)
                ];
                setSelectedIds(allIds);
                
                // Expandir todas las empresas por defecto
                const initialExpanded = {};
                [
                    ...(response.data.nominas || []), 
                    ...(response.data.seguros || []),
                    ...(response.data.impuestos || [])
                ].forEach(d => {
                    initialExpanded[d.empresa_id] = true;
                });
                setExpandedCompanies(initialExpanded);
            }
        } catch (error) {
            console.error('Error cargando documentos de grupo:', error);
            toast.error('Error al cargar documentos del grupo');
        } finally {
            setLoading(false);
        }
    };

    const toggleId = (id) => {
        setSelectedIds(prev => 
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const toggleCompanySelect = (empresaId, isSelected) => {
        const companyDocs = [
            ...documentos.nominas.filter(d => d.empresa_id === empresaId),
            ...documentos.seguros.filter(d => d.empresa_id === empresaId),
            ...documentos.impuestos.filter(d => d.empresa_id === empresaId)
        ].map(d => d.id);

        if (isSelected) {
            setSelectedIds(prev => [...new Set([...prev, ...companyDocs])]);
        } else {
            setSelectedIds(prev => prev.filter(id => !companyDocs.includes(id)));
        }
    };

    const handleEnviar = async () => {
        if (selectedIds.length === 0) {
            toast.error('Selecciona al menos un documento para enviar');
            return;
        }

        setEnviando(true);
        const toastId = toast.loading('Enviando correo del grupo...');

        try {
            const response = await axios.post('/api/enviar-correos-grupo', {
                grupo_id: grupo.id,
                mes,
                anio,
                documento_ids: selectedIds
            }, { withCredentials: true });

            if (response.data.success) {
                toast.success('Correo enviado con éxito', { id: toastId });
                if (onEnviado) onEnviado();
                onClose();
            } else {
                toast.error(response.data.error || 'Error al enviar correo', { id: toastId });
            }
        } catch (error) {
            console.error('Error enviando correo de grupo:', error);
            toast.error('Error al enviar correo de grupo', { id: toastId });
        } finally {
            setEnviando(false);
        }
    };

    // Agrupar documentos por empresa
    const empresasIds = [...new Set([
        ...documentos.nominas.map(d => d.empresa_id),
        ...documentos.seguros.map(d => d.empresa_id),
        ...documentos.impuestos.map(d => d.empresa_id)
    ])];

    const companiesWithDocs = empresasIds.map(id => {
        const nominas = documentos.nominas.filter(d => d.empresa_id === id);
        const seguros = documentos.seguros.filter(d => d.empresa_id === id);
        const impuestos = documentos.impuestos.filter(d => d.empresa_id === id);
        const anyDoc = nominas[0] || seguros[0] || impuestos[0];
        const nombre = anyDoc ? anyDoc.empresa_nombre : "Empresa Desconocida";
        return { id, nombre, nominas, seguros, impuestos };
    }).sort((a, b) => a.nombre.localeCompare(b.nombre));

    const totalAvailable = documentos.nominas.length + documentos.seguros.length + documentos.impuestos.length;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
            <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-3xl w-full flex flex-col max-h-[90vh] overflow-hidden border border-gray-200 dark:border-gray-800 animate-in fade-in zoom-in duration-200">
                
                {/* Header */}
                <div className="p-6 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between bg-linear-to-r from-orange-500 to-red-600">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-white/20 backdrop-blur-md rounded-xl shadow-lg">
                            <Mail className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white tracking-tight">{grupo.nombre}</h2>
                            <p className="text-sm text-orange-50 flex items-center gap-2 opacity-90">
                                <User className="w-3.5 h-3.5" />
                                Enviar a: <span className="font-semibold text-white">{grupo.email}</span>
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/80 hover:text-white">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/30 dark:bg-gray-900/50">
                    
                    {/* Resumen Selección */}
                    <div className="flex items-center justify-between bg-white dark:bg-gray-800 p-4 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm">
                        <div className="flex items-center gap-3">
                            <div className={`p-1.5 rounded-full ${selectedIds.length > 0 ? 'bg-green-100 dark:bg-green-900/30 text-green-600' : 'bg-gray-100 dark:bg-gray-700 text-gray-400'}`}>
                                <CheckCircle className="w-4 h-4" />
                            </div>
                            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                                {selectedIds.length} <span className="font-normal text-gray-500">archivos seleccionados de</span> {totalAvailable}
                            </span>
                        </div>
                        <div className="flex gap-4">
                            <button 
                                onClick={() => setSelectedIds([])}
                                className="text-xs font-bold text-red-500 hover:text-red-600 uppercase tracking-wider transition-colors"
                            >
                                Deseleccionar Todo
                            </button>
                            <button 
                                onClick={() => setSelectedIds([...documentos.nominas, ...documentos.seguros, ...documentos.impuestos].map(d => d.id))}
                                className="text-xs font-bold text-primary hover:text-primary-dark uppercase tracking-wider transition-colors"
                            >
                                Seleccionar Todo
                            </button>
                        </div>
                    </div>

                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-12 gap-3">
                            <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                            <p className="text-gray-500 font-medium">Buscando documentos del grupo...</p>
                        </div>
                    ) : companiesWithDocs.length === 0 ? (
                        <div className="text-center py-12">
                            <div className="bg-gray-50 dark:bg-gray-800 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                                <FileText className="w-8 h-8 text-gray-400" />
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Sin documentos</h3>
                            <p className="text-gray-500">No se encontraron archivos para el periodo seleccionado.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {companiesWithDocs.map(company => {
                                const companySelectedCount = [
                                    ...company.nominas,
                                    ...company.seguros,
                                    ...company.impuestos
                                ].filter(d => selectedIds.includes(d.id)).length;
                                
                                const companyTotal = company.nominas.length + company.seguros.length + company.impuestos.length;
                                const isAllSelected = companySelectedCount === companyTotal;

                                return (
                                    <div key={company.id} className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden shadow-sm">
                                        <div 
                                            className={`flex items-center justify-between p-3.5 cursor-pointer select-none transition-all ${
                                                expandedCompanies[company.id] ? 'bg-orange-50/30 dark:bg-orange-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'
                                            }`}
                                            onClick={() => setExpandedCompanies(prev => ({ ...prev, [company.id]: !prev[company.id] }))}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div onClick={e => e.stopPropagation()}>
                                                    <input 
                                                        type="checkbox"
                                                        checked={isAllSelected}
                                                        onChange={(e) => toggleCompanySelect(company.id, e.target.checked)}
                                                        className="w-5 h-5 text-primary border-gray-300 rounded-md focus:ring-primary shadow-sm transition-all"
                                                    />
                                                </div>
                                                <div className="flex items-center gap-2.5">
                                                    <div className="p-1.5 bg-white dark:bg-gray-700 rounded-lg shadow-xs border border-gray-100 dark:border-gray-600">
                                                        <Building2 className={`w-4 h-4 ${expandedCompanies[company.id] ? 'text-primary' : 'text-gray-400'}`} />
                                                    </div>
                                                    <span className="text-sm font-bold text-gray-800 dark:text-white leading-tight">{company.nombre}</span>
                                                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full transition-colors ${
                                                        isAllSelected ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                                    }`}>
                                                        {companySelectedCount}/{companyTotal}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="p-1 text-gray-400 bg-white/50 dark:bg-gray-800 rounded-full border border-gray-100 dark:border-gray-700">
                                                {expandedCompanies[company.id] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                                            </div>
                                        </div>

                                        {expandedCompanies[company.id] && (
                                            <div className="p-3 bg-white dark:bg-gray-900 divide-y divide-gray-100 dark:divide-gray-800">
                                                {/* Sección Nominas */}
                                                {company.nominas.length > 0 && (
                                                    <div className="mb-2">
                                                        <h4 className="text-[10px] uppercase font-bold text-orange-500 mb-2 mt-1">Nóminas</h4>
                                                        {company.nominas.map(doc => (
                                                            <label key={doc.id} className="flex items-center gap-3 py-2 px-1 hover:bg-orange-50/50 dark:hover:bg-orange-900/10 rounded-lg cursor-pointer transition-colors group">
                                                                 <input 
                                                                    type="checkbox"
                                                                    checked={selectedIds.includes(doc.id)}
                                                                    onChange={() => toggleId(doc.id)}
                                                                    className="w-3.5 h-3.5 text-orange-500 rounded focus:ring-orange-500"
                                                                />
                                                                <div className="flex-1 min-w-0">
                                                                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{doc.nombre_archivo}</p>
                                                                    <p className="text-[10px] text-gray-400">{new Date(doc.fecha).toLocaleDateString()}</p>
                                                                </div>
                                                                <FileText className="w-3.5 h-3.5 text-orange-300 group-hover:text-orange-500 transition-colors" />
                                                            </label>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Sección Seguros */}
                                                {company.seguros.length > 0 && (
                                                    <div className="py-2">
                                                        <h4 className="text-[10px] uppercase font-bold text-green-600 mb-2">Seguros Sociales</h4>
                                                        {company.seguros.map(doc => (
                                                            <label key={doc.id} className="flex items-center gap-3 py-2 px-1 hover:bg-green-50/50 dark:hover:bg-green-900/10 rounded-lg cursor-pointer transition-colors group">
                                                                <input 
                                                                    type="checkbox"
                                                                    checked={selectedIds.includes(doc.id)}
                                                                    onChange={() => toggleId(doc.id)}
                                                                    className="w-3.5 h-3.5 text-green-600 rounded focus:ring-green-500"
                                                                />
                                                                <div className="flex-1 min-w-0">
                                                                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{doc.nombre_archivo}</p>
                                                                    <p className="text-[10px] text-gray-400">{new Date(doc.fecha).toLocaleDateString()}</p>
                                                                </div>
                                                                <FileText className="w-3.5 h-3.5 text-green-300 group-hover:text-green-500 transition-colors" />
                                                            </label>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Sección Impuestos */}
                                                {company.impuestos.length > 0 && (
                                                    <div className="pt-2">
                                                        <h4 className="text-[10px] uppercase font-bold text-blue-600 mb-2">Impuestos</h4>
                                                        {company.impuestos.map(doc => (
                                                            <label key={doc.id} className="flex items-center gap-3 py-2 px-1 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 rounded-lg cursor-pointer transition-colors group">
                                                                <input 
                                                                    type="checkbox"
                                                                    checked={selectedIds.includes(doc.id)}
                                                                    onChange={() => toggleId(doc.id)}
                                                                    className="w-3.5 h-3.5 text-blue-600 rounded focus:ring-blue-500"
                                                                />
                                                                <div className="flex-1 min-w-0">
                                                                    <p className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">{doc.nombre_archivo}</p>
                                                                    <p className="text-[10px] text-gray-400">{new Date(doc.fecha).toLocaleDateString()}</p>
                                                                </div>
                                                                <Landmark className="w-3.5 h-3.5 text-blue-300 group-hover:text-blue-500 transition-colors" />
                                                            </label>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 flex gap-4">
                    <button
                        onClick={onClose}
                        className="flex-1 px-6 py-4 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-all font-bold text-sm tracking-wide"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleEnviar}
                        disabled={enviando || selectedIds.length === 0 || loading}
                        className="flex-[2] flex items-center justify-center gap-3 px-6 py-4 bg-linear-to-r from-orange-500 to-red-600 text-white rounded-xl hover:shadow-xl hover:shadow-orange-200 dark:hover:shadow-none transition-all disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed font-bold text-sm tracking-wide active:scale-[0.98]"
                    >
                        {enviando ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                Enviando...
                            </>
                        ) : (
                            <>
                                <Send className="w-5 h-5" />
                                Enviar {selectedIds.length} Archivos
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
