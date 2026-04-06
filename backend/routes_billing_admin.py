# backend/routes_billing_admin.py
"""
Endpoints de administración de facturación
SOLO PARA SUPER-ADMIN
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models_billing import Suscripcion, Factura
from models import Gestoria
from extensions import db
from constants import NotificationTypes
from functools import wraps

billing_admin_bp = Blueprint('billing_admin', __name__)

# Decorador para verificar super-admin
def require_super_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({NotificationTypes.ERROR: 'No autenticado'}), 401
        
        if not getattr(current_user, 'is_super_admin', False):
            return jsonify({
                NotificationTypes.ERROR: 'Acceso denegado. Solo super-admin.',
                'codigo': 'NO_SUPER_ADMIN'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


@billing_admin_bp.route('/api/admin/suscripciones', methods=['GET'])
@login_required
@require_super_admin
def listar_todas_suscripciones():
    """Lista todas las suscripciones de todas las gestorías"""
    try:
        suscripciones = Suscripcion.query.all()
        
        resultado = []
        for suscripcion in suscripciones:
            gestoria = Gestoria.query.get(suscripcion.gestoria_id)
            data = suscripcion.to_dict()
            data['gestoria_nombre'] = gestoria.nombre if gestoria else 'Desconocida'
            data['gestoria_email'] = gestoria.email if gestoria else None
            resultado.append(data)
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'suscripciones': resultado
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/facturas', methods=['GET'])
@login_required
@require_super_admin
def listar_todas_facturas():
    """Lista todas las facturas de todas las gestorías"""
    try:
        # Filtros opcionales
        estado = request.args.get('estado')
        gestoria_id = request.args.get('gestoria_id', type=int)
        limit = request.args.get('limit', 100, type=int)
        
        query = Factura.query
        
        if estado:
            query = query.filter_by(estado=estado)
        
        if gestoria_id:
            query = query.filter_by(gestoria_id=gestoria_id)
        
        facturas = query.order_by(Factura.fecha_emision.desc()).limit(limit).all()
        
        resultado = []
        for factura in facturas:
            gestoria = Gestoria.query.get(factura.gestoria_id)
            data = factura.to_dict()
            data['gestoria_nombre'] = gestoria.nombre if gestoria else 'Desconocida'
            data['gestoria_email'] = gestoria.email if gestoria else None
            resultado.append(data)
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'facturas': resultado
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/estadisticas', methods=['GET'])
@login_required
@require_super_admin
def obtener_estadisticas():
    """Obtiene estadísticas generales de facturación"""
    try:
        total_suscripciones = Suscripcion.query.count()
        suscripciones_activas = Suscripcion.query.filter_by(estado='activa').count()
        suscripciones_trial = Suscripcion.query.filter_by(estado='trial').count()
        
        total_facturas = Factura.query.count()
        facturas_pendientes = Factura.query.filter_by(estado='pendiente').count()
        facturas_pagadas = Factura.query.filter_by(estado='pagada').count()
        facturas_vencidas = Factura.query.filter_by(estado='vencida').count()
        
        # Calcular totales
        total_pendiente = db.session.query(
            db.func.sum(Factura.total)
        ).filter_by(estado='pendiente').scalar() or 0
        
        total_cobrado = db.session.query(
            db.func.sum(Factura.total)
        ).filter_by(estado='pagada').scalar() or 0
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'estadisticas': {
                'suscripciones': {
                    'total': total_suscripciones,
                    'activas': suscripciones_activas,
                    'trial': suscripciones_trial
                },
                'facturas': {
                    'total': total_facturas,
                    'pendientes': facturas_pendientes,
                    'pagadas': facturas_pagadas,
                    'vencidas': facturas_vencidas
                },
                'montos': {
                    'total_pendiente': float(total_pendiente),
                    'total_cobrado': float(total_cobrado),
                    'total_facturado': float(total_pendiente + total_cobrado)
                }
            }
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/planes/<int:plan_id>/actualizar-suscripciones', methods=['POST'])
@login_required
@require_super_admin
def actualizar_precios_suscripciones(plan_id):
    """Actualiza el precio de todas las suscripciones existentes de un plan"""
    try:
        # Obtener el plan
        plan = Plan.query.get(plan_id)
        if not plan:
            return jsonify({NotificationTypes.ERROR: 'Plan no encontrado'}), 404
        
        # Obtener todas las suscripciones activas con este plan
        suscripciones = Suscripcion.query.filter_by(plan_id=plan_id).all()
        
        if not suscripciones:
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': 'No hay suscripciones con este plan',
                'actualizadas': 0
            })
        
        # Actualizar precio de cada suscripción
        actualizadas = 0
        for suscripcion in suscripciones:
            old_price = suscripcion.precio_actual
            suscripcion.precio_actual = plan.precio_mensual
            actualizadas += 1
            print(f"💰 Suscripción {suscripcion.id}: €{old_price} → €{plan.precio_mensual}")
        
        db.session.commit()
        
        # Emitir evento WebSocket a todas las gestorías afectadas
        try:
            socketio = current_app.extensions.get('socketio')
            if socketio:
                for suscripcion in suscripciones:
                    socketio.emit('plan_changed', {
                        'gestoria_id': suscripcion.gestoria_id,
                        'plan_id': plan_id,
                        'new_price': float(plan.precio_mensual),
                        'mensaje': f'El precio de tu plan ha sido actualizado a €{plan.precio_mensual}/mes'
                    }, room=f'gestoria_{suscripcion.gestoria_id}')
                print(f"📡 Eventos enviados a {actualizadas} gestorías")
        except Exception as ws_error:
            print(f"⚠️ Error emitiendo WebSocket: {ws_error}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': f'{actualizadas} suscripciones actualizadas',
            'actualizadas': actualizadas,
            'nuevo_precio': float(plan.precio_mensual)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando precios: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# GESTIÓN DE CUPONES
# ==========================================

@billing_admin_bp.route('/api/admin/cupones', methods=['GET'])
@login_required
@require_super_admin
def listar_cupones():
    """Lista todos los cupones disponibles"""
    try:
        from models_billing import Cupon
        
        cupones = Cupon.query.filter_by(activo=True).order_by(Cupon.codigo).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'cupones': [{
                'id': c.id,
                'codigo': c.codigo,
                'tipo': c.tipo,
                'valor': float(c.valor),
                'descripcion': c.descripcion,
                'fecha_inicio': c.fecha_inicio.isoformat() if c.fecha_inicio else None,
                'fecha_fin': c.fecha_expiracion.isoformat() if c.fecha_expiracion else None,
                'usos_maximos': c.usos_maximos,
                'usos_actuales': c.usos_actuales,
                # Campos calculados para mostrar en UI
                'descuento_porcentaje': float(c.valor) if c.tipo == 'porcentaje' else None,
                'descuento_fijo': float(c.valor) if c.tipo == 'fijo' else None
            } for c in cupones]
        })
        
    except Exception as e:
        print(f"Error listando cupones: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# GESTIÓN DE BANNERS PROMOCIONALES
# ==========================================

@billing_admin_bp.route('/api/admin/banners', methods=['GET'])
@login_required
@require_super_admin
def listar_banners():
    """Lista todos los banners con analytics"""
    try:
        from models_billing import BannerPromocional
        
        banners = BannerPromocional.query.order_by(
            BannerPromocional.prioridad.desc(),
            BannerPromocional.created_at.desc()
        ).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'banners': [banner.to_dict() for banner in banners]
        })
        
    except Exception as e:
        print(f"Error listando banners: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/banners', methods=['POST'])
@login_required
@require_super_admin
def crear_banner():
    """Crea un nuevo banner promocional"""
    try:
        from models_billing import BannerPromocional, Cupon
        
        data = request.json
        
        # Validar cupón si se proporciona
        if data.get('cupon_codigo'):
            cupon = Cupon.query.filter_by(codigo=data['cupon_codigo']).first()
            if not cupon:
                return jsonify({NotificationTypes.ERROR: 'Cupón no encontrado'}), 404
        
        banner = BannerPromocional(
            titulo=data['titulo'],
            descripcion=data.get('descripcion', ''),
            icono=data.get('icono', '🎉'),
            color_fondo=data.get('color_fondo', '#8B5CF6'),
            plan_objetivo=data.get('plan_objetivo'),
            cupon_codigo=data.get('cupon_codigo'),
            prioridad=data.get('prioridad', 0),
            activo=data.get('activo', True),
            fecha_inicio=data.get('fecha_inicio'),
            fecha_fin=data.get('fecha_fin')
        )
        
        db.session.add(banner)
        db.session.commit()
        
        print(f"✅ Banner creado: {banner.titulo}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': 'Banner creado exitosamente',
            'banner': banner.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creando banner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/banners/<int:banner_id>', methods=['PUT'])
@login_required
@require_super_admin
def actualizar_banner(banner_id):
    """Actualiza un banner existente"""
    try:
        from models_billing import BannerPromocional, Cupon
        
        banner = BannerPromocional.query.get(banner_id)
        if not banner:
            return jsonify({NotificationTypes.ERROR: 'Banner no encontrado'}), 404
        
        data = request.json
        
        # Validar cupón si se proporciona
        if data.get('cupon_codigo'):
            cupon = Cupon.query.filter_by(codigo=data['cupon_codigo']).first()
            if not cupon:
                return jsonify({NotificationTypes.ERROR: 'Cupón no encontrado'}), 404
        
        # Actualizar campos
        banner.titulo = data.get('titulo', banner.titulo)
        banner.descripcion = data.get('descripcion', banner.descripcion)
        banner.icono = data.get('icono', banner.icono)
        banner.color_fondo = data.get('color_fondo', banner.color_fondo)
        banner.plan_objetivo = data.get('plan_objetivo', banner.plan_objetivo)
        banner.cupon_codigo = data.get('cupon_codigo', banner.cupon_codigo)
        banner.prioridad = data.get('prioridad', banner.prioridad)
        banner.activo = data.get('activo', banner.activo)
        banner.fecha_inicio = data.get('fecha_inicio', banner.fecha_inicio)
        banner.fecha_fin = data.get('fecha_fin', banner.fecha_fin)
        
        db.session.commit()
        
        print(f"✅ Banner actualizado: {banner.titulo}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': 'Banner actualizado exitosamente',
            'banner': banner.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error actualizando banner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/banners/<int:banner_id>/toggle', methods=['PATCH'])
@login_required
@require_super_admin
def toggle_banner(banner_id):
    """Activa/desactiva un banner"""
    try:
        from models_billing import BannerPromocional
        
        banner = BannerPromocional.query.get(banner_id)
        if not banner:
            return jsonify({NotificationTypes.ERROR: 'Banner no encontrado'}), 404
        
        banner.activo = not banner.activo
        db.session.commit()
        
        estado = 'activado' if banner.activo else 'desactivado'
        print(f"🔄 Banner {estado}: {banner.titulo}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': f'Banner {estado} exitosamente',
            'activo': banner.activo
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling banner: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_admin_bp.route('/api/admin/banners/<int:banner_id>', methods=['DELETE'])
@login_required
@require_super_admin
def eliminar_banner(banner_id):
    """Elimina un banner"""
    try:
        from models_billing import BannerPromocional
        
        banner = BannerPromocional.query.get(banner_id)
        if not banner:
            return jsonify({NotificationTypes.ERROR: 'Banner no encontrado'}), 404
        
        titulo = banner.titulo
        db.session.delete(banner)
        db.session.commit()
        
        print(f"🗑️ Banner eliminado: {titulo}")
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'mensaje': 'Banner eliminado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error eliminando banner: {e}")
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
