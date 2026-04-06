# backend/models_billing.py
"""
Modelos de facturación con cumplimiento legal español
"""
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import JSONB

class EmpresaEmisora(db.Model):
    """Datos de IAGES (empresa emisora de facturas)"""
    __tablename__ = 'empresa_emisora'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False, default='IAGES')
    cif = db.Column(db.String(20), nullable=False)  # OBLIGATORIO
    direccion = db.Column(db.Text, nullable=False)
    codigo_postal = db.Column(db.String(10))
    ciudad = db.Column(db.String(100))
    provincia = db.Column(db.String(100))
    pais = db.Column(db.String(100), default='España')
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(150))
    web = db.Column(db.String(200))
    logo_path = db.Column(db.String(500))
    
    # Datos bancarios — almacenados encriptados (FIX C-6)
    # NOTA: Las columnas deben ser String(500) en BD para aceptar el texto cifrado.
    #       Si la migración aún no se ha aplicado, los valores legacy siguen funcionando
    #       gracias al prefijo 'enc:' que distingue datos cifrados de texto plano.
    iban = db.Column(db.String(500))   # encriptado
    swift = db.Column(db.String(500))  # encriptado
    banco = db.Column(db.String(500))  # encriptado

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Propiedades de encriptación ──────────────────────────────────────────

    @property
    def iban_decrypted(self) -> str | None:
        """Devuelve el IBAN en texto claro."""
        from utils.encryption_utils import decrypt_field
        return decrypt_field(self.iban)

    @iban_decrypted.setter
    def iban_decrypted(self, value: str):
        from utils.encryption_utils import encrypt_field
        self.iban = encrypt_field(value)

    @property
    def swift_decrypted(self) -> str | None:
        """Devuelve el SWIFT en texto claro."""
        from utils.encryption_utils import decrypt_field
        return decrypt_field(self.swift)

    @swift_decrypted.setter
    def swift_decrypted(self, value: str):
        from utils.encryption_utils import encrypt_field
        self.swift = encrypt_field(value)

    @property
    def banco_decrypted(self) -> str | None:
        """Devuelve el nombre del banco en texto claro."""
        from utils.encryption_utils import decrypt_field
        return decrypt_field(self.banco)

    @banco_decrypted.setter
    def banco_decrypted(self, value: str):
        from utils.encryption_utils import encrypt_field
        self.banco = encrypt_field(value)

    @staticmethod
    def get_datos_iages():
        """Obtiene los datos de IAGES (siempre hay solo un registro)"""
        return EmpresaEmisora.query.first()


# Importar PlanGestoria desde models.py y usarlo directamente
from models import PlanGestoria

# Alias simple para compatibilidad (sin herencia para evitar conflictos)
Plan = PlanGestoria


