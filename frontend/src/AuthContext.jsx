// frontend/src/AuthContext.jsx
import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from './utils/axiosConfig';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // Empezar en true para verificar el estado

  useEffect(() => {
    // Comprobar si ya hay una sesión activa en el backend
    const checkAuthStatus = async () => {
      try {
        const response = await axios.get('/api/auth/status');
        if (response.data.success) {
          setUser(response.data.user);
        }
      } catch (error) {
        console.log("No hay sesión activa.");
      }
      setLoading(false);
    };
    checkAuthStatus();
  }, []);

  // Guardar gestoria_id en localStorage cuando el usuario cambia
  useEffect(() => {
    if (user && user.gestoria_id) {
      localStorage.setItem('gestoria_id', user.gestoria_id.toString());
    } else {
      localStorage.removeItem('gestoria_id');
    }
  }, [user]);

  const login = async (email, password) => {
    try {
      const response = await axios.post('/api/auth/login', { email, password });
      if (response.data.success) {
        // Verificar si requiere 2FA
        if (response.data.requires_2fa) {
          return 'requires_2fa';
        }
        // Login exitoso sin 2FA
        setUser(response.data.user);
        return true;
      }
    } catch (error) {
      throw new Error(error.response?.data?.error || "Error al iniciar sesión");
    }
    return false;
  };


  const logout = async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.error("Error al cerrar sesión:", error);
    }
    setUser(null);
  };

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get('/api/auth/status');
      if (response.data.success) {
        setUser(response.data.user);
        return response.data.user;
      }
    } catch (error) {
      console.log("No hay sesión activa.");
    }
    return null;
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, checkAuthStatus, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};