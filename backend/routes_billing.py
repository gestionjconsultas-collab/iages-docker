# backend/routes_billing.py
"""
Endpoints de facturación (pago por transferencia bancaria)
Accesible para jefaturas (ver su propia gestoría) y super-admin (ver todas)
"""
import logging
import os

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from models_billing import Plan, Suscripcion, Factura, UsoMensual, Cupon
from services.billing_service import BillingService
from extensions import db
from constants import NotificationTypes
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Directorio donde se guardan los PDFs de facturas
FACTURAS_PDF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'facturas_pdf'))

billing_bp = Blueprint('billing', __name__)

# Decorador para verificar super-admin (solo para acciones administrativas)
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

# ==========================================
# PLANES
# ==========================================

@billing_bp.route('/api/planes', methods=['GET'])
def listar_planes():
    """Lista todos los planes activos"""
    try:
        planes = Plan.query.filter_by(activo=True).order_by(Plan.precio_mensual).all()
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'planes': [p.to_dict() for p in planes]
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# SUSCRIPCIÓN
# ==========================================

@billing_bp.route('/api/suscripcion', methods=['GET'])
@login_required
def obtener_suscripcion():
    """Obtiene la suscripción de la gestoría del usuario actual"""
    """Obtiene la suscripción actual de la gestoría"""
    try:
        gestoria_id = current_user.gestoria_id
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        
        if not suscripcion:
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'suscripcion': None,
                'mensaje': 'Sin suscripción activa'
            })
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'suscripcion': suscripcion.to_dict(),
            'gestoria_nombre': current_user.gestoria.nombre if current_user.gestoria else None
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/suscripcion/cambiar-plan', methods=['POST'])
@login_required
@require_super_admin  # Solo admin puede cambiar planes
def cambiar_plan():
    """Cambia el plan de la gestoría"""
    try:
        data = request.json
        gestoria_id = current_user.gestoria_id
        
        nuevo_plan = data.get('plan_codigo')
        ciclo = data.get('ciclo', 'mensual')
        cupon = data.get('cupon_codigo')
        
        if not nuevo_plan:
            return jsonify({NotificationTypes.ERROR: 'Plan requerido'}), 400
        
        resultado = BillingService.cambiar_plan(
            gestoria_id=gestoria_id,
            nuevo_plan_codigo=nuevo_plan,
            ciclo=ciclo,
            cupon_codigo=cupon,
            usuario_id=current_user.id
        )
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            **resultado
        })
    except ValueError as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 400
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/suscripcion/cancelar', methods=['POST'])
@login_required
@require_super_admin  # Solo admin puede cancelar
def cancelar_suscripcion():
    """Cancela la suscripción"""
    try:
        gestoria_id = current_user.gestoria_id
        
        suscripcion = BillingService.cancelar_suscripcion(
            gestoria_id=gestoria_id,
            usuario_id=current_user.id
        )
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'suscripcion': suscripcion.to_dict(),
            'mensaje': 'Suscripción cancelada. Tendrás acceso hasta el fin del período pagado.'
        })
    except ValueError as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 400
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# FACTURAS
# ==========================================

