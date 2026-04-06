# backend/models.py
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from extensions import db

class Departamento(db.Model):
    __tablename__ = 'departamentos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    usuarios = db.relationship('User', backref='departamento', lazy=True)


class Gestoria(db.Model):
    """Modelo para multi-tenant - Cada gestoría es un tenant independiente"""
    __tablename__ = 'gestorias'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Información básica
    nombre = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)  # URL-friendly: gestoria-abc
    email = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(300))
    cif = db.Column(db.String(20))
    
    # Estado y fechas
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_expiracion = db.Column(db.DateTime)  # Para suscripciones
    
    # Configuración personalizada (logo, colores, etc.)
    configuracion = db.Column(db.JSON, default={})
    
    # Límites y cuotas
    max_usuarios = db.Column(db.Integer, default=10)
    max_empresas = db.Column(db.Integer, default=100)
    max_storage_gb = db.Column(db.Integer, default=50)
    
    # Límites de IA
    max_tokens_mes = db.Column(db.Integer, default=1000000)  # 1M tokens/mes
    max_requests_dia = db.Column(db.Integer, default=1000)   # 1K requests/día
    max_certificados = db.Column(db.Integer, default=5)     # Límite de certificados para SyncManager
    iages_active = db.Column(db.Boolean, default=False)     # Flag para activar funciones de IAGES
    
    # Plan de suscripción
    plan = db.Column(db.String(50), default='basico')  # basico, profesional, enterprise
    
    # ⭐ Credenciales Sincronización Externa
    api_key = db.Column(db.String(100), unique=True, nullable=True)
    
    # Relationships
    usuarios = db.relationship('User', backref='gestoria', lazy=True)
    empresas = db.relationship('Empresa', backref='gestoria', lazy=True)
    
    # ── Helpers de encriptación para credenciales Saltra (FIX C-10) ─────────────

    def get_saltra_config_decrypted(self) -> dict:
        """
        Devuelve las credenciales Saltra desencriptadas.
        Uso interno del backend únicamente — nunca serializar al frontend.
        """
        from utils.encryption_utils import decrypt_field
        raw = (self.configuracion or {}).get('saltra', {})
        if not raw:
            return {}
        return {
            'email': decrypt_field(raw.get('email')) or raw.get('email'),
            'password': decrypt_field(raw.get('password')) or raw.get('password'),
            'cert_secret': decrypt_field(raw.get('cert_secret')) or raw.get('cert_secret'),
            'enabled': raw.get('enabled', True)
        }

    def set_saltra_config(self, email: str, password: str, cert_secret: str, enabled: bool = True):
        """
        Guarda las credenciales Saltra encriptadas en el campo JSON de configuración.
        """
        from utils.encryption_utils import encrypt_field
        from sqlalchemy.orm.attributes import flag_modified
        config = dict(self.configuracion or {})
        config['saltra'] = {
            'email': encrypt_field(email) if email else None,
            'password': encrypt_field(password) if password else None,
            'cert_secret': encrypt_field(cert_secret) if cert_secret else None,
            'enabled': enabled
        }
        self.configuracion = config
        flag_modified(self, 'configuracion')

    def to_dict(self):
        # Sanitizar configuración para evitar fuga de credenciales a usuarios no-admin
        safe_config = (self.configuracion or {}).copy()
        for key in ['saltra', 'api_key', 'api_secret', 'password', 'token', 'secret', 'cert_secret']:
            if key in safe_config:
                del safe_config[key]
                
        return {
            'id': self.id,
            'nombre': self.nombre,
            'slug': self.slug,
            'email': self.email,
            'telefono': self.telefono,
            'direccion': self.direccion,
            'cif': self.cif,
            'activa': self.activa,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_expiracion': self.fecha_expiracion.isoformat() if self.fecha_expiracion else None,
            'configuracion': safe_config,
            'max_usuarios': self.max_usuarios,
            'max_empresas': self.max_empresas,
            'max_storage_gb': self.max_storage_gb,
            'max_certificados': self.max_certificados,
            'plan': self.plan
        }

    def to_dict_public(self):
        """Versión minimalista para el endpoint público de info tenant.
        No retornamos ID numérico ni email para evitar 'ruido' técnico en Network.
        """
        return {
            'nombre': self.nombre,
            'slug': self.slug,
            'configuracion': {} 
        }

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    departamento_id = db.Column(db.Integer, db.ForeignKey('departamentos.id'))
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True)  # ⭐ Nullable para soporte externo
    is_super_admin = db.Column(db.Boolean, default=False, nullable=False)  # Super admin flag
    is_soporte = db.Column(db.Boolean, default=False, nullable=False)  # Usuario de soporte (acceso a todas las gestorías)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='SET NULL'))  # RBAC
    preferencias = db.Column(db.JSON, default={}) 
    
    # 2FA fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(128), nullable=True)  # Encriptado
    backup_codes = db.Column(db.Text(500), nullable=True)  # JSON encriptado con Fernet (FIX A-4)
    two_factor_enabled_at = db.Column(db.DateTime, nullable=True)
    
    # Password reset fields
    reset_token = db.Column(db.String(64), nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    rol = db.relationship('Rol', back_populates='usuarios', foreign_keys=[rol_id])
    
    # ── Helpers backup_codes (FIX A-4: encriptación en BD) ──────────────────────

    def get_backup_codes(self) -> list:
        """Devuelve la lista de códigos de respaldo desencriptados."""
        import json
        if not self.backup_codes:
            return []
        raw = self.backup_codes
        if raw.startswith('enc:'):
            from utils.encryption_utils import decrypt_field
            raw = decrypt_field(raw)
        try:
            return json.loads(raw)
        except Exception:
            return []

    def set_backup_codes(self, codes):
        """Guarda los códigos de respaldo como JSON encriptado. Pasa None para limpiar."""
        import json
        if codes is None:
            self.backup_codes = None
            return
        from utils.encryption_utils import encrypt_field
        self.backup_codes = encrypt_field(json.dumps(codes))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password): 
        return check_password_hash(self.password_hash, password)
    
    def tiene_permiso(self, codigo_permiso):
        """Verificar si el usuario tiene un permiso específico"""
        if self.is_super_admin:
            return True
        if not self.rol:
            return False
        return any(rp.permiso.codigo == codigo_permiso for rp in self.rol.permisos if rp.permiso.activo)
    
    def obtener_permisos(self):
        """Obtener lista de códigos de permisos del usuario (rol + individuales)"""
        if self.is_super_admin:
            return ['*']  # Todos los permisos
        
        permisos = set()
        
        # Permisos del rol
        if self.rol and self.rol.activo:
            permisos.update([rp.permiso.codigo for rp in self.rol.permisos if rp.permiso.activo])
        
        # Permisos individuales adicionales
        permisos.update([up.permiso.codigo for up in self.permisos_individuales if up.permiso.activo])
        
        return list(permisos)
    
    def to_dict(self): 
        return {
            'id': self.id, 
            'email': self.email, 
            'nombre': self.nombre, 
            'activo': self.activo, 
            'departamento': self.departamento.nombre if self.departamento else None,
            'departamento_id': self.departamento_id,
            'gestoria_id': self.gestoria_id,
            'is_super_admin': self.is_super_admin,
            'rol_id': self.rol_id,
            'rol_nombre': self.rol.nombre if self.rol else None,
            'preferencias': self.preferencias or {},
            'permisos': self.obtener_permisos(),
            'managed_group_ids': self.get_managed_group_ids(),
            'two_factor_enabled': self.two_factor_enabled
            # FIX A-15: backup_codes_count eliminado — no debe exponerse al cliente
        }

    def to_dict_session(self):
        """Versión refinada para el estado de sesión del frontend (Networking tab limpio)"""
        is_invitado = self.is_invitado()
        
        if not is_invitado:
            # Usuarios normales/admins: todo lo necesario para la lógica completa
            return {
                'id': self.id,
                'email': self.email,
                'nombre': self.nombre,
                'departamento': self.departamento.nombre if self.departamento else None,
                'gestoria_id': self.gestoria_id,
                'is_super_admin': self.is_super_admin,
                'rol_nombre': self.rol.nombre if self.rol else None,
                'managed_group_ids': self.get_managed_group_ids(),
                'preferencias': self.preferencias or {},
                'permisos': self.obtener_permisos(),
                'two_factor_enabled': self.two_factor_enabled
            }
        
        # ⭐ INVITADOS: Elisión agresiva de metadatos
        data = {
            'nombre': self.nombre,
            'departamento': 'Invitado',
            'preferencias': self.preferencias or {}
        }
        
        # Solo enviamos managed_group_ids si realmente gestiona algún grupo
        mg_ids = self.get_managed_group_ids()
        if mg_ids:
            data['managed_group_ids'] = mg_ids
            
        # Elidimos gestoria_id, is_super_admin, permisos y 2FA si son invitados 
        # (el frontend asume defaults o usa flags presentes)
        return data

    def is_invitado(self):
        """Si el usuario pertenece al departamento de Invitado"""
        return self.departamento and self.departamento.nombre == 'Invitado'

    def get_allowed_company_ids(self):
        """Obtiene todos los IDs de empresas a los que el usuario tiene acceso (directo o via grupo)"""
        from extensions import db
        from models import Empresa

        # FIX C-4: Super-admin separado para evitar confusión con gestoria_id=None
        # Solo traer la columna id, no objetos completos
        if self.is_super_admin:
            return [r for (r,) in db.session.query(Empresa.id).all()]

        # Usuarios normales/admins (no invitados): todas las empresas de su gestoría
        if not self.is_invitado():
            return [r for (r,) in db.session.query(Empresa.id)
                    .filter_by(gestoria_id=self.gestoria_id).all()]

        # Invitados: solo las empresas asignadas explícitamente
        allowed_ids = set()

        # 1. Accesos directos a empresas
        for acceso in self.empresa_accesos:
            allowed_ids.add(acceso.empresa_id)

        # 2. Accesos vía grupos (Holdings)
        for g_acceso in self.grupo_accesos:
            for empresa in g_acceso.grupo.empresas_rel:
                allowed_ids.add(empresa.id)

        return list(allowed_ids)

    def has_access_to_company(self, empresa_id):
        """Verifica si el usuario tiene acceso a una empresa específica"""
        from models import Empresa

        # FIX C-4: Super-admin tiene acceso a todo
        if self.is_super_admin:
            return True

        # Usuarios normales/admins: validar que la empresa es de su gestoría
        if not self.is_invitado():
            emp = Empresa.query.get(empresa_id)
            return emp is not None and emp.gestoria_id == self.gestoria_id

        # Invitados: validar contra lista de empresas permitidas
        return empresa_id in self.get_allowed_company_ids()

    def get_managed_group_ids(self):
        """Obtiene los IDs de los grupos donde el usuario es administrador"""
        return [ga.grupo_id for ga in self.grupo_accesos if ga.es_admin_grupo]

