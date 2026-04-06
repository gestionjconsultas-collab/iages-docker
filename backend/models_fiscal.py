# backend/models_fiscal.py
"""
Modelos de base de datos para el Sistema de Gestión Fiscal
Incluye documentos fiscales, clasificación IA, y seguimiento de obligaciones
"""

from datetime import datetime, timezone, date, timedelta
from sqlalchemy import Column, Integer, String, Float, Date, JSON, ForeignKey, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from extensions import db
import enum

# ============================================================================
# ENUMS
# ============================================================================

class TipoDocumentoFiscal(enum.Enum):
    """Tipos de documentos fiscales soportados"""
    MODELO_130 = "Modelo 130 - IRPF Pagos Fraccionados"
    MODELO_200 = "Modelo 200 - Impuesto Sociedades"
    MODELO_202 = "Modelo 202 - Pagos Fraccionados Sociedades"
    MODELO_303 = "Modelo 303 - IVA"
    MODELO_180 = "Modelo 180 - Retenciones Alquileres Anual"
    MODELO_190 = "Modelo 190 - Retenciones Anuales"
    MODELO_111 = "Modelo 111 - Retenciones Trimestrales"
    MODELO_115 = "Modelo 115 - Retenciones Alquileres"
    MODELO_347 = "Modelo 347 - Operaciones con Terceros"
    CERTIFICADO_RETENCIONES = "Certificado Retenciones"
    APLAZAMIENTO_SOLICITUD = "Solicitud Aplazamiento"
    APLAZAMIENTO_CONCESION = "Concesión Aplazamiento"
    OTRO = "Otro"

class ClasificacionFiscal(enum.Enum):
    """Clasificación del documento según requiera pago o sea informativo"""
    PAGO_REQUERIDO = "Pago Requerido"
    INFORMATIVO = "Informativo"
    INFORMATIVO_DEVOLUCION = "Informativo - Devolución"
    INFORMATIVO_SIN_ACTIVIDAD = "Informativo - Sin Actividad"

class EstadoDocumentoFiscal(enum.Enum):
    """Estados del documento en el flujo de trabajo"""
    PENDIENTE_REVISION = "Pendiente Revisión"  # IA procesó, esperando confirmación usuario
    CONFIRMADO = "Confirmado"  # Usuario confirmó clasificación
    PRESENTADO = "Presentado"  # Documento presentado ante Hacienda
    PAGADO = "Pagado"  # Pago realizado
    VENCIDO = "Vencido"  # Fecha límite superada sin pago

# ============================================================================
# MODELOS
# ============================================================================