@billing_bp.route('/api/facturas', methods=['GET'])
@login_required
def listar_facturas():
    """Lista las facturas de la gestoría del usuario actual"""
    """Lista las facturas de la gestoría"""
    try:
        gestoria_id = current_user.gestoria_id
        
        # Filtros opcionales
        estado = request.args.get('estado')
        limit = request.args.get('limit', 50, type=int)
        
        query = Factura.query.filter_by(gestoria_id=gestoria_id)
        
        if estado:
            query = query.filter_by(estado=estado)
        
        facturas = query.order_by(Factura.fecha_emision.desc()).limit(limit).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'facturas': [f.to_dict() for f in facturas]
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/facturas/<int:id>', methods=['GET'])
@login_required
def obtener_factura(id):
    """Obtiene una factura específica"""
    try:
        # Super-admin puede ver cualquier factura
        if getattr(current_user, 'is_super_admin', False):
            factura = Factura.query.get(id)
        else:
            # Usuarios normales solo ven facturas de su gestoría
            gestoria_id = current_user.gestoria_id
            factura = Factura.query.filter_by(id=id, gestoria_id=gestoria_id).first()
        
        if not factura:
            return jsonify({NotificationTypes.ERROR: 'Factura no encontrada'}), 404
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'factura': factura.to_dict()
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/facturas/<int:id>/pdf', methods=['GET'])
@login_required
def descargar_factura_pdf(id):
    """Descarga el PDF de una factura"""
    try:
        # Super-admin puede ver cualquier factura
        if getattr(current_user, 'is_super_admin', False):
            factura = Factura.query.get(id)
        else:
            # Usuarios normales solo ven facturas de su gestoría
            gestoria_id = current_user.gestoria_id
            factura = Factura.query.filter_by(id=id, gestoria_id=gestoria_id).first()
        
        if not factura:
            return jsonify({NotificationTypes.ERROR: 'Factura no encontrada'}), 404
        
        # Generar PDF si no existe
        if not factura.pdf_generado or not factura.pdf_path:
            from utils.pdf_invoice_generator import generar_pdf_factura
            pdf_path = generar_pdf_factura(factura.id)
            factura.pdf_path = pdf_path
            factura.pdf_generado = True
            db.session.commit()

        # Fix 6: Validar path traversal — el PDF debe estar dentro del directorio esperado
        pdf_path_abs = os.path.abspath(factura.pdf_path)
        if not pdf_path_abs.startswith(FACTURAS_PDF_DIR + os.sep) and not pdf_path_abs.startswith(FACTURAS_PDF_DIR):
            logger.warning("Intento de path traversal en factura %d: %s", id, factura.pdf_path)
            return jsonify({NotificationTypes.ERROR: 'Ruta de PDF no válida'}), 400

        return send_file(
            pdf_path_abs,
            as_attachment=True,
            download_name=f"{factura.numero_factura}.pdf"
        )
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/facturas/<int:id>/marcar-pagada', methods=['POST'])
@login_required
@require_super_admin  # Ya valida que sea super-admin
def marcar_factura_pagada(id):
    """Marca una factura como pagada (solo super-admin)"""
    try:
        data = request.json
        metodo_pago = data.get('metodo_pago', 'transferencia')
        
        factura = BillingService.marcar_factura_pagada(
            factura_id=id,
            metodo_pago=metodo_pago
        )
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'factura': factura.to_dict(),
            'mensaje': 'Factura marcada como pagada'
        })
    except ValueError as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 400
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# USO Y LÍMITES
# ==========================================

@billing_bp.route('/api/uso-actual', methods=['GET'])
@login_required
def obtener_uso_actual():
    """Obtiene el uso actual de la gestoría del usuario"""
    try:
        gestoria_id = current_user.gestoria_id
        
        if not gestoria_id:
            return jsonify({NotificationTypes.ERROR: 'Usuario sin gestoría asignada'}), 400
        
        # Calcular uso del mes actual
        uso = BillingService.calcular_uso_mensual(gestoria_id)
        
        # Si no hay uso registrado, crear uno vacío
        if not uso:
            from models_billing import UsoMensual
            from datetime import datetime
            now = datetime.utcnow()
            uso = UsoMensual(
                gestoria_id=gestoria_id,
                mes=now.month,
                anio=now.year,
                usuarios_activos=0,
                empresas_totales=0,
                storage_usado_gb=0,
                tokens_usados=0,
                requests_ia=0,
                documentos_procesados=0,
                emails_enviados=0
            )
            db.session.add(uso)
            db.session.commit()
        
        # Obtener límites del plan
        suscripcion = Suscripcion.query.filter_by(gestoria_id=gestoria_id).first()
        
        limites = {}
        if suscripcion and suscripcion.plan:
            plan = suscripcion.plan
            limites = {
                'usuarios': {
                    'limite': plan.max_usuarios or 0,
                    'uso': uso.usuarios_activos or 0,
                    'porcentaje': ((uso.usuarios_activos or 0) / plan.max_usuarios * 100) if plan.max_usuarios else 0
                },
                'empresas': {
                    'limite': plan.max_empresas or 0,
                    'uso': uso.empresas_totales or 0,
                    'porcentaje': ((uso.empresas_totales or 0) / plan.max_empresas * 100) if plan.max_empresas else 0
                },
                'storage': {
                    'limite': plan.max_storage_gb or 0,
                    'uso': float(uso.storage_usado_gb or 0),
                    'porcentaje': (float(uso.storage_usado_gb or 0) / plan.max_storage_gb * 100) if plan.max_storage_gb else 0
                },
                'tokens': {
                    'limite': plan.max_tokens_mes or 0,
                    'uso': uso.tokens_usados or 0,
                    'porcentaje': ((uso.tokens_usados or 0) / plan.max_tokens_mes * 100) if plan.max_tokens_mes else 0
                }
            }
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'uso': uso.to_dict() if uso else {},
            'limites': limites
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({NotificationTypes.ERROR: f'Error al obtener uso: {str(e)}'}), 500