class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)  # MULTI-TENANT
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)  # ⭐ NUEVO: Para filtrar por empresa
    departamento_destino = db.Column(db.String(100), nullable=True) 
    titulo = db.Column(db.String(100), nullable=False)
    mensaje = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), default='info') 
    link = db.Column(db.String(255), nullable=True) 
    leida = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    gestoria = db.relationship('Gestoria', backref='notificaciones')
    empresa = db.relationship('Empresa', backref='notificaciones')
    
    def to_dict(self): 
        return {
            'id': self.id, 
            'titulo': self.titulo, 
            'mensaje': self.mensaje, 
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'tipo': self.tipo, 
            'link': self.link, 
            'leida': self.leida, 
            'fecha': self.fecha_creacion.isoformat() + 'Z'
        }

class Plantilla(db.Model):
    __tablename__ = 'plantillas'
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True) # NULL significa global/sistema
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255))
    campos = db.Column(db.JSON, default={}) 
    prompt_template = db.Column(db.Text, nullable=True)
    patron_deteccion = db.Column(db.Text, nullable=True)  # Palabra clave o Regex
    categoria_default = db.Column(db.String(100), nullable=True)  # Carpeta destino (ej: Notificaciones)
    prioridad_default = db.Column(db.String(50), nullable=True) # Prioridad destino (ej: informativa, importante, urgente)
    departamento_default = db.Column(db.String(100), nullable=True) # Departamento destino (ej: Laboral)
    
    # Campos para Marketplace
    es_publica = db.Column(db.Boolean, default=False)
    id_original = db.Column(db.Integer, nullable=True) # ID de la plantilla del marketplace de la que proviene
    votos = db.Column(db.Integer, default=0)
    ejemplo = db.Column(db.JSON, default={})

    # Campos para Test Bench
    score_confianza = db.Column(db.Float, default=0.0)  # 0.0 - 1.0, promedio histórico de éxito
    activa = db.Column(db.Boolean, default=True)  # Si está activa en producción
    umbral_activacion = db.Column(db.Float, default=0.9)  # Mínimo score para estar activa
    total_tests_ejecutados = db.Column(db.Integer, default=0)

    # Relaciones
    gestoria = db.relationship('Gestoria', backref='plantillas_rel')
    test_files = db.relationship('PlantillaTestFile', backref='plantilla', lazy=True, cascade='all, delete-orphan')
    test_results = db.relationship('PlantillaTestResult', backref='plantilla', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self): 
        return {
            'id': self.id, 
            'codigo': self.codigo, 
            'nombre': self.nombre, 
            'descripcion': self.descripcion, 
            'campos': self.campos if self.campos is not None else {},
            'patron_deteccion': self.patron_deteccion,
            'categoria_default': self.categoria_default,
            'prioridad_default': self.prioridad_default,
            'departamento_default': self.departamento_default,
            'gestoria_id': self.gestoria_id,
            'es_publica': self.es_publica if self.es_publica is not None else False,
            'id_original': self.id_original,
            'votos': self.votos if self.votos is not None else 0,
            'ejemplo': self.ejemplo if self.ejemplo is not None else {},
            # Test Bench
            'score_confianza': round(self.score_confianza or 0.0, 4),
            'activa': self.activa if self.activa is not None else True,
            'umbral_activacion': self.umbral_activacion or 0.9,
            'total_tests_ejecutados': self.total_tests_ejecutados or 0,
        }


class PlantillaTestFile(db.Model):
    """Archivos PDF de prueba asociados a una plantilla para el Test Bench"""
    __tablename__ = 'plantilla_test_files'
    id = db.Column(db.Integer, primary_key=True)
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantillas.id'), nullable=False)
    nombre_archivo = db.Column(db.String(255), nullable=False)
    ruta_archivo = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)  # Ej: "Factura enero 2024"
    campos_esperados = db.Column(db.JSON, default={})  # Valores esperados para validar extracción
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'plantilla_id': self.plantilla_id,
            'nombre_archivo': self.nombre_archivo,
            'descripcion': self.descripcion,
            'campos_esperados': self.campos_esperados or {},
            'fecha_subida': self.fecha_subida.isoformat() if self.fecha_subida else None,
        }


