#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rutas de Administracion
=======================

Endpoints para funcionalidades de administracion del sistema.
"""

from flask import Blueprint, jsonify, request, current_app
from models import ApiKeyUsage, Gestoria, User, Empresa, Documento, db
from datetime import date, timedelta, datetime
import os
import logging
import shutil
from sqlalchemy import func
from decorators import admin_required
from flask_login import current_user, login_required
from functools import wraps
from constants import NotificationTypes

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


# ============================================
# GESTIÓN DE ACCESOS (INVITADOS / JERARQUÍA)
# ============================================

@admin_bp.route('/users/<int:user_id>/access', methods=['GET'])
@admin_required
def get_user_access(user_id):
    """Obtener accesos de un usuario a empresas y grupos"""
    u = db.session.get(User, user_id)
    if not u or u.gestoria_id != current_user.gestoria_id:
        return jsonify({NotificationTypes.ERROR: "Usuario no encontrado"}), 404
        
    from models import UserEmpresaAcceso, UserGrupoAcceso
    
    empresas = [{
        'id': a.empresa.id,
        'nombre': a.empresa.nombre,
        'nif': a.empresa.nif
    } for a in u.empresa_accesos]
    
    grupos = [{
        'id': a.grupo.id,
        'nombre': a.grupo.nombre,
        'es_admin_grupo': a.es_admin_grupo
    } for a in u.grupo_accesos]
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        'empresas': empresas,
        'grupos': grupos
    })


@admin_bp.route('/users/<int:user_id>/access', methods=['POST'])
@admin_required
def update_user_access(user_id):
    """Actualizar accesos de un usuario"""
    u = db.session.get(User, user_id)
    if not u or u.gestoria_id != current_user.gestoria_id:
        return jsonify({NotificationTypes.ERROR: "Usuario no encontrado"}), 404
        
    data = request.json
    from models import UserEmpresaAcceso, UserGrupoAcceso, Empresa, GrupoEmpresa
    
    try:
        # 1. Actualizar Empresas
        if 'empresa_ids' in data:
            empresa_ids = data['empresa_ids']
            
            # Si no es SuperAdmin/Jefatura total, solo puede afectar empresas de sus grupos gestionados
            # Jefatura suele tener acceso a todo en su gestoría, pero si queremos restringir:
            is_restricted = current_user.departamento.nombre != 'Jefatura' and not current_user.is_super_admin
            managed_group_ids = current_user.get_managed_group_ids() if is_restricted else []

            if is_restricted:
                # Eliminar solo accesos a empresas que pertenecen a los grupos gestionados
                # Usar subquery para compatibilidad con delete()
                subquery = db.session.query(Empresa.id).filter(Empresa.grupo_id.in_(managed_group_ids)).subquery()
                db.session.query(UserEmpresaAcceso).filter(
                    UserEmpresaAcceso.user_id == user_id,
                    UserEmpresaAcceso.empresa_id.in_(subquery)
                ).delete(synchronize_session=False)
            else:
                # Jefatura/SuperAdmin: borrar todo lo de la gestoría para este usuario
                # (Pero solo de su gestoría, que ya está validado arriba)
                UserEmpresaAcceso.query.filter_by(user_id=user_id).delete()
            
            # Añadir nuevos
            for e_id in empresa_ids:
                emp = db.session.get(Empresa, e_id)
                if emp and emp.gestoria_id == u.gestoria_id:
                    # Si es restringido, validar que la empresa esté en sus grupos
                    if is_restricted and emp.grupo_id not in managed_group_ids:
                        continue
                    db.session.add(UserEmpresaAcceso(user_id=user_id, empresa_id=e_id))
        
        # 2. Actualizar Grupos
        if 'grupos' in data:
            is_restricted = current_user.departamento.nombre != 'Jefatura' and not current_user.is_super_admin
            managed_group_ids = current_user.get_managed_group_ids() if is_restricted else []

            if is_restricted:
                # Eliminar solo accesos a grupos gestionados
                db.session.query(UserGrupoAcceso).filter(
                    UserGrupoAcceso.user_id == user_id,
                    UserGrupoAcceso.grupo_id.in_(managed_group_ids)
                ).delete(synchronize_session=False)
            else:
                UserGrupoAcceso.query.filter_by(user_id=user_id).delete()
                
            # Añadir nuevos
            for g_data in data['grupos']:
                g_id = g_data.get('id')
                es_admin = g_data.get('es_admin_grupo', False)
                grp = db.session.get(GrupoEmpresa, g_id)
                if grp and grp.gestoria_id == u.gestoria_id:
                    if is_restricted and g_id not in managed_group_ids:
                        continue
                    db.session.add(UserGrupoAcceso(
                        user_id=user_id, 
                        grupo_id=g_id, 
                        es_admin_grupo=es_admin
                    ))
                    
        db.session.commit()

        # Emitir notificación de actualización de permisos via SocketIO
        try:
            socketio = current_app.extensions.get('socketio')
            if socketio:
                from socketio_events import notify_permissions_updated
                notify_permissions_updated(socketio, user_id)
        except Exception as se:
            print(f"Error al emitir notificación SocketIO: {se}")

        return jsonify({NotificationTypes.SUCCESS: True, "message": "Accesos actualizados"})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/api-keys/stats', methods=['GET'])
@admin_required
def get_api_keys_stats():
    """Estadisticas generales de API keys de hoy"""
    
    hoy = date.today()
    
    # Stats de hoy
    stats_hoy = ApiKeyUsage.query.filter_by(date=hoy).all()
    
    total_requests = sum(s.requests_count for s in stats_hoy)
    total_errors = sum(s.errors_count for s in stats_hoy)
    total_tokens = sum(s.tokens_used for s in stats_hoy)
    
    # Calcular tasa de �xito
    total_calls = total_requests + total_errors
    success_rate = round((total_requests / total_calls * 100), 2) if total_calls > 0 else 100
    
    # Stats por key
    keys_stats = []
    for stat in stats_hoy:
        keys_stats.append(stat.to_dict())
    
    # Contar keys configuradas (verificar variables de entorno)
    import os
    total_keys_configuradas = 0
    configured_key_names = []
    for i in range(1, 5):  # Verificar hasta 4 keys
        key_env = f'GEMINI_API_KEY_{i}' if i > 1 else 'GEMINI_API_KEY'
        if os.getenv(key_env):
            total_keys_configuradas += 1
            key_name = f'GEMINI_API_KEY_{i}' if i > 1 else 'GEMINI_API_KEY_1'
            configured_key_names.append(key_name)
    
    print(f"🔑 Keys configuradas: {total_keys_configuradas}")
    print(f"🔑 Nombres: {configured_key_names}")
    print(f"🔑 Keys en BD hoy: {len(keys_stats)}")
    
    # Contar SOLO las keys configuradas que están disponibles (< 100% uso)
    available_keys = 0
    for key_name in configured_key_names:
        # Buscar esta key en las stats de hoy
        key_stat = next((k for k in keys_stats if k['key_name'] == key_name), None)
        if key_stat:
            # Si tiene stats, verificar si está disponible
            if key_stat['usage_percent'] < 100:
                available_keys += 1
        else:
            # Si no tiene stats hoy, está completamente disponible
            available_keys += 1
    
    print(f"🔑 Keys disponibles: {available_keys}")
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        'date': hoy.isoformat(),
        'summary': {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'total_tokens': total_tokens,
            'success_rate': success_rate,
            'available_keys': available_keys,
            'total_keys': total_keys_configuradas
        },
        'keys': keys_stats
    })


@admin_bp.route('/api-keys/history', methods=['GET'])
@admin_required
def get_api_keys_history():
    """Historial de uso �ltimos 7 d�as"""
    
    hoy = date.today()
    hace_7_dias = hoy - timedelta(days=7)
    
    # Obtener datos de �ltimos 7 d�as
    history = ApiKeyUsage.query.filter(
        ApiKeyUsage.date >= hace_7_dias,
        ApiKeyUsage.date <= hoy
    ).order_by(ApiKeyUsage.date.asc()).all()
    
    # Agrupar por fecha
    por_fecha = {}
    for record in history:
        fecha_str = record.date.isoformat()
        if fecha_str not in por_fecha:
            por_fecha[fecha_str] = {
                'date': fecha_str,
                'total_requests': 0,
                'total_errors': 0,
                'total_tokens': 0,
                'keys': {}
            }
        
        por_fecha[fecha_str]['total_requests'] += record.requests_count
        por_fecha[fecha_str]['total_errors'] += record.errors_count
        por_fecha[fecha_str]['total_tokens'] += record.tokens_used
        por_fecha[fecha_str]['keys'][record.key_name] = {
            'requests': record.requests_count,
            'errors': record.errors_count,
            'tokens': record.tokens_used
        }
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        'history': list(por_fecha.values())
    })


@admin_bp.route('/api-keys/current', methods=['GET'])
@admin_required
def get_api_keys_current():
    """Estado actual de las API keys"""
    
    hoy = date.today()
    stats_hoy = ApiKeyUsage.query.filter_by(date=hoy).all()
    
    # Informaci�n de keys configuradas
    import os
    keys_configuradas = []
    for i in range(1, 4):
        key_env = f'GEMINI_API_KEY_{i}' if i > 1 else 'GEMINI_API_KEY'
        if os.getenv(key_env):
            keys_configuradas.append(f'GEMINI_API_KEY_{i}')
    
    # Estado de cada key
    keys_status = []
    for key_name in keys_configuradas:
        stat = next((s for s in stats_hoy if s.key_name == key_name), None)
        
        if stat:
            total_calls = stat.requests_count + stat.errors_count
            usage_percent = round((total_calls / 20 * 100), 2)
            remaining = max(0, 20 - total_calls)
            
            status = 'available'
            if usage_percent >= 100:
                status = 'exhausted'
            elif usage_percent >= 80:
                status = 'critical'
            elif usage_percent >= 50:
                status = NotificationTypes.WARNING
            
            keys_status.append({
                'key_name': key_name,
                'status': status,
                'usage_percent': usage_percent,
                'requests_used': total_calls,
                'requests_remaining': remaining,
                'tokens_used': stat.tokens_used
            })
        else:
            # Key no usada hoy
            keys_status.append({
                'key_name': key_name,
                'status': 'available',
                'usage_percent': 0,
                'requests_used': 0,
                'requests_remaining': 20,
                'tokens_used': 0
            })
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        'keys': keys_status,
        'total_keys': len(keys_configuradas),
        'available_keys': len([k for k in keys_status if k['status'] == 'available'])
    })


# ===== DECORADOR SUPER ADMIN =====

def super_admin_required(f):
    """Decorador para verificar que el usuario es super-admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "No autenticado"}), 401
        if not getattr(current_user, 'is_super_admin', False):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Acceso denegado. Solo super-administradores."}), 403
        return f(*args, **kwargs)
    return decorated_function


