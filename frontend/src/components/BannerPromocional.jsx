// frontend/src/components/BannerPromocional.jsx
import React, { useState, useEffect } from 'react';
import { Sparkles, Copy, ArrowRight, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'react-hot-toast';
import axios from 'axios';

const BannerPromocional = ({ banners, onCambiarPlan }) => {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [copiado, setCopiado] = useState(false);

    if (!banners || banners.length === 0) return null;

    const currentBanner = banners[currentIndex];

    const handleNext = () => {
        setCurrentIndex((prev) => (prev + 1) % banners.length);
    };

    const handlePrevious = () => {
        setCurrentIndex((prev) => (prev - 1 + banners.length) % banners.length);
    };

    const handleDotClick = (index) => {
        setCurrentIndex(index);
    };

    // Keyboard navigation
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'ArrowLeft') {
                handlePrevious();
            } else if (e.key === 'ArrowRight') {
                handleNext();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentIndex, banners.length]); // eslint-disable-line react-hooks/exhaustive-deps

    const copiarCupon = async () => {
        try {
            await navigator.clipboard.writeText(currentBanner.cupon_codigo);
            setCopiado(true);
            toast.success('Cupón copiado al portapapeles');

            // Registrar click
            await axios.post(`/api/banners/${currentBanner.id}/click`);

            setTimeout(() => setCopiado(false), 2000);
        } catch (error) {
            console.error('Error copiando cupón:', error);
            toast.error('No se pudo copiar el cupón');
        }
    };

    const handleCambiarPlan = async () => {
        try {
            // Registrar click
            await axios.post(`/api/banners/${currentBanner.id}/click`);

            // Llamar callback con el cupón pre-aplicado
            onCambiarPlan(currentBanner.cupon_codigo);
        } catch (error) {
            console.error('Error:', error);
            onCambiarPlan(currentBanner.cupon_codigo);
        }
    };

    return (
        <div className="relative mb-6">
            <div
                className="relative overflow-hidden rounded-xl shadow-lg animate-fade-in transition-all duration-300"
                style={{
                    background: `linear-gradient(135deg, ${currentBanner.color_fondo} 0%, ${currentBanner.color_fondo}dd 100%)`
                }}
            >
                {/* Decoración de fondo */}
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white rounded-full -translate-y-1/2 translate-x-1/2"></div>
                    <div className="absolute bottom-0 left-0 w-48 h-48 bg-white rounded-full translate-y-1/2 -translate-x-1/2"></div>
                </div>

                {/* Contenido */}
                <div className="relative z-10 p-6">
                    <div className="flex items-start justify-between gap-4">
                        {/* Icono y texto */}
                        <div className="flex-1">
                            <div className="flex items-center gap-3 mb-3">
                                <span className="text-4xl">{currentBanner.icono}</span>
                                <div>
                                    <h3 className="text-2xl font-bold text-white mb-1">
                                        {currentBanner.titulo}
                                    </h3>
                                    {currentBanner.descripcion && (
                                        <p className="text-white/90 text-sm">
                                            {currentBanner.descripcion}
                                        </p>
                                    )}
                                </div>
                            </div>

                            {/* Cupón */}
                            {currentBanner.cupon_codigo && (
                                <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/30">
                                    <Sparkles className="w-4 h-4 text-white" />
                                    <span className="text-white font-mono font-bold">
                                        {currentBanner.cupon_codigo}
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* Botones de acción */}
                        <div className="flex flex-col gap-2">
                            {currentBanner.cupon_codigo && (
                                <button
                                    onClick={copiarCupon}
                                    className="flex items-center gap-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white px-4 py-2 rounded-lg transition-all border border-white/30 hover:border-white/50"
                                >
                                    {copiado ? (
                                        <>
                                            <Check className="w-4 h-4" />
                                            <span className="text-sm font-medium">Copiado</span>
                                        </>
                                    ) : (
                                        <>
                                            <Copy className="w-4 h-4" />
                                            <span className="text-sm font-medium">Copiar Cupón</span>
                                        </>
                                    )}
                                </button>
                            )}

                            <button
                                onClick={handleCambiarPlan}
                                className="flex items-center gap-2 bg-white hover:bg-white/90 text-gray-900 px-4 py-2 rounded-lg transition-all shadow-lg hover:shadow-xl font-medium"
                            >
                                <span className="text-sm">Cambiar de Plan</span>
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Flechas de navegación (solo si hay más de 1 banner) */}
                {banners.length > 1 && (
                    <>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handlePrevious();
                            }}
                            className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white p-2 rounded-full transition-all border border-white/30 hover:border-white/50 z-20"
                            aria-label="Banner anterior"
                        >
                            <ChevronLeft className="w-5 h-5" />
                        </button>

                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                handleNext();
                            }}
                            className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white p-2 rounded-full transition-all border border-white/30 hover:border-white/50 z-20"
                            aria-label="Siguiente banner"
                        >
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    </>
                )}
            </div>

            {/* Dots indicator (solo si hay más de 1 banner) */}
            {banners.length > 1 && (
                <div className="flex justify-center gap-2 mt-3">
                    {banners.map((_, index) => (
                        <button
                            key={index}
                            onClick={() => handleDotClick(index)}
                            className={`transition-all ${index === currentIndex
                                ? 'w-8 h-2 bg-orange-500'
                                : 'w-2 h-2 bg-gray-300 hover:bg-gray-400'
                                } rounded-full`}
                            aria-label={`Ir al banner ${index + 1}`}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};

export default BannerPromocional;