class PlantillaTestResult(db.Model):
    """Historial de resultados de ejecuciones del Test Bench"""
    __tablename__ = 'plantilla_test_results'
    id = db.Column(db.Integer, primary_key=True)
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantillas.id'), nullable=False)
    test_file_id = db.Column(db.Integer, db.ForeignKey('plantilla_test_files.id'), nullable=True)
    fecha_ejecucion = db.Column(db.DateTime, default=datetime.utcnow)
    campos_extraidos = db.Column(db.JSON, default={})  # Lo que extrajo la IA
    patron_detectado = db.Column(db.Boolean, default=False)  # Si el patrón OCR fue encontrado
    tasa_exito = db.Column(db.Float, default=0.0)  # 0.0 - 1.0
    campos_correctos = db.Column(db.Integer, default=0)
    campos_totales = db.Column(db.Integer, default=0)
    error = db.Column(db.Text, nullable=True)  # Si hubo error
    nombre_archivo = db.Column(db.String(255), nullable=True)  # Nombre del archivo testeado

    test_file = db.relationship('PlantillaTestFile', backref='resultados')

    def to_dict(self):
        return {
            'id': self.id,
            'plantilla_id': self.plantilla_id,
            'test_file_id': self.test_file_id,
            'fecha_ejecucion': self.fecha_ejecucion.isoformat() if self.fecha_ejecucion else None,
            'campos_extraidos': self.campos_extraidos or {},
            'patron_detectado': self.patron_detectado,
            'tasa_exito': round(self.tasa_exito or 0.0, 4),
            'campos_correctos': self.campos_correctos or 0,
            'campos_totales': self.campos_totales or 0,
            'error': self.error,
            'nombre_archivo': self.nombre_archivo,
        }


class TipoDocumentoConfig(db.Model):
    """
    Configuración por gestoría de cada tipo de documento predefinido.
    Los tipos de documento son perfiles de código; esta tabla guarda
    la configuración operativa (destino, departamento, notificaciones).
    """
    __tablename__ = 'tipos_documento_config'

    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    codigo = db.Column(db.String(100), nullable=False)  # ej: 'providencia_apremio'

    # Configuración operativa
    categoria_default = db.Column(db.String(100), nullable=True)   # Carpeta destino
    prioridad_default = db.Column(db.String(50), nullable=True)    # Prioridad destino
    departamento_default = db.Column(db.String(100), nullable=True) # Departamento asignado
    notificar_cliente = db.Column(db.Boolean, default=False)        # Notificar al cliente
    activo = db.Column(db.Boolean, default=True)                    # Si está activo
    boundary_tags = db.Column(db.JSON, default=[])                  # Stop words para la extracción

    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    gestoria = db.relationship('Gestoria', backref='tipos_documento_config')

    __table_args__ = (
        db.UniqueConstraint('gestoria_id', 'codigo', name='uq_gestoria_tipo_documento'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'gestoria_id': self.gestoria_id,
            'codigo': self.codigo,
            'categoria_default': self.categoria_default or '',
            'prioridad_default': self.prioridad_default or '',
            'departamento_default': self.departamento_default or '',
            'notificar_cliente': self.notificar_cliente or False,
            'activo': self.activo if self.activo is not None else True,
            'boundary_tags': self.boundary_tags or [],
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
        }



class GrupoEmpresa(db.Model):
    """Modelo para agrupaciones de empresas (Holdings)"""
    __tablename__ = 'grupos_empresas'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    email_notificaciones = db.Column(db.String(200))
    usar_email_grupo = db.Column(db.Boolean, default=False)  # Si enviar aquí en lugar de a la empresa
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación backref de empresas está implícita en Empresa
    # empresa.grupo y grupo.empresas
    empresas_rel = db.relationship('Empresa', backref='grupo', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'email_notificaciones': self.email_notificaciones,
            'usar_email_grupo': self.usar_email_grupo,
            'gestoria_id': self.gestoria_id,
            'num_empresas': len(self.empresas_rel),
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }

class Empresa(db.Model):
    __tablename__ = 'empresas'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False, unique=True)
    nif = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(200)) 
    emails_extra = db.Column(db.JSON, default=[]) 
    cuenta_cotizacion = db.Column(db.String(50))  # Número de cuenta de cotización
    saltra_cert_secret = db.Column(db.String(255))  # Cert-Secret de Saltra para DEHU
    estado = db.Column(db.String(50), default='Abierto')
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)  # Multi-tenant
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_empresas.id'), nullable=True)  # Agrupación (Holding)
    activa = db.Column(db.Boolean, default=True)  # Estado de la empresa
    
    # Nuevos campos para importación expandida
    codigo_empresa = db.Column(db.String(50))  # Código interno de la empresa (único por gestoría)
    telefono = db.Column(db.String(20))  # Teléfono de contacto
    nombre_administrador = db.Column(db.String(200))  # Nombre del administrador
    direcciones_sociedad = db.Column(db.JSON, default=[])  # Lista de direcciones de la sociedad
    direcciones_centros_trabajo = db.Column(db.JSON, default=[])  # Lista de direcciones de centros de trabajo
    epigrafes_iae = db.Column(db.JSON, default=[])  # Lista de epígrafes IAE
    cnaes_2009 = db.Column(db.JSON, default=[])  # Lista de códigos CNAE 2009
    cnaes_2025 = db.Column(db.JSON, default=[])  # Lista de códigos CNAE 2025
    administradores = db.Column(db.JSON, default=[])  # Lista de objetos {"nombre": "...", "cif": "..."}
    
    # Nuevos campos planos para importación/edición (Fase Excel Expandida)
    apellido_administrador = db.Column(db.String(200))
    nif_administrador = db.Column(db.String(20))
    provincia = db.Column(db.String(100))
    municipio = db.Column(db.String(100))
    codigo_postal = db.Column(db.String(20))
    direccion = db.Column(db.String(500))
    direccion_centros_trabajo_str = db.Column(db.String(500))
    convenio_numero = db.Column(db.String(50))
    convenio_nombre = db.Column(db.String(200))
    epigrafe_iae_str = db.Column(db.String(100))
    cnae_2009_str = db.Column(db.String(20))
    cnae_2025_str = db.Column(db.String(20))
    
    def to_dict_simple(self): 
        return {
            'id': self.id, 
            'nombre': self.nombre, 
            'nif': self.nif, 
            'email': self.email, 
            'emails_extra': self.emails_extra or [],
            'cuenta_cotizacion': self.cuenta_cotizacion,
            # 'saltra_cert_secret': self.saltra_cert_secret, # 🔒 Ocultado por seguridad
            'codigo_empresa': self.codigo_empresa,
            'telefono': self.telefono,
            'nombre_administrador': self.nombre_administrador,
            'direcciones_sociedad': self.direcciones_sociedad or [],
            'direcciones_centros_trabajo': self.direcciones_centros_trabajo or [],
            'epigrafes_iae': self.epigrafes_iae or [],
            'cnaes_2009': self.cnaes_2009 or [],
            'cnaes_2025': self.cnaes_2025 or [],
            'administradores': self.administradores or [],
            
            # Nuevos campos expuestos
            'apellido_administrador': self.apellido_administrador,
            'nif_administrador': self.nif_administrador,
            'provincia': self.provincia,
            'municipio': self.municipio,
            'codigo_postal': self.codigo_postal,
            'direccion': self.direccion,
            'direccion_centros_trabajo_str': self.direccion_centros_trabajo_str,
            'convenio_numero': self.convenio_numero,
            'convenio_nombre': self.convenio_nombre,
            'epigrafe_iae_str': self.epigrafe_iae_str,
            'cnae_2009_str': self.cnae_2009_str,
            'cnae_2025_str': self.cnae_2025_str,
            
            'activa': self.activa,
            'grupo_id': self.grupo_id,
            'grupo_nombre': self.grupo.nombre if self.grupo else None
        }

