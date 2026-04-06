import React from 'react';

/**
 * Componente simple que muestra PDFs usando el visor nativo del navegador
 * Usa <embed> para mostrar el PDF directamente embebido
 */
export default function MobilePDFViewer({ documentId, pdfUrl }) {
    const url = pdfUrl || `/api/documentos/${documentId}/archivo`;

    return (
        <embed
            src={url}
            type="application/pdf"
            className="w-full h-full"
            style={{ border: 'none' }}
        />
    );
}
