# backend/app.py
try:
    from gevent import monkey
    if not monkey.is_module_patched('os'):
        monkey.patch_all()
        print("✅ Gevent monkey patching applied")
except ImportError:
    print("⚠️ Gevent not found, skipping monkey patching")

import sys
import os
import concurrent.futures
import asyncio
"""
Sistema de Gestión de Notificaciones v5.0 - FINAL ESTABLE
Correcciones: Sin duplicados, rutas dinámicas (app.config), seguridad por departamentos.
"""

import os
import shutil 
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from email.header import Header
import re
import json
from flask import Flask, request, jsonify, send_file, render_template, session, current_app
from werkzeug.utils import secure_filename
from tenant_utils import get_current_gestoria_id


from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime, timezone
from sqlalchemy import or_, and_, func, case, extract, cast, Text
from extensions import init_extensions, db, bcrypt, login_manager, limiter, cache, metrics, socketio
from flask_socketio import emit, join_room, leave_room


from flask_login import login_user, logout_user, login_required, current_user
from decorators import admin_required, departamento_required
from auditoria import auditar, registrar_auditoria, AccionesAuditoria
from routes_chat import register_chat_routes
from routes_permisos import register_permisos_routes

# Cargar variables de entorno
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
if os.path.exists(dotenv_path): load_dotenv(dotenv_path)

from config import config
from extensions import init_extensions, db, bcrypt, login_manager, limiter, cache, metrics
from models import Empresa, Documento, AliasNIF, User, Departamento, Notificacion, Plantilla, Gestoria, GrupoEmpresa, PlantillaTestFile, PlantillaTestResult
from routes_auditoria import register_auditoria_routes
from routes_mesa_trabajo import register_mesa_trabajo_routes
from routes_finiquitos import register_finiquitos_routes
from routes_contratos import register_contratos_routes
from routes_aplazamientos import register_aplazamientos_routes
from services.notificacion_extractor import NotificacionExtractor
from utils import limpiar_nombre_carpeta, clean_and_convert_to_float, _find_nif_with_regex
from utils_limits import validate_gestoria_limit, check_tokens_ia_disponibles, registrar_tokens_ia_usados
import hashlib
import difflib
from constants import DocumentCategories, NotificationTypes, TaskStates
from utils.logger import logger