class Empleado(db.Model):
    __tablename__ = 'empleados'
    id = db.Column(db.Integer, primary_key=True)
    nif = db.Column(db.String(20), nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- Nuevos campos técnicos (IDC) ---
    nss = db.Column(db.String(20), nullable=True)
    fecha_alta = db.Column(db.Date, nullable=True)
    grupo_cotizacion = db.Column(db.String(10), nullable=True)
    tipo_contrato = db.Column(db.String(10), nullable=True)
    parcialidad = db.Column(db.String(20), nullable=True) # % de jornada
    ccc = db.Column(db.String(20), nullable=True) 
    
    # Restricción: Un NIF único por empresa (un empleado puede trabajar en 2 empresas distintas)
    __table_args__ = (
        db.UniqueConstraint('nif', 'empresa_id', name='uq_nif_empresa'),
    )
    
    empresa_rel = db.relationship('Empresa', backref='empleados')

    def to_dict(self):
        return {
            'id': self.id,
            'nif': self.nif,
            'nombre': self.nombre,
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa_rel.nombre if self.empresa_rel else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'nss': self.nss,
            'fecha_alta': self.fecha_alta.isoformat() if self.fecha_alta else None,
            'grupo_cotizacion': self.grupo_cotizacion,
            'tipo_contrato': self.tipo_contrato,
            'parcialidad': self.parcialidad,
            'ccc': self.ccc
        }

class AliasNIF(db.Model):
    __tablename__ = 'alias_nif'
    id = db.Column(db.Integer, primary_key=True)
    nif = db.Column(db.String(30), nullable=False, unique=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    empresa = db.relationship('Empresa', backref='alias_nifs')

class ConfiguracionPerfil(db.Model):
    """Configuración específica de cada gestoría para los perfiles de sistema"""
    __tablename__ = 'configuracion_perfiles'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    perfil_clave = db.Column(db.String(100), nullable=False)  # Clave única del perfil (ej: 'ProvidenciaApremioProfile')
    
    # Configuración de destino
    categoria = db.Column(db.String(50), nullable=True)     # DocumentCategories
    prioridad_default = db.Column(db.String(50), nullable=True) # Prioridad destino
    departamento = db.Column(db.String(100), nullable=True) # Departments
    notificar_cliente = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    
    mapeo_lineas = db.Column(db.JSON, default={})
    
    # ⭐ NUEVO: Etiquetas de límite (STOP WORDS) para evitar sangrado
    boundary_tags = db.Column(db.JSON, default=[])
    
    # Auditoría
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    actualizado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    __table_args__ = (
        db.UniqueConstraint('gestoria_id', 'perfil_clave', name='uq_gestoria_perfil'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'gestoria_id': self.gestoria_id,
            'perfil_clave': self.perfil_clave,
            'categoria': self.categoria,
            'prioridad_default': self.prioridad_default,
            'departamento': self.departamento,
            'notificar_cliente': self.notificar_cliente,
            'activo': self.activo,
            'mapeo_lineas': self.mapeo_lineas or {},
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None
        }

class Documento(db.Model):
    __tablename__ = 'documentos'
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)  # Multi-tenant
    categoria = db.Column(db.String(100), default='Notificaciones') 
    nombre_archivo = db.Column(db.String(500), nullable=False)
    ruta_archivo = db.Column(db.String(1000), nullable=False)
    procesado = db.Column(db.Boolean, default=False)
    fecha_procesado = db.Column(db.DateTime)
    datos_extraidos = db.Column(db.JSON)
    fecha_plazo = db.Column(db.DateTime)
    estado_tarea = db.Column(db.String(100)) 
    asignado_a_id = db.Column(db.Integer, db.ForeignKey('users.id')) 
    email_enviado = db.Column(db.Boolean, default=False)
    fecha_envio = db.Column(db.DateTime)
    guardado = db.Column(db.Boolean, default=False)
    file_hash = db.Column(db.String(64), index=True)
    
    # ✅ NUEVOS CAMPOS DE LECTURA
    leido = db.Column(db.Boolean, default=False)
    fecha_lectura = db.Column(db.DateTime)
    leido_por_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    importe = db.Column(db.Float)
    importe_pagar = db.Column(db.Numeric(10, 2))  # Importe extraído de RLC
    periodo = db.Column(db.String(6))  # Periodo en formato YYYYMM (ej: 202412)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    texto_ocr = db.Column(db.Text, nullable=True)  # Texto completo extraído del PDF para búsqueda
    
    # ⭐ PRIORIDADES PARA KANBAN
    # Valores: 'informativa', 'importante', 'urgente'
    prioridad = db.Column(db.String(20), default='informativa') 


    
    # Relationships
    empresa = db.relationship('Empresa', backref='documentos')
    asignado_a = db.relationship('User', foreign_keys=[asignado_a_id], backref='documentos_asignados')
    leido_por = db.relationship('User', foreign_keys=[leido_por_id], backref='documentos_leidos')
    
    def to_dict(self): 
        return {
            'id': self.id, 
            'empresa_id': self.empresa_id, 
            'categoria': self.categoria, 
            'nombre_archivo': self.nombre_archivo, 
            'procesado': self.procesado, 
            'datos_extraidos': self.datos_extraidos, 
            'email_enviado': self.email_enviado, 
            'guardado': self.guardado,
            # ✅ NUEVOS CAMPOS
            'leido': self.leido,
            'fecha_lectura': self.fecha_lectura.isoformat() if self.fecha_lectura else None,
            'leido_por': self.leido_por.nombre if self.leido_por else None,
            'leido_por_id': self.leido_por_id,
            'fecha_plazo': self.fecha_plazo.isoformat() if self.fecha_plazo else None, 
            'estado_tarea': self.estado_tarea, 
            'asignado_a_id': self.asignado_a_id,
            'asignado_a': self.asignado_a.nombre if self.asignado_a else None,
            'periodo': self.periodo,  # Periodo YYYYMM
            'fecha_creacion': self.fecha_creacion.isoformat(),
            'prioridad': self.prioridad or 'informativa',
            'grupos': [item.grupo.to_dict() for item in self.grupos_items if item.grupo]
        }


# ✅ MODELO DE AUDITORÍA
class AuditoriaLog(db.Model):
    """
    Sistema de auditoría completo para rastrear todos los movimientos
    """
    __tablename__ = 'auditoria_logs'
    id = db.Column(db.Integer, primary_key=True)
    
    # Usuario que realizó la acción
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user_email = db.Column(db.String(150))
    user_nombre = db.Column(db.String(150))
    
    # Multi-tenant: Gestoría
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True, index=True)
    
    # Acción realizada
    accion = db.Column(db.String(100), nullable=False)
    entidad_tipo = db.Column(db.String(50))
    entidad_id = db.Column(db.Integer)
    
    # Detalles
    descripcion = db.Column(db.String(500))
    detalles = db.Column(db.JSON)
    
    # Metadatos
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    metodo_http = db.Column(db.String(10))
    endpoint = db.Column(db.String(255))
    
    # Timestamps
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship('User', backref='logs_auditoria')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'user_nombre': self.user_nombre,
            'accion': self.accion,
            'entidad_tipo': self.entidad_tipo,
            'entidad_id': self.entidad_id,
            'descripcion': self.descripcion,
            'detalles': self.detalles,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'metodo_http': self.metodo_http,
            'endpoint': self.endpoint,
            'fecha_creacion': self.fecha_creacion.isoformat()
        }
    
