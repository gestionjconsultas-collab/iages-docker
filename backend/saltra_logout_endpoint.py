# Endpoint para cerrar sesión de SALTRA (eliminar credenciales)
@admin_bp.route('/saltra/logout', methods=['POST'])
from constants import NotificationTypes
@login_required
def logout_saltra():
    """Eliminar credenciales SALTRA de la gestoría"""
    try:
        # Verificar permisos
        if not current_user.is_super_admin and current_user.departamento.nombre.lower().strip() != 'jefatura':
            return jsonify({NotificationTypes.ERROR: 'No tienes permisos para modificar SALTRA'}), 403
        
        gestoria_id = current_user.gestoria_id
        gestoria = Gestoria.query.get(gestoria_id)
        
        if not gestoria:
            return jsonify({NotificationTypes.ERROR: 'Gestoría no encontrada'}), 404
        
        # Eliminar configuración SALTRA
        if gestoria.configuracion is None:
            gestoria.configuracion = {}
        
        gestoria.configuracion['saltra'] = {
            'enabled': False,
            'email': None,
            'password': None,
            'cert_secret': None
        }
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': 'Sesión de SALTRA cerrada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