# ===== GESTORIAS =====

@admin_bp.route('/gestorias', methods=['GET'])
@super_admin_required
def list_gestorias():
    """Lista todas las gestorias con metricas"""
    try:
        gestorias = Gestoria.query.order_by(Gestoria.id).all()
        
        result = []
        for g in gestorias:
            # Contar metricas
            num_empresas = Empresa.query.filter_by(gestoria_id=g.id).count()
            num_documentos = Documento.query.filter_by(gestoria_id=g.id).count()
            num_usuarios = User.query.filter_by(gestoria_id=g.id).count()
            
            result.append({
                "id": g.id,
                "nombre": g.nombre,
                "slug": g.slug,
                "email": g.email,
                "activa": g.activa,
                "plan": g.plan,
                "fecha_creacion": g.fecha_creacion.isoformat() if g.fecha_creacion else None,
                "configuracion": g.configuracion or {},
                "metricas": {
                    "empresas": num_empresas,
                    "documentos": num_documentos,
                    "usuarios": num_usuarios
                }
            })
        
        return jsonify({NotificationTypes.SUCCESS: True, "gestorias": result})
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias', methods=['POST'])
@super_admin_required
def create_gestoria():
    """Crea una nueva gestoria con su usuario administrador"""
    try:
        data = request.json
        
        # Validar campos requeridos de gestor�a
        if not data.get('nombre'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El nombre es requerido"}), 400
        if not data.get('slug'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El slug es requerido"}), 400
        
        # Validar campos requeridos de admin
        admin_data = data.get('admin', {})
        if not admin_data.get('nombre'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El nombre del administrador es requerido"}), 400
        if not admin_data.get('email'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El email del administrador es requerido"}), 400
        if not admin_data.get('password'):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "La contrase�a del administrador es requerida"}), 400
        
        # Validar formato del slug
        import re
        if not re.match(r'^[a-z0-9-]+$', data['slug']):
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El slug solo puede contener letras minusculas, numeros y guiones"}), 400
        
        # Verificar que el slug no exista
        if Gestoria.query.filter_by(slug=data['slug']).first():
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El slug ya existe"}), 400
        
        # Verificar que el email del admin no exista
        if User.query.filter_by(email=admin_data['email']).first():
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El email del administrador ya existe"}), 400
        
        from datetime import datetime
        
        # Crear gestor�a
        gestoria = Gestoria(
            nombre=data['nombre'],
            slug=data['slug'],
            email=data.get('email'),
            activa=data.get('activa', True),
            plan=data.get('plan', 'basico'),
            max_certificados=data.get('max_certificados', 5),
            configuracion=data.get('configuracion', {}),
            fecha_creacion=datetime.utcnow()
        )
        
        db.session.add(gestoria)
        db.session.flush()  # Para obtener el ID de la gestor�a
        
        # ⭐ Verificar límite de usuarios antes de crear admin
        from utils_limits import validate_gestoria_limit
        puede_crear, mensaje_error = validate_gestoria_limit(gestoria.id, 'usuarios')
        if not puede_crear:
            db.session.rollback()
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: mensaje_error}), 403

        # Crear usuario administrador
        admin_user = User(
            nombre=admin_data['nombre'],
            email=admin_data['email'],
            departamento_id=5,  # Jefatura
            gestoria_id=gestoria.id,
            activo=True
        )
        admin_user.set_password(admin_data['password'])
        
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "message": "Gestoria y usuario administrador creados exitosamente",
            "gestoria": {
                "id": gestoria.id,
                "nombre": gestoria.nombre,
                "slug": gestoria.slug
            },
            "admin": {
                "id": admin_user.id,
                "nombre": admin_user.nombre,
                "email": admin_user.email
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>', methods=['GET'])
@super_admin_required
def get_gestoria(id):
    """Obtiene detalles de una gestoria"""
    try:
        gestoria = db.session.get(Gestoria, id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestoria no encontrada"}), 404
        
        # Metricas
        num_empresas = Empresa.query.filter_by(gestoria_id=gestoria.id).count()
        num_documentos = Documento.query.filter_by(gestoria_id=gestoria.id).count()
        num_usuarios = User.query.filter_by(gestoria_id=gestoria.id).count()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "gestoria": {
                "id": gestoria.id,
                "nombre": gestoria.nombre,
                "slug": gestoria.slug,
                "email": gestoria.email,
                "activa": gestoria.activa,
                "plan": gestoria.plan,
                "fecha_creacion": gestoria.fecha_creacion.isoformat() if gestoria.fecha_creacion else None,
                "configuracion": gestoria.to_dict().get('configuracion', {}),
                "metricas": {
                    "empresas": num_empresas,
                    "documentos": num_documentos,
                    "usuarios": num_usuarios
                }
            }
        })
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>', methods=['PUT'])
@super_admin_required
def update_gestoria(id):
    """Actualiza una gestoria"""
    try:
        gestoria = db.session.get(Gestoria, id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestoria no encontrada"}), 404
        
        data = request.json
        
        if 'nombre' in data:
            gestoria.nombre = data['nombre']
        
        if 'slug' in data:
            # Validar formato
            import re
            if not re.match(r'^[a-z0-9-]+$', data['slug']):
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El slug solo puede contener letras minusculas, numeros y guiones"}), 400
            
            # Verificar que el nuevo slug no exista
            existing = Gestoria.query.filter_by(slug=data['slug']).first()
            if existing and existing.id != id:
                return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "El slug ya existe"}), 400
            gestoria.slug = data['slug']
        
        if 'email' in data:
            gestoria.email = data['email']
        
        if 'activa' in data:
            gestoria.activa = data['activa']
        
        if 'plan' in data:
            old_plan = gestoria.plan
            new_plan_codigo = data['plan']  # basico, plus, premium
            
            # ✅ USAR BILLING SERVICE PARA SINCRONIZACIÓN CENTRALIZADA
            # Esto evita hardcodes de IDs y asegura que Suscripcion, Gestoria y GestoriaPlan estén alineados
            from services.billing_service import BillingService
            
            try:
                print(f"🚀 Iniciando cambio de plan centralizado: {old_plan} -> {new_plan_codigo}")
                BillingService.cambiar_plan(
                    gestoria_id=id,
                    nuevo_plan_codigo=new_plan_codigo,
                    usuario_id=current_user.id
                )
                print(f"✅ Cambio de plan completado vía BillingService")
            except Exception as e:
                print(f"❌ Error en BillingService.cambiar_plan: {e}")
                # Fallback: al menos actualizar el campo de la gestoría si el servicio de billing falla
                gestoria.plan = new_plan_codigo
        
        if 'configuracion' in data:
            gestoria.configuracion = data['configuracion']
        
        if 'max_certificados' in data:
            gestoria.max_certificados = data['max_certificados']
        
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, "message": "Gestoria actualizada exitosamente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>', methods=['DELETE'])
@super_admin_required
def delete_gestoria(id):
    """Desactiva una gestoria (soft delete)"""
    try:
        gestoria = db.session.get(Gestoria, id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestoria no encontrada"}), 404
        
        if gestoria.id == 1:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "No se puede eliminar la gestoria principal"}), 400
        
        gestoria.activa = False
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, "message": "Gestoria desactivada exitosamente"})
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ===== USUARIOS POR GESTORIA =====

@admin_bp.route('/gestorias/<int:id>/usuarios', methods=['GET'])
@super_admin_required
def list_gestoria_users(id):
    """Lista usuarios de una gestoria"""
    try:
        gestoria = db.session.get(Gestoria, id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestoria no encontrada"}), 404
        
        usuarios = User.query.filter_by(gestoria_id=id).order_by(User.nombre).all()
        
        result = [{
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "departamento": u.departamento,
            "activo": u.activo,
            "is_super_admin": getattr(u, 'is_super_admin', False)
        } for u in usuarios]
        
        return jsonify({NotificationTypes.SUCCESS: True, "usuarios": result})
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ===== METRICAS GLOBALES =====

@admin_bp.route('/metricas-sistema', methods=['GET'])
@super_admin_required
def get_system_metrics():
    """Obtiene metricas globales del sistema"""
    try:
        total_gestorias = Gestoria.query.count()
        gestorias_activas = Gestoria.query.filter_by(activa=True).count()
        total_usuarios = User.query.count()
        total_empresas = Empresa.query.count()
        total_documentos = Documento.query.count()
        
        # Metricas por gestoria (top 5)
        top_gestorias = db.session.query(
            Gestoria.nombre,
            func.count(Empresa.id).label('num_empresas')
        ).join(Empresa, Empresa.gestoria_id == Gestoria.id, isouter=True)\
         .group_by(Gestoria.id, Gestoria.nombre)\
         .order_by(func.count(Empresa.id).desc())\
         .limit(5).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "metricas": {
                "gestorias": {
                    "total": total_gestorias,
                    "activas": gestorias_activas,
                    "inactivas": total_gestorias - gestorias_activas
                },
                "usuarios": total_usuarios,
                "empresas": total_empresas,
                "documentos": total_documentos,
                "top_gestorias": [
                    {"nombre": g[0], "empresas": g[1]} for g in top_gestorias
                ]
            }
        })
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# ============================================================================
# CONFIGURACION AVANZADA DE GESTORIAS
# ============================================================================