class Suscripcion(db.Model):
    """Suscripciones de gestorías"""
    __tablename__ = 'suscripciones'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id', ondelete='CASCADE'), nullable=False, unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id'), nullable=False)
    
    # Estado
    estado = db.Column(db.String(50), default='activa')  # activa, cancelada, suspendida, trial, vencida
    fecha_inicio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    fecha_proximo_pago = db.Column(db.DateTime)
    
    # Facturación
    ciclo = db.Column(db.String(20), default='mensual')  # mensual, anual
    precio_actual = db.Column(db.Numeric(10, 2), nullable=False)
    descuento_porcentaje = db.Column(db.Numeric(5, 2), default=0)
    
    # Trial
    trial_hasta = db.Column(db.DateTime)
    
    # Stripe
    stripe_subscription_id = db.Column(db.String(255))
    stripe_customer_id = db.Column(db.String(255))
    
    # Cupones
    cupon_codigo = db.Column(db.String(50))
    cupon_descuento = db.Column(db.Numeric(10, 2), default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = db.relationship('PlanGestoria', backref=db.backref('suscripciones', lazy=True), foreign_keys=[plan_id])
    facturas = db.relationship('Factura', backref='suscripcion', lazy=True)
    
    @property
    def esta_en_trial(self):
        """Verifica si la suscripción está en período de prueba"""
        if not self.trial_hasta:
            return False
        return datetime.utcnow() < self.trial_hasta
    
    @property
    def dias_restantes_trial(self):
        """Días restantes de trial"""
        if not self.esta_en_trial:
            return 0
        return (self.trial_hasta - datetime.utcnow()).days
    
    def to_dict(self):
        return {
            'id': self.id,
            'gestoria_id': self.gestoria_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'estado': self.estado,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'fecha_proximo_pago': self.fecha_proximo_pago.isoformat() if self.fecha_proximo_pago else None,
            'ciclo': self.ciclo,
            'precio_actual': float(self.precio_actual),
            'descuento_porcentaje': float(self.descuento_porcentaje),
            'esta_en_trial': self.esta_en_trial,
            'dias_restantes_trial': self.dias_restantes_trial,
            'cupon_codigo': self.cupon_codigo
        }


class Factura(db.Model):
    """Facturas con cumplimiento legal español"""
    __tablename__ = 'facturas'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id', ondelete='CASCADE'), nullable=False)
    suscripcion_id = db.Column(db.Integer, db.ForeignKey('suscripciones.id'))
    
    # Numeración secuencial OBLIGATORIA
    numero_factura = db.Column(db.String(50), unique=True, nullable=False)
    serie = db.Column(db.String(10), default='FAC')
    numero_secuencial = db.Column(db.Integer, nullable=False)
    
    # Fechas
    fecha_emision = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=False)
    
    # Importes OBLIGATORIOS
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    iva_porcentaje = db.Column(db.Numeric(5, 2), default=21.00)
    iva_importe = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Concepto
    concepto = db.Column(db.Text, nullable=False)
    periodo_inicio = db.Column(db.Date)
    periodo_fin = db.Column(db.Date)
    lineas = db.Column(JSONB, default=[])
    
    # Estado
    estado = db.Column(db.String(50), default='pendiente')  # pendiente, pagada, vencida, cancelada
    fecha_pago = db.Column(db.DateTime)
    metodo_pago = db.Column(db.String(50))
    
    # Stripe
    stripe_invoice_id = db.Column(db.String(255))
    stripe_payment_intent_id = db.Column(db.String(255))
    
    # PDF (CONSERVAR 4 AÑOS)
    pdf_path = db.Column(db.String(500))
    pdf_generado = db.Column(db.Boolean, default=False)
    
    notas = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def esta_vencida(self):
        """Verifica si la factura está vencida"""
        if self.estado == 'pagada':
            return False
        return datetime.utcnow() > self.fecha_vencimiento
    
    @property
    def dias_hasta_vencimiento(self):
        """Días hasta el vencimiento"""
        if self.estado == 'pagada':
            return None
        delta = self.fecha_vencimiento - datetime.utcnow()
        return delta.days
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_factura': self.numero_factura,
            'fecha_emision': self.fecha_emision.isoformat() if self.fecha_emision else None,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'subtotal': float(self.subtotal),
            'iva_porcentaje': float(self.iva_porcentaje),
            'iva_importe': float(self.iva_importe),
            'total': float(self.total),
            'concepto': self.concepto,
            'estado': self.estado,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'metodo_pago': self.metodo_pago,
            'pdf_path': self.pdf_path,
            'pdf_generado': self.pdf_generado,
            'esta_vencida': self.esta_vencida,
            'dias_hasta_vencimiento': self.dias_hasta_vencimiento
        }


class UsoMensual(db.Model):
    """Tracking de uso mensual por gestoría"""
    __tablename__ = 'uso_mensual'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id', ondelete='CASCADE'), nullable=False)
    
    # Período
    mes = db.Column(db.Integer, nullable=False)  # 1-12
    anio = db.Column(db.Integer, nullable=False)
    
    # Uso de recursos
    usuarios_activos = db.Column(db.Integer, default=0)
    empresas_totales = db.Column(db.Integer, default=0)
    storage_usado_gb = db.Column(db.Numeric(10, 2), default=0)
    tokens_usados = db.Column(db.BigInteger, default=0)
    requests_ia = db.Column(db.Integer, default=0)
    documentos_procesados = db.Column(db.Integer, default=0)
    emails_enviados = db.Column(db.Integer, default=0)
    
    # Costos
    costo_ia = db.Column(db.Numeric(10, 2), default=0)
    costo_storage = db.Column(db.Numeric(10, 2), default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('gestoria_id', 'mes', 'anio', name='uq_uso_gestoria_periodo'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'mes': self.mes,
            'anio': self.anio,
            'usuarios_activos': self.usuarios_activos,
            'empresas_totales': self.empresas_totales,
            'storage_usado_gb': float(self.storage_usado_gb),
            'tokens_usados': self.tokens_usados,
            'requests_ia': self.requests_ia,
            'documentos_procesados': self.documentos_procesados,
            'emails_enviados': self.emails_enviados,
            'costo_ia': float(self.costo_ia),
            'costo_storage': float(self.costo_storage)
        }


class Cupon(db.Model):
    """Cupones de descuento"""
    __tablename__ = 'cupones'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    
    # Tipo de descuento
    tipo = db.Column(db.String(20), nullable=False)  # porcentaje, fijo
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Aplicabilidad
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id'))  # NULL = todos los planes
    ciclo = db.Column(db.String(20))  # mensual, anual, NULL = ambos
    
    # Límites
    usos_maximos = db.Column(db.Integer)
    usos_actuales = db.Column(db.Integer, default=0)
    fecha_inicio = db.Column(db.DateTime)
    fecha_expiracion = db.Column(db.DateTime)
    
    # Estado
    activo = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Column doesn't exist in DB
    
    @property
    def esta_vigente(self):
        """Verifica si el cupón está vigente"""
        if not self.activo:
            return False
        
        ahora = datetime.utcnow()
        
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        
        if self.fecha_expiracion and ahora > self.fecha_expiracion:
            return False
        
        if self.usos_maximos and self.usos_actuales >= self.usos_maximos:
            return False
        
        return True
    
    def calcular_descuento(self, precio):
        """Calcula el descuento aplicado al precio"""
        if not self.esta_vigente:
            return 0
        
        if self.tipo == 'porcentaje':
            return float(precio) * (float(self.valor) / 100)
        elif self.tipo == 'fijo':
            return min(float(self.valor), float(precio))
        
        return 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'codigo': self.codigo,
            'descripcion': self.descripcion,
            'tipo': self.tipo,
            'valor': float(self.valor),
            'plan_id': self.plan_id,
            'ciclo': self.ciclo,
            'usos_maximos': self.usos_maximos,
            'usos_actuales': self.usos_actuales,
            'fecha_expiracion': self.fecha_expiracion.isoformat() if self.fecha_expiracion else None,
            'activo': self.activo,
            'esta_vigente': self.esta_vigente
        }


