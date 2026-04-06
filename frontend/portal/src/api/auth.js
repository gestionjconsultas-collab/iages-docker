import axios from 'axios';

const TOKEN_KEY = 'portal_token';
const EMPLEADO_KEY = 'portal_empleado';

export const authApi = {
  // ── Sesión local ───────────────────────────────────────────────────────────

  saveSession(token, empleado) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(EMPLEADO_KEY, JSON.stringify(empleado));
  },

  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMPLEADO_KEY);
  },

  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  getEmpleado() {
    try {
      return JSON.parse(localStorage.getItem(EMPLEADO_KEY));
    } catch {
      return null;
    }
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  // ── Requests ───────────────────────────────────────────────────────────────

  _headers() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  async login(email, password) {
    const res = await axios.post('/portal/api/auth/login', { email, password });
    this.saveSession(res.data.token, res.data.empleado);
    return res.data;
  },

  async activar(token, password) {
    const res = await axios.post('/portal/api/auth/activar', { token, password });
    if (res.data.token) {
      this.saveSession(res.data.token, res.data.empleado);
    }
    return res.data;
  },

  async recuperar(email) {
    const res = await axios.post('/portal/api/auth/recuperar', { email });
    return res.data;
  },

  async me() {
    const res = await axios.get('/portal/api/auth/me', {
      headers: this._headers(),
    });
    return res.data;
  },

  logout() {
    this.clearSession();
  },
};
