// frontend/src/components/MensajeBurbuja.jsx
// v2: adjuntos, notas internas (estilo ámbar), read receipts ✓/✓✓ con color
import React from 'react';
import { Paperclip, Download } from 'lucide-react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || '';

// Solo imágenes permitidas como adjuntos (sin PDF/docs por seguridad)
const IMAGENES = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp']);

const MensajeBurbuja = ({ mensaje, currentUserId }) => {
    const esMio      = Number(mensaje.usuario_id) === Number(currentUserId);
    const esSoporte  = mensaje.es_respuesta_soporte;
    const esSistema  = mensaje.es_mensaje_sistema;
    const esInterno  = mensaje.es_interno;

    // ── Mensaje del sistema ──
    if (esSistema) {
        return (
            <div className="flex justify-center my-3">
                <div className="px-4 py-2 bg-gray-200 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full text-xs max-w-sm text-center shadow-sm">
                    ℹ️ {mensaje.mensaje}
                </div>
            </div>
        );
    }

    // ── Nota interna (solo visible para agentes) ──
    if (esInterno) {
        return (
            <div className="flex justify-end my-1">
                <div className="max-w-xs lg:max-w-md px-4 py-3 rounded-2xl rounded-br-none shadow-sm
                                bg-amber-50 border border-amber-300 text-amber-900">
                    <p className="text-xs font-semibold mb-1 text-amber-700 flex items-center gap-1">
                        🔒 Nota interna · {mensaje.usuario_nombre || 'Agente'}
                    </p>
                    <p className="text-sm whitespace-pre-wrap break-words">{mensaje.mensaje}</p>
                    <_Adjuntos adjuntos={mensaje.adjuntos} ticketId={mensaje.ticket_id} />
                    <_Footer esMio={esMio} mensaje={mensaje} colorBase="text-amber-600" />
                </div>
            </div>
        );
    }

    // ── Mensaje normal ──
    // Soporte → izquierda; usuario (y "yo") → derecha
    const aLaIzquierda = esSoporte && !esMio;

    return (
        <div className={`flex ${aLaIzquierda ? 'justify-start' : 'justify-end'} my-1`}>
            <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl shadow-md
                ${aLaIzquierda
                    ? 'bg-white dark:bg-slate-800 text-gray-900 dark:text-gray-100 rounded-bl-none border border-gray-200 dark:border-slate-700'
                    : 'bg-blue-600 text-white rounded-br-none'}`}>

                {/* Nombre del remitente (solo en mensajes de soporte ajenos) */}
                {aLaIzquierda && (
                    <p className="text-xs font-semibold mb-1 text-green-700 dark:text-green-400">
                        💬 {mensaje.usuario_nombre || 'Soporte'}
                    </p>
                )}

                {/* Texto */}
                <p className="text-sm whitespace-pre-wrap break-words">{mensaje.mensaje}</p>

                {/* Adjuntos */}
                <_Adjuntos adjuntos={mensaje.adjuntos} ticketId={mensaje.ticket_id}
                    className={aLaIzquierda ? 'text-blue-600' : 'text-blue-100'} />

                {/* Footer: hora + read receipt */}
                <_Footer esMio={esMio} mensaje={mensaje}
                    colorBase={aLaIzquierda ? 'text-gray-400' : 'text-blue-100'} />
            </div>
        </div>
    );
};

// ---------------------------------------------------------------------------
// Sub-componente: adjuntos
// ---------------------------------------------------------------------------
function _Adjuntos({ adjuntos, ticketId, className = 'text-blue-200' }) {
    if (!adjuntos || adjuntos.length === 0) return null;

    return (
        <div className="mt-2 space-y-1">
            {adjuntos.map((adj, i) => {
                const ext    = adj.nombre?.split('.').pop()?.toLowerCase() || '';
                const esImg  = IMAGENES.has(ext);
                const urlDl  = `${BACKEND_URL}/api/soporte/adjuntos/${ticketId}/${adj.nombre_disco || adj.nombre}`;

                if (esImg) {
                    return (
                        <a key={i} href={urlDl} target="_blank" rel="noopener noreferrer"
                            className="block rounded-lg overflow-hidden max-w-[200px] mt-1">
                            <img src={urlDl} alt={adj.nombre}
                                className="rounded-lg max-h-40 object-cover w-full" />
                        </a>
                    );
                }

                return (
                    <a key={i} href={urlDl} target="_blank" rel="noopener noreferrer"
                        className={`flex items-center gap-2 text-xs ${className} hover:underline`}>
                        <Paperclip className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate max-w-[180px]">{adj.nombre}</span>
                        <Download className="w-3 h-3 flex-shrink-0" />
                    </a>
                );
            })}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Sub-componente: footer (hora + leído)
// ---------------------------------------------------------------------------
function _Footer({ esMio, mensaje, colorBase }) {
    const hora = new Date(mensaje.fecha_creacion).toLocaleTimeString('es-ES', {
        hour: '2-digit', minute: '2-digit'
    });

    return (
        <div className="flex items-center justify-end gap-1 mt-1">
            <span className={`text-xs ${colorBase}`}>{hora}</span>
            {esMio && (
                <span className={`text-xs ${mensaje.leido ? 'text-blue-300' : colorBase}`}
                    title={mensaje.leido ? 'Leído' : 'Enviado'}>
                    {mensaje.leido ? '✓✓' : '✓'}
                </span>
            )}
        </div>
    );
}

export default MensajeBurbuja;
