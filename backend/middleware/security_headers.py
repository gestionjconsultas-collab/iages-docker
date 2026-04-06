# backend/middleware/security_headers.py
"""
Middleware de headers de seguridad HTTP
Protección contra XSS, Clickjacking, MIME sniffing, etc.
"""

def add_security_headers(response):
    """
    Agrega headers de seguridad a todas las respuestas HTTP.
    
    Headers incluidos:
    - X-Content-Type-Options: Previene MIME sniffing
    - X-Frame-Options: Previene clickjacking
    - X-XSS-Protection: Protección XSS del navegador
    - Strict-Transport-Security: Fuerza HTTPS
    - Referrer-Policy: Controla información del referrer
    - Permissions-Policy: Restringe APIs del navegador
    - Content-Security-Policy: Política de seguridad de contenido
    """
    # Prevenir MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # Prevenir clickjacking (iframes) - SAMEORIGIN permite embeds dentro de la misma app
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    # Protección XSS del navegador
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Forzar HTTPS por 1 año
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Política de referrer
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Restringir APIs del navegador
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    # ⭐ NUEVO: Content Security Policy
    # Permite scripts/estilos necesarios para React, Socket.IO, Gemini API
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' ws: wss: https://generativelanguage.googleapis.com; "
        "frame-ancestors 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Cache control para contenido sensible
    if '/api/' in response.headers.get('Content-Location', ''):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
    
    return response


def init_security_headers(app):
    """
    Inicializa el middleware de headers de seguridad.
    
    Args:
        app: Instancia de Flask
    """
    @app.after_request
    def after_request_security(response):
        return add_security_headers(response)
    
    app.logger.info("✅ Middleware de seguridad HTTP inicializado")
