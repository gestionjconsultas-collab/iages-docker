// frontend/src/components/PlantillasManager.jsx
// Muestra tipos de documento predefinidos + auto-creados por OCR
// Los perfiles auto-creados incluyen selector de campos (checkboxes) y edición de campos personalizados
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  FileText, Settings, CheckCircle2, AlertCircle,
  ChevronDown, ChevronUp, Loader2, Save, ToggleLeft, ToggleRight,
  Zap, Bell, FolderOpen, Users, Search, Check, X, Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';

// ─── Colores por tipo ─────────────────────────────────────────────────────────
const TIPO_COLORS = {
  providencia_apremio: { bg: 'bg-red-50', border: 'border-red-200', badge: 'bg-red-100 text-red-700', icon: '⚡' },
  embargo_cuenta: { bg: 'bg-orange-50', border: 'border-orange-200', badge: 'bg-orange-100 text-orange-700', icon: '🔒' },
  requerimiento_pago: { bg: 'bg-yellow-50', border: 'border-yellow-200', badge: 'bg-yellow-100 text-yellow-700', icon: '📋' },
  auto: { bg: 'bg-violet-50', border: 'border-violet-200', badge: 'bg-violet-100 text-violet-700', icon: '🔍' },
  default: { bg: 'bg-blue-50', border: 'border-blue-200', badge: 'bg-blue-100 text-blue-700', icon: '📄' },
};

function getTipoColor(tipo) {
  if (tipo.auto_creado) return TIPO_COLORS.auto;
  return TIPO_COLORS[tipo.codigo] || TIPO_COLORS.default;
}

