"""
Utilidades para generar y validar tokens de confirmación de pago
"""
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
import os
from constants import TaskStates

def generar_token_confirmacion(linea_id):
    """Genera un token seguro para confirmación de pago de una línea de finiquito"""
    serializer = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key')))
    return serializer.dumps({'linea_id': linea_id}, salt='confirmar-pago-finiquito')

def validar_token_confirmacion(token, max_age=2592000):
    """
    Valida un token de confirmación y retorna el linea_id
    max_age: tiempo máximo de validez en segundos (default 30 días)
    """
    serializer = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key')))
    try:
        data = serializer.loads(token, salt='confirmar-pago-finiquito', max_age=max_age)
        return data.get('linea_id')
    except Exception as e:
        print(f"Error validando token: {e}")
        return None

def generar_url_confirmacion(linea_id, action='pagado'):
    """
    Genera URL completa para confirmar pago
    action: 'pagado' o TaskStates.PENDIENTE
    """
    token = generar_token_confirmacion(linea_id)
    base_url = current_app.config.get('BASE_URL', 'http://localhost:5000')
    return f"{base_url}/finiquitos/confirmar/{token}?action={action}"
