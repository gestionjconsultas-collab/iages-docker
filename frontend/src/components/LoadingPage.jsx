import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingPage = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        {/* Logo o spinner */}
        <div className="mb-4 flex justify-center">
          <div className="relative">
            <div className="w-16 h-16 rounded-full border-4 border-gray-200 dark:border-gray-700"></div>
            <div className="absolute top-0 left-0 w-16 h-16 rounded-full border-4 border-t-orange-500 border-r-red-500 border-b-transparent border-l-transparent animate-spin"></div>
          </div>
        </div>
        
        {/* Texto */}
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Cargando...
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Preparando componente
        </p>
      </div>
    </div>
  );
};

export default LoadingPage;