"""
Sistema de Auditoría Automática
Captura y registra todas las acciones del sistema
"""

from functools import wraps
from flask import request, g, has_request_context
from flask_login import current_user
from datetime import datetime
from extensions import db
import logging

logger = logging.getLogger(__name__)

# Importar AuditoriaLog desde models (no duplicar aquí)
# Este import se hace dentro de las funciones para evitar importación circular


def registrar_auditoria(
    accion: str,
    entidad_tipo: str = None,
    entidad_id: int = None,
    descripcion: str = None,
    detalles: dict = None,
    user_id: int = None,
    gestoria_id: int = None,
    user_email: str = None,
    user_nombre: str = None
):
    """
    Registra una acción en el sistema de auditoría
    
    Args:
        accion: Tipo de acción (ej: "documento_creado", "tarea_asignada")
        entidad_tipo: Tipo de entidad afectada (ej: "documento", "empresa")
        entidad_id: ID de la entidad afectada
        descripcion: Descripción legible de la acción
        detalles: Diccionario con información adicional
        user_id: ID del usuario (para acciones no autenticadas)
        gestoria_id: ID de gestoría (para acciones no autenticadas)
        user_email: Email del usuario (para acciones no autenticadas)
        user_nombre: Nombre del usuario (para acciones no autenticadas)
    """
    try:
        # Importar aquí para evitar importación circular
        from models import AuditoriaLog
        
        # Obtener información del usuario actual o usar los valores explícitos
        if user_id is not None:
            final_user_id = user_id
            final_user_email = user_email or "Sistema"
            final_user_nombre = user_nombre or "Sistema Automático"
        elif current_user.is_authenticated:
            final_user_id = current_user.id
            final_user_email = current_user.email
            final_user_nombre = current_user.nombre
        else:
            final_user_id = None
            final_user_email = "Sistema"
            final_user_nombre = "Sistema Automático"
        
        # FIX M-1: Obtener IP real del cliente (soporte para proxy reverso nginx/gunicorn)
        ip_address = None
        if has_request_context():
            # X-Forwarded-For puede contener una cadena de IPs; la primera es la del cliente real
            x_forwarded_for = request.headers.get('X-Forwarded-For')
            if x_forwarded_for:
                # Tomar solo la primera IP y sanitizarla
                ip_candidata = x_forwarded_for.split(',')[0].strip()
                # Validar que tiene formato de IP (básico) antes de aceptarla
                if ip_candidata and len(ip_candidata) <= 45:
                    ip_address = ip_candidata
            if not ip_address:
                ip_address = request.remote_addr

        # FIX: Sanitizar user-agent para evitar inyección de datos largos
        user_agent = None
        if has_request_context():
            raw_ua = request.headers.get('User-Agent', '')
            # Filtrar caracteres de control y limitar longitud
            user_agent = ''.join(c for c in raw_ua if c.isprintable())[:300]

        metodo_http = request.method if has_request_context() else None
        endpoint = request.path if has_request_context() else None
        
        # Obtener gestoria_id del usuario actual o usar el explícito
        if gestoria_id is not None:
            final_gestoria_id = gestoria_id
        elif current_user.is_authenticated and hasattr(current_user, 'gestoria_id'):
            final_gestoria_id = current_user.gestoria_id
        else:
            final_gestoria_id = None
        
        # Crear registro de auditoría
        log = AuditoriaLog(
            user_id=final_user_id,
            user_email=final_user_email,
            user_nombre=final_user_nombre,
            gestoria_id=final_gestoria_id,
            accion=accion,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            descripcion=descripcion,
            detalles=detalles,
            ip_address=ip_address,
            user_agent=user_agent,
            metodo_http=metodo_http,
            endpoint=endpoint
        )
        
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"📝 Auditoría: {accion} por {final_user_nombre} ({final_user_email})")
        
    except Exception as e:
        logger.error(f"❌ Error al registrar auditoría: {e}")
        db.session.rollback()


