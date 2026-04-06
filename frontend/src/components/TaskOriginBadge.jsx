import React from 'react';
import './TaskOriginBadge.css';

/**
 * Componente para mostrar el origen de una tarea con icono y color
 * Muestra de dónde vino la tarea (Chat IA, manual, auto-asignada, etc.)
 */
const TaskOriginBadge = ({ origen, creado_por, size = 'normal', showLabel = true }) => {
    // Configuración de iconos y colores por origen
    const ORIGEN_CONFIG = {
        chat_ia: {
            icon: '🤖',
            label: 'Chat IA',
            color: '#8b5cf6',
            bgColor: '#f3e8ff'
        },
        manual: {
            icon: '✋',
            label: 'Manual',
            color: '#6b7280',
            bgColor: '#f3f4f6'
        },
        auto_asignada: {
            icon: '⚡',
            label: 'Auto-asignada',
            color: '#f59e0b',
            bgColor: '#fef3c7'
        },
        importada: {
            icon: '📥',
            label: 'Importada',
            color: '#3b82f6',
            bgColor: '#dbeafe'
        },
        calendario: {
            icon: '📅',
            label: 'Calendario',
            color: '#10b981',
            bgColor: '#d1fae5'
        },
        documento: {
            icon: '📄',
            label: 'Documento',
            color: '#ec4899',
            bgColor: '#fce7f3'
        }
    };

    const config = ORIGEN_CONFIG[origen] || ORIGEN_CONFIG.manual;

    // Tamaños
    const sizeClasses = {
        small: 'task-origin-badge-small',
        normal: 'task-origin-badge-normal',
        large: 'task-origin-badge-large'
    };

    return (
        <div className="task-origin-container">
            <span
                className={`task-origin-badge ${sizeClasses[size]}`}
                style={{
                    backgroundColor: config.bgColor,
                    color: config.color
                }}
                title={`Creada desde: ${config.label}${creado_por ? ` por ${creado_por}` : ''}`}
            >
                <span className="task-origin-icon">{config.icon}</span>
                {showLabel && <span className="task-origin-label">{config.label}</span>}
            </span>

            {creado_por && showLabel && (
                <span className="task-creator">
                    por <strong>{creado_por}</strong>
                </span>
            )}
        </div>
    );
};

export default TaskOriginBadge;
