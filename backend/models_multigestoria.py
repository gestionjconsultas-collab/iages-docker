

# ============================================
# SISTEMA MULTI-GESTORÍA AVANZADO
# ============================================

class PlanGestoria(db.Model):
    """Planes disponibles para gestorías"""
    __tablename__ = 'planes_gestoria'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text)
    precio_mensual = db.Column(db.Numeric(10, 2), nullable=False)
    usuarios_max = db.Column(db.Integer, nullable=False)
    empresas_max = db.Column(db.Integer, nullable=False)
    almacenamiento_gb = db.Column(db.Integer, nullable=False)
    tokens_ia_mes = db.Column(db.Integer, nullable=False)
    soporte_nivel = db.Column(db.String(50))
    permite_branding = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio_mensual': float(self.precio_mensual),
            'limites': {
                'usuarios_max': self.usuarios_max,
                'empresas_max': self.empresas_max,
                'almacenamiento_gb': self.almacenamiento_gb,
                'tokens_ia_mes': self.tokens_ia_mes
            },
            'soporte_nivel': self.soporte_nivel,
            'permite_branding': self.permite_branding,
            'activo': self.activo
        }


class GestoriaPlan(db.Model):
    """Relación entre gestoría y su plan actual"""
    __tablename__ = 'gestoria_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False, unique=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id'), nullable=False)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime)
    auto_renovar = db.Column(db.Boolean, default=True)
    estado = db.Column(db.String(20), default='activo')
    
    # Relaciones
    gestoria = db.relationship('Gestoria', backref=db.backref('plan_actual', uselist=False))
    plan = db.relationship('PlanGestoria')
    
    def to_dict(self):
        return {
            'id': self.id,
            'gestoria_id': self.gestoria_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'fecha_inicio': self.fecha_inicio.isoformat() if self.fecha_inicio else None,
            'fecha_fin': self.fecha_fin.isoformat() if self.fecha_fin else None,
            'auto_renovar': self.auto_renovar,
            'estado': self.estado
        }


class UsoGestoria(db.Model):
    """Registro de uso mensual por gestoría"""
    __tablename__ = 'uso_gestoria'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    periodo = db.Column(db.String(7), nullable=False)  # YYYY-MM
    usuarios_activos = db.Column(db.Integer, default=0)
    empresas_count = db.Column(db.Integer, default=0)
    documentos_procesados = db.Column(db.Integer, default=0)
    tokens_ia_usados = db.Column(db.Integer, default=0)
    almacenamiento_usado_gb = db.Column(db.Numeric(10, 2), default=0)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    gestoria = db.relationship('Gestoria', backref='uso_mensual')
    
    __table_args__ = (
        db.UniqueConstraint('gestoria_id', 'periodo', name='uq_gestoria_periodo'),
    )
    
    def to_dict(self):
        return {
            'gestoria_id': self.gestoria_id,
            'periodo': self.periodo,
            'usuarios_activos': self.usuarios_activos,
            'empresas_count': self.empresas_count,
            'documentos_procesados': self.documentos_procesados,
            'tokens_ia_usados': self.tokens_ia_usados,
            'almacenamiento_usado_gb': float(self.almacenamiento_usado_gb),
            'fecha_actualizacion': self.fecha_actualizacion.isoformat()
        }


class AuditoriaAccesoGestoria(db.Model):
    """Auditoría de accesos entre gestorías"""
    __tablename__ = 'auditoria_acceso_gestoria'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    gestoria_origen = db.Column(db.Integer, db.ForeignKey('gestorias.id'))
    gestoria_destino = db.Column(db.Integer, db.ForeignKey('gestorias.id'))
    recurso_tipo = db.Column(db.String(50))
    recurso_id = db.Column(db.Integer)
    accion = db.Column(db.String(50))
    permitido = db.Column(db.Boolean)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'gestoria_origen': self.gestoria_origen,
            'gestoria_destino': self.gestoria_destino,
            'recurso_tipo': self.recurso_tipo,
            'recurso_id': self.recurso_id,
            'accion': self.accion,
            'permitido': self.permitido,
            'ip_address': self.ip_address,
            'fecha': self.fecha.isoformat()
        }


class AlertaSistema(db.Model):
    """Alertas del sistema para gestorías"""
    __tablename__ = 'alertas_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'))
    tipo = db.Column(db.String(50), nullable=False)
    nivel = db.Column(db.String(20), default='info')
    titulo = db.Column(db.String(255), nullable=False)
    mensaje = db.Column(db.Text)
    datos_adicionales = db.Column(db.JSON)
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_leida = db.Column(db.DateTime)
    
    # Relaciones
    gestoria = db.relationship('Gestoria', backref='alertas')
    
    def to_dict(self):
        return {
            'id': self.id,
            'gestoria_id': self.gestoria_id,
            'tipo': self.tipo,
            'nivel': self.nivel,
            'titulo': self.titulo,
            'mensaje': self.mensaje,
            'datos_adicionales': self.datos_adicionales,
            'leida': self.leida,
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'fecha_leida': self.fecha_leida.isoformat() if self.fecha_leida else None
        }


class ConfiguracionGlobal(db.Model):
    """Configuraciones globales del sistema"""
    __tablename__ = 'configuracion_global'
    
    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text)
    tipo = db.Column(db.String(20), default='string')
    descripcion = db.Column(db.Text)
    modificable_por_gestoria = db.Column(db.Boolean, default=False)
    fecha_modificacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'clave': self.clave,
            'valor': self.valor if self.clave in ['webapp_version', 'conecta_version', 'conecta_url', 'conecta_notes', 'conecta_sha256', 'conecta_mandatory'] else '********', # 🔒 Sanitizado
            'tipo': self.tipo,
            'descripcion': self.descripcion,
            'modificable_por_gestoria': self.modificable_por_gestoria
        }
