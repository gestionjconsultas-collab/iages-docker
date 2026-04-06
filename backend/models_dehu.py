from extensions import db
from datetime import datetime

class NotificacionDehu(db.Model):
    __tablename__ = 'notificaciones_dehu'

    id = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.String(100), unique=True, nullable=False) # sentReference
    identificador = db.Column(db.String(100)) # notificationId
    titulo = db.Column(db.String(255))
    nombre_titular = db.Column(db.String(255))
    fecha_emision = db.Column(db.DateTime)
    fecha_descarga = db.Column(db.DateTime)
    nif_titular = db.Column(db.String(20))
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True) # Multi-tenant
    upload_status = db.Column(db.String(20), default='PENDING') # PENDING, UPLOADED, ERROR
    file_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    empresa = db.relationship('Empresa', backref='notificaciones_dehu')
    gestoria = db.relationship('Gestoria', backref='notificaciones_dehu')

    def to_dict(self):
        return {
            'id': self.id,
            'referencia': self.referencia,
            'identificador': self.identificador,
            'titulo': self.titulo,
            'nombre_titular': self.nombre_titular,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'fecha_descarga': self.fecha_descarga.isoformat() if self.fecha_descarga else None,
            'nif_titular': self.nif_titular,
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'upload_status': self.upload_status,
            'file_path': self.file_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
