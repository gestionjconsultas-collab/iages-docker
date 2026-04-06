"""
Constantes del sistema IAGES
Centraliza todos los valores hardcodeados para facilitar mantenimiento
"""

# ============================================
# CATEGORÍAS DE DOCUMENTOS
# ============================================

class DocumentCategories:
    """Categorías de documentos"""
    POR_PROCESAR = "Por Procesar"
    SEGUROS_SOCIALES = "Seguros Sociales"
    NOMINAS = "Nóminas"
    FISCAL = "Fiscal"
    DEHU = "DEHU"
    NOTIFICACIONES = "Notificaciones"
    RLC = "RLC"
    RNT = "RNT"
    ALTAS_TRABAJADORES = "Altas de Trabajadores"
    BAJAS_TRABAJADORES = "Bajas de Trabajadores"
    FINIQUITOS = "Finiquitos"
    CONTRATOS = "Contratos"
    IMPUESTOS = "Impuestos"
    CERTIFICADOS_190 = "Certificados de Retenciones 190"
    CERTIFICADOS_180 = "Certificados de Retenciones 180"
    ACCIDENTES_TRABAJO = "Accidentes de Trabajo"
    
    @classmethod
    def all(cls):
        """Retorna todas las categorías"""
        return [
            cls.POR_PROCESAR,
            cls.SEGUROS_SOCIALES,
            cls.NOMINAS,
            cls.FISCAL,
            cls.DEHU,
            cls.NOTIFICACIONES,
            cls.RLC,
            cls.RNT,
            cls.ALTAS_TRABAJADORES,
            cls.BAJAS_TRABAJADORES,
            cls.FINIQUITOS,
            cls.CONTRATOS,
            cls.CERTIFICADOS_190,
            cls.CERTIFICADOS_180,
            cls.ACCIDENTES_TRABAJO
        ]
    
    @classmethod
    def is_valid(cls, categoria):
        """Verifica si una categoría es válida"""
        return categoria in cls.all()


# ============================================
# ESTADOS DE TAREAS
# ============================================

class TaskStates:
    """Estados de tareas"""
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    
    @classmethod
    def all(cls):
        return [cls.PENDIENTE, cls.EN_PROGRESO, cls.COMPLETADA, cls.CANCELADA]
    
    @classmethod
    def is_valid(cls, estado):
        return estado in cls.all()


# ============================================
# PRIORIDADES
# ============================================

class TaskPriorities:
    """Prioridades de tareas"""
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"
    
    @classmethod
    def all(cls):
        return [cls.ALTA, cls.MEDIA, cls.BAJA]
    
    @classmethod
    def is_valid(cls, prioridad):
        return prioridad in cls.all()


# ============================================
# TIPOS DE NOTIFICACIONES
# ============================================

class NotificationTypes:
    """Tipos de notificaciones"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    @classmethod
    def all(cls):
        return [cls.INFO, cls.SUCCESS, cls.WARNING, cls.ERROR]
    
    @classmethod
    def is_valid(cls, tipo):
        return tipo in cls.all()


# ============================================
# ACCIONES DE AUDITORÍA
# ============================================

class AuditActions:
    """Acciones de auditoría"""
    DOCUMENTO_LEIDO = "documento_leido"
    DOCUMENTO_PROCESADO = "documento_procesado"
    DOCUMENTO_ELIMINADO = "documento_eliminado"
    DOCUMENTO_MOVIDO = "documento_movido"
    TAREA_CREADA = "tarea_creada"
    TAREA_ASIGNADA = "tarea_asignada"
    TAREA_COMPLETADA = "tarea_completada"
    CHAT_PREGUNTA = "chat_pregunta"
    LOGIN = "login"
    LOGOUT = "logout"
    EMAIL_ENVIADO = "email_enviado"
    
    @classmethod
    def all(cls):
        return [
            cls.DOCUMENTO_LEIDO,
            cls.DOCUMENTO_PROCESADO,
            cls.DOCUMENTO_ELIMINADO,
            cls.DOCUMENTO_MOVIDO,
            cls.TAREA_CREADA,
            cls.TAREA_ASIGNADA,
            cls.TAREA_COMPLETADA,
            cls.CHAT_PREGUNTA,
            cls.LOGIN,
            cls.LOGOUT,
            cls.EMAIL_ENVIADO
        ]


# ============================================
# DEPARTAMENTOS
# ============================================

class Departments:
    """Departamentos del sistema"""
    JEFATURA = "Jefatura"
    FISCAL = "Fiscal"
    LABORAL = "Laboral"
    CONTABLE = "Contable"
    
    @classmethod
    def all(cls):
        return [cls.JEFATURA, cls.FISCAL, cls.LABORAL, cls.CONTABLE]
    
    @classmethod
    def is_valid(cls, departamento):
        return departamento in cls.all()


# ============================================
# LÍMITES Y CONFIGURACIÓN
# ============================================

class Limits:
    """Límites del sistema"""
    MAX_FILE_SIZE_MB = 50
    MAX_UPLOAD_FILES = 100
    CACHE_TTL_HOURS = 24
    SESSION_TIMEOUT_MINUTES = 60
    
    # Paginación
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    
    # Chat
    MAX_CHAT_HISTORY = 50
    MAX_TOKENS_PER_REQUEST = 10000
    
    # Rate limiting
    MAX_REQUESTS_PER_HOUR = 1000
    MAX_CHAT_REQUESTS_PER_HOUR = 100


# ============================================
# FORMATOS
# ============================================

class DateFormats:
    """Formatos de fecha"""
    DISPLAY = "%d/%m/%Y"  # Para mostrar al usuario
    DISPLAY_WITH_TIME = "%d/%m/%Y %H:%M"
    ISO = "%Y-%m-%d"  # Para BD
    ISO_WITH_TIME = "%Y-%m-%d %H:%M:%S"
    FILENAME = "%Y%m%d_%H%M%S"  # Para nombres de archivo
    PERIODO = "%Y%m"  # Para periodos (202412)


# ============================================
# ESTADOS DE EMPRESA
# ============================================

class CompanyStates:
    """Estados de empresa"""
    ABIERTO = "Abierto"
    CERRADO = "Cerrado"
    SUSPENDIDO = "Suspendido"
    
    @classmethod
    def all(cls):
        return [cls.ABIERTO, cls.CERRADO, cls.SUSPENDIDO]
    
    @classmethod
    def is_valid(cls, estado):
        return estado in cls.all()


# ============================================
# CATEGORÍAS DE TICKETS DE SOPORTE
# ============================================

class TicketCategories:
    """Categorías de tickets de soporte"""
    BUG = "Bug"
    CONSULTA = "Consulta"
    MEJORA = "Mejora"
    URGENTE = "Urgente"
    
    @classmethod
    def all(cls):
        return [cls.BUG, cls.CONSULTA, cls.MEJORA, cls.URGENTE]


class TicketStates:
    """Estados de tickets"""
    ABIERTO = "Abierto"
    EN_PROCESO = "En Proceso"
    RESUELTO = "Resuelto"
    CERRADO = "Cerrado"
    
    @classmethod
    def all(cls):
        return [cls.ABIERTO, cls.EN_PROCESO, cls.RESUELTO, cls.CERRADO]


class TicketPriorities:
    """Prioridades de tickets"""
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    URGENTE = "Urgente"
    
    @classmethod
    def all(cls):
        return [cls.BAJA, cls.MEDIA, cls.ALTA, cls.URGENTE]
