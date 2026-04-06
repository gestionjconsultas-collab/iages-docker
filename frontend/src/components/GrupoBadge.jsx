// frontend/src/components/GrupoBadge.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FolderOpen } from 'lucide-react';

export default function GrupoBadge({ grupos }) {
  const navigate = useNavigate();

  if (!grupos || grupos.length === 0) return null;

  const colores = {
    blue: 'bg-blue-100 text-blue-700 border-blue-300',
    green: 'bg-green-100 text-green-700 border-green-300',
    red: 'bg-red-100 text-red-700 border-red-300',
    yellow: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    purple: 'bg-purple-100 text-purple-700 border-purple-300',
    pink: 'bg-pink-100 text-pink-700 border-pink-300',
    orange: 'bg-primary-light text-primary-hover border-orange-300',
  };

  const handleClick = (grupo) => {
    // Navegar a la vista de detalles del grupo
    navigate(`/empresa/${grupo.empresa_id}/grupos/${grupo.id}`);
  };

  return (
    <div className="flex flex-wrap gap-1">
      {grupos.map((grupo) => (
        <button
          key={grupo.id}
          onClick={() => handleClick(grupo)}
          className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${colores[grupo.color] || colores.blue
            } hover:opacity-80 transition-opacity cursor-pointer`}
          title={`Ver grupo: ${grupo.nombre}`}
        >
          <FolderOpen size={12} />
          {grupo.nombre}
        </button>
      ))}
    </div>
  );
}