class FiniquitoLinea(db.Model):
    __tablename__ = 'finiquito_lineas'
    
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=False)
    
    # Datos de la tabla
    importe_principal = db.Column(db.Float, nullable=True)
    recargo_apremio = db.Column(db.Float, nullable=True)
    importe_total_deuda = db.Column(db.Float, nullable=True)
    importe_intereses = db.Column(db.Float, nullable=True)
    importe_total_plazo = db.Column(db.Float, nullable=True)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    
    # Estado de pago
    estado = db.Column(db.String(20), default='pendiente')  # 'pendiente' o 'pagado'
    fecha_pago = db.Column(db.Date, nullable=True)  # Cuando se marcó como pagado
    
    # Metadata
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
 # Campos para recordatorios
    ultimo_recordatorio_enviado = db.Column(db.DateTime)
    recordatorios_count = db.Column(db.Integer, default=0)
    confirmado_por_email = db.Column(db.Boolean, default=False)
    token_confirmacion = db.Column(db.String(200))
    
    # Relación
    documento = db.relationship('Documento', backref=db.backref('finiquito_lineas', lazy=True, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'documento_id': self.documento_id,
            'importe_principal': self.importe_principal,
            'recargo_apremio': self.recargo_apremio,
            'importe_total_deuda': self.importe_total_deuda,
            'importe_intereses': self.importe_intereses,
            'importe_total_plazo': self.importe_total_plazo,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'estado': self.estado,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
    
class RecordatorioPago(db.Model):
    """Modelo para registrar el historial de recordatorios enviados"""
    __tablename__ = 'recordatorio_pago'
    
    id = db.Column(db.Integer, primary_key=True)
    finiquito_linea_id = db.Column(db.Integer, db.ForeignKey('finiquito_lineas.id'), nullable=False)
    fecha_envio = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    tipo_recordatorio = db.Column(db.String(20))  # '7_dias', '3_dias', 'vencimiento', 'mora'
    email_enviado_a = db.Column(db.String(200))
    estado = db.Column(db.String(20), default='enviado')  # 'enviado', 'confirmado', 'ignorado'
    fecha_respuesta = db.Column(db.DateTime)
    
    # Relación
    linea = db.relationship('FiniquitoLinea', backref='recordatorios')
    
    def to_dict(self):
        return {
            'id': self.id,
            'finiquito_linea_id': self.finiquito_linea_id,
            'fecha_envio': self.fecha_envio.isoformat() if self.fecha_envio else None,
            'tipo_recordatorio': self.tipo_recordatorio,
            'email_enviado_a': self.email_enviado_a,
            'estado': self.estado,
            'fecha_respuesta': self.fecha_respuesta.isoformat() if self.fecha_respuesta else None
        }
    
class FiniquitoLaboral(db.Model):
    """Modelo para finiquitos laborales (indemnizaciones, liquidaciones de empleados)"""
    __tablename__ = 'finiquito_laboral'
    
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=False, unique=True)
    
    # Datos del trabajador
    nombre_trabajador = db.Column(db.String(200))
    nif_trabajador = db.Column(db.String(20))
    categoria = db.Column(db.String(100))
    
    # Motivo
    motivo_baja = db.Column(db.String(500))
    
    # Importes
    total_devengos = db.Column(db.Float, default=0)
    total_deducciones = db.Column(db.Float, default=0)
    importe_liquido = db.Column(db.Float, default=0)
    
    # Desglose en JSON
    conceptos_devengos = db.Column(db.JSON, default=[])  # [{"concepto": "Salario Base", "importe": 62.31}]
    conceptos_deducciones = db.Column(db.JSON, default=[])  # [{"concepto": "COTIZ.CC", "importe": 3.51}]
    
    # Estado de pago
    estado = db.Column(db.String(20), default='pendiente')  # 'pendiente' o 'pagado'
    fecha_pago = db.Column(db.Date, nullable=True)
    
    # Metadata
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relación
    documento = db.relationship('Documento', backref=db.backref('finiquito_laboral', uselist=False, cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'documento_id': self.documento_id,
            'nombre_trabajador': self.nombre_trabajador,
            'nif_trabajador': self.nif_trabajador,
            'categoria': self.categoria,
            'motivo_baja': self.motivo_baja,
            'total_devengos': self.total_devengos,
            'total_deducciones': self.total_deducciones,
            'importe_liquido': self.importe_liquido,
            'conceptos_devengos': self.conceptos_devengos or [],
            'conceptos_deducciones': self.conceptos_deducciones or [],
            'estado': self.estado,
            'fecha_pago': self.fecha_pago.isoformat() if self.fecha_pago else None,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }


# Campo adicional en Documento para identificar tipo
# Agregar esta migración o campo:
# tipo_finiquito = db.Column(db.String(20))  # 'fiscal' o 'laboral'
class GrupoDocumentos(db.Model):
    """Grupo de documentos relacionados (expediente)"""
    __tablename__ = 'grupo_documentos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)  # ← CAMBIO: empresas.id
    color = db.Column(db.String(20), default='blue')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # ← CAMBIO: users.id
    
    # Relaciones
    empresa = db.relationship('Empresa', backref='grupos_documentos')
    creador = db.relationship('User', foreign_keys=[created_by])
    items = db.relationship('GrupoDocumentosItem', backref='grupo', cascade='all, delete-orphan', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'empresa_id': self.empresa_id,
            'color': self.color,
            'total_documentos': self.items.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }
    
    def to_dict_full(self):
        """Incluye la lista de documentos"""
        data = self.to_dict()
        data['documentos'] = [item.documento.to_dict() for item in self.items if item.documento]
        return data


class GrupoDocumentosItem(db.Model):
    """Relación entre grupo y documento"""
    __tablename__ = 'grupo_documentos_items'
    
    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupo_documentos.id'), nullable=False)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=False)  # ← CAMBIO: documentos.id
    agregado_at = db.Column(db.DateTime, default=datetime.utcnow)
    agregado_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # ← CAMBIO: users.id
    
    # Relaciones
    documento = db.relationship('Documento', backref='grupos_items')
    agregador = db.relationship('User', foreign_keys=[agregado_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'grupo_id': self.grupo_id,
            'documento_id': self.documento_id,
            'agregado_at': self.agregado_at.isoformat() if self.agregado_at else None,
            'agregado_by': self.agregado_by
        }

class Conversacion(db.Model):
    """Conversaciones de chat con IA"""
    __tablename__ = 'conversaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    titulo = db.Column(db.String(200))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    mensajes = db.relationship('MensajeChat', backref='conversacion', lazy='dynamic', cascade='all, delete-orphan', order_by='MensajeChat.fecha_creacion')
    usuario = db.relationship('User', backref='conversaciones')
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            'num_mensajes': self.mensajes.count()
        }
class MensajeChat(db.Model):
    """Mensajes individuales de chat"""
    __tablename__ = 'mensajes_chat'
    
    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(db.Integer, db.ForeignKey('conversaciones.id'), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    tokens_usados = db.Column(db.Integer)
    tiempo_respuesta = db.Column(db.Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'rol': self.rol,
            'contenido': self.contenido,
            'fecha': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'tokens_usados': self.tokens_usados,
            'tiempo_respuesta': self.tiempo_respuesta
        }

class RespuestaCache(db.Model):
    """Caché de respuestas del chat IA"""
    __tablename__ = 'respuestas_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    pregunta = db.Column(db.Text, nullable=False)
    respuesta = db.Column(db.Text, nullable=False)
    contexto_hash = db.Column(db.String(64))
    hits = db.Column(db.Integer, default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_ultimo_uso = db.Column(db.DateTime, default=datetime.utcnow)
    ttl_expiracion = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'pregunta': self.pregunta,
            'hits': self.hits,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_ultimo_uso': self.fecha_ultimo_uso.isoformat() if self.fecha_ultimo_uso else None
        }


class ApiKeyUsage(db.Model):
    """Tracking de uso diario de API keys de Gemini"""
    __tablename__ = 'api_key_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    key_name = db.Column(db.String(50), nullable=False)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    requests_count = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    tokens_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con Gestoría
    gestoria = db.relationship('Gestoria', backref='api_usage')
    
    __table_args__ = (
        db.UniqueConstraint('key_name', 'gestoria_id', 'date', name='uq_key_gestoria_date'),
    )
    
    def to_dict(self):
        total_calls = self.requests_count + self.errors_count
        return {
            'id': self.id,
            'key_name': self.key_name,
            'gestoria_id': self.gestoria_id,
            'date': self.date.isoformat(),
            'requests_count': self.requests_count,
            'errors_count': self.errors_count,
            'tokens_used': self.tokens_used,
            'success_rate': round((self.requests_count / total_calls * 100), 2) if total_calls > 0 else 100,
            'usage_percent': round((total_calls / 20 * 100), 2)  # Límite de 20 req/día
        }


# ============================================
# SISTEMA DE SOPORTE
# ============================================

class TicketSoporte(db.Model):
    """Modelo para tickets de soporte al cliente"""
    __tablename__ = 'tickets_soporte'
    
    id = db.Column(db.Integer, primary_key=True)
    numero_ticket = db.Column(db.String(20), unique=True, nullable=False)  # TKT-2024-001
    
    # Relaciones
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'))  # Nullable - opcional
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)  # Multi-tenant
    usuario_creador_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    asignado_a_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Información del ticket
    asunto = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))  # Bug, Consulta, Mejora, Urgente
    prioridad = db.Column(db.String(20), default='Media')  # Baja, Media, Alta, Urgente
    estado = db.Column(db.String(20), default='Abierto')  # Abierto, En Proceso, Resuelto, Cerrado
    
    # Fechas
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fecha_asignacion = db.Column(db.DateTime)  # ⭐ Cuándo se asignó el ticket
    fecha_resolucion = db.Column(db.DateTime)
    
    # Cierre y valoración
    valoracion = db.Column(db.Integer)  # 1-5 estrellas
    comentario_cierre = db.Column(db.Text)
    
    # Relationships
    empresa = db.relationship('Empresa', backref='tickets_soporte')
    gestoria = db.relationship('Gestoria', backref='tickets_soporte')
    usuario_creador = db.relationship('User', foreign_keys=[usuario_creador_id], backref='tickets_creados')
    asignado_a = db.relationship('User', foreign_keys=[asignado_a_id], backref='tickets_asignados')
    mensajes = db.relationship('MensajeSoporte', backref='ticket', cascade='all, delete-orphan', order_by='MensajeSoporte.fecha_creacion')
    
    @staticmethod
    def generar_numero_ticket():
        """Genera número único de ticket: TKT-YYYY-NNN"""
        año_actual = datetime.now().year
        ultimo_ticket = TicketSoporte.query.filter(
            TicketSoporte.numero_ticket.like(f'TKT-{año_actual}-%')
        ).order_by(TicketSoporte.id.desc()).first()
        
        if ultimo_ticket:
            ultimo_num = int(ultimo_ticket.numero_ticket.split('-')[-1])
            nuevo_num = ultimo_num + 1
        else:
            nuevo_num = 1
        
        return f'TKT-{año_actual}-{str(nuevo_num).zfill(3)}'
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero_ticket': self.numero_ticket,
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'gestoria_id': self.gestoria_id,
            'gestoria_nombre': self.gestoria.nombre if self.gestoria else None,
            'usuario_creador_id': self.usuario_creador_id,
            'usuario_creador_nombre': self.usuario_creador.nombre if self.usuario_creador else None,
            'asignado_a_id': self.asignado_a_id,
            'asignado_a_nombre': self.asignado_a.nombre if self.asignado_a else None,
            'asunto': self.asunto,
            'descripcion': self.descripcion,
            'categoria': self.categoria,
            'prioridad': self.prioridad,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_actualizacion': self.fecha_actualizacion.isoformat() if self.fecha_actualizacion else None,
            'fecha_resolucion': self.fecha_resolucion.isoformat() if self.fecha_resolucion else None,
            'valoracion': self.valoracion,
            'comentario_cierre': self.comentario_cierre,
            'mensajes_count': len(self.mensajes) if self.mensajes else 0,
            'mensajes_sin_leer': sum(1 for m in self.mensajes if not m.leido and m.usuario_id != self.usuario_creador_id)
        }


