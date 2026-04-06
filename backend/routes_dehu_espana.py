# backend/routes_dehu_espana.py
"""
API REST para DEHú España
Endpoints para gestionar notificaciones del gobierno español
"""
import logging

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from services.dehu_session_manager import dehu_manager
from datetime import datetime
import tempfile
import os
from functools import wraps
from async_runner import runner

logger = logging.getLogger(__name__)

dehu_bp = Blueprint('dehu_espana', __name__)

def async_route(f):
    """Decorator para rutas async usando AsyncRunner"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Ejecutar la corrutina en el hilo dedicado de asyncio
        # Esto mantiene vivo el loop y los objetos de Playwright
        return runner.run_sync(f(*args, **kwargs))
    return wrapper


# =============================================================================
# GESTIÓN DE CONEXIÓN
# =============================================================================

@dehu_bp.route('/api/dehu-espana/connect', methods=['POST'])
@login_required
@async_route
async def connect():
    """Inicia sesión DEHú con certificado digital"""
    logger.debug("Entrando a connect endpoint")
    try:
        # No usar get_json() porque es multipart/form-data
        # data = request.get_json() 
        
        # Validar datos
        if 'pfx_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Certificado PFX requerido'
            }), 400
        
        pfx_file = request.files['pfx_file']
        pfx_passphrase = request.form.get('passphrase', '')
        
        if not pfx_passphrase:
            return jsonify({
                'success': False,
                'message': 'Contraseña del certificado requerida'
            }), 400
        
        # Guardar certificado temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pfx') as tmp:
            pfx_file.save(tmp.name)
            pfx_path = tmp.name
        
        try:
            # Crear sesión
            success, service, message = await dehu_manager.create_session(
                user_id=current_user.id,
                pfx_path=pfx_path,
                pfx_passphrase=pfx_passphrase,
                headless=True
            )
            
            if success:
                user_info = dehu_manager.get_user_info(current_user.id)
                return jsonify({
                    'success': True,
                    'message': message,
                    'user_info': user_info
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 401
                
        finally:
            # Eliminar certificado temporal
            try:
                os.unlink(pfx_path)
            except Exception:
                pass
                
    except Exception as e:
        current_app.logger.error(f"Error en connect: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@dehu_bp.route('/api/dehu-espana/disconnect', methods=['POST'])
@login_required
@async_route
async def disconnect():
    """Cierra sesión DEHú"""
    try:
        await dehu_manager.disconnect_user(current_user.id)
        return jsonify({
            'success': True,
            'message': 'Sesión cerrada'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@dehu_bp.route('/api/dehu-espana/status', methods=['GET'])
@login_required
def status():
    """Verifica estado de conexión"""
    is_connected = dehu_manager.is_connected(current_user.id)
    user_info = dehu_manager.get_user_info(current_user.id) if is_connected else None
    
    return jsonify({
        'success': True,
        'connected': is_connected,
        'user_info': user_info
    })


# =============================================================================
# NOTIFICACIONES PENDIENTES
# =============================================================================

@dehu_bp.route('/api/dehu-espana/notifications/pending', methods=['GET'])
@login_required
@async_route
async def get_pending_notifications():
    """Lista notificaciones pendientes"""
    logger.debug("Entrando a get_pending_notifications")
    try:
        service = dehu_manager.get_session(current_user.id)
        if not service:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 50, type=int), 200)

        data = await service.get_pending_notifications(page=page, limit=limit)
        
        # Calcular días restantes para cada notificación
        for item in data.get('items', []):
            if item.get('expirationDate'):
                try:
                    exp = datetime.fromisoformat(item['expirationDate'].replace('Z', '+00:00'))
                    remaining = (exp - datetime.now(exp.tzinfo)).days
                    item['daysRemaining'] = remaining
                except:
                    item['daysRemaining'] = None
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo pendientes: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# NOTIFICACIONES REALIZADAS
# =============================================================================

@dehu_bp.route('/api/dehu-espana/notifications/realized', methods=['GET'])
@login_required
@async_route
async def get_realized_notifications():
    """Lista notificaciones realizadas"""
    try:
        service = dehu_manager.get_session(current_user.id)
        if not service:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        days_back = request.args.get('days_back', 7, type=int)
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 50, type=int), 200)
        
        data = await service.get_realized_notifications(
            days_back=days_back,
            page=page,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo realizadas: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# DETALLE DE NOTIFICACIÓN
# =============================================================================

@dehu_bp.route('/api/dehu-espana/notifications/<sent_reference>/detail', methods=['GET'])
@login_required
@async_route
async def get_notification_detail(sent_reference):
    """Obtiene detalle de una notificación"""
    try:
        service = dehu_manager.get_session(current_user.id)
        if not service:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        notif_type = request.args.get('type', 'pending')
        
        if notif_type == 'realized':
            data = await service.get_realized_detail(sent_reference)
        else:
            data = await service.get_notification_detail(sent_reference)
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo detalle: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# ACEPTAR NOTIFICACIÓN
# =============================================================================

@dehu_bp.route('/api/dehu-espana/notifications/<sent_reference>/accept', methods=['POST'])
@login_required
@async_route
async def accept_notification(sent_reference):
    """Acepta una notificación (IRREVERSIBLE)"""
    try:
        service = dehu_manager.get_session(current_user.id)
        if not service:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        result = await service.accept_notification(sent_reference)
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'message': result.get('error'),
                'detail': result.get('detail')
            }), 400
        
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Notificación aceptada exitosamente'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error aceptando notificación: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# DESCARGAR DOCUMENTOS
# =============================================================================

@dehu_bp.route('/api/dehu-espana/notifications/<sent_reference>/download', methods=['GET'])
@login_required
@async_route
async def download_document(sent_reference):
    """Descarga documento anexo o resguardo"""
    try:
        service = dehu_manager.get_session(current_user.id)
        if not service:
            return jsonify({
                'success': False,
                'message': 'No hay sesión activa'
            }), 401
        
        doc_type = request.args.get('type', 'annexe')
        
        if doc_type == 'voucher':
            pdf_bytes = await service.download_voucher(sent_reference)
            filename = f"{sent_reference[:20]}_resguardo.pdf"
        else:
            pdf_bytes = await service.download_annexe(sent_reference)
            filename = f"{sent_reference[:20]}_documento.pdf"
        
        if not pdf_bytes:
            return jsonify({
                'success': False,
                'message': 'No se pudo descargar el documento'
            }), 404
        
        # Guardar temporalmente y enviar
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        
        try:
            return send_file(
                tmp_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        finally:
            # Limpiar después de enviar
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        
    except Exception as e:
        current_app.logger.error(f"Error descargando documento: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
