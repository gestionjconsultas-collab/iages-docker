#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de Comandos Rápidos para Chat IA
========================================

Permite ejecutar comandos instantáneos sin llamar a Gemini API.

Comandos disponibles:
- /empresas - Lista todas las empresas
- /docs [empresa] - Documentos de una empresa
- /total [empresa] - Total a pagar de RLC
- /rlc [empresa] - Últimos RLC de una empresa
- /nominas [empresa] - Últimas nóminas de una empresa
- /fiscal [empresa] - Documentos fiscales de una empresa
- /stats - Estadísticas del sistema
- /help - Ayuda de comandos
"""

from models import Empresa, Documento, db
from sqlalchemy import func, or_
from models import Empresa, Documento, db
from tenant_utils import get_current_gestoria_id
from constants import DocumentCategories
from constants import DocumentCategories, NotificationTypes


def detectar_comando(texto: str) -> tuple:
    """
    Detecta si el texto es un comando
    
    Args:
        texto: Texto del usuario
    
    Returns:
        (es_comando, comando, argumentos)
    """
    texto = texto.strip()
    
    if not texto.startswith('/'):
        return (False, None, None)
    
    # Parsear comando
    partes = texto.split(maxsplit=1)
    comando = partes[0].lower()
    argumentos = partes[1].strip() if len(partes) > 1 else None
    
    return (True, comando, argumentos)


def ejecutar_comando(comando: str, argumentos: str = None, usuario_id: int = None) -> dict:
    """
    Ejecuta un comando y retorna la respuesta
    
    Args:
        comando: Comando a ejecutar (ej: /empresas)
        argumentos: Argumentos del comando
        usuario_id: ID del usuario (para stats)
    
    Returns:
        dict con 'respuesta' y NotificationTypes.SUCCESS
    """
    handlers = {
        '/empresas': cmd_empresas,
        '/docs': cmd_docs,
        '/total': cmd_total,
        '/rlc': cmd_rlc,
        '/nominas': cmd_nominas,
        '/fiscal': cmd_fiscal,
        '/stats': cmd_stats,
        '/help': cmd_help
    }
    
    handler = handlers.get(comando)
    
    if not handler:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ Comando desconocido: {comando}\n\nUsa /help para ver comandos disponibles"
        }
    
    try:
        # Pasar usuario_id solo a cmd_stats
        if comando == '/stats' and usuario_id:
            return handler(argumentos, usuario_id)
        else:
            return handler(argumentos)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ Error ejecutando comando: {str(e)}"
        }


def buscar_empresa_por_nombre(nombre: str) -> Empresa:
    """
    Busca empresa por nombre con similitud
    
    Args:
        nombre: Nombre o parte del nombre
    
    Returns:
        Empresa encontrada o None
    """
    nombre = nombre.lower().strip()
    
    # Buscar coincidencia exacta primero
    empresa = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
        Empresa.nombre.ilike(f'%{nombre}%')
    ).first()
    
    if empresa:
        return empresa
    
    # Si no hay coincidencia exacta, buscar por similitud
    empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).all()
    
    mejor_match = None
    mejor_score = 0
    
    for emp in empresas:
        score = SequenceMatcher(None, nombre, emp.nombre.lower()).ratio()
        if score > mejor_score and score > 0.6:  # 60% similitud mínima
            mejor_score = score
            mejor_match = emp
    
    return mejor_match


# ============================================================================
# HANDLERS DE COMANDOS
# ============================================================================

def cmd_empresas(args: str = None) -> dict:
    """Lista todas las empresas de la gestoría actual"""
    gestoria_id = get_current_gestoria_id()
    empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).order_by(Empresa.nombre).all()
    
    # Verificar si se solicita lista completa
    mostrar_todas = args and (args.lower() in ['all', '--all', 'todas', 'todo'])
    limite = None if mostrar_todas else 50
    
    if not empresas:
        return {NotificationTypes.SUCCESS: True, 'respuesta': "ℹ️ No tienes empresas registradas en tu gestoría."}

    respuesta = f"📋 EMPRESAS REGISTRADAS ({len(empresas)} total)\n\n"
    
    # Mostrar empresas según límite
    empresas_mostrar = empresas if mostrar_todas else empresas[:limite]
    
    for i, emp in enumerate(empresas_mostrar, 1):
        respuesta += f"{i}. {emp.nombre} ({emp.nif})\n"
    
    if not mostrar_todas and len(empresas) > limite:
        respuesta += f"\n... y {len(empresas) - limite} más\n"
        respuesta += f"\n💡 Usa /empresas all para ver la lista completa\n"
    
    respuesta += "\n💡 Usa /docs [empresa] para ver documentos de una empresa"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_docs(args: str = None) -> dict:
    """Lista documentos de una empresa de la gestoría actual"""
    if not args:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': "❌ Debes especificar una empresa\n\nEjemplo: /docs aeronna food"
        }
    
    # Buscar empresa (ya filtra por gestoria_id internamente)
    empresa = buscar_empresa_por_nombre(args)
    
    if not empresa:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ No se encontró empresa: {args}\n\nUsa /empresas para ver tus empresas"
        }
    
    # Obtener documentos por categoría (filtrando por gestoria_id para seguridad extra)
    gestoria_id = get_current_gestoria_id()
    docs = Documento.query.filter_by(
        empresa_id=empresa.id, 
        gestoria_id=gestoria_id
    ).order_by(
        Documento.fecha_procesado.desc()
    ).all()
    
    if not docs:
        return {
            NotificationTypes.SUCCESS: True,
            'respuesta': f"ℹ️ No hay documentos para {empresa.nombre}"
        }
    
    # Agrupar por categoría
    categorias = {}
    for doc in docs:
        cat = doc.categoria or 'Sin categoría'
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(doc)
    
    respuesta = f"📁 DOCUMENTOS DE {empresa.nombre.upper()}\n\n"
    
    for cat, docs_cat in sorted(categorias.items()):
        respuesta += f"{cat} ({len(docs_cat)}):\n"
        for doc in docs_cat[:5]:  # Máximo 5 por categoría
            fecha = doc.fecha_procesado.strftime('%d/%m/%Y') if doc.fecha_procesado else 'S/F'
            importe = f" - {float(doc.importe_pagar):,.2f}€" if doc.importe_pagar else ""
            respuesta += f"  • {doc.nombre_archivo} ({fecha}){importe}\n"
        
        if len(docs_cat) > 5:
            respuesta += f"  ... y {len(docs_cat) - 5} más\n"
        respuesta += "\n"
    
    respuesta += f"Total documentos: {len(docs)}"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_total(args: str = None) -> dict:
    """Muestra total a pagar de RLC de una empresa"""
    if not args:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': "❌ Debes especificar una empresa\n\nEjemplo: /total aeronna"
        }
    
    empresa = buscar_empresa_por_nombre(args)
    
    if not empresa:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ No se encontró empresa: {args}\n\nUsa /empresas para ver todas las empresas"
        }
    
    # Obtener RLC con importe (con filtro de gestoría para seguridad adicional)
    from models import Empresa
    rlcs = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        Documento.empresa_id == empresa.id,
        Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
        Documento.nombre_archivo.ilike('%RLC%'),
        Documento.importe_pagar.isnot(None)
    ).order_by(Documento.fecha_procesado.desc()).all()
    
    if not rlcs:
        return {
            NotificationTypes.SUCCESS: True,
            'respuesta': f"ℹ️ No hay RLC con importes para {empresa.nombre}"
        }
    
    total = sum(float(rlc.importe_pagar) for rlc in rlcs)
    
    respuesta = f"💰 TOTAL A PAGAR - {empresa.nombre.upper()}\n\n"
    
    for rlc in rlcs:
        fecha = rlc.fecha_procesado.strftime('%m/%Y') if rlc.fecha_procesado else 'S/F'
        respuesta += f"RLC {fecha}: {float(rlc.importe_pagar):,.2f}€\n"
    
    respuesta += f"\n{'='*40}\n"
    respuesta += f"TOTAL: {total:,.2f}€"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_rlc(args: str = None) -> dict:
    """Lista últimos RLC de una empresa"""
    if not args:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': "❌ Debes especificar una empresa\n\nEjemplo: /rlc aeronna"
        }
    
    empresa = buscar_empresa_por_nombre(args)
    
    if not empresa:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ No se encontró empresa: {args}\n\nUsa /empresas para ver todas las empresas"
        }
    
    # Obtener últimos RLC (con filtro de gestoría para seguridad adicional)
    from models import Empresa
    rlcs = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        Documento.empresa_id == empresa.id,
        Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
        Documento.nombre_archivo.ilike('%RLC%')
    ).order_by(Documento.fecha_procesado.desc()).limit(10).all()
    
    if not rlcs:
        return {
            NotificationTypes.SUCCESS: True,
            'respuesta': f"ℹ️ No hay RLC para {empresa.nombre}"
        }
    
    respuesta = f"📄 ÚLTIMOS RLC - {empresa.nombre.upper()}\n\n"
    
    total = 0
    for i, rlc in enumerate(rlcs, 1):
        fecha = rlc.fecha_procesado.strftime('%d/%m/%Y') if rlc.fecha_procesado else 'S/F'
        importe = ""
        if rlc.importe_pagar:
            importe = f" - {float(rlc.importe_pagar):,.2f}€"
            total += float(rlc.importe_pagar)
        
        respuesta += f"{i}. {rlc.nombre_archivo} ({fecha}){importe}\n"
    
    if total > 0:
        respuesta += f"\nTotal: {total:,.2f}€"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_nominas(args: str = None) -> dict:
    """Lista últimas nóminas de una empresa"""
    if not args:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': "❌ Debes especificar una empresa\n\nEjemplo: /nominas aeronna"
        }
    
    empresa = buscar_empresa_por_nombre(args)
    
    if not empresa:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ No se encontró empresa: {args}\n\nUsa /empresas para ver todas las empresas"
        }
    
    # Obtener últimas nóminas (con filtro de gestoría para seguridad adicional)
    from models import Empresa
    nominas = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        Documento.empresa_id == empresa.id,
        Documento.categoria == DocumentCategories.NOMINAS
    ).order_by(Documento.fecha_procesado.desc()).limit(10).all()
    
    if not nominas:
        return {
            NotificationTypes.SUCCESS: True,
            'respuesta': f"ℹ️ No hay nóminas para {empresa.nombre}"
        }
    
    respuesta = f"💼 ÚLTIMAS NÓMINAS - {empresa.nombre.upper()}\n\n"
    
    for i, nomina in enumerate(nominas, 1):
        fecha = nomina.fecha_procesado.strftime('%d/%m/%Y') if nomina.fecha_procesado else 'S/F'
        respuesta += f"{i}. {nomina.nombre_archivo} ({fecha})\n"
    
    respuesta += f"\nTotal nóminas: {len(nominas)}"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_fiscal(args: str = None) -> dict:
    """Lista documentos fiscales de una empresa"""
    if not args:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': "❌ Debes especificar una empresa\n\nEjemplo: /fiscal aeronna"
        }
    
    empresa = buscar_empresa_por_nombre(args)
    
    if not empresa:
        return {
            NotificationTypes.SUCCESS: False,
            'respuesta': f"❌ No se encontró empresa: {args}\n\nUsa /empresas para ver todas las empresas"
        }
    
    # Obtener documentos fiscales (con filtro de gestoría para seguridad adicional)
    from models import Empresa
    fiscales = Documento.query.join(Empresa).filter(
        Empresa.gestoria_id == get_current_gestoria_id(),
        Documento.empresa_id == empresa.id,
        Documento.categoria == DocumentCategories.FISCAL
    ).order_by(Documento.fecha_procesado.desc()).limit(10).all()
    
    if not fiscales:
        return {
            NotificationTypes.SUCCESS: True,
            'respuesta': f"ℹ️ No hay documentos fiscales para {empresa.nombre}"
        }
    
    respuesta = f"📋 DOCUMENTOS FISCALES - {empresa.nombre.upper()}\n\n"
    
    for i, doc in enumerate(fiscales, 1):
        fecha = doc.fecha_procesado.strftime('%d/%m/%Y') if doc.fecha_procesado else 'S/F'
        respuesta += f"{i}. {doc.nombre_archivo} ({fecha})\n"
    
    respuesta += f"\nTotal documentos fiscales: {len(fiscales)}"
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}


def cmd_stats(args: str = None, usuario_id: int = None) -> dict:
    """Estadísticas restringidas a la gestoría actual"""
    from chat_cache import obtener_estadisticas_cache
    from rate_limiter import RateLimiter
    
    gestoria_id = get_current_gestoria_id()
    
    # Estadísticas por gestoría
    total_empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
    total_docs = Documento.query.filter_by(gestoria_id=gestoria_id).count()
    
    # Por categoría (con filtro de gestoría)
    docs_seguros = Documento.query.filter_by(
        gestoria_id=gestoria_id, 
        categoria=DocumentCategories.SEGUROS_SOCIALES
    ).count()
    docs_nominas = Documento.query.filter_by(
        gestoria_id=gestoria_id, 
        categoria=DocumentCategories.NOMINAS
    ).count()
    docs_fiscales = Documento.query.filter_by(
        gestoria_id=gestoria_id, 
        categoria=DocumentCategories.FISCAL
    ).count()
    
    # Cache (estadísticas de uso de IA)
    try:
        cache_stats = obtener_estadisticas_cache()
    except:
        cache_stats = {'total_entradas': 0, 'hit_rate': 0, 'total_hits': 0}
    
    # Rate limit (solo si hay usuario_id)
    rate_info = ""
    if usuario_id:
        try:
            rate_limit = RateLimiter.check_limit(usuario_id, 20, 1)
            minutos = rate_limit['reset_en_segundos'] // 60
            rate_info = f"""
