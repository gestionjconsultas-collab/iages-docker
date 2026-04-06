// frontend/src/components/PreferenciasModal.jsx
import React, { useState } from 'react';
import { X, Settings, Save, Loader2, Bell, Layout, Shield, Key, RefreshCw, XCircle } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '../AuthContext';
import toast from 'react-hot-toast';
import useEscapeKey from '../hooks/useEscapeKey';
import NotificationSettings from './NotificationSettings';
import TwoFactorSetup from './TwoFactorSetup';
import BackupCodesModal from './BackupCodesModal';
import PasswordConfirmModal from './PasswordConfirmModal';


export default function PreferenciasModal({ onClose }) {
  useEscapeKey(onClose);
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('general'); // 'general', 'notifications', 'security'
  const [show2FASetup, setShow2FASetup] = useState(false);
  const [showBackupCodes, setShowBackupCodes] = useState(false);
  const [backupCodes, setBackupCodes] = useState([]);
  const [passwordPrompt, setPasswordPrompt] = useState({ show: false, action: null });

  const [prefs, setPrefs] = useState({
    emailNotif: user?.preferencias?.emailNotif ?? true,
    vistaInicio: user?.preferencias?.vistaInicio || 'dashboard'
  });

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await axios.put('/api/users/me/update',
        { preferencias: prefs },
        { withCredentials: true }
      );
      if (res.data.success) {
        toast.success('Preferencias guardadas');
        setTimeout(() => window.location.reload(), 1000);
      }
    } catch (err) {
      toast.error("Error al guardar preferencias: " + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };
  const [passwordModal, setPasswordModal] = useState({
    isOpen: false,
    action: null,
    title: '',
    message: '',
    confirmText: '',
    confirmColor: 'orange',
    showWarning: false,
    warningMessage: ''
  });

  const handlePasswordConfirm = async (password) => {
    try {
      if (passwordModal.action === 'regenerate') {
        const response = await axios.post('/api/auth/2fa/regenerate-backup-codes',
          { password },
          { withCredentials: true }
        );
        setBackupCodes(response.data.backup_codes);
        setShowBackupCodes(true);
        toast.success('Códigos regenerados exitosamente');
      } else if (passwordModal.action === 'disable') {
        await axios.post('/api/auth/2fa/disable', { password }, { withCredentials: true });
        toast.success('2FA desactivado');
        setTimeout(() => window.location.reload(), 1000);
      }
    } catch (error) {
      toast.error(error.response?.data?.error || 'Error al procesar la solicitud');
      throw error; // Re-throw para que el modal maneje el error
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-100 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex justify-between items-center p-4 border-b bg-gray-50">
          <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" /> Preferencias
          </h2>
          <button onClick={onClose}><X className="w-5 h-5 text-gray-500 hover:text-gray-700" /></button>
        </div>

        {/* Tabs */}
        <div className="flex border-b bg-gray-50">
          <button
            onClick={() => setActiveTab('general')}
            className={`flex-1 px-4 py-3 font-medium text-sm transition ${activeTab === 'general'
              ? 'text-primary border-b-2 border-primary bg-white'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            General
          </button>
          <button
            onClick={() => setActiveTab('notifications')}
            className={`flex-1 px-4 py-3 font-medium text-sm transition ${activeTab === 'notifications'
              ? 'text-primary border-b-2 border-primary bg-white'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <Bell className="w-4 h-4 inline mr-1" />
            Notificaciones
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`flex-1 px-4 py-3 font-medium text-sm transition ${activeTab === 'security'
              ? 'text-primary border-b-2 border-primary bg-white'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <Settings className="w-4 h-4 inline mr-1" />
            Seguridad
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'general' && (
            <div className="p-6 space-y-6">
              {/* Notificaciones Email */}
              <div className="flex items-start gap-4">
                <div className="p-2 bg-blue-50 rounded-lg text-blue-600"><Bell className="w-6 h-6" /></div>
                <div className="flex-1">
                  <label className="flex items-center justify-between cursor-pointer mb-1">
                    <span className="font-medium text-gray-900">Notificaciones Email</span>
                    <input type="checkbox" className="w-5 h-5 text-primary rounded focus:ring-primary" checked={prefs.emailNotif} onChange={e => setPrefs({ ...prefs, emailNotif: e.target.checked })} />
                  </label>
                  <p className="text-xs text-gray-500">Recibir correos cuando se te asigne una tarea.</p>
                </div>
              </div>

              <hr className="border-gray-100" />

              {/* Vista de Inicio */}
              <div className="flex items-start gap-4">
                <div className="p-2 bg-purple-50 rounded-lg text-purple-600"><Layout className="w-6 h-6" /></div>
                <div className="flex-1">
                  <label className="block font-medium text-gray-900 mb-1">Vista de Inicio</label>
                  <p className="text-xs text-gray-500 mb-3">Pantalla principal al iniciar sesión.</p>
                  <select className="w-full p-2 border rounded-lg text-sm bg-white" value={prefs.vistaInicio} onChange={e => setPrefs({ ...prefs, vistaInicio: e.target.value })}>
                    <option value="dashboard">Dashboard de Empresas</option>
                    <option value="calendario">Calendario de Tareas</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="p-6">
              <NotificationSettings />
            </div>
          )}

          {activeTab === 'security' && (
            <div className="p-6">
              {show2FASetup ? (
                <TwoFactorSetup
                  onComplete={() => {
                    setShow2FASetup(false);
                    toast.success('2FA configurado exitosamente');
                    setTimeout(() => window.location.reload(), 1500);
                  }}
                  onCancel={() => setShow2FASetup(false)}
                />
              ) : (
                <div className="space-y-6">
                  {/* Header */}
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <Shield className="w-6 h-6 text-orange-600" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-gray-900 mb-1">
                        Autenticación de Dos Factores (2FA)
                      </h3>
                      <p className="text-sm text-gray-600">
                        Añade una capa extra de seguridad requiriendo un código de verificación además de tu contraseña.
                      </p>
                    </div>
                  </div>

                  {/* Estado de 2FA */}
                  {user?.two_factor_enabled ? (
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 shadow-sm">
                      <div className="flex items-start gap-4">
                        <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 shadow-md">
                          <Shield className="w-7 h-7 text-green-600" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="text-lg font-bold text-green-900">2FA Activado</h4>
                            <span className="px-2 py-1 bg-green-200 text-green-800 text-xs font-semibold rounded-full">
                              ACTIVO
                            </span>
                          </div>
                          <p className="text-sm text-green-700 mb-4">
                            Tu cuenta está protegida con autenticación de dos factores.
                          </p>

                          {/* Estadísticas */}
                          <div className="bg-white rounded-lg p-3 mb-4 border border-green-100">
                            <div className="flex items-center gap-2">
                              <Key className="w-4 h-4 text-green-600" />
                              <span className="text-sm text-gray-700">
                                <strong>{user?.backup_codes_count || 0}</strong> códigos de respaldo disponibles
                              </span>
                            </div>
                          </div>

                          {/* Botones de acción */}
                          <div className="flex flex-wrap gap-2">
                            <button
                              onClick={() => {
                                setPasswordModal({
                                  isOpen: true,
                                  action: 'regenerate',
                                  title: 'Regenerar Códigos de Respaldo',
                                  message: 'Los códigos actuales dejarán de funcionar. Se generarán 10 nuevos códigos.',
                                  confirmText: 'Regenerar',
                                  confirmColor: 'blue',
                                  showWarning: true,
                                  warningMessage: '⚠️ Esta acción invalidará todos los códigos de respaldo actuales.'
                                });
                              }}
                              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-sm font-medium shadow-sm flex items-center gap-2"
                            >
                              <RefreshCw className="w-4 h-4" />
                              Regenerar Códigos
                            </button>
                            <button
                              onClick={() => {
                                setPasswordModal({
                                  isOpen: true,
                                  action: 'disable',
                                  title: 'Desactivar 2FA',
                                  message: 'Tu cuenta será menos segura sin autenticación de dos factores.',
                                  confirmText: 'Desactivar',
                                  confirmColor: 'red',
                                  showWarning: true,
                                  warningMessage: '⚠️ Al desactivar 2FA, tu cuenta quedará protegida solo con contraseña.'
                                });
                              }}
                              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition text-sm font-medium shadow-sm flex items-center gap-2"
                            >
                              <XCircle className="w-4 h-4" />
                              Desactivar 2FA
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gradient-to-r from-orange-50 to-red-50 border-2 border-orange-200 rounded-xl p-6 shadow-sm">
                      <div className="flex items-start gap-4">
                        <div className="w-14 h-14 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0 shadow-md">
                          <Shield className="w-7 h-7 text-orange-600" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="text-lg font-bold text-orange-900">2FA Desactivado</h4>
                            <span className="px-2 py-1 bg-orange-200 text-orange-800 text-xs font-semibold rounded-full">
                              INACTIVO
                            </span>
                          </div>
                          <p className="text-sm text-orange-700 mb-4">
                            Recomendamos activar 2FA para proteger mejor tu cuenta.
                          </p>

                          {/* Beneficios */}
                          <div className="bg-white rounded-lg p-3 mb-4 border border-orange-100">
                            <p className="text-xs font-semibold text-gray-700 mb-2">Beneficios de 2FA:</p>
                            <ul className="text-xs text-gray-600 space-y-1">
                              <li>✓ Protección contra accesos no autorizados</li>
                              <li>✓ Compatible con Google Authenticator y Microsoft Authenticator</li>
                              <li>✓ Códigos de respaldo por si pierdes tu dispositivo</li>
                            </ul>
                          </div>

                          <button
                            onClick={() => setShow2FASetup(true)}
                            className="px-6 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition font-medium shadow-md flex items-center gap-2"
                          >
                            <Shield className="w-5 h-5" />
                            Activar 2FA Ahora
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Modal de códigos de respaldo */}
              {showBackupCodes && (
                <BackupCodesModal
                  codes={backupCodes}
                  onClose={() => {
                    setShowBackupCodes(false);
                    setTimeout(() => window.location.reload(), 500);
                  }}
                />
              )}
              <PasswordConfirmModal
                isOpen={passwordModal.isOpen}
                onClose={() => setPasswordModal({ ...passwordModal, isOpen: false })}
                onConfirm={handlePasswordConfirm}
                title={passwordModal.title}
                message={passwordModal.message}
                confirmText={passwordModal.confirmText}
                confirmColor={passwordModal.confirmColor}
                showWarning={passwordModal.showWarning}
                warningMessage={passwordModal.warningMessage}
              />
            </div>
          )}


        </div>

        {/* Footer - Solo mostrar en tab general */}
        {activeTab === 'general' && (
          <div className="p-4 bg-gray-50 border-t flex justify-end gap-3">
            <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg text-sm font-medium">Cancelar</button>
            <button onClick={handleSave} disabled={loading} className="px-4 py-2 bg-primary text-black rounded-lg hover:bg-primary-hover flex items-center gap-2 text-sm font-bold shadow-sm">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Guardar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}