@admin_bp.route('/gestorias/<int:id>/upload-logo', methods=['POST'])
@super_admin_required
def upload_gestoria_logo(id):
    """
    Sube el logo de una gestor�a
    
    Form Data:
        - file: Imagen del logo (PNG, JPG, SVG)
    
    Returns:
        JSON con URL del logo
    """
    import os
    from werkzeug.utils import secure_filename
    
    try:
        gestoria = Gestoria.query.get(id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestor�a no encontrada"}), 404
        
        if 'file' not in request.files:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "No se proporcion� archivo"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Archivo vac�o"}), 400
        
        # Validar extensi�n
        allowed_extensions = {'png', 'jpg', 'jpeg', 'svg'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if ext not in allowed_extensions:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: f"Formato no permitido. Use: {', '.join(allowed_extensions)}"
            }), 400
        
        # Validar tama�o (2MB m�ximo)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 2 * 1024 * 1024:  # 2MB
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Archivo muy grande. M�ximo 2MB"
            }), 400
        
        # Crear directorio si no existe
        upload_dir = os.path.join('storage', 'logos', str(id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Guardar archivo
        filename = f"logo.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Actualizar configuraci�n
        config = gestoria.configuracion or {}
        if 'branding' not in config:
            config['branding'] = {}
        
        config['branding']['logo_url'] = f"/storage/logos/{id}/{filename}"
        gestoria.configuracion = config
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "logo_url": config['branding']['logo_url']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>/upload-favicon', methods=['POST'])
@super_admin_required
def upload_gestoria_favicon(id):
    """
    Sube el favicon de una gestor�a
    
    Form Data:
        - file: Imagen del favicon (ICO, PNG)
    
    Returns:
        JSON con URL del favicon
    """
    import os
    from werkzeug.utils import secure_filename
    
    try:
        gestoria = Gestoria.query.get(id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestor�a no encontrada"}), 404
        
        if 'file' not in request.files:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "No se proporcion� archivo"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Archivo vac�o"}), 400
        
        # Validar extensi�n
        allowed_extensions = {'ico', 'png'}
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if ext not in allowed_extensions:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: f"Formato no permitido. Use: {', '.join(allowed_extensions)}"
            }), 400
        
        # Validar tama�o (500KB m�ximo)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 500 * 1024:  # 500KB
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Archivo muy grande. M�ximo 500KB"
            }), 400
        
        # Crear directorio si no existe
        upload_dir = os.path.join('storage', 'logos', str(id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Guardar archivo
        filename = f"favicon.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Actualizar configuraci�n
        config = gestoria.configuracion or {}
        if 'branding' not in config:
            config['branding'] = {}
        
        config['branding']['favicon_url'] = f"/storage/logos/{id}/{filename}"
        gestoria.configuracion = config
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "favicon_url": config['branding']['favicon_url']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>/configuracion', methods=['PUT'])
@super_admin_required
def update_gestoria_configuracion(id):
    """
    Actualiza la configuraci�n JSON completa de una gestor�a
    
    JSON Body:
        - configuracion: Objeto JSON con configuraci�n
    
    Returns:
        JSON con success y configuraci�n actualizada
    """
    try:
        from validators.config_validator import validate_gestoria_config
        
        gestoria = Gestoria.query.get(id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestor�a no encontrada"}), 404
        
        data = request.json
        nueva_config = data.get('configuracion')
        
        if not nueva_config:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Configuraci�n requerida"}), 400
        
        # Validar configuraci�n
        is_valid, errors = validate_gestoria_config(nueva_config)
        
        if not is_valid:
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: "Configuraci�n inv�lida",
                "validation_errors": errors
            }), 400
        
        # Actualizar
        gestoria.configuracion = nueva_config
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "message": "Configuraci�n actualizada correctamente",
            "configuracion": gestoria.configuracion
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestorias/<int:id>/configuracion', methods=['GET'])
@super_admin_required
def get_gestoria_configuracion(id):
    """
    Obtiene la configuraci�n completa de una gestor�a
    
    Returns:
        JSON con configuraci�n
    """
    try:
        from validators.config_validator import get_default_config
        
        gestoria = Gestoria.query.get(id)
        if not gestoria:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: "Gestor�a no encontrada"}), 404
        
        # Si no tiene configuraci�n, retornar default
        config = gestoria.configuracion or get_default_config()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            "configuracion": gestoria.to_dict().get('configuracion', {})
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: str(e)}), 500


# =========================================================================
# ENDPOINTS DE CONFIGURACI�N SALTRA POR GESTOR�A
# =========================================================================

@admin_bp.route('/gestoria/saltra-config', methods=['GET'])
@admin_required
def get_saltra_config():
    """Obtener estado de configuraci�n SALTRA de la gestor�a actual"""
    try:
        gestoria_id = current_user.gestoria_id
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        # Usar helper para desencriptar y verificar si hay credenciales válidas
        config = gestoria.get_saltra_config_decrypted() if gestoria.configuracion else {}
        configured = bool(config.get('email') and config.get('password'))

        # No exponer las credenciales, solo el estado
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'configured': configured,
            'enabled': config.get('enabled', False)
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestoria/saltra-config', methods=['PUT'])
@admin_required
def update_saltra_config():
    """Actualizar configuracion SALTRA de la gestoria (super-admin o Jefatura)"""
    try:
        # Debug: Log del departamento del usuario
        dept_nombre = current_user.departamento.nombre if current_user.departamento else None
        print(f"🔍 DEBUG - Usuario: {current_user.nombre}")
        print(f"🔍 DEBUG - Departamento objeto: '{current_user.departamento}'")
        print(f"🔍 DEBUG - Departamento nombre: '{dept_nombre}'")
        print(f"🔍 DEBUG - Is super admin: {current_user.is_super_admin}")
        
        # Verificar que sea super-admin o Jefatura (case-insensitive)
        if not current_user.is_super_admin:
            if not current_user.departamento or current_user.departamento.nombre.lower().strip() != 'jefatura':
                return jsonify({
                    NotificationTypes.ERROR: f'Solo super-administradores o Jefatura pueden configurar SALTRA. Tu departamento: "{dept_nombre}"'
                }), 403
        
        data = request.json
        gestoria_id = current_user.gestoria_id
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        # Validar datos requeridos (solo email y password)
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        cert_secret = data.get('cert_secret', '').strip()  # Opcional
        enabled = data.get('enabled', True)
        
        if not email or not password:
            return jsonify({NotificationTypes.ERROR: 'Email y Password son requeridos'}), 400
        
        # VALIDAR CREDENCIALES: Intentar login a SALTRA (sin cert_secret)
        import requests
        
        try:
            login_response = requests.post(
                'https://api.saltra.es/api/v4/auth/login',
                json={'email': email, 'password': password},
                timeout=30
            )
            
            login_data = login_response.json()
            
            if not login_data.get('success'):
                error_msg = login_data.get('message', 'Credenciales inválidas')
                return jsonify({
                    NotificationTypes.ERROR: f'Credenciales inválidas: {error_msg}'
                }), 400
                
        except Exception as e:
            return jsonify({
                NotificationTypes.ERROR: f'Error al validar credenciales: {str(e)}'
            }), 400
        
        # Si llegamos aquí, las credenciales son válidas
        # Guardar con encriptación Fernet usando el helper del modelo
        if not gestoria.configuracion:
            gestoria.configuracion = {}

        gestoria.set_saltra_config(
            email=email,
            password=password,
            cert_secret=cert_secret or '',
            enabled=enabled
        )

        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': 'Configuraci�n SALTRA actualizada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/gestoria/saltra-config', methods=['DELETE'])
@admin_required
def delete_saltra_config():
    """Eliminar configuraci�n SALTRA de la gestor�a (solo super-admin)"""
    try:
        # Verificar que sea super-admin
        if not current_user.is_super_admin:
            return jsonify({NotificationTypes.ERROR: 'Solo super-administradores pueden eliminar configuraci�n SALTRA'}), 403
        
        gestoria_id = current_user.gestoria_id
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        # Eliminar configuraci�n SALTRA
        if gestoria.configuracion and 'saltra' in gestoria.configuracion:
            del gestoria.configuracion['saltra']
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(gestoria, 'configuracion')
            
            db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': 'Configuraci�n SALTRA eliminada'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
# Agregar al final de routes_admin.py