def get_file_hash(file_path):
    """
    Genera hash SHA256 de un archivo para detectar duplicados reales.
    
    Args:
        file_path: Ruta absoluta al archivo
        
    Returns:
        Hash SHA256 en formato hexadecimal (64 caracteres)
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # Leer en chunks de 8KB para no saturar memoria
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculando hash: {e}")
        return None

def _buscar_empresa_fallback(texto, gestoria_id):
    """
    Fallback de clasificación: busca empresa por CCC o razón social cuando
    el NIF no fue detectado o no coincide con ninguna empresa registrada.

    Orden de búsqueda:
      1. CCC (Código Cuenta Cotización) — campo cuenta_cotizacion de Empresa
      2. Razón social — fuzzy match (SequenceMatcher >= 0.78) contra Empresa.nombre

    Args:
        texto (str): Texto completo extraído del documento
        gestoria_id (int): ID de la gestoría para filtrar empresas

    Returns:
        Empresa | None
    """
    if not texto or not gestoria_id:
        return None

    texto_upper = texto.upper()

    # --- 1. BUSCAR POR CCC ---
    ccc_patterns = [
        r'C[OÓ]DIGO\s+(?:DE\s+)?CUENTA\s+(?:DE\s+)?COTIZACI[OÓ]N[:\s]+(\d[\d\s]{5,15}\d)',
        r'\bCCC[:\s]+(\d[\d\s]{5,15}\d)',
        r'N[ÚU]MERO\s+DE\s+COTIZACI[OÓ]N[:\s]+(\d[\d\s]{5,15}\d)',
        r'C[OÓ]DIGO\s+CUENTA\s+COTIZACI[OÓ]N\s+(\d[\d\s]{5,15}\d)',
    ]

    for pattern in ccc_patterns:
        match = re.search(pattern, texto_upper)
        if match:
            ccc_raw = re.sub(r'\s+', '', match.group(1))
            # CCC español: normalmente 11 dígitos (prov 2 + empresa 8 + control 2)
            # Aceptamos entre 8 y 13 por variaciones de formato
            if 8 <= len(ccc_raw) <= 13:
                emp = Empresa.query.filter_by(
                    cuenta_cotizacion=ccc_raw,
                    gestoria_id=gestoria_id
                ).first()
                if emp:
                    logger.info(f"✅ Fallback CCC '{ccc_raw}' → empresa: {emp.nombre}")
                    return emp

    # --- 2. BUSCAR POR RAZÓN SOCIAL ---
    nombre_patterns = [
        r'RAZ[OÓ]N\s+SOCIAL[:\s]+([^\n]{3,80})',
        r'DENOMINACI[OÓ]N\s+SOCIAL[:\s]+([^\n]{3,80})',
        r'RAZ[OÓ]N\s+O\s+DENOMINACI[OÓ]N\s+SOCIAL[:\s]+([^\n]{3,80})',
        r'EMPRESA[:\s]+([^\n]{3,80})',
        r'NOMBRE\s+(?:DE\s+LA\s+)?EMPRESA[:\s]+([^\n]{3,80})',
    ]

    candidatos = []
    for pattern in nombre_patterns:
        match = re.search(pattern, texto_upper)
        if match:
            nombre_doc = match.group(1).strip().rstrip('.,;:')
            if len(nombre_doc) > 3:
                candidatos.append(nombre_doc)

    if candidatos:
        empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
        mejor_emp = None
        mejor_ratio = 0.0

        for nombre_doc in candidatos:
            for emp in empresas:
                ratio = difflib.SequenceMatcher(
                    None,
                    nombre_doc,
                    emp.nombre.upper()
                ).ratio()
                if ratio > mejor_ratio:
                    mejor_ratio = ratio
                    mejor_emp = emp

        if mejor_ratio >= 0.78 and mejor_emp:
            logger.info(f"✅ Fallback nombre (ratio={mejor_ratio:.2f}) → empresa: {mejor_emp.nombre}")
            return mejor_emp

    return None


def get_saltra_credentials(gestoria_id=None):
    """
    Obtener credenciales SALTRA desencriptadas de la configuración de la gestoría.

    Returns:
        dict: {'email': str, 'password': str, 'cert_secret': str, 'enabled': bool} o None
    """
    from models import Gestoria
    from flask_login import current_user

    if gestoria_id is None:
        if not current_user or not current_user.is_authenticated:
            return None
        gestoria_id = current_user.gestoria_id

    gestoria = Gestoria.query.get(gestoria_id)
    if not gestoria or not gestoria.configuracion:
        return None

    # Verificar que esté habilitado antes de desencriptar
    saltra_raw = gestoria.configuracion.get('saltra', {})
    if not saltra_raw.get('enabled', False):
        return None

    # Usar helper que desencripta automáticamente (FIX: credenciales estaban en enc:...)
    config = gestoria.get_saltra_config_decrypted()

    # Solo email y password son obligatorios; cert_secret es opcional (puede ser per-empresa)
    if not config.get('email') or not config.get('password'):
        return None

    return {
        'email': config['email'],
        'password': config['password'],
        'cert_secret': config.get('cert_secret'),  # puede ser None
        'enabled': config.get('enabled', True)
    }

def create_app(config_name='development'):
    """Factory para crear la aplicación Flask"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Importar rutas
    from routes_mesa_trabajo import register_mesa_trabajo_routes
    
    # CORS configuration - Restringir orígenes permitidos
    allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    allowed_origins = [origin.strip() for origin in allowed_origins]
    
    CORS(app, 
         resources={r"/api/*": {
             "origins": allowed_origins,
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Range", "X-Content-Range"],
             "max_age": 3600
         }}, 
         supports_credentials=True
    )
    
    init_extensions(app)
    
    # Inicializar funcionalidades de monitoreo (solo Compress por ahora)
    from init_monitoring import init_monitoring_features
    init_monitoring_features(app)
    
    # Configurar SocketIO para notificaciones en tiempo real
    # ✅ FIX: Usar la misma instancia de extensions.py y configurar message_queue
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Detectar si gevent está disponible para async_mode
    async_mode = None
    try:
        import gevent
        async_mode = 'gevent'
    except ImportError:
        async_mode = 'threading'
        
    socketio.init_app(
        app,
        cors_allowed_origins='*',
        message_queue=redis_url,
        async_mode=async_mode,
        # M-3: Heartbeat para detectar y limpiar conexiones muertas
        ping_timeout=60,    # segundos esperando pong antes de desconectar
        ping_interval=25,   # segundos entre pings al cliente
    )
    app.config['SOCKETIO'] = socketio  

    # Inicializar Redis Listener para recibir notificaciones de Celery
    try:
        from redis_listener import init_redis_listener
        init_redis_listener(app, socketio)
        logger.info("✅ Redis Listener inicializado para notificaciones de Celery")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo inicializar Redis Listener: {e}")


    # Handlers de SocketIO
    @socketio.on('connect')
    def handle_connect():
        """Cliente se conecta al WebSocket"""
        try:
            if current_user and current_user.is_authenticated:
                # Unir al room personal del usuario
                join_room(f'user_{current_user.id}')
                # FIX A-8: Usar departamento_id en lugar del nombre para evitar colisiones
                if current_user.departamento_id:
                    join_room(f'departamento_{current_user.departamento_id}')
                # ⭐ Unir al room de su gestoría (para comunicados globales)
                if current_user.gestoria_id:
                    join_room(f'gestoria_{current_user.gestoria_id}')
                    # Unir a los admins a un room específico de staff
                    if not current_user.is_invitado():
                        join_room(f'gestoria_staff_{current_user.gestoria_id}')

                # ⭐ Unir a rooms específicos de empresa (crucial para notificaciones privadas a clientes)
                if current_user.is_invitado():
                    empresa_ids = current_user.get_allowed_company_ids()
                    for eid in empresa_ids:
                        join_room(f'empresa_{eid}')
                
                logger.info(f"Usuario {current_user.nombre} conectado a WebSocket")
                emit('connection_success', {'user_id': current_user.id})
            else:
                print("⚠️ Cliente no autenticado intentó conectarse")
        except Exception as e:
            print(f"Error en conexión WebSocket: {e}")

    @socketio.on('disconnect')
    def handle_disconnect():
        """Cliente se desconecta"""
        try:
            if current_user and current_user.is_authenticated:
                print(f"👋 Usuario {current_user.nombre} desconectado")
        except Exception as e:
            print(f"Error en desconexión WebSocket: {e}")
    
    # ⭐ Eventos de Chat de Soporte
    @socketio.on('join_ticket')
    def handle_join_ticket(data):
        """Usuario se une a la room de un ticket (con validación de permisos)"""
        try:
            if not (current_user and current_user.is_authenticated):
                return False
            ticket_id = data.get('ticket_id')
            if not ticket_id:
                return False
            from models import TicketSoporte
            ticket = TicketSoporte.query.get(ticket_id)
            if not ticket:
                return False

            es_superadmin = current_user.is_super_admin
            es_soporte = (current_user.departamento and
                          current_user.departamento.nombre.strip() == 'Soporte')
            # Soporte externo: departamento Soporte sin gestoría propia
            es_soporte_externo = es_soporte and current_user.gestoria_id is None

            # Superadmin y soporte externo pueden unirse a cualquier ticket
            if not es_superadmin and not es_soporte_externo:
                # Resto de usuarios: ticket debe pertenecer a su gestoría
                if ticket.gestoria_id != current_user.gestoria_id:
                    logger.warning(f"⛔ {current_user.nombre} intentó unirse a ticket de otra gestoría: {ticket_id}")
                    return False
                # Invitados/clientes solo pueden unirse a tickets que ellos crearon
                if current_user.is_invitado() and ticket.usuario_creador_id != current_user.id:
                    logger.warning(f"⛔ {current_user.nombre} intentó unirse a ticket ajeno: {ticket_id}")
                    return False

            room = f'ticket_{ticket_id}'
            join_room(room)
            logger.info(f"✅ {current_user.nombre} se unió a {room} (soporte_externo={es_soporte_externo}, superadmin={es_superadmin})")
        except Exception as e:
            logger.error(f"Error en join_ticket: {e}")
    
    @socketio.on('leave_ticket')
    def handle_leave_ticket(data):
        """Usuario sale de la room de un ticket"""
        try:
            if current_user and current_user.is_authenticated:
                ticket_id = data.get('ticket_id')
                if ticket_id:
                    room = f'ticket_{ticket_id}'
                    leave_room(room)
                    print(f"👋 {current_user.nombre} salió de {room}")
        except Exception as e:
            print(f"Error en leave_ticket: {e}")
    
    @socketio.on('typing_soporte')
    def handle_typing_soporte(data):
        """Usuario está escribiendo en el chat"""
        try:
            if current_user and current_user.is_authenticated:
                ticket_id = data.get('ticket_id')
                if ticket_id:
                    socketio.emit('usuario_escribiendo_soporte', {
                        'ticket_id': ticket_id,
                        'usuario': current_user.nombre,
                        'usuario_id': current_user.id
                    }, room=f'ticket_{ticket_id}', skip_sid=request.sid)
        except Exception as e:
            print(f"Error en typing_soporte: {e}")
    
    @socketio.on('join_gestoria')
    def handle_join_gestoria(data):
        """Usuario se une al room de su gestoría"""
        try:
            if current_user and current_user.is_authenticated:
                gestoria_id = data.get('gestoria_id')
                if gestoria_id:
                    # FIX C-9: Validar que el gestoria_id solicitado coincide con
                    # el del usuario. Soporte externo (gestoria_id=None) puede unirse.
                    if current_user.gestoria_id is not None and current_user.gestoria_id != int(gestoria_id):
                        logger.warning(
                            f"Intento de unirse a gestoría ajena: user={current_user.id} "
                            f"gestoria_user={current_user.gestoria_id} gestoria_req={gestoria_id}"
                        )
                        return
                    room = f'gestoria_{gestoria_id}'
                    join_room(room)
                    # También unir a la sala de staff si corresponde
                    if not current_user.is_invitado():
                        staff_room = f'gestoria_staff_{gestoria_id}'
                        join_room(staff_room)
                        logger.debug(f"Usuario {current_user.nombre} se unió a {staff_room}")
                    logger.debug(f"Usuario {current_user.nombre} se unió a {room}")
        except Exception as e:
            print(f"Error en join_gestoria: {e}")
    
    @socketio.on('leave_gestoria')
    def handle_leave_gestoria(data):
        """Usuario sale del room de su gestoría"""
        try:
            if current_user and current_user.is_authenticated:
                gestoria_id = data.get('gestoria_id')
                if gestoria_id:
                    room = f'gestoria_{gestoria_id}'
                    leave_room(room)
                    print(f"👋 {current_user.nombre} salió de {room}")
        except Exception as e:
            print(f"Error en leave_gestoria: {e}")
    
    register_routes(app)
    register_auditoria_routes(app)
    register_finiquitos_routes(app)
    register_contratos_routes(app)
    register_aplazamientos_routes(app)
    register_mesa_trabajo_routes(app)  # Mesa de Trabajo

    # Test Bench de Plantillas
    from routes_plantilla_test import plantilla_test_bp
    app.register_blueprint(plantilla_test_bp)

    # Tipos de Documento (perfiles predefinidos)
    from routes_tipos_documento import tipos_documento_bp
    app.register_blueprint(tipos_documento_bp)

    # Búsqueda full-text de documentos por texto OCR
    from routes_busqueda import busqueda_bp
    app.register_blueprint(busqueda_bp)

    # Emails pendientes de envío
    from routes_emails_pendientes import emails_pendientes_bp
    app.register_blueprint(emails_pendientes_bp)

    # Detección de perfil sugerido para un documento (Mesa de Trabajo)
    from routes_documento_detect import detectar_bp
    app.register_blueprint(detectar_bp)


    @app.route('/finiquitos/confirmar/<token>')
    def confirmar_pago_finiquito(token):
        """Confirma el pago de una cuota mediante link de email"""
        from email_tokens import validar_token_confirmacion
        from models import FiniquitoLinea, Documento, Empresa, RecordatorioPago
        from datetime import datetime, timezone, date
        
        try:
            # Validar token
            linea_id = validar_token_confirmacion(token)
            
            if not linea_id:
                return render_template('confirmacion_pago.html', 
                                     accion=NotificationTypes.ERROR,
                                     mensaje='El enlace ha expirado o no es válido.')
            
            # Obtener línea
            linea = db.session.get(FiniquitoLinea, linea_id)
            if not linea:
                return render_template('confirmacion_pago.html',
                                     accion=NotificationTypes.ERROR, 
                                     mensaje='Cuota no encontrada.')
            
            # Obtener documento y empresa
            documento = db.session.get(Documento, linea.documento_id)
            empresa = db.session.get(Empresa, documento.empresa_id) if documento else None
            
            # Acción (pagado o pendiente)
            action = request.args.get('action', 'pagado')
            
            if action == 'pagado':
                linea.estado = 'pagado'
                linea.fecha_pago = date.today()
                linea.confirmado_por_email = True
                
                # Actualizar recordatorio
                recordatorio = RecordatorioPago.query.filter_by(
                    finiquito_linea_id=linea.id
                ).order_by(RecordatorioPago.fecha_envio.desc()).first()
                
                if recordatorio:
                    recordatorio.estado = 'confirmado'
                    recordatorio.fecha_respuesta = datetime.now(timezone.utc)
                
                db.session.commit()
                
                return render_template('confirmacion_pago.html',
                                     accion='pagado',
                                     linea=linea,
                                     documento=documento,
                                     empresa=empresa)
            else:
                # Marcar recordatorio como "ignorado"
                recordatorio = RecordatorioPago.query.filter_by(
                    finiquito_linea_id=linea.id
                ).order_by(RecordatorioPago.fecha_envio.desc()).first()
                
                if recordatorio:
                    recordatorio.estado = 'ignorado'
                    recordatorio.fecha_respuesta = datetime.now(timezone.utc)
                
                db.session.commit()
                
                return render_template('confirmacion_pago.html',
                                     accion=TaskStates.PENDIENTE,
                                     linea=linea,
                                     documento=documento,
                                     empresa=empresa)
        
        except Exception as e:
            print(f"Error confirmando pago: {e}")
            import traceback
            traceback.print_exc()
            return render_template('confirmacion_pago.html',
                                 accion=NotificationTypes.ERROR,
                                 mensaje='Ha ocurrido un error. Por favor, contacte con soporte.')
    
    
    @app.route('/api/finiquitos/recordatorios', methods=['GET'])
    @login_required
    def get_recordatorios_historial():
        """Obtiene el historial de recordatorios enviados"""
        from models import RecordatorioPago, FiniquitoLinea, Documento, Empresa

        empresa_id = request.args.get('empresa_id', type=int)
        estado_filtro = request.args.get('estado')
        gestoria_id = get_current_gestoria_id()

        query = db.session.query(
            RecordatorioPago,
            FiniquitoLinea,
            Documento,
            Empresa
        ).join(
            FiniquitoLinea, RecordatorioPago.finiquito_linea_id == FiniquitoLinea.id
        ).join(
            Documento, FiniquitoLinea.documento_id == Documento.id
        ).join(
            Empresa, Documento.empresa_id == Empresa.id
        )

        # FIX A-9: Filtrar siempre por gestoría del usuario
        query = query.filter(Empresa.gestoria_id == gestoria_id)

        if empresa_id:
            # Validar que la empresa pertenece a la gestoría antes de filtrar
            if not current_user.has_access_to_company(empresa_id):
                return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
            query = query.filter(Empresa.id == empresa_id)

        if estado_filtro:
            query = query.filter(RecordatorioPago.estado == estado_filtro)
        
        query = query.order_by(RecordatorioPago.fecha_envio.desc()).limit(100)
        
        resultados = query.all()
        
        recordatorios_lista = []
        for recordatorio, linea, documento, empresa in resultados:
            rec_dict = recordatorio.to_dict()
            rec_dict['linea'] = {
                'importe_total_plazo': linea.importe_total_plazo,
                'fecha_vencimiento': linea.fecha_vencimiento.isoformat() if linea.fecha_vencimiento else None,
                'estado': linea.estado
            }
            rec_dict['documento'] = {
                'nombre_archivo': documento.nombre_archivo
            }
            rec_dict['empresa'] = {
                'nombre': empresa.nombre
            }
            recordatorios_lista.append(rec_dict)
        
        return jsonify({NotificationTypes.SUCCESS: True, 'recordatorios': recordatorios_lista})
    
    
    @app.route('/api/finiquitos/cuotas-proximas', methods=['GET'])
    @login_required
    def get_cuotas_proximas_vencer():
        """Obtiene cuotas que vencen en los próximos 30 días"""
        from models import FiniquitoLinea, Documento, Empresa
        from datetime import date, timedelta

        empresa_id = request.args.get('empresa_id', type=int)
        dias = request.args.get('dias', 30, type=int)
        gestoria_id = get_current_gestoria_id()

        hoy = date.today()
        fecha_limite = hoy + timedelta(days=dias)

        query = db.session.query(
            FiniquitoLinea,
            Documento,
            Empresa
        ).join(
            Documento, FiniquitoLinea.documento_id == Documento.id
        ).join(
            Empresa, Documento.empresa_id == Empresa.id
        ).filter(
            FiniquitoLinea.fecha_vencimiento.between(hoy, fecha_limite),
            FiniquitoLinea.estado == TaskStates.PENDIENTE
        )

        # FIX A-9: Filtrar siempre por gestoría del usuario
        query = query.filter(Empresa.gestoria_id == gestoria_id)

        if empresa_id:
            # Validar que la empresa pertenece a la gestoría antes de filtrar
            if not current_user.has_access_to_company(empresa_id):
                return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
            query = query.filter(Empresa.id == empresa_id)
        
        query = query.order_by(FiniquitoLinea.fecha_vencimiento)
        
        resultados = query.all()
        
        cuotas_lista = []
        for linea, documento, empresa in resultados:
            linea_dict = linea.to_dict()
            linea_dict['documento'] = {
                'nombre_archivo': documento.nombre_archivo
            }
            linea_dict['empresa'] = {
                'nombre': empresa.nombre
            }
            # Calcular días faltantes
            dias_faltantes = (linea.fecha_vencimiento - hoy).days
            linea_dict['dias_faltantes'] = dias_faltantes
            linea_dict['recordatorios_enviados'] = linea.recordatorios_count or 0
            linea_dict['ultimo_recordatorio'] = linea.ultimo_recordatorio_enviado.isoformat() if linea.ultimo_recordatorio_enviado else None
            
            cuotas_lista.append(linea_dict)
        
        return jsonify({NotificationTypes.SUCCESS: True, 'cuotas': cuotas_lista, 'total': len(cuotas_lista)})
    
    @app.route('/api/finiquitos/estadisticas-recordatorios', methods=['GET'])
    @login_required
    def get_estadisticas_recordatorios():
        """Estadísticas de recordatorios enviados"""
        from models import RecordatorioPago
        
        total_enviados = RecordatorioPago.query.count()
        confirmados = RecordatorioPago.query.filter_by(estado='confirmado').count()
        ignorados = RecordatorioPago.query.filter_by(estado='ignorado').count()
        pendientes = RecordatorioPago.query.filter_by(estado='enviado').count()
        
        tasa_respuesta = (confirmados + ignorados) / total_enviados * 100 if total_enviados > 0 else 0
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'estadisticas': {
                'total_enviados': total_enviados,
                'confirmados': confirmados,
                'ignorados': ignorados,
                'pendientes_respuesta': pendientes,
                'tasa_respuesta': round(tasa_respuesta, 2)
            }
        })


    # Registrar rutas de grupos de documentos
    from routes_grupos_documentos import grupos_bp
    app.register_blueprint(grupos_bp)
    
    # Registrar rutas de gestión fiscal
    from routes_fiscal import fiscal_bp
    app.register_blueprint(fiscal_bp)
    
    # Registrar rutas de administración
    from routes_admin import admin_bp
    app.register_blueprint(admin_bp)
    
    # Registrar rutas de soporte
    from routes_soporte import soporte_bp
    app.register_blueprint(soporte_bp)
    print("✅ Rutas de Soporte registradas")
    
    # Registrar rutas de chat de soporte
    from routes_soporte_chat import soporte_chat_bp
    app.register_blueprint(soporte_chat_bp)
    print("✅ Rutas de Chat de Soporte registradas")

    # Registrar rutas de configuración de perfiles
    from routes_configuracion_perfiles import config_perfiles_bp
    app.register_blueprint(config_perfiles_bp)
    
    # Registrar rutas de tareas
    from routes_tareas import tareas_bp
    app.register_blueprint(tareas_bp)
    print("✅ Rutas de Tareas registradas")
    
    # Registrar rutas de dashboard
    from routes_dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    print("✅ Rutas de Dashboard registradas")
    
    # Registrar rutas de exportación
    from routes_export import export_bp
    app.register_blueprint(export_bp)
    print("✅ Rutas de Exportación registradas")
    
    # Registrar rutas de Super-Admin
    from routes_super_admin import super_admin_bp
    app.register_blueprint(super_admin_bp)
    print("✅ Rutas de Super-Admin registradas")
    
    # Registrar rutas de facturación
    from routes_billing import billing_bp
    app.register_blueprint(billing_bp)
    print("✅ Rutas de Facturación registradas")
    
    # Registrar rutas de administración de facturación
    from routes_billing_admin import billing_admin_bp
    app.register_blueprint(billing_admin_bp)
    print("✅ Rutas de Administración de Facturación registradas")

    # Registrar rutas de nóminas
    from routes_nominas import nominas_bp
    app.register_blueprint(nominas_bp)
    print("✅ Rutas de Nóminas registradas")
    
    # Registrar rutas de Modelo 190
    from routes_modelo_190 import modelo_190_bp
    app.register_blueprint(modelo_190_bp)
    print("✅ Rutas de Modelo 190 registradas")
    
    # Registrar rutas de Modelo 180
    from routes_modelo_180 import modelo_180_bp
    app.register_blueprint(modelo_180_bp)

    from routes_alta import alta_bp
    app.register_blueprint(alta_bp)
    print("✅ Rutas de Modelo 180 registradas")
    
    # Registrar rutas de estado de tareas
    from routes_task_status import task_status_bp
    app.register_blueprint(task_status_bp)
    print("✅ Rutas de Task Status registradas")
    
    # Registrar rutas de cancelación de tareas
    from routes_cancel_task import cancel_task_bp
    app.register_blueprint(cancel_task_bp)
    print("✅ Rutas de Cancelación de Tareas registradas")
    
    # Registrar rutas de calendario tributario AEAT
    from routes_calendario import calendario_bp
    app.register_blueprint(calendario_bp)
    
    # Registrar blueprint de DEHú España (Sustituido por SyncManager/Conecta)
    # from routes_dehu_espana import dehu_bp
    # app.register_blueprint(dehu_bp)
    from routes_dehu_sync import dehu_sync_bp
    app.register_blueprint(dehu_sync_bp)
    print("✅ Rutas de DEHú Sync habilitadas")
    
    # Registrar rutas de Desktop App (Conecta)
    from routes_desktop_app import desktop_app_bp
    app.register_blueprint(desktop_app_bp)
    print("✅ Rutas de Desktop App registradas")
    
    # Registrar rutas de Mesa de Trabajo - YA REGISTRADO ARRIBA
    # from routes_mesa_trabajo import register_mesa_trabajo_routes
    # register_mesa_trabajo_routes(app)
    print("✅ Rutas de Mesa de Trabajo registradas")
    
    # Middleware de modo de mantenimiento
    from middleware.maintenance_mode import check_maintenance_mode

    @app.before_request
    def before_request_maintenance_check():
        """Verifica modo de mantenimiento antes de cada request"""
        response = check_maintenance_mode()
        if response:
            return response

    @app.before_request
    def before_request_gestoria_activa():
        """Bloquea acceso si la gestoría del usuario está inactiva"""
        # Solo aplica a usuarios autenticados con gestoría (no super_admin, no soporte externo)
        if not current_user.is_authenticated:
            return None
        if current_user.is_super_admin or not current_user.gestoria_id:
            return None
        # Rutas permitidas aunque la gestoría esté inactiva
        rutas_permitidas = ['/api/auth/logout', '/api/auth/me', '/static/']
        if any(request.path.startswith(r) for r in rutas_permitidas):
            return None
        # Verificar estado de la gestoría (query ligera, solo activa)
        gestoria = Gestoria.query.with_entities(Gestoria.activa).filter_by(id=current_user.gestoria_id).first()
        if gestoria and not gestoria.activa:
            return jsonify({
                'success': False,
                'error': 'gestoria_inactiva',
                'message': 'Tu gestoría está inactiva. Contacta con el administrador del sistema.'
            }), 403
    
    # ⚠️ SEGURIDAD: Middleware de headers de seguridad HTTP
    from middleware.security_headers import init_security_headers
    init_security_headers(app)


    # ==========================================
    # PUSH NOTIFICATIONS ROUTES
    # ==========================================
    
    @app.route('/api/push/subscribe', methods=['POST'])
    @login_required
    def push_subscribe():
        """Suscribir usuario a notificaciones push"""
        from models import PushSubscription
        
        data = request.get_json()
        subscription = data.get('subscription')
        
        if not subscription:
            return jsonify({'success': False, 'error': 'Datos de suscripción requeridos'}), 400
        
        try:
            # Verificar si ya existe
            existing = PushSubscription.query.filter_by(
                endpoint=subscription['endpoint']
            ).first()
            
            if existing:
                # Actualizar si existe
                existing.p256dh = subscription['keys']['p256dh']
                existing.auth = subscription['keys']['auth']
                existing.active = True
                existing.user_agent = request.headers.get('User-Agent')
            else:
                # Crear nueva suscripción
                new_sub = PushSubscription(
                    user_id=current_user.id,
                    endpoint=subscription['endpoint'],
                    p256dh=subscription['keys']['p256dh'],
                    auth=subscription['keys']['auth'],
                    user_agent=request.headers.get('User-Agent')
                )
                db.session.add(new_sub)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Suscripción guardada correctamente'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error guardando suscripción: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/push/unsubscribe', methods=['POST'])
    @login_required
    def push_unsubscribe():
        """Desuscribir de notificaciones push"""
        from models import PushSubscription
        
        data = request.get_json()
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return jsonify({'success': False, 'error': 'Endpoint requerido'}), 400
        
        try:
            subscription = PushSubscription.query.filter_by(
                endpoint=endpoint,
                user_id=current_user.id
            ).first()
            
            if subscription:
                subscription.active = False
                db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Desuscripción exitosa'
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error desuscribiendo: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/push/vapid-public-key', methods=['GET'])
    def get_vapid_public_key():
        """Obtener clave pública VAPID para suscripciones"""
        app.logger.info("🔑 Petición de VAPID Public Key recibida")
        public_key = app.config.get('VAPID_PUBLIC_KEY')
        
        if not public_key:
            return jsonify({'success': False, 'error': 'VAPID no configurado'}), 500
        
        # ⭐ Recuperación Ultra-Robusta de VAPID
        try:
            import base64
            import re
            from cryptography.hazmat.primitives import serialization
            
            pk_input = public_key.strip()
            
            # Si ya parece una llave limpia de 87 caracteres (formato ecdh público), no tocamos nada
            if len(pk_input) == 87 and re.match(r'^[A-Za-z0-9_-]+$', pk_input):
                 app.logger.info("🔑 VAPID Public Key detectada como LIMPIA. No requiere recuperación.")
            else:
                # Si el PEM entero está base64-encodeada
                if pk_input.startswith('LS0tLS1'):
                    try:
                        while len(pk_input) % 4 != 0: pk_input += '='
                        pem_str = base64.b64decode(pk_input).decode('utf-8')
                        lines = pem_str.split('\n')
                        pk_raw_b64 = "".join([l for l in lines if 'BEGIN' not in l and 'END' not in l and l.strip()])
                    except:
                        pk_raw_b64 = pk_input
                else:
                    pk_raw_b64 = pk_input

                # Limpieza base64 (Soportando URL-Safe y Standard)
                pk_raw_b64 = re.sub(r'[^A-Za-z0-9+/_-]', '', pk_raw_b64)
                # Convertir URL-safe a Standard para b64decode
                pk_raw_std = pk_raw_b64.replace('-', '+').replace('_', '/')
                
                if len(pk_raw_std) % 4 == 1: pk_raw_std = pk_raw_std[:-1]
                while len(pk_raw_std) % 4 != 0: pk_raw_std += '='
                
                der_data = base64.b64decode(pk_raw_std)
                
                key = None
                # Intentar cargar DER
                for length in range(len(der_data), 60, -1):
                    try:
                        key = serialization.load_der_public_key(der_data[:length])
                        app.logger.info(f"✅ VAPID Public Key RECUPERADA (longitud: {length} bytes)")
                        break
                    except:
                        continue
                
                if key:
                    # Extraer punto EC (65 bytes)
                    raw_bytes = key.public_bytes(
                        encoding=serialization.Encoding.X962,
                        format=serialization.PublicFormat.UncompressedPoint
                    )
                    public_key = base64.urlsafe_b64encode(raw_bytes).decode('utf-8').rstrip('=')
                else:
                    app.logger.warning("⚠️ No se pudo recuperar estructura DER. Usando llave original como fallback.")
            
        except Exception as e:
            app.logger.error(f"❌ Error recuperando VAPID: {e}")

        return jsonify({
            'success': True,
            'publicKey': public_key
        })


    @app.route('/api/push/test', methods=['POST'])
    @login_required
    def push_test():
        """Enviar notificación de prueba"""
        from services.push_notification_service import PushNotificationService
        
        notification = {
            'title': 'Notificación de prueba',
            'body': 'Esta es una notificación de prueba de IAGES',
            'icon': '/icons/web-app-manifest-192x192.png',
            'badge': '/icons/favicon-96x96.png',
            'data': {
                'url': '/dashboard',
                'type': 'test'
            }
        }
        
        sent = PushNotificationService.send_to_user(current_user.id, notification)
        
        return jsonify({
            'success': sent > 0,
            'message': f'Notificación enviada a {sent} dispositivo(s)'
        })
    
    # ==========================================
    # NOTIFICACIONES CONTEXTUALES DE DOCUMENTOS
    # ==========================================
    
    @app.route('/api/documents/<int:doc_id>/notify', methods=['POST'])
    @login_required
    def notify_document(doc_id):
        """Enviar notificación instantánea sobre un documento"""
        from services.push_notification_service import notify_document_available
        from models import Documento, Empresa, User
        
        # Verificar que el usuario es Jefatura o Super Admin
        departamento_nombre = current_user.departamento.nombre if current_user.departamento else None
        if not (current_user.is_super_admin or departamento_nombre == 'Jefatura'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        # Obtener documento
        documento = Documento.query.get_or_404(doc_id)
        
        # Verificar que pertenece a la gestoría del usuario
        if documento.gestoria_id != current_user.gestoria_id:
            return jsonify({'success': False, 'error': 'Documento no encontrado'}), 404
        
        # Obtener empresa
        empresa = Empresa.query.get(documento.empresa_id)
        if not empresa:
            return jsonify({'success': False, 'error': 'Empresa no encontrada'}), 404
        
        # Obtener mensaje personalizado (opcional)
        data = request.get_json() or {}
        custom_message = data.get('message', '')
        
        # 🆕 CREAR COMUNICADO ESPECIAL para el documento
        from models import Comunicado
        
        comunicado = Comunicado(
            gestoria_id=current_user.gestoria_id,
            emisor_id=current_user.id,
            titulo=f"📄 Documento disponible: {documento.nombre_archivo}",
            contenido=custom_message or f"Nuevo documento de {empresa.nombre}",
            tipo='general',
            prioridad='alta',
            alcance='empresa',  # Solo usuarios con acceso a esta empresa
            filtro_id=empresa.id,
            activo=True,
            extra_data={
                'type': 'document_notification',
                'document_id': documento.id,
                'empresa_id': empresa.id,
                'empresa_nombre': empresa.nombre,
                'documento_nombre': documento.nombre_archivo,
                'documento_categoria': documento.categoria
            }
        )
        
        db.session.add(comunicado)
        db.session.commit()
        
        # Emitir notificación SocketIO (como los comunicados normales)
        notif_dict = {
            'id': f"doc-{comunicado.id}",
            'titulo': comunicado.titulo,
            'mensaje': comunicado.contenido[:100] + ('...' if len(comunicado.contenido) > 100 else ''),
            'tipo': 'document_notification',
            'link': '/empresas',
            'fecha': comunicado.fecha_creacion.isoformat() + 'Z',
            'is_comunicado': True,
            'document_id': documento.id
        }
        
        # 1. Notificar a Jefatura/Staff de la gestoría
        socketio.emit('nueva_notificacion', notif_dict, room=f'gestoria_{current_user.gestoria_id}')
        
        # 2. Notificar individualmente a cada invitado con acceso a esta empresa
        from models import User
        invitados = User.query.filter(User.departamento.has(nombre='Invitado')).all()
        for inv in invitados:
            if inv.has_access_to_company(empresa.id):
                socketio.emit('nueva_notificacion', notif_dict, room=f'user_{inv.id}')
        
        # 🔥 Enviar push notification (como los comunicados)
        from services.push_notification_service import PushNotificationService
        
        push_data = {
            'title': f'📁 Documento disponible',
            'body': f'{documento.nombre_archivo} de {empresa.nombre}',
            'icon': '/logo-light.png',
            'badge': '/notification-badge.png',
            'data': {
                'url': '/empresas',  # Ir al muro de comunicados
                'type': 'document_notification',
                'document_id': documento.id
            }
        }
        
        # Enviar notificación segmentada por empresa (igual que Comunicados)
        total_sent = PushNotificationService.send_segmented_push(
            gestoria_id=current_user.gestoria_id,
            alcance='empresa',
            filtro_id=empresa.id,
            notification_data=push_data,
            exclude_user_id=current_user.id  # No enviar al que notifica
        )
        
        # Registrar en audit log
        app.logger.info(f"Usuario {current_user.id} notificó documento {doc_id} a {total_sent} usuarios de empresa {empresa.id}")
        
        return jsonify({
            'success': True,
            'message': f'Notificación enviada a {total_sent} usuario(s)',
            'users_notified': total_sent
        })
    
    @app.route('/api/documents/<int:doc_id>/schedule-notification', methods=['POST'])
    @login_required
    def schedule_document_notification(doc_id):
        """Programar notificaciones de recordatorio para un documento"""
        from models import Documento, Empresa, User, ScheduledNotification
        from datetime import datetime, timedelta
        
        # Verificar que el usuario es Jefatura o Super Admin
        departamento_nombre = current_user.departamento.nombre if current_user.departamento else None
        if not (current_user.is_super_admin or departamento_nombre == 'Jefatura'):
            return jsonify({'success': False, 'error': 'No autorizado'}), 403
        
        # Obtener documento
        documento = Documento.query.get_or_404(doc_id)
        
        # Verificar que pertenece a la gestoría del usuario
        if documento.gestoria_id != current_user.gestoria_id:
            return jsonify({'success': False, 'error': 'Documento no encontrado'}), 404
        
        # Obtener parámetros
        data = request.get_json()
        reminder_days = data.get('reminder_days', [7, 1])  # Por defecto: 7 días y 1 día antes
        deadline = data.get('deadline')  # Fecha de vencimiento (ISO format)
        
        if not deadline:
            return jsonify({'success': False, 'error': 'Fecha de vencimiento requerida'}), 400
        
        try:
            deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        except:
            return jsonify({'success': False, 'error': 'Formato de fecha inválido'}), 400
        
        # Obtener empresa
        empresa = Empresa.query.get(documento.empresa_id)
        
        # Obtener usuarios que recibirán las notificaciones (mismo método que Comunicados)
        from services.push_notification_service import PushNotificationService
        from models import User
        
        # Obtener todos los usuarios activos con acceso a esta empresa
        query = User.query.filter_by(gestoria_id=current_user.gestoria_id, activo=True)
        all_users = query.all()
        
        app.logger.info(f"📋 Programando recordatorios para documento {doc_id} de empresa {empresa.nombre}")
        app.logger.info(f"   Total usuarios en gestoría: {len(all_users)}")
        
        # Filtrar usuarios que tienen acceso a esta empresa
        usuarios_notificar = []
        for user in all_users:
            should_notify = False
            # Jefatura / Admin ven todas las empresas
            if not user.is_invitado() or user.is_super_admin:
                should_notify = True
                app.logger.debug(f"   ✅ {user.nombre} (Jefatura/Admin)")
            else:
                # Usuarios "Invitado" verificar acceso a empresa
                should_notify = user.has_access_to_company(empresa.id)
                if should_notify:
                    app.logger.info(f"   ✅ {user.nombre} (Invitado con acceso)")
                else:
                    app.logger.debug(f"   ❌ {user.nombre} (Invitado sin acceso)")
            
            if should_notify:
                usuarios_notificar.append(user)
        
        if not usuarios_notificar:
            app.logger.warning(f"   ⚠️ No hay usuarios con acceso a empresa {empresa.id}")
            return jsonify({'success': False, 'error': 'No hay usuarios con acceso a esta empresa'}), 400
        
        app.logger.info(f"   👥 Total usuarios a notificar: {len(usuarios_notificar)}")
        
        # Crear notificaciones programadas
        notifications_created = 0
        for days_before in reminder_days:
            scheduled_date = deadline_date - timedelta(days=days_before)
            
            # Solo crear si la fecha programada es futura
            if scheduled_date > datetime.utcnow():
                for usuario in usuarios_notificar:
                    notification = ScheduledNotification(
                        document_id=documento.id,
                        user_id=usuario.id,
                        notification_type=f'deadline_{days_before}days',
                        scheduled_date=scheduled_date,
                        sent=False
                    )
                    db.session.add(notification)
                    notifications_created += 1
                    app.logger.debug(f"   📅 Programado para {usuario.nombre} ({days_before} días antes)")
        
        db.session.commit()
        
        app.logger.info(f"✅ Usuario {current_user.id} programó {notifications_created} recordatorios para documento {doc_id}")
        
        return jsonify({
            'success': True,
            'message': f'{notifications_created} recordatorio(s) programado(s)',
            'notifications_created': notifications_created
        })
    
    @app.route('/api/documents/<int:doc_id>/scheduled-notifications', methods=['GET'])
    @login_required
    def get_scheduled_notifications(doc_id):
        """Obtener notificaciones programadas para un documento"""
        from models import Documento, ScheduledNotification
        
        # Obtener documento
        documento = Documento.query.get_or_404(doc_id)
        
        # Verificar que pertenece a la gestoría del usuario
        if documento.gestoria_id != current_user.gestoria_id:
            return jsonify({'success': False, 'error': 'Documento no encontrado'}), 404
        
        # Obtener notificaciones programadas pendientes
        notifications = ScheduledNotification.query.filter_by(
            document_id=doc_id,
            sent=False
        ).order_by(ScheduledNotification.scheduled_date).all()
        
        return jsonify({
            'success': True,
            'notifications': [n.to_dict() for n in notifications]
        })
    
    return app


def register_routes(app):
    
    # ==========================================
    # HELPERS INTERNOS
    # ==========================================
    def generar_texto_email(documento: Documento):
        """
        Genera asunto y cuerpo del email usando todos los campos OCR disponibles.
        La firma se toma del modelo Gestoria (nombre + teléfono).
        """
        datos = documento.datos_extraidos or {}

        # Firma dinámica desde la gestoría
        gestoria = db.session.get(Gestoria, documento.gestoria_id)
        firma_nombre = gestoria.nombre if gestoria else 'Su Gestoría'
        firma_tel = f"\nTel {gestoria.telefono}" if gestoria and gestoria.telefono else ''

        # Asunto: usar tipo_documento extraído o fallback al nombre del archivo
        tipo = datos.get('tipo_documento') or 'Notificación'
        subject = f"{tipo}: {documento.nombre_archivo}"

        # Campos OCR que se muestran si tienen valor
        CAMPOS = [
            ('organismo_emisor',     'Organismo'),
            ('referencia',           'Referencia'),
            ('expediente',           'Expediente'),
            ('nif_destinatario',     'NIF Destinatario'),
            ('nombre_destinatario',  'Destinatario'),
            ('asunto',               'Asunto'),
            ('concepto',             'Concepto'),
            ('descripcion',          'Descripción'),
            ('importe_total_deuda',  'Importe deuda'),
            ('importe_embargado',    'Importe embargado'),
            ('importe_pagar',        'Importe a pagar'),
            ('fecha_notificacion',   'Fecha notificación'),
            ('fecha_limite',         'Fecha límite'),
            ('fecha_plazo',          'Fecha plazo'),
            ('resumen',              'Resumen'),
        ]
        lineas = [
            f"{etiqueta}: {datos[campo]}"
            for campo, etiqueta in CAMPOS
            if datos.get(campo) and str(datos[campo]).strip()
        ]

        cuerpo_datos = '\n'.join(lineas) if lineas else f"Documento: {documento.nombre_archivo}"
        return subject, f"Se adjunta la siguiente notificación:\n\n{cuerpo_datos}\n\n{firma_nombre}{firma_tel}"

    def notificar(titulo, mensaje, gestoria_id, departamento=None, user_id=None, link=None, tipo=NotificationTypes.INFO):
        """
        Crea una notificación y la emite en tiempo real por WebSocket.
        
        Args:
            titulo: Título de la notificación
            mensaje: Mensaje de la notificación
            gestoria_id: ID de la gestoría (REQUERIDO para multi-tenancy)
            departamento: Departamento al que se envía (opcional)
            user_id: ID del usuario específico (opcional)
            link: URL de la notificación (opcional)
            tipo: Tipo de notificación (NotificationTypes.INFO, NotificationTypes.WARNING, NotificationTypes.SUCCESS, NotificationTypes.ERROR)
        """
        try:
            # Crear notificación en BD
            nueva = Notificacion(
                titulo=titulo, 
                mensaje=mensaje,
                gestoria_id=gestoria_id,  # MULTI-TENANT
                departamento_destino=departamento,
                user_id=user_id, 
                link=link, 
                tipo=tipo
            )
            db.session.add(nueva)
            db.session.commit()
            
            # ✅ NUEVO: Emitir notificación por WebSocket en tiempo real
            notificacion_dict = nueva.to_dict()
            
            if user_id:
                # Enviar a usuario específico
                socketio.emit('nueva_notificacion', notificacion_dict, room=f'user_{user_id}')
                print(f"🔔 Notificación enviada a user_{user_id}: {titulo}")
            elif departamento:
                # Enviar a todo el departamento
                socketio.emit('nueva_notificacion', notificacion_dict, room=f'departamento_{departamento}')
                print(f"🔔 Notificación enviada a departamento_{departamento}: {titulo}")
                
        except Exception as e:
            logger.error(f"Error creando notificación: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

    # ==========================================
    # 1. AUTENTICACIÓN Y USUARIOS
    # ==========================================
    
    @app.route('/api/auth/login', methods=['POST'])
    @limiter.limit(lambda: "5 per minute" if not current_app.debug else "20 per minute")
    def login():
        """
        Login con protección contra timing attacks
        """
        import time
        from werkzeug.security import check_password_hash, generate_password_hash

        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({NotificationTypes.ERROR: 'Email y password son requeridos'}), 400

        # Normalizar email a minúsculas (case-insensitive login)
        email = email.strip().lower()

        # Buscar usuario (case-insensitive en PostgreSQL)
        user = User.query.filter(func.lower(User.email) == email).first()
        
        # Protección contra timing attacks
        # Siempre ejecutar check_password (aunque user sea None)
        if user:
            password_valid = user.check_password(password)
        else:
            # Fake check para mantener tiempo constante
            dummy_hash = generate_password_hash('dummy_password_for_timing')
            check_password_hash(dummy_hash, password)
            password_valid = False
        
        # Agregar delay aleatorio pequeño (0.1-0.2 segundos)
        # Basado en hash del email para consistencia
        delay = 0.1 + (hash(email) % 100) / 1000
        time.sleep(delay)
        
        # Validar credenciales
        if not user or not password_valid:
            return jsonify({NotificationTypes.ERROR: 'Credenciales inválidas'}), 401
        
        # Verificar si el usuario está activo
        if not user.activo:
            return jsonify({NotificationTypes.ERROR: "Usuario desactivado"}), 403

        # Verificar si la gestoría del usuario está activa
        if user.gestoria_id and not user.is_super_admin:
            gestoria = Gestoria.query.get(user.gestoria_id)
            if gestoria and not gestoria.activa:
                return jsonify({
                    NotificationTypes.ERROR: "Tu gestoría está inactiva. Contacta con el administrador del sistema."
                }), 403

        # ⭐ NUEVO: Verificar si tiene 2FA activado
        if user.two_factor_enabled:
            # Guardar user_id en sesión temporal (NO hacer login aún)
            session['2fa_user_id'] = user.id
            return jsonify({
                'success': True,
                'requires_2fa': True,
                'message': 'Ingresa el código de tu aplicación de autenticación'
            }), 200
        
        # Login normal sin 2FA
        login_user(user, remember=bool(data.get('remember', False)))
        session.permanent = True
        cache.delete(f'user_permissions_{user.id}')
        
        # ⭐ NUEVO: Verificar tareas vencidas y crear notificaciones
        try:
            from models import Tarea, Notificacion
            from datetime import datetime
            
            hoy = datetime.now()
            
            # Buscar tareas vencidas del usuario
            tareas_vencidas = Tarea.query.filter(
                Tarea.asignado_a_id == user.id,
                Tarea.fecha_vencimiento < hoy,
                Tarea.estado.in_([TaskStates.PENDIENTE, TaskStates.EN_PROGRESO])
            ).all()
            
            if tareas_vencidas:
                # Verificar si ya existe notificación para cada tarea vencida
                notificaciones_creadas = 0
                for tarea in tareas_vencidas:
                    # Buscar si ya hay notificación de esta tarea (hoy)
                    notif_existente = Notificacion.query.filter_by(
                        user_id=user.id,
                        tipo='tarea_vencida'
                    ).filter(
                        Notificacion.titulo.like(f'%{tarea.titulo[:20]}%'),
                        Notificacion.fecha_creacion >= hoy.replace(hour=0, minute=0, second=0)
                    ).first()
                    
                    if not notif_existente:
                        # Calcular días vencida
                        dias_vencida = (hoy.date() - tarea.fecha_vencimiento.date()).days
                        
                        # Usar gestoria_id de la tarea (más seguro que del usuario)
                        # Si la tarea no tiene gestoria_id, usar 1 como fallback
                        gestoria_id_notif = tarea.gestoria_id if tarea.gestoria_id else 1
                        
                        # Crear notificación
                        nueva_notif = Notificacion(
                            user_id=user.id,
                            gestoria_id=gestoria_id_notif,
                            tipo='tarea_vencida',
                            titulo=f'⚠️ Tarea vencida',
                            mensaje=f'{tarea.titulo} - Vencida hace {dias_vencida} día(s)',
                            link=f'/calendario',
                            leida=False
                        )
                        db.session.add(nueva_notif)
                        notificaciones_creadas += 1
                
                if notificaciones_creadas > 0:
                    db.session.commit()
        except Exception as e:
            print(f"Error creando notificaciones de tareas vencidas: {e}")
            # No bloquear el login si falla la creación de notificaciones
        
        # Auditar login
        auditar('login', 'auth')
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })

    @app.route('/api/auth/logout', methods=['POST'])
    @login_required
    def logout():
        if current_user.is_authenticated:
            cache.delete(f'user_permissions_{current_user.id}')
        logout_user()
        return jsonify({NotificationTypes.SUCCESS: True}), 200
    
    @app.route('/api/auth/status', methods=['GET'])
    def auth_status():
        if current_user.is_authenticated:
            return jsonify({NotificationTypes.SUCCESS: True, "user": current_user.to_dict_session()}), 200
        return jsonify({NotificationTypes.ERROR: "No autenticado"}), 401

    # ==================== PASSWORD RESET ====================
    
    @app.route('/api/auth/forgot-password', methods=['POST'])
    @limiter.limit("3 per hour")  # Límite estricto para prevenir abuso
    def forgot_password():
        """
        Solicita reset de contraseña - Envía email con token
        """
        import secrets
        from datetime import datetime, timedelta
        from email_sender import enviar_email
        
        data = request.json
        email = (data.get('email') or '').strip().lower()

        if not email:
            return jsonify({'error': 'Email requerido'}), 400

        user = User.query.filter(func.lower(User.email) == email).first()
        
        # ⚠️ SEGURIDAD: No revelar si el email existe o no
        # Siempre devolver el mismo mensaje
        if user:
            import hashlib
            # Generar token seguro (se envía al usuario en el email)
            reset_token = secrets.token_urlsafe(32)

            # Guardar solo el hash SHA-256 en BD (el token en claro nunca toca la BD)
            user.reset_token = hashlib.sha256(reset_token.encode()).hexdigest()
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()

            # Enviar email con el token en claro
            reset_url = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/reset-password?token={reset_token}"
            
            try:
                enviar_email(
                    destinatario=user.email,
                    asunto='Recuperación de contraseña - IAGES',
                    cuerpo_html=f'''
                    <h2>Recuperación de contraseña</h2>
                    <p>Hola {user.nombre},</p>
                    <p>Recibimos una solicitud para restablecer tu contraseña.</p>
                    <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                    <p><a href="{reset_url}">Restablecer contraseña</a></p>
                    <p>Este enlace expira en 1 hora.</p>
                    <p>Si no solicitaste este cambio, ignora este email.</p>
                    <br>
                    <p>Saludos,<br>Equipo IAGES</p>
                    '''
                )
            except Exception as e:
                print(f"Error enviando email de reset: {e}")
                # No revelar el error al usuario
        
        # Siempre devolver el mismo mensaje (seguridad)
        return jsonify({
            'success': True,
            'message': 'Si el email existe, recibirás instrucciones para restablecer tu contraseña'
        }), 200
    
    @app.route('/api/auth/validate-reset-token', methods=['GET'])
    def validate_reset_token():
        """
        Valida si un token de reset está activo y no ha caducado.
        Usado por el frontend para redirigir inmediatamente si el token es inválido.
        """
        import hashlib
        from datetime import datetime
        token = request.args.get('token')

        if not token:
            return jsonify({'valid': False, 'error': 'Token no proporcionado'}), 400

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = User.query.filter_by(reset_token=token_hash).first()

        if not user:
            return jsonify({'valid': False, 'error': 'Token inválido o ya utilizado'}), 400

        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'valid': False, 'error': 'El enlace ha caducado. Solicita uno nuevo.'}), 400

        return jsonify({'valid': True}), 200

    @app.route('/api/auth/reset-password', methods=['POST'])
    @limiter.limit("5 per hour")
    def reset_password():
        """
        Restablece la contraseña usando el token con validación de fortaleza
        """
        import hashlib
        from datetime import datetime
        from utils.password_validator import validate_password_strength

        data = request.json
        token = data.get('token')
        new_password = data.get('password')

        if not token or not new_password:
            return jsonify({'error': 'Token y contraseña requeridos'}), 400

        # Comparar hash del token recibido con el hash almacenado en BD
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = User.query.filter_by(reset_token=token_hash).first()
        
        if not user:
            return jsonify({'error': 'Token inválido o expirado'}), 400
        
        # Verificar si el token ha expirado
        if user.reset_token_expiry < datetime.utcnow():
            return jsonify({'error': 'Token expirado. Solicita uno nuevo'}), 400
        
        # ⚠️ SEGURIDAD: Validar fortaleza de contraseña
        is_valid, errors = validate_password_strength(
            password=new_password,
            username=user.username if hasattr(user, 'username') else None,
            email=user.email
        )
        
        if not is_valid:
            return jsonify({
                'error': 'Contraseña no cumple con los requisitos de seguridad',
                'errors': errors
            }), 400
        
        # Cambiar contraseña
        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        # Auditar
        registrar_auditoria(
            accion='password_reset',
            entidad_tipo='auth',
            entidad_id=user.id,
            descripcion=f'Usuario {user.email} restableció su contraseña',
            user_id=user.id,
            user_email=user.email,
            user_nombre=user.nombre,
            gestoria_id=user.gestoria_id
        )
        
        return jsonify({
            'success': True,
            'message': 'Contraseña restablecida exitosamente'
        }), 200

    # ==================== USER REGISTRATION ====================
    
    @app.route('/api/auth/register', methods=['POST'])
    @login_required
    @admin_required
    def register_user():
        """
        Registra un nuevo usuario (solo administradores)
        Permite a usuarios de Jefatura y Super-Admins crear usuarios en su gestoría.
        También permite a Administradores de Grupo crear invitados.
        """
        try:
            data = request.json
            
            # Validar campos requeridos
            nombre = data.get('nombre', '').strip()
            email = data.get('email', '').strip().lower()
            password = data.get('password', '').strip()
            departamento_id = data.get('departamento_id')
            
            if not all([nombre, email, password, departamento_id]):
                return jsonify({'error': 'Todos los campos son requeridos'}), 400
            
            # Validar formato de email
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email):
                return jsonify({'error': 'El email no es válido'}), 400
            
            # Validar longitud de contraseña
            if len(password) < 6:
                return jsonify({'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
            
            # Verificar que el email no exista
            if User.query.filter_by(email=email).first():
                return jsonify({'error': 'El email ya está registrado'}), 400
            
            # Verificar que el departamento existe
            departamento = Departamento.query.get(departamento_id)
            if not departamento:
                return jsonify({'error': 'Departamento no válido'}), 400
            
            # Obtener gestoría del usuario actual
            gestoria_id = current_user.gestoria_id
            
            # ✅ VALIDACIÓN DE PERMISOS PARA ADMIN DE GRUPO
            is_jefatura_or_higher = not current_user.is_invitado() or current_user.is_super_admin
            managed_group_ids = current_user.get_managed_group_ids()
            
            if not is_jefatura_or_higher:
                if not managed_group_ids:
                    return jsonify({'error': 'No tienes permisos para crear usuarios'}), 403
                
                # Un admin de grupo SOLO puede crear "Invitados"
                invitado_dept = Departamento.query.filter_by(nombre='Invitado').first()
                if not invitado_dept or departamento_id != invitado_dept.id:
                    return jsonify({'error': 'Solo puedes crear usuarios del departamento Invitado'}), 403
            
            # ⭐ IMPORTANTE: Verificar límite de usuarios de la gestoría
            from utils_limits import validate_gestoria_limit
            puede_crear, mensaje_error = validate_gestoria_limit(gestoria_id, 'usuarios')
            if not puede_crear:
                return jsonify({'error': mensaje_error}), 403
            
            # Crear nuevo usuario
            nuevo_usuario = User(
                nombre=nombre,
                email=email,
                departamento_id=departamento_id,
                gestoria_id=gestoria_id,
                activo=True
            )
            nuevo_usuario.set_password(password)
            
            db.session.add(nuevo_usuario)
            db.session.flush() # Para obtener el ID

            # ✅ SI ES ADMIN DE GRUPO: Asignar accesos automáticamente
            if not is_jefatura_or_higher and managed_group_ids:
                from models import UserGrupoAcceso
                for g_id in managed_group_ids:
                    db.session.add(UserGrupoAcceso(user_id=nuevo_usuario.id, grupo_id=g_id))
            
            db.session.commit()
            
            # Auditar
            registrar_auditoria(
                accion='crear_usuario',
                entidad_tipo='user',
                entidad_id=nuevo_usuario.id,
                descripcion=f'Usuario {email} creado por {current_user.email}'
            )
            
            logger.info(f"Usuario creado: {email} en gestoría {gestoria_id} por {current_user.email}")
            
            return jsonify({
                'success': True,
                'message': f'Usuario {nombre} creado exitosamente',
                'usuario': {
                    'id': nuevo_usuario.id,
                    'nombre': nuevo_usuario.nombre,
                    'email': nuevo_usuario.email,
                    'departamento': departamento.nombre,
                    'activo': nuevo_usuario.activo
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear usuario: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Error al crear el usuario'}), 500
    
        # ==================== 2FA ENDPOINTS ====================

    @app.route('/api/auth/2fa/setup', methods=['POST'])
    @login_required
    def setup_2fa():
        """
        Inicia el proceso de configuración de 2FA
        Genera secret y QR code
        """
        from services.totp_service import TOTPService
        
        try:
            # Generar secret
            secret = TOTPService.generate_secret()
            
            # Generar QR code
            qr_code = TOTPService.generate_qr_code(secret, current_user.email)
            
            # Guardar secret temporalmente en sesión (no en BD aún)
            session['temp_2fa_secret'] = secret
            
            return jsonify({
                'success': True,
                'secret': secret,  # Para entrada manual
                'qr_code': qr_code  # Base64 image
            })
        except Exception as e:
            print(f"Error en setup_2fa: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/2fa/verify-setup', methods=['POST'])
    @login_required
    def verify_2fa_setup():
        """
        Verifica el código TOTP y activa 2FA
        """
        from services.totp_service import TOTPService
        
        data = request.json
        token = data.get('token')
        
        if not token:
            return jsonify({'error': 'Token requerido'}), 400
        
        # Obtener secret temporal
        secret = session.get('temp_2fa_secret')
        if not secret:
            return jsonify({'error': 'Sesión expirada. Inicia el proceso nuevamente'}), 400
        
        
        # Limpiar token (remover espacios y caracteres no numéricos)
        token = str(token).strip().replace(' ', '').replace('-', '')
        
        # Debug logging
        print(f"🔐 DEBUG 2FA:")
        print(f"   Token recibido: '{token}' (len={len(token)})")
        print(f"   Secret: {secret[:10]}...")
        
        # Obtener token actual para comparación
        from services.totp_service import TOTPService as TOTP_Debug
        current_token = TOTP_Debug.get_current_token(secret)
        print(f"   Token esperado: {current_token}")
        
        # Verificar token
        if not TOTPService.verify_token(secret, token):
            print(f"   ❌ Token inválido")
            return jsonify({'error': f'Código inválido. Esperado: {current_token}'}), 400
        
        print(f"   ✅ Token válido")
        
        try:
            # Encriptar y guardar secret
            encryption_key = app.config['TOTP_ENCRYPTION_KEY']
            encrypted_secret = TOTPService.encrypt_secret(secret, encryption_key)
            
            # Generar códigos de respaldo
            backup_codes = TOTPService.generate_backup_codes()

            # Activar 2FA
            current_user.two_factor_enabled = True
            current_user.two_factor_secret = encrypted_secret
            current_user.set_backup_codes(backup_codes)  # FIX A-4: encriptado en BD
            current_user.two_factor_enabled_at = datetime.utcnow()
            
            db.session.commit()
            
            # Limpiar sesión
            session.pop('temp_2fa_secret', None)
            
            # Auditar
            auditar('activar_2fa', 'user')
            
            return jsonify({
                'success': True,
                'backup_codes': backup_codes,
                'message': '2FA activado exitosamente'
            })
        except Exception as e:
            db.session.rollback()
            print(f"Error en verify_2fa_setup: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/2fa/verify', methods=['POST'])
    def verify_2fa_login():
        """
        Verifica código 2FA durante login
        """
        from services.totp_service import TOTPService
        
        data = request.json
        token = data.get('token')
        user_id = session.get('2fa_user_id')
        
        if not user_id:
            return jsonify({'error': 'Sesión inválida'}), 400
        
        user = User.query.get(user_id)
        if not user or not user.two_factor_enabled:
            return jsonify({'error': 'Usuario inválido'}), 400
        
        try:
            # Desencriptar secret
            encryption_key = app.config['TOTP_ENCRYPTION_KEY']
            secret = TOTPService.decrypt_secret(user.two_factor_secret, encryption_key)
            
            # Verificar token TOTP
            if TOTPService.verify_token(secret, token):
                # Login exitoso
                login_user(user)
                session.pop('2fa_user_id', None)
                
                return jsonify({
                    'success': True,
                    'user': user.to_dict(),
                    'message': 'Acceso concedido'
                })
            
            # Verificar si es código de respaldo (FIX A-4: leer desencriptado)
            codes = user.get_backup_codes()
            if codes and token.upper() in codes:
                # Remover código usado de forma atómica
                remaining = [c for c in codes if c != token.upper()]
                user.set_backup_codes(remaining)

                db.session.commit()

                # Login exitoso
                login_user(user)
                session.pop('2fa_user_id', None)

                return jsonify({
                    'success': True,
                    'user': user.to_dict(),
                    'backup_code_used': True,
                    'remaining_codes': len(remaining),
                    'message': 'Acceso concedido con código de respaldo'
                })
            
            return jsonify({'error': 'Código inválido'}), 401
        except Exception as e:
            print(f"Error en verify_2fa_login: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/2fa/disable', methods=['POST'])
    @login_required
    def disable_2fa():
        """
        Desactiva 2FA (requiere contraseña)
        """
        data = request.json
        password = data.get('password')
        
        if not password or not current_user.check_password(password):
            return jsonify({'error': 'Contraseña incorrecta'}), 401
        
        try:
            # Desactivar 2FA
            current_user.two_factor_enabled = False
            current_user.two_factor_secret = None
            current_user.set_backup_codes(None)

            db.session.commit()

            # Auditar
            auditar('desactivar_2fa', 'user')
            
            return jsonify({
                'success': True,
                'message': '2FA desactivado exitosamente'
            })
        except Exception as e:
            db.session.rollback()
            print(f"Error en disable_2fa: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/2fa/regenerate-backup-codes', methods=['POST'])
    @login_required
    def regenerate_backup_codes():
        """
        Regenera códigos de respaldo (requiere contraseña)
        """
        from services.totp_service import TOTPService
        
        data = request.json
        password = data.get('password')
        
        if not password or not current_user.check_password(password):
            return jsonify({'error': 'Contraseña incorrecta'}), 401
        
        if not current_user.two_factor_enabled:
            return jsonify({'error': '2FA no está activado'}), 400
        
        try:
            # Generar nuevos códigos
            backup_codes = TOTPService.generate_backup_codes()
            current_user.set_backup_codes(backup_codes)  # FIX A-4: encriptado en BD

            db.session.commit()

            return jsonify({
                'success': True,
                'backup_codes': backup_codes,
                'message': 'Códigos de respaldo regenerados'
            })
        except Exception as e:
            db.session.rollback()
            print(f"Error en regenerate_backup_codes: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    # ==================== END 2FA ENDPOINTS ====================


    @app.route('/api/users', methods=['GET'])
    @admin_required
    def get_all_users():
        """Obtener usuarios - MULTI-TENANT: Filtrar por gestoria_id y accesos de grupo"""
        gestoria_id = current_user.gestoria_id
        
        # 1. SI ES SUPER-ADMIN O JEFATURA: Ver todos los de la gestoría
        if not current_user.is_invitado() or current_user.is_super_admin:
            users = User.query.filter_by(gestoria_id=gestoria_id).all()
        else:
            # 2. SI ES INVITADO (ADMIN DE GRUPO): Ver solo usuarios vinculados a sus grupos o empresas de sus grupos
            managed_group_ids = current_user.get_managed_group_ids()
            if not managed_group_ids:
                return jsonify({NotificationTypes.SUCCESS: True, "users": []}), 200
                
            # Buscar usuarios que tengan acceso a estos grupos
            from models import UserGrupoAcceso, UserEmpresaAcceso, Empresa
            
            # Opción A: Usuarios vinculados al grupo directamente
            u_ids_grupo = db.session.query(UserGrupoAcceso.user_id).filter(
                UserGrupoAcceso.grupo_id.in_(managed_group_ids)
            )
            
            # Opción B: Usuarios vinculados a empresas que pertenecen a esos grupos
            u_ids_empresa = db.session.query(UserEmpresaAcceso.user_id).join(Empresa).filter(
                Empresa.grupo_id.in_(managed_group_ids)
            )
            
            # Combinar ambos (UNION)
            user_ids_query = u_ids_grupo.union(u_ids_empresa).distinct()
            user_ids = [uid[0] for uid in user_ids_query.all()]
            
            # Siempre incluirse a sí mismo
            if current_user.id not in user_ids:
                user_ids.append(current_user.id)
                
            users = User.query.filter(User.id.in_(user_ids)).all()
            
        return jsonify({NotificationTypes.SUCCESS: True, "users": [u.to_dict() for u in users]}), 200

    @app.route('/api/users/<int:user_id>', methods=['PUT'])
    @admin_required
    def update_user(user_id):
        u = db.session.get(User, user_id)
        # FIX C-3: Validar que el usuario pertenece a la gestoría del admin
        if not u or (not current_user.is_super_admin and u.gestoria_id != current_user.gestoria_id):
            return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        data = request.json
        if 'departamento_id' in data: u.departamento_id = data['departamento_id']
        if 'activo' in data: u.activo = bool(data['activo'])

        # Permitir a Admins/Jefatura cambiar la contraseña manualmente
        if 'password' in data and data['password']:
            u.set_password(data['password'])
            registrar_auditoria('password_reset_admin', 'user', u.id, f'Admin {current_user.email} cambió la contraseña')

        db.session.commit(); return jsonify({NotificationTypes.SUCCESS: True})

    # Endpoint para que Admins desactiven 2FA de un usuario
    @app.route('/api/users/<int:user_id>/disable-2fa', methods=['POST'])
    @admin_required
    def admin_disable_user_2fa(user_id):
        u = db.session.get(User, user_id)
        # FIX C-3: Validar gestoría del usuario objetivo
        if not u or (not current_user.is_super_admin and u.gestoria_id != current_user.gestoria_id):
            return jsonify({NotificationTypes.ERROR: "Usuario no encontrado"}), 404
        
        try:
            u.two_factor_enabled = False
            u.two_factor_secret = None
            u.backup_codes = None
            db.session.commit()
            
            registrar_auditoria('admin_disable_2fa', 'user', u.id, f'Admin {current_user.email} desactivó el 2FA')
            
            return jsonify({
                "success": True, 
                "message": f"2FA desactivado correctamente para {u.nombre}"
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error desactivando 2FA por admin: {e}")
            return jsonify({"error": "Error interno al desactivar 2FA"}), 500

    @app.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
    @admin_required
    def toggle_user_status(user_id):
        u = db.session.get(User, user_id)
        # FIX C-3: Validar gestoría del usuario objetivo
        if not u or (not current_user.is_super_admin and u.gestoria_id != current_user.gestoria_id):
            return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        if u.id == current_user.id: return jsonify({NotificationTypes.ERROR: "No puedes desactivarte"}), 400
        u.activo = not u.activo; db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, "activo": u.activo})

    @app.route('/api/users/por-departamento', methods=['POST'])
    @login_required
    def get_users_by_dept():
        name = request.json.get('nombre_departamento')
        if not name: return jsonify({"users": []})
        match = re.search(r'\((.*?)\)', name); clean = match.group(1) if match else name
        dept = Departamento.query.filter_by(nombre=clean).first()
        if not dept: return jsonify({"users": []})
        
        # ⭐ MULTI-TENANT: Filtrar por gestoría del usuario actual
        gestoria_id = current_user.gestoria_id
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "users": [
                u.to_dict() for u in User.query.filter_by(
                    departamento_id=dept.id, 
                    activo=True,
                    gestoria_id=gestoria_id  # ⭐ CRÍTICO: Solo usuarios de la misma gestoría
                ).all()
            ]
        })

    @app.route('/api/users/me/update', methods=['PUT'])
    @login_required
    def update_me():
        u = db.session.get(User, current_user.id); data = request.json
        if 'nombre' in data: u.nombre = data['nombre']
        
        # ⭐ NUEVO: Permitir cambiar el email
        if 'email' in data:
            new_email = data['email'].strip().lower()
            if new_email and new_email != u.email:
                existing = User.query.filter_by(email=new_email).first()
                if existing:
                    # Generic error to prevent email enumeration
                    return jsonify({'error': 'No ha sido posible actualizar la dirección de correo electrónico.'}), 400
                u.email = new_email
                
        if 'password' in data and data['password']: u.set_password(data['password'])
        if 'preferencias' in data:
            u.preferencias = {**(u.preferencias or {}), **data['preferencias']}
        db.session.commit(); return jsonify({NotificationTypes.SUCCESS: True, "user": u.to_dict()})

    # ==========================================
    # 2. EMPRESAS Y DEPARTAMENTOS
    # ==========================================

    @app.route('/api/departamentos', methods=['GET'])
    @login_required
    def get_departamentos():
        """Obtiene todos los departamentos con sus usuarios activos - MULTI-TENANT"""
        # ⭐ MULTI-TENANT: Obtener gestoría del usuario actual
        gestoria_id = current_user.gestoria_id
        
        departamentos = Departamento.query.all()
        result = []
        
        for dept in departamentos:
            # ⭐ Filtrar departamento "Soporte" para usuarios normales
            # Solo super-admins pueden ver y crear usuarios de soporte
            if dept.nombre == 'Soporte' and not current_user.is_super_admin:
                continue
                
            usuarios = []
            for user in dept.usuarios:
                # ⭐ CRÍTICO: Solo usuarios de la misma gestoría
                if user.activo and user.gestoria_id == gestoria_id:
                    usuarios.append({
                        'id': user.id,
                        'nombre': user.nombre,
                        'email': user.email
                    })
            
            result.append({
                'id': dept.id,
                'nombre': dept.nombre,
                'usuarios': usuarios
            })
        
        return jsonify({NotificationTypes.SUCCESS: True, 'departamentos': result}), 200
    
    @app.route('/api/empresas/<int:empresa_id>/toggle-status', methods=['POST'])
    @login_required
    def toggle_empresa_status(empresa_id):
        """Alterna el estado activo/inactivo de una empresa"""
        from tenant_utils import require_gestoria_ownership
        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            return jsonify({NotificationTypes.ERROR: 'Empresa no encontrada'}), 404
        
        try:
            require_gestoria_ownership(empresa)
        except PermissionError:
            return jsonify({NotificationTypes.ERROR: 'No tienes permiso para modificar esta empresa'}), 403
            
        empresa.activa = not empresa.activa
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            'activa': empresa.activa,
            'message': f"Empresa {'activada' if empresa.activa else 'desactivada'} correctamente"
        })

    @app.route('/api/empresas', methods=['GET'])
    @login_required
    def get_empresas():
        """
        Obtiene lista de empresas con contadores de documentos
        
        Parámetros opcionales:
            page (int): Número de página para paginación (default: None = todas)
            per_page (int): Items por página (default: 50, max: 100)
        
        Returns:
            JSON con empresas y metadata de paginación (si se usa paginación)
        """
        # Condiciones de filtrado por departamento
        base = ((Documento.procesado == True) & (Documento.guardado == False) & (Documento.email_enviado == False) & (Documento.estado_tarea != None))
        cond_tarea = base if current_user.departamento.nombre == 'Jefatura' else (base & Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'))
        
        # MULTI-TENANT: Obtener gestoria_id del usuario actual
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # Query base con filtro de gestoría
        # ⭐ CARGAR TODOS LOS CAMPOS DE EMPRESA
        q = db.session.query(
            Empresa,
            func.count(Documento.id).label('total'), 
            func.count(case(((Documento.categoria == DocumentCategories.POR_PROCESAR), Documento.id), else_=None)).label('pia'), 
            func.count(case((cond_tarea, Documento.id), else_=None)).label('ptarea')
        ).select_from(Empresa).outerjoin(Documento)\
         .filter(Empresa.gestoria_id == gestoria_id)

        # ⭐ NUEVO: Filtrar por acceso de usuario invitado
        if current_user.departamento and current_user.departamento.nombre != 'Jefatura' and not current_user.is_super_admin:
            # Obtener IDs permitidos vía método del modelo
            allowed_ids = current_user.get_allowed_company_ids()
            q = q.filter(Empresa.id.in_(allowed_ids)) if allowed_ids else q.filter(Empresa.id == -1)
            
        q = q.group_by(Empresa.id, Empresa.grupo_id).order_by(Empresa.activa.desc(), Empresa.nombre.asc())
        
        # Verificar si se solicita paginación
        page = request.args.get('page', type=int)
        
        if page is not None:
            # Modo paginado
            per_page = request.args.get('per_page', 50, type=int)
            per_page = min(per_page, 100)  # Max 100 items per page
            
            total = q.count()
            items = q.order_by(Empresa.nombre).offset((page - 1) * per_page).limit(per_page).all()
            
            result = {
                'items': items,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                    'has_next': page * per_page < total,
                    'has_prev': page > 1
                }
            }
            
            return jsonify({
                NotificationTypes.SUCCESS: True, 
                "items": [{
                    **r[0].to_dict_simple(),
                    'total_documentos': r.total, 
                    'notificaciones_pendientes_ia': r.pia, 
                    'notificaciones_pendientes_tarea': r.ptarea
                } for r in result['items']],
                "pagination": result['pagination']
            }), 200
        else:
            # Modo legacy: devolver todas (backward compatibility)
            return jsonify({
                NotificationTypes.SUCCESS: True, 
                "empresas": [{
                    **r[0].to_dict_simple(),
                    'total_documentos': r.total, 
                    'notificaciones_pendientes_ia': r.pia, 
                    'notificaciones_pendientes_tarea': r.ptarea
                } for r in q.all()]
            }), 200

    @app.route('/api/empresas/lista-simple', methods=['GET'])
    @login_required
    def get_empresas_lista_simple():
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        q = db.session.query(Empresa.id, Empresa.nombre, Empresa.nif).filter(Empresa.gestoria_id == gestoria_id)
        
        # ⭐ NUEVO: Filtrar por acceso de administrador de grupo/invitado
        is_jefatura_or_higher = not current_user.is_invitado() or current_user.is_super_admin
        
        if not is_jefatura_or_higher:
            managed_group_ids = current_user.get_managed_group_ids()
            if managed_group_ids:
                # Si es admin de grupo, ve todas las empresas de sus grupos gestionados
                q = q.filter(Empresa.grupo_id.in_(managed_group_ids))
            else:
                # Si solo es invitado normal, ve sus empresas permitidas
                allowed_ids = current_user.get_allowed_company_ids()
                q = q.filter(Empresa.id.in_(allowed_ids)) if allowed_ids else q.filter(Empresa.id == -1)
            
        data = q.all()
        return jsonify({NotificationTypes.SUCCESS: True, "empresas": [{"id": e.id, "nombre": e.nombre, "nif": e.nif} for e in data]}), 200

    @app.route('/api/empresas/crear', methods=['POST'])
    @login_required
    def crear_empresa_manual():
        # Validar límite de empresas
        from utils.quota_utils import validate_gestoria_limit
        gestoria_id = get_current_gestoria_id()
        puede_crear, mensaje_error = validate_gestoria_limit(gestoria_id, 'empresas')
        if not puede_crear:
            return jsonify({NotificationTypes.ERROR: mensaje_error}), 403
        
        data = request.json; nombre = data.get('nombre', '').strip(); nif = data.get('nif', '').strip().upper()
        if not nombre or not nif: return jsonify({NotificationTypes.ERROR: "Faltan datos"}), 400
        if Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(or_(Empresa.nif == nif, Empresa.nombre == nombre)).first(): return jsonify({NotificationTypes.ERROR: "Existe"}), 409
        
        clean_name = limpiar_nombre_carpeta(nombre)
        path = os.path.join(app.config['RUTA_RAIZ_NOTIFICACIONES'], clean_name)
        if not os.path.exists(path): os.makedirs(path, exist_ok=True)
        for c in [DocumentCategories.NOTIFICACIONES, "Nominas", "Impuestos", "Contratos Trabajo", "Inspecciones", "Documentos Empresa", DocumentCategories.SEGUROS_SOCIALES, "Finiquitos", "Certificados Retenciones 180-190", "Aplazamiento", DocumentCategories.POR_PROCESAR]: os.makedirs(os.path.join(path, c), exist_ok=True)
        
        new_emp = Empresa(
            nombre=clean_name, 
            nif=nif, 
            email=data.get('email'),
            gestoria_id=gestoria_id
        )
        try:
            db.session.add(new_emp)
            db.session.flush()
            db.session.add(AliasNIF(nif=nif, empresa_id=new_emp.id))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error guardando nueva empresa: {e}")
            return jsonify({NotificationTypes.ERROR: "Error al guardar en base de datos"}), 500
        
        cache.delete('view_/api/empresas')
        cache.delete('view_/api/empresas/lista-simple')
        cache.delete('empresas_list')
        return jsonify({NotificationTypes.SUCCESS: True, "message": "Creada", "empresa": new_emp.to_dict_simple()})

    @app.route('/api/grupos-empresas', methods=['GET'])
    @login_required
    def get_grupos_empresas():
        """Listar grupos de empresas de la gestoría actual"""
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        q = GrupoEmpresa.query.filter_by(gestoria_id=gestoria_id)
        
        # ⭐ NUEVO: Filtrar por acceso de administrador de grupo
        is_jefatura_or_higher = not current_user.is_invitado() or current_user.is_super_admin
        if not is_jefatura_or_higher:
            managed_group_ids = current_user.get_managed_group_ids()
            if managed_group_ids:
                q = q.filter(GrupoEmpresa.id.in_(managed_group_ids))
            else:
                q = q.filter(GrupoEmpresa.id == -1) # No ve ningún grupo si no es admin de ninguno

        grupos = q.all()
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "grupos": [g.to_dict() for g in grupos]
        })

    @app.route('/api/grupos-empresas', methods=['POST'])
    @login_required
    def crear_grupo_empresa():
        """Crear una nueva agrupación (Holding)"""
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        data = request.json
        
        nombre = data.get('nombre', '').strip()
        if not nombre:
            return jsonify({NotificationTypes.ERROR: "Falta el nombre de la agrupación"}), 400
            
        new_grupo = GrupoEmpresa(
            nombre=nombre,
            descripcion=data.get('descripcion'),
            email_notificaciones=data.get('email_notificaciones'),
            usar_email_grupo=data.get('usar_email_grupo', False),
            gestoria_id=gestoria_id
        )
        
        db.session.add(new_grupo)
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "message": "Agrupación creada", 
            "grupo": new_grupo.to_dict()
        })

    # ============================================
    # MURO DE COMUNICADOS (MUCHO MÁS FLUIDO)
    # ============================================

    @app.route('/api/comunicados', methods=['GET'])
    @login_required
    def get_comunicados():
        """Obtener comunicados visibles para el usuario actual (MURO INFORMATIVO)"""
        from models import Comunicado
        gestoria_id = current_user.gestoria_id
        
        # Base: Solo activos y de su gestoría
        q = Comunicado.query.filter_by(gestoria_id=gestoria_id, activo=True)
        
        # Filtrar por alcance según los accesos del usuario
        if current_user.is_invitado() and not current_user.is_super_admin:
            allowed_company_ids = current_user.get_allowed_company_ids()
            allowed_group_ids = [ga.grupo_id for ga in current_user.grupo_accesos]
            
            from sqlalchemy import or_
            q = q.filter(or_(
                Comunicado.alcance == 'global',
                (Comunicado.alcance == 'grupo') & (Comunicado.filtro_id.in_(allowed_group_ids)),
                (Comunicado.alcance == 'empresa') & (Comunicado.filtro_id.in_(allowed_company_ids))
            ))
            
        # Ordenar por prioridad (Alta > Media > Baja) y luego por fecha
        from sqlalchemy import case
        prioridad_order = case(
            (Comunicado.prioridad == 'alta', 0),
            (Comunicado.prioridad == 'media', 1),
            (Comunicado.prioridad == 'baja', 2),
            else_=3
        )
        
        comunicados = q.order_by(prioridad_order.asc(), Comunicado.fecha_creacion.desc()).limit(15).all()
        return jsonify({NotificationTypes.SUCCESS: True, "comunicados": [c.to_dict() for c in comunicados]})

    @app.route('/api/admin/comunicados', methods=['POST'])
    @admin_required
    def crear_comunicado():
        """Crear comunicado masivo (solo Jefatura/Admin)"""
        from models import Comunicado
        data = request.json
        gestoria_id = current_user.gestoria_id
        
        nuevo = Comunicado(
            gestoria_id=gestoria_id,
            emisor_id=current_user.id,
            titulo=data.get('titulo'),
            contenido=data.get('contenido'),
            tipo=data.get('tipo', 'general'),
            prioridad=data.get('prioridad', 'media'),
            alcance=data.get('alcance', 'global'),
            filtro_id=data.get('filtro_id')
        )
        
        db.session.add(nuevo)
        db.session.commit()
        
        # ⭐ Emitir notificación por SocketIO a toda la gestoría
        try:
            notif_dict = {
                'id': f"com-{nuevo.id}",
                'titulo': f"📢 {nuevo.titulo}",
                'mensaje': nuevo.contenido[:100] + ('...' if len(nuevo.contenido) > 100 else ''),
                'tipo': 'comunicado',
                'link': '/empresas',
                'fecha': nuevo.fecha_creacion.isoformat() + 'Z',
                'is_comunicado': True
            }
            socketio.emit('nueva_notificacion', notif_dict, room=f'gestoria_{gestoria_id}')
            
            # 🔥 ENVIAR PUSH REAL (PWA / Celular)
            from services.push_notification_service import PushNotificationService
            push_data = {
                'title': f'📢 {nuevo.titulo}',
                'body': nuevo.contenido[:150] + ('...' if len(nuevo.contenido) > 150 else ''),
                'data': {
                    'url': '/empresas',
                    'type': 'comunicado',
                    'id': nuevo.id
                }
            }
            # No enviamos al emisor (quien lo crea)
            PushNotificationService.send_segmented_push(
                gestoria_id=gestoria_id,
                alcance=nuevo.alcance,
                filtro_id=nuevo.filtro_id,
                notification_data=push_data,
                exclude_user_id=current_user.id
            )
            
        except Exception as e:
            logger.error(f"Error emitiendo notificaciones para comunicado: {e}")

        return jsonify({NotificationTypes.SUCCESS: True, "message": "Comunicado publicado", "comunicado": nuevo.to_dict()})

    @app.route('/api/admin/comunicados/<int:id>', methods=['DELETE'])
    @admin_required
    def eliminar_comunicado(id):
        """Eliminar un comunicado"""
        from models import Comunicado
        com = db.session.get(Comunicado, id)
        if not com or com.gestoria_id != current_user.gestoria_id:
            return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
            
        db.session.delete(com)
        db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, "message": "Comunicado eliminado"})

    @app.route('/api/comunicados/<int:id>/leer', methods=['POST'])
    @login_required
    def marcar_comunicado_leido(id):
        """Marcar un comunicado como leído por el usuario actual"""
        from models import Comunicado
        com = db.session.get(Comunicado, id)
        if not com or com.gestoria_id != current_user.gestoria_id:
            return jsonify({NotificationTypes.ERROR: "Comunicado no encontrado"}), 404
        
        # Agregar usuario a la lista de lectura si no está
        leido_por = list(com.leido_por) if com.leido_por else []
        if current_user.id not in leido_por:
            leido_por.append(current_user.id)
            com.leido_por = leido_por
            # db.session.add(com) # SQLAlchemy usually detects change in JSON if assigned
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(com, "leido_por")
            db.session.commit()
            
        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/grupos-empresas/<int:id>', methods=['PUT', 'PATCH'])
    @login_required
    def actualizar_grupo_empresa(id):
        """Actualizar datos de una agrupación"""
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        grupo = GrupoEmpresa.query.get(id)
        
        if not grupo or grupo.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: "Agrupación no encontrada"}), 404
            
        data = request.json
        if 'nombre' in data: grupo.nombre = data['nombre'].strip()
        if 'descripcion' in data: grupo.descripcion = data['descripcion']
        if 'email_notificaciones' in data: grupo.email_notificaciones = data['email_notificaciones']
        if 'usar_email_grupo' in data: grupo.usar_email_grupo = data['usar_email_grupo']
        
        db.session.commit()
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "message": "Agrupación actualizada", 
            "grupo": grupo.to_dict()
        })

    @app.route('/api/grupos-empresas/<int:id>', methods=['DELETE'])
    @login_required
    def eliminar_grupo_empresa(id):
        """Eliminar una agrupación (las empresas quedan huérfanas pero no se borran)"""
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        grupo = GrupoEmpresa.query.get(id)
        
        if not grupo or grupo.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: "Agrupación no encontrada"}), 404
            
        # Desvincular empresas
        Empresa.query.filter_by(grupo_id=id).update({Empresa.grupo_id: None})
        
        db.session.delete(grupo)
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, "message": "Agrupación eliminada"})

    @app.route('/api/grupos-empresas/<int:id>/asignar', methods=['POST'])
    @login_required
    def asignar_empresas_a_grupo(id):
        """Asignar múltiples empresas a un grupo"""
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        grupo = GrupoEmpresa.query.get(id)
        
        if not grupo or grupo.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: "Agrupación no encontrada"}), 404
            
        data = request.json
        empresa_ids = data.get('empresa_ids', [])
        
        if not empresa_ids:
            return jsonify({NotificationTypes.ERROR: "No se enviaron IDs de empresas"}), 400
            
        # Actualizar empresas que pertenecen a esta gestoría
        Empresa.query.filter(
            Empresa.id.in_(empresa_ids),
            Empresa.gestoria_id == gestoria_id
        ).update({Empresa.grupo_id: id}, synchronize_session=False)
        
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, "message": f"{len(empresa_ids)} empresas asignadas al grupo"})

    @app.route('/api/empresas/<int:id>', methods=['GET'])
    @login_required
    @cache.cached(timeout=300, key_prefix='empresa_%s')
    def get_empresa(id):
        """Obtener empresa - MULTI-TENANT: Validar gestoría"""
        e = db.session.get(Empresa, id)
        # MULTI-TENANT: Verificar que la empresa pertenece a la gestoría actual
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-email', methods=['POST'])
    @login_required
    def actualizar_email_empresa(id):
        """Actualizar email - MULTI-TENANT: Validar gestoría"""
        e = db.session.get(Empresa, id)
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        e.email = request.json.get('email')
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/agregar-email', methods=['POST'])
    @login_required
    def agregar_email_extra(id):
        e = db.session.get(Empresa, id)
        # FIX IDOR: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        new = request.json.get('email')
        if new and new not in (e.emails_extra or []):
            l = list(e.emails_extra or []); l.append(new); e.emails_extra = l; db.session.commit(); cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/eliminar-email', methods=['POST'])
    @login_required
    def eliminar_email_extra(id):
        e = db.session.get(Empresa, id)
        # FIX IDOR: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        email_eliminar = request.json.get('email')
        if e.emails_extra and email_eliminar in e.emails_extra:
            emails = list(e.emails_extra)
            emails.remove(email_eliminar)
            e.emails_extra = emails
            db.session.commit()
            cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-cuenta-cotizacion', methods=['POST'])
    @login_required
    def actualizar_cuenta_cotizacion(id):
        e = db.session.get(Empresa, id)
        # FIX IDOR: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        e.cuenta_cotizacion = request.json.get('cuenta_cotizacion')
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-cert-secret', methods=['POST'])
    @login_required
    def actualizar_cert_secret(id):
        """Actualiza el cert-secret de Saltra para la empresa"""
        e = db.session.get(Empresa, id)
        # FIX C-2: Validar que la empresa pertenece a la gestoría del usuario
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404

        cert_secret = request.json.get('saltra_cert_secret', '').strip()
        e.saltra_cert_secret = cert_secret if cert_secret else None
        db.session.commit()
        cache.delete(f'empresa_{id}')

        return jsonify({
            NotificationTypes.SUCCESS: True,
            "message": "Certificado Saltra actualizado",
            "empresa": e.to_dict_simple()
        })

    @app.route('/api/empresas/<int:id>/actualizar-codigo-empresa', methods=['POST'])
    @login_required
    def actualizar_codigo_empresa(id):
        e = db.session.get(Empresa, id)
        # FIX C-2: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        e.codigo_empresa = request.json.get('codigo_empresa')
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-telefono', methods=['POST'])
    @login_required
    def actualizar_telefono(id):
        e = db.session.get(Empresa, id)
        # FIX C-2: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        e.telefono = request.json.get('telefono')
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-administrador', methods=['POST'])
    @login_required
    def actualizar_administrador(id):
        e = db.session.get(Empresa, id)
        # FIX C-2: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        e.nombre_administrador = request.json.get('nombre_administrador')
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})

    @app.route('/api/empresas/<int:id>/actualizar-campos-extra', methods=['POST'])
    @login_required
    def actualizar_campos_extra(id):
        e = db.session.get(Empresa, id)
        # FIX C-2: Validar gestoría
        if not e or e.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.SUCCESS: False, "message": "Empresa no encontrada"}), 404
        
        data = request.json
        if 'codigo_empresa' in data: e.codigo_empresa = data['codigo_empresa']
        if 'telefono' in data: e.telefono = data['telefono']
        if 'nombre_administrador' in data: e.nombre_administrador = data['nombre_administrador']
        if 'apellido_administrador' in data: e.apellido_administrador = data['apellido_administrador']
        if 'nif_administrador' in data: e.nif_administrador = data['nif_administrador']
        if 'provincia' in data: e.provincia = data['provincia']
        if 'municipio' in data: e.municipio = data['municipio']
        if 'codigo_postal' in data: e.codigo_postal = data['codigo_postal']
        if 'direccion' in data: e.direccion = data['direccion']
        if 'direccion_centros_trabajo_str' in data: e.direccion_centros_trabajo_str = data['direccion_centros_trabajo_str']
        if 'convenio_numero' in data: e.convenio_numero = data['convenio_numero']
        if 'convenio_nombre' in data: e.convenio_nombre = data['convenio_nombre']
        if 'epigrafe_iae_str' in data: e.epigrafe_iae_str = data['epigrafe_iae_str']
        if 'cnae_2009_str' in data: e.cnae_2009_str = data['cnae_2009_str']
        if 'cnae_2025_str' in data: e.cnae_2025_str = data['cnae_2025_str']
        
        if 'direcciones_sociedad' in data: e.direcciones_sociedad = data['direcciones_sociedad']
        if 'direcciones_centros_trabajo' in data: e.direcciones_centros_trabajo = data['direcciones_centros_trabajo']
        if 'epigrafes_iae' in data: e.epigrafes_iae = data['epigrafes_iae']
        if 'cnaes_2009' in data: e.cnaes_2009 = data['cnaes_2009']
        if 'cnaes_2025' in data: e.cnaes_2025 = data['cnaes_2025']

        # Sincronizar administradores JSON si se actualizaron los campos planos
        if any(k in data for k in ['nombre_administrador', 'apellido_administrador', 'nif_administrador']):
            nombres = [v.strip() for v in (e.nombre_administrador or "").split(';') if v.strip()]
            apellidos = [v.strip() for v in (e.apellido_administrador or "").split(';') if v.strip()]
            nifs = [v.strip() for v in (e.nif_administrador or "").split(';') if v.strip()]
            
            new_admins = []
            max_len = max(len(nombres), len(apellidos), len(nifs))
            for i in range(max_len):
                adm = {}
                if i < len(nombres): adm['nombre'] = nombres[i]
                if i < len(apellidos): adm['apellido'] = apellidos[i]
                if i < len(nifs): adm['cif'] = nifs[i]
                if adm: new_admins.append(adm)
            
            e.administradores = new_admins
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(e, 'administradores')
        
        db.session.commit()
        cache.delete(f'empresa_{id}')
        return jsonify({NotificationTypes.SUCCESS: True, "empresa": e.to_dict_simple()})
    @app.route('/api/empresas/<int:id>/carpetas-destino', methods=['GET'])
    @login_required
    def get_carpetas_destino(id):
        """Retorna categorías disponibles (solo metadata, no carpetas físicas)"""
        # MULTI-TENANT: Verificar que la empresa pertenece a la gestoría actual
        empresa = Empresa.query.get(id)
        if not empresa or empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        
        # Categorías exactamente como están en CategoriasView.jsx (Dashboard)
        categorias = [
            "Notificaciones",
            "Inspecciones",
            "Aplazamiento",
            "Nóminas",
            "Altas de Trabajadores",
            "Bajas de Trabajadores",
            "Cartas de Despidos",
            "Finiquitos",
            "Impuestos",
            "Seguros Sociales",
            "Contratos Trabajo",
            "Certificados de Retenciones 180",
            "Certificados de Retenciones 190",
            "Documentos Empresa",
            "Por Procesar"
        ]
        
        return jsonify({NotificationTypes.SUCCESS: True, "carpetas": categorias}), 200

    @app.route('/api/plantillas', methods=['GET'])
    @login_required
    def get_plantillas_unificadas():
        """
        Retorna una lista unificada de Plantillas (antiguas) y ExtractionTemplates (nuevas/globales)
        para el selector de 'Procesar con IA' del ModalProcesamientoUnificado.
        """
        from models import Plantilla, ExtractionTemplate, ConfiguracionPerfil
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # 1. Plantillas clásicas (de la gestoría o globales)
        plantillas_db = Plantilla.query.filter(
            (Plantilla.gestoria_id == gestoria_id) | (Plantilla.gestoria_id == None)
        ).all()
        
        # 2. ExtractionTemplates (Nuevos perfiles compartidos auto-creados)
        # Solo los que tienen perfil configurado o son auto-creados
        templates_db = ExtractionTemplate.query.all()
        
        lista_final = []
        
        # Agregar Plantillas clásicas
        for p in plantillas_db:
            lista_final.append({
                'id': p.id,
                'codigo': p.codigo,
                'nombre': p.nombre,
                'tipo': 'plantilla_ia',
                'descripcion': p.descripcion or f"Extracción {p.nombre}",
                'icon': '🤖'
            })
            
        # Agregar ExtractionTemplates (Perfiles)
        # Evitar duplicados si el código es el mismo
        codigos_vistos = {p.codigo for p in plantillas_db}
        
        for t in templates_db:
            if t.id in codigos_vistos: continue
            
            # Ver si el usuario tiene configuración local para este template
            config_local = ConfiguracionPerfil.query.filter_by(
                perfil_clave=t.id, 
                gestoria_id=gestoria_id
            ).first()
            
            lista_final.append({
                'id': t.id,
                'codigo': f"PROFILE:{t.id}", # Prefijo para que Celery lo reconozca como perfil
                'nombre': f"Perfil: {t.nombre}",
                'tipo': 'perfil_auto',
                'descripcion': f"Auto-detección: {t.nombre}",
                'configurado': config_local is not None,
                'icon': '🔍'
            })
            
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "plantillas": lista_final
        }), 200

    @app.route('/api/empresas/<int:id>/categorias-conteo', methods=['GET'])
    @login_required
    def get_categorias_conteo(id):
        """Obtener conteo de categorías - MULTI-TENANT: Validar gestoría"""
        # MULTI-TENANT: Verificar que la empresa pertenece a la gestoría actual
        empresa = Empresa.query.get(id)
        if not empresa or empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        
        # Contar documentos por categoría
        
        cats = [
            DocumentCategories.POR_PROCESAR, 
            DocumentCategories.NOTIFICACIONES, 
            "Inspecciones", 
            "Aplazamiento", 
            DocumentCategories.NOMINAS, 
            DocumentCategories.ALTAS_TRABAJADORES,
            DocumentCategories.BAJAS_TRABAJADORES, 
            "Cartas de Despidos", 
            DocumentCategories.IMPUESTOS, 
            DocumentCategories.SEGUROS_SOCIALES, 
            DocumentCategories.CONTRATOS, 
            DocumentCategories.FINIQUITOS, 
            DocumentCategories.CERTIFICADOS_180, 
            DocumentCategories.CERTIFICADOS_190, 
            "Documentos Empresa"
        ]
        
        conteos = {}

        # Aplicar filtro de departamento igual que en get_documentos_empresa
        for c in cats:
            if c == 'Aplazamiento':
                # Aplazamiento: incluir docs con categoria='Aplazamiento' O is_aplazamiento=true
                q = Documento.query.filter(
                    Documento.empresa_id == id,
                    or_(
                        Documento.categoria == 'Aplazamiento',
                        cast(Documento.datos_extraidos['is_aplazamiento'], Text) == 'true'
                    )
                )
            else:
                q = Documento.query.filter_by(empresa_id=id, categoria=c)

            # Los invitados ven todos los documentos de esa empresa. Si es empleado, se filtra por su departmamento
            if not current_user.is_invitado() and current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                q = q.filter(
                    or_(
                        Documento.estado_tarea == None,
                        Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'),
                        Documento.asignado_a_id == current_user.id
                    )
                )

            conteos[c] = q.count()
        
        return jsonify({NotificationTypes.SUCCESS: True, "conteos": conteos}), 200


    # ==========================================
    # 3. DOCUMENTOS (CORE)
    # ==========================================

    
    @app.route('/api/documentos/<int:doc_id>/pdf', methods=['GET'])
    @login_required
    def get_documento_pdf(doc_id):
        """
        Sirve el archivo PDF de un documento para visualización
        MULTI-TENANT: Validar que el documento pertenece a la gestoría del usuario
        """
        try:
            documento = Documento.query.get_or_404(doc_id)
            
            # MULTI-TENANT: Verificar que el documento pertenece a la gestoría actual
            if documento.empresa.gestoria_id != get_current_gestoria_id():
                return jsonify({NotificationTypes.ERROR: "Acceso denegado"}), 403
            
            # DEBUG: Ver qué ruta está buscando
            logger.info(f"Buscando PDF ID {doc_id}:")
            print(f"   Ruta en BD: {documento.ruta_archivo}")
            print(f"   Existe: {os.path.exists(documento.ruta_archivo)}")
            
            # Verificar que el archivo existe
            if not os.path.exists(documento.ruta_archivo):
                from utils.storage_utils import get_empresa_storage_path
                empresa_path = get_empresa_storage_path(documento.gestoria_id or documento.empresa.gestoria_id, documento.empresa.nombre)
                
                # Intentar reconstruir ruta
                rebuild = os.path.join(empresa_path, documento.categoria, documento.nombre_archivo)
                if os.path.exists(rebuild):
                    documento.ruta_archivo = rebuild
                    db.session.commit()
                else:
                    # Intentar en Por Procesar
                    rebuild_pp = os.path.join(empresa_path, "Por Procesar", documento.nombre_archivo)
                    if os.path.exists(rebuild_pp):
                        documento.ruta_archivo = rebuild_pp
                        db.session.commit()
                    else:
                        logger.error(f"Archivo no encontrado en: {documento.ruta_archivo}")
                        return jsonify({NotificationTypes.ERROR: "Archivo no encontrado"}), 404
            
            # Servir el archivo PDF
            return send_file(
                documento.ruta_archivo,
                mimetype='application/pdf',
                as_attachment=False,
                download_name=documento.nombre_archivo
            )
        
        except Exception as e:
            logger.error(f"Error sirviendo PDF: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    @app.route('/api/empresas/novedades', methods=['GET'])
    @login_required
    def get_novedades_timeline():
        """
        Obtiene el feed unificado de novedades (Documentos y Comunicados)
        para las empresas a las que el usuario tiene acceso.
        """
        from models import Documento, Comunicado, Empresa
        from sqlalchemy import or_, desc, and_
        from datetime import datetime, timedelta
        
        # Obtener parámetros del request
        dias = request.args.get('dias', default=10, type=int)
        empresa_id_filter = request.args.get('empresa_id', type=int)
        
        # Calcular fecha límite
        fecha_limite = None
        if dias > 0:
            fecha_limite = datetime.utcnow() - timedelta(days=dias)
        
        # 1. Obtener IDs de empresas permitidas para el usuario
        if current_user.is_invitado() and not current_user.is_super_admin:
            allowed_empresa_ids = current_user.get_allowed_company_ids()
        else:
            # Empleados o SuperAdmins ven todo de su gestoría
            gestoria_id = get_current_gestoria_id()
            empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
            allowed_empresa_ids = [e.id for e in empresas]
            
        # Filtrar por empresa_id si se solicita
        if empresa_id_filter:
            if empresa_id_filter in allowed_empresa_ids:
                empresa_ids = [empresa_id_filter]
            else:
                return jsonify({NotificationTypes.ERROR: "No tienes acceso a esta empresa"}), 403
        else:
            empresa_ids = allowed_empresa_ids

        if not empresa_ids:
            return jsonify({NotificationTypes.SUCCESS: True, "novedades": []}), 200
            
        novedades = []
        
        # 2. Traer Documentos Recientes
        from constants import DocumentCategories
        
        # Excluir documentos en "Por Procesar" o "Borrador/Papelera"
        filtros_docs = [
            Documento.empresa_id.in_(empresa_ids),
            Documento.categoria != DocumentCategories.POR_PROCESAR,
            Documento.categoria != 'Papelera',
            Documento.categoria != 'Borrador'
        ]
        
        if fecha_limite:
            filtros_docs.append(Documento.fecha_creacion >= fecha_limite)
            
        q_docs = Documento.query.filter(and_(*filtros_docs))
        
        # Si es empleado (no invitado) filtramos por su departamento (excepto Jefatura)
        if not current_user.is_invitado() and current_user.departamento and current_user.departamento.nombre != 'Jefatura':
            dept_name = current_user.departamento.nombre
            q_docs = q_docs.filter(or_(
                Documento.estado_tarea == None, 
                Documento.estado_tarea.ilike(f'%{dept_name}%'), 
                Documento.asignado_a_id == current_user.id
            ))
            
        # Ordenar y limitar documentos
        docs = q_docs.order_by(desc(Documento.fecha_creacion)).limit(40).all()
        
        for d in docs:
            novedades.append({
                'id': f"doc_{d.id}",
                'doc_id': d.id,
                'tipo_evento': 'Documento',
                'categoria': d.categoria,
                'titulo': d.nombre_archivo,
                'descripcion': f"Nuevo documento en {d.categoria}",
                'empresa_id': d.empresa_id,
                'empresa_nombre': d.empresa.nombre if d.empresa else 'Desconocida',
                'fecha': d.fecha_creacion.isoformat() + 'Z',
                'is_leido': getattr(d, 'leido', False),
                'prioridad': getattr(d, 'prioridad', 'informativa'),
                'link': f"/api/documentos/{d.id}/archivo"
            })
            
        # 3. Traer Comunicados Recientes
        q_com = Comunicado.query.filter_by(gestoria_id=current_user.gestoria_id, activo=True)
        if current_user.is_invitado() and not current_user.is_super_admin:
            group_ids = [ga.grupo_id for ga in current_user.grupo_accesos]
            q_com = q_com.filter(or_(
                Comunicado.alcance == 'global',
                (Comunicado.alcance == 'grupo') & (Comunicado.filtro_id.in_(group_ids)),
                (Comunicado.alcance == 'empresa') & (Comunicado.filtro_id.in_(allowed_empresa_ids))
            ))
            
            # Filtro adicional si el usuario seleccionó una empresa específica
            if empresa_id_filter:
                # Si se filtra por empresa, mostrar los globales, del grupo de esa empresa, o de esa empresa
                q_com = q_com.filter(and_(
                    or_(
                        Comunicado.alcance == 'global',
                        (Comunicado.alcance == 'empresa') & (Comunicado.filtro_id == empresa_id_filter)
                        # Nota: Comunicados de 'grupo' se filtran por los grupos del usuario invitados
                    )
                ))

            
        if fecha_limite:
            q_com = q_com.filter(Comunicado.fecha_creacion >= fecha_limite)
            
        comunicados = q_com.order_by(desc(Comunicado.fecha_creacion)).limit(10).all()
        
        for c in comunicados:
            novedades.append({
                'id': f"com_{c.id}",
                'doc_id': c.id, 
                'tipo_evento': 'Comunicado',
                'categoria': 'Comunicados',
                'titulo': c.titulo,
                'descripcion': c.contenido[:100] + '...' if len(c.contenido) > 100 else c.contenido,
                'empresa_id': c.filtro_id if c.alcance == 'empresa' else None,
                'empresa_nombre': 'Comunicado', 
                'fecha': c.fecha_creacion.isoformat() + 'Z',
                'is_leido': current_user in getattr(c, 'leido_por', []),
                'prioridad': getattr(c, 'prioridad', 'informativa'),
                'link': None # Los comunicados se ven en modal
            })
            
        # 4. Ordenar fechas descendente
        novedades.sort(key=lambda x: x['fecha'], reverse=True)
        
        return jsonify({NotificationTypes.SUCCESS: True, "novedades": novedades[:50]}), 200

    @app.route('/api/empresas/<int:id>/documentos', methods=['GET'])
    @login_required
    def get_documentos_empresa(id):
        """Obtener documentos - MULTI-TENANT: Validar gestoría"""
        # MULTI-TENANT: Verificar que la empresa pertenece a la gestoría actual
        empresa = Empresa.query.get(id)
        if not empresa or empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        
        # 🔒 VALIDAR ACCESO: Usuarios invitados solo ven documentos de sus empresas permitidas
        if current_user.is_invitado() and not current_user.is_super_admin:
            if not current_user.has_access_to_company(id):
                return jsonify({NotificationTypes.ERROR: "No tienes acceso a esta empresa"}), 403
        
        cat = request.args.get('categoria', DocumentCategories.POR_PROCESAR)
        # Si categoria='all', devolver todos los documentos de la empresa
        if cat == 'all':
            q = Documento.query.filter_by(empresa_id=id)
        elif cat == 'Aplazamiento':
            # Incluir docs con categoria='Aplazamiento' O docs de otros grupos con is_aplazamiento=true
            q = Documento.query.filter(
                Documento.empresa_id == id,
                or_(
                    Documento.categoria == 'Aplazamiento',
                    cast(Documento.datos_extraidos['is_aplazamiento'], Text) == 'true'
                )
            )
        else:
            q = Documento.query.filter_by(empresa_id=id, categoria=cat)
    
        # Empleados normales solo ven lo suyo o lo de su departamento. Invitados ven todos los documentos de la empresa.
        if not current_user.is_invitado() and current_user.departamento and current_user.departamento.nombre != 'Jefatura':
            q = q.filter(or_(Documento.estado_tarea == None, Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'), Documento.asignado_a_id == current_user.id))
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "documentos": [d.to_dict() for d in q.order_by(Documento.fecha_creacion.desc()).all()],
            "empresa": empresa.to_dict_simple()
        }), 200

    @app.route('/api/documentos/<int:doc_id>/archivo', methods=['GET'])
    @login_required
    def get_archivo_documento(doc_id):
        """Descarga o visualiza archivo - MULTI-TENANT: Validar gestoría"""
        d = db.session.get(Documento, doc_id)
        if not d: return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        
        # MULTI-TENANT: Verificar PRIMERO que el documento pertenece a la gestoría actual
        if d.empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Acceso denegado"}), 403
        
        # 🔒 VALIDAR ACCESO A EMPRESA: Usuarios invitados solo ven documentos de sus empresas
        if current_user.is_invitado() and not current_user.is_super_admin:
            if not current_user.has_access_to_company(d.empresa_id):
                return jsonify({NotificationTypes.ERROR: "No tienes acceso a esta empresa"}), 403
        
        # ✅ AUDITAR: Documento leído/visualizado
        registrar_auditoria(
            accion=AccionesAuditoria.DOCUMENTO_LEIDO,
            entidad_tipo='documento',
            entidad_id=doc_id,
            descripcion=f"Usuario visualizó el documento: {d.nombre_archivo}",
            detalles={
                'documento_id': doc_id,
                'documento_nombre': d.nombre_archivo,
                'empresa_id': d.empresa_id,
                'categoria': d.categoria
            }
        )

        if os.path.exists(d.ruta_archivo): 
            return send_file(d.ruta_archivo)

        from utils.storage_utils import get_empresa_storage_path
        empresa_path = get_empresa_storage_path(d.gestoria_id or d.empresa.gestoria_id, d.empresa.nombre)
        
        # Reconstruir ruta en la categoría actual
        rebuild = os.path.join(empresa_path, d.categoria, d.nombre_archivo)
        if os.path.exists(rebuild): 
            d.ruta_archivo = rebuild
            db.session.commit()
            return send_file(rebuild)
            
        return jsonify({NotificationTypes.ERROR: "Archivo físico no encontrado"}), 404

    @app.route('/api/documentos/enviar-multiples', methods=['POST'])
    @login_required
    def enviar_multiples_documentos():
        """
        Permite enviar múltiples documentos por correo electrónico a terceros.
        Usado principalmente desde la vista Timeline/Novedades por invitados.
        """
        try:
            data = request.json
            document_ids = data.get('document_ids', [])
            destinatarios = data.get('destinatarios', [])
            asunto = data.get('asunto', 'Compartición de Documentos')
            mensaje = data.get('mensaje', 'Se adjuntan los documentos solicitados.')
            
            print(f"[EMAIL DEBUG] user={current_user.nombre} ids={document_ids} destinos={destinatarios}")
            
            if not document_ids or not destinatarios:
                return jsonify({NotificationTypes.ERROR: "Documentos y destinatarios son requeridos"}), 400
                
            from models import Documento
            from email_sender import enviar_email_con_adjuntos
            import os
            
            # Convertir a enteros en caso de que vengan como strings
            document_ids_int = []
            for did in document_ids:
                try:
                    document_ids_int.append(int(did))
                except (ValueError, TypeError):
                    print(f"[EMAIL DEBUG] ID inválido ignorado: {did}")
            
            print(f"[EMAIL DEBUG] IDs enteros: {document_ids_int}")
            documentos = Documento.query.filter(Documento.id.in_(document_ids_int)).all()
            print(f"[EMAIL DEBUG] Documentos encontrados: {len(documentos)} de {len(document_ids_int)}")
            
            if len(documentos) != len(document_ids_int):
                return jsonify({NotificationTypes.ERROR: f"Sólo se encontraron {len(documentos)} de {len(document_ids_int)} documentos solicitados"}), 404
                
            adjuntos = []
            nombres_enviados = []
            
            for d in documentos:
                print(f"[EMAIL DEBUG] Procesando doc {d.id} empresa_id={d.empresa_id} ruta={d.ruta_archivo}")
                # 🔒 Validación estricta de acceso: misma gestoría
                if d.empresa.gestoria_id != get_current_gestoria_id():
                    return jsonify({NotificationTypes.ERROR: f"Acceso denegado al documento {d.id}"}), 403
                    
                # 🔒 Validación para invitados (solo sus empresas)
                if current_user.is_invitado() and not current_user.is_super_admin:
                    if not current_user.has_access_to_company(d.empresa_id):
                        return jsonify({NotificationTypes.ERROR: f"No tienes acceso a la empresa del documento {d.id}"}), 403
                
                # Verificar existencia física del archivo
                if not d.ruta_archivo or not os.path.exists(d.ruta_archivo):
                    print(f"[EMAIL DEBUG] Archivo no encontrado en: {d.ruta_archivo}, intentando reconstruir")
                    # Intento de reconstrucción
                    from utils.storage_utils import get_empresa_storage_path
                    empresa_path = get_empresa_storage_path(d.gestoria_id or d.empresa.gestoria_id, d.empresa.nombre)
                    rebuild = os.path.join(empresa_path, d.categoria, d.nombre_archivo)
                    print(f"[EMAIL DEBUG] Rebuild path: {rebuild} existe={os.path.exists(rebuild)}")
                    if os.path.exists(rebuild):
                        d.ruta_archivo = rebuild
                        db.session.commit()
                    else:
                        return jsonify({NotificationTypes.ERROR: f"Archivo físico '{d.nombre_archivo}' no encontrado en el servidor"}), 404
                
                # Preparar para adjuntar
                adjuntos.append({
                    'ruta': d.ruta_archivo,
                    'nombre': d.nombre_archivo
                })
                nombres_enviados.append(d.nombre_archivo)
                
            print(f"[EMAIL DEBUG] Enviando {len(adjuntos)} adjuntos a {destinatarios}")
            # Llamar al servicio de email (usará configuración de la gestoría del tenant actual)
            resultado = enviar_email_con_adjuntos(
                destinatarios=destinatarios,
                asunto=asunto,
                cuerpo=mensaje,
                adjuntos=adjuntos,
                usar_html=True,
                empresa_nombre=current_user.nombre,  # Nombre de quien lo envía
                gestoria_id=get_current_gestoria_id()
            )
            print(f"[EMAIL DEBUG] Resultado: {resultado}")
            
            if resultado.get(NotificationTypes.SUCCESS):
                # ✅ AUDITORÍA: Registrar el envío
                # Como son múltiples, registramos en uno solo, o el primero
                dest_str = ", ".join(destinatarios)
                registrar_auditoria(
                    accion=AccionesAuditoria.EMAIL_ENVIADO,
                    entidad_tipo='documento_multiples',
                    entidad_id=document_ids_int[0] if document_ids_int else None,
                    descripcion=f"{current_user.nombre} envió {len(adjuntos)} documentos por email a {dest_str}",
                    detalles={
                        'document_ids': document_ids_int,
                        'nombres_documentos': nombres_enviados,
                        'destinatarios': destinatarios
                    }
                )
                return jsonify({NotificationTypes.SUCCESS: True, "message": "Correos enviados correctamente"}), 200
            else:
                error_msg = resultado.get(NotificationTypes.ERROR, "Error al enviar correos")
                print(f"[EMAIL DEBUG] Error SMTP: {error_msg}")
                return jsonify({NotificationTypes.ERROR: error_msg}), 500
                
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[EMAIL DEBUG] EXCEPCION: {str(e)}\n{tb}")
            logger.error(f"Error en enviar_multiples_documentos: {str(e)}\n{tb}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
        rebuild = os.path.join(empresa_path, d.categoria, d.nombre_archivo)
        if os.path.exists(rebuild): 
            d.ruta_archivo = rebuild
            db.session.commit()
            return send_file(rebuild)

        # Reconstruir en Por Procesar (como fallback)
        rebuild_pp = os.path.join(empresa_path, DocumentCategories.POR_PROCESAR, d.nombre_archivo)
        if os.path.exists(rebuild_pp): 
            d.ruta_archivo = rebuild_pp
            d.categoria = DocumentCategories.POR_PROCESAR
            db.session.commit()
            return send_file(rebuild_pp)

        return jsonify({NotificationTypes.ERROR: "Físico no encontrado"}), 404

    @app.route('/api/documentos/<int:doc_id>/mover', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_ACTUALIZADO,
        entidad_tipo='documento'
    )
    def mover_documento(doc_id):
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        
        categoria_anterior = doc.categoria
        new_cat = request.json.get('categoria_destino')
        tipo_asignado = request.json.get('tipo_documento_asignado')
        
        # ✅ RUTA ROBUSTA: No confiar en doc.ruta_archivo directamente para construir el nuevo path
        from utils.storage_utils import get_empresa_storage_path, resolve_document_path
        
        orig = resolve_document_path(doc) # Asegura que tenemos la ruta real física
        if not orig or not os.path.exists(orig):
            return jsonify({NotificationTypes.ERROR: "Archivo físico no encontrado para mover"}), 404
            
        empresa_path = get_empresa_storage_path(doc.gestoria_id, doc.empresa.nombre)
        dest = os.path.join(empresa_path, new_cat, doc.nombre_archivo)
        
        if not os.path.exists(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
        
        if orig != dest:
            shutil.move(orig, dest)
            
        doc.ruta_archivo = dest
        doc.categoria = new_cat
        
        if tipo_asignado:
            meta = doc.datos_extraidos or {}
            meta['_metadata'] = meta.get('_metadata', {})
            meta['_metadata']['tipo_documento_preferido'] = tipo_asignado
            doc.datos_extraidos = dict(meta)
        
        db.session.commit()
        cache.delete(f'empresa_{doc.empresa_id}_documentos')
        
        # Detalles para auditoría
        request.auditoria_detalles = {
            'documento_id': doc_id,
            'nombre': doc.nombre_archivo,
            'de_categoria': categoria_anterior,
            'a_categoria': new_cat,
            'empresa_id': doc.empresa_id,
            'empresa_nombre': doc.empresa.nombre if doc.empresa else None
        }
        request.auditoria_entidad_id = doc_id
        
        return jsonify({NotificationTypes.SUCCESS: True}), 200

    @app.route('/api/documentos/<int:doc_id>', methods=['PUT', 'PATCH'])
    @login_required
    def update_documento_generic(doc_id):
        """Actualización genérica de documentos (Prioridad, metadatos, etc)"""
        d = db.session.get(Documento, doc_id)
        if not d: return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        
        # MULTI-TENANT: Validar gestoría
        if d.empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Acceso denegado"}), 403
            
        data = request.get_json()
        if not data:
            return jsonify({NotificationTypes.ERROR: "No data provided"}), 400
            
        # Campos admitidos para actualización rápida
        if 'prioridad' in data:
            d.prioridad = data['prioridad']
            
        if 'leido' in data:
            d.leido = data['leido']
            if d.leido:
                d.fecha_lectura = datetime.utcnow()
                d.leido_por_id = current_user.id
        
        if 'tipo_documento_asignado' in data:
            # Sincronizar con _metadata para compatibilidad con el motor de extracción
            meta = d.datos_extraidos or {}
            meta['_metadata'] = meta.get('_metadata', {})
            meta['_metadata']['tipo_documento_preferido'] = data['tipo_documento_asignado']
            d.datos_extraidos = dict(meta)

        if 'categoria' in data:
            d.categoria = data['categoria']

        db.session.commit()
        # Limpiar cache de la empresa
        cache.delete(f'empresa_{d.empresa_id}_documentos')
        
        return jsonify({NotificationTypes.SUCCESS: True}), 200

    @app.route('/api/documentos/<int:doc_id>/procesar-aplazamiento', methods=['POST'])
    @login_required
    def procesar_aplazamiento_sync(doc_id):
        """Procesa un documento como aplazamiento de forma SÍNCRONA (sin Celery)"""
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        if doc.empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
        try:
            from services.impuesto_extractor import ImpuestoExtractor
            from utils.storage_utils import resolve_document_path
            from sqlalchemy.orm.attributes import flag_modified
            pdf_path = resolve_document_path(doc)
            datos = ImpuestoExtractor().extract_tax_data(pdf_path)
            datos_previos = doc.datos_extraidos or {}
            for campo in ('email_preparado',):
                if campo in datos_previos and campo not in datos:
                    datos[campo] = datos_previos[campo]
            doc.datos_extraidos = datos
            doc.procesado = True
            flag_modified(doc, 'datos_extraidos')
            # No cambiamos categoria: doc se queda en Inspecciones
            # y aparece en Aplazamiento por el flag is_aplazamiento=true
            db.session.commit()
            cache.delete(f'empresa_{doc.empresa_id}_documentos')
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'is_aplazamiento': datos.get('is_aplazamiento', False),
                'num_liquidaciones': len(datos.get('detalle_liquidacion') or []),
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/documentos/<int:doc_id>/procesar', methods=['POST'])
    @login_required
    def procesar_documento(doc_id):
        doc = db.session.get(Documento, doc_id)
        tipo = request.json.get('tipo_documento')
        if not tipo and doc.datos_extraidos: tipo = doc.datos_extraidos.get('_metadata', {}).get('tipo_documento_preferido')
        from celery_worker import procesar_documento_async
        task = procesar_documento_async.delay(doc_id, tipo or 'notificacion_generica')
        return jsonify({NotificationTypes.SUCCESS: True, "task_id": task.id})

    @app.route('/api/documentos/<int:id>/asignar-tarea', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.TAREA_ASIGNADA,
        entidad_tipo='documento'
    )
    def asignar_tarea(id):
        doc = db.session.get(Documento, id); data = request.json
        doc.estado_tarea = data.get('estado_tarea')
        doc.asignado_a_id = int(data.get('asignado_a_id')) if data.get('asignado_a_id') else None
        if data.get('fecha_plazo'): doc.fecha_plazo = datetime.fromisoformat(data['fecha_plazo'].split('.')[0])
        doc.guardado = False; doc.email_enviado = False; db.session.commit()
        if doc.asignado_a_id: notificar("Tarea Personal", f"Asignado: {doc.nombre_archivo}", doc.empresa.gestoria_id, user_id=doc.asignado_a_id, link=f"/empresa/{doc.empresa_id}/Notificaciones", tipo=NotificationTypes.WARNING)
        elif doc.estado_tarea:
            match = re.search(r'\((.*?)\)', doc.estado_tarea)
            if match: notificar("Tarea Depto", f"Para {match.group(1)}: {doc.nombre_archivo}", doc.empresa.gestoria_id, departamento=match.group(1), link=f"/empresa/{doc.empresa_id}/Notificaciones")
        
        # Detalles para auditoría
        request.auditoria_detalles = {
            'documento_id': id,
            'documento_nombre': doc.nombre_archivo,
            'estado_nuevo': doc.estado_tarea,
            'asignado_nuevo': doc.asignado_a_id,
            'empresa_id': doc.empresa_id
        }
        request.auditoria_entidad_id = id
        
        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/documentos/<int:id>/marcar-pendiente', methods=['POST'])
    @login_required
    def mark_pen(id):
        """
        Revierte un documento a Por Procesar.
        NOTA: Solo actualiza BD, NO mueve archivo físico (consistente con Mesa de Trabajo)
        También elimina tareas asociadas del calendario.
        """
        d = db.session.get(Documento, id)
        if not d:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # Solo actualizar campos en BD
        d.categoria = DocumentCategories.POR_PROCESAR
        d.procesado = False
        d.estado_tarea = None
        d.asignado_a_id = None
        d.fecha_plazo = None
        d.guardado = False
        d.email_enviado = False
        
        # ⭐ NUEVO: Eliminar tareas asociadas al documento
        from models import Tarea
        tareas_asociadas = Tarea.query.filter_by(documento_id=id).all()
        tareas_eliminadas = len(tareas_asociadas)
        
        for tarea in tareas_asociadas:
            db.session.delete(tarea)
        
        db.session.commit()
        
        mensaje = 'Documento marcado como pendiente'
        if tareas_eliminadas > 0:
            mensaje += f' y {tareas_eliminadas} tarea(s) eliminada(s) del calendario'
        
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            'message': mensaje,
            'tareas_eliminadas': tareas_eliminadas
        })

    @app.route('/api/documentos/<int:id>/guardar', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_GUARDADO,
        entidad_tipo='documento'
    )
    def save_doc(id):
        d = db.session.get(Documento, id)
        if not d:
            return jsonify({NotificationTypes.ERROR: "No encontrado"}), 404
        
        d.guardado = True
        d.estado_tarea = None
        db.session.commit()
        
        request.auditoria_detalles = {
            'documento_id': id,
            'documento_nombre': d.nombre_archivo,
            'empresa_id': d.empresa_id
        }
        request.auditoria_entidad_id = id
        
        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/documentos/<int:doc_id>/enviar-email', methods=['POST'])
    @login_required
    @auditar(
    accion=AccionesAuditoria.EMAIL_ENVIADO,
    entidad_tipo='documento'
)
    def enviar_email(doc_id):
        try:
            doc = db.session.get(Documento, doc_id); emp = db.session.get(Empresa, doc.empresa_id)
            dests = request.json.get('destinatarios', [])
            if not dests and request.json.get('destinatario'): dests = [request.json.get('destinatario')]
            
            # 🏢 NUEVO: Lógica de Agrupaciones (Email centralizado)
            if not dests:
                from email_sender import obtener_email_notificaciones
                email_final = obtener_email_notificaciones(emp.id)
                if email_final:
                    dests = [email_final]
                elif emp.email:
                    dests = [emp.email]
            
            msg = MIMEMultipart('related'); msg["From"] = f"IAGES <{app.config['SMTP_USER']}>"; msg["To"] = ", ".join(dests); msg["Subject"] = Header(request.json.get('subject'), 'utf-8')
            msg_alt = MIMEMultipart('alternative'); msg.attach(msg_alt)
            msg_alt.attach(MIMEText(request.json.get('body'), "plain", "utf-8"))
            
            # HTML CON LOGO PEQUEÑO Y CENTRADO
            html = f"""<html><head><style>body{{font-family:'Segoe UI',sans-serif;background:#f3f4f6;padding:20px}}.container{{max-width:600px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}.header{{background:linear-gradient(90deg,#f97316 0%,#ef4444 100%);padding:15px;text-align:center}}.content{{padding:30px 25px;color:#374151;font-size:15px;line-height:1.5}}.attachment-box{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:6px;padding:12px;margin-top:20px;display:flex;align-items:center;font-size:13px}}.footer{{background:#f9fafb;padding:15px;text-align:center;font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb}}</style></head><body><div class="container"><div class="header"><img src="cid:logo_iages" style="height:60px;width:auto;display:block;margin:0 auto"></div><div class="content">{request.json.get('body').replace(chr(10),'<br>')}<div class="attachment-box">📄 <strong>Adjunto:</strong> &nbsp; {doc.nombre_archivo}</div></div><div class="footer"><p><strong>Victor Cisneros Müller</strong><br>Tel 932687082</p><p>© 2025 IAGES</p></div></div></body></html>"""
            msg_alt.attach(MIMEText(html, "html", "utf-8"))

            logo = os.path.join(basedir, 'assets', 'logo-iages.png')
            if os.path.exists(logo): 
                with open(logo, 'rb') as f: img = MIMEImage(f.read()); img.add_header('Content-ID', '<logo_iages>'); msg.attach(img)

            with open(doc.ruta_archivo, "rb") as f:
                p = MIMEBase("application", "octet-stream"); p.set_payload(f.read()); encoders.encode_base64(p)
                p.add_header("Content-Disposition", "attachment", filename=Header(doc.nombre_archivo, 'utf-8').encode()); msg.attach(p)
            
            ctx = ssl.create_default_context()
            port = int(app.config['SMTP_PORT'])
            if port == 465:
                with smtplib.SMTP_SSL(app.config['SMTP_SERVER'], port, context=ctx) as s:
                    s.login(app.config['SMTP_USER'], app.config['SMTP_PASS']); s.sendmail(app.config['SMTP_USER'], dests, msg.as_string())
            else:
                with smtplib.SMTP(app.config['SMTP_SERVER'], port) as s:
                    s.starttls(context=ctx)
                    s.login(app.config['SMTP_USER'], app.config['SMTP_PASS']); s.sendmail(app.config['SMTP_USER'], dests, msg.as_string())
            
            doc.email_enviado = True; doc.guardado = False; doc.fecha_envio = datetime.now(timezone.utc); doc.estado_tarea = None
            db.session.commit()
            
            # Detalles para auditoría
            request.auditoria_detalles = {
                'documento_id': doc_id,
                'documento_nombre': doc.nombre_archivo,
                'destinatarios': dests,
                'asunto': request.json.get('subject'),
                'empresa_id': doc.empresa_id,
                'empresa_nombre': emp.nombre if emp else None
            }
            request.auditoria_entidad_id = doc_id
            
            return jsonify({NotificationTypes.SUCCESS: True})
        except Exception as e: return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/documentos/<int:id>/previsualizar-email', methods=['GET'])
    @login_required
    def prev_email(id): d = db.session.get(Documento, id); s, b = generar_texto_email(d); return jsonify({NotificationTypes.SUCCESS:True, "subject":s, "body":b})

    # ==========================================
    # CLASIFICACIÓN (INBOX)
    # ==========================================
    
    @app.route('/api/archivos-no-clasificados', methods=['GET'])
    @login_required
    def get_archivos_no_clasificados():
        """
        Listar archivos de carpetas de no clasificados
        MULTI-TENANT: Filtrar por gestoria_id del usuario actual
        """
        gestoria_id = current_user.gestoria_id
        
        
        # Listar archivos de carpetas de no clasificados
        archivos_dict = {}  # Usar dict para eliminar duplicados por nombre
        
        # MULTI-TENANT: Usar inbox de la gestoría (con slug, no ID numérico)
        from utils.storage_utils import get_gestoria_inbox_path
        ruta_inbox = get_gestoria_inbox_path(gestoria_id)
        
        # Escanear inbox de la gestoría
        for f in os.listdir(ruta_inbox):
            if f.lower().endswith('.pdf'):
                archivos_dict[f] = {"nombre_archivo": f, "origen": "inbox"}
        
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "files": list(archivos_dict.values())
        })

    @app.route('/api/archivos-no-clasificados/<path:filename>', methods=['GET'])
    @login_required
    def get_archivo_no_clasificado(filename):
        """Servir archivo no clasificado - MULTI-TENANT: Usar ruta de gestoría"""
        from utils.storage_utils import get_gestoria_inbox_path
        
        # MULTI-TENANT: Obtener inbox de la gestoría actual
        gestoria_id = get_current_gestoria_id()
        ruta_no_clasificados = get_gestoria_inbox_path(gestoria_id)
        file_path = os.path.join(ruta_no_clasificados, os.path.basename(filename))
        
        logger.info(f"Buscando archivo: {file_path}")
        
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='application/pdf')
        
        logger.error(f"Archivo no encontrado: {file_path}")
        return jsonify({NotificationTypes.ERROR: "Archivo no encontrado"}), 404

    @app.route('/api/clasificar/obtener-nif-inbox/<path:filename>', methods=['GET'])
    @login_required
    def get_nif_inbox(filename):
        """Obtener NIF de archivo - MULTI-TENANT: Usar ruta de gestoría"""
        try:
            from utils.storage_utils import get_gestoria_inbox_path
            
            # MULTI-TENANT: Buscar en inbox de la gestoría actual
            gestoria_id = get_current_gestoria_id()
            ruta_no_clasificados = get_gestoria_inbox_path(gestoria_id)
            ruta_archivo = os.path.join(ruta_no_clasificados, os.path.basename(filename))
            
            if not os.path.exists(ruta_archivo):
                return jsonify({NotificationTypes.ERROR: "Archivo no encontrado"}), 404
            
            # 🆕 OPTIMIZACIÓN: Búsqueda temprana de NIF (Short-circuit)
            from cocoindex.pdf_partitioner import get_pdf_partitioner
            partitioner = get_pdf_partitioner()
            nif_result = partitioner.find_nif_early_exit(ruta_archivo, max_pages=15)
            
            nif_final = "No encontrado"
            if nif_result:
                nif_final = nif_result['nif']
            else:
                # Fallback: Búsqueda tradicional (extracción completa)
                from services.notificacion_extractor import NotificacionExtractor
                extractor = NotificacionExtractor()
                texto = extractor.extract_text_from_pdf(ruta_archivo)
                nif_final = _find_nif_with_regex(texto) or "No encontrado"
                
            return jsonify({NotificationTypes.SUCCESS: True, "nif_encontrado": nif_final})
        except Exception as e: 
            logger.error(f"Error en get_nif_inbox: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/documentos/<int:documento_id>', methods=['DELETE'])
    @login_required
    def eliminar_documento(documento_id):
        """
        Elimina un documento físicamente y de la base de datos.
        MULTI-TENANT: Solo permite borrar si pertenece a la gestoría del usuario.
        """
        try:
            from models import Documento
            from tenant_utils import get_current_gestoria_id
            import os
            
            gestoria_id = get_current_gestoria_id()
            doc = db.session.get(Documento, documento_id)
            
            if not doc:
                return jsonify({NotificationTypes.ERROR: "Documento no encontrado"}), 404
            
            # Seguridad: Verificar gestoría
            if doc.gestoria_id != gestoria_id:
                return jsonify({NotificationTypes.ERROR: "No tienes permiso para eliminar este documento"}), 403
            
            # 1. Intentar eliminar archivo físico
            if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                try:
                    os.remove(doc.ruta_archivo)
                    logger.info(f"🗑️ Archivo eliminado físicamente: {doc.ruta_archivo}")
                    
                    # ✅ También eliminar copia en Aplazamientos si existe
                    # Verificar si es un aplazamiento o si existe la carpeta Aplazamientos
                    directorio_base = os.path.dirname(doc.ruta_archivo)
                    nombre_archivo = os.path.basename(doc.ruta_archivo)
                    
                    # Si estaba en la raíz de la empresa, buscar en subcarpeta Aplazamientos
                    ruta_posible_aplazamiento = os.path.join(directorio_base, 'Aplazamientos', nombre_archivo)
                    if os.path.exists(ruta_posible_aplazamiento):
                        os.remove(ruta_posible_aplazamiento)
                        logger.info(f"🗑️ Copia de aplazamiento eliminada: {ruta_posible_aplazamiento}")
                        
                    # Si estaba en Impuestos y se copió a Aplazamientos (estructura antigua)
                    # Subir un nivel y buscar en Aplazamientos
                    if os.path.basename(directorio_base) == 'Impuestos':
                        ruta_raiz_empresa = os.path.dirname(directorio_base)
                        ruta_posible_aplazamiento = os.path.join(ruta_raiz_empresa, 'Aplazamientos', nombre_archivo)
                        if os.path.exists(ruta_posible_aplazamiento):
                            os.remove(ruta_posible_aplazamiento)
                            logger.info(f"🗑️ Copia de aplazamiento eliminada (layout antiguo): {ruta_posible_aplazamiento}")

                except Exception as fe:
                    logger.error(f"⚠️ Error eliminando archivo físico {doc.ruta_archivo}: {fe}")
                    # Continuamos con el borrado en BD aunque falle el físico para evitar huérfanos
            
            # 2. Eliminar relaciones con grupos (GrupoDocumentosItem) para evitar FK violation
            from models import GrupoDocumentosItem
            GrupoDocumentosItem.query.filter_by(documento_id=documento_id).delete()

            # 3. Eliminar de la base de datos
            db.session.delete(doc)
            db.session.commit()
            
            # Auditoría
            from auditoria import registrar_auditoria, AccionesAuditoria
            registrar_auditoria(
                accion=AccionesAuditoria.DOCUMENTO_ELIMINADO,
                entidad_id=documento_id,
                entidad_tipo='documento',
                descripcion=f"Documento eliminado: {doc.nombre_archivo}",
                detalles={'nombre': doc.nombre_archivo, 'ruta': doc.ruta_archivo}
            )
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "message": "Documento eliminado correctamente"
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error en eliminar_documento: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/clasificar/eliminar-inbox/<path:filename>', methods=['DELETE'])
    @login_required
    def eliminar_archivo_inbox(filename):
        """Elimina un archivo del inbox - MULTI-TENANT: Usar ruta de gestoría"""
        try:
            from utils.storage_utils import get_gestoria_inbox_path
            
            # MULTI-TENANT: Buscar en inbox de la gestoría actual
            gestoria_id = get_current_gestoria_id()
            ruta_no_clasificados = get_gestoria_inbox_path(gestoria_id)
            ruta_archivo = os.path.join(ruta_no_clasificados, os.path.basename(filename))
            
            if not os.path.exists(ruta_archivo):
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Archivo no encontrado"}), 404
            
            # Eliminar archivo
            os.remove(ruta_archivo)
            print(f"🗑️ Archivo eliminado: {filename}")
            
            return jsonify({NotificationTypes.SUCCESS: True, "message": f"Archivo {filename} eliminado correctamente"})
        except Exception as e:
            logger.error(f"Error eliminando archivo: {str(e)}")
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/clasificar/batch-delete', methods=['POST'])
    @login_required
    def batch_eliminar_inbox():
        """Elimina varios archivos del inbox por lote - MULTI-TENANT"""
        try:
            from utils.storage_utils import get_gestoria_inbox_path
            data = request.get_json()
            filenames = data.get('filenames', [])
            
            if not filenames:
                return jsonify({NotificationTypes.ERROR: "No se proporcionaron nombres de archivo"}), 400
            
            gestoria_id = get_current_gestoria_id()
            ruta_no_clasificados = get_gestoria_inbox_path(gestoria_id)
            
            resultados = []
            for filename in filenames:
                ruta_archivo = os.path.join(ruta_no_clasificados, os.path.basename(filename))
                if os.path.exists(ruta_archivo):
                    os.remove(ruta_archivo)
                    resultados.append({'filename': filename, 'status': 'deleted'})
                else:
                    resultados.append({'filename': filename, 'status': 'not_found'})
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "message": f"Procesados {len(resultados)} archivos",
                "resultados": resultados
            })
        except Exception as e:
            logger.error(f"Error en batch_eliminar_inbox: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/clasificar-y-subir', methods=['POST'])
    @login_required
    @limiter.limit("20 per minute")  # ⚠️ SEGURIDAD: Rate limiting en uploads
    def clasificar_y_subir():
        """
        Clasifica y sube un archivo PDF con validación MIME
        """
        logger.error("📥 INICIO: Petición a clasificar_y_subir recibida")
        from utils.file_validation import validate_pdf_mime, allowed_file
        
        if 'file' not in request.files:
            return jsonify({NotificationTypes.ERROR: 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        force_empresa_id = request.form.get('empresa_id')
        force_categoria = request.form.get('categoria')
        return _procesar_un_archivo_individual(file, force_empresa_id, force_categoria)

    @app.route('/api/clasificar-y-subir-multiple', methods=['POST'])
    @login_required
    @limiter.limit("10 per minute") # Lotes de hasta 100 archivos
    def clasificar_y_subir_multiple():
        """
        Procesa múltiples archivos en una sola transacción (máx 100)
        """
        files = request.files.getlist('files[]')
        if not files:
            return jsonify({NotificationTypes.ERROR: 'No se enviaron archivos'}), 400
        
        if len(files) > 100:
            return jsonify({NotificationTypes.ERROR: 'Límite máximo de 100 archivos por subida excedido'}), 400

        force_empresa_id = request.form.get('empresa_id')
        force_categoria = request.form.get('categoria')

        resultados = []
        exitosos = 0
        errores = 0

        for file in files:
            try:
                res = _procesar_un_archivo_individual(file, force_empresa_id, force_categoria)
                # Extraer body si es una Response de Flask
                if hasattr(res, 'get_json'):
                    data = res.get_json()
                    status_code = res.status_code
                else:
                    data = res[0].get_json()
                    status_code = res[1]

                resultados.append({
                    'filename': file.filename,
                    'success': status_code < 400,
                    'message': data.get('message') or data.get('error')
                })
                
                # Manejo de warnings (duplicados, etc)
                if data.get('warning'):
                    logger.warning(f"⚠️ Warning en lote para {file.filename}: {data.get('message')}")
                    # No incrementamos error, pero podriamos marcarlo diferente en resultados
                    resultados[-1]['success'] = True
                    resultados[-1]['warning'] = True
                
                if status_code < 400:
                    exitosos += 1
                else:
                    logger.error(f"❌ Error en lote para {file.filename}: {data.get('message') or data.get('error')}")
                    errores += 1
            except Exception as e:
                logger.error(f"Error procesando {file.filename} en lote: {e}")
                resultados.append({
                    'filename': file.filename,
                    'success': False,
                    'message': str(e)
                })
                errores += 1

        return jsonify({
            'success': exitosos > 0,
            'total': len(files),
            'exitosos': exitosos,
            'errores': errores,
            'detalles': resultados
        })

    @app.route('/api/subir-directo-multiple', methods=['POST'])
    @login_required
    @limiter.limit("20 per minute")
    def subir_directo_multiple():
        """
        Sube archivos directamente a una empresa y categoría sin procesamiento inteligente.
        Ideal para archivos ya clasificados o subidas manuales directas.
        """
        from utils.file_validation import validate_pdf_mime, allowed_file
        from utils.storage_utils import get_empresa_storage_path
        from utils import limpiar_nombre_carpeta
        import hashlib

        files = request.files.getlist('files[]')
        empresa_id = request.form.get('empresa_id')
        categoria = request.form.get('categoria', DocumentCategories.NOTIFICACIONES)

        if not files:
            return jsonify({NotificationTypes.ERROR: 'No se enviaron archivos'}), 400
        
        if not empresa_id:
            return jsonify({NotificationTypes.ERROR: 'Empresa ID es requerido'}), 400

        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            return jsonify({NotificationTypes.ERROR: 'Empresa no encontrada'}), 404

        # Seguridad multi-tenant
        gestoria_id = get_current_gestoria_id()
        if empresa.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado a esta empresa'}), 403

        # Determinar carpeta de destino según categoría
        dest_folder = "Fiscal" # Default
        if categoria in [DocumentCategories.ALTAS_TRABAJADORES, DocumentCategories.BAJAS_TRABAJADORES, 
                         DocumentCategories.NOMINAS, DocumentCategories.SEGUROS_SOCIALES, 
                         DocumentCategories.FINIQUITOS, DocumentCategories.CONTRATOS]:
            dest_folder = "Laboral"
        elif categoria in [DocumentCategories.NOTIFICACIONES, DocumentCategories.DEHU]:
            dest_folder = "Notificaciones"
        elif categoria == DocumentCategories.FISCAL:
            dest_folder = "Fiscal"

        base_storage = current_app.config.get('RUTA_RAIZ_NOTIFICACIONES', 'storage')
        nombre_f_emp = limpiar_nombre_carpeta(empresa.nombre)
        final_dest_dir = os.path.join(base_storage, get_gestoria_folder_name(gestoria_id), nombre_f_emp, dest_folder)
        os.makedirs(final_dest_dir, exist_ok=True)

        resultados = []
        docs_creados = []
        exitosos = 0
        errores = 0

        for file in files:
            try:
                if file.filename == '' or not allowed_file(file.filename):
                    errores += 1
                    resultados.append({'filename': file.filename, 'success': False, 'error': 'Archivo no permitido'})
                    continue

                # Validar MIME
                is_valid, error_msg = validate_pdf_mime(file)
                if not is_valid:
                    errores += 1
                    resultados.append({'filename': file.filename, 'success': False, 'error': error_msg})
                    continue

                filename = secure_filename(file.filename)
                
                # Check storage limit
                from utils.quota_utils import validate_gestoria_limit
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                puede_subir, error_cuota = validate_gestoria_limit(gestoria_id, 'storage', file_size)
                if not puede_subir:
                    errores += 1
                    resultados.append({'filename': file.filename, 'success': False, 'error': error_cuota})
                    continue

                # Hash check for duplicates
                file_content = file.read()
                file_hash = hashlib.sha256(file_content).hexdigest()
                file.seek(0)

                doc_duplicado = Documento.query.filter_by(file_hash=file_hash, empresa_id=empresa_id).first()
                if doc_duplicado:
                    resultados.append({
                        'filename': filename, 
                        'success': True, 
                        'warning': True, 
                        'message': 'Ya existe un archivo idéntico para esta empresa'
                    })
                    exitosos += 1
                    continue

                # Save file
                final_path = os.path.join(final_dest_dir, filename)
                # handle filename collisions
                if os.path.exists(final_path):
                    name, ext = os.path.splitext(filename)
                    final_path = os.path.join(final_dest_dir, f"{name}_{int(datetime.now().timestamp())}{ext}")

                file.save(final_path)

                # Create Documento
                nuevo_doc = Documento(
                    empresa_id=empresa_id,
                    gestoria_id=gestoria_id,
                    categoria=categoria,
                    nombre_archivo=os.path.basename(final_path),
                    ruta_archivo=final_path,
                    procesado=True, # Lo marcamos como procesado para que no aparezca en "Por Procesar"
                    fecha_procesado=datetime.utcnow(),
                    file_hash=file_hash,
                    datos_extraidos={}, # Sin lectura inteligente
                    leido=False
                )
                db.session.add(nuevo_doc)
                docs_creados.append(nuevo_doc)
                exitosos += 1
                resultados.append({'filename': filename, 'success': True})

            except Exception as e:
                logger.error(f"Error en subida directa de {file.filename}: {str(e)}")
                errores += 1
                resultados.append({'filename': file.filename, 'success': False, 'error': str(e)})

        db.session.commit()
        return jsonify({
            'success': exitosos > 0,
            'total': len(files),
            'exitosos': exitosos,
            'errores': errores,
            'detalles': resultados,
            'documento_ids': [doc.id for doc in docs_creados]
        })

    @app.route('/api/subir-a-categoria', methods=['POST'])
    @login_required
    @limiter.limit("20 per minute")
    def subir_a_categoria():
        """
        Sube archivos a una empresa y categoría específica ejecutando el extractor OCR correspondiente.
        A diferencia de la subida normal, aquí ya conocemos la empresa (empresa_id enviada).
        """
        from utils.file_validation import validate_pdf_mime, allowed_file
        from utils.storage_utils import get_empresa_storage_path
        from utils import limpiar_nombre_carpeta
        import hashlib
        from datetime import datetime

        files = request.files.getlist('files[]')
        empresa_id = request.form.get('empresa_id')
        categoria = request.form.get('categoria')

        if not files or not empresa_id or not categoria:
            return jsonify({NotificationTypes.ERROR: 'Faltan datos requeridos (archivos, empresa o categoría)'}), 400

        empresa = db.session.get(Empresa, empresa_id)
        if not empresa:
            return jsonify({NotificationTypes.ERROR: 'Empresa no encontrada'}), 404

        gestoria_id = get_current_gestoria_id()
        if empresa.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403

        # Directorio temporal para procesamiento
        temp_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'temp'), 'categorized_upload', str(datetime.now().timestamp()))
        os.makedirs(temp_dir, exist_ok=True)

        resultados = []
        exitosos = 0
        errores = 0

        for file in files:
            try:
                if not allowed_file(file.filename):
                    resultados.append({'filename': file.filename, 'success': False, 'error': 'Archivo no permitido'})
                    errores += 1
                    continue

                filename = secure_filename(file.filename)
                temp_path = os.path.join(temp_dir, filename)
                file.save(temp_path)

                # Calcular hash para evitar duplicados
                file_hash = get_file_hash(temp_path)
                doc_duplicado = Documento.query.filter_by(file_hash=file_hash, empresa_id=empresa_id).first()
                if doc_duplicado:
                    resultados.append({'filename': filename, 'success': True, 'warning': True, 'message': 'Ya existe este archivo'})
                    exitosos += 1
                    continue

                # --- LLAMAR AL SERVICIO CORRESPONDIENTE SEGÚN CATEGORÍA ---
                # Importar servicios on-demand
                from services.procesar_altas import procesar_altas
                from services.procesar_finiquitos import procesar_finiquitos
                from services.procesar_contratos import procesar_contratos
                from services.procesar_modelo_190 import procesar_certificados_190
                from services.procesar_modelo_180 import procesar_certificados_180
                from procesar_documentos_fiscales import procesar_documento_fiscal
                import asyncio
                
                output_sub_dir = os.path.join(temp_dir, 'output')
                os.makedirs(output_sub_dir, exist_ok=True)

                res_ocr = []
                if categoria == DocumentCategories.IMPUESTOS:
                    from services.procesar_impuestos import procesar_impuestos
                    res_ocr = procesar_impuestos(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())

                elif categoria in [DocumentCategories.ALTAS_TRABAJADORES, DocumentCategories.BAJAS_TRABAJADORES]:
                    res_ocr = procesar_altas(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == DocumentCategories.FINIQUITOS:
                    res_ocr = procesar_finiquitos(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == DocumentCategories.CONTRATOS:
                    res_ocr = procesar_contratos(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == DocumentCategories.CERTIFICADOS_190:
                    res_ocr = procesar_certificados_190(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == DocumentCategories.CERTIFICADOS_180:
                    res_ocr = procesar_certificados_180(temp_path, output_sub_dir, gestoria_id=gestoria_id, app_context=current_app.app_context())
                else:
                    # Fallback para categorías sin OCR específico todavía (Nóminas, etc.)
                    # Guardamos el archivo directamente en la categoría elegida
                    res_ocr = [{'empresa_id': empresa_id, 'pdf_path': temp_path, 'nombre_archivo': filename}]

                # --- GUARDADO FINAL Y PERSISTENCIA (Para el resto de categorías) ---
                for item in res_ocr:
                    # FORZAR empresa_id si el OCR no la encontró o encontró otra (aquí manda la vista)
                    final_empresa_id = empresa_id
                    final_pdf_path = item.get('pdf_path') or temp_path
                    
                    # Mover a la carpeta final de la empresa
                    base_storage = current_app.config.get('RUTA_RAIZ_NOTIFICACIONES', 'storage')
                    dest_folder = categoria  # Por defecto usar el nombre de la categoría como carpeta
                    if categoria in [DocumentCategories.ALTAS_TRABAJADORES, DocumentCategories.BAJAS_TRABAJADORES, 
                                     DocumentCategories.NOMINAS, DocumentCategories.SEGUROS_SOCIALES, 
                                     DocumentCategories.FINIQUITOS, DocumentCategories.CONTRATOS]:
                        dest_folder = "Laboral"
                    elif categoria in [DocumentCategories.NOTIFICACIONES, DocumentCategories.DEHU]:
                        dest_folder = "Notificaciones"
                    elif categoria in [DocumentCategories.IMPUESTOS, DocumentCategories.CERTIFICADOS_190, DocumentCategories.CERTIFICADOS_180]:
                        dest_folder = "Fiscal"

                    
                    logger.info(f"[DEBUG IMPUESTOS] empresa_id={empresa_id}, empresa.nombre={empresa.nombre}, final_empresa_id={final_empresa_id}, pdf={final_pdf_path}")
                    nombre_f_emp = limpiar_nombre_carpeta(empresa.nombre)
                    final_dest_dir = os.path.join(base_storage, get_gestoria_folder_name(gestoria_id), nombre_f_emp, dest_folder)
                    os.makedirs(final_dest_dir, exist_ok=True)
                    
                    final_filename = os.path.basename(final_pdf_path)
                    final_full_path = os.path.join(final_dest_dir, final_filename)
                    if os.path.exists(final_full_path):
                        name, ext = os.path.splitext(final_filename)
                        final_filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
                        final_full_path = os.path.join(final_dest_dir, final_filename)
                    
                    shutil.move(final_pdf_path, final_full_path)
                    
                    # Registrar en BD
                    nuevo_doc = Documento(
                        empresa_id=final_empresa_id,
                        gestoria_id=gestoria_id,
                        categoria=categoria,
                        nombre_archivo=final_filename,
                        ruta_archivo=final_full_path,
                        procesado=True,
                        fecha_procesado=datetime.utcnow(),
                        file_hash=file_hash,
                        leido=False,
                        datos_extraidos=item,
                        periodo=item.get('ejercicio') or item.get('periodo') # Capturamos el año si el OCR lo sacó
                    )
                    db.session.add(nuevo_doc)
                    exitosos += 1
                
                resultados.append({'filename': filename, 'success': True})

            except Exception as e:
                logger.error(f"Error procesando {file.filename} en categorized upload: {str(e)}")
                errores += 1
                resultados.append({'filename': file.filename, 'success': False, 'error': str(e)})

        db.session.commit()
        # Limpieza temp
        try: shutil.rmtree(temp_dir)
        except: pass

        return jsonify({
            'success': exitosos > 0,
            'total': len(files),
            'exitosos': exitosos,
            'errores': errores,
            'detalles': resultados
        })


    def get_gestoria_folder_name(gestoria_id):
        """Helper para obtener el nombre de la carpeta de gestoría (slug o gestoria_id)"""
        from models import Gestoria
        g = db.session.get(Gestoria, gestoria_id)
        if g and g.slug:
            return g.slug
        return f"gestoria_{gestoria_id}"


    def _procesar_un_archivo_individual(file, force_empresa_id=None, force_categoria=None):
        """Helper para procesar un solo archivo (lógica original extraída)"""
        from utils.file_validation import validate_pdf_mime, allowed_file
        from models import Empresa
        from services.notificacion_extractor import NotificacionExtractor
        
        extractor = NotificacionExtractor()
        
        if file.filename == '':
            return jsonify({NotificationTypes.ERROR: 'Nombre de archivo vacío'}), 400
        
        # Validar extensión
        if not allowed_file(file.filename):
            return jsonify({NotificationTypes.ERROR: 'Solo se permiten archivos PDF'}), 400
        
        # Guardar filename
        filename = secure_filename(file.filename)
        
        # ⚠️ SEGURIDAD: Validar MIME type (magic bytes)
        is_valid, error_msg = validate_pdf_mime(file)
        if not is_valid:
            return jsonify({NotificationTypes.ERROR: error_msg}), 400
        
        # Validar límite de storage
        from utils.quota_utils import validate_gestoria_limit
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        
        gestoria_id = get_current_gestoria_id()
        puede_subir, mensaje_error = validate_gestoria_limit(gestoria_id, 'storage', file_size)
        if not puede_subir:
            return jsonify({NotificationTypes.ERROR: mensaje_error}), 403
        
        # Usar inbox por gestoría
        from utils.storage_utils import get_gestoria_inbox_path
        ruta_inbox = get_gestoria_inbox_path(get_current_gestoria_id())
        temp_path = os.path.join(ruta_inbox, f"temp_{filename}")
        file.save(temp_path)
        file_hash = get_file_hash(temp_path)

        doc_duplicado = None
        if file_hash:
            doc_duplicado = Documento.query.filter_by(file_hash=file_hash).first()
        
        if doc_duplicado:
            # Es un duplicado REAL (mismo contenido)
            os.remove(temp_path)  # Eliminar archivo temporal
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "duplicado_real",
                "message": f"⚠️ Archivo idéntico ya existe: {doc_duplicado.nombre_archivo}",
                "documento_existente": {
                    "id": doc_duplicado.id,
                    "nombre": doc_duplicado.nombre_archivo,
                    "fecha": doc_duplicado.fecha_creacion.strftime('%d/%m/%Y')
                }
            }), 400
        
        # 🔍 INTERCEPCIÓN PARA CERTIFICADOS 180/190 / ALTAS
        # Si se fuerza una de estas categorías, usamos su procesador especializado 
        # que sabe dividir páginas y extraer datos técnicos.
        if force_categoria in ['Certificados de Retenciones 190', 'Certificados de Retenciones 180', 'Altas']:
            logger.info(f"🚀 Usando procesador especializado para {force_categoria}")
            
            # Guardar archivo temporal para procesar
            temp_proc_dir = tempfile.mkdtemp()
            temp_proc_path = os.path.join(temp_proc_dir, secure_filename(file.filename))
            file.save(temp_proc_path)
            
            from services.procesar_modelo_190 import procesar_certificados_190
            from services.procesar_modelo_180 import procesar_certificados_180
            from services.procesar_altas import procesar_altas
            
            try:
                if force_categoria == 'Certificados de Retenciones 190':
                    output_dir = os.path.join(temp_proc_dir, "fragments")
                    res_certs = procesar_certificados_190(temp_proc_path, output_dir, gestoria_id=gestoria_id)
                elif force_categoria == 'Certificados de Retenciones 180':
                    output_dir = os.path.join(temp_proc_dir, "fragments")
                    res_certs = procesar_certificados_180(temp_proc_path, output_dir, gestoria_id=gestoria_id)
                else: # Altas
                    output_dir = os.path.join(temp_proc_dir, "fragments")
                    res_certs = procesar_altas(temp_proc_path, output_dir, gestoria_id=gestoria_id)
                
                # La lógica de guardado final y movimiento a carpetas de empresa ya está 
                # integrada en los servicios o en sus rutas. 
                # Para evitar duplicar lógica, vamos a "simular" una respuesta exitosa
                # ya que el procesador especializado ya hizo el trabajo sucio.
                
                if res_certs:
                    # OJO: Los procesadores 180/190 actuales SOLO devuelven los metadatos.
                    # Necesitamos mover los fragmentos a sus carpetas finales aquí o dentro del servicio.
                    # Analizando routes_modelo_180.py, vemos que la lógica de movimiento está en la RUTA.
                    # Vamos a REUTILIZAR esa lógica de movimiento aquí para no romper nada.
                    
                    from utils import limpiar_nombre_carpeta
                    from utils.storage_utils import get_empresa_storage_path
                    from models import Empresa

                    storage_root = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
                    documentos_creados = []
                    count = 0
                    for cert in res_certs:
                        # FORZAR la empresa destino si el usuario la seleccionó explícitamente, ignorando el OCR
                        cert_emp_id = force_empresa_id if force_empresa_id else cert.get('empresa_id')
                        cert_nom_emp = cert.get('nombre_empresa', 'Empresa_Desconocida')
                        pdf_frag = cert.get('pdf_path')
                        
                        if cert_emp_id:
                            emp_obj = db.session.get(Empresa, cert_emp_id)
                            nombre_f_emp = limpiar_nombre_carpeta(emp_obj.nombre) if emp_obj else limpiar_nombre_carpeta(cert_nom_emp)
                        else:
                            nombre_f_emp = limpiar_nombre_carpeta(cert_nom_emp)

                        
                        if force_categoria == 'Altas':
                            dest_folder = "Laboral"
                            cat_final = DocumentCategories.ALTAS_TRABAJADORES
                        else:
                            dest_folder = "Fiscal"
                            cat_final = force_categoria

                        final_dest_dir = os.path.join(storage_root, nombre_f_emp, dest_folder)
                        os.makedirs(final_dest_dir, exist_ok=True)
                        
                        final_f_path = os.path.join(final_dest_dir, os.path.basename(pdf_frag))
                        shutil.copy2(pdf_frag, final_f_path)
                        
                        h = get_file_hash(final_f_path)
                        ejercicio = str(cert.get('ejercicio')) if cert.get('ejercicio') else str(datetime.now().year)
                        
                        exist = Documento.query.filter_by(file_hash=h, empresa_id=cert_emp_id).first() if cert_emp_id else None
                        if not exist:
                            if force_categoria == 'Altas':
                                d_extra = {
                                    'nif_empleado': cert.get('nif_trabajador'),
                                    'nombre_empleado': cert.get('nombre_trabajador'),
                                    'ejercicio': ejercicio,
                                    'tipo_especifico': cert.get('tipo_documento'),
                                    'fecha_alta': cert.get('fecha_alta')
                                }
                            else:
                                d_extra = {
                                    'nif_empleado': cert.get('nif_perceptor') or cert.get('nif_arrendatario'),
                                    'nombre_empleado': cert.get('nombre_perceptor') or cert.get('nombre_arrendatario'),
                                    'ejercicio': ejercicio
                                }
                            
                            new_d = Documento(
                                empresa_id=cert_emp_id,
                                gestoria_id=gestoria_id,
                                nombre_archivo=os.path.basename(final_f_path),
                                ruta_archivo=final_f_path,
                                categoria=cat_final,
                                procesado=True,
                                periodo=ejercicio,
                                file_hash=h,
                                datos_extraidos=d_extra
                            )
                            db.session.add(new_d)
                            documentos_creados.append(new_d)
                            count += 1
                
                    db.session.commit()

                    # ✅ AGRUPACIÓN AUTOMÁTICA
                    if force_categoria == 'Altas':
                        try:
                            from utils.document_utils import auto_group_altas
                            for d in documentos_creados:
                                auto_group_altas(d.id, gestoria_id, current_user.id)
                        except Exception as e:
                            current_app.logger.error(f"[APP UPLOAD] Error en agrupación automática: {str(e)}")

                    return jsonify({
                        NotificationTypes.SUCCESS: True,
                        "message": f"Dividido y procesado: {count} certificados generados."
                    }), 200
                else:
                    return jsonify({NotificationTypes.ERROR: "No se pudieron extraer certificados del PDF"}), 400
            
            finally:
                if os.path.exists(temp_proc_dir):
                    shutil.rmtree(temp_proc_dir, ignore_errors=True)

        logger.info(f"📄 Procesando archivo temporal: {temp_path}")
        try:
            # Si se fuerza empresa y categoría, saltar detección
            nif = None
            emp = None
            categoria_final = force_categoria or DocumentCategories.POR_PROCESAR
            esta_procesado = False
            dept_notif = "Administrativo"
            datos_auto = {}

            if force_empresa_id:
                emp = db.session.get(Empresa, force_empresa_id)
                if emp and emp.gestoria_id != gestoria_id:
                    emp = None # Seguridad
            
            if not emp:
                # 🆕 OPTIMIZACIÓN: Detección temprana de NIF (Short-circuit)
                from cocoindex.pdf_partitioner import get_pdf_partitioner
                partitioner = get_pdf_partitioner()
            
            nif = None
            extraction_method = None
            extraction_confidence = 0
            texto = ""
            
            # Intentar búsqueda ultra-rápida (páginas 1-15)
            nif_result = partitioner.find_nif_early_exit(temp_path, max_pages=15)
            
            if nif_result:
                nif = nif_result['nif']
                extraction_method = nif_result['method']
                extraction_confidence = int(nif_result['confidence'] * 100)
                texto = nif_result.get('context', "")
                logger.info(f"⚡ EARLY EXIT: NIF {nif} encontrado en página {nif_result.get('page_found')}")
            else:
                # 🐢 FALLBACK: Proceso original (extracción completa de texto)
                logger.info("🐢 NIF no encontrado temprano, iniciando extracción completa...")
                texto = extractor.extract_text_from_pdf(temp_path)

                # Intentar particionado completo sobre el texto extraído
                try:
                    elements = partitioner.partition_pdf(temp_path)
                    nif_result = partitioner.find_nif_in_elements(elements)
                    
                    if nif_result:
                        nif = nif_result['nif']
                        extraction_method = nif_result['method']
                        extraction_confidence = int(nif_result['confidence'] * 100)
                        logger.info(f"NIF encontrado tras particionado completo: {nif}")
                except Exception as part_err:
                    logger.warning(f"Error en particionado completo: {part_err}")

            # 🆕 PASO 2: COCOINDEX Template Matching (solo si NIF aún no se conoce)
            template_detected = False
            if not nif:
                logger.info("🔍 Intentando Template Matching...")
                try:
                    from cocoindex.template_matcher import get_template_matcher
                    matcher = get_template_matcher()
                    template_match = matcher.find_best_template(texto, min_confidence=0.75)
                    
                    if template_match['template'] and template_match['confidence'] > 0.75:
                        template_detected = True
                        logger.info(f"TEMPLATE DETECTADO: {template_match['template']['nombre']} (confianza: {template_match['confidence']:.2%})")
                        
                        # Extraer datos con la plantilla
                        datos_extraidos = extractor.extract_with_template(temp_path, template_match['template'])
                        
                        # Intentar obtener NIF de los datos extraídos
                        nif = (datos_extraidos.get('nif_destinatario') or 
                               datos_extraidos.get('nif_deudor') or 
                               datos_extraidos.get('nif'))
                        
                        if nif:
                            extraction_method = 'template'
                            extraction_confidence = int(template_match['confidence'] * 100)
                            logger.info(f"NIF extraído de plantilla: {nif}")
                        
                        # Registrar estadística de extracción
                        try:
                            from sqlalchemy import text
                            
                            query = text("""
                            INSERT INTO document_extractions_stats 
                            (template_id, extraction_method, success, confidence_score, cost)
                            VALUES (:template_id, 'template', true, :confidence, 0.00001)
                            """)
                            
                            db.session.execute(query, {
                                'template_id': template_match['template']['id'],
                                'confidence': int(template_match['confidence'] * 100)
                            })
                            db.session.commit()
                        except Exception as stats_err:
                            logger.warning(f"Error registrando estadística: {stats_err}")
                            
                except Exception as template_err:
                    logger.warning(f"Template matching falló, usando fallback: {template_err}")



            # Fallback intermedio: Usar IA para extraer NIF si template falló
            ai_extraction_used = False
            if not nif:
                try:
                    print("🤖 Usando IA para extraer NIF (template no detectado o confianza baja)...")
                    
                    # Usar Gemini para extraer solo el NIF
                    import google.generativeai as genai
                    
                    # Configurar con la key de documentos
                    gemini_key_docs = os.getenv('GEMINI_API_KEY_DOCUMENTS') or os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY_1')
                    genai.configure(api_key=gemini_key_docs)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""Extrae ÚNICAMENTE el NIF/CIF del destinatario de este documento.

Texto del documento:
{texto[:1000]}

Responde SOLO con el NIF/CIF en formato JSON:
{{"nif": "B12345678"}}

Si no encuentras el NIF, responde: {{"nif": null}}"""
                    
                    response = model.generate_content(prompt)
                    
                    # Parsear respuesta JSON
                    import json
                    import re as regex_module  # Evitar conflicto con 're' usado más adelante
                    
                    # Limpiar respuesta (quitar markdown)
                    response_text = response.text.strip()
                    response_text = regex_module.sub(r'```json\s*|\s*```', '', response_text)
                    
                    try:
                        data = json.loads(response_text)
                        if data.get('nif'):
                            nif = data['nif']
                            ai_extraction_used = True
                            extraction_method = 'ai_fallback'
                            extraction_confidence = 95
                            logger.info(f"NIF extraído con IA: {nif}")
                            
                            # Registrar estadística
                            try:
                                from sqlalchemy import text
                                
                                query = text("""
                                INSERT INTO document_extractions_stats 
                                (template_id, extraction_method, success, confidence_score, cost)
                                VALUES (NULL, 'ai_nif_only', true, 95, 0.0001)
                                """)
                                
                                db.session.execute(query)
                                db.session.commit()
                            except Exception as e:
                                logger.warning(f"Error registrando estadística IA: {e}")
                    except json.JSONDecodeError:
                        logger.warning(f"No se pudo parsear respuesta de IA: {response_text}")
                        
                except Exception as e:
                    logger.warning(f"Extracción con IA falló: {e}")
            else:
                logger.info("✅ NIF ya obtenido, saltando extracción con IA.")


            # 🔍 DEBUG: Ver qué NIF detectó y con qué método
            if not extraction_method:
                extraction_method = 'none'
            # 🔍 BUSCAR AUTOMATIZACIÓN (PATRONES)
            automation_match = None
            try:
                # Usar la primera página para rapidez
                automation_match = extractor.detectar_plantilla(temp_path)
            except Exception as auto_err:
                logger.warning(f"Error en detección de automatización: {auto_err}")

            # --- BÚSQUEDA DE EMPRESA ---
            # Orden: NIF → alias NIF → fallback CCC/nombre → inbox
            nif_clean = None
            
            if not emp:
                if nif:
                    nif_clean = re.sub(r'[\s\.-]', '', nif.strip().upper()).lstrip("ES").lstrip("0")[:9]
                    alias = AliasNIF.query.filter_by(nif=nif_clean).first()
                    # Multi-tenant: filtrar por gestoria_id
                    emp = alias.empresa if alias else Empresa.query.filter_by(nif=nif_clean, gestoria_id=get_current_gestoria_id()).first()

                # Fallback: si no hay empresa todavía, intentar por CCC o razón social
                if not emp and texto:
                    emp = _buscar_empresa_fallback(texto, get_current_gestoria_id())
                    if emp:
                        logger.info(f"🔄 Empresa clasificada por fallback CCC/nombre: {emp.nombre}")

            if emp:
                # ✅ VERIFICAR SI EL ARCHIVO YA EXISTE
                doc_existente = Documento.query.filter_by(
                    empresa_id=emp.id,
                    nombre_archivo=filename
                ).first()
                
                if doc_existente:
                    os.remove(temp_path)
                    return jsonify({
                        NotificationTypes.SUCCESS: True, 
                        "warning": True,
                        "message": f"Duplicado: ya existe en carpeta '{doc_existente.categoria}'",
                        "categoria_existente": doc_existente.categoria
                    })
                
                # Clasificación por defecto (si no se forzó)
                if not force_categoria:
                    categoria_final = DocumentCategories.POR_PROCESAR
                    esta_procesado = False
                    dept_notif = "Administrativo"
                    datos_auto = {}

                    if automation_match:
                        if automation_match.categoria_default:
                            categoria_final = automation_match.categoria_default
                            esta_procesado = True
                            datos_auto['plantilla_auto'] = automation_match.codigo
                            logger.info(f"✨ Aplicando automatización: {automation_match.nombre} -> {categoria_final}")
                        
                        if automation_match.departamento_default:
                            dept_notif = automation_match.departamento_default
                            datos_auto['departamento_auto'] = automation_match.departamento_default
                else:
                    # Si se forzó categoría, podemos intentar ver si hay automatización para el departamento
                    if automation_match and automation_match.departamento_default:
                        dept_notif = automation_match.departamento_default
                    # Caso especial: Altas y Bajas de Trabajadores (Procesamiento con IA/OCR)
                    if force_categoria in ['Altas', 'Bajas', DocumentCategories.ALTAS_TRABAJADORES, DocumentCategories.BAJAS_TRABAJADORES]:
                        try:
                            from services.procesar_altas import procesar_altas
                            from utils.document_utils import auto_group_altas
                            
                            save_dir = os.path.join(ruta_raiz, "altas_bajas")
                            os.makedirs(save_dir, exist_ok=True)
                            
                            final_path = os.path.join(save_dir, filename)
                            file.save(final_path)
                            
                            with app.app_context():
                                resultados = procesar_altas(final_path, save_dir, gestoria_id=emp.gestoria_id)
                                
                            if resultados:
                                res = resultados[0]
                                categoria_v = res.get('categoria_final', DocumentCategories.ALTAS_TRABAJADORES)
                                
                                doc = Documento(
                                    nombre_archivo=filename,
                                    ruta_archivo=final_path,
                                    empresa_id=emp.id,
                                    gestoria_id=emp.gestoria_id,
                                    categoria=categoria_v,
                                    procesado=True,
                                    datos_extraidos=res,
                                    subido_por=current_user.id,
                                    file_hash=file_hash
                                )
                                db.session.add(doc)
                                db.session.commit()
                                
                                # ✅ Agrupación automática
                                auto_group_altas(doc.id, emp.gestoria_id, current_user.id)
                                
                                return jsonify({
                                    NotificationTypes.SUCCESS: True, 
                                    "message": f"Clasificado como {categoria_v}: {emp.nombre}", 
                                    "empresa": emp.nombre,
                                    "categoria": categoria_v
                                })
                        except Exception as e:
                            logger.error(f"Error procesando alta/baja en upload genérico: {e}")
                            traceback.print_exc()

                # --- PROCESO ESTÁNDAR (Si no es Alta/Baja forzada o falló el proceso IA) ---
                nombre_empresa = emp.nombre
                empresa_id = emp.id
                
                try:
                    # Determinar destino final
                    from utils.storage_utils import get_empresa_storage_path
                    empresa_path = get_empresa_storage_path(get_current_gestoria_id(), nombre_empresa)
                    dest_dir = os.path.join(empresa_path, categoria_final)
                    os.makedirs(dest_dir, exist_ok=True)
                    
                    dest = os.path.join(dest_dir, filename)
                    shutil.move(temp_path, dest)
                    
                    nuevo_doc = Documento(
                        empresa_id=emp.id,
                        gestoria_id=get_current_gestoria_id(),
                        nombre_archivo=filename, 
                        ruta_archivo=dest, 
                        categoria=categoria_final,
                        procesado=esta_procesado,
                        file_hash=file_hash,
                        datos_extraidos=datos_auto if datos_auto else None
                    )
                    db.session.add(nuevo_doc)
                    db.session.commit()
                    
                    # Intentar limpiar caché
                    try:
                        cache.delete(f'empresa_{empresa_id}_documentos')
                        cache.delete('view_/api/empresas')
                    except: pass
                    
                    # Notificar
                    try:
                        notificar(
                            "Nuevo Documento", 
                            f"Recibido para {nombre_empresa} en {categoria_final}", 
                            emp.gestoria_id, 
                            departamento=dept_notif, 
                            link=f"/empresa/{empresa_id}/{categoria_final}", 
                            tipo=NotificationTypes.SUCCESS
                        )
                    except: pass
                    
                    return jsonify({
                        NotificationTypes.SUCCESS: True, 
                        "message": f"Clasificado: {nombre_empresa} -> {categoria_final}", 
                        "empresa": nombre_empresa,
                        "categoria": categoria_final
                    })
                except Exception as db_error:
                    db.session.rollback()
                    logger.error(f"Error en DB al clasificar: {str(db_error)}")
                    return jsonify({NotificationTypes.SUCCESS: True, "message": f"Archivo movido a {nombre_empresa} (error en BD: {str(db_error)})", "empresa": nombre_empresa})
            else:
                # Sin NIF, sin CCC coincidente y sin nombre reconocible → inbox
                if nif_clean:
                    razon = f"NIF {nif_clean} no registrado"
                    tipo_notif = NotificationTypes.ERROR
                else:
                    razon = "NIF/CCC/Nombre no detectados"
                    tipo_notif = NotificationTypes.WARNING
                shutil.move(temp_path, os.path.join(ruta_inbox, filename))
                notificar("Archivo sin clasificar", f"{razon}: {filename}", get_current_gestoria_id(), departamento="Administrativo", link="/no-clasificados", tipo=tipo_notif)
                try:
                    _gestoria_id = get_current_gestoria_id()
                    socketio.emit('inbox_actualizado', {'gestoria_id': _gestoria_id, 'filename': filename, 'nif': nif_clean}, room=f'gestoria_staff_{_gestoria_id}')
                except Exception:
                    pass
                return jsonify({NotificationTypes.SUCCESS: True, "message": f"Enviado al Inbox ({razon})", "nif": nif_clean})
        except Exception as e: 
            print(f"🔥 ERROR CRÍTICO en clasificar_y_subir: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.error(f"Error en clasificar_y_subir: {str(e)}", exc_info=True)
            return jsonify({NotificationTypes.ERROR: f"Error interno del servidor: {str(e)}"}), 500
    
    @app.route('/api/procesar-impuestos', methods=['POST'])
    @login_required
    @limiter.limit("10 per minute")
    def procesar_impuestos():
        """
        Procesa documentos de impuestos con OCR especializado.
        Detecta: NIF, Modelo, Estado (NEGATIVA/SIN ACTIVIDAD/RESULTADO CERO), Calidad (Colaborador/Titular)
        Límite: 100 archivos por subida
        """
        try:
            files = request.files.getlist('files[]')
            if not files:
                return jsonify({'success': False, 'message': 'No se recibieron archivos'}), 400
            
            if len(files) > 100:
                return jsonify({'success': False, 'message': 'Límite máximo de 100 archivos por subida excedido'}), 400
            
            # --- VALIDACIÓN DE TIPO DE DOCUMENTO ---
            force_guardado = request.form.get('force', 'false').lower() == 'true'
            if not force_guardado:
                from utils.document_detector import predecir_categoria_documento
                import tempfile
                for file in files:
                    temp_dir_val = tempfile.mkdtemp()
                    temp_pdf_path_val = os.path.join(temp_dir_val, secure_filename(file.filename))
                    file.save(temp_pdf_path_val)
                    
                    deteccion = predecir_categoria_documento(temp_pdf_path_val)
                    file.seek(0)
                    shutil.rmtree(temp_dir_val, ignore_errors=True)
                    
                    if deteccion.get("analizado") and deteccion.get("tipo_detectado") not in ["impuestos", "desconocido"]:
                        return jsonify({
                            'success': False,
                            'estado': 'confirmacion',
                            'detectado': deteccion.get("tipo_detectado"),
                            'empresa_detectada': deteccion.get("empresa_detectada"),
                            'filename': file.filename,
                            'message': f'El archivo {file.filename} parece ser de tipo {deteccion.get("tipo_detectado").replace("_", " ")}. ¿Continuar como Impuestos?'
                        }), 400
            
            gestoria_id = get_current_gestoria_id()
            
            # Importar extractor de impuestos
            from services.impuesto_extractor import ImpuestoExtractor
            extractor = ImpuestoExtractor()
            
            resultados = []
            exitosos = 0
            errores = 0
            
            for file in files:
                try:
                    # Validar archivo
                    if file.filename == '':
                        resultados.append({
                            'filename': 'Sin nombre',
                            'success': False,
                            'error': 'Nombre de archivo vacío'
                        })
                        errores += 1
                        continue
                    
                    filename = secure_filename(file.filename)
                    
                    # Validar extensión
                    if not filename.lower().endswith('.pdf'):
                        resultados.append({
                            'filename': filename,
                            'success': False,
                            'error': 'Solo se permiten archivos PDF'
                        })
                        errores += 1
                        continue
                    
                    # Guardar temporalmente
                    import tempfile
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    file.save(temp_path)
                    
                    # Extraer datos con OCR
                    datos_impuesto = extractor.extract_tax_data(temp_path)
                    
                    # Buscar empresa por NIF
                    empresa = None
                    if datos_impuesto['nif']:
                        nif_clean = re.sub(r'[\s\.-]', '', datos_impuesto['nif'].strip().upper()).lstrip("ES").lstrip("0")[:9]
                        empresa = Empresa.query.filter_by(
                            nif=nif_clean,
                            gestoria_id=gestoria_id
                        ).first()
                    
                    # Determinar carpeta destino
                    from utils.storage_utils import get_empresa_storage_path, get_gestoria_inbox_path
                    if empresa:
                        carpeta_destino = get_empresa_storage_path(gestoria_id, empresa.nombre)
                        # Si es aplazamiento, asignar esa categoría; si no, Impuestos
                        if datos_impuesto.get('is_aplazamiento'):
                            categoria = 'Aplazamiento'
                        else:
                            categoria = 'Impuestos'
                        clasificado = True
                    else:
                        # No clasificado → Inbox
                        carpeta_destino = get_gestoria_inbox_path(gestoria_id)
                        categoria = 'No Clasificado'
                        clasificado = False
                    
                    os.makedirs(carpeta_destino, exist_ok=True)
                    
                    # Mover archivo
                    ruta_final = os.path.join(carpeta_destino, filename)
                    
                    # Verificar si ya existe
                    if os.path.exists(ruta_final):
                        os.remove(temp_path)
                        resultados.append({
                            'filename': filename,
                            'success': False,
                            'error': 'El archivo ya existe'
                        })
                        errores += 1
                        continue
                    
                    shutil.move(temp_path, ruta_final)
                    
                    # ✅ Si es un aplazamiento, copiar también a carpeta Aplazamientos
                    if datos_impuesto.get('is_aplazamiento') and empresa:
                        carpeta_aplazamientos = os.path.join(
                            get_empresa_storage_path(gestoria_id, empresa.nombre),
                            'Aplazamientos'
                        )
                        os.makedirs(carpeta_aplazamientos, exist_ok=True)
                        ruta_aplazamiento = os.path.join(carpeta_aplazamientos, filename)
                        
                        # Copiar archivo (no mover, porque ya está en Impuestos)
                        shutil.copy2(ruta_final, ruta_aplazamiento)
                        logger.info(f"📋 Aplazamiento copiado a: {ruta_aplazamiento}")
                    
                    # Crear registro en BD
                    documento = Documento(
                        empresa_id=empresa.id if empresa else None,
                        gestoria_id=gestoria_id,
                        categoria=categoria,
                        nombre_archivo=filename,
                        ruta_archivo=ruta_final,
                        procesado=True,
                        fecha_procesado=datetime.utcnow(),
                        periodo=datos_impuesto.get('ejercicio'),
                        datos_extraidos={
                            'modelo': datos_impuesto['modelo'],
                            'es_negativa': datos_impuesto['es_negativa'],
                            'sin_actividad': datos_impuesto['sin_actividad'],
                            'resultado_cero': datos_impuesto['resultado_cero'],
                            'calidad': datos_impuesto['calidad'],
                            'confianza_ocr': datos_impuesto['confianza'],
                            'nif_detectado': datos_impuesto['nif'],
                            'fecha_presentacion': datos_impuesto.get('fecha_presentacion'),
                            'numero_justificante': datos_impuesto.get('numero_justificante'),
                            'expediente': datos_impuesto.get('expediente'),
                            'csv': datos_impuesto.get('csv'),
                            'razon_social': datos_impuesto.get('razon_social'),
                            'resultado_texto': datos_impuesto.get('resultado_texto'),
                            'is_aplazamiento': datos_impuesto.get('is_aplazamiento', False),
                            'detalle_liquidacion': datos_impuesto.get('detalle_liquidacion'),
                            'ejercicio': datos_impuesto.get('ejercicio')
                        }
                    )
                    db.session.add(documento)
                    db.session.commit()
                    
                    resultados.append({
                        'filename': filename,
                        'success': True,
                        'empresa': empresa.nombre if empresa else 'No clasificado',
                        'nif': datos_impuesto['nif'],
                        'modelo': datos_impuesto['modelo'],
                        'calidad': datos_impuesto['calidad'],
                        'clasificado': clasificado
                    })
                    exitosos += 1
                    
                except Exception as e:
                    logger.error(f"Error procesando {file.filename}: {e}")
                    resultados.append({
                        'filename': file.filename,
                        'success': False,
                        'error': str(e)
                    })
                    errores += 1
                    
                    # Limpiar archivo temporal si existe
                    try:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except:
                        pass
            
            return jsonify({
                'success': exitosos > 0,
                'total': len(files),
                'exitosos': exitosos,
                'errores': errores,
                'detalles': resultados
            })
            
        except Exception as e:
            logger.error(f"Error en procesar_impuestos: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/tenant/info', methods=['GET'])
    def get_tenant_info():
        """
        Obtiene información del tenant.
        - Si el usuario está logueado: usa su gestoria_id
        - Si no está logueado: usa el slug (para página de login)
        """
        gestoria = None
        
        # Si el usuario está autenticado, usar su gestoria_id
        if current_user.is_authenticated:
            gestoria = Gestoria.query.filter_by(id=current_user.gestoria_id, activa=True).first()
        else:
            # Si no está autenticado, usar slug (para login page)
            slug = request.args.get('slug', 'principal')
            
            # Validar slug (solo alfanumérico y guiones)
            import re
            if not re.match(r'^[a-z0-9-]+$', slug):
                slug = 'principal'
            
            gestoria = Gestoria.query.filter_by(slug=slug, activa=True).first()
        
        if not gestoria:
            # Fallback a gestoría principal
            gestoria = Gestoria.query.filter_by(id=1).first()
        
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Tenant no encontrado"}), 404
        
        # ⭐ Sanitizar configuración para evitar fuga de credenciales
        safe_config = (gestoria.configuracion or {}).copy()
        for key in ['saltra', 'api_key', 'api_secret', 'password', 'token', 'cert_secret']:
            if key in safe_config:
                del safe_config[key]

        return jsonify({
            NotificationTypes.SUCCESS: True,
            "tenant": {
                "id": gestoria.id,
                "nombre": gestoria.nombre,
                "slug": gestoria.slug,
                "email": gestoria.email,
                "configuracion": safe_config
            }
        })
        
    @app.route('/api/nif/asignar', methods=['POST'])
    @login_required
    def asignar_nif():
        try:
            data = request.json
            empresa_id = data.get('empresa_id')
            categoria_destino = data.get('categoria', DocumentCategories.POR_PROCESAR)
            
            emp = db.session.get(Empresa, empresa_id)
            
            if not emp:
                return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
            
            if data.get('crear_alias'):
                nif = re.sub(r'[\s\.-]', '', data['nif'].strip().upper()).lstrip("ES").lstrip("0")[:9]
                if nif and not AliasNIF.query.filter_by(nif=nif).first(): 
                    db.session.add(AliasNIF(nif=nif, empresa_id=emp.id))
            
            # Buscar en inbox de la gestoría
            from utils.storage_utils import get_gestoria_inbox_path
            inbox_path = get_gestoria_inbox_path(get_current_gestoria_id())
            orig = os.path.join(inbox_path, data['nombre_archivo'])
            
            # Verificar que el archivo existe
            if not os.path.exists(orig):
                return jsonify({NotificationTypes.ERROR: "Archivo no encontrado en inbox"}), 404
            
            # Ruta destino (multi-tenant)
            from utils.storage_utils import get_empresa_storage_path
            empresa_path = get_empresa_storage_path(get_current_gestoria_id(), emp.nombre)
            dest = os.path.join(empresa_path, data['nombre_archivo'])
            
            # ✅ CORRECCIÓN: Calcular hash ANTES de mover el archivo
            file_hash_asignar = get_file_hash(orig)
            
            # Mover archivo después de calcular hash
            shutil.move(orig, dest)
            
            db.session.add(Documento(
                empresa_id=emp.id,
                gestoria_id=get_current_gestoria_id(),  # Multi-tenant
                nombre_archivo=data['nombre_archivo'], 
                ruta_archivo=dest, 
                categoria=categoria_destino,
                file_hash=file_hash_asignar
            ))
            db.session.commit()
            
            # Intentar notificar (no crítico)
            try:
                notificar("Asignado", f"{data['nombre_archivo']} a {emp.nombre}", emp.gestoria_id, departamento="Administrativo", link=f"/empresa/{emp.id}/{categoria_destino}")
            except:
                pass
            
            return jsonify({NotificationTypes.SUCCESS: True})
            
        except FileNotFoundError:
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: "Archivo no encontrado"}), 404
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error asignando archivo: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: f"Error al asignar: {str(e)}"}), 500
    
    
    @app.route('/api/escanear-raiz', methods=['POST'])
    @login_required
    def scan_root():
        root = app.config['RUTA_RAIZ_NOTIFICACIONES']; count = 0
        if not os.path.exists(root): return jsonify({NotificationTypes.ERROR: "Ruta inválida"}), 400
        for emp_name in os.listdir(root):
            emp_path = os.path.join(root, emp_name)
            if not os.path.isdir(emp_path) or emp_name.startswith('__'): continue
            emp = Empresa.query.filter_by(nombre=emp_name, gestoria_id=get_current_gestoria_id()).first()
            if not emp: continue
            for cat_db, cat_fs in {DocumentCategories.POR_PROCESAR: DocumentCategories.POR_PROCESAR, DocumentCategories.NOTIFICACIONES: DocumentCategories.NOTIFICACIONES}.items():
                cp = os.path.join(emp_path, cat_fs)
                if os.path.exists(cp):
                    for f in os.listdir(cp):
                        if f.endswith('.pdf'):
                            p = os.path.join(cp, f)
                            if not Documento.query.filter_by(empresa_id=emp.id, ruta_archivo=p).first():
                                db.session.add(Documento(empresa_id=emp.id, gestoria_id=get_current_gestoria_id(), nombre_archivo=f, ruta_archivo=p, categoria=cat_db)); count += 1
        db.session.commit(); cache.clear(); return jsonify({NotificationTypes.SUCCESS: True, "mensaje": f"Completado. {count} nuevos."})

    # ==========================================
    # TAREAS, NOTIFICACIONES, BÚSQUEDA, PLANTILLAS
    # ==========================================
    
    @app.route('/api/tareas/calendario', methods=['GET'])
    @login_required
    def get_cal():
        """Obtener tareas para calendario - MULTI-TENANT: Filtrar por gestoria_id"""
        from models import Tarea
        
        # MULTI-TENANT: Filtrar tareas por usuario actual
        q = Tarea.query.filter_by(asignado_a_id=current_user.id)
        
        # Opcional: filtrar solo pendientes y en_progreso
        estado_filter = request.args.get('estado')
        if estado_filter:
            q = q.filter_by(estado=estado_filter)
        else:
            # Por defecto, mostrar solo pendientes y en progreso
            q = q.filter(Tarea.estado.in_([TaskStates.PENDIENTE, TaskStates.EN_PROGRESO]))
        
        tareas = q.all()
        
        eventos = []
        hoy = datetime.now().date()
        
        for t in tareas:
            # Usar fecha_vencimiento si existe, sino fecha_creacion
            fecha = t.fecha_vencimiento if t.fecha_vencimiento else t.fecha_creacion
            
            # Determinar color según estado y fecha
            if t.estado == TaskStates.COMPLETADA:
                backgroundColor = '#10b981'  # Verde
                borderColor = '#059669'
            else:
                # Calcular días hasta vencimiento
                if t.fecha_vencimiento:
                    vencimiento_date = t.fecha_vencimiento.date() if hasattr(t.fecha_vencimiento, 'date') else t.fecha_vencimiento
                    dias_hasta_vencimiento = (vencimiento_date - hoy).days
                    
                    # Rojo: Vencida o próxima a vencer (≤3 días)
                    if dias_hasta_vencimiento < 0 or dias_hasta_vencimiento <= 3:
                        backgroundColor = '#ef4444'  # Rojo (vencida o crítica)
                        borderColor = '#dc2626'
                    # Amarillo: Advertencia (4-7 días)
                    elif dias_hasta_vencimiento <= 7:
                        backgroundColor = '#f59e0b'  # Amarillo (advertencia)
                        borderColor = '#d97706'
                    # Azul: Futuras (>7 días)
                    else:
                        backgroundColor = '#3b82f6'  # Azul (futura)
                        borderColor = '#2563eb'
                else:
                    backgroundColor = '#3b82f6'  # Azul por defecto
                    borderColor = '#2563eb'
            
            eventos.append({
                'title': t.titulo,
                'start': fecha.isoformat() if fecha else None,
                'end': fecha.isoformat() if fecha else None,
                'allDay': True,
                'backgroundColor': backgroundColor,
                'borderColor': borderColor,
                'textColor': '#ffffff',
                'data': {
                    'id': t.id,
                    'descripcion': t.descripcion,
                    'estado': t.estado,
                    'prioridad': t.prioridad,
                    'empresa_id': t.empresa_id,
                    'documento_id': t.documento_id
                }
            })
        
        return jsonify({NotificationTypes.SUCCESS: True, "eventos": eventos})

    @app.route('/api/tareas/conteo', methods=['GET'])
    @login_required
    def count_tareas():
        """Contar tareas pendientes - MULTI-TENANT: Filtrar por usuario"""
        from models import Tarea
        
        # Contar tareas pendientes del usuario actual
        total = Tarea.query.filter_by(
            asignado_a_id=current_user.id
        ).filter(
            Tarea.estado.in_([TaskStates.PENDIENTE, TaskStates.EN_PROGRESO])
        ).count()
        
        return jsonify({NotificationTypes.SUCCESS: True, "total": total})
    
    @app.route('/api/documentos/buscar-por-nombre', methods=['POST'])
    @login_required
    def buscar_documento_por_nombre():
        """Buscar documento por nombre de archivo - Para enlaces en chat"""
        from urllib.parse import quote
        
        data = request.json
        nombre_archivo = data.get('nombre_archivo', '').strip()
        
        if not nombre_archivo:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Nombre de archivo requerido"}), 400
        
        # Buscar documento por nombre exacto en la gestoría actual
        doc = Documento.query.join(Empresa).filter(
            Documento.nombre_archivo == nombre_archivo,
            Empresa.gestoria_id == get_current_gestoria_id()
        ).first()
        
        if not doc or not doc.empresa:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Documento no encontrado"}), 404
        
        # Generar URL para navegar al documento
        categoria_encoded = quote(doc.categoria)
        url = f"/empresa/{doc.empresa_id}/{categoria_encoded}?doc={doc.id}"
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "documento": {
                "id": doc.id,
                "nombre_archivo": doc.nombre_archivo,
                "empresa_id": doc.empresa_id,
                "empresa_nombre": doc.empresa.nombre,
                "categoria": doc.categoria,
                "url": url
            }
        })

    @app.route('/api/notificaciones', methods=['GET'])
    @login_required
    def get_notificaciones():
        """
        Obtener notificaciones del usuario - MULTI-TENANT: Filtrar por gestoria_id
        Incluye también los Comunicados no leídos.
        """
        # 1. Notificaciones estándar
        q_notif = Notificacion.query.filter(
            Notificacion.leida == False,
            Notificacion.gestoria_id == current_user.gestoria_id
        )
        
        if current_user.is_invitado():
            allowed_company_ids = current_user.get_allowed_company_ids()
            q_notif = q_notif.filter(Notificacion.empresa_id.in_(allowed_company_ids))
        elif getattr(current_user, 'departamento', None) and current_user.departamento.nombre != 'Jefatura':
            q_notif = q_notif.filter(Notificacion.user_id == current_user.id)
            
        notificaciones = q_notif.order_by(Notificacion.fecha_creacion.desc()).limit(50).all()
        list_notif = [n.to_dict() for n in notificaciones]

        # 2. Comunicados relevantes y no leídos
        from models import Comunicado
        q_com = Comunicado.query.filter_by(gestoria_id=current_user.gestoria_id, activo=True)
        
        # Filtrar por alcance (igual que en get_comunicados)
        if current_user.is_invitado() and not current_user.is_super_admin:
            allowed_company_ids = current_user.get_allowed_company_ids()
            allowed_group_ids = [ga.grupo_id for ga in current_user.grupo_accesos]
            from sqlalchemy import or_
            q_com = q_com.filter(or_(
                Comunicado.alcance == 'global',
                (Comunicado.alcance == 'grupo') & (Comunicado.filtro_id.in_(allowed_group_ids)),
                (Comunicado.alcance == 'empresa') & (Comunicado.filtro_id.in_(allowed_company_ids))
            ))
        
        # Ordenar por prioridad y fecha
        from sqlalchemy import case
        p_order = case(
            (Comunicado.prioridad == 'alta', 0),
            (Comunicado.prioridad == 'media', 1),
            (Comunicado.prioridad == 'baja', 2),
            else_=3
        )
        comunicados_all = q_com.order_by(p_order.asc(), Comunicado.fecha_creacion.desc()).limit(15).all()
        
        # Filtrar unread en memoria (más simple para JSON fields)
        comunicados_unread = [c for c in comunicados_all if current_user.id not in (c.leido_por or [])]
        
        # Transformar a formato notificacion
        for c in comunicados_unread:
            p_score = 2 # baja
            if c.prioridad == 'alta': p_score = 0
            elif c.prioridad == 'media': p_score = 1
            
            list_notif.append({
                'id': f"com-{c.id}",
                'titulo': f"📢 {c.titulo}",
                'mensaje': c.contenido[:100] + ('...' if len(c.contenido) > 100 else ''),
                'tipo': 'comunicado',
                'link': '/empresas', # Ir al muro
                'leida': False,
                'fecha': c.fecha_creacion.isoformat() + 'Z' if c.fecha_creacion else None,
                'is_comunicado': True,
                'p_score': p_score
            })

        # Re-ordenar la lista combinada: 
        # Criterio: p_score (menor es más prioritario), luego fecha descendente
        def get_sort_tuple(x):
            ps = x.get('p_score', 5) # 5 para notificaciones normales
            return (ps, -(datetime.fromisoformat(x['fecha'].replace('Z', '')).timestamp() if x['fecha'] else 0))

        from datetime import datetime
        list_notif.sort(key=get_sort_tuple)

        return jsonify({
            NotificationTypes.SUCCESS: True,
            "notificaciones": list_notif,
            "total": len(list_notif)
        })

    @app.route('/api/notificaciones/<int:id>/leer', methods=['POST'])
    @login_required
    def marcar_notificacion_leida(id):
        notif = Notificacion.query.get_or_404(id)
        notif.leida = True
        db.session.commit()
        return jsonify({'success': True})
    
    # ==========================================
    # PREFERENCIAS DE NOTIFICACIONES PUSH
    # ==========================================
    
    @app.route('/api/notifications/preferences', methods=['GET'])
    @login_required
    def get_notification_preferences():
        """Obtener preferencias de notificación del usuario actual"""
        try:
            from services.notification_service import NotificationService
            prefs = NotificationService.get_user_preferences(current_user.id)
            return jsonify({
                'success': True,
                'preferences': prefs
            })
        except Exception as e:
            print(f"Error obteniendo preferencias: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/notifications/preferences', methods=['PUT'])
    @login_required
    def update_notification_preferences():
        """Actualizar preferencias de notificación"""
        try:
            from services.notification_service import NotificationService
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No se recibieron datos'}), 400
            
            NotificationService.update_preferences(current_user.id, data)
            
            return jsonify({
                'success': True,
                'message': 'Preferencias actualizadas correctamente'
            })
        except Exception as e:
            print(f"Error actualizando preferencias: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/notifications/test', methods=['POST'])
    @login_required
    def test_notification():
        """Enviar notificación de prueba al usuario actual"""
        try:
            socketio = current_app.extensions.get('socketio')
            if not socketio:
                return jsonify({'error': 'WebSocket no disponible'}), 500

            # Emitir notificación de prueba al usuario
            socketio.emit('test_notification', {
                'title': '🔔 Notificación de Prueba',
                'body': 'Las notificaciones están funcionando correctamente',
                'icon': '/logo192.png',
                'tag': 'test-notification'
            }, room=f'user_{current_user.id}')
            
            logger.info(f"Notificación de prueba enviada a user_{current_user.id}")
            
            return jsonify({
                'success': True,
                'message': 'Notificación de prueba enviada'
            })
        except Exception as e:
            print(f"Error enviando notificación de prueba: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/plantillas', methods=['GET'])
    @login_required
    def get_plantillas():
        """Obtener solo las plantillas propias de la gestoría (incluye importadas)"""
        try:
            gestoria_id = get_current_gestoria_id()
            logger.info(f"DEBUG_PLANTILLAS: Obteniendo plantillas para gestoria_id={gestoria_id}")
            plantillas = Plantilla.query.filter(Plantilla.gestoria_id == gestoria_id).all()
            logger.info(f"DEBUG_PLANTILLAS: Encontradas {len(plantillas)} plantillas")
            return jsonify({NotificationTypes.SUCCESS: True, "plantillas": [p.to_dict() for p in plantillas]})
        except Exception as e:
            logger.error(f"ERROR en get_plantillas: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plantillas/marketplace', methods=['GET'])
    @login_required
    def get_marketplace_plantillas():
        """Obtener plantillas públicas que NO pertenecen a la gestoría actual"""
        try:
            gestoria_id = get_current_gestoria_id()
            logger.info(f"DEBUG_PLANTILLAS: Buscando Marketplace para gestoria_id={gestoria_id}")
            
            # Obtener IDs de plantillas ya importadas para no duplicar en la lista
            importadas_ids = [p.id_original for p in Plantilla.query.filter(
                Plantilla.gestoria_id == gestoria_id, 
                Plantilla.id_original != None
            ).all() if p.id_original is not None]

            # Mostrar plantillas que:
            # 1. Son públicas
            # 2. Son del sistema (gestoria_id IS NULL) O de cualquier gestoría (INCLUIDA la mía)
            query = Plantilla.query.filter(
                Plantilla.es_publica == True
            )
            
            # 3. No las he importado ya (Evitar not_in([]) si la lista está vacía)
            # Nota: Si es mi propia plantilla original, no necesito filtrarla del marketplace
            if importadas_ids:
                query = query.filter(Plantilla.id.not_in(importadas_ids))
            
            plantillas = query.all()
            logger.info(f"DEBUG_PLANTILLAS: Encontradas {len(plantillas)} plantillas en Marketplace")
            return jsonify({NotificationTypes.SUCCESS: True, "plantillas": [p.to_dict() for p in plantillas]})
        except Exception as e:
            logger.error(f"ERROR en get_marketplace_plantillas: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plantillas', methods=['POST'])
    @login_required
    def crear_plantilla():
        """Crear una plantilla para la gestoría actual"""
        # Solo Jefatura o Admin pueden crear plantillas
        if current_user.rol.nombre not in ['Jefatura', 'Super Admin', 'admin-gestoria']:
            print(f"⚠️ Acceso denegado a crear plantilla para usuario {current_user.nombre} con rol {current_user.rol.nombre}")
            return jsonify({NotificationTypes.ERROR: f"Permiso denegado. Rol actual: {current_user.rol.nombre}"}), 403
            
        d = request.json
        gestoria_id = get_current_gestoria_id()
        
        # Verificar código duplicado en la misma gestoría
        if Plantilla.query.filter_by(codigo=d['codigo'], gestoria_id=gestoria_id).first():
            return jsonify({NotificationTypes.ERROR: "Ya existe una plantilla con este código"}), 400
            
        new = Plantilla(
            gestoria_id=gestoria_id,
            codigo=d['codigo'], 
            nombre=d['nombre'], 
            descripcion=d.get('descripcion'), 
            campos=d.get('campos',{}), 
            prompt_template=d.get('prompt_template'),
            patron_deteccion=d.get('patron_deteccion'),
            categoria_default=d.get('categoria_default'),
            departamento_default=d.get('departamento_default'),
            es_publica=d.get('es_publica', False),
            ejemplo=d.get('ejemplo', {})
        )
        db.session.add(new)
        db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, "plantilla": new.to_dict()})

    @app.route('/api/plantillas/<int:plantilla_id>/votar', methods=['POST'])
    @login_required
    def votar_plantilla(plantilla_id):
        """Incrementar votos de una plantilla en el marketplace"""
        try:
            plantilla = Plantilla.query.get_or_404(plantilla_id)
            if not plantilla.es_publica:
                return jsonify({"error": "Solo se pueden votar plantillas públicas"}), 400
            
            plantilla.votos = (plantilla.votos or 0) + 1
            db.session.commit()
            return jsonify({NotificationTypes.SUCCESS: True, "votos": plantilla.votos})
        except Exception as e:
            logger.error(f"Error al votar plantilla: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/plantillas/<int:id>/importar', methods=['POST'])
    @login_required
    def importar_plantilla_marketplace(id):
        """Clona una plantilla del marketplace a la gestoría actual"""
        original = db.session.get(Plantilla, id)
        if not original or not original.es_publica:
            return jsonify({NotificationTypes.ERROR: "Plantilla no encontrada o no es pública"}), 404
            
        gestoria_id = get_current_gestoria_id()
        
        # Evitar duplicados
        nuevo_codigo = f"{original.codigo}_copy_{gestoria_id}"
        if Plantilla.query.filter_by(codigo=nuevo_codigo, gestoria_id=gestoria_id).first():
            return jsonify({NotificationTypes.ERROR: "Ya has importado esta plantilla"}), 400
            
        nueva = Plantilla(
            gestoria_id=gestoria_id,
            codigo=nuevo_codigo,
            nombre=f"{original.nombre} (Importada)",
            descripcion=original.descripcion,
            campos=original.campos,
            prompt_template=original.prompt_template,
            patron_deteccion=original.patron_deteccion,
            categoria_default=original.categoria_default,
            departamento_default=original.departamento_default,
            id_original=original.id,
            es_publica=False,
            ejemplo=original.ejemplo
        )
        db.session.add(nueva)
        db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, "plantilla": nueva.to_dict()})

    @app.route('/api/plantillas/<int:id>', methods=['PUT', 'DELETE'])
    @login_required
    def handle_plantilla_v2(id):
        """Gestiona (Edita/Elimina) una plantilla propia"""
        p = db.session.get(Plantilla, id)
        if not p: return jsonify({NotificationTypes.ERROR: "No existe"}), 404
        
        gestoria_id = get_current_gestoria_id()
        # Solo puede editar/borrar si es suya o es SuperAdmin global
        allowed_roles = ['Jefatura', 'Super Admin', 'Admin', 'Administrador', 'Gerencia']
        if p.gestoria_id != gestoria_id and not current_user.is_super_admin and current_user.rol.nombre not in allowed_roles:
            return jsonify({NotificationTypes.ERROR: "No tienes permiso sobre esta plantilla"}), 403

        if request.method == 'DELETE':
            if p.codigo == 'notificacion_generica': return jsonify({NotificationTypes.ERROR: "Protegida"}), 400
            db.session.delete(p); db.session.commit(); return jsonify({NotificationTypes.SUCCESS: True})
            
        try:
            d = request.json
            p.nombre = d.get('nombre', p.nombre)
            p.descripcion = d.get('descripcion', p.descripcion)
            p.campos = d.get('campos', p.campos)
            p.prompt_template = d.get('prompt_template', p.prompt_template)
            p.patron_deteccion = d.get('patron_deteccion', p.patron_deteccion)
            p.categoria_default = d.get('categoria_default', p.categoria_default)
            p.departamento_default = d.get('departamento_default', p.departamento_default)
            p.es_publica = d.get('es_publica', p.es_publica)
            p.ejemplo = d.get('ejemplo', p.ejemplo)
            
            # Nuevos campos del Test Bench - Manejo seguro
            if 'score_confianza' in d: p.score_confianza = float(d['score_confianza'])
            if 'activa' in d: p.activa = bool(d['activa'])
            if 'umbral_activacion' in d: p.umbral_activacion = float(d['umbral_activacion'])

            db.session.commit()
            return jsonify({NotificationTypes.SUCCESS: True, "plantilla": p.to_dict()})
        except Exception as e:
            db.session.rollback()
            import traceback
            error_msg = f"Error guardando plantilla: {str(e)}\n{traceback.format_exc()}"
            print(error_msg) # Para logs
            return jsonify({NotificationTypes.ERROR: str(e), "details": error_msg}), 500


    @app.route('/api/config/categories-and-departments', methods=['GET'])
    @login_required
    def get_categories_and_departments():
        from constants import DocumentCategories, Departments
        return jsonify({
            "categories": DocumentCategories.all(),
            "departments": Departments.all()
        })

    @app.route('/api/buscar')
    @login_required
    def buscar_global():
        """Búsqueda global en empresas y documentos"""
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'empresas': [], 'documentos': []})
        
        # Buscar empresas
        emps = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
            or_(Empresa.nombre.ilike(f'%{q}%'), Empresa.nif.ilike(f'%{q}%'))
        ).limit(5).all()
        
        # Buscar documentos
        dq = Documento.query.filter(Documento.nombre_archivo.ilike(f'%{q}%'), Documento.gestoria_id==get_current_gestoria_id())
        if current_user.departamento.nombre != 'Jefatura': 
            dq = dq.filter(or_(Documento.estado_tarea == None, Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%')))
        docs = dq.limit(5).all()

        # Formatear resultados
        empresas_res = []
        for e in emps:
            empresas_res.append({"tipo": "empresa", "id": e.id, "titulo": e.nombre, "subtitulo": e.nif, "link": f"/empresa/{e.id}"})
        
        documentos_res = []
        for d in docs:
            documentos_res.append({"tipo": "documento", "id": d.id, "titulo": d.nombre_archivo, "subtitulo": "", "link": f"/empresa/{d.empresa_id}/{d.categoria}"})

        return jsonify({NotificationTypes.SUCCESS: True, "empresas": empresas_res, "documentos": documentos_res})

    @app.route('/api/tasks/<tid>', methods=['GET'])
    @login_required
    def get_task(tid):
        from celery_worker import celery; from celery.result import AsyncResult
        t = AsyncResult(tid, app=celery)
        res = {'state': t.state, 'progress': 0}
        if t.state == 'SUCCESS': res.update({'progress': 100, 'result': t.info})
        elif t.state == 'PROCESSING': res.update({'progress': t.info.get('progress', 0)})
        elif t.state == 'FAILURE': res.update({NotificationTypes.ERROR: str(t.info)})
        return jsonify(res)

    @app.route('/api/health', methods=['GET'])
    def health(): return jsonify({"status": "ok"}), 200


# ==========================================
    # SALTRA DEHU
    # ==========================================
    
    @app.route('/api/saltra/notificaciones', methods=['GET'])
    @login_required
    def get_saltra_notificaciones():
        """Lista notificaciones de Saltra con filtros - MULTI-TENANT"""
        from models_saltra import NotificacionSaltra
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        estado = request.args.get('estado')  # ACEPTADA, PENDIENTE
        empresa_id = request.args.get('empresa_id', type=int)
        nif = request.args.get('nif')
        sin_empresa = request.args.get('sin_empresa') == 'true'
        
        # ✅ FASE 2: Nuevos filtros de búsqueda avanzada
        identifier = request.args.get('identifier')  # Número de notificación
        emitter_entity = request.args.get('emitter_entity')  # Organismo emisor
        start_date = request.args.get('start_date')  # Fecha inicio
        end_date = request.args.get('end_date')  # Fecha fin
        
        q = NotificacionSaltra.query
        
        # MULTI-TENANT: Filtrar por gestoría del usuario actual
        q = q.filter(NotificacionSaltra.gestoria_id == current_user.gestoria_id)
        
        if estado:
            q = q.filter(NotificacionSaltra.state == estado)
        if empresa_id:
            q = q.filter(NotificacionSaltra.empresa_id == empresa_id)
        # Filtros opcionales
        nif = request.args.get('nif')
        if nif:
            from utils import escape_like
            nif_safe = escape_like(nif)
            q = q.filter(NotificacionSaltra.nif_titular.ilike(f'%{nif_safe}%', escape='\\'))
        if sin_empresa:
            q = q.filter(NotificacionSaltra.empresa_id == None)
        
        identifier = request.args.get('identifier')
        if identifier:
            from utils import escape_like
            identifier_safe = escape_like(identifier)
            q = q.filter(NotificacionSaltra.identifier.ilike(f'%{identifier_safe}%', escape='\\'))
        
        emitter_entity = request.args.get('emitter_entity')
        if emitter_entity:
            from utils import escape_like
            emitter_safe = escape_like(emitter_entity)
            q = q.filter(NotificacionSaltra.emitter_entity.ilike(f'%{emitter_safe}%', escape='\\'))
        if start_date:
            from datetime import datetime
            from sqlalchemy import func
            # Comparar solo la fecha, ignorando la hora
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            q = q.filter(func.date(NotificacionSaltra.availability_date) >= start_dt)
        if end_date:
            from datetime import datetime
            from sqlalchemy import func
            # Comparar solo la fecha, ignorando la hora
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            q = q.filter(func.date(NotificacionSaltra.availability_date) <= end_dt)
        
        total = q.count()
        items = q.order_by(NotificacionSaltra.availability_date.desc()).offset((page-1)*limit).limit(limit).all()
        
        # Calcular estadísticas
        stats = {
            'total': total,
            'con_empresa': q.filter(NotificacionSaltra.empresa_id != None).count(),
            'sin_empresa': q.filter(NotificacionSaltra.empresa_id == None).count(),
            'pdfs_descargados': q.filter(NotificacionSaltra.pdf_descargado == True).count()
        }
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "total": total,
            "page": page,
            "limit": limit,
            "stats": stats,
            "notificaciones": [n.to_dict_simple() for n in items]
        })
    
    @app.route('/api/saltra/status', methods=['GET'])
    @login_required
    def get_saltra_status():
        """Obtener estado de SALTRA - MULTI-TENANT: Verifica configuración de gestoría"""
        try:
            # Verificar si la gestoría tiene SALTRA configurado
            credentials = get_saltra_credentials()
            configured = credentials is not None
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "configured": configured,
                "enabled": credentials.get('enabled', False) if credentials else False
            })
        except Exception as e:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/saltra/notificaciones/<int:id>', methods=['GET'])
    @login_required
    def get_saltra_notificacion(id):
        """Detalle de una notificación"""
        from models_saltra import NotificacionSaltra
        n = db.session.get(NotificacionSaltra, id)
        if not n:
            return jsonify({NotificationTypes.ERROR: "No encontrada"}), 404
        return jsonify({NotificationTypes.SUCCESS: True, "notificacion": n.to_dict()})
    
    @app.route('/api/saltra/sync', methods=['POST'])
    @admin_required
    def trigger_saltra_sync():
        """Dispara sincronización manual - MULTI-TENANT: Verifica credenciales de gestoría"""
        # Verificar que la gestoría tenga credenciales SALTRA configuradas
        credentials = get_saltra_credentials()
        if not credentials:
            return jsonify({
                NotificationTypes.SUCCESS: False, 
                NotificationTypes.ERROR: "SALTRA no configurado",
                "message": "Esta gestoría no tiene credenciales SALTRA configuradas. Contacta al administrador."
            }), 400
        
        
        from celery_worker import sincronizar_saltra
        
        # Sincronizar AMBOS tipos: pendientes y aceptadas
        task_done = sincronizar_saltra.delay('done', 50, current_user.gestoria_id)
        task_pending = sincronizar_saltra.delay('pending', 50, current_user.gestoria_id)
        
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            "task_ids": {
                "done": task_done.id,
                "pending": task_pending.id
            },
            "message": "Sincronización iniciada (pendientes + aceptadas)"
        })
    
    @app.route('/api/saltra/sync-all', methods=['POST'])
    @admin_required
    def sync_all_saltra_notifications():
        """
        Dispara tarea de Celery para descarga masiva de notificaciones SALTRA
        Retorna task_id para consultar progreso
        """
        try:
            from models_saltra import NotificacionSaltra
            from celery_worker import descargar_masivo_saltra
            
            gestoria_id = get_current_gestoria_id()
            
            # Verificar credenciales
            credentials = get_saltra_credentials()
            if not credentials:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: "SALTRA no configurado"
                }), 400
            
            # Obtener IDs de notificaciones pendientes (ACEPTADAS y PENDIENTES para testing)
            pendientes = NotificacionSaltra.query.filter(
                NotificacionSaltra.pdf_descargado == False,
                NotificacionSaltra.empresa_id != None,
                NotificacionSaltra.gestoria_id == gestoria_id,
                NotificacionSaltra.state.in_(['ACEPTADA', 'PENDIENTE'])  # ACEPTADAS y PENDIENTES
            ).all()
            
            if not pendientes:
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'message': 'No hay notificaciones pendientes',
                    'total': 0
                })
            
            notificacion_ids = [n.id for n in pendientes]
            
            # Disparar tarea de Celery
            task = descargar_masivo_saltra.delay(gestoria_id, notificacion_ids)
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'task_id': task.id,
                'total': len(notificacion_ids),
                'message': f'Descarga iniciada para {len(notificacion_ids)} notificaciones'
            })
            
        except Exception as e:
            logger.error(f"Error iniciando descarga masiva: {str(e)}")
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: str(e)
            }), 500
    
    @app.route('/api/saltra/sync-all/status/<task_id>', methods=['GET'])
    @login_required
    def get_saltra_download_status(task_id):
        """
        Consulta el progreso de una descarga masiva de SALTRA
        """
        try:
            import json
            from celery_worker import celery
            
            # Obtener progreso desde Redis
            progress_key = f"saltra_download_progress:{task_id}"
            progress_data = celery.backend.get(progress_key)
            
            if not progress_data:
                # Si no hay datos en Redis, consultar estado de la tarea
                from celery.result import AsyncResult
                task = AsyncResult(task_id, app=celery)
                
                return jsonify({
                    'task_id': task_id,
                    'status': task.state,
                    'progress': 0,
                    'message': 'Tarea no encontrada o expirada'
                })
            
            progress = json.loads(progress_data)
            return jsonify(progress)
            
        except Exception as e:
            logger.error(f"Error consultando progreso: {str(e)}")
            return jsonify({
                'task_id': task_id,
                'status': 'ERROR',
                'error': str(e)
            }), 500
    
    @app.route('/api/saltra/notificaciones/<int:id>/descargar-pdf', methods=['POST'])
    @login_required
    def descargar_pdf_notif_saltra(id):
        """Descarga AMBOS archivos de una notificación (documento + resguardo)"""
        from models_saltra import NotificacionSaltra
        from services.saltra_service import SaltraService
        
        try:
            # Obtener notificación
            notif = db.session.get(NotificacionSaltra, id)
            if not notif:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Notificación no encontrada"}), 404
            
            # Verificar que tenga empresa asignada
            if not notif.empresa_id:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Asigna una empresa primero"}), 400
            
            # Obtener credenciales SALTRA
            credentials = get_saltra_credentials()
            if not credentials:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "SALTRA no configurado"}), 400
            
            # Descargar ambos archivos
            saltra = SaltraService(
                api_key=credentials['email'],
                api_secret=credentials['password'],
                cert_secret=credentials['cert_secret']
            )
            result = saltra.download_notification_files(notif.sent_reference)
            
            if not result[NotificationTypes.SUCCESS]:
                return jsonify({
                    NotificationTypes.SUCCESS: False, 
                    NotificationTypes.ERROR: "No se pudo descargar ningún archivo",
                    "detalles": result['errors']
                }), 500
            
            # Rutas para guardar
            import re
            gestoria_slug = notif.empresa.gestoria.slug
            nombre_empresa_safe = re.sub(r'[^\w\s-]', '', notif.empresa.nombre).strip().replace('_', ' ')
            
            ruta_base = os.path.join(
                app.config['RUTA_RAIZ_NOTIFICACIONES'],
                gestoria_slug,
                nombre_empresa_safe,
                DocumentCategories.POR_PROCESAR
            )
            
            archivos_guardados = []
            
            # Guardar documento principal
            if result['document']:
                pdf_bytes, filename = result['document']
                ruta_doc = os.path.join(ruta_base, 'DEHU_Documentos')
                os.makedirs(ruta_doc, exist_ok=True)
                
                safe_filename = f"DOC_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                ruta_completa = os.path.join(ruta_doc, safe_filename)
                
                with open(ruta_completa, 'wb') as f:
                    f.write(pdf_bytes)
                
                doc = Documento(
                    empresa_id=notif.empresa_id,
                    gestoria_id=notif.gestoria_id,
                    nombre_archivo=os.path.basename(ruta_completa),
                    ruta_archivo=ruta_completa,
                    categoria=DocumentCategories.POR_PROCESAR,
                    procesado=False,
                    datos_extraidos={
                        'origen': 'DEHU_SALTRA',
                        'tipo': 'Documento Principal',
                        'subcategoria': 'Documentos',
                        'identifier': notif.identifier,
                        'sent_reference': notif.sent_reference
                    }
                )
                db.session.add(doc)
                archivos_guardados.append('documento')
            
            # Guardar resguardo
            if result['voucher']:
                pdf_bytes, filename = result['voucher']
                ruta_resg = os.path.join(ruta_base, 'DEHU_Resguardos')
                os.makedirs(ruta_resg, exist_ok=True)
                
                safe_filename = f"RESG_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                ruta_completa = os.path.join(ruta_resg, safe_filename)
                
                with open(ruta_completa, 'wb') as f:
                    f.write(pdf_bytes)
                
                doc = Documento(
                    empresa_id=notif.empresa_id,
                    gestoria_id=notif.gestoria_id,
                    nombre_archivo=os.path.basename(ruta_completa),
                    ruta_archivo=ruta_completa,
                    categoria=DocumentCategories.POR_PROCESAR,
                    procesado=True,
                    datos_extraidos={
                        'origen': 'DEHU_SALTRA',
                        'tipo': 'Resguardo',
                        'subcategoria': 'Resguardos',
                        'identifier': notif.identifier,
                        'sent_reference': notif.sent_reference
                    }
                )
                db.session.add(doc)
                archivos_guardados.append('resguardo')
            
            # Marcar como descargado
            notif.pdf_descargado = True
            notif.procesado = True
            db.session.commit()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "message": f"Descargados: {', '.join(archivos_guardados)}",
                "archivos": archivos_guardados
            })
            
        except Exception as e:
            logger.error(f"Error descargando PDF: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/saltra/notificaciones/<int:id>/ver-pdf', methods=['GET'])
    @login_required
    def ver_pdf_notif_saltra(id):
        """Sirve el PDF descargado de una notificación para visualización"""
        from models_saltra import NotificacionSaltra
        
        try:
            # Obtener notificación
            notif = db.session.get(NotificacionSaltra, id)
            if not notif:
                return jsonify({NotificationTypes.ERROR: "Notificación no encontrada"}), 404
            
            # Verificar que esté descargado
            if not notif.pdf_descargado:
                return jsonify({NotificationTypes.ERROR: "PDF no descargado aún"}), 404
            
            # Buscar el documento principal en BD usando LIKE en nombre de archivo
            doc = Documento.query.filter(
                Documento.empresa_id == notif.empresa_id,
                Documento.categoria == DocumentCategories.POR_PROCESAR,
                Documento.nombre_archivo.like(f'DOC_{notif.identifier}%')
            ).first()
            
            if not doc:
                # Si no hay documento principal, buscar resguardo
                doc = Documento.query.filter(
                    Documento.empresa_id == notif.empresa_id,
                    Documento.categoria == DocumentCategories.POR_PROCESAR,
                    Documento.nombre_archivo.like(f'RESG_{notif.identifier}%')
                ).first()
            
            if not doc:
                # Último intento: buscar cualquier documento reciente de esta empresa
                doc = Documento.query.filter(
                    Documento.empresa_id == notif.empresa_id,
                    Documento.categoria == DocumentCategories.POR_PROCESAR
                ).order_by(Documento.fecha_creacion.desc()).first()
                
                if not doc:
                    return jsonify({NotificationTypes.ERROR: "Documento no encontrado en BD"}), 404
            
            # Verificar que el archivo existe
            if not os.path.exists(doc.ruta_archivo):
                return jsonify({NotificationTypes.ERROR: f"Archivo físico no encontrado: {doc.ruta_archivo}"}), 404
            
            # Servir el PDF
            return send_file(
                doc.ruta_archivo,
                mimetype='application/pdf',
                as_attachment=False,  # Para visualizar en navegador
                download_name=doc.nombre_archivo
            )
            
        except Exception as e:
            logger.error(f"Error sirviendo PDF: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/saltra/notificaciones/<int:id>/aceptar', methods=['POST'])
    @login_required
    def aceptar_notificacion_saltra(id):
        """Acepta una notificación pendiente"""
        from models_saltra import NotificacionSaltra
        from services.saltra_service import SaltraService
        
        n = db.session.get(NotificacionSaltra, id)
        if not n:
            return jsonify({NotificationTypes.ERROR: "No encontrada"}), 404
        
        if n.state != 'PENDIENTE':
            return jsonify({NotificationTypes.ERROR: "La notificación no está pendiente"}), 400
        
        # Obtener credenciales SALTRA
        credentials = get_saltra_credentials()
        if not credentials:
            return jsonify({NotificationTypes.ERROR: "SALTRA no configurado"}), 400
        
        saltra = SaltraService(
            api_key=credentials['email'],
            api_secret=credentials['password'],
            cert_secret=credentials['cert_secret']
        )
        result = saltra.accept_notification(n.sent_reference)
        
        if result.get(NotificationTypes.SUCCESS):
            # Actualizar estado en BD
            n.state = 'ACEPTADA'
            db.session.commit()
            return jsonify({NotificationTypes.SUCCESS: True, "message": "Notificación aceptada"})
        else:
            return jsonify({NotificationTypes.ERROR: result.get('message', 'Error al aceptar')}), 500

    @app.route('/api/saltra/notificaciones/<int:id>/asignar-empresa', methods=['POST'])
    @login_required
    def asignar_empresa_saltra(id):
        """Asigna empresa a notificación sin empresa"""
        from models_saltra import NotificacionSaltra
        n = db.session.get(NotificacionSaltra, id)
        if not n:
            return jsonify({NotificationTypes.ERROR: "No encontrada"}), 404
        
        empresa_id = request.json.get('empresa_id')
        if not empresa_id:
            return jsonify({NotificationTypes.ERROR: "empresa_id requerido"}), 400
        
        emp = db.session.get(Empresa, empresa_id)
        if not emp:
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        
        n.empresa_id = empresa_id
        
        # Crear alias si se solicita
        if request.json.get('crear_alias') and n.nif_titular:
            nif_clean = re.sub(r'[\s\.-]', '', n.nif_titular.strip().upper()).lstrip("ES").lstrip("0")[:9]
            if nif_clean and not AliasNIF.query.filter_by(nif=nif_clean).first():
                db.session.add(AliasNIF(nif=nif_clean, empresa_id=empresa_id))
        
        db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, "notificacion": n.to_dict()})
    
    @app.route('/api/saltra/stats', methods=['GET'])
    @login_required
    def saltra_stats():
        """Estadísticas de notificaciones Saltra"""
        from models_saltra import NotificacionSaltra, SaltraSyncLog
        
        gestoria_id = get_current_gestoria_id()
        
        total = NotificacionSaltra.query.filter_by(gestoria_id=gestoria_id).count()
        con_empresa = NotificacionSaltra.query.filter(
            NotificacionSaltra.empresa_id != None,
            NotificacionSaltra.gestoria_id == gestoria_id
        ).count()
        sin_empresa = total - con_empresa
        pdfs_descargados = NotificacionSaltra.query.filter(
            NotificacionSaltra.pdf_descargado == True,
            NotificacionSaltra.gestoria_id == gestoria_id
        ).count()
        
        # Notificaciones descargables (ACEPTADAS y PENDIENTES con empresa y sin descargar)
        descargables = NotificacionSaltra.query.filter(
            NotificacionSaltra.pdf_descargado == False,
            NotificacionSaltra.empresa_id != None,
            NotificacionSaltra.state.in_(['ACEPTADA', 'PENDIENTE']),
            NotificacionSaltra.gestoria_id == gestoria_id
        ).count()
        
        ultimo_sync = SaltraSyncLog.query.filter_by(gestoria_id=gestoria_id).order_by(SaltraSyncLog.fecha.desc()).first()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "stats": {
                "total": total,
                "con_empresa": con_empresa,
                "sin_empresa": sin_empresa,
                "pdfs_descargados": pdfs_descargados,
                "descargables": descargables,  # Nuevas: solo ACEPTADAS
                "ultimo_sync": ultimo_sync.to_dict() if ultimo_sync else None
            }
        })
    
    @app.route('/api/saltra/dehu-stats', methods=['GET'])
    @login_required
    def saltra_dehu_stats():
        """Estadísticas en tiempo real desde la API de DEHU"""
        from services.saltra_service import SaltraService
        
        try:
            # Obtener credenciales SALTRA
            credentials = get_saltra_credentials()
            if not credentials:
                return jsonify({NotificationTypes.SUCCESS: False, "message": "SALTRA no configurado"}), 400
            
            saltra = SaltraService(
                api_key=credentials['email'],
                api_secret=credentials['password'],
                cert_secret=credentials['cert_secret']
            )
            result = saltra.get_dehu_stats()
            
            if result.get(NotificationTypes.SUCCESS):
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/saltra/alertas-vencimiento', methods=['GET'])
    @login_required
    def saltra_alertas_vencimiento():
        """
        Retorna notificaciones próximas a vencer
        - Críticas: ≤3 días
        - Advertencias: ≤7 días
        """
        from models_saltra import NotificacionSaltra
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        try:
            gestoria_id = get_current_gestoria_id()
            if not gestoria_id:
                return jsonify({NotificationTypes.ERROR: "No se pudo determinar la gestoría"}), 400
            
            hoy = datetime.now().date()
            fecha_critica = hoy + timedelta(days=3)
            fecha_advertencia = hoy + timedelta(days=7)
            
            # Notificaciones críticas (vencen en 3 días o menos)
            criticas = NotificacionSaltra.query.filter(
                NotificacionSaltra.gestoria_id == gestoria_id,
                NotificacionSaltra.state == 'PENDIENTE',
                func.date(NotificacionSaltra.expiration_date) <= fecha_critica,
                func.date(NotificacionSaltra.expiration_date) >= hoy
            ).order_by(NotificacionSaltra.expiration_date.asc()).all()
            
            # Advertencias (vencen en 4-7 días)
            advertencias = NotificacionSaltra.query.filter(
                NotificacionSaltra.gestoria_id == gestoria_id,
                NotificacionSaltra.state == 'PENDIENTE',
                func.date(NotificacionSaltra.expiration_date) > fecha_critica,
                func.date(NotificacionSaltra.expiration_date) <= fecha_advertencia
            ).order_by(NotificacionSaltra.expiration_date.asc()).all()
            
            # Total pendientes
            total_pendientes = NotificacionSaltra.query.filter(
                NotificacionSaltra.gestoria_id == gestoria_id,
                NotificacionSaltra.state == 'PENDIENTE'
            ).count()
            
            # Calcular días restantes para cada notificación
            def calcular_dias_restantes(notif):
                dias = (notif.expiration_date.date() - hoy).days
                return max(0, dias)  # No negativos
            
            return jsonify({
                'criticas': [
                    {
                        **n.to_dict_simple(),
                        'dias_restantes': calcular_dias_restantes(n)
                    } for n in criticas
                ],
                'advertencias': [
                    {
                        **n.to_dict_simple(),
                        'dias_restantes': calcular_dias_restantes(n)
                    } for n in advertencias
                ],
                'criticas_count': len(criticas),
                'advertencias_count': len(advertencias),
                'total_pendientes': total_pendientes
            })
            
        except Exception as e:
            app.logger.error(f"Error en alertas de vencimiento: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/saltra/notificaciones-calendario', methods=['GET'])
    @login_required
    def saltra_notificaciones_calendario():
        """
        Retorna TODAS las notificaciones PENDIENTES para mostrar en el calendario
        """
        from models_saltra import NotificacionSaltra
        
        try:
            gestoria_id = get_current_gestoria_id()
            if not gestoria_id:
                return jsonify({NotificationTypes.ERROR: "No se pudo determinar la gestoría"}), 400
            
            # Obtener TODAS las notificaciones pendientes
            notificaciones = NotificacionSaltra.query.filter(
                NotificacionSaltra.gestoria_id == gestoria_id,
                NotificacionSaltra.state == 'PENDIENTE'
            ).order_by(NotificacionSaltra.expiration_date.asc()).all()
            
            return jsonify({
                'notificaciones': [n.to_dict_simple() for n in notificaciones],
                'total': len(notificaciones)
            })
            
        except Exception as e:
            app.logger.error(f"Error obteniendo notificaciones para calendario: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/dashboard/estadisticas', methods=['GET'])
    @login_required
    def get_dashboard_stats():
        """
        Endpoint para estadísticas del dashboard analítico.
        Retorna KPIs y datos para gráficos.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func, extract, case
        
        # Fecha actual y mes actual
        hoy = datetime.now()
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # MULTI-TENANT: Obtener gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # 1. Documentos este mes
        docs_mes = Documento.query.filter(
            Documento.fecha_creacion >= inicio_mes,
            Documento.gestoria_id == gestoria_id
        ).count()
        
        # 2. Pendientes de procesar con IA
        pendientes_ia = Documento.query.filter_by(
            procesado=False,
            categoria=DocumentCategories.POR_PROCESAR,
            gestoria_id=gestoria_id
        ).count()
        
        # 3. Tareas vencidas (fecha_plazo pasada y no completadas)
        tareas_vencidas = Documento.query.filter(
            Documento.fecha_plazo < hoy,
            Documento.fecha_plazo.isnot(None),
            Documento.guardado == False,
            Documento.email_enviado == False,
            Documento.gestoria_id == gestoria_id
        ).count()
        
        # 4. Tiempo promedio de procesamiento (simplificado)
        # Calcular promedio de días entre creación y procesamiento
        docs_procesados = db.session.query(
            func.avg(
                func.extract('epoch', Documento.fecha_procesado - Documento.fecha_creacion) / 3600
            ).label('promedio_horas')
        ).filter(
            Documento.procesado == True,
            Documento.fecha_procesado.isnot(None),
            Documento.fecha_creacion >= inicio_mes,
            Documento.gestoria_id == gestoria_id
        ).scalar()
        
        tiempo_promedio = round(docs_procesados or 0, 1)
        
        # 5. Documentos por departamento
        por_departamento = []
        departamentos = Departamento.query.all()
        
        for depto in departamentos:
            count = Documento.query.filter(
                Documento.estado_tarea.like(f'%{depto.nombre}%'),
                Documento.gestoria_id == gestoria_id
            ).count()
            
            if count > 0:  # Solo incluir departamentos con documentos
                por_departamento.append({
                    'name': depto.nombre,
                    'total': count
                })
        
        # 6. Distribución por estado/categoría
        categorias = [DocumentCategories.POR_PROCESAR, DocumentCategories.NOTIFICACIONES, 'Embargos', 'Nominas', 'Finiquitos']
        por_estado = []
        
        for cat in categorias:
            count = Documento.query.filter_by(categoria=cat, gestoria_id=gestoria_id).count()
            if count > 0:
                por_estado.append({
                    'name': cat,
                    'value': count
                })
        
        # Documentos archivados
        archivados = Documento.query.filter_by(guardado=True, gestoria_id=gestoria_id).count()
        if archivados > 0:
            por_estado.append({
                'name': 'Archivados',
                'value': archivados
            })
        
        # 7. Tendencia últimos 7 días
        tendencia = []
        for i in range(7):
            fecha = hoy - timedelta(days=6-i)
            fecha_inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = fecha_inicio + timedelta(days=1)
            
            count = Documento.query.filter(
                Documento.fecha_creacion >= fecha_inicio,
                Documento.fecha_creacion < fecha_fin,
                Documento.gestoria_id == gestoria_id
            ).count()
            
            tendencia.append({
                'fecha': fecha.strftime('%d/%m'),
                'documentos': count
            })
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "stats": {
                "documentos_mes": docs_mes,
                "pendientes_ia": pendientes_ia,
                "tareas_vencidas": tareas_vencidas,
                "tiempo_promedio": tiempo_promedio,
                "por_departamento": por_departamento,
                "por_estado": por_estado,
                "tendencia_7_dias": tendencia
            }
        })

    @app.route('/api/buscar/avanzada', methods=['POST'])
    @login_required
    def busqueda_avanzada():
        """Búsqueda avanzada con filtros múltiples."""
        from sqlalchemy import or_
        from datetime import datetime
        
        data = request.json
        query = data.get('query', '').strip()
        filtros = data.get('filtros', {})
        
        es_jefatura = current_user.departamento.nombre == 'Jefatura'
        
        resultados = {'empresas': [], 'documentos': [], 'total_empresas': 0, 'total_documentos': 0}
        
        # Buscar empresas
        if query:
            empresas_q = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
                or_(Empresa.nombre.ilike(f'%{query}%'), Empresa.nif.ilike(f'%{query}%'), Empresa.email.ilike(f'%{query}%'))
            )
            empresas = empresas_q.limit(10).all()
            resultados['empresas'] = [{
                'id': e.id,
                'nombre': e.nombre,
                'nif': e.nif,
                'email': e.email,
                'link': f'/empresa/{e.id}/Por Procesar'
            } for e in empresas]
            resultados['total_empresas'] = empresas_q.count()
        
        # Buscar documentos
        docs_q = Documento.query
        if query:
            docs_q = docs_q.filter(
        or_(
            Documento.nombre_archivo.ilike(f'%{query}%'),
            Documento.datos_extraidos.cast(db.String).ilike(f'%{query}%')
        )
    )
        if filtros.get('categoria'):
            docs_q = docs_q.filter(Documento.categoria == filtros['categoria'])
        if filtros.get('departamento'):
            docs_q = docs_q.filter(Documento.estado_tarea.ilike(f'%{filtros["departamento"]}%'))
        
        # Aplicar permisos
        if not es_jefatura:
            docs_q = docs_q.filter(
                or_(
                    Documento.estado_tarea == None,
                    Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'),
                    Documento.asignado_a_id == current_user.id
                )
            )
        
        docs = docs_q.order_by(Documento.fecha_creacion.desc()).limit(20).all()
        resultados['documentos'] = [{
            'id': d.id,
            'nombre_archivo': d.nombre_archivo,
            'categoria': d.categoria,
            'empresa': d.empresa.nombre if d.empresa else 'Sin empresa',
            'empresa_id': d.empresa_id,
            'fecha_creacion': d.fecha_creacion.isoformat(),
            'link': f'/empresa/{d.empresa_id}/{d.categoria}'
        } for d in docs]
        resultados['total_documentos'] = docs_q.count()
        
        return jsonify({NotificationTypes.SUCCESS: True, "resultados": resultados})
    
