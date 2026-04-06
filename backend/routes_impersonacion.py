from flask import jsonify, request, session
from flask_login import login_required, current_user
from models import db, Gestoria, User
from constants import NotificationTypes
import uuid, json
from datetime import datetime


def register_impersonacion_routes(app, socketio, redis_client):

    def puede_impersonar(user):
        if user.is_super_admin:
            return True
        if getattr(user, 'is_soporte', False) and user.gestoria_id is None:
            return True
        if user.departamento and user.departamento.nombre == 'Soporte' and user.gestoria_id is None:
            return True
        return False

    @app.route('/api/impersonacion/solicitar/<int:gestoria_id>', methods=['POST'])
    @login_required
    def solicitar_acceso_gestoria(gestoria_id):
        if not puede_impersonar(current_user):
            return jsonify({NotificationTypes.ERROR: 'Sin permisos'}), 403
        gestoria = db.session.get(Gestoria, gestoria_id)
        if not gestoria:
            return jsonify({NotificationTypes.ERROR: 'Gestoría no encontrada'}), 404

        request_id = str(uuid.uuid4())
        solicitud = {
            'request_id': request_id,
            'soporte_user_id': current_user.id,
            'soporte_nombre': current_user.nombre,
            'gestoria_id': gestoria_id,
            'gestoria_nombre': gestoria.nombre,
            'timestamp': datetime.utcnow().isoformat()
        }
        redis_client.setex(f'solicitud_imp:{request_id}', 300, json.dumps(solicitud))

        socketio.emit('solicitud_acceso_soporte', {
            'request_id': request_id,
            'soporte_nombre': current_user.nombre,
            'gestoria_nombre': gestoria.nombre,
            'timestamp': solicitud['timestamp']
        }, room=f'gestoria_staff_{gestoria_id}')

        try:
            from auditoria import registrar_auditoria
            registrar_auditoria(
                accion='SOLICITUD_IMPERSONACION', entidad_tipo='gestoria',
                entidad_id=gestoria_id,
                descripcion=f'Soporte {current_user.nombre} solicitó acceso a {gestoria.nombre}',
                detalles={'request_id': request_id}
            )
        except Exception:
            pass

        return jsonify({NotificationTypes.SUCCESS: True, 'request_id': request_id})

    @app.route('/api/impersonacion/responder', methods=['POST'])
    @login_required
    def responder_solicitud_impersonacion():
        data = request.json
        request_id = data.get('request_id')
        accion = data.get('accion')  # 'aceptar' o 'rechazar'

        if accion not in ('aceptar', 'rechazar'):
            return jsonify({NotificationTypes.ERROR: 'Acción inválida'}), 400
        if not current_user.gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'Sin permisos'}), 403

        raw = redis_client.get(f'solicitud_imp:{request_id}')
        if not raw:
            return jsonify({NotificationTypes.ERROR: 'Solicitud expirada'}), 404

        solicitud = json.loads(raw)
        if solicitud['gestoria_id'] != current_user.gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'No autorizado'}), 403

        soporte_uid = solicitud['soporte_user_id']
        redis_client.delete(f'solicitud_imp:{request_id}')

        if accion == 'aceptar':
            token = str(uuid.uuid4())
            redis_client.setex(f'token_imp:{token}', 1800, json.dumps({
                'soporte_user_id': soporte_uid,
                'gestoria_id': solicitud['gestoria_id'],
                'gestoria_nombre': solicitud['gestoria_nombre'],
                'aprobado_por': current_user.nombre,
                'aprobado_por_id': current_user.id
            }))
            socketio.emit('respuesta_acceso_soporte', {
                'aceptado': True, 'token': token,
                'gestoria_id': solicitud['gestoria_id'],
                'gestoria_nombre': solicitud['gestoria_nombre'],
                'aprobado_por': current_user.nombre
            }, room=f'user_{soporte_uid}')
            try:
                from auditoria import registrar_auditoria
                registrar_auditoria(
                    accion='IMPERSONACION_ACEPTADA', entidad_tipo='gestoria',
                    entidad_id=solicitud['gestoria_id'],
                    descripcion=f'{current_user.nombre} aceptó acceso a {solicitud["gestoria_nombre"]} para soporte {solicitud["soporte_nombre"]}'
                )
            except Exception:
                pass
        else:
            socketio.emit('respuesta_acceso_soporte', {
                'aceptado': False,
                'gestoria_nombre': solicitud['gestoria_nombre'],
                'aprobado_por': current_user.nombre
            }, room=f'user_{soporte_uid}')
            try:
                from auditoria import registrar_auditoria
                registrar_auditoria(
                    accion='IMPERSONACION_RECHAZADA', entidad_tipo='gestoria',
                    entidad_id=solicitud['gestoria_id'],
                    descripcion=f'{current_user.nombre} rechazó acceso a {solicitud["gestoria_nombre"]} para soporte {solicitud["soporte_nombre"]}'
                )
            except Exception:
                pass

        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/impersonacion/activar', methods=['POST'])
    @login_required
    def activar_impersonacion():
        if not puede_impersonar(current_user):
            return jsonify({NotificationTypes.ERROR: 'Sin permisos'}), 403
        token = request.json.get('token')
        raw = redis_client.get(f'token_imp:{token}')
        if not raw:
            return jsonify({NotificationTypes.ERROR: 'Token inválido o expirado'}), 400
        td = json.loads(raw)
        if td['soporte_user_id'] != current_user.id:
            return jsonify({NotificationTypes.ERROR: 'Token no válido'}), 403

        session['impersonando_gestoria_id'] = td['gestoria_id']
        session['impersonando_gestoria_nombre'] = td['gestoria_nombre']
        session['impersonando_aprobado_por'] = td['aprobado_por']
        session.modified = True
        redis_client.delete(f'token_imp:{token}')

        try:
            from auditoria import registrar_auditoria
            registrar_auditoria(
                accion='IMPERSONACION_ACTIVADA', entidad_tipo='gestoria',
                entidad_id=td['gestoria_id'],
                descripcion=f'Soporte {current_user.nombre} inició sesión en {td["gestoria_nombre"]}'
            )
        except Exception:
            pass

        return jsonify({NotificationTypes.SUCCESS: True,
                        'gestoria_id': td['gestoria_id'],
                        'gestoria_nombre': td['gestoria_nombre']})

    @app.route('/api/impersonacion/terminar', methods=['POST'])
    @login_required
    def terminar_impersonacion():
        gid = session.pop('impersonando_gestoria_id', None)
        gnombre = session.pop('impersonando_gestoria_nombre', None)
        session.pop('impersonando_aprobado_por', None)
        session.modified = True
        if gid:
            try:
                from auditoria import registrar_auditoria
                registrar_auditoria(
                    accion='IMPERSONACION_TERMINADA', entidad_tipo='gestoria',
                    entidad_id=gid,
                    descripcion=f'Soporte {current_user.nombre} terminó sesión en {gnombre}'
                )
            except Exception:
                pass
        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/impersonacion/estado', methods=['GET'])
    @login_required
    def estado_impersonacion():
        gid = session.get('impersonando_gestoria_id')
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'activa': gid is not None,
            'gestoria_id': gid,
            'gestoria_nombre': session.get('impersonando_gestoria_nombre'),
            'aprobado_por': session.get('impersonando_aprobado_por')
        })
