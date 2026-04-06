"""
Utilidades de encriptación para datos sensibles en BD (Fernet/AES-128-CBC).

Uso:
    from utils.encryption_utils import encrypt_field, decrypt_field

    # Al guardar:
    model.iban_enc = encrypt_field(iban_texto)

    # Al leer:
    iban_texto = decrypt_field(model.iban_enc)

La clave se toma de la variable de entorno FIELD_ENCRYPTION_KEY.
Si no existe, usa TOTP_ENCRYPTION_KEY como fallback.

IMPORTANTE: Los campos cifrados necesitan columnas de tipo String(500) en BD
(los datos cifrados son más largos que el texto plano).
"""

import os
import base64
import logging

logger = logging.getLogger(__name__)

# ─── Clave de encriptación ─────────────────────────────────────────────────────

def _get_encryption_key() -> bytes:
    """Obtiene la clave Fernet desde las variables de entorno."""
    key = os.environ.get('FIELD_ENCRYPTION_KEY') or os.environ.get('TOTP_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY no está definida. "
            "Añade esta variable de entorno antes de arrancar la aplicación."
        )
    # Fernet requiere exactamente 32 bytes codificados en base64 URL-safe
    raw = key.encode() if isinstance(key, str) else key
    # Normalizar a 32 bytes (padding/truncate si es necesario)
    raw_padded = (raw * ((32 // len(raw)) + 1))[:32]
    return base64.urlsafe_b64encode(raw_padded)


# ─── Encriptar / Desencriptar ──────────────────────────────────────────────────

def encrypt_field(plaintext: str) -> str | None:
    """
    Encripta un string con Fernet (AES-128-CBC + HMAC-SHA256).

    Args:
        plaintext: Texto en claro a encriptar.

    Returns:
        Cadena encriptada base64 URL-safe con prefijo 'enc:',
        o None si plaintext es None/vacío.
    """
    if not plaintext:
        return None
    try:
        from cryptography.fernet import Fernet
        fernet = Fernet(_get_encryption_key())
        token = fernet.encrypt(plaintext.encode('utf-8'))
        return 'enc:' + token.decode('ascii')
    except Exception as e:
        logger.error(f"Error al encriptar campo: {e}")
        raise


def decrypt_field(ciphertext: str) -> str | None:
    """
    Desencripta un string previamente encriptado con encrypt_field().

    Args:
        ciphertext: Cadena encriptada (con prefijo 'enc:') o texto plano legacy.

    Returns:
        Texto en claro, o None si ciphertext es None/vacío.
    """
    if not ciphertext:
        return None
    # Compatibilidad con valores legacy (sin prefijo 'enc:')
    if not ciphertext.startswith('enc:'):
        return ciphertext
    try:
        from cryptography.fernet import Fernet, InvalidToken
        fernet = Fernet(_get_encryption_key())
        token = ciphertext[4:].encode('ascii')
        return fernet.decrypt(token).decode('utf-8')
    except ImportError:
        logger.error("cryptography no instalado — no se puede desencriptar")
        return None
    except Exception as e:
        # InvalidToken: clave incorrecta o dato corrupto → no crashear la app
        # El campo quedará como None y el llamador debe re-pedir la configuración
        logger.warning(
            f"decrypt_field: no se pudo desencriptar (clave incorrecta o dato corrupto). "
            f"Tipo: {type(e).__name__}. "
            f"Asegúrate de que FIELD_ENCRYPTION_KEY coincide con la usada en la migración."
        )
        return None


def mask_field(value: str, visible_chars: int = 4) -> str | None:
    """
    Enmascara un valor sensible para mostrar en interfaces/logs.
    Ej: mask_field('ES7621000418401234567891', 4) → '********************7891'

    Args:
        value: Valor a enmascarar.
        visible_chars: Número de caracteres finales que se muestran.

    Returns:
        Cadena enmascarada, o None si value es None/vacío.
    """
    if not value:
        return None
    if len(value) <= visible_chars:
        return '*' * len(value)
    return '*' * (len(value) - visible_chars) + value[-visible_chars:]
