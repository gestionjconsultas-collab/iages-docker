import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { authApi } from './api/auth';
import Login from './pages/Login';
import Activar from './pages/Activar';
import Recuperar from './pages/Recuperar';
import Dashboard from './pages/Dashboard';

function PrivateRoute({ empleado, children }) {
  if (!empleado) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const [empleado, setEmpleado] = useState(authApi.getEmpleado());
  const [loading, setLoading] = useState(!!authApi.getToken());
  const navigate = useNavigate();

  useEffect(() => {
    if (!authApi.getToken()) {
      setLoading(false);
      return;
    }
    authApi.me()
      .then(data => {
        setEmpleado(data.empleado);
        authApi.saveSession(authApi.getToken(), data.empleado);
      })
      .catch(() => {
        authApi.clearSession();
        setEmpleado(null);
        navigate('/login', { replace: true });
      })
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = (emp) => {
    setEmpleado(emp);
    navigate('/', { replace: true });
  };

  const handleLogout = () => {
    authApi.logout();
    setEmpleado(null);
    navigate('/login', { replace: true });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={handleLogin} />} />
      <Route path="/activar" element={<Activar onActivado={handleLogin} />} />
      <Route path="/recuperar" element={<Recuperar />} />
      <Route
        path="/*"
        element={
          <PrivateRoute empleado={empleado}>
            <Dashboard empleado={empleado} onLogout={handleLogout} />
          </PrivateRoute>
        }
      />
    </Routes>
  );
}
