#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Chat Module - Context Builder and Gemini Integration
Provides intelligent chat functionality using Gemini API
"""

import google.generativeai as genai
from models import Empresa, Documento, User, Conversacion, MensajeChat
from datetime import datetime, timedelta
from extensions import db
from tenant_utils import get_current_gestoria_id
from constants import DocumentCategories, TaskStates


def construir_contexto_sistema(usuario):
    """
    Construye contexto general del sistema para Gemini
    
    Args:
        usuario: User object del usuario actual
    
    Returns:
        str: Contexto formateado para Gemini
    """
    # Obtener gestoría actual
    gestoria_id = get_current_gestoria_id()
    
    # Estadísticas generales (FILTRADAS POR GESTORÍA)
    total_empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
    total_documentos = Documento.query.join(Empresa).filter(Empresa.gestoria_id == gestoria_id).count()
    
    # Documentos recientes (últimos 10) - FILTRADOS POR GESTORÍA
    docs_recientes = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == gestoria_id
    ).order_by(
        Documento.fecha_creacion.desc()
    ).limit(10).all()
    
    # Documentos por categoría - FILTRADOS POR GESTORÍA
    categorias = db.session.query(
        Documento.categoria,
        db.func.count(Documento.id).label('count')
    ).join(Empresa).filter(
        Empresa.gestoria_id == gestoria_id
    ).group_by(Documento.categoria).all()
    
    contexto = f"""Eres un asistente inteligente para IAGES, un sistema de gestión documental para gestorías.

INFORMACIÓN DEL SISTEMA:
- Total de empresas: {total_empresas}
- Total de documentos: {total_documentos}
- Usuario actual: {usuario.nombre} ({usuario.departamento.nombre if usuario.departamento else 'Sin departamento'})

NOTA: Tienes acceso a TODAS las {total_empresas} empresas del sistema. Cuando el usuario pregunte por una empresa específica (por nombre o NIF), buscaré la información completa de esa empresa.

DOCUMENTOS POR CATEGORÍA:
{chr(10).join([f"- {cat}: {count} documentos" for cat, count in categorias])}

DOCUMENTOS RECIENTES:
{chr(10).join([f"- {d.nombre_archivo} ({d.categoria}, {d.empresa.nombre if d.empresa else 'Sin empresa'})" for d in docs_recientes])}

CAPACIDADES Y ACCIONES QUE PUEDES REALIZAR:
1. **Crear Tareas**: Puedes programar tareas para usuarios específicos
   - Ejemplo: "Programa tarea reunion en sala de juntas para Usuario Prueba2"
   - Ejemplo: "Crea una tarea de revisión de documentos para Juan mañana a las 10am"
   - Puedes especificar: título, descripción, usuario asignado, fecha/hora, prioridad
   
2. **Consultar Información**: Buscar datos sobre empresas, documentos, estadísticas
3. **Analizar Importes**: Calcular totales a pagar de documentos
4. **Listar Documentos**: Mostrar documentos por empresa, categoría, fecha

