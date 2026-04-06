#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chat Analytics - Funciones analíticas para el chat IA
Permite al chat responder preguntas complejas con consultas SQL
"""

from models import Empresa, Documento, db
from sqlalchemy import func, and_, or_, not_
from tenant_utils import get_current_gestoria_id
from constants import DocumentCategories
from constants import DocumentCategories, TaskStates


def obtener_empresas_sin_categorias(categorias, gestoria_id=None):
    """
    Obtiene empresas que NO tienen documentos de ciertas categorías
    
    Args:
        categorias: list - Lista de categorías a verificar (ej: [DocumentCategories.NOMINAS, DocumentCategories.SEGUROS_SOCIALES])
        gestoria_id: int - ID de gestoría (opcional, usa actual si no se especifica)
    
    Returns:
        list: Lista de empresas sin esas categorías
    """
    if gestoria_id is None:
        gestoria_id = get_current_gestoria_id()
    
    # Obtener todas las empresas de la gestoría
    todas_empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
    
    empresas_sin_categorias = []
    
    for empresa in todas_empresas:
        # Verificar si tiene documentos de alguna de las categorías
        tiene_categoria = Documento.query.filter(
            Documento.empresa_id == empresa.id,
            Documento.categoria.in_(categorias)
        ).first()
        
        if not tiene_categoria:
            empresas_sin_categorias.append(empresa)
    
    return empresas_sin_categorias


def obtener_empresas_con_documentos_pendientes(gestoria_id=None):
    """
    Obtiene empresas con documentos en DocumentCategories.POR_PROCESAR
    
    Args:
        gestoria_id: int - ID de gestoría
    
    Returns:
        list: Lista de tuplas (empresa, count)
    """
    if gestoria_id is None:
        gestoria_id = get_current_gestoria_id()
    
    resultados = db.session.query(
        Empresa,
        func.count(Documento.id).label('count')
    ).join(Documento).filter(
        Empresa.gestoria_id == gestoria_id,
        Documento.categoria == DocumentCategories.POR_PROCESAR
    ).group_by(Empresa.id).all()
    
    return resultados


def obtener_empresas_sin_documentos(gestoria_id=None):
    """
    Obtiene empresas que no tienen ningún documento
    
    Args:
        gestoria_id: int - ID de gestoría
    
    Returns:
        list: Lista de empresas sin documentos
    """
    if gestoria_id is None:
        gestoria_id = get_current_gestoria_id()
    
    # Subquery de empresas con documentos
    empresas_con_docs = db.session.query(
        Documento.empresa_id
    ).distinct().subquery()
    
    # Empresas sin documentos
    empresas_sin_docs = Empresa.query.filter(
        Empresa.gestoria_id == gestoria_id,
        ~Empresa.id.in_(db.session.query(empresas_con_docs))
    ).all()
    
    return empresas_sin_docs


def obtener_estadisticas_por_categoria(gestoria_id=None):
    """
    Obtiene estadísticas de documentos por categoría
    
    Args:
        gestoria_id: int - ID de gestoría
    
    Returns:
        dict: Estadísticas por categoría
    """
    if gestoria_id is None:
        gestoria_id = get_current_gestoria_id()
    
    categorias = db.session.query(
        Documento.categoria,
        func.count(Documento.id).label('count'),
        func.count(func.distinct(Documento.empresa_id)).label('empresas_count')
    ).join(Empresa).filter(
        Empresa.gestoria_id == gestoria_id
    ).group_by(Documento.categoria).all()
    
    return {
        cat: {'total_docs': count, 'total_empresas': emp_count}
        for cat, count, emp_count in categorias
    }


def detectar_consulta_analitica(pregunta):
    """
    Detecta si la pregunta requiere análisis de datos
    
    Args:
        pregunta: str - Pregunta del usuario
    
    Returns:
        dict o None: Tipo de análisis y parámetros
    """
    pregunta_lower = pregunta.lower()
    
    # Patrón: empresas sin X categoría (múltiples variaciones)
    patrones_sin_categorias = [
        'sin nomina', 'sin nómina', 'sin seguro', 
        'no tienen nomina', 'no tienen nómina', 'no tienen seguro',
        'no les he subido nomina', 'no les he subido nómina', 'no les he subido seguro',
        'falta nomina', 'falta nómina', 'falta seguro',
        'no hay nomina', 'no hay nómina', 'no hay seguro'
    ]
    
    if any(patron in pregunta_lower for patron in patrones_sin_categorias):
        categorias = []
        if 'nomina' in pregunta_lower or 'nómina' in pregunta_lower:
            categorias.append(DocumentCategories.NOMINAS)
        if 'seguro' in pregunta_lower or 'ss' in pregunta_lower or 'social' in pregunta_lower:
            categorias.append(DocumentCategories.SEGUROS_SOCIALES)
        
        print(f"📊 Detectada consulta analítica: empresas_sin_categorias - {categorias}")
        
        return {
            'tipo': 'empresas_sin_categorias',
            'categorias': categorias
        }
    
    # Patrón: empresas sin documentos
    if 'sin documento' in pregunta_lower or 'sin archivos' in pregunta_lower:
        print(f"📊 Detectada consulta analítica: empresas_sin_documentos")
        return {
            'tipo': 'empresas_sin_documentos'
        }
    
    # Patrón: empresas con pendientes
    if TaskStates.PENDIENTE in pregunta_lower and 'empresa' in pregunta_lower:
        print(f"📊 Detectada consulta analítica: empresas_con_pendientes")
        return {
            'tipo': 'empresas_con_pendientes'
        }
    
    return None


def ejecutar_consulta_analitica(tipo_analisis, parametros):
    """
    Ejecuta la consulta analítica y formatea el resultado
    
    Args:
        tipo_analisis: str - Tipo de análisis
        parametros: dict - Parámetros del análisis
    
    Returns:
        str: Resultado formateado
    """
    gestoria_id = get_current_gestoria_id()
    
    if tipo_analisis == 'empresas_sin_categorias':
        categorias = parametros.get('categorias', [])
        empresas = obtener_empresas_sin_categorias(categorias, gestoria_id)
        
        if not empresas:
            return f"✅ Todas las empresas tienen documentos de {' y '.join(categorias)}."
        
        resultado = f"📋 **Empresas sin {' ni '.join(categorias)}** ({len(empresas)} empresas):\n\n"
        for emp in empresas[:50]:  # Limitar a 50 para no sobrecargar
            resultado += f"- {emp.nombre} (NIF: {emp.nif})\n"
        
        if len(empresas) > 50:
            resultado += f"\n... y {len(empresas) - 50} empresas más.\n"
        
        return resultado
    
    elif tipo_analisis == 'empresas_sin_documentos':
        empresas = obtener_empresas_sin_documentos(gestoria_id)
        
        if not empresas:
            return "✅ Todas las empresas tienen al menos un documento."
        
        resultado = f"📋 **Empresas sin documentos** ({len(empresas)} empresas):\n\n"
        for emp in empresas:
            resultado += f"- {emp.nombre} (NIF: {emp.nif})\n"
        
        return resultado
    
    elif tipo_analisis == 'empresas_con_pendientes':
        resultados = obtener_empresas_con_documentos_pendientes(gestoria_id)
        
        if not resultados:
            return "✅ No hay empresas con documentos pendientes de procesar."
        
        resultado = f"📋 **Empresas con documentos pendientes** ({len(resultados)} empresas):\n\n"
        for emp, count in resultados:
            resultado += f"- {emp.nombre}: {count} documento{'s' if count > 1 else ''} pendiente{'s' if count > 1 else ''}\n"
        
        return resultado
    
    return None
