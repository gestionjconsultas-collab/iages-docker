# ============================================================================
# MODELOS DEL SISTEMA RBAC (Role-Based Access Control)
# ============================================================================

from datetime import datetime
from extensions import db

class Rol(db.Model):
    """Modelo de Rol para sistema de permisos"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id', ondelete='CASCADE'))
    es_sistema = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    permisos = db.relationship('RolPermiso', back_populates='rol', cascade='all, delete-orphan')
    usuarios = db.relationship('User', back_populates='rol')
    gestoria = db.relationship('Gestoria', foreign_keys=[gestoria_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'gestoria_id': self.gestoria_id,
            'gestoria_nombre': self.gestoria.nombre if self.gestoria else 'Global',
            'es_sistema': self.es_sistema,
            'activo': self.activo,
            'permisos_count': len(self.permisos),
            'usuarios_count': len(self.usuarios),
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
    def __repr__(self):
        return f'<Rol {self.nombre}>'


class Permiso(db.Model):
    """Modelo de Permiso para sistema RBAC"""
    __tablename__ = 'permisos'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(100), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    modulo = db.Column(db.String(100))
    recurso = db.Column(db.String(100))
    accion = db.Column(db.String(50))
    ruta = db.Column(db.String(255))
    icono = db.Column(db.String(50))
    es_sistema = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    roles = db.relationship('RolPermiso', back_populates='permiso', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'modulo': self.modulo,
            'recurso': self.recurso,
            'accion': self.accion,
            'ruta': self.ruta,
            'icono': self.icono,
            'es_sistema': self.es_sistema,
            'activo': self.activo
        }
    
    def __repr__(self):
        return f'<Permiso {self.codigo}>'


class RolPermiso(db.Model):
    """Tabla de relación entre Roles y Permisos"""
    __tablename__ = 'roles_permisos'
    
    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permisos.id', ondelete='CASCADE'), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    rol = db.relationship('Rol', back_populates='permisos')
    permiso = db.relationship('Permiso', back_populates='roles')
    
    def to_dict(self):
        return {
            'id': self.id,
            'rol_id': self.rol_id,
            'permiso_id': self.permiso_id,
            'rol_nombre': self.rol.nombre if self.rol else None,
            'permiso_codigo': self.permiso.codigo if self.permiso else None,
            'fecha_asignacion': self.fecha_asignacion.isoformat() if self.fecha_asignacion else None
        }
    
    def __repr__(self):
        return f'<RolPermiso rol={self.rol_id} permiso={self.permiso_id}>'