@admin_bp.route('/gestoria/<int:gestoria_id>/saltra-status', methods=['GET'])
@admin_required
def get_gestoria_saltra_status(gestoria_id):
    """Obtener estado de configuración SALTRA de una gestoría específica (super-admin)"""
    try:
        # Solo super-admin puede ver estado de otras gestorías
        if not current_user.is_super_admin and current_user.gestoria_id != gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'No autorizado'}), 403
        
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        if not gestoria.configuracion or not gestoria.configuracion.get('saltra'):
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'configured': False,
                'enabled': False
            })
        
        saltra_config = gestoria.configuracion['saltra']
        has_credentials = bool(saltra_config.get('email') and saltra_config.get('password'))
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'configured': has_credentials,
            'enabled': saltra_config.get('enabled', False)
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@admin_bp.route('/gestoria/<int:gestoria_id>/saltra-config', methods=['PUT'])
@admin_required
def update_gestoria_saltra_config(gestoria_id):
    """Actualizar configuración SALTRA de una gestoría específica (solo super-admin)"""
    try:
        # Solo super-admin puede configurar otras gestorías
        if not current_user.is_super_admin:
            return jsonify({NotificationTypes.ERROR: 'Solo super-administradores pueden configurar SALTRA de otras gestorías'}), 403
        
        data = request.json
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        
        # Validar datos requeridos (email y password para login)
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        enabled = data.get('enabled', True)
        
        if not email or not password:
            return jsonify({NotificationTypes.ERROR: 'Email y Password son requeridos'}), 400
        
        # Actualizar configuración
        if not gestoria.configuracion:
            gestoria.configuracion = {}
        
        gestoria.configuracion['saltra'] = {
            'email': email,
            'password': password,
            'enabled': enabled
        }
        
        # Marcar como modificado (necesario para JSONB)
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(gestoria, 'configuracion')
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': f'Configuración SALTRA actualizada para {gestoria.nombre}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@admin_bp.route('/saltra/validate-credentials', methods=['POST'])
@login_required
def validate_saltra_credentials():
    """Validar credenciales SALTRA y obtener cert_secret"""
    try:
        data = request.json
        print(f"🔍 DEBUG - Request data: {data}")
        print(f"🔍 DEBUG - Request headers: {dict(request.headers)}")
        
        email = data.get('email', '').strip() if data else ''
        password = data.get('password', '').strip() if data else ''
        
        print(f"🔍 DEBUG - Email: '{email}'")
        print(f"🔍 DEBUG - Password length: {len(password)}")
        
        if not email or not password:
            print(f"❌ DEBUG - Validation failed: email={bool(email)}, password={bool(password)}")
            return jsonify({NotificationTypes.ERROR: 'Email y Password son requeridos'}), 400
        
        # Validar con SALTRA
        import requests
        
        try:
            # Hacer login para validar credenciales
            print(f"🔑 DEBUG - Intentando login a SALTRA...")
            login_response = requests.post(
                'https://api.saltra.es/api/v4/auth/login',
                json={'email': email, 'password': password},
                timeout=30
            )
            
            print(f"📊 DEBUG - Login status code: {login_response.status_code}")
            
            login_data = login_response.json()
            
            if not login_data.get(NotificationTypes.SUCCESS):
                error_msg = login_data.get('message', 'Credenciales inválidas')
                print(f"❌ DEBUG - Login fallido: {error_msg}")
                return jsonify({NotificationTypes.ERROR: f'Login fallido: {error_msg}'}), 400
            
            # Credenciales válidas
            print(f"✅ DEBUG - Credenciales validadas correctamente!")
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': 'Credenciales validadas correctamente. Ahora ingresa tu cert-secret manualmente.'
            })
                
        except requests.exceptions.RequestException as e:
            return jsonify({NotificationTypes.ERROR: f'Error al conectar con SALTRA: {str(e)}'}), 400
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@admin_bp.route('/saltra/logout', methods=['POST'])
@login_required
def logout_saltra():
    """Eliminar credenciales SALTRA de la gestoría"""
    try:
        # Verificar permisos
        if not current_user.is_super_admin and current_user.departamento.nombre.lower().strip() != 'jefatura':
            return jsonify({NotificationTypes.ERROR: 'No tienes permisos para modificar SALTRA'}), 403
        
        gestoria_id = current_user.gestoria_id
        gestoria = Gestoria.query.get(gestoria_id)
        
        if not gestoria:
            return jsonify({NotificationTypes.ERROR: 'Gestoría no encontrada'}), 404
        
        # Eliminar configuración SALTRA
        if gestoria.configuracion is None:
            gestoria.configuracion = {}
        
        gestoria.configuracion['saltra'] = {
            'enabled': False,
            'email': None,
            'password': None,
            'cert_secret': None
        }
        
        # IMPORTANTE: Marcar como modificado para que SQLAlchemy detecte el cambio en JSONB
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(gestoria, 'configuracion')
        
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': 'Sesión de SALTRA cerrada correctamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Endpoint para importar empresas desde Excel/CSV
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Endpoint para previsualizar importación de empresas desde Excel/CSV
"""

@admin_bp.route('/empresas/preview-excel', methods=['POST'])
@login_required
def preview_empresas_excel():
    """
    Previsualiza empresas desde archivo Excel o CSV SIN guardar en BD
    Requiere: rol Jefatura o super-admin
    
    Retorna datos parseados con validaciones para revisión del usuario
    """
    try:
        # Verificar permisos
        if not current_user.is_super_admin:
            if not current_user.departamento or current_user.departamento.nombre.lower() != 'jefatura':
                return jsonify({NotificationTypes.ERROR: 'No tienes permisos para importar empresas'}), 403
        
        # Verificar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({NotificationTypes.ERROR: 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({NotificationTypes.ERROR: 'Nombre de archivo vacío'}), 400
        
        # Validar extensión
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if ext not in ['xlsx', 'csv']:
            return jsonify({NotificationTypes.ERROR: 'Formato no soportado. Use .xlsx o .csv'}), 400
        
        # Parsear archivo
        import pandas as pd
        from io import BytesIO
        
        try:
            if ext == 'xlsx':
                df = pd.read_excel(BytesIO(file.read()), engine='openpyxl')
            else:  # csv
                df = pd.read_csv(BytesIO(file.read()))
        except Exception as e:
            return jsonify({NotificationTypes.ERROR: f'Error leyendo archivo: {str(e)}'}), 400
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas (aceptar variaciones)
        has_nif = 'nif' in df.columns or 'nif-nie-cif' in df.columns or 'cif' in df.columns
        has_nombre = 'nombre' in df.columns or 'nombre sociedad' in df.columns
        
        if not has_nif or not has_nombre:
            return jsonify({
                NotificationTypes.ERROR: 'El archivo debe tener las columnas: NIF (o NIF-NIE-CIF), y Nombre Sociedad'
            }), 400
            
        # Normalizar columna NIF
        if 'nif-nie-cif' in df.columns and 'nif' not in df.columns:
            df['nif'] = df['nif-nie-cif']
        elif 'cif' in df.columns and 'nif' not in df.columns:
            df['nif'] = df['cif']
        
        # Normalizar columna nombre si es 'nombre sociedad'
        if 'nombre sociedad' in df.columns and 'nombre' not in df.columns:
            df['nombre'] = df['nombre sociedad']
        
        # Limitar a 500 empresas
        if len(df) > 500:
            return jsonify({
                NotificationTypes.ERROR: f'Máximo 500 empresas por archivo. Tu archivo tiene {len(df)} filas'
            }), 400
        
        # Importar validador de NIF
        # Importar validador de NIF (evitar conflicto con validators.py)
        import sys
        import os
        validators_path = os.path.join(os.path.dirname(__file__), 'validators')
        if validators_path not in sys.path:
            sys.path.insert(0, validators_path)
        from nif_validator import validar_nif_espanol, normalizar_nif
        
        # Función auxiliar para parsear valores múltiples
        def parse_multiple_values(value):
            """Convierte string separado por ; en lista"""
            if pd.isna(value) or not str(value).strip():
                return []
            return [v.strip() for v in str(value).split(';') if v.strip()]
        
        # Procesar empresas (PREVIEW - sin guardar)
        gestoria_id = current_user.gestoria_id
        datos_preview = []
        
        for idx, row in df.iterrows():
            fila_num = idx + 2  # +2 porque idx empieza en 0 y hay header
            
            validacion = {
                'valido': True,
                'errores': [],
                'advertencias': []
            }
            
            # Helper para limpiar decimales de Excel (ej: 631.0 -> 631)
            def clean_excel_val(val):
                if pd.isna(val) or not str(val).strip(): return ''
                s = str(val).strip()
                if s.endswith('.0'): s = s[:-2]
                return s

            try:
                # Extraer datos básicos
                nif_raw = str(row.get('nif', row.get('nif-nie-cif', ''))).strip() if pd.notna(row.get('nif', row.get('nif-nie-cif'))) else ''
                nombre = str(row.get('nombre', row.get('nombre sociedad', ''))).strip() if pd.notna(row.get('nombre', row.get('nombre sociedad'))) else ''
                email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None
                
                # Extraer nuevos campos planos
                codigo_empresa = clean_excel_val(row.get('codigo empresa'))
                telefono = clean_excel_val(row.get('telefono', row.get('teléfono', '')))
                cuenta_cotizacion = clean_excel_val(row.get('cuenta cotización', row.get('cuenta cotizacion', row.get('ccc', ''))))
                
                apellido_administrador = str(row.get('apellido administrador', '')).strip() if pd.notna(row.get('apellido administrador')) else None
                nif_administrador = str(row.get('nif-nie-cif administrador', '')).strip() if pd.notna(row.get('nif-nie-cif administrador')) else None
                provincia = clean_excel_val(row.get('provincia'))
                municipio = clean_excel_val(row.get('municipio'))
                codigo_postal = clean_excel_val(row.get('código postal', row.get('codigo postal', row.get('cp', ''))))
                direccion = clean_excel_val(row.get('dirección', row.get('direccion', row.get('direccion sociedad', ''))))
                convenio_numero = clean_excel_val(row.get('convenio colectivo número', row.get('convenio colectivo numero', row.get('convenio numero', ''))))
                convenio_nombre = str(row.get('convenio colectivo nombre', '')).strip() if pd.notna(row.get('convenio colectivo nombre')) else None
                
                # Campos que también van a JSON (Compatibilidad)
                direccion_centros_trabajo_str = clean_excel_val(row.get('dirección centros trabajo', row.get('direccion centros trabajo', '')))
                epigrafe_iae_str = clean_excel_val(row.get('epígrafe iae', row.get('epigrafe iae', '')))
                cnae_2009_str = clean_excel_val(row.get('cnae 2009', ''))
                cnae_2025_str = clean_excel_val(row.get('cnae 2025', ''))
                
                # Administradores (Mantiene compatibilidad con JSON list si hay varios separados por ;)
                nombres_admins = parse_multiple_values(row.get('nombre administrador'))
                apellidos_admins = parse_multiple_values(row.get('apellido administrador'))
                cifs_admins = parse_multiple_values(row.get('nif-nie-cif administrador', row.get('cif administrador')))
                
                administradores = []
                max_len = max(len(nombres_admins), len(apellidos_admins), len(cifs_admins))
                for i in range(max_len):
                    admin = {}
                    if i < len(nombres_admins):
                        admin['nombre'] = nombres_admins[i]
                    if i < len(apellidos_admins):
                        admin['apellido'] = apellidos_admins[i]
                    if i < len(cifs_admins):
                        admin['cif'] = cifs_admins[i]
                    if admin:
                        administradores.append(admin)
                
                # Extraer campos múltiples para los campos JSON originales
                direcciones_sociedad = parse_multiple_values(row.get('dirección', row.get('direccion', row.get('direccion sociedad'))))
                direcciones_centros_trabajo = parse_multiple_values(direccion_centros_trabajo_str)
                epigrafes_iae = parse_multiple_values(epigrafe_iae_str)
                cnaes_2009 = parse_multiple_values(cnae_2009_str)
                cnaes_2025 = parse_multiple_values(cnae_2025_str)
                
                # Validar NIF
                es_actualizacion = False
                conflictos = []
                empresa_id_actualizar = None
                
                if not nif_raw:
                    validacion['errores'].append('NIF vacío')
                    validacion['valido'] = False
                else:
                    nif = normalizar_nif(nif_raw)
                    
                    if not validar_nif_espanol(nif):
                        validacion['errores'].append('NIF inválido')
                        validacion['valido'] = False
                    else:
                        # Verificar si ya existe en BD
                        empresa_existente = Empresa.query.filter_by(nif=nif).first()
                        if empresa_existente:
                            if empresa_existente.gestoria_id == gestoria_id:
                                es_actualizacion = True
                                empresa_id_actualizar = empresa_existente.id
                                
                                # Función auxiliar para limpiar y comparar
                                def val(v): return str(v).strip() if pd.notna(v) and v else ''
                                
                                # Comparar campos de texto
                                campos_a_revisar = [
                                    ('nombre', 'Nombre Sociedad', nombre, val(empresa_existente.nombre)),
                                    ('email', 'Email', email, val(empresa_existente.email)),
                                    ('telefono', 'Teléfono', telefono, val(empresa_existente.telefono)),
                                    ('codigo_empresa', 'Código Empresa', codigo_empresa, val(empresa_existente.codigo_empresa)),
                                    ('cuenta_cotizacion', 'Cuenta Cotización', cuenta_cotizacion, val(empresa_existente.cuenta_cotizacion)),
                                    ('provincia', 'Provincia', provincia, val(empresa_existente.provincia)),
                                    ('municipio', 'Municipio', municipio, val(empresa_existente.municipio)),
                                    ('codigo_postal', 'Código Postal', codigo_postal, val(empresa_existente.codigo_postal)),
                                    ('direccion', 'Dirección', direccion, val(empresa_existente.direccion)),
                                    ('convenio_numero', 'Convenio Nº', convenio_numero, val(empresa_existente.convenio_numero)),
                                    ('convenio_nombre', 'Convenio Nombre', convenio_nombre, val(empresa_existente.convenio_nombre)),
                                    ('direccion_centros_trabajo_str', 'Centros de Trabajo', direccion_centros_trabajo_str, val(empresa_existente.direccion_centros_trabajo_str)),
                                    ('epigrafe_iae_str', 'Epígrafe IAE', epigrafe_iae_str, val(empresa_existente.epigrafe_iae_str)),
                                    ('cnae_2009_str', 'CNAE 2009', cnae_2009_str, val(empresa_existente.cnae_2009_str)),
                                    ('cnae_2025_str', 'CNAE 2025', cnae_2025_str, val(empresa_existente.cnae_2025_str)),
                                    ('nombre_administrador', 'Nombre Administrador', '; '.join(nombres_admins), val(empresa_existente.nombre_administrador)),
                                    ('apellido_administrador', 'Apellidos Administrador', '; '.join(apellidos_admins), val(empresa_existente.apellido_administrador)),
                                    ('nif_administrador', 'NIF Administrador', '; '.join(cifs_admins), val(empresa_existente.nif_administrador)),
                                ]
                                
                                for campo_key, label, nuevo, actual in campos_a_revisar:
                                    nuevo_limpio = val(nuevo)
                                    if nuevo_limpio and nuevo_limpio != actual:
                                        conflictos.append({
                                            'campo': campo_key,
                                            'label': label,
                                            'valor_actual': actual,
                                            'valor_nuevo': nuevo_limpio
                                        })
                                
                                # JSON Arrays (Direcciones, epigrafes, cnaes, administradores) logica simple: si hay nuevos en excel, sobrescribe.
                                if length_admins := len(administradores):
                                    # Very basic check: just alert that excel has N admins and DB has M. Let user choose which list to keep entirely.
                                    db_admins = val(len(empresa_existente.administradores) if empresa_existente.administradores else 0)
                                    if str(length_admins) != str(db_admins):
                                        pass # Handled by flat fields anyway, or user accepts wholesale replacement.
                                        
                                if conflictos:
                                    validacion['advertencias'].append(f'La empresa existe. Se encontraron {len(conflictos)} diferencias para actualizar.')
                                else:
                                    validacion['advertencias'].append(f'La empresa ya existe. Sin datos nuevos para actualizar.')
                            else:
                                validacion['errores'].append(f'NIF ya existe (Gestoría ID: {empresa_existente.gestoria_id})')
                                validacion['valido'] = False
                
                # Validar nombre

                if not nombre:
                    validacion['errores'].append('Nombre vacío')
                    validacion['valido'] = False
                
                # Validar email si se proporciona
                if email:
                    import re
                    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_regex, email):
                        validacion['errores'].append(f'Email inválido: {email}')
                        validacion['valido'] = False
                
                # Verificar codigo_empresa único por gestoría
                if codigo_empresa:
                    empresa_codigo_existente = Empresa.query.filter_by(
                        codigo_empresa=codigo_empresa,
                        gestoria_id=gestoria_id
                    ).first()
                    
                    if empresa_codigo_existente and (not es_actualizacion or empresa_codigo_existente.id != empresa_id_actualizar):
                        validacion['errores'].append('Codigo Empresa ya existe en esta gestoría y pertenece a otra empresa')
                        validacion['valido'] = False
                
                # Agregar a datos de preview
                datos_preview.append({
                    'fila': fila_num,
                    'es_actualizacion': es_actualizacion,
                    'empresa_id_actualizar': empresa_id_actualizar,
                    'conflictos': conflictos,
                    'codigo_empresa': codigo_empresa or '',
                    'nif': nif_raw,
                    'nombre': nombre,
                    'email': email or '',
                    'telefono': telefono or '',
                    'cuenta_cotizacion': cuenta_cotizacion or '',
                    'administradores': administradores,
                    'apellido_administrador': apellido_administrador or '',
                    'nif_administrador': nif_administrador or '',
                    'provincia': provincia or '',
                    'municipio': municipio or '',
                    'codigo_postal': codigo_postal or '',
                    'direccion': direccion or '',
                    'direccion_centros_trabajo_str': direccion_centros_trabajo_str or '',
                    'convenio_numero': convenio_numero or '',
                    'convenio_nombre': convenio_nombre or '',
                    'epigrafe_iae_str': epigrafe_iae_str or '',
                    'cnae_2009_str': cnae_2009_str or '',
                    'cnae_2025_str': cnae_2025_str or '',
                    'direcciones_sociedad': direcciones_sociedad,
                    'direcciones_centros_trabajo': direcciones_centros_trabajo,
                    'epigrafes_iae': epigrafes_iae,
                    'cnaes_2009': cnaes_2009,
                    'cnaes_2025': cnaes_2025,
                    'validacion': validacion
                })
                
            except Exception as e:
                datos_preview.append({
                    'fila': fila_num,
                    'codigo_empresa': '',
                    'nif': nif_raw if 'nif_raw' in locals() else 'N/A',
                    'nombre': '',
                    'email': '',
                    'telefono': '',
                    'cuenta_cotizacion': '',
                    'administradores': [],
                    'direcciones_sociedad': [],
                    'direcciones_centros_trabajo': [],
                    'epigrafes_iae': [],
                    'cnaes_2009': [],
                    'cnaes_2025': [],
                    'validacion': {
                        'valido': False,
                        'errores': [str(e)],
                        'advertencias': []
                    }
                })
        
        # Contar válidos
        validos = sum(1 for d in datos_preview if d['validacion']['valido'])
        invalidos = len(datos_preview) - validos
        
        # Preparar respuesta
        response_data = {
            NotificationTypes.SUCCESS: True,
            'total': len(datos_preview),
            'validos': validos,
            'invalidos': invalidos,
            'datos': datos_preview
        }
        
        print(f"📊 Preview generado: {validos} válidos, {invalidos} inválidos de {len(datos_preview)} total")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ Error en preview Excel: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            NotificationTypes.ERROR: f'Error inesperado: {str(e)}'
        }), 500


@admin_bp.route('/empresas/importar-excel', methods=['POST'])
@login_required
def importar_empresas_excel():
    """
    Importa empresas desde archivo Excel o CSV
    Requiere: rol Jefatura o super-admin
    
    Formato esperado:
    - Columnas: NIF-NIE-CIF, Nombre Sociedad, Email, Telefono, etc.
    - Formatos: .xlsx, .csv
    - Máximo: 500 empresas por archivo
    """
    try:
        # Verificar permisos
        if not current_user.is_super_admin:
            if not current_user.departamento or current_user.departamento.nombre.lower() != 'jefatura':
                return jsonify({NotificationTypes.ERROR: 'No tienes permisos para importar empresas'}), 403
        
        # Verificar que se envio un archivo
        if 'file' not in request.files:
            return jsonify({NotificationTypes.ERROR: 'No se envio ningun archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({NotificationTypes.ERROR: 'Nombre de archivo vacio'}), 400
        
        # Parsear resoluciones de conflictos
        import json
        resoluciones_str = request.form.get('resoluciones', '{}')
        try:
            resoluciones = json.loads(resoluciones_str)
        except Exception as e:
            print(f"Error parseando resoluciones: {e}")
            resoluciones = {}
        
        # Validar extensión
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if ext not in ['xlsx', 'csv']:
            return jsonify({NotificationTypes.ERROR: 'Formato no soportado. Use .xlsx o .csv'}), 400
        
        # Parsear archivo
        import pandas as pd
        from io import BytesIO
        
        try:
            if ext == 'xlsx':
                df = pd.read_excel(BytesIO(file.read()), engine='openpyxl')
            else:  # csv
                df = pd.read_csv(BytesIO(file.read()))
        except Exception as e:
            return jsonify({NotificationTypes.ERROR: f'Error leyendo archivo: {str(e)}'}), 400
        
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.lower()
        
        # Validar columnas requeridas (aceptar variaciones)
        has_nif = any(col in df.columns for col in ['nif', 'nif-nie-cif', 'cif', 'nif-nie-cif administrador'])
        # Consideramos valido si tiene 'nif' tras normalizacion manual
        if 'nif-nie-cif' in df.columns: has_nif = True
        
        has_nombre = 'nombre' in df.columns or 'nombre sociedad' in df.columns
        
        if not has_nif or not has_nombre:
            return jsonify({
                NotificationTypes.ERROR: 'El archivo debe tener las columnas: NIF (o NIF-NIE-CIF), y Nombre Sociedad'
            }), 400
            
        # Normalizar columna NIF
        if 'nif-nie-cif' in df.columns and 'nif' not in df.columns:
            df['nif'] = df['nif-nie-cif']
        elif 'cif' in df.columns and 'nif' not in df.columns:
            df['nif'] = df['cif']
        
        # Normalizar columna nombre si es 'nombre sociedad'
        if 'nombre sociedad' in df.columns and 'nombre' not in df.columns:
            df['nombre'] = df['nombre sociedad']
        
        # Limitar a 500 empresas
        if len(df) > 500:
            return jsonify({
                NotificationTypes.ERROR: f'Maximo 500 empresas por archivo. Tu archivo tiene {len(df)} filas'
            }), 400
        
        # Importar validador de NIF
        import sys
        import os
        validators_path = os.path.join(os.path.dirname(__file__), 'validators')
        if validators_path not in sys.path:
            sys.path.insert(0, validators_path)
        from nif_validator import validar_nif_espanol, normalizar_nif
        
        # Procesar empresas
        gestoria_id = current_user.gestoria_id

        def parse_multiple_values(value):
            """Convierte string separado por ; en lista"""
            if pd.isna(value) or not str(value).strip():
                return []
            return [v.strip() for v in str(value).split(';') if v.strip()]

        exitosos = []
        actualizados = []
        duplicados = []
        errores = []
        
        for idx, row in df.iterrows():
            fila_num = idx + 2  # +2 porque idx empieza en 0 y hay header
            
            try:
                # ⭐ CRITICAL FIX: begin_nested() permite que si falla una fila, solo se revierta esa operacion específica
                with db.session.begin_nested():
                    # Función para limpiar decimales de Excel (ej: 933.0 -> 933)
                    def clean_excel_val(val):
                        if pd.isna(val) or not str(val).strip(): return ''
                        s = str(val).strip()
                        if s.endswith('.0'): s = s[:-2]
                        return s

                    # Extraer datos con fallbacks consistentes para tildes (archivo del usuario tiene 'Dirección', 'Cuenta Cotización', etc.)
                    nif_raw = clean_excel_val(row.get('nif-nie-cif', row.get('nif', row.get('cif', ''))))
                    nombre = str(row.get('nombre sociedad', row.get('nombre', ''))).strip() if pd.notna(row.get('nombre sociedad', row.get('nombre'))) else ''
                    email = str(row.get('email', '')).strip() if pd.notna(row.get('email')) else None
                    codigo_empresa = clean_excel_val(row.get('codigo empresa', ''))
                    telefono = clean_excel_val(row.get('telefono', row.get('teléfono', '')))
                    cuenta_cotizacion = clean_excel_val(row.get('cuenta cotización', row.get('cuenta cotizacion', row.get('ccc', ''))))
                    
                    nombres_admins = parse_multiple_values(row.get('nombre administrador', row.get('nombre administrador', '')))
                    apellidos_admins = parse_multiple_values(row.get('apellido administrador', ''))
                    cifs_admins = parse_multiple_values(row.get('nif-nie-cif administrador', row.get('cif administrador', '')))
                    
                    # Provincias, Municipios, Códigos Postales
                    provincia = clean_excel_val(row.get('provincia'))
                    municipio = clean_excel_val(row.get('municipio'))
                    codigo_postal = clean_excel_val(row.get('código postal', row.get('codigo postal', row.get('cp', ''))))
                    direccion = clean_excel_val(row.get('dirección', row.get('direccion', row.get('direccion sociedad', ''))))
                    
                    convenio_numero = clean_excel_val(row.get('convenio colectivo número', row.get('convenio colectivo numero', row.get('convenio numero', ''))))
                    convenio_nombre = clean_excel_val(row.get('convenio colectivo nombre', row.get('convenio nombre', '')))
                    direccion_centros_trabajo_str = clean_excel_val(row.get('dirección centros trabajo', row.get('direccion centros trabajo', '')))

                    administradores = []
                    max_len = max(len(nombres_admins), len(apellidos_admins), len(cifs_admins))
                    for i in range(max_len):
                        admin = {}
                        if i < len(nombres_admins): admin['nombre'] = nombres_admins[i]
                        if i < len(apellidos_admins): admin['apellido'] = apellidos_admins[i]
                        if i < len(cifs_admins): admin['cif'] = cifs_admins[i]
                        if admin: administradores.append(admin)
                    
                    # Campos múltiples para JSON
                    direcciones_sociedad = [clean_excel_val(v) for v in parse_multiple_values(row.get('dirección', row.get('direccion', row.get('direccion sociedad', ''))))]
                    direcciones_centros_trabajo = [clean_excel_val(v) for v in parse_multiple_values(row.get('dirección centros trabajo', row.get('direccion centros trabajo', '')))]
                    epigrafes_iae = [clean_excel_val(v) for v in parse_multiple_values(row.get('epígrafe iae', row.get('epigrafe iae', '')))]
                    cnaes_2009 = [clean_excel_val(v) for v in parse_multiple_values(row.get('cnae 2009'))]
                    cnaes_2025 = [clean_excel_val(v) for v in parse_multiple_values(row.get('cnae 2025'))]
                    
                    # Epigrafe strings planos
                    epigrafe_iae_str = clean_excel_val(row.get('epígrafe iae', row.get('epigrafe iae', '')))
                    cnae_2009_str = clean_excel_val(row.get('cnae 2009', ''))
                    cnae_2025_str = clean_excel_val(row.get('cnae 2025', ''))

                    # Validaciones básicas
                    if not nif_raw:
                        errores.append({'fila': fila_num, 'nif': nif_raw, NotificationTypes.ERROR: 'NIF vacio'})
                        continue
                    
                    nif = normalizar_nif(nif_raw)
                    if not validar_nif_espanol(nif):
                        errores.append({'fila': fila_num, 'nif': nif_raw, NotificationTypes.ERROR: 'NIF invalido'})
                        continue
                    
                    if not nombre:
                        errores.append({'fila': fila_num, 'nif': nif, NotificationTypes.ERROR: 'Nombre vacio'})
                        continue

                    # Buscar si existe
                    empresa_existente = Empresa.query.filter_by(nif=nif).first()
                    
                    if empresa_existente:
                        if empresa_existente.gestoria_id == gestoria_id:
                            # Actualización
                            res_fila = resoluciones.get(str(fila_num), {})
                            cambios = False
                            
                            def update_if_new(db_attr, val_xlsx, res_key):
                                res = res_fila.get(res_key, 'nuevo')
                                if res == 'nuevo' and pd.notna(val_xlsx) and str(val_xlsx).strip():
                                    curr = getattr(empresa_existente, db_attr)
                                    val_s = str(val_xlsx).strip()
                                    if str(curr or "").strip() != val_s:
                                        setattr(empresa_existente, db_attr, val_s)
                                        return True
                                return False

                            if update_if_new('nombre', nombre, 'nombre'): cambios = True
                            if update_if_new('email', email, 'email'): cambios = True
                            if update_if_new('telefono', telefono, 'telefono'): cambios = True
                            if update_if_new('codigo_empresa', codigo_empresa, 'codigo_empresa'): cambios = True
                            if update_if_new('cuenta_cotizacion', cuenta_cotizacion, 'cuenta_cotizacion'): cambios = True
                            if update_if_new('provincia', provincia, 'provincia'): cambios = True
                            if update_if_new('municipio', municipio, 'municipio'): cambios = True
                            if update_if_new('codigo_postal', codigo_postal, 'codigo_postal'): cambios = True
                            if update_if_new('direccion', direccion, 'direccion'): cambios = True
                            if update_if_new('convenio_numero', convenio_numero, 'convenio_numero'): cambios = True
                            if update_if_new('convenio_nombre', convenio_nombre, 'convenio_nombre'): cambios = True
                            if update_if_new('direccion_centros_trabajo_str', direccion_centros_trabajo_str, 'direccion_centros_trabajo_str'): cambios = True
                            if update_if_new('epigrafe_iae_str', epigrafe_iae_str, 'epigrafe_iae_str'): cambios = True
                            if update_if_new('cnae_2009_str', cnae_2009_str, 'cnae_2009_str'): cambios = True
                            if update_if_new('cnae_2025_str', cnae_2025_str, 'cnae_2025_str'): cambios = True
                            
                            # Administradores planos (unificando con separador ; si vienen varios en Excel)
                            if nombres_admins:
                                if update_if_new('nombre_administrador', '; '.join(nombres_admins), 'nombre_administrador'): cambios = True
                            if apellidos_admins:
                                if update_if_new('apellido_administrador', '; '.join(apellidos_admins), 'apellido_administrador'): cambios = True
                            if cifs_admins:
                                if update_if_new('nif_administrador', '; '.join(cifs_admins), 'nif_administrador'): cambios = True
                            
                            from sqlalchemy.orm.attributes import flag_modified
                            if administradores and res_fila.get('administradores', 'nuevo') == 'nuevo':
                                empresa_existente.administradores = administradores
                                flag_modified(empresa_existente, 'administradores')
                                cambios = True
                            
                            if cambios:
                                db.session.add(empresa_existente)
                                db.session.flush() # Validar contra DB
                                actualizados.append({'fila': fila_num, 'nif': nif, 'nombre': nombre, 'email': email or 'Sin email'})
                            continue
                        else:
                            duplicados.append({'fila': fila_num, 'nif': nif, 'nombre': nombre, 'razon': f'NIF pertenece a Gestoría ID {empresa_existente.gestoria_id}'})
                            continue

                    # Crear nueva empresa
                    nueva = Empresa(
                        nif=nif, nombre=nombre, email=email, gestoria_id=gestoria_id,
                        codigo_empresa=codigo_empresa, telefono=telefono, cuenta_cotizacion=cuenta_cotizacion,
                        administradores=administradores, provincia=provincia, municipio=municipio,
                        codigo_postal=codigo_postal, direccion=direccion,
                        direccion_centros_trabajo_str=direccion_centros_trabajo_str,
                        convenio_numero=convenio_numero, convenio_nombre=convenio_nombre,
                        epigrafe_iae_str=epigrafe_iae_str, cnae_2009_str=cnae_2009_str, cnae_2025_str=cnae_2025_str,
                        direcciones_sociedad=direcciones_sociedad, direcciones_centros_trabajo=direcciones_centros_trabajo,
                        epigrafes_iae=epigrafes_iae, cnaes_2009=cnaes_2009, cnaes_2025=cnaes_2025,
                        # Campos de administrador planos
                        nombre_administrador='; '.join(nombres_admins) if nombres_admins else None,
                        apellido_administrador='; '.join(apellidos_admins) if apellidos_admins else None,
                        nif_administrador='; '.join(cifs_admins) if cifs_admins else None
                    )
                    db.session.add(nueva)
                    db.session.flush()
                    exitosos.append({'fila': fila_num, 'nif': nif, 'nombre': nombre, 'email': email or 'Sin email'})
                    
            except Exception as e:
                # begin_nested() asegura el rollback local. Registramos el error.
                errores.append({'fila': fila_num, 'nif': nif_raw if 'nif_raw' in locals() else 'N/A', NotificationTypes.ERROR: str(e)})
                current_app.logger.error(f"Error procesando fila {fila_num} del importador: {e}")
                continue
        
        # Todas las operaciones válidas se confirman aquí
        try:
            db.session.commit()
            print(f"✅ Importación completada: {len(exitosos)} nuevas, {len(actualizados)} actualizadas, {len(errores)} errores")
        except Exception as e:
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: f'Error en guardado final: {str(e)}'}), 500
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'total': len(df),
            'exitosas': len(exitosos),
            'actualizadas': len(actualizados),
            'duplicadas': len(duplicados),
            'errores': len(errores),
            'detalles': {
                'duplicados': duplicados[:10],
                'errores': errores[:10]
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            NotificationTypes.ERROR: f'Error inesperado: {str(e)}'
        }), 500


@admin_bp.route('/empresas/plantilla-excel', methods=['GET'])
@login_required
def descargar_plantilla_excel():
    """
    Descarga plantilla Excel de ejemplo para importar empresas
    """
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Crear DataFrame de ejemplo con los 19 campos solicitados en el orden exacto
        df = pd.DataFrame({
            'Codigo Empresa': ['EMP001', 'EMP002', 'EMP003'],
            'NIF-NIE-CIF': ['B12345678', 'A87654321', '12345678Z'],
            'Nombre Sociedad': ['Empresa Ejemplo SL', 'Otra Empresa SA', 'Autonomo Ejemplo'],
            'Email': ['info@ejemplo.com', 'contacto@otra.com', ''],
            'Telefono': ['912345678', '934567890', ''],
            'Nombre Administrador': ['Juan', 'Maria', 'Pedro'],
            'Apellido Administrador': ['Perez Garcia', 'Garcia Lopez', 'Lopez Martinez'],
            'NIF-NIE-CIF ADMINISTRADOR': ['11223344X', '22334455Y', '33445566Z'],
            'Provincia': ['Madrid', 'Barcelona', 'Valencia'],
            'Municipio': ['Madrid', 'Barcelona', 'Valencia'],
            'Código Postal': ['28001', '08019', '46001'],
            'Dirección': ['Calle Mayor 1', 'Av. Diagonal 100', 'Plaza Espana 5'],
            'Dirección Centros Trabajo': ['Calle Trabajo 1; Calle Trabajo 2', 'Poligono Industrial 5', ''],
            'Cuenta Cotizacion': ['28123456789', '', ''],
            'Convenio Colectivo Número': ['99000015011981', '', ''],
            'Convenio Colectivo Nombre': ['Convenio Colectivo de Oficinas y Despachos', '', ''],
            'EPIGRAFE IAE': ['6411', '6412;6413', ''],
            'CNAE 2009': ['6201', '6202;6203', ''],
            'CNAE 2025': ['62.01', '62.02;62.03', '']
        })
        
        # Generar Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Empresas')
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='plantilla_empresas_iages.xlsx'
        )
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500



@admin_bp.route('/gestoria/usage', methods=['GET'])
@login_required
def get_gestoria_usage_endpoint():
    from tenant_utils import get_current_gestoria_id
    from utils.quota_utils import get_gestoria_usage
    gestoria_id = get_current_gestoria_id()
    usage = get_gestoria_usage(gestoria_id)
    if not usage:
        return jsonify({NotificationTypes.ERROR: 'Gestoría no encontrada'}), 404
    return jsonify(usage), 200

# =========================================================================
# IMPORTACIÓN DE GRUPOS Y USUARIOS (ADMINS DE GRUPO) DESDE EXCEL
# =========================================================================

@admin_bp.route('/grupos/plantilla-excel', methods=['GET'])
@login_required
def descargar_plantilla_grupos_excel():
    """Descarga plantilla Excel para importar agrupaciones y sus admins"""
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        df = pd.DataFrame({
            'Nombre Grupo': ['Grupo Garcia', 'Holding Inversiones SL'],
            'Email Grupo': ['grupo.garcia@gmail.com', 'holding.inversiones@gmail.com'],
            'NIFs Empresas': ['B12345678;A87654321', 'B55544433']
        })
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Agrupaciones')
        
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='plantilla_importar_grupos.xlsx'
        )
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

@admin_bp.route('/grupos/import-excel', methods=['POST'])
@login_required
def importar_grupos_excel():
    """
    Importa agrupaciones, crea usuarios admin de grupo y asocia empresas existentes.
    Requiere: rol Jefatura o super-admin
    """
    try:
        # Verificar permisos
        if not current_user.is_super_admin:
            if not current_user.departamento or current_user.departamento.nombre.lower() != 'jefatura':
                return jsonify({NotificationTypes.ERROR: 'No tienes permisos para importar agrupaciones'}), 403
        
        if 'file' not in request.files:
            return jsonify({NotificationTypes.ERROR: 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({NotificationTypes.ERROR: 'Archivo inválido'}), 400
            
        import pandas as pd
        from io import BytesIO
        from werkzeug.security import generate_password_hash
        from models import GrupoEmpresa, UserGrupoAcceso, User, Empresa, Departamento, db
        
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in ['xlsx', 'csv']:
            return jsonify({NotificationTypes.ERROR: 'Formato no soportado (.xlsx o .csv)'}), 400
            
        if ext == 'xlsx':
            df = pd.read_excel(BytesIO(file.read()), engine='openpyxl')
        else:
            df = pd.read_csv(BytesIO(file.read()))
            
        # Normalizar columnas
        df.columns = df.columns.str.strip().str.lower()
        mapping = {
            'nombre grupo': 'nombre_grupo',
            'email grupo': 'email_grupo',
            'descripcion grupo': 'descripcion_grupo',
            'nombre usuario': 'nombre_usuario',
            'email usuario': 'email_usuario',
            'nifs empresas': 'nifs_empresas'
        }
        df = df.rename(columns=lambda x: mapping.get(x, x))
        
        required = ['nombre_grupo', 'email_grupo']
        for col in required:
            if col not in df.columns:
                return jsonify({NotificationTypes.ERROR: f'Columna requerida faltante: {col}'}), 400

        gestoria_id = current_user.gestoria_id
        exitosos = []
        errores = []
        
        for idx, row in df.iterrows():
            fila_num = idx + 2
            try:
                nombre_grupo = str(row.get('nombre_grupo', '')).strip()
                email_grupo = str(row.get('email_grupo', '')).strip() or None
                desc_grupo = str(row.get('descripcion_grupo', '')).strip() or nombre_grupo
                nombre_user = str(row.get('nombre_usuario', '')).strip() or nombre_grupo
                email_user = str(row.get('email_usuario', row.get('email_grupo', ''))).strip().lower()
                nifs_raw = str(row.get('nifs_empresas', '')).strip()
                
                if not nombre_grupo or not email_user:
                    errores.append({'fila': fila_num, 'error': 'Nombre de grupo o Email de usuario vacío'})
                    continue
                    
                # 1. Crear/Obtener Grupo
                grupo = GrupoEmpresa.query.filter_by(nombre=nombre_grupo, gestoria_id=gestoria_id).first()
                if not grupo:
                    grupo = GrupoEmpresa(
                        nombre=nombre_grupo,
                        email_notificaciones=email_grupo,
                        descripcion=desc_grupo,
                        gestoria_id=gestoria_id,
                        usar_email_grupo=bool(email_grupo)
                    )
                    db.session.add(grupo)
                    db.session.flush() # Para tener grupo.id

                # 2. Crear/Obtener Usuario
                usuario = User.query.filter_by(email=email_user).first()
                if not usuario:
                    # Crear usuario invitado temporal
                    from models import Departamento
                    dept_invitado = Departamento.query.filter(Departamento.nombre.ilike('%invitado%')).first()
                    
                    usuario = User(
                        nombre=nombre_user,
                        email=email_user,
                        password_hash=generate_password_hash("Iages2026*"), # Pass temporal
                        gestoria_id=gestoria_id,
                        departamento_id=dept_invitado.id if dept_invitado else None,
                        activo=True
                    )
                    db.session.add(usuario)
                    db.session.flush()
                
                # 3. Vincular Usuario al Grupo (Admin Grupo)
                acceso = UserGrupoAcceso.query.filter_by(user_id=usuario.id, grupo_id=grupo.id).first()
                if not acceso:
                    acceso = UserGrupoAcceso(
                        user_id=usuario.id,
                        grupo_id=grupo.id,
                        es_admin_grupo=True
                    )
                    db.session.add(acceso)

                # 4. Vincular Empresas al Grupo
                nifs = [n.strip() for n in nifs_raw.split(';') if n.strip()]
                vink_count = 0
                for nif in nifs:
                    emp = Empresa.query.filter_by(nif=nif, gestoria_id=gestoria_id).first()
                    if emp:
                        emp.grupo_id = grupo.id
                        vink_count += 1
                
                exitosos.append({
                    'fila': fila_num, 
                    'grupo': nombre_grupo, 
                    'usuario': email_user, 
                    'empresas_vinculadas': vink_count
                })
                
            except Exception as e:
                import traceback
                current_app.logger.error(f"❌ Error importando fila {fila_num}: {str(e)}\n{traceback.format_exc()}")
                print(f"❌ Error importando fila {fila_num}: {str(e)}\n{traceback.format_exc()}")
                db.session.rollback()
                errores.append({'fila': fila_num, 'error': str(e)})

        db.session.commit()
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'message': f'Importación completada. Se han creado {len(exitosos)} agrupaciones. La contraseña temporal para los nuevos usuarios es: Iages2026*',
            'total': len(df),
            'exitosos': exitosos,
            'errores': errores
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Endpoint de mÃ©tricas para super-admin
"""





