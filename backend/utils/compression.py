"""
Configuración de Flask-Compress para compresión de respuestas
Mejora el rendimiento reduciendo el tamaño de las respuestas HTTP
"""
from flask_compress import Compress

compress = Compress()

def init_compress(app):
    """
    Inicializa compresión de respuestas
    
    Comprime automáticamente respuestas > 500 bytes
    Soporta: gzip, deflate, br (Brotli)
    """
    app.config['COMPRESS_MIMETYPES'] = [
        'text/html',
        'text/css',
        'text/xml',
        'application/json',
        'application/javascript',
        'text/javascript'
    ]
    app.config['COMPRESS_LEVEL'] = 6  # Balance entre velocidad y compresión
    app.config['COMPRESS_MIN_SIZE'] = 500  # Solo comprimir respuestas > 500 bytes
    
    compress.init_app(app)
    return compress
