"""
Portal del Empleado — Rutas de autenticación y gestión.

Endpoints públicos (portal frontend):
  POST /portal/api/auth/login        — login con email + contraseña
  POST /portal/api/auth/activar      — activar cuenta con token de email
  POST /portal/api/auth/recuperar    — solicitar restablecimiento de contraseña
  GET  /portal/api/auth/me           — datos del empleado logueado (Bearer token)

Endpoints para gestorías (dashboard principal):
  POST   /api/portal/empleados/<id>/invitar     — invitar empleado al portal
  DELETE /api/portal/empleados/<id>/revocar     — revocar acceso
  GET    /api/portal/empresas/<id>/empleados    — listar empleados con estado portal
"""
import os
from datetime import datetime
from functools import wraps

from flask import jsonify, request, g, current_app
from flask_login import login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from extensions import db
from models import Empleado, Empresa, Gestoria
from models_portal import PortalEmpleadoAuth
from email_sender import _enviar_email_smtp


# ── Tokens de sesión ──────────────────────────────────────────────────────────

def _signer(salt: str) -> URLSafeTimedSerializer:
    secret = os.environ.get('PORTAL_JWT_SECRET') or current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret, salt=salt)


def create_session_token(auth_id: int, empleado_id: int, gestoria_id: int) -> str:
    return _signer('portal-session').dumps(
        {'aid': auth_id, 'eid': empleado_id, 'gid': gestoria_id}
    )


def verify_session_token(token: str) -> dict | None:
    try:
        return _signer('portal-session').loads(token, max_age=7 * 24 * 3600)
    except (SignatureExpired, BadSignature):
        return None


def portal_required(f):
    """Decorador para endpoints que requieren sesión activa del portal."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token requerido'}), 401
        data = verify_session_token(auth_header[7:])
        if not data:
            return jsonify({'error': 'Token inválido o expirado'}), 401
        g.portal_auth_id = data['aid']
        g.portal_empleado_id = data['eid']
        g.portal_gestoria_id = data['gid']
        return f(*args, **kwargs)
    return decorated


# ── Emails ────────────────────────────────────────────────────────────────────

def _email_activacion(auth: PortalEmpleadoAuth, empleado: Empleado,
                      gestoria: Gestoria, url: str) -> bool:
    nombre = empleado.nombre.split()[0] if empleado.nombre else 'empleado'
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);
                  padding:30px;border-radius:12px 12px 0 0;text-align:center;">
        <h1 style="color:white;margin:0;font-size:24px;">Portal del Empleado</h1>
        <p style="color:#bfdbfe;margin:8px 0 0;">{gestoria.nombre}</p>
      </div>
      <div style="background:#f8fafc;padding:30px;
                  border-radius:0 0 12px 12px;border:1px solid #e2e8f0;">
        <p style="font-size:16px;color:#374151;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#6b7280;">
          Has sido invitado a acceder al <strong>Portal del Empleado</strong> de
          <strong>{gestoria.nombre}</strong>. Desde aquí podrás consultar tus nóminas,
          contratos y demás documentos laborales.
        </p>
        <div style="text-align:center;margin:30px 0;">
          <a href="{url}"
             style="background:#2563eb;color:white;padding:14px 32px;
                    border-radius:8px;text-decoration:none;font-weight:bold;
                    font-size:16px;display:inline-block;">
            Activar mi cuenta
          </a>
        </div>
        <p style="color:#9ca3af;font-size:13px;">
          Este enlace caduca en 48 horas. Si no esperabas este correo, puedes ignorarlo.
        </p>
      </div>
    </div>
    """
    return _enviar_email_smtp(
        destinatario=auth.email,
        asunto=f'Acceso al Portal del Empleado — {gestoria.nombre}',
        html_body=html,
        gestoria_id=gestoria.id,
    )


