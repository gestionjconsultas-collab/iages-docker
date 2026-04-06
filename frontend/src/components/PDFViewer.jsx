// frontend/src/components/PDFViewer.jsx
import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download } from 'lucide-react';

// Configurar worker de PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

/**
 * Componente para mostrar PDFs con controles completos de navegación
 * Usa react-pdf para mejor compatibilidad cross-browser
 */
export default function PDFViewer({ documentId, pdfUrl, className = "w-full h-full" }) {
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Usar pdfUrl si se proporciona, sino construir desde documentId
    const url = pdfUrl || `/api/documentos/${documentId}/archivo`;

    function onDocumentLoadSuccess({ numPages }) {
        setNumPages(numPages);
        setLoading(false);
        setError(null);
    }

    function onDocumentLoadError(error) {
        console.error('Error loading PDF:', error);
        setError('Error al cargar el PDF');
        setLoading(false);
    }

    const changePage = (offset) => {
        setPageNumber(prevPageNumber => prevPageNumber + offset);
    };

    const previousPage = () => {
        if (pageNumber > 1) changePage(-1);
    };

    const nextPage = () => {
        if (pageNumber < numPages) changePage(1);
    };

    const zoomIn = () => {
        setScale(prevScale => Math.min(prevScale + 0.2, 3.0));
    };

    const zoomOut = () => {
        setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-100">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Cargando PDF...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full bg-gray-100 p-8">
                <div className="text-center">
                    <svg className="w-16 h-16 mx-auto mb-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-red-600 mb-4">{error}</p>
                    <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        <Download className="w-5 h-5" />
                        Descargar PDF
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className={`flex flex-col ${className}`}>
            {/* Controles superiores */}
            <div className="bg-gray-800 px-4 py-2 flex items-center justify-between text-white text-sm flex-shrink-0">
                <div className="flex items-center gap-2">
                    <button
                        onClick={previousPage}
                        disabled={pageNumber <= 1}
                        className="p-2 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Página anterior"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="font-medium min-w-[80px] text-center">
                        {pageNumber} / {numPages}
                    </span>
                    <button
                        onClick={nextPage}
                        disabled={pageNumber >= numPages}
                        className="p-2 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Página siguiente"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={zoomOut}
                        className="p-2 hover:bg-gray-700 rounded transition-colors"
                        title="Alejar"
                    >
                        <ZoomOut className="w-5 h-5" />
                    </button>
                    <span className="font-medium min-w-[60px] text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <button
                        onClick={zoomIn}
                        className="p-2 hover:bg-gray-700 rounded transition-colors"
                        title="Acercar"
                    >
                        <ZoomIn className="w-5 h-5" />
                    </button>
                </div>

                <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 hover:bg-gray-700 rounded transition-colors"
                    title="Descargar PDF"
                >
                    <Download className="w-5 h-5" />
                </a>
            </div>

            {/* Visor PDF */}
            <div className="flex-1 overflow-auto bg-gray-900 p-4">
                <div className="flex justify-center">
                    <Document
                        file={url}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading={
                            <div className="text-white">Cargando documento...</div>
                        }
                    >
                        <Page
                            pageNumber={pageNumber}
                            scale={scale}
                            renderTextLayer={true}
                            renderAnnotationLayer={true}
                            className="shadow-2xl"
                        />
                    </Document>
                </div>
            </div>
        </div>
    );
}
