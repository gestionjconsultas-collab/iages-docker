"""
Portal del Empleado — Modelo de autenticación independiente.
Los empleados tienen credenciales separadas del sistema de gestorías.
"""
from datetime import datetime, timedelta
import secrets
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash


class PortalEmpleadoAuth(db.Model):
    __tablename__ = 'portal_empleado_auth'

    id = db.Column(db.Integer, primary_key=True)
    empleado_id = db.Column(
        db.Integer,
        db.ForeignKey('empleados.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
        index=True,
    )
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)   # null hasta activación
    activo = db.Column(db.Boolean, default=False, nullable=False)

    # Token para activación inicial / recuperación de contraseña
    token_activacion = db.Column(db.String(100), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    empleado = db.relationship(
        'Empleado',
        backref=db.backref('portal_auth', uselist=False, cascade='all, delete-orphan'),
    )

    # ── Contraseña ─────────────────────────────────────────────────────────────

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # ── Token de activación / recuperación ─────────────────────────────────────

    def generate_activation_token(self, hours: int = 48) -> str:
        token = secrets.token_urlsafe(32)
        self.token_activacion = token
        self.token_expiry = datetime.utcnow() + timedelta(hours=hours)
        return token

    def is_token_valid(self, token: str) -> bool:
        if not self.token_activacion or not self.token_expiry:
            return False
        if self.token_activacion != token:
            return False
        if datetime.utcnow() > self.token_expiry:
            return False
        return True

    def invalidate_token(self):
        self.token_activacion = None
        self.token_expiry = None

    # ── Serialización ──────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'empleado_id': self.empleado_id,
            'email': self.email,
            'activo': self.activo,
            'ultimo_acceso': self.ultimo_acceso.isoformat() if self.ultimo_acceso else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
