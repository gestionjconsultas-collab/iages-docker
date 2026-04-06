import React, { useState } from 'react';
import './TagSelector.css';

/**
 * Componente para seleccionar y crear tags para tareas
 * Permite seleccionar tags predefinidos y crear nuevos
 */
const TagSelector = ({ selectedTags = [], onChange }) => {
    const [inputValue, setInputValue] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);

    // Tags predefinidos comunes
    const PREDEFINED_TAGS = [
        'urgente',
        'fiscal',
        'nominas',
        'seguros',
        'rlc',
        'dehu',
        'cliente_vip',
        'revision',
        'seguimiento',
        'pendiente_cliente',
        'alta_prioridad',
        'baja_prioridad'
    ];

    // Filtrar tags sugeridos basado en input
    const getSuggestions = () => {
        if (!inputValue) return PREDEFINED_TAGS;
        return PREDEFINED_TAGS.filter(tag =>
            tag.toLowerCase().includes(inputValue.toLowerCase()) &&
            !selectedTags.includes(tag)
        );
    };

    // Agregar tag
    const addTag = (tag) => {
        if (!tag || selectedTags.includes(tag)) return;

        const newTags = [...selectedTags, tag.toLowerCase().trim()];
        onChange(newTags);
        setInputValue('');
        setShowSuggestions(false);
    };

    // Remover tag
    const removeTag = (tagToRemove) => {
        const newTags = selectedTags.filter(tag => tag !== tagToRemove);
        onChange(newTags);
    };

    // Manejar Enter
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && inputValue.trim()) {
            e.preventDefault();
            addTag(inputValue);
        }
    };

    // Colores para tags
    const getTagColor = (tag) => {
        const colors = {
            urgente: '#ef4444',
            fiscal: '#3b82f6',
            nominas: '#8b5cf6',
            seguros: '#10b981',
            rlc: '#f59e0b',
            dehu: '#06b6d4',
            cliente_vip: '#ec4899',
            revision: '#6366f1',
            seguimiento: '#14b8a6',
            pendiente_cliente: '#f97316',
            alta_prioridad: '#dc2626',
            baja_prioridad: '#84cc16'
        };
        return colors[tag] || '#6b7280';
    };

    return (
        <div className="tag-selector">
            <label className="tag-selector-label">
                Tags
                <span className="tag-selector-hint">
                    (Presiona Enter para agregar)
                </span>
            </label>

            {/* Tags seleccionados */}
            <div className="selected-tags">
                {selectedTags.map(tag => (
                    <span
                        key={tag}
                        className="tag-badge"
                        style={{ backgroundColor: getTagColor(tag) }}
                    >
                        {tag}
                        <button
                            type="button"
                            className="tag-remove"
                            onClick={() => removeTag(tag)}
                            aria-label={`Remover ${tag}`}
                        >
                            ×
                        </button>
                    </span>
                ))}
            </div>

            {/* Input para agregar tags */}
            <div className="tag-input-container">
                <input
                    type="text"
                    className="tag-input"
                    placeholder="Agregar tag..."
                    value={inputValue}
                    onChange={(e) => {
                        setInputValue(e.target.value);
                        setShowSuggestions(true);
                    }}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setShowSuggestions(true)}
                    onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                />

                {/* Sugerencias */}
                {showSuggestions && getSuggestions().length > 0 && (
                    <div className="tag-suggestions">
                        {getSuggestions().map(tag => (
                            <button
                                key={tag}
                                type="button"
                                className="tag-suggestion"
                                onClick={() => addTag(tag)}
                            >
                                <span
                                    className="tag-suggestion-color"
                                    style={{ backgroundColor: getTagColor(tag) }}
                                />
                                {tag}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Contador */}
            <div className="tag-counter">
                {selectedTags.length} tag{selectedTags.length !== 1 ? 's' : ''} seleccionado{selectedTags.length !== 1 ? 's' : ''}
            </div>
        </div>
    );
};

export default TagSelector;
