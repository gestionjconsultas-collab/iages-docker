# backend/models_saltra.py
"""
Modelos para integración con Saltra DEHU
"""
from datetime import datetime
from extensions import db


class NotificacionSaltra(db.Model):
    """
    Modelo para almacenar notificaciones sincronizadas desde Saltra DEHU
    """
    __tablename__ = 'notificaciones_saltra'
    
    # Identificadores
    id = db.Column(db.Integer, primary_key=True)
    sent_reference = db.Column(db.String(100), unique=True, nullable=False, index=True)
    identifier = db.Column(db.String(100))
    
    # Datos del titular
    nif_titular = db.Column(db.String(20), nullable=True, index=True)  # Permitir NULL para notificaciones sin NIF
    vinculo_receptor = db.Column(db.String(50))
    bond_type = db.Column(db.String(50))
    
    # Emisor
    emitter_entity = db.Column(db.String(500))
    emitter_source_entity = db.Column(db.String(500))
    
    # Contenido
    concept = db.Column(db.String(1000))
    
    # ✅ FASE 2: Campos adicionales
    # Datos del receptor
    nif_receptor = db.Column(db.String(20), index=True)
    name_receptor = db.Column(db.String(500))
    
    # Código SIA (Sistema de Información Administrativa)
    sia_code = db.Column(db.String(50), index=True)
    sia_denomination = db.Column(db.String(500))
    
    # Anexos
    cant_annexes = db.Column(db.Integer, default=0)
    
    # Estado
    state = db.Column(db.String(50), index=True)
    notification_priority = db.Column(db.String(20), default='NORMAL')
    assurance_level = db.Column(db.String(20))
    
    # Fechas
    availability_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    final_date = db.Column(db.DateTime)
    
    # Flags
    postal_delivery = db.Column(db.Boolean, default=False)
    has_annexes = db.Column(db.Boolean, default=False)
    
    # Archivos descargados
    pdf_descargado = db.Column(db.Boolean, default=False)
    pdf_path = db.Column(db.String(1000))
    resguardo_path = db.Column(db.String(1000))
    
    # Relación con empresa local
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    empresa = db.relationship('Empresa', backref='notificaciones_saltra')
    
    # Multi-tenant: Gestoría a la que pertenece esta notificación
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False, index=True)
    gestoria = db.relationship('Gestoria', backref='notificaciones_saltra')
    
    # Documento local creado
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=True)
    documento = db.relationship('Documento', backref='notificacion_saltra_origen')
    
    # Metadatos de sincronización
    sincronizado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    datos_raw = db.Column(db.JSON)
    
    # Estado interno
    procesado = db.Column(db.Boolean, default=False)
    error_mensaje = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'sent_reference': self.sent_reference,
            'identifier': self.identifier,
            'nif_titular': self.nif_titular,
            'vinculo_receptor': self.vinculo_receptor,
            'emitter_entity': self.emitter_entity,
            'emitter_source_entity': self.emitter_source_entity,
            'concept': self.concept,
            # Fase 2: Campos adicionales
            'nif_receptor': self.nif_receptor,
            'name_receptor': self.name_receptor,
            'sia_code': self.sia_code,
            'sia_denomination': self.sia_denomination,
            'cant_annexes': self.cant_annexes,
            'state': self.state,
            'notification_priority': self.notification_priority,
            'availability_date': self.availability_date.isoformat() if self.availability_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'final_date': self.final_date.isoformat() if self.final_date else None,
            'has_annexes': self.has_annexes,
            'pdf_descargado': self.pdf_descargado,
            'pdf_path': self.pdf_path,
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'documento_id': self.documento_id,
            'procesado': self.procesado,
            'sincronizado_en': self.sincronizado_en.isoformat() if self.sincronizado_en else None,
            'error_mensaje': self.error_mensaje
        }
    
    def to_dict_simple(self):
        return {
            'id': self.id,
            'sent_reference': self.sent_reference,
            'identifier': self.identifier,
            'nif_titular': self.nif_titular,
            'emitter_entity': self.emitter_entity,
            'concept': self.concept,
            # Fase 2: Campos adicionales
            'sia_code': self.sia_code,
            'cant_annexes': self.cant_annexes,
            'state': self.state,
            'availability_date': self.availability_date.isoformat() if self.availability_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'pdf_descargado': self.pdf_descargado,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'procesado': self.procesado
        }
    
    @classmethod
    def from_api_data(cls, data: dict):
        """
        Crea una instancia desde los datos de la API de Saltra
        
        Args:
            data: Dict con los datos de una notificación de la API
        
        Returns:
            NotificacionSaltra: Instancia sin guardar
        """
        from dateutil import parser
        
        def parse_date(date_str):
            """Parsea fechas de la API"""
            if not date_str:
                return None
            try:
                return parser.parse(date_str)
            except:
                return None
        
        # INFERIR ESTADO si viene vacío o None
        state = data.get('state')
        if not state or state == '':
            # Si tiene finalDate, está aceptada/procesada
            if data.get('finalDate'):
                state = 'ACEPTADA'
            else:
                # Si no tiene finalDate, está pendiente
                state = 'PENDIENTE'
        
        return cls(
            sent_reference=data.get('sentReference'),
            identifier=data.get('identifier'),
            nif_titular=data.get('nifTitular'),
            vinculo_receptor=data.get('vinculoReceptor'),
            bond_type=data.get('bondType'),
            emitter_entity=data.get('emitterEntity'),
            emitter_source_entity=data.get('emitterSourceEntity'),
            concept=data.get('concept'),
            # ✅ FASE 2: Mapear nuevos campos
            nif_receptor=data.get('nifReceptor'),
            name_receptor=data.get('nameReceptor'),
            sia_code=data.get('siaCode'),
            sia_denomination=data.get('siaDenomination'),
            cant_annexes=data.get('cantAnnexes', 0),
            state=state or 'PENDIENTE',  # Default a PENDIENTE si sigue siendo None
            notification_priority=data.get('notificationPriority', 'NORMAL'),
            assurance_level=data.get('assuranceLevel'),
            availability_date=parse_date(data.get('availabilityDate')),
            expiration_date=parse_date(data.get('expirationDate')),
            final_date=parse_date(data.get('finalDate')),
            postal_delivery=data.get('postalDelivery', False),
            has_annexes=data.get('hasAnnexes', False),
            datos_raw=data
        )


class SaltraSyncLog(db.Model):
    """Log de sincronizaciones con Saltra"""
    __tablename__ = 'saltra_sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Multi-tenant: Gestoría que ejecutó la sincronización
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False, index=True)
    gestoria = db.relationship('Gestoria', backref='saltra_sync_logs')
    
    tipo = db.Column(db.String(50))
    total_api = db.Column(db.Integer)
    nuevas = db.Column(db.Integer, default=0)
    actualizadas = db.Column(db.Integer, default=0)
    errores = db.Column(db.Integer, default=0)
    duracion_segundos = db.Column(db.Float)
    mensaje = db.Column(db.String(500))
    detalles = db.Column(db.JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'tipo': self.tipo,
            'total_api': self.total_api,
            'nuevas': self.nuevas,
            'actualizadas': self.actualizadas,
            'errores': self.errores,
            'duracion_segundos': self.duracion_segundos,
            'mensaje': self.mensaje
        }