"""
Validación de archivos subidos
"""
import os


def validate_pdf_mime(file):
    """
    Valida que un archivo sea realmente un PDF verificando magic bytes
    
    Args:
        file: FileStorage object de Flask
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    try:
        # Leer los primeros bytes para verificar magic bytes
        file.seek(0)
        header = file.read(8)
        file.seek(0)  # Reset para uso posterior
        
        # PDF magic bytes: %PDF-
        if not header.startswith(b'%PDF-'):
            return False, "El archivo no es un PDF válido (magic bytes incorrectos)"
        
        # Verificar extensión
        if not file.filename.lower().endswith('.pdf'):
            return False, "La extensión del archivo debe ser .pdf"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validando archivo: {str(e)}"


def allowed_file(filename, allowed_extensions={'pdf'}):
    """
    Verifica si la extensión del archivo está permitida
    
    Args:
        filename: Nombre del archivo
        allowed_extensions: Set de extensiones permitidas
    
    Returns:
        bool: True si la extensión está permitida
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions
