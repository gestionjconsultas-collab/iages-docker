# Rutas de API para Push Notifications
# Agregar a app.py

@app.route('/api/push/subscribe', methods=['POST'])
@login_required
def push_subscribe():
    """Suscribir usuario a notificaciones push"""
    from models import PushSubscription
    
    data = request.get_json()
    subscription = data.get('subscription')
    
    if not subscription:
        return jsonify({'success': False, 'error': 'Datos de suscripción requeridos'}), 400
    
    try:
        # Verificar si ya existe
        existing = PushSubscription.query.filter_by(
            endpoint=subscription['endpoint']
        ).first()
        
        if existing:
            # Actualizar si existe
            existing.p256dh = subscription['keys']['p256dh']
            existing.auth = subscription['keys']['auth']
            existing.active = True
            existing.user_agent = request.headers.get('User-Agent')
        else:
            # Crear nueva suscripción
            new_sub = PushSubscription(
                user_id=current_user.id,
                endpoint=subscription['endpoint'],
                p256dh=subscription['keys']['p256dh'],
                auth=subscription['keys']['auth'],
                user_agent=request.headers.get('User-Agent')
            )
            db.session.add(new_sub)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Suscripción guardada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error guardando suscripción: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/push/unsubscribe', methods=['POST'])
@login_required
def push_unsubscribe():
    """Desuscribir de notificaciones push"""
    from models import PushSubscription
    
    data = request.get_json()
    endpoint = data.get('endpoint')
    
    if not endpoint:
        return jsonify({'success': False, 'error': 'Endpoint requerido'}), 400
    
    try:
        subscription = PushSubscription.query.filter_by(
            endpoint=endpoint,
            user_id=current_user.id
        ).first()
        
        if subscription:
            subscription.active = False
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Desuscripción exitosa'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error desuscribiendo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/push/vapid-public-key', methods=['GET'])
def get_vapid_public_key():
    """Obtener clave pública VAPID para suscripciones"""
    public_key = app.config.get('VAPID_PUBLIC_KEY')
    
    if not public_key:
        return jsonify({'success': False, 'error': 'VAPID no configurado'}), 500
    
    return jsonify({
        'success': True,
        'publicKey': public_key
    })


@app.route('/api/push/test', methods=['POST'])
@login_required
def push_test():
    """Enviar notificación de prueba"""
    from services.push_notification_service import PushNotificationService
    
    notification = {
        'title': 'Notificación de prueba',
        'body': 'Esta es una notificación de prueba de IAGES',
        'icon': '/icons/icon-192x192.png',
        'badge': '/icons/badge-72x72.png',
        'data': {
            'url': '/dashboard',
            'type': 'test'
        }
    }
    
    sent = PushNotificationService.send_to_user(current_user.id, notification)
    
    return jsonify({
        'success': sent > 0,
        'message': f'Notificación enviada a {sent} dispositivo(s)'
    })
