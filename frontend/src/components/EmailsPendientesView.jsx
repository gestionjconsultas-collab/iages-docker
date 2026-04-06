// frontend/src/components/EmailsPendientesView.jsx
/**
 * Vista de correos pendientes de envío.
 * Lista documentos con email preparado y no enviado.
 * Permite envío individual o masivo.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Mail, Send, RefreshCw, CheckSquare, Square, AlertCircle,
  Building2, FileText, Users, Calendar, Loader2, X, ChevronDown
} from 'lucide-react';
import toast from 'react-hot-toast';

const API = import.meta.env.VITE_API_URL || '';

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatFecha(str) {
  if (!str) return '—';
  try {
    return new Date(str).toLocaleDateString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return str;
  }
}

// ─── Modal envío individual ──────────────────────────────────────────────────

function ModalConfirmEnvio({ doc, onConfirm, onClose, loading }) {
  const [destinatarios, setDestinatarios] = useState(
    (doc?.destinatarios || []).join(', ')
  );
  const [asunto, setAsunto] = useState(doc?.asunto || '');
  const [cuerpo, setCuerpo] = useState(doc?.cuerpo || '');

  function handleEnviar() {
    const dests = destinatarios.split(/[,;\s]+/).map(d => d.trim()).filter(Boolean);
    if (!dests.length) { toast.error('Añade al menos un destinatario'); return; }
    onConfirm({ destinatarios: dests, asunto, cuerpo });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-5 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-orange-500" />
            <h2 className="font-semibold text-gray-900 text-base">Enviar correo</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 pt-4 pb-2">
          <p className="text-xs text-gray-500 mb-1">Documento</p>
          <p className="text-sm font-medium text-gray-800 truncate">{doc?.nombre_archivo}</p>
          <p className="text-xs text-gray-500 mt-0.5">{doc?.empresa_nombre}</p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Destinatarios <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={destinatarios}
              onChange={e => setDestinatarios(e.target.value)}
              placeholder="email1@ejemplo.com, email2@ejemplo.com"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
            <p className="text-xs text-gray-400 mt-1">Separa múltiples emails con comas</p>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Asunto</label>
            <input
              type="text"
              value={asunto}
              onChange={e => setAsunto(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Cuerpo del mensaje</label>
            <textarea
              value={cuerpo}
              onChange={e => setCuerpo(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 resize-none"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 p-5 border-t border-gray-200">
          <button onClick={onClose} disabled={loading}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancelar
          </button>
          <button onClick={handleEnviar} disabled={loading}
            className="px-4 py-2 text-sm rounded-lg bg-orange-500 hover:bg-orange-600 text-white flex items-center gap-2 disabled:opacity-60">
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Enviando…</> : <><Send className="w-4 h-4" /> Enviar correo</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Modal confirmación masivo ───────────────────────────────────────────────

function ModalConfirmMasivo({ count, erroresPrevios, onConfirm, onClose, loading }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
            <Send className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">Envío masivo</h2>
            <p className="text-sm text-gray-500">
              Se enviarán {count} correo{count !== 1 ? 's' : ''} a sus destinatarios guardados
            </p>
          </div>
        </div>

        {/* Errores del intento anterior */}
        {erroresPrevios?.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-xs font-semibold text-red-700 mb-2 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" /> Errores del envío anterior:
            </p>
            {erroresPrevios.map((e, i) => (
              <p key={i} className="text-xs text-red-600 mb-0.5">
                <span className="font-medium">{e.nombre}:</span> {e.error}
              </p>
            ))}
          </div>
        )}

        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700 mb-5 flex gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>Esta acción no se puede deshacer. Los emails serán enviados inmediatamente.</span>
        </div>
        <div className="flex justify-end gap-3">
          <button onClick={onClose} disabled={loading}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50">
            Cancelar
          </button>
          <button onClick={onConfirm} disabled={loading}
            className="px-4 py-2 text-sm rounded-lg bg-orange-500 hover:bg-orange-600 text-white flex items-center gap-2 disabled:opacity-60">
            {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Enviando…</> : <><Send className="w-4 h-4" /> Confirmar envío</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Fila de la tabla ────────────────────────────────────────────────────────

function EmailRow({ doc, selected, onToggle, onSend }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${selected ? 'bg-orange-50' : ''}`}>
        <td className="px-4 py-3 w-10">
          <button onClick={() => onToggle(doc.id)} className="text-gray-400 hover:text-orange-500">
            {selected ? <CheckSquare className="w-4 h-4 text-orange-500" /> : <Square className="w-4 h-4" />}
          </button>
        </td>

        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-gray-900">{doc.empresa_nombre}</p>
              {doc.empresa_nif && <p className="text-xs text-gray-500">{doc.empresa_nif}</p>}
            </div>
          </div>
        </td>

        <td className="px-4 py-3 max-w-[200px]">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <p className="text-sm text-gray-700 truncate" title={doc.nombre_archivo}>{doc.nombre_archivo}</p>
          </div>
        </td>

        <td className="px-4 py-3">
          {doc.destinatarios?.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {doc.destinatarios.slice(0, 2).map(d => (
                <span key={d} className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs">
                  {d}
                </span>
              ))}
              {doc.destinatarios.length > 2 && (
                <span className="text-xs text-gray-400">+{doc.destinatarios.length - 2}</span>
              )}
            </div>
          ) : (
            <span className="text-xs text-amber-600 flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> Sin destinatarios
            </span>
          )}
        </td>

        <td className="px-4 py-3 whitespace-nowrap">
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            {formatFecha(doc.fecha_preparacion)}
          </div>
        </td>

        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => onSend(doc)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium transition-colors"
            >
              <Send className="w-3 h-3" /> Enviar
            </button>
            <button
              onClick={() => setExpanded(p => !p)}
              className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
              title="Ver asunto y mensaje"
            >
              <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </td>
      </tr>

      {expanded && (
        <tr className="bg-gray-50">
          <td />
          <td colSpan={5} className="px-4 py-3">
            <p className="text-xs font-semibold text-gray-600 mb-1">
              Asunto: <span className="font-normal">{doc.asunto || '—'}</span>
            </p>
            <pre className="text-xs text-gray-500 whitespace-pre-wrap font-sans">{doc.cuerpo || '—'}</pre>
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Vista principal ─────────────────────────────────────────────────────────

export default function EmailsPendientesView() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const [sending, setSending] = useState(false);
  const [erroresMasivo, setErroresMasivo] = useState([]);

  const [modalDoc, setModalDoc] = useState(null);
  const [showMasivo, setShowMasivo] = useState(false);

  const fetchPendientes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/emails-pendientes`, { credentials: 'include' });
      if (!res.ok) throw new Error('Error al cargar emails pendientes');
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setSelected(new Set());
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPendientes(); }, [fetchPendientes]);

  function toggleSelect(id) {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected(selected.size === items.length ? new Set() : new Set(items.map(d => d.id)));
  }

  const allSelected = items.length > 0 && selected.size === items.length;
  const someSelected = selected.size > 0 && selected.size < items.length;

  // Envío individual
  async function handleSendIndividual({ destinatarios, asunto, cuerpo }) {
    setSending(true);
    try {
      const res = await fetch(`${API}/api/emails-pendientes/${modalDoc.id}/enviar`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destinatarios, asunto, cuerpo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al enviar');
      toast.success('Correo enviado correctamente');
      setModalDoc(null);
      setItems(prev => prev.filter(d => d.id !== modalDoc.id));
      setTotal(t => t - 1);
      setSelected(prev => { const n = new Set(prev); n.delete(modalDoc.id); return n; });
    } catch (err) {
      toast.error(err.message, { duration: 6000 });
    } finally {
      setSending(false);
    }
  }

  // Envío masivo
  async function handleSendMasivo() {
    const doc_ids = selected.size > 0 ? [...selected] : [];
    setSending(true);
    setErroresMasivo([]);
    try {
      const res = await fetch(`${API}/api/emails-pendientes/enviar-masivo`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_ids }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error en envío masivo');

      const { enviados, errores } = data;

      if (enviados > 0) {
        toast.success(`${enviados} correo${enviados !== 1 ? 's' : ''} enviado${enviados !== 1 ? 's' : ''} correctamente`);
      }
      if (errores?.length > 0) {
        // Mostrar el error real en pantalla, no solo en consola
        setErroresMasivo(errores);
        toast.error(
          `${errores.length} error${errores.length !== 1 ? 'es' : ''}: ${errores[0].error}`,
          { duration: 8000 }
        );
      } else {
        setShowMasivo(false);
      }

      fetchPendientes();
    } catch (err) {
      toast.error(err.message, { duration: 6000 });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center">
            <Mail className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Correos Pendientes</h1>
            <p className="text-sm text-gray-500">
              {loading ? 'Cargando…' : `${total} correo${total !== 1 ? 's' : ''} pendiente${total !== 1 ? 's' : ''} de envío`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={fetchPendientes}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-60 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>

          {selected.size > 0 ? (
            <button
              onClick={() => { setErroresMasivo([]); setShowMasivo(true); }}
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-sm text-white font-medium disabled:opacity-60 transition-colors"
            >
              <Send className="w-4 h-4" />
              Enviar {selected.size} seleccionado{selected.size !== 1 ? 's' : ''}
            </button>
          ) : items.length > 0 ? (
            <button
              onClick={() => { setErroresMasivo([]); setShowMasivo(true); }}
              disabled={sending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 text-sm text-white font-medium disabled:opacity-60 transition-colors"
            >
              <Send className="w-4 h-4" />
              Enviar todos ({items.length})
            </button>
          ) : null}
        </div>
      </div>

      {/* Barra de selección */}
      {selected.size > 0 && (
        <div className="mb-3 flex items-center gap-3 px-4 py-2.5 bg-orange-50 border border-orange-200 rounded-lg">
          <CheckSquare className="w-4 h-4 text-orange-500" />
          <span className="text-sm text-orange-700 font-medium">
            {selected.size} documento{selected.size !== 1 ? 's' : ''} seleccionado{selected.size !== 1 ? 's' : ''}
          </span>
          <button onClick={() => setSelected(new Set())} className="ml-auto text-xs text-orange-600 hover:underline">
            Limpiar selección
          </button>
        </div>
      )}

      {/* Tabla */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading && items.length === 0 ? (
          <div className="flex items-center justify-center py-20 gap-3 text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin" />
            <span>Cargando correos pendientes…</span>
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-center px-4">
            <div className="w-16 h-16 rounded-2xl bg-green-50 flex items-center justify-center">
              <Mail className="w-8 h-8 text-green-500" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">No hay correos pendientes</h3>
              <p className="text-sm text-gray-500 max-w-xs">
                Todos los correos han sido enviados o aún no hay emails preparados.
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 w-10">
                    <button onClick={toggleAll} className="text-gray-400 hover:text-orange-500">
                      {allSelected
                        ? <CheckSquare className="w-4 h-4 text-orange-500" />
                        : someSelected
                          ? <CheckSquare className="w-4 h-4 text-orange-300" />
                          : <Square className="w-4 h-4" />}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center gap-1"><Building2 className="w-3.5 h-3.5" /> Empresa</div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> Documento</div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center gap-1"><Users className="w-3.5 h-3.5" /> Destinatarios</div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Preparado</div>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map(doc => (
                  <EmailRow
                    key={doc.id}
                    doc={doc}
                    selected={selected.has(doc.id)}
                    onToggle={toggleSelect}
                    onSend={setModalDoc}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modals */}
      {modalDoc && (
        <ModalConfirmEnvio
          doc={modalDoc}
          onConfirm={handleSendIndividual}
          onClose={() => setModalDoc(null)}
          loading={sending}
        />
      )}

      {showMasivo && (
        <ModalConfirmMasivo
          count={selected.size > 0 ? selected.size : items.length}
          erroresPrevios={erroresMasivo}
          onConfirm={handleSendMasivo}
          onClose={() => { setShowMasivo(false); setErroresMasivo([]); }}
          loading={sending}
        />
      )}
    </div>
  );
}
