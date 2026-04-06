#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de Caché para Respuestas del Chat IA
============================================

Reduce llamadas a Gemini API cacheando respuestas basadas en hash de pregunta + contexto.

Funciones principales:
- generar_cache_key(): Genera hash único para pregunta + contexto
- obtener_respuesta_cache(): Busca respuesta en cache
- guardar_respuesta_cache(): Guarda respuesta en cache
- limpiar_cache_expirado(): Elimina entradas vencidas
- obtener_estadisticas_cache(): Métricas de uso del cache
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from models import db, RespuestaCache


def generar_cache_key(pregunta: str, contexto: str = "") -> str:
    """
    Genera hash SHA256 único para pregunta + contexto
    
    Args:
        pregunta: Pregunta del usuario
        contexto: Contexto adicional generado
    
    Returns:
        str: Hash SHA256 de 64 caracteres
    """
    # Normalizar pregunta (lowercase, strip)
    pregunta_norm = pregunta.lower().strip()
    
    # Combinar pregunta + contexto
    contenido = f"{pregunta_norm}|{contexto}"
    
    # Generar hash
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def obtener_respuesta_cache(pregunta: str, contexto: str = "") -> Optional[Dict]:
    """
    Busca respuesta en cache
    
    Args:
        pregunta: Pregunta del usuario
        contexto: Contexto adicional
    
    Returns:
        dict con respuesta y metadata si existe, None si no
    """
    cache_key = generar_cache_key(pregunta, contexto)
    
    # Buscar en BD
    cache = RespuestaCache.query.filter_by(cache_key=cache_key).first()
    
    if not cache:
        return None
    
    # Verificar si expiró
    if cache.ttl_expiracion and datetime.utcnow() > cache.ttl_expiracion:
        print(f"⏰ Cache expirado para: {pregunta[:50]}...")
        return None
    
    # Actualizar estadísticas
    cache.hits += 1
    cache.fecha_ultimo_uso = datetime.utcnow()
    db.session.commit()
    
    print(f"✅ Respuesta obtenida de cache (hits: {cache.hits})")
    
    return {
        'respuesta': cache.respuesta,
        'hits': cache.hits,
        'cacheado': True,
        'fecha_creacion': cache.fecha_creacion
    }


def guardar_respuesta_cache(
    pregunta: str,
    respuesta: str,
    contexto: str = "",
    ttl_horas: int = 24
) -> None:
    """
    Guarda respuesta en cache
    
    Args:
        pregunta: Pregunta del usuario
        respuesta: Respuesta de Gemini
        contexto: Contexto adicional
        ttl_horas: Tiempo de vida en horas (default: 24)
    """
    cache_key = generar_cache_key(pregunta, contexto)
    contexto_hash = hashlib.sha256(contexto.encode('utf-8')).hexdigest()
    
    # Verificar si ya existe
    cache = RespuestaCache.query.filter_by(cache_key=cache_key).first()
    
    if cache:
        # Actualizar existente
        cache.respuesta = respuesta
        cache.ttl_expiracion = datetime.utcnow() + timedelta(hours=ttl_horas)
        cache.fecha_ultimo_uso = datetime.utcnow()
        print(f"🔄 Cache actualizado para: {pregunta[:50]}...")
    else:
        # Crear nuevo
        cache = RespuestaCache(
            cache_key=cache_key,
            pregunta=pregunta,
            respuesta=respuesta,
            contexto_hash=contexto_hash,
            ttl_expiracion=datetime.utcnow() + timedelta(hours=ttl_horas)
        )
        db.session.add(cache)
        print(f"💾 Nueva respuesta cacheada: {pregunta[:50]}...")
    
    db.session.commit()


def limpiar_cache_expirado() -> int:
    """
    Elimina entradas de cache expiradas
    
    Returns:
        int: Número de entradas eliminadas
    """
    ahora = datetime.utcnow()
    
    # Buscar entradas expiradas
    expirados = RespuestaCache.query.filter(
        RespuestaCache.ttl_expiracion < ahora
    ).all()
    
    count = len(expirados)
    
    for cache in expirados:
        db.session.delete(cache)
    
    db.session.commit()
    
    if count > 0:
        print(f"🗑️ {count} entradas de cache expiradas eliminadas")
    
    return count


def limpiar_cache_completo() -> int:
    """
    Elimina todas las entradas de cache
    
    Returns:
        int: Número de entradas eliminadas
    """
    count = RespuestaCache.query.count()
    
    RespuestaCache.query.delete()
    db.session.commit()
    
    print(f"🗑️ Cache completo limpiado ({count} entradas)")
    
    return count


def obtener_estadisticas_cache() -> Dict:
    """
    Obtiene estadísticas del cache
    
    Returns:
        dict: Estadísticas de uso del cache
    """
    total = RespuestaCache.query.count()
    
    # Total de hits
    total_hits = db.session.query(
        db.func.sum(RespuestaCache.hits)
    ).scalar() or 0
    
    # Top 10 más usadas
    top_hits = RespuestaCache.query.order_by(
        RespuestaCache.hits.desc()
    ).limit(10).all()
    
    # Entradas expiradas
    ahora = datetime.utcnow()
    expirados = RespuestaCache.query.filter(
        RespuestaCache.ttl_expiracion < ahora
    ).count()
    
    return {
        'total_entradas': total,
        'total_hits': total_hits,
        'entradas_expiradas': expirados,
        'hit_rate': (total_hits / total * 100) if total > 0 else 0,
        'top_preguntas': [
            {
                'pregunta': c.pregunta,
                'hits': c.hits,
                'fecha_creacion': c.fecha_creacion.isoformat() if c.fecha_creacion else None
            }
            for c in top_hits
        ]
    }


def mantener_limite_cache(limite: int = 1000) -> int:
    """
    Mantiene el cache bajo un límite eliminando las menos usadas
    
    Args:
        limite: Número máximo de entradas permitidas
    
    Returns:
        int: Número de entradas eliminadas
    """
    total = RespuestaCache.query.count()
    
    if total <= limite:
        return 0
    
    # Calcular cuántas eliminar
    a_eliminar = total - limite
    
    # Obtener las menos usadas
    menos_usadas = RespuestaCache.query.order_by(
        RespuestaCache.hits.asc(),
        RespuestaCache.fecha_ultimo_uso.asc()
    ).limit(a_eliminar).all()
    
    for cache in menos_usadas:
        db.session.delete(cache)
    
    db.session.commit()
    
    print(f"🗑️ {a_eliminar} entradas menos usadas eliminadas (límite: {limite})")
    
    return a_eliminar
