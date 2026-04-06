import hashlib
import os

def get_file_hash(filepath, block_size=65536):
    """Calcula el hash SHA-256 de un archivo"""
    if not os.path.exists(filepath):
        return None
        
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha256.update(block)
    return sha256.hexdigest()
