# Agregar al archivo models.py

class PushSubscription(db.Model):
    """Suscripciones a notificaciones push"""
    __tablename__ = 'push_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.String(500), nullable=False, unique=True)
    p256dh = db.Column(db.String(200), nullable=False)
    auth = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, default=True)
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con usuario
    user = db.relationship('User', backref=db.backref('push_subscriptions', lazy=True))
    
    def __repr__(self):
        return f'<PushSubscription {self.id} - User {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'endpoint': self.endpoint,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