# ==========================================
# CUPONES
# ==========================================

@billing_bp.route('/api/cupones/validar', methods=['POST'])
@login_required
def validar_cupon():
    """Valida un cupón de descuento"""
    try:
        data = request.json
        codigo = data.get('codigo')
        plan_id = data.get('plan_id')
        ciclo = data.get('ciclo')
        
        if not codigo:
            return jsonify({NotificationTypes.ERROR: 'Código de cupón requerido'}), 400
        
        resultado = BillingService.validar_cupon(
            codigo=codigo,
            plan_id=plan_id,
            ciclo=ciclo
        )
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            **resultado
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# DATOS BANCARIOS (para transferencias)
# ==========================================

@billing_bp.route('/api/datos-bancarios', methods=['GET'])
@login_required
def obtener_datos_bancarios():
    """Obtiene los datos bancarios de IAGES para transferencias"""
    try:
        from models_billing import EmpresaEmisora
        
        empresa = EmpresaEmisora.get_datos_iages()
        
        if not empresa:
            return jsonify({NotificationTypes.ERROR: 'Datos bancarios no configurados'}), 404
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'datos_bancarios': {
                'nombre': empresa.nombre,
                'cif': empresa.cif,
                'iban': empresa.iban_decrypted,
                'swift': empresa.swift_decrypted,
                'banco': empresa.banco_decrypted,
                'direccion': empresa.direccion,
                'email': empresa.email
            }
        })
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# BANNERS PROMOCIONALES
# ==========================================

@billing_bp.route('/api/banners/activos', methods=['GET'])
@login_required
def obtener_banners_activos():
    """Obtiene banners promocionales activos para el usuario actual"""
    try:
        from models_billing import BannerPromocional
        from models import Gestoria
        
        # Obtener gestoría del usuario
        gestoria = Gestoria.query.get(current_user.gestoria_id)
        if not gestoria:
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'banner': None
            })
        
        plan_actual = gestoria.plan
        
        # Obtener banners activos ordenados por prioridad
        banners = BannerPromocional.query.filter_by(activo=True).order_by(
            BannerPromocional.prioridad.desc(),
            BannerPromocional.created_at.desc()
        ).all()
        
        # Filtrar banners válidos
        banners_validos = []
        for banner in banners:
            # Verificar que esté dentro del período válido
            if not banner.esta_activo():
                continue
            
            # Si tiene plan objetivo, solo mostrar si el usuario NO tiene ese plan
            if banner.plan_objetivo and banner.plan_objetivo == plan_actual:
                continue
            
            banners_validos.append(banner.to_dict())
        
        # Retornar todos los banners válidos (ordenados por prioridad)
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'banners': banners_validos
        })
        
    except Exception as e:
        logger.error("Error obteniendo banners: %s", e, exc_info=True)
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@billing_bp.route('/api/banners/<int:banner_id>/click', methods=['POST'])
@login_required
def registrar_click_banner(banner_id):
    """Registra un click en un banner (analytics)"""
    try:
        from models_billing import BannerPromocional
        
        banner = BannerPromocional.query.get(banner_id)
        if not banner:
            return jsonify({NotificationTypes.ERROR: 'Banner no encontrado'}), 404
        
        banner.incrementar_clicks()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'clicks': banner.clicks
        })
        
    except Exception as e:
        logger.error("Error registrando click en banner %d: %s", banner_id, e)
        return jsonify({NotificationTypes.ERROR: str(e)}), 500
