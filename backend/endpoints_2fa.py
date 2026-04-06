# ==================== 2FA ENDPOINTS ====================

@app.route('/api/auth/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    """
    Inicia el proceso de configuración de 2FA
    Genera secret y QR code
    """
    from services.totp_service import TOTPService
    
    try:
        # Generar secret
        secret = TOTPService.generate_secret()
        
        # Generar QR code
        qr_code = TOTPService.generate_qr_code(secret, current_user.email)
        
        # Guardar secret temporalmente en sesión (no en BD aún)
        session['temp_2fa_secret'] = secret
        
        # FIX C-5: No enviar el secret en texto plano en la respuesta HTTP.
        # El QR ya contiene el secret embebido; si el usuario quiere entrada manual,
        # que inicie el proceso de nuevo o use el QR.
        return jsonify({
            'success': True,
            'qr_code': qr_code  # Base64 image (contiene el secret visualmente)
        })
    except Exception as e:
        print(f"Error en setup_2fa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/2fa/verify-setup', methods=['POST'])
@login_required
def verify_2fa_setup():
    """
    Verifica el código TOTP y activa 2FA
    """
    from services.totp_service import TOTPService
    
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token requerido'}), 400
    
    # Obtener secret temporal
    secret = session.get('temp_2fa_secret')
    if not secret:
        return jsonify({'error': 'Sesión expirada. Inicia el proceso nuevamente'}), 400
    
    # Verificar token
    if not TOTPService.verify_token(secret, token):
        return jsonify({'error': 'Código inválido'}), 400
    
    try:
        # Encriptar y guardar secret
        encryption_key = current_app.config['TOTP_ENCRYPTION_KEY']
        encrypted_secret = TOTPService.encrypt_secret(secret, encryption_key)
        
        # Generar códigos de respaldo
        backup_codes = TOTPService.generate_backup_codes()

        # Activar 2FA
        current_user.two_factor_enabled = True
        current_user.two_factor_secret = encrypted_secret
        current_user.set_backup_codes(backup_codes)  # FIX A-4: encriptado en BD
        current_user.two_factor_enabled_at = datetime.utcnow()
        
        db.session.commit()
        
        # Limpiar sesión
        session.pop('temp_2fa_secret', None)
        
        # Auditar
        from auditoria import registrar_auditoria
        registrar_auditoria('activar_2fa', current_user.id, {'user_id': current_user.id})
        
        return jsonify({
            'success': True,
            'backup_codes': backup_codes,
            'message': '2FA activado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error en verify_2fa_setup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/2fa/verify', methods=['POST'])
# FIX A-1: Rate limiting para prevenir fuerza bruta (6 dígitos = 1M combinaciones)
@limiter.limit("5 per minute; 20 per hour")
def verify_2fa_login():
    """
    Verifica código 2FA durante login
    """
    from services.totp_service import TOTPService
    from auditoria import registrar_auditoria

    data = request.json
    token = data.get('token')
    user_id = session.get('2fa_user_id')

    if not user_id:
        return jsonify({'error': 'Sesión inválida'}), 400

    user = User.query.get(user_id)
    if not user or not user.two_factor_enabled:
        return jsonify({'error': 'Usuario inválido'}), 400

    try:
        # Desencriptar secret
        encryption_key = current_app.config['TOTP_ENCRYPTION_KEY']
        secret = TOTPService.decrypt_secret(user.two_factor_secret, encryption_key)

        # Verificar token TOTP
        if TOTPService.verify_token(secret, token):
            login_user(user)
            session.pop('2fa_user_id', None)
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'message': 'Acceso concedido'
            })

        # Verificar si es código de respaldo (FIX A-4: leer desencriptado)
        codes = user.get_backup_codes()
        if codes and token.upper() in codes:
            # Remover código usado de forma atómica para evitar reutilización
            remaining = [c for c in codes if c != token.upper()]
            user.set_backup_codes(remaining)
            db.session.commit()

            login_user(user)
            session.pop('2fa_user_id', None)
            return jsonify({
                'success': True,
                'user': user.to_dict(),
                'backup_code_used': True,
                'remaining_codes': len(remaining),
                'message': 'Acceso concedido con código de respaldo'
            })

        # FIX M-5: Auditar intento fallido de 2FA
        registrar_auditoria(
            '2fa_intento_fallido',
            entidad_tipo='user',
            entidad_id=user.id,
            descripcion=f'Intento fallido de verificación 2FA para {user.email}',
            user_id=user.id,
            gestoria_id=user.gestoria_id,
            user_email=user.email,
            user_nombre=user.nombre
        )

        return jsonify({'error': 'Código inválido'}), 401
    except Exception as e:
        print(f"Error en verify_2fa_login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    """
    Desactiva 2FA (requiere contraseña)
    """
    data = request.json
    password = data.get('password')
    
    if not password or not current_user.check_password(password):
        return jsonify({'error': 'Contraseña incorrecta'}), 401
    
    try:
        # Desactivar 2FA
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.set_backup_codes(None)
        
        db.session.commit()
        
        # Auditar
        from auditoria import registrar_auditoria
        registrar_auditoria('desactivar_2fa', current_user.id, {'user_id': current_user.id})
        
        return jsonify({
            'success': True,
            'message': '2FA desactivado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error en disable_2fa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/2fa/regenerate-backup-codes', methods=['POST'])
@login_required
def regenerate_backup_codes():
    """
    Regenera códigos de respaldo (requiere contraseña)
    """
    from services.totp_service import TOTPService
    
    data = request.json
    password = data.get('password')
    
    if not password or not current_user.check_password(password):
        return jsonify({'error': 'Contraseña incorrecta'}), 401
    
    if not current_user.two_factor_enabled:
        return jsonify({'error': '2FA no está activado'}), 400
    
    try:
        # Generar nuevos códigos
        backup_codes = TOTPService.generate_backup_codes()
        current_user.set_backup_codes(backup_codes)  # FIX A-4: encriptado en BD
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'backup_codes': backup_codes,
            'message': 'Códigos de respaldo regenerados'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error en regenerate_backup_codes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