# ==========================================
# PAGINACIÓN - Nuevos endpoints
# ==========================================

def register_pagination_routes(app):
    @app.route('/api/empresas/<int:empresa_id>/documentos/paged', methods=['GET'])
    @login_required
    def get_documentos_paged(empresa_id):
        """Endpoint paginado para documentos de una empresa"""
        # MULTI-TENANT: Verificar que la empresa pertenece a la gestoría actual
        empresa = Empresa.query.get(empresa_id)
        if not empresa or empresa.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        categoria = request.args.get('categoria')
        
        query = Documento.query.filter_by(empresa_id=empresa_id)
        
        if categoria:
            query = query.filter_by(categoria=categoria)
        
        # Total de documentos
        total = query.count()
        
        # Documentos paginados
        documentos = query.order_by(Documento.fecha_creacion.desc())\
            .offset((page - 1) * limit)\
            .limit(limit)\
            .all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'documentos': [d.to_dict() for d in documentos],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit,
                'has_next': page * limit < total,
                'has_prev': page > 1
            }
        })
    
# ==========================================
# CÓDIGO PARA AGREGAR A app.py
# ==========================================

def register_seguros_sociales_routes(app):
    @app.route('/api/procesar-seguros-sociales', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_CREADO,
        entidad_tipo='seguros_sociales'
    )
    def api_procesar_seguros_sociales():
        """
        Procesa archivos consolidados de Seguros Sociales (RLC + RNT) de forma asíncrona
        """
        try:
            # Validar archivos
            if 'rlc' not in request.files or 'rnt' not in request.files:
                return jsonify({NotificationTypes.ERROR: "Debes subir ambos archivos: RLC y RNT"}), 400
            
            rlc_file = request.files['rlc']
            rnt_file = request.files['rnt']
            
            if not rlc_file.filename.lower().endswith('.pdf') or not rnt_file.filename.lower().endswith('.pdf'):
                return jsonify({NotificationTypes.ERROR: "Los archivos deben ser PDF"}), 400
            
            # Crear directorio de procesamiento dentro del proyecto si no existe
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            app_temp_dir = os.path.join(backend_dir, 'temp')
            os.makedirs(app_temp_dir, exist_ok=True)
            
            # Guardar archivos en subdirectorio temporal único
            import tempfile
            temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
            
            rlc_path = os.path.join(temp_dir, secure_filename(rlc_file.filename))
            rnt_path = os.path.join(temp_dir, secure_filename(rnt_file.filename))
            
            rlc_file.save(rlc_path)
            rnt_file.save(rnt_path)
            
            # Obtener periodo personalizado (opcional)
            periodo_custom = request.form.get('periodo')
            
            # Verificar modo empresa única
            empresa_unica_mode = request.form.get('empresa_unica') == 'true'

            if empresa_unica_mode:
                print("🚀 MODO EMPRESA ÚNICA ACTIVADO - SEGUROS SOCIALES")
                from procesar_seguros_sociales import extraer_info_empresa_rlc, extraer_info_empresa_rnt, get_or_create_inbox_empresa
                from models import Empresa, Documento, db
                from utils import limpiar_nombre_carpeta
                
                from datetime import datetime
                
                from difflib import SequenceMatcher
                from pypdf import PdfReader

                storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']

                def _extraer_ss_texto_lineal(texto):
                    """
                    Extractor para texto linearizado por PyPDF de PDFs de Seguridad Social.

                    El problema: PyPDF mezcla las columnas del PDF oficial de la TGSS y produce:
                      "Código de Cuenta de Cotización: 00088900 GRUP KARMAYOG 10 S.L.
                       02/2026 - 02/2026 0111 08236209776 9 0B24832701 ...
                       Razón Social: Período de Liquidación: ..."

                    Es decir: los LABELS quedan al final sin valores, y los VALORES quedan
                    al principio sin labels (o con el label incorrecto).
                    Estrategia: buscar por FORMA de los datos, no por su label precedente.
                    """
                    info = {'razon_social': None, 'ccc': None, 'nif': None, 'periodo': None}
                    t = texto.replace('\n', ' ')

                    # ── Razón Social ─────────────────────────────────────────────
                    # El nombre aparece como valor suelto con forma jurídica (S.L., S.A., etc.)
                    # Buscar cualquier nombre con forma jurídica en el texto completo.
                    m = re.search(
                        r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s\.\,\-\&]{1,55?}'
                        r'(?:S\.L\.U\.|S\.A\.U\.|S\.L\.P\.|S\.COOP\.|S\.L\.|S\.A\.|'
                        r'S\.C\.|C\.B\.|SLU|SAU|SL|SA)\.?)',
                        t, re.IGNORECASE
                    )
                    if m:
                        info['razon_social'] = m.group(1).strip().rstrip('.,')

                    # ── CCC (Código Cuenta Cotización) ────────────────────────────
                    # Formato real: "0111 08236209776" = 4 dígitos + espacio + 11 dígitos
                    # El número de autorización (00088900) tiene solo 8 dígitos → no coincide.
                    # Primero intentar tras el label (cuando sí aparece junto):
                    m = re.search(
                        r'C[oó]digo\s+(?:de\s+)?[Cc]uenta\s+(?:de\s+)?[Cc]otizaci[oó]n\s*:?\s+'
                        r'(\d{4}\s+\d{11})',
                        t, re.IGNORECASE
                    )
                    if m:
                        info['ccc'] = m.group(1).replace(' ', '')
                    else:
                        # Fallback: buscar el patrón numérico puro 4+11 dígitos en cualquier lugar
                        m = re.search(r'\b(\d{4})\s+(\d{11})\b', t)
                        if m:
                            info['ccc'] = m.group(1) + m.group(2)

                    # ── NIF (Código de Empresario) ────────────────────────────────
                    # Aparece como "9 0B24832701" → prefijo numérico + 0 + NIF
                    # NIF formato: letra + 8 dígitos (ej: B24832701)
                    # Primero intentar tras el label:
                    m = re.search(
                        r'C[oó]digo\s+de\s+[Ee]mpresario\s*:?\s+\d+\s+0?([A-Z]\d{8}[A-Z0-9]?)',
                        t, re.IGNORECASE
                    )
                    if m:
                        info['nif'] = m.group(1).strip()
                    else:
                        # Fallback: buscar patrón "dígito(s) espacio 0LetraDígitos"
                        m = re.search(r'\b\d+\s+0([A-Z]\d{7,8})\b', t)
                        if m:
                            info['nif'] = m.group(1).strip()

                    # ── Período ───────────────────────────────────────────────────
                    # "02/2026 - 02/2026" o "02/2026-02/2026"
                    m = re.search(r'\b(\d{2})[/\-](\d{4})\b', t)
                    if m:
                        info['periodo'] = f"{m.group(2)}{m.group(1)}"

                    return info

                try:
                    # Función auxiliar para escanear PDF multipágina
                    def escanear_pdf_en_busca_de_info(pdf_path, extractor_func, max_pages=50):
                        """
                        Escanea el PDF página a página con pdfplumber (principal) y PyPDF (rescate).
                        Devuelve (info_dict, texto_completo_todas_paginas).
                        El texto_completo permite al fallback buscar S.L./S.A./CCC aunque
                        el nombre esté en una página diferente a la de los datos fiscales.
                        """
                        all_texts = []   # texto de TODAS las páginas para fallback

                        # ── 1. PDFPlumber ──────────────────────────────────────────────
                        plumber_ok = False
                        try:
                            with pdfplumber.open(pdf_path) as pdf:
                                plumber_ok = True
                                for i, page in enumerate(pdf.pages[:max_pages]):
                                    page_text = page.extract_text() or ""
                                    all_texts.append(page_text)
                                    info = extractor_func(page)
                                    if info.get('nif') or info.get('razon_social'):
                                        return info, ' '.join(all_texts)
                        except Exception as e:
                            print(f"⚠️ pdfplumber falló en {os.path.basename(pdf_path)}: {e}")

                        # ── 2. PyPDF (siempre como segundo intento) ────────────────────
                        pypdf_texts = []
                        try:
                            reader = PdfReader(pdf_path)
                            for i, page in enumerate(reader.pages[:max_pages]):
                                text = page.extract_text() or ""
                                pypdf_texts.append(text)
                                info = extractor_func(text)
                                if info.get('nif') or info.get('razon_social'):
                                    print(f"✅ Info rescatada con PyPDF (pág {i}) para {os.path.basename(pdf_path)}")
                                    combined = ' '.join(pypdf_texts + all_texts)
                                    return info, combined
                        except Exception as e:
                            print(f"⚠️ PyPDF también falló en {os.path.basename(pdf_path)}: {e}")

                        # ── Último recurso: extractor directo sobre texto completo ──
                        # Útil cuando PyPDF lineariza el PDF y pone labels y valores
                        # en orden separado (típico en el formato de la Seguridad Social).
                        full_text = ' '.join(all_texts + pypdf_texts)
                        info_directo = _extraer_ss_texto_lineal(full_text)
                        if info_directo.get('nif') or info_directo.get('razon_social') or info_directo.get('ccc'):
                            return info_directo, full_text.replace('\n', ' ')

                        return {}, full_text.replace('\n', ' ')

                    # Procesar RLC (Escanear múltiples páginas)
                    info_rlc, raw_text_rlc = escanear_pdf_en_busca_de_info(rlc_path, extraer_info_empresa_rlc)
                    
                    # Procesar RNT (Escanear múltiples páginas)
                    info_rnt, raw_text_rnt = escanear_pdf_en_busca_de_info(rnt_path, extraer_info_empresa_rnt)
                    
                    # Identificar empresa (priorizando RLC)
                    gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1
                    empresa = None

                    nif = info_rlc.get('nif') or info_rnt.get('nif')
                    rs  = info_rlc.get('razon_social') or info_rnt.get('razon_social')
                    ccc = info_rlc.get('ccc') or info_rnt.get('ccc')

                    # Sanear rs: si parece una etiqueta del PDF (palabras clave del documento),
                    # ── Siempre correr el extractor directo sobre el texto completo ──
                    # Esto complementa (y en caso de conflicto, corrige) la extracción
                    # del extractor estructurado que falla con texto linearizado por PyPDF.
                    raw_combined = ' '.join(filter(None, [raw_text_rlc, raw_text_rnt]))
                    info_lineal = _extraer_ss_texto_lineal(raw_combined)

                    # Dar prioridad al extractor directo si el NIF tiene forma válida
                    _NIF_VALIDO = re.compile(r'^[A-Z]\d{7,8}[A-Z0-9]?$')
                    if not nif and info_lineal.get('nif') and _NIF_VALIDO.match(info_lineal['nif']):
                        nif = info_lineal['nif']
                    if not ccc and info_lineal.get('ccc'):
                        ccc = info_lineal['ccc']
                    # Período: usar el del extractor directo si los estructurados no lo encontraron
                    if not info_rlc.get('periodo') and not info_rnt.get('periodo') and info_lineal.get('periodo'):
                        info_rlc['periodo'] = info_lineal['periodo']

                    # Sanear rs: descartar si parece etiqueta/sección del PDF
                    # Un nombre de empresa REAL debe contener una forma jurídica (S.L., S.A., etc.)
                    _FORMA_JURIDICA_CHECK = re.compile(
                        r'S\.L\.|S\.A\.|S\.L\.U\.|S\.A\.U\.|S\.C\.|C\.B\.|S\.COOP\.|SLU|SAU',
                        re.IGNORECASE
                    )
                    if rs and not _FORMA_JURIDICA_CHECK.search(rs):
                        print(f"⚠️ RS descartado (sin forma jurídica): '{rs[:60]}'")
                        rs = None

                    # Usar razón social del extractor directo si el estructurado falló
                    if not rs and info_lineal.get('razon_social'):
                        rs = info_lineal['razon_social']

                    # Construir lista de candidatos desde el texto RAW para fuzzy match
                    _FORMA_JURIDICA_RE = re.compile(
                        r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\s\-\.,&]{2,60?}'
                        r'(?:S\.L\.U?\.?|S\.A\.U?\.?|S\.L\.P\.?|S\.C\.?|C\.B\.?|'
                        r'S\.COOP\.?|S\.L\b|S\.A\b|SLU|SAU|SL|SA))',
                        re.IGNORECASE
                    )
                    rs_candidatos = []
                    if rs:
                        rs_candidatos.append(rs)
                    for m in _FORMA_JURIDICA_RE.finditer(raw_combined):
                        candidato = m.group(1).strip().rstrip('.,')
                        if candidato and candidato not in rs_candidatos:
                            rs_candidatos.append(candidato)

                    metodo_deteccion = "No detectado"
                    best_r = 0
                    best_empresa_nombre = "Ninguno"

                    # 1. Búsqueda por NIF
                    if nif:
                        nif_norm = nif.lstrip('0').upper()
                        empresa = Empresa.query.filter(
                            (Empresa.nif == nif) | (Empresa.nif == nif_norm),
                            Empresa.gestoria_id == gestoria_id
                        ).first()
                        if empresa:
                            metodo_deteccion = f"NIF ({nif})"

                    # 2. Búsqueda por CCC (cuenta_cotizacion)
                    if not empresa and ccc:
                        ccc_clean = re.sub(r'\s+', '', ccc)
                        empresa = Empresa.query.filter(
                            Empresa.cuenta_cotizacion.ilike(f'%{ccc_clean}%'),
                            Empresa.gestoria_id == gestoria_id
                        ).first()
                        if empresa:
                            metodo_deteccion = f"CCC ({ccc_clean})"

                    # 3. Búsqueda por Nombre Fuzzy contra todos los candidatos extraídos
                    if not empresa and rs_candidatos:
                        empresas_bd = Empresa.query.filter_by(gestoria_id=gestoria_id).all()
                        best_empresa = None

                        for candidato in rs_candidatos:
                            candidato_up = candidato.upper()
                            for e in empresas_bd:
                                ratio = SequenceMatcher(None, candidato_up, e.nombre.upper()).ratio()
                                if ratio > best_r:
                                    best_r = ratio
                                    best_empresa = e
                                    best_empresa_nombre = e.nombre
                                    rs = candidato  # guardar cuál candidato ganó

                        if best_r >= 0.75:
                            empresa = best_empresa
                            metodo_deteccion = f"Nombre Fuzzy ({int(best_r*100)}%): {rs}"

                    if not empresa:
                        print(f"⚠️ Empresa no encontrada para Seguros Sociales, enviando a Inbox.")
                        empresa = get_or_create_inbox_empresa(db, Empresa, gestoria_id)
                        debug_txt = raw_text_rlc or raw_text_rnt or "Vacio"
                        metodo_deteccion = f"FALLO. RAW='{debug_txt}'. Extr: N={nif or 'N/A'} RS='{rs or 'N/A'}'"
                         
                    # Mover archivos
                    empresa_dir = os.path.join(storage_dir, limpiar_nombre_carpeta(empresa.nombre), "Seguros Sociales")
                    os.makedirs(empresa_dir, exist_ok=True)
                    
                    # Evitar doble prefijo: solo añadir RLC_/RNT_ si el nombre no lo tiene ya
                    rlc_safe_name = secure_filename(rlc_file.filename)
                    rnt_safe_name = secure_filename(rnt_file.filename)
                    rlc_final_name = rlc_safe_name if rlc_safe_name.upper().startswith('RLC_') else f"RLC_{rlc_safe_name}"
                    rnt_final_name = rnt_safe_name if rnt_safe_name.upper().startswith('RNT_') else f"RNT_{rnt_safe_name}"
                    final_rlc = os.path.join(empresa_dir, rlc_final_name)
                    final_rnt = os.path.join(empresa_dir, rnt_final_name)
                    
                    shutil.move(rlc_path, final_rlc)
                    shutil.move(rnt_path, final_rnt)
                    
                    # Registrar BD
                    periodo_doc = periodo_custom or info_rlc.get('periodo') or info_rnt.get('periodo')
                    
                    doc_rlc = Documento(
                            empresa_id=empresa.id, gestoria_id=gestoria_id,
                            nombre_archivo=os.path.basename(final_rlc), ruta_archivo=final_rlc,
                            categoria='Seguros Sociales', fecha_creacion=datetime.utcnow(),
                            guardado=True, procesado=True, periodo=periodo_doc
                    )
                    
                    doc_rnt = Documento(
                            empresa_id=empresa.id, gestoria_id=gestoria_id,
                            nombre_archivo=os.path.basename(final_rnt), ruta_archivo=final_rnt,
                            categoria='Seguros Sociales', fecha_creacion=datetime.utcnow(),
                            guardado=True, procesado=True, periodo=periodo_doc
                    )
                    
                    db.session.add(doc_rlc)
                    db.session.add(doc_rnt)
                    db.session.commit()
                    
                    # Limpiar
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    return jsonify({
                        'success': True, 
                        'message': 'Seguros Sociales procesados en Modo Empresa Única', 
                        'async': False,
                        'rlc_procesados': 1,
                        'rnt_procesados': 1,
                        'empresas_asociadas': 1,
                        'empresas_no_encontradas': 0,
                        'total_documentos': 2,
                        'documentos_creados': 2,
                        'detalles': [
                            {
                                'estado': 'exito',
                                'nombre_trabajador': f'RLC: {os.path.basename(final_rlc)}',
                                'empresa': empresa.nombre,
                                'mensaje': f"Detectado por: {metodo_deteccion}"
                            },
                            {
                                'estado': 'exito',
                                'nombre_trabajador': f'RNT: {os.path.basename(final_rnt)}',
                                'empresa': empresa.nombre,
                                'mensaje': f"Detectado por: {metodo_deteccion}"
                            }
                        ]
                    })

                except Exception as e:
                    import traceback; traceback.print_exc()
                    shutil.rmtree(temp_dir, ignore_errors=True) # Ensure cleanup
                    return jsonify({
                        'success': False,
                        'message': f'Error al procesar Seguros Sociales: {str(e)}',
                        'async': False,
                        'detalles': [{
                            'estado': 'error',
                            'nombre_trabajador': 'Proceso Seguros Sociales',
                            'empresa': 'Error General',
                             'mensaje': str(e)
                        }]
                    })
            
            # Lanzar tarea asíncrona (Modo Normal)
            from tasks_seguros_sociales import procesar_seguros_async
            from models import TareaSeguros, db
            
            gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1
            
            task = procesar_seguros_async.apply_async(
                args=[rlc_path, rnt_path, current_user.id, gestoria_id],
                kwargs={'periodo_override': periodo_custom}
            )
            
            # Guardar en historial
            tarea_registro = TareaSeguros(
                task_id=task.id,
                user_id=current_user.id,
                gestoria_id=gestoria_id,
                filename_rlc=rlc_file.filename,
                filename_rnt=rnt_file.filename,
                status='PENDING'
            )
            db.session.add(tarea_registro)
            db.session.commit()
            
            print(f"⚡ Tarea asíncrona de Seguros iniciada: {task.id}")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'async': True,
                'task_id': task.id,
                'message': 'Procesando Seguros Sociales en segundo plano...'
            })
            
        except Exception as e:
            logger.error(f"Error procesando Seguros Sociales: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
        
        finally:
            # Limpieza de archivos temporales (solo si no es asíncrono, 
            # pero en este caso la tarea de Celery se encarga de su propia limpieza 
            # de los archivos que ella recibe. 
            # Sin embargo, los archivos guardados en el endpoint deben persistir 
            # hasta que Celery los lea. Por eso pusimos el delay en el worker.)
            pass

    @app.route('/api/seguros-sociales/estadisticas', methods=['GET'])
    @login_required
    def api_estadisticas_seguros_sociales():
        """
        Retorna estadísticas de Seguros Sociales guardados
        
        Response:
            {
                "total_empresas": 245,
                "con_seguros_sociales": 155,
                "sin_seguros_sociales": 90,
                "documentos_seguros_sociales": 310,
                "ultimos_periodos": ["202511", "202510", "202509"]
            }
        """
        try:
            # MULTI-TENANT: Obtener gestoria_id
            gestoria_id = get_current_gestoria_id()
            
            # Total empresas
            total_empresas = Empresa.query.filter_by(gestoria_id=gestoria_id).count()
            
            # Empresas con SS
            empresas_con_ss = db.session.query(Empresa.id).join(
                Documento, Empresa.id == Documento.empresa_id
            ).filter(
                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                Empresa.gestoria_id == gestoria_id
            ).distinct().count()
            
            # Total documentos SS
            total_docs_ss = Documento.query.filter_by(categoria=DocumentCategories.SEGUROS_SOCIALES, gestoria_id=gestoria_id).count()
            
            # Últimos periodos procesados (extraer de nombres de archivo)
            import re
            docs_ss = Documento.query.filter_by(categoria=DocumentCategories.SEGUROS_SOCIALES, gestoria_id=gestoria_id).all()
            periodos = set()
            
            for doc in docs_ss:
                match = re.search(r'(\d{6})', doc.nombre_archivo)
                if match:
                    periodos.add(match.group(1))
            
            ultimos_periodos = sorted(list(periodos), reverse=True)[:12]  # Últimos 12 meses
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "total_empresas": total_empresas,
                "con_seguros_sociales": empresas_con_ss,
                "sin_seguros_sociales": total_empresas - empresas_con_ss,
                "documentos_seguros_sociales": total_docs_ss,
                "ultimos_periodos": ultimos_periodos
            })
        
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas SS: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/comprobar-seguros-nominas', methods=['GET'])
    @login_required
    def comprobar_seguros_nominas():
        """
        Endpoint para verificar qué empresas tienen documentos de Nominas y Seguros Sociales
        para un mes/año específico
        """
        try:
            mes = request.args.get('mes', type=int)
            anio = request.args.get('anio', type=int)
            
            if not mes or not anio:
                return jsonify({NotificationTypes.ERROR: "Parámetros mes y anio requeridos"}), 400
            
            if mes < 1 or mes > 12:
                return jsonify({NotificationTypes.ERROR: "Mes debe estar entre 1 y 12"}), 400
            
            # Obtener TODAS las empresas de la gestoria
            empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).order_by(Empresa.nombre).all()
            
            resultado = []
            
            # Formatear periodo esperado (YYYYMM)
            periodo_buscado = f"{anio}{mes:02d}"
            
            for empresa in empresas:
                # Contar documentos de Nominas en el mes/año
                # Priorizar campo 'periodo', fallback a fecha_creacion para docs antiguos
                nominas_count = Documento.query.filter(
                    Documento.empresa_id == empresa.id,
                    Documento.categoria == DocumentCategories.NOMINAS,
                    Documento.gestoria_id == empresa.gestoria_id,
                    db.or_(
                        Documento.periodo == periodo_buscado,
                        db.and_(
                            Documento.periodo.is_(None),
                            db.func.extract('month', Documento.fecha_creacion) == mes,
                            db.func.extract('year', Documento.fecha_creacion) == anio
                        )
                    )
                ).count()
                
                # Contar documentos de Seguros Sociales en el mes/año
                seguros_count = Documento.query.filter(
                    Documento.empresa_id == empresa.id,
                    Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                    Documento.gestoria_id == empresa.gestoria_id,
                    db.or_(
                        Documento.periodo == periodo_buscado,
                        db.and_(
                            Documento.periodo.is_(None),
                            db.func.extract('month', Documento.fecha_creacion) == mes,
                            db.func.extract('year', Documento.fecha_creacion) == anio
                        )
                    )
                ).count()
                
                from email_sender import obtener_email_notificaciones
                email_final = obtener_email_notificaciones(empresa.id) or empresa.email

                resultado.append({
                    "id": empresa.id,
                    "nombre": empresa.nombre,
                    "email": email_final,  # ✅ Soporte para Agrupaciones
                    "nominas_count": nominas_count,
                    "seguros_count": seguros_count
                })
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "mes": mes,
                "anio": anio,
                "empresas": resultado
            })
        
        except Exception as e:
            logger.error(f"Error en comprobar-seguros-nominas: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/comprobar-seguros-nominas/grupos', methods=['GET'])
    @login_required
    def comprobar_seguros_nominas_grupos():
        """
        Endpoint para verificar el estado de documentos por Grupos de Empresas
        """
        try:
            mes = request.args.get('mes', type=int)
            anio = request.args.get('anio', type=int)
            
            if not mes or not anio:
                return jsonify({NotificationTypes.ERROR: "Parámetros mes y anio requeridos"}), 400
            
            periodo_buscado = f"{anio}{mes:02d}"
            gestoria_id = get_current_gestoria_id()
            
            grupos = GrupoEmpresa.query.filter_by(gestoria_id=gestoria_id).order_by(GrupoEmpresa.nombre).all()
            
            resultado = []
            for grupo in grupos:
                empresas = grupo.empresas_rel
                count_nominas = 0
                count_seguros = 0
                detalle = []
                
                for empresa in empresas:
                    n_count = Documento.query.filter(
                        Documento.empresa_id == empresa.id,
                        Documento.categoria == DocumentCategories.NOMINAS,
                        Documento.gestoria_id == gestoria_id,
                        db.or_(
                            Documento.periodo == periodo_buscado,
                            db.and_(
                                Documento.periodo.is_(None),
                                db.func.extract('month', Documento.fecha_creacion) == mes,
                                db.func.extract('year', Documento.fecha_creacion) == anio
                            )
                        )
                    ).count()
                    
                    s_count = Documento.query.filter(
                        Documento.empresa_id == empresa.id,
                        Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                        Documento.gestoria_id == gestoria_id,
                        db.or_(
                            Documento.periodo == periodo_buscado,
                            db.and_(
                                Documento.periodo.is_(None),
                                db.func.extract('month', Documento.fecha_creacion) == mes,
                                db.func.extract('year', Documento.fecha_creacion) == anio
                            )
                        )
                    ).count()
                    
                    if n_count > 0: count_nominas += 1
                    if s_count > 0: count_seguros += 1
                    
                    detalle.append({
                        "id": empresa.id,
                        "nombre": empresa.nombre,
                        "nominas_count": n_count,
                        "seguros_count": s_count
                    })
                
                resultado.append({
                    "id": grupo.id,
                    "nombre": grupo.nombre,
                    "email": grupo.email_notificaciones,
                    "total_empresas": len(empresas),
                    "empresas_con_nominas": count_nominas,
                    "empresas_con_seguros": count_seguros,
                    "detalle": detalle
                })
                
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "grupos": resultado
            })
        except Exception as e:
            logger.error(f"Error en comprobar-seguros-nominas-grupos: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/grupo/<int:grupo_id>/documentos-mes', methods=['GET'])
    @login_required
    def get_documentos_grupo_mes(grupo_id):
        """
        Obtener todos los documentos de todas las empresas de un grupo para un mes/año
        """
        try:
            mes = request.args.get('mes', type=int)
            anio = request.args.get('anio', type=int)
            
            if not mes or not anio:
                return jsonify({NotificationTypes.ERROR: "Parámetros mes y anio requeridos"}), 400
                
            grupo = GrupoEmpresa.query.get(grupo_id)
            if not grupo:
                return jsonify({NotificationTypes.ERROR: "Grupo no encontrado"}), 404
                
            gestoria_id = get_current_gestoria_id()
            periodo_buscado = f"{anio}{mes:02d}"
            
            resultado = {
                "success": True,
                "nominas": [],
                "seguros": [],
                "impuestos": []
            }
            
            for empresa in grupo.empresas_rel:
                # Nóminas
                docs_n = Documento.query.filter(
                    Documento.empresa_id == empresa.id,
                    Documento.categoria == DocumentCategories.NOMINAS,
                    Documento.gestoria_id == gestoria_id,
                    db.or_(
                        Documento.periodo == periodo_buscado,
                        db.and_(
                            Documento.periodo.is_(None),
                            db.func.extract('month', Documento.fecha_creacion) == mes,
                            db.func.extract('year', Documento.fecha_creacion) == anio
                        )
                    )
                ).all()
                
                for d in docs_n:
                    resultado["nominas"].append({
                        "id": d.id,
                        "nombre_archivo": d.nombre_archivo,
                        "empresa_nombre": empresa.nombre,
                        "empresa_id": empresa.id,
                        "fecha": d.fecha_creacion.isoformat()
                    })
                    
                # Seguros
                docs_s = Documento.query.filter(
                    Documento.empresa_id == empresa.id,
                    Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                    Documento.gestoria_id == gestoria_id,
                    db.or_(
                        Documento.periodo == periodo_buscado,
                        db.and_(
                            Documento.periodo.is_(None),
                            db.func.extract('month', Documento.fecha_creacion) == mes,
                            db.func.extract('year', Documento.fecha_creacion) == anio
                        )
                    )
                ).all()
                
                for d in docs_s:
                    resultado["seguros"].append({
                        "id": d.id,
                        "nombre_archivo": d.nombre_archivo,
                        "empresa_nombre": empresa.nombre,
                        "empresa_id": empresa.id,
                        "fecha": d.fecha_creacion.isoformat()
                    })

                # Impuestos
                docs_i = Documento.query.filter(
                    Documento.empresa_id == empresa.id,
                    Documento.categoria == DocumentCategories.IMPUESTOS,
                    Documento.gestoria_id == gestoria_id,
                    db.or_(
                        Documento.periodo == periodo_buscado,
                        db.and_(
                            Documento.periodo.is_(None),
                            db.func.extract('month', Documento.fecha_creacion) == mes,
                            db.func.extract('year', Documento.fecha_creacion) == anio
                        )
                    )
                ).all()

                for d in docs_i:
                    resultado["impuestos"].append({
                        "id": d.id,
                        "nombre_archivo": d.nombre_archivo,
                        "empresa_nombre": empresa.nombre,
                        "empresa_id": empresa.id,
                        "fecha": d.fecha_creacion.isoformat()
                    })
            
            return jsonify(resultado)
        except Exception as e:
            logger.error(f"Error obteniendo documentos de grupo: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/enviar-correos-grupo', methods=['POST'])
    @login_required
    def enviar_correos_grupo():
        """
        Envía un único correo con todos los documentos de todas las empresas de un grupo
        """
        try:
            data = request.get_json()
            grupo_id = data.get('grupo_id')
            mes = data.get('mes')
            anio = data.get('anio')
            tipos = data.get('tipos_documentos', {'nominas': True, 'seguros': True})
            
            if not grupo_id or not mes or not anio:
                return jsonify({NotificationTypes.ERROR: "Datos incompletos"}), 400
                
            grupo = GrupoEmpresa.query.get(grupo_id)
            if not grupo or not grupo.email_notificaciones:
                return jsonify({NotificationTypes.ERROR: "Grupo no encontrado o sin email configurado"}), 404
            
            gestoria_id = get_current_gestoria_id()
            periodo_buscado = f"{anio}{mes:02d}"
            adjuntos = []
            
            documento_ids = data.get('documento_ids') # Opcional: lista de IDs específicos
            
            if documento_ids:
                # Enviar solo los documentos seleccionados
                docs = Documento.query.filter(
                    Documento.id.in_(documento_ids),
                    Documento.gestoria_id == gestoria_id
                ).all()
                
                for d in docs:
                    if os.path.exists(d.ruta_archivo):
                        prefix = "Nomina" if d.categoria == DocumentCategories.NOMINAS else "Seguros"
                        emp_nombre = d.empresa.nombre if d.empresa else "Desconocida"
                        adjuntos.append({'ruta': d.ruta_archivo, 'nombre': f"{prefix}_{emp_nombre}_{d.nombre_archivo}"})
            else:
                # Lógica original: enviar todo lo del periodo
                for empresa in grupo.empresas_rel:
                    # Buscar nóminas
                    if tipos.get('nominas'):
                        docs_nominas = Documento.query.filter(
                            Documento.empresa_id == empresa.id,
                            Documento.categoria == DocumentCategories.NOMINAS,
                            Documento.gestoria_id == gestoria_id,
                            db.or_(
                                Documento.periodo == periodo_buscado,
                                db.and_(
                                    Documento.periodo.is_(None),
                                    db.func.extract('month', Documento.fecha_creacion) == mes,
                                    db.func.extract('year', Documento.fecha_creacion) == anio
                                )
                            )
                        ).all()
                        for d in docs_nominas:
                            if os.path.exists(d.ruta_archivo):
                                adjuntos.append({'ruta': d.ruta_archivo, 'nombre': f"Nomina_{empresa.nombre}_{d.nombre_archivo}"})
                    
                    # Buscar seguros sociales
                    if tipos.get('seguros'):
                        docs_seguros = Documento.query.filter(
                            Documento.empresa_id == empresa.id,
                            Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                            Documento.gestoria_id == gestoria_id,
                            db.or_(
                                Documento.periodo == periodo_buscado,
                                db.and_(
                                    Documento.periodo.is_(None),
                                    db.func.extract('month', Documento.fecha_creacion) == mes,
                                    db.func.extract('year', Documento.fecha_creacion) == anio
                                )
                            )
                        ).all()
                        for d in docs_seguros:
                            if os.path.exists(d.ruta_archivo):
                                adjuntos.append({'ruta': d.ruta_archivo, 'nombre': f"Seguros_{empresa.nombre}_{d.nombre_archivo}"})
            
            if not adjuntos:
                return jsonify({NotificationTypes.ERROR: "No hay documentos para enviar"}), 404
            
            from email_sender import enviar_email_con_adjuntos
            asunto = f"Documentación Laboral - {grupo.nombre} - {mes}/{anio}"
            cuerpo = f"Adjuntamos la documentación de Nóminas y Seguros Sociales correspondiente al periodo {mes}/{anio} para todas las empresas de su grupo."
            
            res_email = enviar_email_con_adjuntos(
                destinatarios=[grupo.email_notificaciones],
                asunto=asunto,
                cuerpo=cuerpo,
                adjuntos=adjuntos,
                empresa_nombre=grupo.nombre,
                gestoria_id=gestoria_id
            )
            
            if res_email.get(NotificationTypes.SUCCESS):
                return jsonify({NotificationTypes.SUCCESS: True, "message": "Correo enviado con éxito"})
            else:
                return jsonify({NotificationTypes.ERROR: res_email.get(NotificationTypes.ERROR)}), 500
                
        except Exception as e:
            logger.error(f"Error enviando correo de grupo: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/empresa/<int:empresa_id>/documentos-mes', methods=['GET'])
    @login_required
    def get_documentos_empresa_mes(empresa_id):
        """
        Obtener documentos de Nominas y Seguros Sociales de una empresa para un mes/año
        """
        try:
            mes = request.args.get('mes', type=int)
            anio = request.args.get('anio', type=int)
            
            if not mes or not anio:
                return jsonify({NotificationTypes.ERROR: "Parámetros mes y anio requeridos"}), 400
            
            empresa = Empresa.query.get(empresa_id)
            if not empresa:
                return jsonify({NotificationTypes.ERROR: "Empresa no encontrada"}), 404
            
            # Formatear periodo esperado (YYYYMM)
            periodo_buscado = f"{anio}{mes:02d}"
            
            # Obtener documentos de Nominas
            # Priorizar campo 'periodo', fallback a fecha_creacion para docs antiguos
            nominas = Documento.query.filter(
                Documento.empresa_id == empresa_id,
                Documento.categoria == DocumentCategories.NOMINAS,
                Documento.gestoria_id == get_current_gestoria_id(),
                db.or_(
                    Documento.periodo == periodo_buscado,
                    db.and_(
                        Documento.periodo.is_(None),
                        db.func.extract('month', Documento.fecha_creacion) == mes,
                        db.func.extract('year', Documento.fecha_creacion) == anio
                    )
                )
            ).all()
            
            # Obtener documentos de Seguros Sociales
            seguros = Documento.query.filter(
                Documento.empresa_id == empresa_id,
                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                Documento.gestoria_id == get_current_gestoria_id(),
                db.or_(
                    Documento.periodo == periodo_buscado,
                    db.and_(
                        Documento.periodo.is_(None),
                        db.func.extract('month', Documento.fecha_creacion) == mes,
                        db.func.extract('year', Documento.fecha_creacion) == anio
                    )
                )
            ).all()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "empresa": {
                    "id": empresa.id,
                    "nombre": empresa.nombre
                },
                "nominas": [{"id": d.id, "nombre_archivo": d.nombre_archivo, "ruta_archivo": d.ruta_archivo, "fecha_creacion": d.fecha_creacion.isoformat()} for d in nominas],
                "seguros": [{"id": d.id, "nombre_archivo": d.nombre_archivo, "ruta_archivo": d.ruta_archivo, "fecha_creacion": d.fecha_creacion.isoformat()} for d in seguros]
            })
        
        except Exception as e:
            logger.error(f"Error en documentos-mes: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

def register_nominas_routes(app):
    """Registra rutas para procesamiento de Nominas"""
    
    @app.route('/api/procesar-nominas', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_CREADO,
        entidad_tipo='nominas'
    )
    def api_procesar_nominas():
        """
        Procesa un archivo consolidado de nóminas (PDF de múltiples páginas)
        """
        try:
            # Validar archivos
            if 'file' not in request.files:
                return jsonify({NotificationTypes.ERROR: "No se ha subido ningún archivo"}), 400
            
            nominas_file = request.files['file']
            
            if not nominas_file.filename.lower().endswith('.pdf'):
                return jsonify({NotificationTypes.ERROR: "El archivo debe ser PDF"}), 400
            
            # Crear directorio de procesamiento dentro del proyecto si no existe
            import os
            from werkzeug.utils import secure_filename
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            app_temp_dir = os.path.join(backend_dir, 'temp')
            os.makedirs(app_temp_dir, exist_ok=True)
            
            # Guardar archivo en subdirectorio temporal único
            import tempfile
            temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
            temp_output_dir = tempfile.mkdtemp(dir=app_temp_dir)
            
            nominas_path = os.path.join(temp_dir, secure_filename(nominas_file.filename))
            nominas_file.save(nominas_path)
            
            # Obtener periodo personalizado (opcional)
            periodo_custom = request.form.get('periodo')
            
            # Detectar tamaño del PDF
            from pypdf import PdfReader
            pdf_reader = PdfReader(nominas_path)
            total_pages = len(pdf_reader.pages)
            print(f"📄 Total de páginas: {total_pages}")
            
            # Decidir procesamiento síncrono vs asíncrono
            # Bajamos el límite a 50 para favorecer la estabilidad y el monitoreo
            LIMITE_SINCRONO = 50
            
            if total_pages >= LIMITE_SINCRONO:
                # Procesamiento ASÍNCRONO con Celery
                from tasks_nominas import procesar_nominas_async
                from models import TareaNomina, db
                
                gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1
                
                task = procesar_nominas_async.delay(
                    nominas_path,
                    temp_output_dir,
                    app.config['RUTA_RAIZ_NOTIFICACIONES'],
                    current_user.id,
                    periodo_override=periodo_custom
                )
                
                # Registrar en historial
                tarea_registro = TareaNomina(
                    task_id=task.id,
                    user_id=current_user.id,
                    gestoria_id=gestoria_id,
                    filename=nominas_file.filename,
                    status='PENDING'
                )
                db.session.add(tarea_registro)
                db.session.commit()
                
                print(f"⚡ Procesamiento asíncrono iniciado (Task ID: {task.id})")
                
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'async': True,
                    'task_id': task.id,
                    'total_pages': total_pages,
                    'message': f'Procesando {total_pages} páginas en segundo plano. Recibirás una notificación al completar.'
                })
            
            # Procesamiento SÍNCRONO (< 50 páginas)
            from procesar_nominas import (
                procesar_nominas,
                asociar_con_empresas_bd,
                guardar_en_carpetas_empresas,
                registrar_en_bd
            )
            
            try:
                print(f"🔄 Procesamiento síncrono")
                resultados = procesar_nominas(nominas_path, temp_output_dir, periodo_override=periodo_custom)
                asociar_con_empresas_bd(resultados)
                
                storage_dir = app.config['RUTA_RAIZ_NOTIFICACIONES']
                guardar_en_carpetas_empresas(resultados, storage_dir)
                registrar_en_bd(resultados)
                
                empresas_asociadas = sum(1 for r in resultados if r.get('empresa_id'))
                total_trabajadores = sum(r.get('num_trabajadores', 0) for r in resultados)
                
                response = {
                    NotificationTypes.SUCCESS: True,
                    "total_empresas": len(resultados),
                    "empresas_clasificadas": empresas_asociadas,
                    "total_trabajadores": total_trabajadores,
                    "documentos_creados": empresas_asociadas,
                }
                
                # Auditoría
                request.auditoria_detalles = {
                    'archivo': nominas_file.filename,
                    'empresas_procesadas': len(resultados),
                    'empresas_asociadas': empresas_asociadas
                }
                
                return jsonify(response)
                
            finally:
                # Limpiar temporales del procesamiento síncrono
                try:
                    shutil.rmtree(temp_dir)
                    shutil.rmtree(temp_output_dir)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error procesando Nominas: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    
    @app.route('/api/procesar-nominas-multiple', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_CREADO,
        entidad_tipo='nominas_multiple'
    )
    def api_procesar_nominas_multiple():
        """
        Procesa múltiples archivos de nóminas
        
        Request:
            - files['files[]']: Array de archivos PDF
            - form['periodo']: Periodo manual (opcional)
        
        Response:
            {
                NotificationTypes.SUCCESS: true,
                "task_ids": ["id1", "id2"],
                "total_files": 2
            }
        """
        try:
            # Validar archivos
            files = request.files.getlist('files[]')
            if not files:
                return jsonify({NotificationTypes.ERROR: "Debes subir al menos un archivo"}), 400
            
            periodo_custom = request.form.get('periodo')
            
            import tempfile
            import os
            from tasks_nominas import procesar_nominas_async
            
            task_ids = []
            storage_dir = app.config['RUTA_RAIZ_NOTIFICACIONES']
            
            for file in files:
                if not file.filename.lower().endswith('.pdf'):
                    continue
                
                # Crear directorios temporales
                temp_upload_dir = tempfile.mkdtemp()
                temp_output_dir = tempfile.mkdtemp()
                
                # Guardar archivo
                file_path = os.path.join(temp_upload_dir, file.filename)
                file.save(file_path)
                
                # Enviar a Celery
                task = procesar_nominas_async.delay(
                    file_path,
                    temp_output_dir,
                    storage_dir,
                    current_user.id,
                    periodo_override=periodo_custom
                )
                
                task_ids.append({
                    'task_id': task.id,
                    'filename': file.filename
                })
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'task_ids': task_ids,
                'total_files': len(files),
                'message': f'Procesando {len(files)} archivos en segundo plano'
            })
        
        except Exception as e:
            logger.error(f"Error procesando múltiples nóminas: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    
    @app.route('/api/preview-nominas', methods=['POST'])
    @login_required
    def api_preview_nominas():
        """
        Detecta el periodo de un archivo de nóminas sin procesarlo
        Lee solo la primera página para extraer el periodo
        
        Request:
            - files['file']: Archivo PDF de nóminas
            - form['periodo_manual']: Periodo manual ingresado por usuario (opcional)
        
        Response:
            {
                "periodo_detectado": "202511",
                "periodo_detectado_texto": "Noviembre 2025",
                "periodo_manual": "202512",
                "hay_discrepancia": true,
                "mensaje_warning": "..."
            }
        """
        try:
            if 'file' not in request.files:
                return jsonify({NotificationTypes.ERROR: "Debes subir un archivo"}), 400
            
            file = request.files['file']
            periodo_manual = request.form.get('periodo_manual')
            
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({NotificationTypes.ERROR: "El archivo debe ser PDF"}), 400
            
            import tempfile
            import os
            import pdfplumber
            from procesar_nominas import extraer_info_empresa_nomina
            
            # Guardar archivo temporal
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, file.filename)
            file.save(temp_path)
            
            try:
                # Importar extractores actualizados
                from procesar_nominas import extraer_info_empresa_nomina
                from procesar_seguros_sociales import extraer_info_empresa_rlc, extraer_info_empresa_rnt
                
                # Leer solo la primera página
                with pdfplumber.open(temp_path) as pdf:
                    if len(pdf.pages) == 0:
                        return jsonify({NotificationTypes.ERROR: "El PDF está vacío"}), 400
                    
                    first_page = pdf.pages[0]
                    
                    # 1. Intentar como Nómina
                    info = extraer_info_empresa_nomina(first_page)
                    periodo_detectado = info.get('periodo')
                    periodo_detectado_texto = info.get('periodo_texto')
                    
                    # 2. Intentar como RLC
                    if not periodo_detectado:
                        info_ss = extraer_info_empresa_rlc(first_page)
                        if info_ss.get('ccc'):
                            periodo_detectado = info_ss.get('periodo')
                            periodo_detectado_texto = info_ss.get('periodo_texto')
                    
                    # 3. Intentar como RNT
                    if not periodo_detectado:
                        info_ss = extraer_info_empresa_rnt(first_page)
                        if info_ss.get('ccc'):
                            periodo_detectado = info_ss.get('periodo')
                            periodo_detectado_texto = info_ss.get('periodo_texto')
                    
                    # 4. Fallback final: Buscar patrón MM/YYYY con contexto de liquidación
                    if not periodo_detectado:
                        full_text = first_page.extract_text() or ""
                        # Buscar patron mm/yyyy con contexto de liquidacion (Soporta DD/MM/YYYY, /, -, espacio)
                        match = re.search(r'LIQUIDACI[OÓ]N[:\s-]+(?:(\d{1,2})[\s/-]+)?(\d{1,2})[\s/-]+(\d{4})', full_text, re.IGNORECASE | re.DOTALL)
                        if not match:
                            # Intento mas agresivo
                            match = re.search(r'PERIODO[:\s-]+(?:(\d{1,2})[\s/-]+)?(\d{1,2})[\s/-]+(\d{4})', full_text, re.IGNORECASE | re.DOTALL)
                        
                        if match:
                            g1, g2, g3 = match.groups()
                            mes, año = (g2, g3) if g3 else (g1, g2)
                            if mes and año:
                                mes = f"{int(mes):02d}"
                                periodo_detectado = f"{año}{mes}"
                                meses_map = {
                                    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                                    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                                    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                                }
                                periodo_detectado_texto = f"{meses_map.get(mes, mes)} {año}"
                
                # Definir meses para el formateo de periodo manual si es necesario
                meses_dict = {
                    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
                }
                # Comparar con periodo manual
                hay_discrepancia = False
                mensaje_warning = None
                
                if periodo_manual and periodo_detectado:
                    if periodo_manual != periodo_detectado:
                        hay_discrepancia = True
                        año_manual = periodo_manual[:4]
                        mes_manual = periodo_manual[4:6]
                        periodo_manual_texto = f"{meses_dict.get(mes_manual, mes_manual)} {año_manual}"
                        
                        mensaje_warning = (
                            f"⚠️ Discrepancia detectada:\n\n"
                            f"Periodo seleccionado: {periodo_manual_texto}\n"
                            f"Periodo detectado en el PDF: {periodo_detectado_texto or periodo_detectado}\n\n"
                            f"¿Estás seguro de que quieres procesar este archivo con el periodo {periodo_manual_texto}?"
                        )
                
                return jsonify({
                    'success': True,
                    'periodo_detectado': periodo_detectado,
                    'periodo_detectado_texto': periodo_detectado_texto,
                    'periodo_manual': periodo_manual,
                    'hay_discrepancia': hay_discrepancia,
                    'mensaje_warning': mensaje_warning
                })
            
            finally:
                # Limpiar archivo temporal
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error en preview de nóminas: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    
    @app.route('/api/buscar-documentos-periodo', methods=['GET'])
    @login_required
    def buscar_documentos_periodo():
        """
        Busca documentos de una empresa por periodo
        
        Query params:
            - empresa_id: ID de la empresa
            - periodo: Periodo en formato YYYYMM (ej: 202412)
        
        Response:
            {
                NotificationTypes.SUCCESS: true,
                "periodo": "202412",
                "total": 17,
                "nominas": [...],
                "rnt": [...],
                "rlc": [...],
                "otros": [...]
            }
        """
        try:
            empresa_id = request.args.get('empresa_id', type=int)
            periodo = request.args.get('periodo')
            
            if not empresa_id or not periodo:
                return jsonify({NotificationTypes.ERROR: "Faltan parámetros: empresa_id y periodo son requeridos"}), 400
            
            # Buscar nóminas
            nominas = Documento.query.filter_by(
                empresa_id=empresa_id,
                categoria='Nominas',
                periodo=periodo,
                gestoria_id=get_current_gestoria_id()
            ).all()
            
            # Buscar RNT
            rnt = Documento.query.filter(
                Documento.empresa_id == empresa_id,
                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                Documento.periodo == periodo,
                Documento.nombre_archivo.ilike('%RNT%'),
                Documento.gestoria_id == get_current_gestoria_id()
            ).all()
            
            # Buscar RLC
            rlc = Documento.query.filter(
                Documento.empresa_id == empresa_id,
                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                Documento.periodo == periodo,
                Documento.nombre_archivo.ilike('%RLC%'),
                Documento.gestoria_id == get_current_gestoria_id()
            ).all()
            
            # Buscar otros seguros sociales
            otros = Documento.query.filter(
                Documento.empresa_id == empresa_id,
                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                Documento.periodo == periodo,
                ~Documento.nombre_archivo.ilike('%RNT%'),
                ~Documento.nombre_archivo.ilike('%RLC%'),
                Documento.gestoria_id == get_current_gestoria_id()
            ).all()
            
            total = len(nominas) + len(rnt) + len(rlc) + len(otros)
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "periodo": periodo,
                "total": total,
                "nominas": [n.to_dict() for n in nominas],
                "rnt": [r.to_dict() for r in rnt],
                "rlc": [r.to_dict() for r in rlc],
                "otros": [o.to_dict() for o in otros]
            })
            
        except Exception as e:
            print(f"Error buscando documentos por periodo: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500

    
    @app.route('/api/enviar-correo-nominas', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_PROCESADO,
        entidad_tipo='correo_nominas'
    )
    def api_enviar_correo_nominas():
        """
        Envía correo con nóminas y opcionalmente RNT
        
        Request:
            {
                "email": "destino@empresa.com",
                "modo": "NOMINAS" | "NOMINAS_RNT" | "PERSONALIZADO",
                "nominas_ids": [1, 2, 3],
                "incluir_rnt": true/false (solo para PERSONALIZADO)
            }
        
        Response:
            {
                NotificationTypes.SUCCESS: true,
                "enviados": 3,
                "adjuntos": 4,
                "email": "destino@empresa.com"
            }
        """
        try:
            from email_payroll import enviar_nominas_automatico, buscar_rnt_periodo
            
            data = request.json
            email_destino = data.get('email')
            modo_envio = data.get('modo', 'NOMINAS')
            nominas_ids = data.get('nominas_ids', [])
            incluir_rnt = data.get('incluir_rnt', False)
            
            # Validar email
            if not email_destino:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Email requerido'}), 400
            
            # Validar formato de email
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, email_destino):
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Email inválido'}), 400
            
            # Obtener nóminas
            nominas = []
            for nomina_id in nominas_ids:
                doc = Documento.query.get(nomina_id)
                if doc:
                    # Extraer periodo del nombre del archivo
                    periodo_match = re.search(r'(\d{6})', doc.nombre_archivo)
                    periodo = periodo_match.group(1) if periodo_match else 'N/A'
                    
                    # Obtener nombre de empresa
                    empresa = Empresa.query.get(doc.empresa_id)
                    empresa_nombre = empresa.nombre if empresa else 'Cliente'
                    
                    nominas.append({
                        'id': doc.id,
                        'ruta_pdf': doc.ruta_archivo,
                        'nombre_archivo': os.path.basename(doc.ruta_archivo),
                        'periodo': periodo,
                        'empresa_id': doc.empresa_id,
                        'empresa_nombre': empresa_nombre
                    })
            
            # Obtener TODOS los documentos de Seguros Sociales seleccionados (RNT, RLC, etc.)
            seguros_ids = data.get('seguros_ids', [])
            seguros_data = []
            
            if seguros_ids and len(seguros_ids) > 0:
                logger.info(f"Procesando {len(seguros_ids)} documentos de Seguros Sociales")
                for seguro_id in seguros_ids:
                    doc_seguros = Documento.query.get(seguro_id)
                    if doc_seguros:
                        print(f"  ✅ Agregado: {doc_seguros.nombre_archivo}")
                        seguros_data.append({
                            'id': doc_seguros.id,
                            'ruta_pdf': doc_seguros.ruta_archivo,
                            'nombre_archivo': os.path.basename(doc_seguros.ruta_archivo),
                            'empresa_id': doc_seguros.empresa_id
                        })
                    else:
                        print(f"  ⚠️ No se encontró documento con ID {seguro_id}")
            else:
                print(f"ℹ️ No se enviaron seguros_ids")
            
            # Validar que haya al menos un documento para enviar
            if not nominas and not seguros_data:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Debe seleccionar al menos un documento para enviar'}), 400
            
            # Enviar correo con nueva firma (forzar reenvío en modo manual)
            resultado = enviar_nominas_automatico(
                email_destino=email_destino,
                nominas=nominas,
                rnt=seguros_data,  # Ahora es una lista con todos los seguros
                usuario_id=current_user.id,
                forzar_reenvio=True  # ✅ Permite reenviar manualmente
            )
            
            # Auditoría
            if resultado.get(NotificationTypes.SUCCESS):
                request.auditoria_detalles = {
                    'email_destino': email_destino,
                    'modo_envio': modo_envio,
                    'nominas_enviadas': resultado.get('enviados', 0),
                    'incluyo_rnt': resultado.get('incluyo_rnt', False)
                }
            
            return jsonify(resultado)
        
        except Exception as e:
            logger.error(f"Error enviando correo: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500

    @app.route('/api/enviar-correos-masivo', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_PROCESADO,
        entidad_tipo='correo_masivo'
    )
    def api_enviar_correos_masivo():
        """
        Envía correos masivos a empresas con email principal.
        
        ESTRATEGIA HÍBRIDA:
        - < 50 emails: Procesamiento síncrono con rate limiting
        - ≥ 50 emails: Procesamiento asíncrono con Celery
        
        Request:
            {
                "mes": 12,
                "anio": 2025,
                "modo": "NOMINAS" | "NOMINAS_RNT"
            }
        """
        try:
            data = request.get_json()
            mes = data.get('mes')
            anio = data.get('anio')
            tipos_documentos = data.get('tipos_documentos', {'nominas': True, 'rnt': False, 'rlc': False})
            
            if not mes or not anio:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'Mes y año requeridos'}), 400
            
            # Obtener empresas con email principal
            empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
                Empresa.email.isnot(None),
                Empresa.email != ''
            ).all()
            
            total_empresas = len(empresas)
            
            # 🎯 DECISIÓN: Síncrono vs Asíncrono
            LIMITE_SINCRONO = 50
            
            if total_empresas >= LIMITE_SINCRONO:
                # ⚡ PROCESAMIENTO ASÍNCRONO CON CELERY
                from celery_worker import enviar_correos_masivo_async
                
                task = enviar_correos_masivo_async.delay(
                    mes=mes,
                    anio=anio,
                    tipos_documentos=tipos_documentos,
                    user_id=current_user.id
                )
                
                print(f"📤 Envío masivo asíncrono iniciado: {total_empresas} empresas (Task ID: {task.id})")
                
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'async': True,
                    'task_id': task.id,
                    'total_empresas': total_empresas,
                    'message': f'Procesando {total_empresas} empresas en segundo plano. Puedes cerrar esta ventana.'
                })
            
            else:
                # 🔄 PROCESAMIENTO SÍNCRONO CON RATE LIMITING
                import time
                
                print(f"📤 Envío masivo síncrono: {total_empresas} empresas")
                
                resultados = {
                    'total_empresas': total_empresas,
                    'enviados': 0,
                    'errores': 0,
                    'omitidos': 0,
                    'detalles': []
                }
                
                periodo = f"{anio}{str(mes).zfill(2)}"
                
                for idx, empresa in enumerate(empresas):
                    try:
                        documentos_adjuntos = []
                        
                        # Buscar Nóminas si están seleccionadas
                        if tipos_documentos.get('nominas', False):
                            nominas = Documento.query.filter(
                                Documento.empresa_id == empresa.id,
                                Documento.categoria == 'Nominas',
                                Documento.periodo == periodo,
                                Documento.gestoria_id == empresa.gestoria_id
                            ).all()
                            documentos_adjuntos.extend(nominas)
                        
                        # Buscar RNT si está seleccionado
                        if tipos_documentos.get('rnt', False):
                            rnt = Documento.query.filter(
                                Documento.empresa_id == empresa.id,
                                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                                Documento.nombre_archivo.ilike('%RNT%'),
                                Documento.periodo == periodo,
                                Documento.gestoria_id == empresa.gestoria_id
                            ).all()
                            documentos_adjuntos.extend(rnt)
                        
                        # Buscar RLC si está seleccionado
                        if tipos_documentos.get('rlc', False):
                            rlc = Documento.query.filter(
                                Documento.empresa_id == empresa.id,
                                Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
                                Documento.nombre_archivo.ilike('%RLC%'),
                                Documento.periodo == periodo,
                                Documento.gestoria_id == empresa.gestoria_id
                            ).all()
                            documentos_adjuntos.extend(rlc)
                        
                        # Si no hay documentos, omitir
                        if not documentos_adjuntos:
                            resultados['omitidos'] += 1
                            resultados['detalles'].append({
                                'empresa': empresa.nombre,
                                'email': empresa.email,
                                'status': 'omitido',
                                'razon': 'Sin documentos para el periodo'
                            })
                            continue
                        
                        # Preparar datos de documentos
                        nominas_data = []
                        seguros_data = []  # Lista para todos los seguros sociales (RNT, RLC, etc.)
                        
                        for doc in documentos_adjuntos:
                            if doc.categoria == 'Nominas':
                                periodo_match = re.search(r'(\d{6})', doc.nombre_archivo)
                                periodo_doc = periodo_match.group(1) if periodo_match else 'N/A'
                                
                                nominas_data.append({
                                    'id': doc.id,
                                    'ruta_pdf': doc.ruta_archivo,
                                    'nombre_archivo': os.path.basename(doc.ruta_archivo),
                                    'periodo': periodo_doc,
                                    'empresa_id': doc.empresa_id,
                                    'empresa_nombre': empresa.nombre
                                })
                            elif doc.categoria == DocumentCategories.SEGUROS_SOCIALES:
                                # Agregar todos los seguros sociales (RNT, RLC, etc.)
                                seguros_data.append({
                                    'id': doc.id,
                                    'ruta_pdf': doc.ruta_archivo,
                                    'nombre_archivo': os.path.basename(doc.ruta_archivo),
                                    'empresa_id': doc.empresa_id
                                })
                        
                        # Enviar correo usando email_payroll
                        from email_payroll import enviar_nominas_automatico
                        
                        resultado = enviar_nominas_automatico(
                            email_destino=empresa.email,
                            nominas=nominas_data,
                            rnt=seguros_data if seguros_data else None,  # Pasar lista de seguros
                            usuario_id=current_user.id
                        )
                        
                        if resultado.get(NotificationTypes.SUCCESS):
                            resultados['enviados'] += 1
                            resultados['detalles'].append({
                                'empresa': empresa.nombre,
                                'email': empresa.email,
                                'status': 'enviado',
                                'adjuntos': len(nominas_data) + len(seguros_data)
                            })
                            logger.info(f"[{idx+1}/{total_empresas}] {empresa.nombre}")
                        else:
                            resultados['errores'] += 1
                            resultados['detalles'].append({
                                'empresa': empresa.nombre,
                                'email': empresa.email,
                                'status': NotificationTypes.ERROR,
                                'razon': resultado.get(NotificationTypes.ERROR, 'Error desconocido')
                            })
                            logger.error(f"[{idx+1}/{total_empresas}] {empresa.nombre}")
                        
                        # ⏱️ RATE LIMITING
                        if (idx + 1) % 10 == 0:
                            time.sleep(5)  # 5 segundos cada 10 emails
                        else:
                            time.sleep(2)  # 2 segundos entre emails
                            
                    except Exception as e:
                        resultados['errores'] += 1
                        resultados['detalles'].append({
                            'empresa': empresa.nombre,
                            'email': empresa.email if hasattr(empresa, 'email') else 'N/A',
                            'status': NotificationTypes.ERROR,
                            'razon': str(e)
                        })
                        logger.error(f"[{idx+1}/{total_empresas}] {empresa.nombre} - {e}")
                
                logger.info(f"Envío síncrono completado: {resultados['enviados']} enviados, {resultados['errores']} errores")
                
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'async': False,
                    'resultados': resultados
                })
            
        except Exception as e:
            logger.error(f"Error en envío masivo: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: str(e)
            }), 500
    
    @app.route('/api/enviar-correos-masivo/status/<task_id>', methods=['GET'])
    @login_required
    def api_enviar_correos_status(task_id):
        """
        Consulta el estado de una tarea de envío masivo asíncrona.
        
        Returns:
            {
                "state": "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE",
                "current": 10,
                "total": 100,
                "empresa": "Empresa Ejemplo",
                "enviados": 8,
                "errores": 2,
                "result": {...}  # Solo en SUCCESS
            }
        """
        try:
            from celery_worker import celery
            from celery.result import AsyncResult
            
            task = AsyncResult(task_id, app=celery)
            
            if task.state == 'PENDING':
                response = {
                    'state': task.state,
                    'status': 'Pendiente...',
                    'current': 0,
                    'total': 0
                }
            elif task.state == 'PROGRESS':
                response = {
                    'state': task.state,
                    'current': task.info.get('current', 0),
                    'total': task.info.get('total', 1),
                    'empresa': task.info.get('empresa', ''),
                    'enviados': task.info.get('enviados', 0),
                    'errores': task.info.get('errores', 0),
                    'status': f"Procesando {task.info.get('current', 0)}/{task.info.get('total', 1)}"
                }
            elif task.state == 'SUCCESS':
                response = {
                    'state': task.state,
                    'result': task.result,
                    'status': 'Completado'
                }
            else:
                # FAILURE o estado desconocido
                response = {
                    'state': task.state,
                    'status': str(task.info),
                    NotificationTypes.ERROR: str(task.info) if task.state == 'FAILURE' else None
                }
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({
                'state': 'ERROR',
                NotificationTypes.ERROR: str(e)
            }), 500
    
   

    

