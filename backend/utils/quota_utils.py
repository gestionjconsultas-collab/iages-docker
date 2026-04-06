#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilidades para gestión de límites y cuotas por gestoría
"""

import os
from models import Gestoria, Empresa, User, Documento, db
from utils.storage_utils import get_gestoria_storage_path


def get_gestoria_storage_size(gestoria_id):
    """
    Calcula el tamaño total de almacenamiento usado por una gestoría
    
    Args:
        gestoria_id (int): ID de la gestoría
    
    Returns:
        int: Tamaño en bytes
    """
    gestoria_path = get_gestoria_storage_path(gestoria_id)
    
    if not os.path.exists(gestoria_path):
        return 0
    
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(gestoria_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    
    return total_size


def get_gestoria_usage(gestoria_id):
    """
    Obtiene el uso actual de recursos de una gestoría
    
    Args:
        gestoria_id (int): ID de la gestoría
    
    Returns:
        dict: Uso actual de recursos
    """
    gestoria = db.session.get(Gestoria, gestoria_id)
    if not gestoria:
        return None
    
    # Contar recursos
    empresas_count = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
    usuarios_count = User.query.filter_by(gestoria_id=gestoria_id).count()
    storage_bytes = get_gestoria_storage_size(gestoria_id)
    storage_gb = storage_bytes / (1024 ** 3)
    
    return {
        'empresas': {
            'usado': empresas_count,
            'limite': gestoria.max_empresas,
            'porcentaje': round((empresas_count / gestoria.max_empresas * 100), 2) if gestoria.max_empresas > 0 else 0
        },
        'usuarios': {
            'usado': usuarios_count,
            'limite': gestoria.max_usuarios,
            'porcentaje': round((usuarios_count / gestoria.max_usuarios * 100), 2) if gestoria.max_usuarios > 0 else 0
        },
        'storage': {
            'usado_gb': round(storage_gb, 2),
            'limite_gb': gestoria.max_storage_gb,
            'porcentaje': round((storage_gb / gestoria.max_storage_gb * 100), 2) if gestoria.max_storage_gb > 0 else 0
        }
    }


def validate_gestoria_limit(gestoria_id, resource_type, additional_count=1):
    """
    Valida si se puede crear un nuevo recurso sin exceder límites
    
    Args:
        gestoria_id (int): ID de la gestoría
        resource_type (str): Tipo de recurso ('empresas', 'usuarios', 'storage')
        additional_count (int|float): Cantidad a agregar (1 para empresas/usuarios, bytes para storage)
    
    Returns:
        tuple: (bool, str) - (puede_crear, mensaje_error)
    """
    gestoria = db.session.get(Gestoria, gestoria_id)
    if not gestoria:
        return False, "Gestoría no encontrada"
    
    if resource_type == 'empresas':
        current_count = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
        if current_count + additional_count > gestoria.max_empresas:
            return False, f"Límite de empresas alcanzado ({gestoria.max_empresas} máximo). Contacta a soporte para ampliar tu plan."
    
    elif resource_type == 'usuarios':
        current_count = User.query.filter_by(gestoria_id=gestoria_id).count()
        if current_count + additional_count > gestoria.max_usuarios:
            return False, f"Límite de usuarios alcanzado ({gestoria.max_usuarios} máximo). Contacta a soporte para ampliar tu plan."
    
    elif resource_type == 'storage':
        current_bytes = get_gestoria_storage_size(gestoria_id)
        current_gb = current_bytes / (1024 ** 3)
        additional_gb = additional_count / (1024 ** 3)
        
        if current_gb + additional_gb > gestoria.max_storage_gb:
            return False, f"Límite de almacenamiento alcanzado ({gestoria.max_storage_gb}GB máximo). Usado: {current_gb:.2f}GB. Contacta a soporte para ampliar tu plan."
    
    else:
        return False, f"Tipo de recurso desconocido: {resource_type}"
    
    return True, ""


def check_approaching_limit(gestoria_id, resource_type, threshold=80):
    """
    Verifica si un recurso está cerca de alcanzar su límite
    
    Args:
        gestoria_id (int): ID de la gestoría
        resource_type (str): Tipo de recurso
        threshold (int): Porcentaje de umbral (default 80%)
    
    Returns:
        bool: True si está cerca del límite
    """
    usage = get_gestoria_usage(gestoria_id)
    if not usage:
        return False
    
    if resource_type in usage:
        return usage[resource_type]['porcentaje'] >= threshold
    
    return False


def validate_ai_usage(gestoria_id):
    """Valida si la gestoría puede hacer más requests de IA"""
    from datetime import date
    from models import Gestoria, ApiKeyUsage, db
    from sqlalchemy import func
    
    gestoria = Gestoria.query.get(gestoria_id)
    if not gestoria:
        return False, "Gestoría no encontrada"
    
    # Verificar límite diario de requests
    hoy = date.today()
    usage_hoy = db.session.query(
        func.sum(ApiKeyUsage.requests_count)
    ).filter(
        ApiKeyUsage.gestoria_id == gestoria_id,
        ApiKeyUsage.date == hoy
    ).scalar() or 0
    
    if usage_hoy >= gestoria.max_requests_dia:
        return False, f"Límite diario alcanzado ({gestoria.max_requests_dia} requests)"
    
    # Verificar límite mensual de tokens
    inicio_mes = hoy.replace(day=1)
    tokens_mes = db.session.query(
        func.sum(ApiKeyUsage.tokens_used)
    ).filter(
        ApiKeyUsage.gestoria_id == gestoria_id,
        ApiKeyUsage.date >= inicio_mes
    ).scalar() or 0
    
    if tokens_mes >= gestoria.max_tokens_mes:
        return False, f"Límite mensual de tokens alcanzado ({gestoria.max_tokens_mes})"
    
    return True, "OK"


def track_api_usage(key_name, tokens_used, success=True, gestoria_id=None):
    """Registra el uso de API con gestoría"""
    from datetime import date
    from models import ApiKeyUsage, db
    from tenant_utils import get_current_gestoria_id
    
    # Si no se pasa gestoria_id, obtenerlo del contexto
    if gestoria_id is None:
        gestoria_id = get_current_gestoria_id()
    
    today = date.today()
    
    # Buscar o crear registro
    usage = ApiKeyUsage.query.filter_by(
        key_name=key_name,
        gestoria_id=gestoria_id,
        date=today
    ).first()
    
    if not usage:
        usage = ApiKeyUsage(
            key_name=key_name,
            gestoria_id=gestoria_id,
            date=today,
            requests_count=0,
            errors_count=0,
            tokens_used=0
        )
        db.session.add(usage)
    
    # Asegurar que los campos no sean None
    if usage.tokens_used is None:
        usage.tokens_used = 0
    if usage.requests_count is None:
        usage.requests_count = 0
    if usage.errors_count is None:
        usage.errors_count = 0
    
    # Actualizar contadores
    usage.tokens_used += tokens_used
    if success:
        usage.requests_count += 1
    else:
        usage.errors_count += 1
    
    db.session.commit()
    return usage