// ─── Selector de campos para perfiles auto-creados ────────────────────────────
function CampoSelector({ campos, camposActivos, onChange, onEditRequest }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-medium text-violet-700 uppercase tracking-wide flex items-center gap-1.5">
          <Search size={13} />
          Campos detectados — selecciona cuáles guardar
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => onChange(campos)}
            className="text-xs text-violet-600 hover:underline"
          >Todos</button>
          <span className="text-gray-300">|</span>
          <button
            onClick={() => onChange([])}
            className="text-xs text-gray-400 hover:underline"
          >Ninguno</button>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {campos.map(campo => {
          const activo = camposActivos.includes(campo);
          return (
            <div
              key={campo}
              className={`flex items-center gap-1.5 text-xs font-mono px-2.5 py-1.5 rounded-lg border transition-all ${activo
                ? 'bg-violet-100 border-violet-300 text-violet-800 font-semibold'
                : 'bg-gray-50 border-gray-200 text-gray-400'
                }`}
            >
              <button
                onClick={() => {
                  if (activo) onChange(camposActivos.filter(c => c !== campo));
                  else onChange([...camposActivos, campo]);
                }}
                className={`flex-shrink-0 transition-colors ${activo ? 'text-violet-600' : 'text-gray-300'}`}
              >
                {activo ? <CheckCircle2 size={14} /> : <X size={14} />}
              </button>
              <span
                className={`flex-1 cursor-pointer hover:underline ${!activo && 'line-through opacity-60'}`}
                onClick={() => onEditRequest(campo)}
                title="Haz click para editar las etiquetas de este campo"
              >
                {campo}
              </span>
              <Settings
                size={10}
                className="text-violet-400 opacity-0 group-hover:opacity-100 cursor-pointer"
                onClick={() => onEditRequest(campo)}
              />
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 mt-1">
        {camposActivos.length} de {campos.length} campos activos
      </p>
    </div>
  );
}

// ─── Componente Editor de Campos Personalizados ──────────────────────────────
function CustomFieldsEditor({ fields, onChange, draft, setDraft }) {
  const handleAddField = () => {
    if (!draft.key || !draft.labels) {
      toast.error('Nombre y etiquetas requeridos');
      return;
    }
    const labelList = draft.labels.split(',').map(s => s.trim()).filter(Boolean);
    onChange({ ...fields, [draft.key]: labelList });
    setDraft({ key: '', labels: '' });
  };

  const removeField = (key) => {
    const next = { ...fields };
    delete next[key];
    onChange(next);
  };

  return (
    <div className="space-y-3 p-3 bg-violet-50 border border-violet-200 rounded-xl">
      <p className="text-xs font-medium text-violet-700 uppercase tracking-wide flex items-center gap-1.5">
        <Zap size={13} className="text-amber-500" />
        Campos Personalizados (Extra)
      </p>

      {/* Lista de existentes */}
      <div className="space-y-2">
        {Object.entries(fields || {}).map(([key, labels]) => (
          <div
            key={key}
            className="group flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-violet-100 shadow-sm hover:border-violet-300 hover:shadow-md transition-all cursor-pointer"
            onClick={() => setDraft({ key, labels: labels.join(', ') })}
            title="Haz click para editar este campo"
          >
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-violet-400 group-hover:bg-violet-600 transition-colors" />
              <div className="flex flex-col">
                <span className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                  {key}
                  <Settings size={10} className="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                </span>
                <span className="text-[10px] text-gray-400 font-mono">Busca: {labels.join(', ')}</span>
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); removeField(key); }}
              className="text-red-300 hover:text-red-600 transition p-1 opacity-0 group-hover:opacity-100"
              title="Eliminar campo"
            >
              <Trash2 size={13} />
            </button>
          </div>
        ))}
        {Object.keys(fields || {}).length === 0 && (
          <p className="text-[10px] text-gray-400 italic text-center py-1">Sin campos extra definidos</p>
        )}
      </div>

      {/* Formulario nuevo */}
      <div className="pt-2 border-t border-violet-100 grid grid-cols-1 sm:grid-cols-2 gap-2">
        <input
          type="text"
          placeholder="Nombre campo (ej: num_exp)"
          className="text-xs border border-violet-200 rounded px-2 py-1.5 focus:ring-1 focus:ring-violet-400 outline-none"
          value={draft.key}
          onChange={e => setDraft(f => ({ ...f, key: e.target.value.toLowerCase().replace(/\s+/g, '_') }))}
        />
        <div className="flex gap-1">
          <input
            type="text"
            placeholder="Etiquetas (separadas por coma)"
            className="flex-1 text-xs border border-violet-200 rounded px-2 py-1.5 focus:ring-1 focus:ring-violet-400 outline-none"
            value={draft.labels}
            onChange={e => setDraft(f => ({ ...f, labels: e.target.value }))}
          />
          <button
            type="button"
            onClick={handleAddField}
            className="bg-violet-600 text-white rounded p-1.5 hover:bg-violet-700 transition"
          >
            <Check size={14} />
          </button>
        </div>
      </div>
      <p className="text-[10px] text-gray-400 italic">
        * Se buscará el valor justo debajo o al lado de cualquiera de estas etiquetas.
      </p>
    </div>
  );
}

