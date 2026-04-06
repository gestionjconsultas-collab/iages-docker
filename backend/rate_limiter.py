"""
Sistema de Rate Limiting para Chat IA
======================================

Limita el número de preguntas que un usuario puede hacer por hora
para controlar costos y prevenir abuso del sistema.

Uso:
    from rate_limiter import rate_limit
    
    @rate_limit(limite=20, ventana_horas=1)
    def mi_endpoint():
        ...
"""

from functools import wraps
from flask import jsonify
from datetime import datetime, timedelta
from flask_login import current_user
from extensions import db
from models import MensajeChat, Conversacion
from sqlalchemy import func
from constants import NotificationTypes


class RateLimiter:
    """Sistema de rate limiting por usuario"""
    
    @staticmethod
    def check_limit(usuario_id: int, limite: int = 20, ventana_horas: int = 1) -> dict:
        """
        Verifica si usuario ha excedido límite de requests
        
        Args:
            usuario_id: ID del usuario
            limite: Número máximo de requests permitidos
            ventana_horas: Ventana de tiempo en horas
        
        Returns:
            dict con:
                - permitido: bool
                - requests_usados: int
                - requests_restantes: int
                - reset_en_segundos: int
                - limite: int
        """
        # Calcular ventana de tiempo
        ahora = datetime.now()
        desde = ahora - timedelta(hours=ventana_horas)
        
        # Contar mensajes del usuario en la ventana
        count = db.session.query(
            func.count(MensajeChat.id)
        ).join(
            Conversacion,
            MensajeChat.conversacion_id == Conversacion.id
        ).filter(
            Conversacion.usuario_id == usuario_id,
            MensajeChat.rol == 'user',
            MensajeChat.fecha_creacion >= desde
        ).scalar() or 0
        
        # Verificar si está permitido
        permitido = count < limite
        requests_restantes = max(0, limite - count)
        
        # Calcular cuándo se resetea el límite
        primer_mensaje = db.session.query(
            MensajeChat.fecha_creacion
        ).join(
            Conversacion,
            MensajeChat.conversacion_id == Conversacion.id
        ).filter(
            Conversacion.usuario_id == usuario_id,
            MensajeChat.rol == 'user',
            MensajeChat.fecha_creacion >= desde
        ).order_by(
            MensajeChat.fecha_creacion.asc()
        ).first()
        
        if primer_mensaje:
            reset_time = primer_mensaje[0] + timedelta(hours=ventana_horas)
            segundos_restantes = (reset_time - ahora).total_seconds()
        else:
            segundos_restantes = 0
        
        return {
            'permitido': permitido,
            'requests_usados': count,
            'requests_restantes': requests_restantes,
            'reset_en_segundos': max(0, int(segundos_restantes)),
            'limite': limite,
            'ventana_horas': ventana_horas
        }


def rate_limit(limite: int = 20, ventana_horas: int = 1):
    """
    Decorador para aplicar rate limiting a endpoints
    
    Args:
        limite: Número máximo de requests permitidos
        ventana_horas: Ventana de tiempo en horas
    
    Uso:
        @rate_limit(limite=20, ventana_horas=1)
        def mi_endpoint():
            ...
    
    Retorna:
        - 429 si se excede el límite
        - Agrega headers X-RateLimit-* a la respuesta
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar límite
            resultado = RateLimiter.check_limit(
                current_user.id,
                limite,
                ventana_horas
            )
            
            # Si excedió el límite, retornar error 429
            if not resultado['permitido']:
                minutos_restantes = resultado['reset_en_segundos'] // 60
                
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'rate_limit_exceeded',
                    'mensaje': f"Has alcanzado el límite de {limite} preguntas por hora. "
                              f"Podrás hacer más preguntas en {minutos_restantes} minutos.",
                    'rate_limit': {
                        'limite': resultado['limite'],
                        'usado': resultado['requests_usados'],
                        'restante': resultado['requests_restantes'],
                        'reset_en': resultado['reset_en_segundos']
                    }
                }), 429
            
            # Ejecutar función original
            response = f(*args, **kwargs)
            
            # Agregar headers de rate limit a la respuesta
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(limite)
                response.headers['X-RateLimit-Remaining'] = str(resultado['requests_restantes'])
                response.headers['X-RateLimit-Reset'] = str(resultado['reset_en_segundos'])
            
            return response
        
        return decorated_function
    return decorator
