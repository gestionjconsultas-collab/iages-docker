# backend/config_compress.py
"""
Configuración de compresión de respuestas HTTP
Reduce el tamaño de las respuestas en ~70-80%
"""

from flask_compress import Compress

def init_compress(app):
    """
    Inicializa Flask-Compress para comprimir respuestas HTTP
    
    Beneficios:
    - Reduce ancho de banda en ~70-80%
    - Mejora velocidad de carga
    - Reduce costos de transferencia
    
    Args:
        app: Instancia de Flask
    """
    compress = Compress()
    
    # Configuración de compresión
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript',
    ]
    
    # Nivel de compresión (1-9, 6 es el default óptimo)
    app.config['COMPRESS_LEVEL'] = 6
    
    # Tamaño mínimo para comprimir (500 bytes)
    app.config['COMPRESS_MIN_SIZE'] = 500
    
    # Comprimir solo si el cliente lo soporta
    app.config['COMPRESS_ALGORITHM'] = 'gzip'
    
    compress.init_app(app)
    
    return compress