// ─── Componente Editor de Etiquetas de Límite (Stop Words) ───────────────────
function BoundaryTagsEditor({ tags, onChange }) {
  const [newTag, setNewTag] = useState('');

  const handleAddTag = () => {
    if (!newTag.trim()) return;
    if (tags.includes(newTag.trim())) {
      toast.error('Esta etiqueta ya existe');
      return;
    }
    onChange([...tags, newTag.trim()]);
    setNewTag('');
  };

  const removeTag = (index) => {
    const next = [...tags];
    next.splice(index, 1);
    onChange(next);
  };

  return (
    <div className="space-y-3 p-3 bg-amber-50 border border-amber-200 rounded-xl">
      <p className="text-xs font-medium text-amber-700 uppercase tracking-wide flex items-center gap-1.5">
        <X size={13} className="text-red-500" />
        Límites de Extracción (Stop Words)
      </p>

      <div className="flex flex-wrap gap-2">
        {tags.map((tag, idx) => (
          <span
            key={idx}
            className="flex items-center gap-1 bg-white border border-amber-200 px-2 py-1 rounded text-[10px] font-medium text-amber-800 shadow-sm"
          >
            {tag}
            <button
              onClick={() => removeTag(idx)}
              className="text-amber-400 hover:text-red-500 transition"
            >
              <X size={10} />
            </button>
          </span>
        ))}
        {tags.length === 0 && (
          <p className="text-[10px] text-amber-600/60 italic px-1">Sin límites personalizados</p>
        )}
      </div>

      <div className="pt-2 border-t border-amber-100 flex gap-1">
        <input
          type="text"
          placeholder="Ej: Detalle de la deuda"
          className="flex-1 text-xs border border-amber-200 rounded px-2 py-1.5 focus:ring-1 focus:ring-amber-400 outline-none"
          value={newTag}
          onChange={e => setNewTag(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAddTag()}
        />
        <button
          type="button"
          onClick={handleAddTag}
          className="bg-amber-600 text-white rounded p-1.5 hover:bg-amber-700 transition"
        >
          <Check size={14} />
        </button>
      </div>
      <p className="text-[10px] text-amber-600 italic">
        * Estas frases obligan al motor a dejar de leer el campo actual para evitar sangrados.
      </p>
    </div>
  );
}




// ─── Tarjeta de tipo de documento ─────────────────────────────────────────────
function TipoDocumentoCard({ tipo, configs, onRefresh }) {
  const color = getTipoColor(tipo);
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState({ key: '', labels: '' });

  const [form, setForm] = useState({
    categoria_default: tipo.config?.categoria_default || '',
    prioridad_default: tipo.config?.prioridad_default || '',
    departamento_default: tipo.config?.departamento_default || '',
    notificar_cliente: tipo.config?.notificar_cliente || false,
    activo: tipo.config?.activo !== undefined ? tipo.config.activo : true,
    // Para perfiles auto-creados
    campos_activos: tipo.config?.campos_activos || tipo.campos_extraidos || [],
    campos_personalizados: tipo.config?.campos_personalizados || {},
    mapeo_lineas: tipo.config?.mapeo_lineas || {},
    boundary_tags: tipo.config?.boundary_tags || [],
  });

  const hasConfig = tipo.config && (tipo.config.categoria_default || tipo.config.departamento_default || Object.keys(tipo.config.campos_personalizados || {}).length > 0);

  const handleSave = async () => {
    setSaving(true);
    try {
      await axios.put(`/api/tipos-documento/${tipo.codigo}/config`, form, { withCredentials: true });
      toast.success('Configuración guardada');
      onRefresh();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`¿Estás seguro de que quieres eliminar permanentemente el perfil ${tipo.nombre}? Esta acción no se puede deshacer.`)) {
      return;
    }
    setSaving(true);
    try {
      await axios.delete(`/api/tipos-documento/${tipo.codigo}`, { withCredentials: true });
      toast.success('Perfil eliminado con éxito');
      onRefresh(); // Refrescar lista
    } catch (err) {
      toast.error(err.response?.data?.error || 'Error al eliminar');
      setSaving(false);
    }
  };

  const camposVisibles = tipo.campos_extraidos || [];
  const camposActivos = form.campos_activos || [];

  return (
    <div className={`rounded-xl border-2 ${color.border} ${color.bg} overflow-hidden transition-all duration-200`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:opacity-80 transition"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{color.icon}</span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-800">{tipo.nombre}</h3>
              {tipo.auto_creado && (
                <span className="text-xs px-1.5 py-0.5 rounded bg-violet-100 text-violet-600 font-medium">
                  auto-OCR
                </span>
              )}
              {form.activo ? (
                <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">
                  <CheckCircle2 size={11} /> Activo
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs font-medium text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                  <AlertCircle size={11} /> Inactivo
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{tipo.descripcion}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {hasConfig && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color.badge}`}>
              Configurado
            </span>
          )}
          <span className="hidden sm:block text-xs font-mono bg-white/70 border border-gray-200 px-2 py-0.5 rounded text-gray-600">
            {tipo.patron_deteccion}
          </span>
          {expanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
      </div>

      {/* Chips de campos (siempre visible) */}
      {camposVisibles.length > 0 && (
        <div className="px-4 pb-3 flex flex-wrap gap-1.5">
          {camposVisibles.map(campo => {
            const activo = tipo.auto_creado ? camposActivos.includes(campo) : true;
            return (
              <span
                key={campo}
                className={`text-xs border px-2 py-0.5 rounded-full font-mono transition-all ${activo
                  ? 'bg-white/80 border-gray-200 text-gray-600'
                  : 'bg-gray-100 border-gray-200 text-gray-300 line-through'
                  }`}
              >
                {campo}
              </span>
            );
          })}
        </div>
      )}

      {/* Panel expandido */}
      {expanded && (
        <div className="border-t border-gray-200 bg-white/60 p-4 space-y-6">
          {/* Fila 1: Campos y Automatización */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Izquierda: Selección de campos */}
            {tipo.auto_creado ? (
              <div className="space-y-4">
                <CampoSelector
                  campos={camposVisibles}
                  camposActivos={form.campos_activos}
                  onChange={nuevos => setForm(f => ({ ...f, campos_activos: nuevos }))}
                  onEditRequest={key => {
                    const existing = form.campos_personalizados[key] || (tipo.base_labels && tipo.base_labels[key]) || [];
                    setDraft({ key, labels: existing.join(', ') });
                    toast.success(`Cargado campo "${key}" para editar etiquetas`, { icon: '📝' });
                  }}
                />
                <CustomFieldsEditor
                  fields={form.campos_personalizados}
                  draft={draft}
                  setDraft={setDraft}
                  onChange={nuevos => {
                    const keysNuevas = Object.keys(nuevos).filter(k => !form.campos_personalizados[k]);
                    setForm(f => ({
                      ...f,
                      campos_personalizados: nuevos,
                      campos_activos: [...f.campos_activos, ...keysNuevas]
                    }));
                  }}
                />
                <BoundaryTagsEditor
                  tags={form.boundary_tags}
                  onChange={nuevos => setForm(f => ({ ...f, boundary_tags: nuevos }))}
                />
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-500 p-4 border border-blue-100 bg-blue-50/50 rounded-xl">
                  Este es un perfil predefinido y programado por nuestro sistema. Los campos se extraen de forma automatizada.
                </p>
              </div>
            )}

            {/* Derecha: Configuración General */}
            <div className="space-y-4">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
                Configuración de automatización
              </p>

              <div className="grid grid-cols-1 gap-4">
                {/* Categoría */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5">
                    <FolderOpen size={14} className="text-blue-500" />
                    Categoría destino
                  </label>
                  <select
                    value={form.categoria_default}
                    onChange={e => setForm(f => ({ ...f, categoria_default: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Sin categoría asignada</option>
                    {(configs.categories || []).map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>

                {/* Prioridad (solo visible si la categoría es Notificaciones) */}
                {form.categoria_default === 'Notificaciones' && (
                  <div className="animate-in fade-in slide-in-from-top-2">
                    <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5">
                      <AlertCircle size={14} className="text-orange-500" />
                      Prioridad
                    </label>
                    <select
                      value={form.prioridad_default}
                      onChange={e => setForm(f => ({ ...f, prioridad_default: e.target.value }))}
                      className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                    >
                      <option value="informativa">Informativas</option>
                      <option value="importante">Importantes</option>
                      <option value="urgente">Urgentes</option>
                    </select>
                  </div>
                )}

                {/* Departamento */}
                <div>
                  <label className="flex items-center gap-1.5 text-sm font-medium text-gray-700 mb-1.5">
                    <Users size={14} className="text-purple-500" />
                    Departamento asignado
                  </label>
                  <select
                    value={form.departamento_default}
                    onChange={e => setForm(f => ({ ...f, departamento_default: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">Sin departamento asignado</option>
                    {(configs.departments || []).map(dep => (
                      <option key={dep} value={dep}>{dep}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Notificar cliente */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <Bell size={15} className="text-amber-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-700">Notificar al cliente</p>
                    <p className="text-[10px] text-gray-500">Crear alerta en el panel del cliente</p>
                  </div>
                </div>
                <button
                  onClick={() => setForm(f => ({ ...f, notificar_cliente: !f.notificar_cliente }))}
                  className={form.notificar_cliente ? "text-amber-500 transition-colors" : "text-gray-300 transition-colors"}
                >
                  {form.notificar_cliente ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                </button>
              </div>

              {/* Activo */}
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-center gap-2">
                  <Zap size={15} className="text-green-500" />
                  <div>
                    <p className="text-sm font-medium text-gray-700">Automatización activa</p>
                    <p className="text-[10px] text-gray-400">Proceso desatendido al detectar patrón</p>
                  </div>
                </div>
                <button onClick={() => setForm(f => ({ ...f, activo: !f.activo }))} className="transition">
                  {form.activo
                    ? <ToggleRight size={28} className="text-green-500" />
                    : <ToggleLeft size={28} className="text-gray-400" />
                  }
                </button>
              </div>

              {/* Guardar y Eliminar */}
              <div className="flex justify-between items-center pt-2 mt-2 border-t border-gray-100">
                {tipo.auto_creado ? (
                  <button
                    onClick={handleDelete}
                    disabled={saving}
                    className="flex items-center gap-1.5 text-xs font-semibold text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-lg transition"
                    title="Eliminar perfil permanentemente"
                  >
                    <Trash2 size={16} /> Eliminar perfil
                  </button>
                ) : <div />}

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition disabled:opacity-60 shadow-md"
                >
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  Guardar configuración
                </button>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}

// ─── Componente principal ─────────────────────────────────────────────────────
export default function PlantillasManager() {
  const [tipos, setTipos] = useState([]);
  const [configs, setConfigs] = useState({ categories: [], departments: [] });
  const [loading, setLoading] = useState(true);

  const cargar = async () => {
    try {
      const [tiposRes, configsRes] = await Promise.all([
        axios.get('/api/tipos-documento', { withCredentials: true }),
        axios.get('/api/config/categories-and-departments', { withCredentials: true }),
      ]);
      setTipos(tiposRes.data.tipos || []);
      setConfigs(configsRes.data || { categories: [], departments: [] });
    } catch (err) {
      console.error('Error cargando tipos de documento:', err);
      toast.error('Error al cargar los tipos de documento');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { cargar(); }, []);

  if (loading) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="animate-spin w-8 h-8 text-blue-500" />
      </div>
    );
  }

  const tiposEstaticos = tipos.filter(t => !t.auto_creado);
  const tiposAuto = tipos.filter(t => t.auto_creado);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="text-blue-600" size={24} />
            Tipos de Documento
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Gestión de perfiles de extracción automática y perfiles detectados por OCR.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 text-xs font-medium px-3 py-1.5 rounded-full">
          <Zap size={12} />
          100% Automático
        </div>
      </div>

      {tiposAuto.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Search size={16} className="text-violet-600" />
            <h2 className="text-sm font-semibold text-violet-700 uppercase tracking-wide">
              Detectados automáticamente por OCR
            </h2>
            <span className="text-xs bg-violet-100 text-violet-600 px-2 py-0.5 rounded-full font-medium">
              {tiposAuto.length}
            </span>
          </div>
          {tiposAuto.map(tipo => (
            <TipoDocumentoCard key={tipo.codigo} tipo={tipo} configs={configs} onRefresh={cargar} />
          ))}
        </div>
      )}

      <div className="space-y-4">
        <div className="flex items-center gap-2 pt-2">
          <FileText size={16} className="text-blue-600" />
          <h2 className="text-sm font-semibold text-blue-700 uppercase tracking-wide">
            Perfiles predefinidos
          </h2>
        </div>
        {tiposEstaticos.map(tipo => (
          <TipoDocumentoCard key={tipo.codigo} tipo={tipo} configs={configs} onRefresh={cargar} />
        ))}
      </div>

      {tipos.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <FileText size={48} className="mx-auto mb-3 opacity-30" />
          <p className="font-medium">No hay tipos de documento configurados</p>
        </div>
      )}
    </div>
  );
}