INSTRUCCIONES:
- Responde en español de forma clara y concisa
- Si no tienes información suficiente, pídela al usuario
- Proporciona datos específicos cuando sea posible
- Usa formato markdown para listas y énfasis
- Sé profesional pero amigable
- Si te preguntan por estadísticas, usa los datos proporcionados
- **IMPORTANTE**: Cuando el usuario pida crear una tarea, programar algo, o asignar trabajo, CRÉALA DIRECTAMENTE sin pedir confirmación
- Si falta información CRÍTICA para crear una tarea (como el usuario asignado cuando se menciona "para [usuario]"), pregunta por ella UNA SOLA VEZ
- IMPORTANTE: Cuando busques una empresa, tendrás acceso a TODAS las empresas del sistema, no solo a un subconjunto
"""
    
    return contexto


def buscar_documentos_relevantes(pregunta, limit=5):
    """
    Busca documentos relevantes para la pregunta usando búsqueda mejorada
    
    Args:
        pregunta: str - Pregunta del usuario
        limit: int - Máximo de documentos a retornar
    
    Returns:
        list: Lista de objetos Documento relevantes
    """
    pregunta_lower = pregunta.lower()
    documentos_encontrados = set()
    
    # Diccionario de sinónimos para búsqueda semántica
    sinonimos = {
        'deuda': ['embargo', 'reclamación', 'reclamacion', 'impago', TaskStates.PENDIENTE, 'adeudo'],
        'seguro': ['cotización', 'cotizacion', 'ss', 'seguridad social', 'tesoreria'],
        'fiscal': ['hacienda', 'aeat', 'impuesto', 'tributario', 'iva', 'irpf'],
        'nomina': ['nómina', 'salario', 'sueldo', 'pago'],
        'notificacion': ['notificación', 'aviso', 'comunicación', 'comunicacion']
    }
    
    # Expandir términos de búsqueda con sinónimos
    terminos_busqueda = set(pregunta_lower.split())
    for palabra in list(terminos_busqueda):
        for termino_base, lista_sinonimos in sinonimos.items():
            if palabra in lista_sinonimos or palabra == termino_base:
                terminos_busqueda.update(lista_sinonimos)
                terminos_busqueda.add(termino_base)
    
    # Detectar búsqueda por categoría específica
    categorias_map = {
        'seguro': DocumentCategories.SEGUROS_SOCIALES,
        'seguros': DocumentCategories.SEGUROS_SOCIALES,
        'social': DocumentCategories.SEGUROS_SOCIALES,
        'sociales': DocumentCategories.SEGUROS_SOCIALES,
        'nomina': DocumentCategories.NOMINAS,
        'nómina': DocumentCategories.NOMINAS,
        'nominas': DocumentCategories.NOMINAS,
        'nóminas': DocumentCategories.NOMINAS,
        'notificacion': DocumentCategories.NOTIFICACIONES,
        'notificación': DocumentCategories.NOTIFICACIONES,
        'finiquito': 'Finiquitos',
        'fiscal': 'Documentos Fiscales'
    }
    
    # Obtener gestoría actual
    gestoria_id = get_current_gestoria_id()
    
    # Buscar por categoría - FILTRADO POR GESTORÍA
    for palabra_clave, categoria in categorias_map.items():
        if palabra_clave in pregunta_lower:
            docs = Documento.query.join(Empresa).filter(
                Empresa.gestoria_id == gestoria_id,
                Documento.categoria == categoria
            ).limit(limit * 2).all()
            documentos_encontrados.update(docs)
            break
    
    # Detectar búsqueda por empresa específica (NIF o nombre)
    # Buscar NIFs en la pregunta (formatos: B12345678, 12345678X, etc.)
    import re
    # Regex mejorado para capturar diferentes formatos de NIF/NIE/CIF
    nifs = re.findall(r'\b[A-Z]?\d{7,8}[A-Z]?\b', pregunta.upper())
    
    print(f"🔍 NIFs detectados en pregunta: {nifs}")
    
    if nifs:
        for nif in nifs:
            empresa = Empresa.query.filter_by(nif=nif, gestoria_id=get_current_gestoria_id()).first()
            if empresa:
                print(f"✅ Empresa encontrada por NIF {nif}: {empresa.nombre}")
                empresa_encontrada = empresa
                break
            else:
                print(f"❌ No se encontró empresa con NIF: {nif}")
    
    # Buscar por palabras clave en nombre de archivo - FILTRADO POR GESTORÍA
    # Usar términos expandidos con sinónimos
    for termino in terminos_busqueda:
        if len(termino) < 3:
            continue
            
        # Buscar en nombre de archivo
        docs = Documento.query.join(Empresa).filter(
            Empresa.gestoria_id == gestoria_id,
            Documento.nombre_archivo.ilike(f'%{termino}%')
        ).limit(limit).all()
        
        documentos_encontrados.update(docs)
        
        if len(documentos_encontrados) >= limit * 2:
            break
    
    return list(documentos_encontrados)[:limit * 2]


def buscar_empresas_relevantes(pregunta, limit=5):
    """
    Busca empresas relevantes para la pregunta
    
    Args:
        pregunta: str - Pregunta del usuario
        limit: int - Máximo de empresas a retornar
    
    Returns:
        list: Lista de objetos Empresa relevantes
    """
    palabras = pregunta.lower().split()
    
    empresas_encontradas = set()
    
    for palabra in palabras:
        if len(palabra) < 3:
            continue
            
        # Buscar en nombre y NIF
        empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
            db.or_(
                Empresa.nombre.ilike(f'%{palabra}%'),
                Empresa.nif.ilike(f'%{palabra}%')
            )
        ).limit(limit).all()
        
        empresas_encontradas.update(empresas)
        
        if len(empresas_encontradas) >= limit:
            break
    
    return list(empresas_encontradas)[:limit]


def generar_contexto_adicional(pregunta):
    """
    Genera contexto adicional basado en la pregunta
    
    Args:
        pregunta: str - Pregunta del usuario
    
    Returns:
        str: Contexto adicional relevante
    """
    from chat_actions import detectar_intencion_analizar_importes, analizar_importes_documentos
    
    contexto_adicional = []
    pregunta_lower = pregunta.lower()
    gestoria_id = get_current_gestoria_id()
    
    # 🆕 ANÁLISIS AUTOMÁTICO DE IMPORTES
    if detectar_intencion_analizar_importes(pregunta):
        print("💰 Detectada intención de analizar importes")
        analisis = analizar_importes_documentos(pregunta, gestoria_id)
        
        if analisis['count'] > 0:
            contexto_adicional.append("\n" + "="*60)
            contexto_adicional.append("💰 ANÁLISIS AUTOMÁTICO DE IMPORTES")
            contexto_adicional.append("="*60)
            contexto_adicional.append(f"\n📊 TOTAL A PAGAR: {analisis['total']:.2f}€")
            contexto_adicional.append(f"📄 Documentos analizados: {analisis['count']}")
            
            if analisis['categoria']:
                contexto_adicional.append(f"📁 Categoría: {analisis['categoria']}")
            if analisis['empresa']:
                contexto_adicional.append(f"🏢 Empresa: {analisis['empresa']}")
            
            contexto_adicional.append("\n📋 DESGLOSE POR DOCUMENTO:")
            for i, doc in enumerate(analisis['documentos'][:15], 1):
                fecha_str = doc.fecha_creacion.strftime('%d/%m/%Y') if doc.fecha_creacion else 'Sin fecha'
                empresa_str = doc.empresa.nombre if doc.empresa else 'Sin empresa'
                contexto_adicional.append(
                    f"{i}. {doc.nombre_archivo}\n   💶 {float(doc.importe_pagar):.2f}€ | 📅 {fecha_str} | 🏢 {empresa_str}"
                )
            
            if analisis['count'] > 15:
                contexto_adicional.append(f"\n... y {analisis['count'] - 15} documentos más")
            
            contexto_adicional.append("="*60 + "\n")
        else:
            contexto_adicional.append("\n⚠️ No se encontraron documentos con importes para los criterios especificados.\n")
    
    # Detectar búsqueda combinada: empresa + categoría
    import re
    nifs = re.findall(r'\b[A-Z]?\d{7,8}[A-Z]?\b', pregunta.upper())
    
    categorias_keywords = {
        'seguros sociales': ['seguro', 'seguros', 'social', 'sociales'],
        'nóminas': ['nomina', 'nómina', 'nominas', 'nóminas'],
        'notificaciones': ['notificacion', 'notificación'],
        'finiquitos': ['finiquito'],
        'documentos fiscales': ['fiscal']
    }
    
    # Detectar TODAS las categorías mencionadas
    categorias_detectadas = []
    for categoria, keywords in categorias_keywords.items():
        if any(kw in pregunta_lower for kw in keywords):
            categorias_detectadas.append(categoria.title())
    
    # Detectar si pide "todos los archivos" o "todos los documentos"
    pide_todos = any(palabra in pregunta_lower for palabra in [
        'todos los', 'dame los', 'archivos de', 'documentos de', 
        'qué documentos', 'qué archivos', 'cuáles son', 'listado',
        'dame el listado', 'muestra los', 'ver los', 'lista de'
    ])
    
    # Detectar si pregunta por importes/costos
    palabras_importe = ['cuánto', 'importe', 'pagar', 'costo', 'precio', 'monto', 'cantidad', 'total']
    pide_importe = any(palabra in pregunta_lower for palabra in palabras_importe)
    
    # Buscar empresa por NIF o por nombre
    empresa_encontrada = None
    
    # Primero intentar por NIF
    if nifs:
        for nif in nifs:
            empresa_encontrada = Empresa.query.filter_by(nif=nif, gestoria_id=get_current_gestoria_id()).first()
            if empresa_encontrada:
                break
    
    # Si no encontramos por NIF, buscar por nombre de empresa
    if not empresa_encontrada:
        # Buscar nombres de empresas en la pregunta
        empresas_todas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).all()
        
        # Primero: Buscar coincidencia exacta (ignorando mayúsculas)
        for empresa in empresas_todas:
            if empresa.nombre.lower() in pregunta_lower:
                empresa_encontrada = empresa
                break
        
        # Segundo: Si no hay coincidencia exacta, buscar por palabras clave significativas
        if not empresa_encontrada:
            from difflib import SequenceMatcher
            mejor_match = None
            mejor_ratio = 0
            
            for empresa in empresas_todas:
                # Calcular similitud entre el nombre de la empresa y la pregunta
                ratio = SequenceMatcher(None, empresa.nombre.lower(), pregunta_lower).ratio()
                
                # También verificar si las palabras principales de la empresa están en la pregunta
                palabras_empresa = [p for p in empresa.nombre.lower().split() if len(p) > 2]
                palabras_en_pregunta = sum(1 for p in palabras_empresa if p in pregunta_lower)
                ratio_palabras = palabras_en_pregunta / len(palabras_empresa) if palabras_empresa else 0
                
                # Combinar ambos ratios
                ratio_combinado = (ratio * 0.3) + (ratio_palabras * 0.7)
                
                if ratio_combinado > mejor_ratio:
                    mejor_ratio = ratio_combinado
                    mejor_match = empresa
            
            # Solo aceptar si la similitud es > 50%
            if mejor_ratio > 0.5:
                empresa_encontrada = mejor_match
    
    # Si encontramos empresa
    if empresa_encontrada:
        # Caso 1: Pide múltiples categorías O pide "todos los documentos"
        if len(categorias_detectadas) > 1 or (len(categorias_detectadas) == 0 and pide_todos):
            # Mostrar TODOS los documentos agrupados por categoría
            total_docs = Documento.query.filter_by(empresa_id=empresa_encontrada.id).count()
            contexto_adicional.append(f"\nEMPRESA: {empresa_encontrada.nombre} (NIF: {empresa_encontrada.nif})")
            contexto_adicional.append(f"Total de documentos: {total_docs}")
            
            if total_docs > 0:
                # Mostrar documentos por categoría CON NOMBRES DE ARCHIVO
                categorias_empresa = db.session.query(
                    Documento.categoria,
                    db.func.count(Documento.id).label('count')
                ).filter(
                    Documento.empresa_id == empresa_encontrada.id
                ).group_by(Documento.categoria).all()
                
                contexto_adicional.append("\nDocumentos por categoría:")
                for cat, count in categorias_empresa:
                    contexto_adicional.append(f"\n{cat}: {count} documentos")
                    
                    # Listar nombres de archivos de esta categoría
                    docs_categoria = Documento.query.filter(
                        Documento.empresa_id == empresa_encontrada.id,
                        Documento.categoria == cat
                    ).order_by(Documento.fecha_creacion.desc()).limit(10).all()
                    
                    for doc in docs_categoria:
                        from urllib.parse import quote
                        fecha_str = doc.fecha_creacion.strftime('%d/%m/%Y') if doc.fecha_creacion else 'Sin fecha'
                        
                        # Generar enlace clickeable para el documento
                        categoria_encoded = quote(doc.categoria)
                        doc_link = f"/empresa/{doc.empresa_id}/{categoria_encoded}?doc={doc.id}"
                        
                        # Mostrar importe si existe y se pregunta por costos
                        if pide_importe and doc.importe_pagar:
                            contexto_adicional.append(f"  - [{doc.nombre_archivo}]({doc_link}) ({fecha_str}) - {float(doc.importe_pagar):.2f}€")
                        else:
                            contexto_adicional.append(f"  - [{doc.nombre_archivo}]({doc_link}) ({fecha_str})")
                    
                    # Si hay más de 10, indicarlo
                    if count > 10:
                        contexto_adicional.append(f"  ... y {count - 10} documentos más")
        
        # Caso 2: Pide UNA categoría específica
        elif len(categorias_detectadas) == 1:
            categoria_detectada = categorias_detectadas[0]
            docs_empresa_categoria = Documento.query.filter(
                Documento.empresa_id == empresa_encontrada.id,
                Documento.categoria == categoria_detectada
            ).order_by(Documento.fecha_creacion.desc()).all()
            
            if docs_empresa_categoria:
                contexto_adicional.append(f"\nDOCUMENTOS DE {categoria_detectada.upper()} PARA {empresa_encontrada.nombre}:")
                contexto_adicional.append(f"Total: {len(docs_empresa_categoria)} documentos\n")
                
                # Calcular total de importes si se pregunta por costos
                if pide_importe:
                    docs_con_importe = [d for d in docs_empresa_categoria if d.importe_pagar]
                    if docs_con_importe:
                        total_importe = sum(float(d.importe_pagar) for d in docs_con_importe)
                        contexto_adicional.append(f"💰 TOTAL A PAGAR: {total_importe:.2f}€\n")
                
                # Listar nombres de archivos con fechas e importes
                for i, doc in enumerate(docs_empresa_categoria[:15], 1):
                    from urllib.parse import quote
                    fecha_str = doc.fecha_creacion.strftime('%d/%m/%Y') if doc.fecha_creacion else 'Sin fecha'
                    
                    # Generar enlace clickeable
                    categoria_encoded = quote(doc.categoria)
                    doc_link = f"/empresa/{doc.empresa_id}/{categoria_encoded}?doc={doc.id}"
                    
                    if pide_importe and doc.importe_pagar:
                        contexto_adicional.append(f"{i}. [{doc.nombre_archivo}]({doc_link}) ({fecha_str}) - {float(doc.importe_pagar):.2f}€")
                    else:
                        contexto_adicional.append(f"{i}. [{doc.nombre_archivo}]({doc_link}) ({fecha_str})")
                
                # Si hay más de 15, indicarlo
                if len(docs_empresa_categoria) > 15:
                    contexto_adicional.append(f"\n... y {len(docs_empresa_categoria) - 15} documentos más")
            else:
                contexto_adicional.append(
                    f"\n⚠️ No se encontraron documentos de {categoria_detectada} para {empresa_encontrada.nombre} (NIF: {empresa_encontrada.nif}) en la base de datos."
                )
                
                # Verificar si hay documentos de esa empresa con otras categorías
                total_docs_empresa = Documento.query.filter_by(empresa_id=empresa_encontrada.id).count()
                if total_docs_empresa > 0:
                    contexto_adicional.append(
                        f"Nota: Esta empresa tiene {total_docs_empresa} documentos en total, pero ninguno clasificado como '{categoria_detectada}'."
                    )
                    
                    # Mostrar qué categorías tiene
                    categorias_empresa = db.session.query(
                        Documento.categoria,
                        db.func.count(Documento.id).label('count')
                    ).filter(
                        Documento.empresa_id == empresa_encontrada.id
                    ).group_by(Documento.categoria).all()
                    
                    contexto_adicional.append("Categorías disponibles para esta empresa:")
                    for cat, count in categorias_empresa:
                        contexto_adicional.append(f"  - {cat}: {count} documentos")
                else:
                    contexto_adicional.append(
                        f"Nota: Esta empresa no tiene ningún documento registrado en la base de datos."
                    )
    
    # Detectar si pregunta por documentos (búsqueda general) - FILTRADO POR GESTORÍA
    elif any(palabra in pregunta_lower for palabra in ['documento', 'pdf', 'archivo', 'nómina', 'seguro']):
        docs = buscar_documentos_relevantes(pregunta, limit=20)
        if docs:
            contexto_adicional.append("\nDOCUMENTOS RELEVANTES:")
            for doc in docs:
                contexto_adicional.append(
                    f"- {doc.nombre_archivo} ({doc.categoria}, {doc.empresa.nombre if doc.empresa else 'Sin empresa'})"
                )
    
    # Detectar si pregunta por empresas (solo si NO encontramos empresa específica)
    if not empresa_encontrada and any(palabra in pregunta_lower for palabra in ['empresa', 'compañía', 'cliente', 'nif']):
        empresas = buscar_empresas_relevantes(pregunta, limit=10)
        if empresas:
            contexto_adicional.append("\nEMPRESAS RELEVANTES:")
            for emp in empresas:
                num_docs = Documento.query.filter_by(empresa_id=emp.id).count()
                contexto_adicional.append(
                    f"- {emp.nombre} (NIF: {emp.nif}, {num_docs} documentos)"
                )
    
    # Detectar si pregunta por estadísticas de tiempo - FILTRADO POR GESTORÍA
    if any(palabra in pregunta_lower for palabra in ['hoy', 'semana', 'mes', 'año']):
        gestoria_id = get_current_gestoria_id()
        hoy = datetime.now().date()
        
        if 'hoy' in pregunta_lower:
            docs_hoy = Documento.query.join(Empresa).filter(
                Empresa.gestoria_id == gestoria_id,
                db.func.date(Documento.fecha_creacion) == hoy
            ).count()
            contexto_adicional.append(f"\nDOCUMENTOS DE HOY: {docs_hoy}")
        
        if 'semana' in pregunta_lower:
            inicio_semana = hoy - timedelta(days=hoy.weekday())
            docs_semana = Documento.query.join(Empresa).filter(
                Empresa.gestoria_id == gestoria_id,
                Documento.fecha_creacion >= inicio_semana
            ).count()
            contexto_adicional.append(f"\nDOCUMENTOS ESTA SEMANA: {docs_semana}")
        
        if 'mes' in pregunta_lower:
            inicio_mes = hoy.replace(day=1)
            docs_mes = Documento.query.join(Empresa).filter(
                Empresa.gestoria_id == gestoria_id,
                Documento.fecha_creacion >= inicio_mes
            ).count()
            contexto_adicional.append(f"\nDOCUMENTOS ESTE MES: {docs_mes}")
    
    # Debug: Imprimir contexto generado
    contexto_final = "\n".join(contexto_adicional) if contexto_adicional else ""
    if contexto_final:
        print("\n" + "="*60)
        print("🔍 CONTEXTO GENERADO PARA GEMINI:")
        print("="*60)
        print(contexto_final)
        print("="*60 + "\n")
    
    return contexto_final