Rate limiting:
- Preguntas restantes: {rate_limit['requests_restantes']}/20
- Reset en: {minutos} minutos
"""
        except:
            pass
    
    respuesta = f"""📊 ESTADÍSTICAS DE TU GESTORÍA
 
Empresas: {total_empresas}
Documentos totales: {total_docs}
  • Seguros Sociales: {docs_seguros}
  • Nóminas: {docs_nominas}
  • Fiscales: {docs_fiscales}

Caché de respuestas:
  • Entradas: {cache_stats['total_entradas']}
  • Hit rate: {cache_stats['hit_rate']:.1f}%
  • Total hits: {cache_stats['total_hits']}
{rate_info}"""
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta.strip()}


def cmd_help(args: str = None) -> dict:
    """Ayuda de comandos"""
    respuesta = """🤖 COMANDOS DISPONIBLES

/empresas [all]
  Lista todas las empresas registradas
  Usa 'all' para ver la lista completa
  Ejemplo: /empresas all

/docs [empresa]
  Muestra documentos de una empresa
  Ejemplo: /docs aeronna food

/total [empresa]
  Total a pagar de RLC de una empresa
  Ejemplo: /total aeronna

/rlc [empresa]
  Últimos RLC de una empresa
  Ejemplo: /rlc aeronna

/nominas [empresa]
  Últimas nóminas de una empresa
  Ejemplo: /nominas aeronna

/fiscal [empresa]
  Documentos fiscales de una empresa
  Ejemplo: /fiscal aeronna

/stats
  Estadísticas del sistema

/help
  Esta ayuda

💡 También puedes hacer preguntas en lenguaje natural
"""
    
    return {NotificationTypes.SUCCESS: True, 'respuesta': respuesta}
