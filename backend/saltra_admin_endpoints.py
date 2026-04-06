# Agregar al final de routes_admin.py

from constants import NotificationTypes
@admin_bp.route('/gestoria/<int:gestoria_id>/saltra-status', methods=['GET'])
@admin_required
def get_gestoria_saltra_status(gestoria_id):
    """Obtener estado de configuración SALTRA de una gestoría específica (super-admin)"""
    try:
        # Solo super-admin puede ver estado de otras gestorías
        if not current_user.is_super_admin and current_user.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'No autorizado'}), 403
        
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        if not gestoria.configuracion or not gestoria.configuracion.get('saltra'):
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'configured': False,
                'enabled': False
            })
        
        saltra_config = gestoria.configuracion['saltra']
        has_credentials = bool(saltra_config.get('email') and saltra_config.get('password'))
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'configured': has_credentials,
            'enabled': saltra_config.get('enabled', False)
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@admin_bp.route('/gestoria/<int:gestoria_id>/saltra-config', methods=['PUT'])
@admin_required
def update_gestoria_saltra_config(gestoria_id):
    """Actualizar configuración SALTRA de una gestoría específica (solo super-admin)"""
    try:
        # Solo super-admin puede configurar otras gestorías
        if not current_user.is_super_admin:
            return jsonify({NotificationTypes.ERROR: 'Solo super-administradores pueden configurar SALTRA de otras gestorías'}), 403
        
        data = request.json
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        # Validar datos requeridos (email y password para login)
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        enabled = data.get('enabled', True)
        
        if not email or not password:
            return jsonify({NotificationTypes.ERROR: 'Email y Password son requeridos'}), 400
        
        # Usar helper encriptado (preserva cert_secret del entorno si existe)
        import os
        cert_secret = os.getenv('SALTRA_CERT_SECRET')
        gestoria.set_saltra_config(email=email, password=password, cert_secret=cert_secret, enabled=enabled)

        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': f'Configuración SALTRA actualizada para {gestoria.nombre}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