class DocumentoFiscal(db.Model):
    """
    Modelo principal para documentos fiscales
    Soporta clasificación asistida por IA con confirmación de usuario
    """
    __tablename__ = 'documentos_fiscales'
    
    # ========== Identificación ==========
    id = db.Column(db.Integer, primary_key=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False, index=True)
    
    # ========== Tipo y Clasificación ==========
    tipo_documento = db.Column(db.String(50), nullable=False)  # TipoDocumentoFiscal
    ejercicio_fiscal = db.Column(db.Integer, nullable=False, index=True)
    periodo = db.Column(db.String(10))  # T1, T2, T3, T4, ANUAL, MES_01, etc.
    
    # ========== Datos Extraídos ==========
    nif = db.Column(db.String(20))
    numero_justificante = db.Column(db.String(50))
    fecha_presentacion = db.Column(db.Date)
    
    # ========== Clasificación IA (Sugerencia vs Confirmación) ==========
    clasificacion_sugerida = db.Column(db.String(50))  # ClasificacionFiscal - Sugerencia de IA
    clasificacion_confirmada = db.Column(db.String(50))  # ClasificacionFiscal - Confirmada por usuario
    confianza_ia = db.Column(db.Float)  # 0.0 - 1.0 (nivel de confianza de la IA)
    
    # ========== Metadatos Específicos (JSON flexible) ==========
    metadatos = db.Column(db.JSON)  # Campos específicos según tipo de documento
    """
    Ejemplos de metadatos:
    - Modelo 303: {resultado_autoliquidacion, base_imponible, cuota_deducir}
    - Modelo 200: {base_imponible, cuota_liquida, tipo_gravamen}
    - Certificado: {nif_perceptor, nif_pagador, retenciones_practicadas}
    - Aplazamiento: {importe_deuda, num_plazos, vencimientos: [{fecha, importe}]}
    """
    
    # ========== Información de Pago ==========
    importe_pago = db.Column(db.Float, nullable=True)
    fecha_limite_pago = db.Column(db.Date, nullable=True, index=True)
    
    # ========== Estado y Archivo ==========
    estado = db.Column(db.String(50), default='PENDIENTE_REVISION', index=True)  # EstadoDocumentoFiscal
    archivo_pdf_path = db.Column(db.String(500), nullable=False)
    
    # ========== Auditoría y Timestamps ==========
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))
    procesado_por_ia_at = db.Column(db.DateTime)  # Cuándo la IA procesó el documento
    confirmado_por_usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    confirmado_at = db.Column(db.DateTime)  # Cuándo el usuario confirmó
    
    # ========== Relaciones ==========
    empresa = db.relationship('Empresa', backref='documentos_fiscales')
    confirmado_por = db.relationship('User', foreign_keys=[confirmado_por_usuario_id])
    
    def to_dict(self):
        """Serialización para API"""
        return {
            'id': self.id,
            'empresa_id': self.empresa_id,
            'empresa_nombre': self.empresa.nombre if self.empresa else None,
            'tipo_documento': self.tipo_documento,
            'ejercicio_fiscal': self.ejercicio_fiscal,
            'periodo': self.periodo,
            'nif': self.nif,
            'numero_justificante': self.numero_justificante,
            'fecha_presentacion': self.fecha_presentacion.isoformat() if self.fecha_presentacion else None,
            'clasificacion_sugerida': self.clasificacion_sugerida,
            'clasificacion_confirmada': self.clasificacion_confirmada,
            'confianza_ia': self.confianza_ia,
            'metadatos': self.metadatos or {},
            'importe_pago': self.importe_pago,
            'fecha_limite_pago': self.fecha_limite_pago.isoformat() if self.fecha_limite_pago else None,
            'estado': self.estado,
            'archivo_pdf_path': self.archivo_pdf_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'procesado_por_ia_at': self.procesado_por_ia_at.isoformat() if self.procesado_por_ia_at else None,
            'confirmado_por': self.confirmado_por.nombre if self.confirmado_por else None,
            'confirmado_at': self.confirmado_at.isoformat() if self.confirmado_at else None,
            # Indicadores útiles
            'requiere_confirmacion': self.estado == 'PENDIENTE_REVISION',
            'requiere_pago': self.clasificacion_confirmada == 'PAGO_REQUERIDO' or self.clasificacion_sugerida == 'PAGO_REQUERIDO',
            'dias_hasta_vencimiento': self._calcular_dias_hasta_vencimiento()
        }
    
    def _calcular_dias_hasta_vencimiento(self):
        """Calcula días hasta vencimiento (negativo si ya venció)"""
        if not self.fecha_limite_pago:
            return None
        delta = self.fecha_limite_pago - date.today()
        return delta.days
    
    def marcar_como_confirmado(self, usuario_id, clasificacion_confirmada, metadatos_corregidos=None):
        """
        Marca el documento como confirmado por el usuario
        Permite correcciones de la clasificación y metadatos sugeridos por IA
        """
        self.clasificacion_confirmada = clasificacion_confirmada
        if metadatos_corregidos:
            self.metadatos = metadatos_corregidos
        self.estado = 'CONFIRMADO'
        self.confirmado_por_usuario_id = usuario_id
        self.confirmado_at = datetime.now(timezone.utc)
    
    def marcar_como_presentado(self):
        """Marca el documento como presentado ante Hacienda"""
        self.estado = 'PRESENTADO'
        self.updated_at = datetime.now(timezone.utc)
    
    def marcar_como_pagado(self):
        """Marca el documento como pagado"""
        self.estado = 'PAGADO'
        self.updated_at = datetime.now(timezone.utc)
    
    def verificar_vencimiento(self):
        """Verifica si el documento está vencido y actualiza estado"""
        if self.fecha_limite_pago and self.fecha_limite_pago < date.today():
            if self.estado not in ['PAGADO', 'VENCIDO']:
                self.estado = 'VENCIDO'
                return True
        return False


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_fecha_limite_modelo_303(ejercicio, trimestre):
    """
    Calcula fecha límite de presentación del Modelo 303
    Regla: 20 días naturales siguientes al trimestre
    """
    meses_fin_trimestre = {
        'T1': 3,  # Marzo
        'T2': 6,  # Junio
        'T3': 9,  # Septiembre
        'T4': 12  # Diciembre
    }
    
    mes_fin = meses_fin_trimestre.get(trimestre)
    if not mes_fin:
        return None
    
    # Último día del trimestre
    if mes_fin == 12:
        ultimo_dia = date(ejercicio, 12, 31)
    else:
        # Primer día del siguiente mes - 1 día
        siguiente_mes = date(ejercicio, mes_fin + 1, 1)
        ultimo_dia = siguiente_mes - timedelta(days=1)
    
    # 20 días naturales después
    fecha_limite = ultimo_dia + timedelta(days=20)
    
    return fecha_limite


def calcular_fecha_limite_modelo_200(ejercicio):
    """
    Calcula fecha límite de presentación del Modelo 200
    Regla: 25 días naturales siguientes a los 6 meses posteriores al cierre del ejercicio
    Normalmente: 25 de julio del año siguiente
    """
    return date(ejercicio + 1, 7, 25)