app = create_app(os.getenv('FLASK_ENV', 'development'))
register_chat_routes(app)  # Chat IA routes
register_permisos_routes(app)  # RBAC routes
@app.after_request
def clear_legacy_cookies(response):
    """Limpiar cookies obsoletas para evitar rastro en cURL y Network tab"""
    if 'remember_token' in request.cookies:
        response.delete_cookie('remember_token')
    if 'session' in request.cookies:
        response.delete_cookie('session')
    return response

# ⭐ Rutas de Monitoreo para Super-Admin
from routes_monitoring import register_monitoring_routes
register_monitoring_routes(app)

register_pagination_routes(app)
register_seguros_sociales_routes(app)
register_nominas_routes(app)

# ⭐ Rutas de Impersonación (soporte/super_admin)
from routes_impersonacion import register_impersonacion_routes
import redis as _redis_lib
_redis_client_imp = _redis_lib.from_url(
    app.config.get('REDIS_URL', 'redis://localhost:6379/0'),
    decode_responses=True
)
register_impersonacion_routes(app, socketio, _redis_client_imp)
print("✅ Rutas de Impersonación registradas")

# ⭐ Portal del Empleado
from routes_portal_empleado import register_portal_empleado_routes
register_portal_empleado_routes(app)
print("✅ Rutas del Portal del Empleado registradas")