class HistorialCambiosPlan(db.Model):
    """Historial de cambios de plan (auditoría)"""
    __tablename__ = 'historial_cambios_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id', ondelete='CASCADE'), nullable=False)
    suscripcion_id = db.Column(db.Integer, db.ForeignKey('suscripciones.id'))
    
    plan_anterior_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id'))
    plan_nuevo_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id'))
    
    motivo = db.Column(db.String(50))  # upgrade, downgrade, cancelacion
    precio_anterior = db.Column(db.Numeric(10, 2))
    precio_nuevo = db.Column(db.Numeric(10, 2))
    
    # Prorrateado
    credito_generado = db.Column(db.Numeric(10, 2), default=0)
    cargo_adicional = db.Column(db.Numeric(10, 2), default=0)
    
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    plan_anterior = db.relationship('PlanGestoria', foreign_keys=[plan_anterior_id])
    plan_nuevo = db.relationship('PlanGestoria', foreign_keys=[plan_nuevo_id])

    def to_dict(self):
        return {
            'id': self.id,
            'fecha': self.created_at.isoformat() if self.created_at else None,
            'motivo': self.motivo,
            'plan_anterior': self.plan_anterior.nombre if self.plan_anterior else None,
            'plan_nuevo': self.plan_nuevo.nombre if self.plan_nuevo else None,
            'precio_anterior': float(self.precio_anterior) if self.precio_anterior else None,
            'precio_nuevo': float(self.precio_nuevo) if self.precio_nuevo else None,
            'credito_generado': float(self.credito_generado),
            'cargo_adicional': float(self.cargo_adicional)
        }


class BannerPromocional(db.Model):
    """Banners promocionales para la vista de facturación"""
    __tablename__ = 'banners_promocionales'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), default='promocion')  # upgrade, descuento, promocion
    cupon_codigo = db.Column(db.String(50), db.ForeignKey('cupones.codigo'))
    plan_objetivo = db.Column(db.String(50))  # basico, plus, premium
    color_fondo = db.Column(db.String(20), default='#FF6B35')  # Hex color
    icono = db.Column(db.String(50), default='🎉')  # Emoji
    url_accion = db.Column(db.String(200))  # URL opcional
    activo = db.Column(db.Boolean, default=True)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    prioridad = db.Column(db.Integer, default=0)  # Mayor número = mayor prioridad
    
    # Analytics
    clicks = db.Column(db.Integer, default=0)
    conversiones = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cupon = db.relationship('Cupon', backref='banners')
    
    def esta_activo(self):
        """Verifica si el banner está activo y dentro del período válido"""
        if not self.activo:
            return False
        
        ahora = datetime.utcnow()
        
        # Verificar fecha de inicio
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        
        # Verificar fecha de fin
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        
        return True
    
    def incrementar_clicks(self):
        """Incrementa el contador de clicks"""
        if self.clicks is None:
            self.clicks = 0
        self.clicks += 1
        db.session.commit()
    
    def incrementar_conversiones(self):
        """Incrementa el contador de conversiones"""
        if self.conversiones is None:
            self.conversiones = 0
        self.conversiones += 1
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'tipo': self.tipo,
            'cupon_codigo': self.cupon_codigo,
            'plan_objetivo': self.plan_objetivo,
            'color_fondo': self.color_fondo,
            'icono': self.icono,
            'url_accion': self.url_accion,
            'activo': self.activo,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'prioridad': self.prioridad,
            'clicks': self.clicks,
            'conversiones': self.conversiones,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'esta_activo': self.esta_activo()
        }