def auditar(accion: str, entidad_tipo: str = None):
    """
    Decorador para auditar automáticamente funciones
    
    Usage:
        @auditar("documento_creado", "documento")
        def crear_documento():
            # ... código ...
            return documento
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ejecutar función original
            result = f(*args, **kwargs)
            
            # Intentar extraer detalles del request
            entidad_id = getattr(request, 'auditoria_entidad_id', None)
            detalles = getattr(request, 'auditoria_detalles', {})
            
            # Si no hay detalles en request, intentar extraer del resultado
            if not entidad_id and isinstance(result, dict):
                entidad_id = result.get('id') or result.get('documento_id') or result.get('empresa_id')
            elif not entidad_id and hasattr(result, 'id'):
                entidad_id = result.id
            
            if not detalles and isinstance(result, dict):
                # FIX A-14: Ampliar lista de campos sensibles que no deben aparecer en auditoría
                _campos_sensibles = {
                    'password', 'token', 'secret', 'api_key', 'api_secret',
                    'cert_secret', 'private_key', 'encryption_key', 'totp_secret',
                    'backup_codes', 'iban', 'swift', 'credit_card', 'cvv',
                    'saltra_password', 'saltra_cert_secret', 'stripe_key',
                    'two_factor_secret', 'reset_token'
                }
                detalles = {k: v for k, v in result.items() if k.lower() not in _campos_sensibles}
            
            # Generar descripción mejorada basada en la acción y detalles
            if current_user.is_authenticated:
                usuario = current_user.nombre
                
                # Descripciones específicas por tipo de acción
                if accion == AccionesAuditoria.TAREA_ASIGNADA and detalles:
                    asignado_a = detalles.get('asignado_a', 'Usuario desconocido')
                    tarea = detalles.get('tarea', detalles.get('estado_nuevo', 'Tarea'))
                    doc_nombre = detalles.get('documento_nombre', 'documento')
                    descripcion = f"{usuario} asignó tarea '{tarea}' a {asignado_a} para documento {doc_nombre}"
                
                elif accion == AccionesAuditoria.EMAIL_ENVIADO and detalles:
                    destinatarios = detalles.get('destinatarios', [])
                    dest_str = ', '.join(destinatarios) if destinatarios else 'destinatario desconocido'
                    doc_nombre = detalles.get('documento_nombre', 'documento')
                    descripcion = f"{usuario} envió email a {dest_str} con documento {doc_nombre}"
                
                elif accion == AccionesAuditoria.DOCUMENTO_ACTUALIZADO and detalles:
                    cat_ant = detalles.get('categoria_anterior', '')
                    cat_nueva = detalles.get('categoria_nueva', '')
                    doc_nombre = detalles.get('documento_nombre', 'documento')
                    if cat_ant and cat_nueva:
                        descripcion = f"{usuario} movió {doc_nombre} de '{cat_ant}' a '{cat_nueva}'"
                    else:
                        descripcion = f"{usuario} actualizó {doc_nombre}"
                
                elif accion == AccionesAuditoria.DOCUMENTO_GUARDADO and detalles:
                    doc_nombre = detalles.get('documento_nombre', 'documento')
                    descripcion = f"{usuario} guardó documento {doc_nombre}"
                
                elif accion == AccionesAuditoria.DOCUMENTO_PROCESADO and detalles:
                    doc_nombre = detalles.get('documento_nombre', 'documento')
                    tipo = detalles.get('tipo_documento', 'IA')
                    descripcion = f"{usuario} procesó {doc_nombre} con tipo {tipo}"
                
                else:
                    # Descripción genérica para otras acciones
                    descripcion = f"{usuario} realizó acción: {accion}"
            else:
                descripcion = f"Sistema realizó acción: {accion}"
            
            # Registrar auditoría
            registrar_auditoria(
                accion=accion,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                descripcion=descripcion,
                detalles=detalles if detalles else None
            )
            
            return result
        
        return decorated_function
    return decorator
# =============================================================================
# CONSTANTES DE ACCIONES (para consistencia)
# =============================================================================

class AccionesAuditoria:
    """Catálogo de acciones auditables"""
    
    # Documentos
    DOCUMENTO_CREADO = "documento_creado"
    DOCUMENTO_LEIDO = "documento_leido"
    DOCUMENTO_PROCESADO = "documento_procesado"
    DOCUMENTO_ASIGNADO = "documento_asignado"
    DOCUMENTO_ELIMINADO = "documento_eliminado"
    DOCUMENTO_GUARDADO = "documento_guardado"
    DOCUMENTO_EDITADO = "documento_editado"
    DOCUMENTO_ACTUALIZADO = "documento_actualizado"
    
    # Tareas
    TAREA_CREADA = "tarea_creada"
    TAREA_ASIGNADA = "tarea_asignada"
    TAREA_COMPLETADA = "tarea_completada"
    TAREA_CANCELADA = "tarea_cancelada"
    TAREA_ACTUALIZADA = "tarea_actualizada"
    
    # Empresas
    EMPRESA_CREADA = "empresa_creada"
    EMPRESA_ACTUALIZADA = "empresa_actualizada"
    EMPRESA_ELIMINADA = "empresa_eliminada"
    
    # Emails
    EMAIL_ENVIADO = "email_enviado"
    EMAIL_FALLIDO = "email_fallido"
    
    # Notificaciones Saltra
    SALTRA_SINCRONIZADA = "saltra_sincronizada"
    SALTRA_ACEPTADA = "saltra_aceptada"
    SALTRA_PDF_DESCARGADO = "saltra_pdf_descargado"
    
    # Usuarios
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREADO = "user_creado"
    USER_ACTUALIZADO = "user_actualizado"
    
    # Sistema
    CONFIGURACION_ACTUALIZADA = "configuracion_actualizada"
    EXPORTACION_REALIZADA = "exportacion_realizada"
    IMPORTACION_REALIZADA = "importacion_realizada"