# ⭐ Rutas de Sincronización Externa DEHú - REGISTRADAS ARRIBA (línea ~760)

# ⭐ Servir el frontend del Portal del Empleado (build estático)
_PORTAL_STATIC = os.path.join(basedir, 'static', 'portal')

@app.route('/portal/', defaults={'path': ''})
@app.route('/portal/<path:path>')
def serve_portal(path):
    """Sirve el frontend del Portal del Empleado (SPA)."""
    from flask import send_from_directory
    if path and os.path.exists(os.path.join(_PORTAL_STATIC, path)):
        return send_from_directory(_PORTAL_STATIC, path)
    return send_from_directory(_PORTAL_STATIC, 'index.html')

# Servir archivos estáticos del directorio storage
@app.route('/storage/<path:filename>')
def serve_storage_file(filename):
    """Sirve archivos estáticos del directorio storage (logos, favicons, etc.)"""
    from flask import send_from_directory
    return send_from_directory('storage', filename)




# ============================================
# HEALTH CHECK ENDPOINTS
# ============================================

@app.route('/api/health')
def health_check():
    """Health check superficial para load balancers."""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route('/api/health/deep')
def deep_health_check():
    """Health check profundo para monitoreo."""
    from sqlalchemy import text
    import redis as redis_lib
    
    checks = {}
    
    # Check database
    try:
        db.session.execute(text('SELECT 1'))
        checks['database'] = {'healthy': True}
    except Exception as e:
        checks['database'] = {'healthy': False, 'error': str(e)}
    
    # Check Redis
    try:
        redis_client = redis_lib.from_url(app.config['REDIS_URL'])
        redis_client.ping()
        checks['redis'] = {'healthy': True}
    except Exception as e:
        checks['redis'] = {'healthy': False, 'error': str(e)}
    
    # Check Celery
    try:
        from celery_worker import celery
        result = celery.control.ping(timeout=3)
        checks['celery'] = {'healthy': len(result) > 0 if result else False, 'workers': len(result) if result else 0}
    except Exception as e:
        checks['celery'] = {'healthy': False, 'error': str(e)}
    
    # Check storage
    try:
        storage_path = app.config['RUTA_RAIZ_NOTIFICACIONES']
        checks['storage'] = {'healthy': os.path.exists(storage_path), 'path': storage_path}
    except Exception as e:
        checks['storage'] = {'healthy': False, 'error': str(e)}
    
    all_healthy = all(c.get('healthy', False) for c in checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }), status_code


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handler para archivos que exceden el límite de tamaño."""
    return jsonify({
        'error': 'Archivo demasiado grande',
        'max_size_mb': 50,
        'message': 'El archivo excede el límite de 50MB'
    }), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handler global para límites de peticiones (Flask-Limiter)"""
    return jsonify({
        'error': f"Has excedido el límite de peticiones. {e.description}"
    }), 429


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("\n🚀 Servidor WebSocket iniciando en http://127.0.0.1:5000\n")
    
    # Obtener socketio desde app
    socketio = app.config['SOCKETIO']
    socketio.run(app, debug=True, port=5000)