def _email_recuperacion(auth: PortalEmpleadoAuth, empleado: Empleado,
                        gestoria: Gestoria, url: str) -> bool:
    nombre = empleado.nombre.split()[0] if empleado.nombre else 'empleado'
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#1e40af,#3b82f6);
                  padding:30px;border-radius:12px 12px 0 0;text-align:center;">
        <h1 style="color:white;margin:0;font-size:24px;">Portal del Empleado</h1>
        <p style="color:#bfdbfe;margin:8px 0 0;">{gestoria.nombre}</p>
      </div>
      <div style="background:#f8fafc;padding:30px;
                  border-radius:0 0 12px 12px;border:1px solid #e2e8f0;">
        <p style="font-size:16px;color:#374151;">Hola <strong>{nombre}</strong>,</p>
        <p style="color:#6b7280;">
          Recibimos una solicitud para restablecer tu contraseña del Portal del Empleado.
        </p>
        <div style="text-align:center;margin:30px 0;">
          <a href="{url}"
             style="background:#dc2626;color:white;padding:14px 32px;
                    border-radius:8px;text-decoration:none;font-weight:bold;
                    font-size:16px;display:inline-block;">
            Restablecer contraseña
          </a>
        </div>
        <p style="color:#9ca3af;font-size:13px;">
          Este enlace caduca en 1 hora. Si no lo solicitaste, ignora este correo.
        </p>
      </div>
    </div>
    """
    return _enviar_email_smtp(
        destinatario=auth.email,
        asunto='Restablecer contraseña — Portal del Empleado',
        html_body=html,
        gestoria_id=gestoria.id,
    )


# ── Registro de rutas ─────────────────────────────────────────────────────────

def register_portal_empleado_routes(app):

    PORTAL_BASE_URL = os.environ.get('PORTAL_BASE_URL', 'http://localhost:5174')

    # ── Autenticación del portal ───────────────────────────────────────────────

    @app.route('/portal/api/auth/login', methods=['POST'])
    def portal_login():
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'error': 'Email y contraseña requeridos'}), 400

        auth = PortalEmpleadoAuth.query.filter_by(email=email).first()
        if not auth or not auth.activo or not auth.check_password(password):
            return jsonify({'error': 'Credenciales incorrectas'}), 401

        empleado = db.session.get(Empleado, auth.empleado_id)
        empresa = db.session.get(Empresa, empleado.empresa_id)

        auth.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        token = create_session_token(auth.id, auth.empleado_id, empresa.gestoria_id)
        return jsonify({
            'token': token,
            'empleado': {
                'id': empleado.id,
                'nombre': empleado.nombre,
                'nif': empleado.nif,
                'empresa': empresa.nombre,
            },
        })

    @app.route('/portal/api/auth/activar', methods=['POST'])
    def portal_activar():
        data = request.get_json() or {}
        token = data.get('token') or ''
        password = data.get('password') or ''

        if not token or not password:
            return jsonify({'error': 'Token y contraseña requeridos'}), 400
        if len(password) < 8:
            return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

        auth = PortalEmpleadoAuth.query.filter_by(token_activacion=token).first()
        if not auth or not auth.is_token_valid(token):
            return jsonify({'error': 'Enlace de activación inválido o expirado'}), 400

        auth.set_password(password)
        auth.activo = True
        auth.invalidate_token()
        auth.ultimo_acceso = datetime.utcnow()
        db.session.commit()

        empleado = db.session.get(Empleado, auth.empleado_id)
        empresa = db.session.get(Empresa, empleado.empresa_id)
        session_token = create_session_token(auth.id, auth.empleado_id, empresa.gestoria_id)

        return jsonify({
            'success': True,
            'token': session_token,
            'empleado': {
                'id': empleado.id,
                'nombre': empleado.nombre,
                'nif': empleado.nif,
                'empresa': empresa.nombre,
            },
        })

    @app.route('/portal/api/auth/recuperar', methods=['POST'])
    def portal_recuperar():
        """Solicitar restablecimiento de contraseña. Siempre 200 para no enumerar emails."""
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()

        auth = PortalEmpleadoAuth.query.filter_by(email=email, activo=True).first()
        if auth:
            token = auth.generate_activation_token(hours=1)
            db.session.commit()
            empleado = db.session.get(Empleado, auth.empleado_id)
            empresa = db.session.get(Empresa, empleado.empresa_id)
            gestoria = db.session.get(Gestoria, empresa.gestoria_id)
            reset_url = f'{PORTAL_BASE_URL}/activar?token={token}&reset=1'
            _email_recuperacion(auth, empleado, gestoria, reset_url)

        return jsonify({'success': True, 'message': 'Si el email existe, recibirás instrucciones'})

    @app.route('/portal/api/auth/me', methods=['GET'])
    @portal_required
    def portal_me():
        auth = db.session.get(PortalEmpleadoAuth, g.portal_auth_id)
        empleado = db.session.get(Empleado, g.portal_empleado_id)
        empresa = db.session.get(Empresa, empleado.empresa_id)
        return jsonify({
            'empleado': {
                'id': empleado.id,
                'nombre': empleado.nombre,
                'nif': empleado.nif,
                'nss': empleado.nss,
                'tipo_contrato': empleado.tipo_contrato,
                'grupo_cotizacion': empleado.grupo_cotizacion,
                'fecha_alta': empleado.fecha_alta.isoformat() if empleado.fecha_alta else None,
                'empresa': empresa.nombre,
                'empresa_id': empresa.id,
            },
            'email': auth.email,
            'ultimo_acceso': auth.ultimo_acceso.isoformat() if auth.ultimo_acceso else None,
        })

    # ── Gestión desde el dashboard de la gestoría ─────────────────────────────

    @app.route('/api/portal/empleados/<int:empleado_id>/invitar', methods=['POST'])
    @login_required
    def portal_invitar_empleado(empleado_id):
        data = request.get_json() or {}
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'error': 'Email requerido'}), 400

        empleado = db.session.get(Empleado, empleado_id)
        if not empleado:
            return jsonify({'error': 'Empleado no encontrado'}), 404

        empresa = db.session.get(Empresa, empleado.empresa_id)
        if not current_user.has_access_to_company(empresa.id):
            return jsonify({'error': 'Sin permisos'}), 403

        auth = PortalEmpleadoAuth.query.filter_by(empleado_id=empleado_id).first()

        if auth and auth.activo:
            return jsonify({'error': 'Este empleado ya tiene acceso activo al portal'}), 409

        if auth:
            # Reenviar invitación actualizando email
            auth.email = email
        else:
            if PortalEmpleadoAuth.query.filter_by(email=email).first():
                return jsonify({'error': 'Este email ya está registrado en el portal'}), 409
            auth = PortalEmpleadoAuth(empleado_id=empleado_id, email=email)
            db.session.add(auth)

        token = auth.generate_activation_token(hours=48)
        db.session.flush()

        gestoria = db.session.get(Gestoria, empresa.gestoria_id)
        activation_url = f'{PORTAL_BASE_URL}/activar?token={token}'
        _email_activacion(auth, empleado, gestoria, activation_url)

        db.session.commit()
        return jsonify({'success': True, 'message': f'Invitación enviada a {email}'})

    @app.route('/api/portal/empleados/<int:empleado_id>/revocar', methods=['DELETE'])
    @login_required
    def portal_revocar_empleado(empleado_id):
        empleado = db.session.get(Empleado, empleado_id)
        if not empleado:
            return jsonify({'error': 'Empleado no encontrado'}), 404

        empresa = db.session.get(Empresa, empleado.empresa_id)
        if not current_user.has_access_to_company(empresa.id):
            return jsonify({'error': 'Sin permisos'}), 403

        auth = PortalEmpleadoAuth.query.filter_by(empleado_id=empleado_id).first()
        if auth:
            db.session.delete(auth)
            db.session.commit()

        return jsonify({'success': True})

    @app.route('/api/portal/empresas/<int:empresa_id>/empleados', methods=['GET'])
    @login_required
    def portal_lista_empleados_empresa(empresa_id):
        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            return jsonify({'error': 'Empresa no encontrada'}), 404
        if not current_user.has_access_to_company(empresa_id):
            return jsonify({'error': 'Sin permisos'}), 403

        empleados = Empleado.query.filter_by(empresa_id=empresa_id).order_by(Empleado.nombre).all()
        result = []
        for emp in empleados:
            a = emp.portal_auth
            result.append({
                'id': emp.id,
                'nombre': emp.nombre,
                'nif': emp.nif,
                'portal': {
                    'email': a.email,
                    'activo': a.activo,
                    'ultimo_acceso': a.ultimo_acceso.isoformat() if a.ultimo_acceso else None,
                } if a else None,
            })

        return jsonify({'empleados': result})
