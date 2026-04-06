import React from 'react';
import { FileText, User, Briefcase, LogOut, Clock } from 'lucide-react';

export default function Dashboard({ empleado, onLogout }) {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navbar */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
              <span className="text-white text-sm font-bold">P</span>
            </div>
            <span className="font-semibold text-gray-900">Portal del Empleado</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600 hidden sm:block">{empleado?.nombre}</span>
            <button
              onClick={onLogout}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-600 transition"
            >
              <LogOut className="w-4 h-4" />
              Salir
            </button>
          </div>
        </div>
      </header>

      {/* Contenido */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Bienvenida */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-2xl p-6 mb-8 text-white shadow-lg">
          <h2 className="text-2xl font-bold">
            Bienvenido, {empleado?.nombre?.split(' ')[0]} 👋
          </h2>
          <p className="text-blue-200 mt-1">{empleado?.empresa}</p>
        </div>

        {/* Módulos (placeholders para Fase 2+) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <ModuleCard
            icon={<FileText className="w-6 h-6" />}
            title="Mis Nóminas"
            description="Consulta y descarga tus nóminas mensuales"
            color="blue"
            comingSoon
          />
          <ModuleCard
            icon={<Briefcase className="w-6 h-6" />}
            title="Mis Contratos"
            description="Accede a tus contratos laborales"
            color="green"
            comingSoon
          />
          <ModuleCard
            icon={<User className="w-6 h-6" />}
            title="Mis Datos"
            description="Consulta tu información laboral"
            color="purple"
            comingSoon
          />
          <ModuleCard
            icon={<Clock className="w-6 h-6" />}
            title="Mi Finiquito"
            description="Revisa el detalle de tu liquidación"
            color="orange"
            comingSoon
          />
        </div>

        {/* Info empleado */}
        <div className="mt-8 bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Mis datos</h3>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Nombre</dt>
              <dd className="font-medium text-gray-900">{empleado?.nombre || '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">NIF</dt>
              <dd className="font-medium text-gray-900">{empleado?.nif || '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Empresa</dt>
              <dd className="font-medium text-gray-900">{empleado?.empresa || '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500">NSS</dt>
              <dd className="font-medium text-gray-900">{empleado?.nss || '—'}</dd>
            </div>
          </dl>
        </div>
      </main>
    </div>
  );
}

function ModuleCard({ icon, title, description, color, comingSoon }) {
  const colors = {
    blue:   'bg-blue-50 text-blue-600 border-blue-100',
    green:  'bg-green-50 text-green-600 border-green-100',
    purple: 'bg-purple-50 text-purple-600 border-purple-100',
    orange: 'bg-orange-50 text-orange-600 border-orange-100',
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition relative overflow-hidden">
      <div className={`inline-flex p-2.5 rounded-xl border ${colors[color]} mb-3`}>
        {icon}
      </div>
      <h4 className="font-semibold text-gray-900">{title}</h4>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
      {comingSoon && (
        <span className="absolute top-3 right-3 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
          Próximamente
        </span>
      )}
    </div>
  );
}
