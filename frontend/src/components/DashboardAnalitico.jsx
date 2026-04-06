import React, { useState, useEffect } from 'react';
import { useStats } from '../hooks/useStats';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line
} from 'recharts';
import { TrendingUp, Clock, AlertTriangle, FileText, Loader2 } from 'lucide-react';

const COLORS = {
  primary: '#f97316',
  secondary: '#fb923c',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  purple: '#a855f7',
  pink: '#ec4899'
};

const PIE_COLORS = [
  COLORS.primary,
  COLORS.secondary,
  COLORS.info,
  COLORS.success,
  COLORS.warning,
  COLORS.purple,
  COLORS.pink,
  COLORS.danger
];

export default function DashboardAnalitico() {
const { data, isLoading } = useStats();
const stats = data?.estadisticas || {};
const loading = isLoading;



  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center p-8">
        <p className="text-gray-500">No se pudieron cargar las estadísticas</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <TrendingUp className="w-8 h-8 text-primary" />
          Dashboard Analítico
        </h1>
        <p className="text-gray-600 mt-1">Visualización de métricas y tendencias</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <KPICard
          titulo="Documentos Este Mes"
          valor={stats.documentos_mes}
          icon={<FileText className="w-8 h-8" />}
          color="blue"
        />
        <KPICard
          titulo="Pendientes IA"
          valor={stats.pendientes_ia}
          icon={<Clock className="w-8 h-8" />}
          color="orange"
        />
        <KPICard
          titulo="Tareas Vencidas"
          valor={stats.tareas_vencidas}
          icon={<AlertTriangle className="w-8 h-8" />}
          color="red"
        />
        <KPICard
          titulo="Tiempo Promedio"
          valor={`${stats.tiempo_promedio}h`}
          icon={<Clock className="w-8 h-8" />}
          color="green"
        />
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Documentos por Departamento */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="font-bold text-lg mb-4 text-gray-900">Documentos por Departamento</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats.por_departamento}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="total" fill={COLORS.primary} radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribución por Estado */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="font-bold text-lg mb-4 text-gray-900">Distribución por Categoría</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stats.por_estado}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                labelLine={false}
              >
                {stats.por_estado.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Tendencia 7 días */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <h3 className="font-bold text-lg mb-4 text-gray-900">Tendencia Últimos 7 Días</h3>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={stats.tendencia_7_dias}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="fecha" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey="documentos" 
              stroke={COLORS.primary} 
              strokeWidth={3}
              dot={{ fill: COLORS.primary, r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function KPICard({ titulo, valor, icon, color = 'blue' }) {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-600',
    orange: 'bg-primary-light border-primary-light text-primary',
    red: 'bg-red-50 border-red-200 text-red-600',
    green: 'bg-green-50 border-green-200 text-green-600'
  };

  return (
    <div className={`${colorClasses[color]} border rounded-xl p-6 transition-transform hover:scale-105`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-75 mb-2">{titulo}</p>
          <p className="text-3xl font-bold">{valor}</p>
        </div>
        <div className="opacity-50">
          {icon}
        </div>
      </div>
    </div>
  );
}