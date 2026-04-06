#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TOTP Service - Servicio para autenticación de dos factores
"""

import pyotp
import qrcode
import io
import base64
import secrets
from cryptography.fernet import Fernet


class TOTPService:
    """Servicio para gestionar autenticación de dos factores con TOTP"""
    
    @staticmethod
    def generate_secret():
        """
        Genera un secret aleatorio para TOTP
        
        Returns:
            str: Secret en formato base32
        """
        return pyotp.random_base32()
    
    @staticmethod
    def encrypt_secret(secret, key):
        """
        Encripta el secret antes de guardarlo en BD
        
        Args:
            secret: str - Secret a encriptar
            key: bytes - Clave de encriptación
        
        Returns:
            str: Secret encriptado
        """
        f = Fernet(key)
        return f.encrypt(secret.encode()).decode()
    
    @staticmethod
    def decrypt_secret(encrypted_secret, key):
        """
        Desencripta el secret de la BD
        
        Args:
            encrypted_secret: str - Secret encriptado
            key: bytes - Clave de encriptación
        
        Returns:
            str: Secret desencriptado
        """
        f = Fernet(key)
        return f.decrypt(encrypted_secret.encode()).decode()
    
    @staticmethod
    def generate_qr_code(secret, email, issuer_name='IAGES'):
        """
        Genera QR code para Google Authenticator
        
        Args:
            secret: str - Secret TOTP
            email: str - Email del usuario
            issuer_name: str - Nombre de la aplicación
        
        Returns:
            str: QR code en base64
        """
        # Generar URI para TOTP
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=email,
            issuer_name=issuer_name
        )
        
        # Generar QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Convertir a imagen
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    @staticmethod
    def verify_token(secret, token):
        """
        Verifica si el token TOTP es válido
        
        Args:
            secret: str - Secret TOTP
            token: str - Token de 6 dígitos
        
        Returns:
            bool: True si el token es válido
        """
        totp = pyotp.TOTP(secret)
        # valid_window=1 permite ±30 segundos de margen
        return totp.verify(token, valid_window=1)
    
    @staticmethod
    def generate_backup_codes(count=10):
        """
        Genera códigos de respaldo
        
        Args:
            count: int - Número de códigos a generar
        
        Returns:
            list: Lista de códigos de respaldo
        """
        return [secrets.token_hex(4).upper() for _ in range(count)]
    
    @staticmethod
    def get_current_token(secret):
        """
        Obtiene el token actual (útil para testing)
        
        Args:
            secret: str - Secret TOTP
        
        Returns:
            str: Token actual de 6 dígitos
        """
        totp = pyotp.TOTP(secret)
        return totp.now()