class MensajeSoporte(db.Model):
    """Modelo para mensajes dentro de tickets de soporte"""
    __tablename__ = 'mensajes_soporte'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets_soporte.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    mensaje = db.Column(db.Text, nullable=False)
    es_interno = db.Column(db.Boolean, default=False)  # Notas internas del equipo
    es_respuesta_soporte = db.Column(db.Boolean, default=False)  # ⭐ Mensaje del equipo de soporte
    es_mensaje_sistema = db.Column(db.Boolean, default=False)  # ⭐ Mensaje automático del sistema
    adjuntos = db.Column(db.JSON)  # [{nombre: '', ruta: ''}]
    leido = db.Column(db.Boolean, default=False)
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    usuario = db.relationship('User', backref='mensajes_soporte')
    
    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'usuario_id': self.usuario_id,
            'usuario_nombre': self.usuario.nombre if self.usuario else None,
            'usuario_rol': self.usuario.departamento.nombre if (self.usuario and self.usuario.departamento) else None,
            'mensaje': self.mensaje,
            'es_interno': self.es_interno,
            'es_respuesta_soporte': self.es_respuesta_soporte,  # ⭐ NUEVO
            'es_mensaje_sistema': self.es_mensaje_sistema,  # ⭐ NUEVO
            'adjuntos': self.adjuntos,
            'leido': self.leido,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }
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

class UserPermiso(db.Model):
    """Permisos individuales asignados directamente a usuarios"""
    __tablename__ = 'user_permisos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permisos.id', ondelete='CASCADE'), nullable=False)
    asignado_por = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    fecha_asignacion = db.Column(db.DateTime, default=datetime.utcnow)
    notas = db.Column(db.Text)
    
    # Relaciones
    user = db.relationship('User', foreign_keys=[user_id], backref='permisos_individuales')
    permiso = db.relationship('Permiso')
    asignador = db.relationship('User', foreign_keys=[asignado_por])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'permiso_id': self.permiso_id,
            'permiso_codigo': self.permiso.codigo if self.permiso else None,
            'permiso_nombre': self.permiso.nombre if self.permiso else None,
            'asignado_por': self.asignador.nombre if self.asignador else None,
            'fecha_asignacion': self.fecha_asignacion.isoformat() if self.fecha_asignacion else None,
            'notas': self.notas
        }


