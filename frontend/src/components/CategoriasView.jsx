// frontend/src/components/CategoriasView.jsx
import React, { useState } from 'react';
import { useEmpresa } from '../hooks/useEmpresa';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, Folder, FileText, Briefcase, Building, FileBarChart, Bell, Loader2, Shield, Users, FileCheck, DollarSign, Package, UserPlus, UserMinus, FileX, Activity } from 'lucide-react';
import axios from 'axios';
import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

const categorias = [
  { nombre: "Notificaciones", icono: Bell, color: "from-red-500 to-pink-500", bgColor: "bg-red-50", textColor: "text-red-600", link: "Notificaciones", descripcion: "Documentos oficiales recibidos" },
  { nombre: "Inspecciones", icono: Shield, color: "from-yellow-500 to-orange-500", bgColor: "bg-yellow-50", textColor: "text-yellow-600", link: "Inspecciones", descripcion: "Informes de inspecciones" },
  { nombre: "Aplazamiento", icono: FileBarChart, color: "from-blue-500 to-cyan-500", bgColor: "bg-blue-50", textColor: "text-blue-600", link: "Aplazamiento", descripcion: "Solicitudes de aplazamiento" },
  { nombre: "Nóminas", icono: DollarSign, color: "from-green-500 to-emerald-500", bgColor: "bg-green-50", textColor: "text-green-600", link: "Nóminas", descripcion: "Nóminas de empleados" },
  { nombre: "Altas de Trabajadores", icono: UserPlus, color: "from-emerald-500 to-teal-500", bgColor: "bg-emerald-50", textColor: "text-emerald-600", link: "Altas de Trabajadores", descripcion: "Altas a la SS" },
  { nombre: "Bajas de Trabajadores", icono: UserMinus, color: "from-orange-500 to-red-500", bgColor: "bg-orange-50", textColor: "text-orange-600", link: "Bajas de Trabajadores", descripcion: "Bajas a la SS" },
  { nombre: "Cartas de Despidos", icono: FileX, color: "from-rose-500 to-pink-500", bgColor: "bg-rose-50", textColor: "text-rose-600", link: "Cartas de Despidos", descripcion: "Despidos" },
  { nombre: "Finiquitos", icono: Package, color: "from-rose-600 to-red-600", bgColor: "bg-rose-50", textColor: "text-rose-700", link: "Finiquitos", descripcion: "Documentos de finiquito" },
  { nombre: "Impuestos", icono: FileText, color: "from-purple-500 to-violet-500", bgColor: "bg-purple-50", textColor: "text-purple-600", link: "Impuestos", descripcion: "Declaraciones fiscales" },
  { nombre: "Seguros Sociales", icono: Users, color: "from-teal-500 to-cyan-500", bgColor: "bg-teal-50", textColor: "text-teal-600", link: "Seguros Sociales", descripcion: "Documentos de SS" },
  { nombre: "Contratos Trabajo", icono: FileCheck, color: "from-indigo-500 to-blue-500", bgColor: "bg-indigo-50", textColor: "text-indigo-600", link: "Contratos", descripcion: "Contratos laborales" },
  { nombre: "Accidentes de Trabajo", icono: Activity, color: "from-pink-500 to-rose-600", bgColor: "bg-pink-50", textColor: "text-pink-600", link: "Accidentes de Trabajo", descripcion: "Accidentes Laborales", disabled: true },
  { nombre: "Certificados de Retenciones 180", icono: FileText, color: "from-amber-500 to-yellow-500", bgColor: "bg-amber-50", textColor: "text-amber-600", link: "Certificados de Retenciones 180", descripcion: "Certificados Mod 180" },
  { nombre: "Certificados de Retenciones 190", icono: FileText, color: "from-amber-600 to-yellow-600", bgColor: "bg-amber-100", textColor: "text-amber-700", link: "Certificados de Retenciones 190", descripcion: "Certificados Mod 190" },
  { nombre: "Documentos Empresa", icono: Building, color: "from-gray-500 to-slate-500", bgColor: "bg-gray-50", textColor: "text-gray-600", link: "Documentos Empresa", descripcion: "Documentación general" },
  { nombre: "Por Procesar", icono: Folder, color: "from-gray-700 to-gray-900", bgColor: "bg-gray-100", textColor: "text-gray-800", link: "Por Procesar", descripcion: "Bandeja de entrada" },
];

export default function CategoriasView() {
  const { empresaId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data, isLoading: loading, refetch } = useEmpresa(empresaId);
  const empresa = data?.empresa || null;
  const conteos = data?.conteos || {};

  // ✅ FORZAR REFRESCO AL ENTRAR (Defensivo contra cache persistente)
  useEffect(() => {
    if (empresaId) {
      // Invalidador redundante para asegurar datos frescos
      queryClient.invalidateQueries({ queryKey: ['empresa', String(empresaId)] });
      refetch();
    }
  }, [empresaId]);

  const totalDocumentos = Object.values(conteos).reduce((acc, val) => acc + val, 0);

  if (loading) return <div className="flex justify-center h-96 items-center"><Loader2 className="w-12 h-12 animate-spin text-primary" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/empresas')} className="p-2 hover:bg-gray-100 rounded-lg"><ChevronLeft className="w-5 h-5 text-gray-600" /></button>
        <div><h1 className="text-3xl font-bold text-gray-900">{empresa?.nombre}</h1><div className="flex gap-3 mt-1"><p className="text-gray-600">{empresa?.nif}</p>{totalDocumentos > 0 && <span className="px-2 py-1 bg-primary-light text-primary-hover text-xs font-bold rounded-full">{totalDocumentos} docs</span>}</div></div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {categorias.map(cat => {
          const count = conteos[cat.link] || 0;
          return (
            <div key={cat.nombre} onClick={() => !cat.disabled && navigate(`/empresa/${empresaId}/${cat.link}`)} className={`bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-lg transition-all group relative overflow-hidden ${cat.disabled ? 'cursor-not-allowed opacity-75' : 'cursor-pointer'}`}>
              <div className="flex justify-between mb-4"><div className={`p-3 bg-linear-to-br ${cat.color} rounded-xl shadow-md group-hover:scale-110 transition-transform`}><cat.icono className="w-6 h-6 text-white" /></div>{count > 0 && <div className={`px-3 py-1 bg-linear-to-r ${cat.color} text-white text-sm font-bold rounded-full`}>{count}</div>}</div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">{cat.nombre}</h3>
              <p className="text-sm text-gray-500 mb-3">{cat.descripcion}</p>
              <div className="pt-3 border-t border-gray-100"><p className={`text-sm font-medium ${count > 0 ? cat.textColor : 'text-gray-400'}`}>{count === 0 ? 'Vacío' : `${count} archivo${count !== 1 ? 's' : ''}`}</p></div>
              {cat.disabled && <div className="absolute top-3 right-3 px-2 py-1 bg-gray-200 text-gray-600 text-[10px] font-bold uppercase rounded-full">Próximamente</div>}
            </div>
          );
        })}
      </div>
    </div>
  );
}