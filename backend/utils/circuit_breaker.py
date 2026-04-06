# backend/utils/circuit_breaker.py
"""
Circuit Breaker para proteger contra fallos en servicios externos
Usa pybreaker para implementar el patrón Circuit Breaker
"""

try:
    import pybreaker
    PYBREAKER_AVAILABLE = True
except ImportError:
    PYBREAKER_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ pybreaker no instalado. Circuit breaker deshabilitado.")


# ==========================================
# CIRCUIT BREAKERS CONFIGURADOS
# ==========================================

if PYBREAKER_AVAILABLE:
    # Circuit Breaker para Saltra API
    # - Falla después de 5 errores consecutivos
    # - Se resetea después de 60 segundos
    # - Timeout de 30 segundos por request
    saltra_breaker = pybreaker.CircuitBreaker(
        fail_max=5,
        reset_timeout=60,
        exclude=[
            pybreaker.CircuitBreakerError,
            KeyboardInterrupt,
        ],
        name='saltra_api'
    )
    
    # Circuit Breaker para Gemini AI
    # - Más tolerante: 10 fallos antes de abrir
    # - Reset más rápido: 30 segundos
    gemini_breaker = pybreaker.CircuitBreaker(
        fail_max=10,
        reset_timeout=30,
        exclude=[
            pybreaker.CircuitBreakerError,
            KeyboardInterrupt,
        ],
        name='gemini_ai'
    )
    
    # Circuit Breaker para SMTP
    smtp_breaker = pybreaker.CircuitBreaker(
        fail_max=3,
        reset_timeout=120,  # 2 minutos
        name='smtp_server'
    )
    
else:
    # Fallback: decorador dummy que no hace nada
    class DummyBreaker:
        """Circuit breaker dummy cuando pybreaker no está disponible"""
        def __call__(self, func):
            return func
        
        @property
        def current_state(self):
            return "disabled"
    
    saltra_breaker = DummyBreaker()
    gemini_breaker = DummyBreaker()
    smtp_breaker = DummyBreaker()


# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================

def get_breaker_status(breaker_name: str) -> dict:
    """
    Obtiene el estado actual de un circuit breaker
    
    Args:
        breaker_name: Nombre del breaker ('saltra_api', 'gemini_ai', 'smtp_server')
    
    Returns:
        dict con estado del circuit breaker
    """
    if not PYBREAKER_AVAILABLE:
        return {
            'name': breaker_name,
            'state': 'disabled',
            'available': False,
            'message': 'pybreaker not installed'
        }
    
    breakers = {
        'saltra_api': saltra_breaker,
        'gemini_ai': gemini_breaker,
        'smtp_server': smtp_breaker
    }
    
    breaker = breakers.get(breaker_name)
    if not breaker:
        return {
            'name': breaker_name,
            'state': 'unknown',
            'available': False,
            'message': 'Breaker not found'
        }
    
    state = str(breaker.current_state)
    
    return {
        'name': breaker_name,
        'state': state,
        'available': state == 'closed',
        'fail_counter': breaker.fail_counter if hasattr(breaker, 'fail_counter') else 0,
        'fail_max': breaker.fail_max if hasattr(breaker, 'fail_max') else 0,
        'message': f'Circuit breaker is {state}'
    }


def get_all_breakers_status() -> dict:
    """
    Obtiene el estado de todos los circuit breakers
    
    Returns:
        dict con estado de todos los breakers
    """
    return {
        'saltra_api': get_breaker_status('saltra_api'),
        'gemini_ai': get_breaker_status('gemini_ai'),
        'smtp_server': get_breaker_status('smtp_server'),
        'pybreaker_available': PYBREAKER_AVAILABLE
    }


def reset_breaker(breaker_name: str) -> bool:
    """
    Resetea manualmente un circuit breaker
    
    Args:
        breaker_name: Nombre del breaker a resetear
    
    Returns:
        bool: True si se reseteó correctamente
    """
    if not PYBREAKER_AVAILABLE:
        return False
    
    breakers = {
        'saltra_api': saltra_breaker,
        'gemini_ai': gemini_breaker,
        'smtp_server': smtp_breaker
    }
    
    breaker = breakers.get(breaker_name)
    if breaker and hasattr(breaker, 'close'):
        try:
            breaker.close()
            return True
        except:
            return False
    
    return False