class Tarea(db.Model):
    """Modelo de tareas para gestión"""
    __tablename__ = 'tareas'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Relaciones
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=True)  # MULTI-TENANT
    asignado_a_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documentos.id'), nullable=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=True)
    
    # Tracking - Nuevos campos
    origen = db.Column(db.String(50), default='manual')  # manual, chat_ia, auto_asignada, importada, calendario, documento
    creado_por_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notas = db.Column(db.Text, nullable=True)  # Notas internas adicionales
    tags = db.Column(db.JSON, nullable=True)  # Array de tags: ["urgente", "fiscal"]
    conversacion_id = db.Column(db.Integer, nullable=True)  # ID de conversación IA (sin FK hasta que exista la tabla)
    
    # Estado y prioridad
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, en_progreso, completada, cancelada
    prioridad = db.Column(db.String(10), default='media')  # alta, media, baja
    
    # Fechas
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.DateTime, nullable=True)
    fecha_completada = db.Column(db.DateTime, nullable=True)
    
    # Auditoría
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones inversas
    gestoria = db.relationship('Gestoria', backref='tareas')
    asignado_a = db.relationship('User', backref='tareas_asignadas', foreign_keys=[asignado_a_id])
    documento = db.relationship('Documento', backref='tareas')
    empresa = db.relationship('Empresa', backref='tareas')
    creado_por = db.relationship('User', backref='tareas_creadas', foreign_keys=[creado_por_id])
    # conversacion = db.relationship('ConversacionIA', backref='tareas_generadas', foreign_keys=[conversacion_id])  # Descomentar cuando exista el modelo
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'asignado_a_id': self.asignado_a_id,
            'asignado_a': self.asignado_a.nombre if self.asignado_a else None,
            'documento_id': self.documento_id,
            'documento_categoria': self.documento.categoria if self.documento else None,  # ⭐ Para redirigir a carpeta correcta
            'empresa_id': self.empresa_id,
            'empresa': self.empresa.nombre if self.empresa else None,
            'estado': self.estado,
            'prioridad': self.prioridad,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_vencimiento': self.fecha_vencimiento.isoformat() if self.fecha_vencimiento else None,
            'fecha_completada': self.fecha_completada.isoformat() if self.fecha_completada else None,
            # Tracking fields
            'origen': self.origen,
            'creado_por_id': self.creado_por_id,
            'creado_por': self.creado_por.nombre if self.creado_por else None,
            'notas': self.notas,
            'tags': self.tags,
            'conversacion_id': self.conversacion_id
        }
    
    def __repr__(self):
        return f'<UserPermiso user={self.user_id} permiso={self.permiso_id}>'


class FechaTributaria(db.Model):
    """
    Fechas importantes del calendario tributario de la AEAT
    """
    __tablename__ = 'fechas_tributarias'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Información de la fecha
    fecha = db.Column(db.Date, nullable=False, index=True)
    titulo = db.Column(db.String(500), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Categorización
    tipo_impuesto = db.Column(db.String(100))  # IVA, IRPF, Sociedades, etc.
    modelo = db.Column(db.String(50))  # 303, 111, 190, etc.
    periodicidad = db.Column(db.String(50))  # Mensual, Trimestral, Anual
    
    # Metadatos
    año = db.Column(db.Integer, nullable=False, index=True)
    mes = db.Column(db.Integer)
    trimestre = db.Column(db.Integer)
    
    # Control de sincronización
    fuente_url = db.Column(db.String(500))  # URL de donde se obtuvo
    fecha_sincronizacion = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'titulo': self.titulo,
            'descripcion': self.descripcion,
            'tipo_impuesto': self.tipo_impuesto,
            'modelo': self.modelo,
            'periodicidad': self.periodicidad,
            'año': self.año,
            'mes': self.mes,
            'trimestre': self.trimestre,
            'fuente_url': self.fuente_url,
            'fecha_sincronizacion': self.fecha_sincronizacion.isoformat() if self.fecha_sincronizacion else None,
            'activo': self.activo
        }
    
    def __repr__(self):
        return f'<FechaTributaria {self.fecha} - {self.titulo[:50]}>'


