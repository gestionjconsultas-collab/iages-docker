"""
Endpoints para gestión de preferencias de notificaciones push
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from services.notification_service import NotificationService

notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """Obtener preferencias de notificación del usuario actual"""
    try:
        prefs = NotificationService.get_user_preferences(current_user.id)
        return jsonify({
            'success': True,
            'preferences': prefs
        })
    except Exception as e:
        print(f"Error obteniendo preferencias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/preferences', methods=['PUT'])
@login_required
def update_preferences():
    """Actualizar preferencias de notificación"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
        
        NotificationService.update_preferences(current_user.id, data)
        
        return jsonify({
            'success': True,
            'message': 'Preferencias actualizadas correctamente'
        })
    except Exception as e:
        print(f"Error actualizando preferencias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@notifications_bp.route('/test', methods=['POST'])
@login_required
def test_notification():
    """Enviar notificación de prueba al usuario actual"""
    try:
        socketio = current_app.extensions.get('socketio')
        if not socketio:
            return jsonify({'error': 'WebSocket no disponible'}), 500
        
        # Emitir notificación de prueba al usuario
        socketio.emit('test_notification', {
            'title': '🔔 Notificación de Prueba',
            'body': 'Las notificaciones están funcionando correctamente',
            'icon': '/logo192.png',
            'tag': 'test-notification'
        }, room=f'user_{current_user.id}')
        
        print(f"✅ Notificación de prueba enviada a user_{current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Notificación de prueba enviada'
        })
    except Exception as e:
        print(f"Error enviando notificación de prueba: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
