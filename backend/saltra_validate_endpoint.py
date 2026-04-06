# Backend endpoint to add to routes_admin.py

from constants import NotificationTypes
@admin_bp.route('/saltra/validate-credentials', methods=['POST'])
@login_required
def validate_saltra_credentials():
    """Validar credenciales SALTRA y retornar cert_secret"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({NotificationTypes.ERROR: 'Email y Password son requeridos'}), 400
        
        # Intentar login a SALTRA para validar credenciales
        from services.saltra_service import SaltraService
        import os
        
        # Usar cert_secret del .env como fallback para la validación
        cert_secret = os.getenv('SALTRA_CERT_SECRET')
        
        try:
            # Crear servicio temporal
            saltra_test = SaltraService(
                api_key=email,
                api_secret=password,
                cert_secret=cert_secret
            )
            
            # Intentar obtener token
            token = saltra_test._get_token()
            
            if not token:
                return jsonify({
                    NotificationTypes.ERROR: 'Credenciales inválidas'
                }), 400
            
            # Si el login fue exitoso, confirmar sin exponer el secret
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': 'Credenciales validadas correctamente'
            })
                
        except Exception as e:
            return jsonify({
                NotificationTypes.ERROR: f'Error al validar: {str(e)}'
            }), 400
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