@admin_bp.route('/super-admin/gestorias/metrics', methods=['GET'])
@login_required
def get_all_gestorias_metrics():
    """Retorna métricas de todas las gestorías (solo super-admin)"""
    if not current_user.is_super_admin:
        return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
    
    try:
        from utils.quota_utils import get_gestoria_usage
        from datetime import date
        
        gestorias = Gestoria.query.all()
        metrics = []
        
        # Calcular fecha de inicio del mes
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)
        
        for g in gestorias:
            usage = get_gestoria_usage(g.id)
            
            # Métricas de IA por gestoría (último mes)
            ai_stats = db.session.query(
                func.sum(ApiKeyUsage.requests_count).label('total_requests'),
                func.sum(ApiKeyUsage.tokens_used).label('total_tokens'),
                func.sum(ApiKeyUsage.errors_count).label('total_errors')
            ).filter(
                ApiKeyUsage.gestoria_id == g.id,
                ApiKeyUsage.date >= inicio_mes
            ).first()
            
            # Detectar alertas
            alertas = []
            if usage['empresas']['porcentaje'] >= 80:
                alertas.append('empresas_80')
            if usage['storage']['porcentaje'] >= 80:
                alertas.append('storage_80')
            if usage['usuarios']['porcentaje'] >= 80:
                alertas.append('usuarios_80')
            
            metrics.append({
                'id': g.id,
                'nombre': g.nombre,
                'slug': g.slug,
                'activa': g.activa,
                'plan': g.plan,
                'empresas': usage['empresas'],
                'usuarios': usage['usuarios'],
                'storage': usage['storage'],
                'ia_usage': {
                    'requests': ai_stats.total_requests or 0,
                    'tokens': ai_stats.total_tokens or 0,
                    'errors': ai_stats.total_errors or 0,
                    'success_rate': round((ai_stats.total_requests / (ai_stats.total_requests + ai_stats.total_errors) * 100), 2) if (ai_stats.total_requests or 0) + (ai_stats.total_errors or 0) > 0 else 100
                },
                'ultima_actividad': None,
                'alertas': alertas
            })
        
        return jsonify({'gestorias': metrics}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@admin_bp.route('/documentos/reprocesar-categoria', methods=['POST'])
@admin_required
def reprocesar_categoria():
    """
    Reprocesa todos los documentos de una empresa y categoría específica.
    Útil para aplicar mejoras de IA a documentos ya subidos.
    """
    data = request.json
    empresa_id = data.get('empresa_id')
    categoria = data.get('categoria')
    
    logger = logging.getLogger('flask.app')
    logger.info(f"🚀 [ADMIN] Solicitud reprocesar: empresa_id={empresa_id}, categoria={categoria}, user={current_user.nombre}")
    
    if not empresa_id or not categoria:
        logger.error("❌ [ADMIN] Faltan parámetros en reprocesar_categoria")
        return jsonify({NotificationTypes.ERROR: "Faltan empresa_id o categoria"}), 400
        
    gestoria_id = current_user.gestoria_id
    
    # Solo permitir ciertas categorías por ahora
    categorias_soportadas = [
        'Impuestos', 'Altas de Trabajadores', 'Bajas de Trabajadores', 
        'Finiquitos', 'Contratos', 'Certificados de Retenciones 190', 
        'Certificados de Retenciones 180'
    ]
    
    if categoria not in categorias_soportadas:
        return jsonify({NotificationTypes.ERROR: f"Categoría '{categoria}' no soportada para reprocesamiento"}), 400
        
    # Buscar documentos
    docs = Documento.query.filter_by(
        empresa_id=empresa_id,
        categoria=categoria,
        gestoria_id=gestoria_id
    ).all()
    
    if not docs:
        return jsonify({NotificationTypes.SUCCESS: True, "message": "No hay documentos para reprocesar", "procesados": 0})
        
    # Importar servicios on-demand
    from services.procesar_impuestos import procesar_impuestos
    from services.procesar_altas import procesar_altas
    from services.procesar_finiquitos import procesar_finiquitos
    from services.procesar_contratos import procesar_contratos
    from services.procesar_modelo_190 import procesar_certificados_190
    from services.procesar_modelo_180 import procesar_certificados_180
    
    # Directorio temporal para el extractor (necesita un output_dir)
    temp_output = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'temp'), 'reprocess_output', str(datetime.now().timestamp()))
    os.makedirs(temp_output, exist_ok=True)
    
    procesados = 0
    errores = 0
    
    logger = logging.getLogger(__name__)

    try:
        for doc in docs:
            if not os.path.exists(doc.ruta_archivo):
                continue
                
            res_ocr = []
            try:
                if categoria == 'Impuestos':
                    res_ocr = procesar_impuestos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria in ['Altas de Trabajadores', 'Bajas de Trabajadores']:
                    res_ocr = procesar_altas(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == 'Finiquitos':
                    res_ocr = procesar_finiquitos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == 'Contratos':
                    res_ocr = procesar_contratos(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == 'Certificados de Retenciones 190':
                    res_ocr = procesar_certificados_190(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                elif categoria == 'Certificados de Retenciones 180':
                    res_ocr = procesar_certificados_180(doc.ruta_archivo, temp_output, gestoria_id=gestoria_id, app_context=current_app.app_context())
                
                if res_ocr:
                    item = res_ocr[0] # Usualmente es 1 a 1 para estos casos
                    doc.datos_extraidos = item
                    doc.procesado = True
                    doc.fecha_procesado = datetime.utcnow()
                    doc.periodo = item.get('ejercicio') or item.get('periodo')
                    procesados += 1
            except Exception as e:
                logger.error(f"Error reprocesando doc {doc.id}: {e}")
                errores += 1
                
        db.session.commit()
        
        # Registrar en auditoría
        from models import AuditoriaLog
        log = AuditoriaLog(
            user_id=current_user.id,
            accion="REPROCESAR_CATEGORIA",
            entidad_tipo="Documento",
            descripcion=f"Reprocesamiento masivo de {categoria} para empresa {empresa_id}",
            detalles={'empresa_id': empresa_id, 'categoria': categoria, 'procesados': procesados, 'errores': errores},
            gestoria_id=gestoria_id
        )
        db.session.add(log)
        db.session.commit()
        
    finally:
        try: shutil.rmtree(temp_output)
        except: pass
        
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "message": f"Reprocesamiento completado: {procesados} exitosos, {errores} fallidos",
        "procesados": procesados,
        "errores": errores
    })


@admin_bp.route('/documentos/reprocesar-categoria-global', methods=['POST'])
@admin_required
def reprocesar_categoria_global():
    """
    Inicia una tarea de Celery para reprocesar todos los documentos de una categoría
    en TODAS las empresas de la gestoría.
    """
    data = request.json
    categoria = data.get('categoria')
    
    logger = logging.getLogger('flask.app')
    logger.info(f"🚀 [ADMIN] Solicitud reprocesar GLOBAL: categoria={categoria}, user={current_user.nombre}")
    
    if not categoria:
        return jsonify({NotificationTypes.ERROR: "Falta el parámetro categoria"}), 400
        
    gestoria_id = current_user.gestoria_id
    
    # Categorías soportadas (mismas que el individual)
    categorias_soportadas = [
        'Impuestos', 'Altas de Trabajadores', 'Bajas de Trabajadores', 
        'Finiquitos', 'Contratos', 'Certificados de Retenciones 190', 
        'Certificados de Retenciones 180'
    ]
    
    if categoria not in categorias_soportadas:
        return jsonify({NotificationTypes.ERROR: f"Categoría '{categoria}' no soportada para reprocesamiento"}), 400
        
    # Disparar tarea Celery
    from celery_tasks_admin import reprocesar_categoria_global_task
    task = reprocesar_categoria_global_task.delay(gestoria_id, categoria, current_user.id)
    
    # Registrar en auditoría la intención
    from models import AuditoriaLog
    log = AuditoriaLog(
        user_id=current_user.id,
        accion="REPROCESAR_CATEGORIA_GLOBAL_INICIO",
        entidad_tipo="Documento",
        descripcion=f"Solicitado reprocesamiento GLOBAL de {categoria} (Task ID: {task.id})",
        detalles={'categoria': categoria, 'task_id': task.id},
        gestoria_id=gestoria_id
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        NotificationTypes.SUCCESS: True,
        "message": f"Se ha iniciado el reprocesamiento global de '{categoria}' en segundo plano. Esto puede tardar varios minutos.",
        "task_id": task.id
    })
