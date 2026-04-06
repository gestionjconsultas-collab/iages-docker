// frontend/src/components/ProcesandoToast.jsx
import React from 'react';
import { Loader2 } from 'lucide-react';

export default function ProcesandoToast() {
  return (
    <div className="fixed top-6 right-6 z-50">
      <div className="flex items-center gap-3 p-4 bg-white rounded-lg shadow-xl border border-blue-200">
        <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
        <span className="font-medium text-blue-700">
          Procesando con IA, por favor espera...
        </span>
      </div>
    </div>
  );
}