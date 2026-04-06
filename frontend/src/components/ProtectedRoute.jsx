// frontend/src/components/ProtectedRoute.jsx
import React from 'react';
import { useAuth } from '../AuthContext';
import { Navigate, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function ProtectedRoute({ children }) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-12 h-12 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!auth.user) {
    // Redirigir al login, guardando la ubicación actual
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}