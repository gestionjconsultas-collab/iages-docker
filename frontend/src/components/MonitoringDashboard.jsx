// frontend/src/components/MonitoringDashboard.jsx
/**
 * Dashboard de Monitoreo para Super-Admin
 * Visualiza métricas de Prometheus, alertas y estado del sistema
 */

import { useState, useEffect } from 'react';
import axios from 'axios';
import './MonitoringDashboard.css';

const MonitoringDashboard = () => {
    const [dashboard, setDashboard] = useState(null);
    const [alerts, setAlerts] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');

    useEffect(() => {
        loadDashboardData();
        // Actualizar cada 30 segundos
        const interval = setInterval(loadDashboardData, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadDashboardData = async () => {
        try {
            const [dashboardRes, alertsRes, healthRes] = await Promise.all([
                axios.get('/api/admin/monitoring/dashboard'),
                axios.get('/api/admin/monitoring/alerts'),
                axios.get('/api/admin/monitoring/health')
            ]);

            setDashboard(dashboardRes.data.dashboard);
            setAlerts(alertsRes.data.alerts);
            setHealth(healthRes.data.health);
            setLoading(false);
        } catch (error) {
            console.error('Error cargando dashboard:', error);
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="monitoring-loading">
                <div className="spinner"></div>
                <p>Cargando métricas del sistema...</p>
            </div>
        );
    }

    return (
        <div className="monitoring-dashboard">
            <div className="monitoring-header">
                <h1>🔬 Dashboard de Monitoreo</h1>
                <div className="header-actions">
                    <button onClick={loadDashboardData} className="btn-refresh">
                        🔄 Actualizar
                    </button>
                    <span className="last-update">
                        Última actualización: {new Date().toLocaleTimeString()}
                    </span>
                </div>
            </div>

            {/* Alertas */}
            {alerts.length > 0 && (
                <div className="alerts-section">
                    <h2>⚠️ Alertas Activas ({alerts.length})</h2>
                    <div className="alerts-grid">
                        {alerts.map((alert, idx) => (
                            <div key={idx} className={`alert alert-${alert.level}`}>
                                <div className="alert-header">
                                    <span className="alert-icon">
                                        {alert.level === 'error' ? '🔴' : alert.level === 'warning' ? '🟡' : 'ℹ️'}
                                    </span>
                                    <strong>{alert.title}</strong>
                                </div>
                                <p>{alert.message}</p>
                                <small className="alert-action">💡 {alert.action}</small>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Tabs */}
            <div className="monitoring-tabs">
                <button
                    className={activeTab === 'overview' ? 'tab active' : 'tab'}
                    onClick={() => setActiveTab('overview')}
                >
                    📊 Resumen
                </button>
                <button
                    className={activeTab === 'health' ? 'tab active' : 'tab'}
                    onClick={() => setActiveTab('health')}
                >
                    💚 Estado del Sistema
                </button>
                <button
                    className={activeTab === 'activity' ? 'tab active' : 'tab'}
                    onClick={() => setActiveTab('activity')}
                >
                    📈 Actividad
                </button>
                <button
                    className={activeTab === 'metrics' ? 'tab active' : 'tab'}
                    onClick={() => setActiveTab('metrics')}
                >
                    📊 Métricas
                </button>
            </div>

            {/* Contenido de tabs */}
            <div className="tab-content">
                {activeTab === 'overview' && (
                    <OverviewTab dashboard={dashboard} />
                )}
                {activeTab === 'health' && (
                    <HealthTab health={health} />
                )}
                {activeTab === 'activity' && (
                    <ActivityTab dashboard={dashboard} />
                )}
                {activeTab === 'metrics' && (
                    <MetricsTab />
                )}
            </div>
        </div>
    );
};

// Tab de Resumen
const OverviewTab = ({ dashboard }) => {
    if (!dashboard) return null;

    const stats = dashboard.statistics;

    return (
        <div className="overview-tab">
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon">👥</div>
                    <div className="stat-content">
                        <h3>{stats.total_users}</h3>
                        <p>Usuarios Totales</p>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">📄</div>
                    <div className="stat-content">
                        <h3>{stats.total_documents}</h3>
                        <p>Documentos Totales</p>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">📅</div>
                    <div className="stat-content">
                        <h3>{stats.documents_today}</h3>
                        <p>Documentos Hoy</p>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon">⚡</div>
                    <div className="stat-content">
                        <h3>{stats.activity_24h}</h3>
                        <p>Acciones (24h)</p>
                    </div>
                </div>
            </div>

            {/* Top Usuarios */}
            <div className="top-users-section">
                <h3>🏆 Usuarios Más Activos (7 días)</h3>
                <div className="users-list">
                    {dashboard.top_users.map((user, idx) => (
                        <div key={idx} className="user-item">
                            <span className="user-rank">#{idx + 1}</span>
                            <span className="user-name">{user.nombre}</span>
                            <span className="user-actions">{user.acciones} acciones</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

// Tab de Estado del Sistema
const HealthTab = ({ health }) => {
    if (!health) return null;

    const getStatusIcon = (status) => {
        if (status === 'healthy' || status === 'active') return '✅';
        if (status === 'degraded') return '⚠️';
        if (status === 'inactive') return '⭕';
        return '❌';
    };

    return (
        <div className="health-tab">
            <div className="health-overview">
                <div className={`health-status health-${health.status}`}>
                    <h2>{getStatusIcon(health.status)} Sistema {health.status === 'healthy' ? 'Saludable' : 'Degradado'}</h2>
                </div>
            </div>

            <div className="health-checks">
                <h3>Verificaciones de Componentes</h3>
                {Object.entries(health.checks).map(([component, check]) => (
                    <div key={component} className="health-check-item">
                        <div className="check-header">
                            <span className="check-icon">{getStatusIcon(check.status)}</span>
                            <strong>{component.toUpperCase()}</strong>
                            <span className={`check-badge badge-${check.status}`}>
                                {check.status}
                            </span>
                        </div>
                        <p className="check-message">{check.message}</p>
                    </div>
                ))}
            </div>

            <div className="health-links">
                <h3>Enlaces Útiles</h3>
                <div className="links-grid">
                    <a href="/api/docs" target="_blank" className="health-link">
                        📚 Swagger API Docs
                    </a>
                    <a href="/metrics" target="_blank" className="health-link">
                        📊 Prometheus Metrics
                    </a>
                    <a href="https://sentry.io" target="_blank" className="health-link">
                        🐛 Sentry Dashboard
                    </a>
                </div>
            </div>
        </div>
    );
};

// Tab de Actividad
const ActivityTab = ({ dashboard }) => {
    if (!dashboard) return null;

    return (
        <div className="activity-tab">
            <h3>🚨 Errores Recientes (24h)</h3>
            {dashboard.recent_errors.length === 0 ? (
                <div className="no-errors">
                    <p>✅ No hay errores recientes</p>
                </div>
            ) : (
                <div className="errors-list">
                    {dashboard.recent_errors.map((error) => (
                        <div key={error.id} className="error-item">
                            <div className="error-header">
                                <span className="error-icon">🔴</span>
                                <strong>{error.accion}</strong>
                                <span className="error-time">
                                    {new Date(error.fecha).toLocaleString()}
                                </span>
                            </div>
                            <p className="error-description">{error.descripcion}</p>
                            <small className="error-user">Usuario: {error.user}</small>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// Tab de Métricas de Prometheus
const MetricsTab = () => {
    const [metrics, setMetrics] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadMetrics();
    }, []);

    const loadMetrics = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await axios.get('/metrics');
            setMetrics(response.data);
            setLoading(false);
        } catch (err) {
            console.error('Error cargando métricas:', err);
            setError('No se pudieron cargar las métricas de Prometheus');
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="metrics-tab">
                <div className="metrics-loading">
                    <div className="spinner"></div>
                    <p>Cargando métricas de Prometheus...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="metrics-tab">
                <div className="metrics-error">
                    <p>❌ {error}</p>
                    <button onClick={loadMetrics} className="btn-retry">
                        🔄 Reintentar
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="metrics-tab">
            <div className="metrics-header">
                <h3>📊 Métricas de Prometheus</h3>
                <div className="metrics-actions">
                    <button onClick={loadMetrics} className="btn-refresh-small">
                        🔄 Actualizar
                    </button>
                    <a href="/metrics" target="_blank" className="btn-open-raw">
                        🔗 Abrir en nueva pestaña
                    </a>
                </div>
            </div>
            <div className="metrics-content">
                <pre className="metrics-raw">
                    <code>{metrics}</code>
                </pre>
            </div>
            <div className="metrics-footer">
                <p>
                    💡 <strong>Tip:</strong> Estas métricas están en formato Prometheus.
                    Puedes conectar Grafana para visualizarlas de forma más amigable.
                </p>
            </div>
        </div>
    );
};

export default MonitoringDashboard;