class UserEmpresaAcceso(db.Model):
    """Tabla de asociación para vincular usuarios con empresas específicas (Invitados)"""
    __tablename__ = 'user_empresa_acceso'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id', ondelete='CASCADE'), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref=db.backref('empresa_accesos', cascade='all, delete-orphan'))
    empresa = db.relationship('Empresa', backref=db.backref('user_accesos', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<UserEmpresaAcceso u={self.user_id} e={self.empresa_id}>'


class UserGrupoAcceso(db.Model):
    """Tabla de asociación para vincular usuarios con grupos (Holdings)"""
    __tablename__ = 'user_grupo_acceso'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_empresas.id', ondelete='CASCADE'), nullable=False)
    es_admin_grupo = db.Column(db.Boolean, default=False)  # ⭐ Si puede gestionar accesos del grupo
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    user = db.relationship('User', backref=db.backref('grupo_accesos', cascade='all, delete-orphan'))
    grupo = db.relationship('GrupoEmpresa', backref=db.backref('user_accesos', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<UserGrupoAcceso u={self.user_id} g={self.grupo_id}>'



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
    certificados_max = db.Column(db.Integer, default=5)
    soporte_nivel = db.Column(db.String(50))
    permite_branding = db.Column(db.Boolean, default=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Nota: La relación 'suscripciones' se define en models_billing.py via backref
    # No duplicar aquí para evitar errores de importación circular
    
    # Propiedades calculadas para compatibilidad con sistema de facturación
    @property
    def codigo(self):
        """Código del plan (basado en nombre)"""
        return self.nombre.lower()
    
    @property
    def precio_anual(self):
        """Precio anual con 17% descuento"""
        return float(self.precio_mensual) * 12 * 0.83
    
    @property
    def max_usuarios(self):
        return self.usuarios_max
    
    @property
    def max_empresas(self):
        return self.empresas_max
    
    @property
    def max_storage_gb(self):
        return self.almacenamiento_gb
    
    @property
    def max_tokens_mes(self):
        return self.tokens_ia_mes

    @property
    def max_certificados(self):
        return self.certificados_max
    
    @property
    def features(self):
        """Features del plan"""
        return {
            'smtp_personalizado': self.nombre.lower() in ['premium', 'plus'],
            'api_access': self.nombre.lower() in ['premium', 'plus']
        }
    
    @property
    def orden(self):
        """Orden de visualización"""
        orden_map = {'basico': 1, 'plus': 2, 'premium': 3}
        return orden_map.get(self.nombre.lower(), 0)
    
    def to_dict(self):
        """Serialización para API (compatible con sistema de facturación)"""
        return {
            'id': self.id,
            'codigo': self.codigo,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio_mensual': float(self.precio_mensual),
            'precio_anual': self.precio_anual,
            'max_usuarios': self.max_usuarios,
            'max_empresas': self.max_empresas,
            'max_storage_gb': self.max_storage_gb,
            'max_tokens_mes': self.max_tokens_mes,
            'max_certificados': self.max_certificados,
            'max_requests_dia': None,
            'features': self.features,
            'activo': self.activo,
            'orden': self.orden
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


class PlanHistorial(db.Model):
    """Historial de cambios en planes"""
    __tablename__ = 'planes_historial'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes_gestoria.id', ondelete='CASCADE'), nullable=False)
    campo_modificado = db.Column(db.String(50), nullable=False)
    valor_anterior = db.Column(db.Text)
    valor_nuevo = db.Column(db.Text)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    fecha_cambio = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.Text)
    
    # Relaciones
    plan = db.relationship('PlanGestoria', backref='historial')
    usuario = db.relationship('User', backref='cambios_planes')
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'plan_nombre': self.plan.nombre if self.plan else None,
            'campo_modificado': self.campo_modificado,
            'valor_anterior': self.valor_anterior,
            'valor_nuevo': self.valor_nuevo,
            'usuario_id': self.usuario_id,
            'usuario_nombre': self.usuario.nombre if self.usuario else 'Sistema',
            'fecha_cambio': self.fecha_cambio.isoformat() if self.fecha_cambio else None,
            'motivo': self.motivo
        }


# Modelo para configuración del sistema
class SystemConfig(db.Model):
    """
    Modelo para almacenar configuración global del sistema
    Incluye modo de mantenimiento y otras configuraciones
    """
    __tablename__ = 'system_config'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationship
    
    @staticmethod
    def get_value(key, default=None):
        """
        Obtiene el valor de una configuración
        
        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe
            
        Returns:
            Valor de la configuración o default
        """
        config = SystemConfig.query.filter_by(key=key).first()
        return config.value if config else default
    
    @staticmethod
    def set_value(key, value, user_id=None):
        """
        Establece el valor de una configuración
        
        Args:
            key: Clave de configuración
            value: Nuevo valor
            user_id: ID del usuario que realiza el cambio
        """
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
            config.updated_at = datetime.utcnow()
            config.updated_by = user_id
        else:
            config = SystemConfig(
                key=key,
                value=value,
                updated_by=user_id
            )
            db.session.add(config)
        db.session.commit()
    
    @staticmethod
    def is_maintenance_mode():
        """
        Verifica si el sistema está en modo de mantenimiento
        
        Returns:
            True si está en mantenimiento, False en caso contrario
        """
        value = SystemConfig.get_value('maintenance_mode', 'false')
        return value.lower() == 'true'
    
    @staticmethod
    def get_maintenance_message():
        """
        Obtiene el mensaje de mantenimiento actual
        
        Returns:
            Mensaje de mantenimiento
        """
        return SystemConfig.get_value(
            'maintenance_message',
            'El sistema está en mantenimiento. Volveremos pronto.'
        )
    
    def to_dict(self):
        """Convierte el objeto a diccionario"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }


class NotificationPreferences(db.Model):
    """Preferencias de notificaciones push del navegador por usuario"""
    __tablename__ = 'notification_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Preferencias por tipo de notificación
    documentos_procesados = db.Column(db.Boolean, default=True)
    errores_procesamiento = db.Column(db.Boolean, default=True)
    vencimientos = db.Column(db.Boolean, default=True)
    tareas_asignadas = db.Column(db.Boolean, default=True)
    respuestas_soporte = db.Column(db.Boolean, default=False)
    mantenimiento = db.Column(db.Boolean, default=True)
    
    # Configuración general
    enabled = db.Column(db.Boolean, default=True)
    sound_enabled = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación
    user = db.relationship('User', backref=db.backref('notification_prefs', uselist=False))
    
    def to_dict(self):
        return {
            'enabled': self.enabled,
            'sound_enabled': self.sound_enabled,
            'documentos_procesados': self.documentos_procesados,
            'errores_procesamiento': self.errores_procesamiento,
            'vencimientos': self.vencimientos,
            'tareas_asignadas': self.tareas_asignadas,
            'respuestas_soporte': self.respuestas_soporte,
            'mantenimiento': self.mantenimiento
        }
# ==========================================
# PUSH NOTIFICATIONS
# ==========================================
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

class ScheduledNotification(db.Model):
    """Notificaciones programadas para documentos"""
    __tablename__ = 'scheduled_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documentos.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'deadline_7days', 'deadline_1day', 'custom'
    scheduled_date = db.Column(db.DateTime, nullable=False, index=True)
    sent = db.Column(db.Boolean, default=False, index=True)
    custom_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    # Relaciones
    document = db.relationship('Documento', backref=db.backref('scheduled_notifications', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('scheduled_notifications', lazy=True))
    
    def __repr__(self):
        return f'<ScheduledNotification {self.id} - Doc {self.document_id} - {self.notification_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'user_id': self.user_id,
            'notification_type': self.notification_type,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'sent': self.sent,
            'custom_message': self.custom_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }

class TareaNomina(db.Model):
    """Historial de procesamiento de nóminas"""
    __tablename__ = 'tareas_nominas'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    filename = db.Column(db.String(500))
    status = db.Column(db.String(50), default='PENDING')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    total_empresas = db.Column(db.Integer)
    total_trabajadores = db.Column(db.Integer)
    periodo = db.Column(db.String(10))
    error_message = db.Column(db.Text)
    
    # Relaciones
    user = db.relationship('User', backref='tareas_nominas')
    gestoria = db.relationship('Gestoria', backref='tareas_nominas')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'filename': self.filename,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_empresas': self.total_empresas,
            'total_trabajadores': self.total_trabajadores,
            'periodo': self.periodo,
            'error_message': self.error_message
        }


class TareaSeguros(db.Model):
    """Historial de procesamiento de seguros sociales"""
    __tablename__ = 'tareas_seguros'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    filename_rlc = db.Column(db.String(500))
    filename_rnt = db.Column(db.String(500))
    status = db.Column(db.String(50), default='PENDING')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    total_empresas = db.Column(db.Integer)
    total_trabajadores = db.Column(db.Integer)
    periodo = db.Column(db.String(10))
    error_message = db.Column(db.Text)
    
    # Relaciones
    user = db.relationship('User', backref='tareas_seguros')
    gestoria = db.relationship('Gestoria', backref='tareas_seguros')
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'filename_rlc': self.filename_rlc,
            'filename_rnt': self.filename_rnt,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_empresas': self.total_empresas,
            'total_trabajadores': self.total_trabajadores,
            'periodo': self.periodo,
            'error_message': self.error_message
        }


class Comunicado(db.Model):
    """Modelo para el Muro de Comunicados de la Gestoría"""
    __tablename__ = 'comunicados'
    
    id = db.Column(db.Integer, primary_key=True)
    gestoria_id = db.Column(db.Integer, db.ForeignKey('gestorias.id'), nullable=False)
    emisor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    
    # impuestos, nominas, seguros, urgente, general
    tipo = db.Column(db.String(20), default='general')
    # baja, media, alta
    prioridad = db.Column(db.String(20), default='media')
    
    # global, grupo, empresa
    alcance = db.Column(db.String(20), default='global')
    filtro_id = db.Column(db.Integer, nullable=True) # ID de grupo o empresa destino
    
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_inicio = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_fin = db.Column(db.DateTime, nullable=True) # Destrucción automática opcional
    
    # Tracking de lectura simplificado
    leido_por = db.Column(db.JSON, default=[]) # IDs de usuarios
    
    # Datos extra para comunicados especiales (ej: notificaciones de documentos)
    extra_data = db.Column(db.JSON, default={})
    
    # Relaciones
    gestoria = db.relationship('Gestoria', backref='comunicados')
    emisor = db.relationship('User', foreign_keys=[emisor_id], backref='comunicados_emitidos')
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'contenido': self.contenido,
            'tipo': self.tipo,
            'prioridad': self.prioridad,
            'alcance': self.alcance,
            'filtro_id': self.filtro_id,
            'activo': self.activo,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'emisor_nombre': self.emisor.nombre if self.emisor else 'Gestoría',
            'metadata': self.extra_data or {}  # Mantener 'metadata' en la API por compatibilidad
        }


class ExtractionTemplate(db.Model):
    """
    Motor Declarativo: Plantillas de extracción de datos (JSON)
    Reemplaza a los hardcoded python profiles para notificaciones nuevas.
    """
    __tablename__ = 'extraction_templates'
    
    id = db.Column(db.String(100), primary_key=True)  # Ej: tgss_embargo_vehiculos_tva391
    nombre = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(10), default='1.0')
    
    # Herencia: permite que un perfil herede reglas de otro (ej: variante provincial)
    hereda_de = db.Column(db.String(100), db.ForeignKey('extraction_templates.id'), nullable=True)
    
    idioma_principal = db.Column(db.String(5), default='es')  # es, ca, eu, gl
    
    # El corazón del sistema: JSON con reglas de detección y extracción
    profile_json = db.Column(db.JSON, nullable=False)
    
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación jerárquica
    parent = db.relationship('ExtractionTemplate', remote_side=[id], backref='children')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'version': self.version,
            'hereda_de': self.hereda_de,
            'idioma_principal': self.idioma_principal,
            'profile_json': self.profile_json,
            'activo': self.activo,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
