"""
Rutas de API para Super-Admin
Dashboard global, gestión de gestorías, usuarios, planes y auditoría
"""
import os
import shutil
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import (db, Gestoria, User, Empresa, Documento, TicketSoporte,
                   PlanGestoria, GestoriaPlan, UsoGestoria, AlertaSistema,
                   AuditoriaAccesoGestoria, ConfiguracionGlobal, PlanHistorial,
                   Rol, Departamento)
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import func, desc
import traceback
from utils.logger import logger, log_success, log_error, log_warning

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/api/super-admin')

def require_super_admin(f):
    """Decorator que requiere permisos de super-admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            return jsonify({'error': 'Acceso denegado. Se requieren permisos de super-admin'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# DASHBOARD GLOBAL
# ============================================

@super_admin_bp.route('/dashboard-global', methods=['GET'])
@login_required
@require_super_admin
def dashboard_global():
    """Dashboard global con métricas de todas las gestorías"""
    try:
        # Métricas generales
        total_gestorias = Gestoria.query.count()
        gestorias_activas = Gestoria.query.filter_by(activa=True).count()
        total_usuarios = User.query.count()
        total_empresas = Empresa.query.count()
        total_documentos = Documento.query.count()
        
        # Usuarios online (últimos 15 minutos)
        hace_15_min = datetime.utcnow() - timedelta(minutes=15)
        usuarios_online = User.query.filter(User.last_seen >= hace_15_min).count() if hasattr(User, 'last_seen') else 0
        
        # Gestorías con mayor actividad (documentos procesados hoy)
        hoy = datetime.now().date()
        gestorias_activas_hoy = db.session.query(
            Gestoria.nombre,
            func.count(Documento.id).label('docs_count')
        ).join(Documento).filter(
            func.date(Documento.fecha_creacion) == hoy
        ).group_by(Gestoria.id, Gestoria.nombre).order_by(
            desc('docs_count')
        ).limit(5).all()
        
        # Uso de IA por gestoría (mes actual)
        periodo_actual = datetime.now().strftime('%Y-%m')
        uso_ia = db.session.query(
            Gestoria.nombre,
            UsoGestoria.tokens_ia_usados,
            PlanGestoria.tokens_ia_mes
        ).join(UsoGestoria, Gestoria.id == UsoGestoria.gestoria_id
        ).join(GestoriaPlan, Gestoria.id == GestoriaPlan.gestoria_id
        ).join(PlanGestoria, GestoriaPlan.plan_id == PlanGestoria.id
        ).filter(UsoGestoria.periodo == periodo_actual
        ).order_by(desc(UsoGestoria.tokens_ia_usados)
        ).limit(5).all()
        
        # Alertas activas
        alertas_count = AlertaSistema.query.filter_by(leida=False).count()
        alertas_criticas = AlertaSistema.query.filter_by(
            leida=False,
            nivel='critical'
        ).count()
        
        # Tickets de soporte pendientes
        tickets_pendientes = TicketSoporte.query.filter(
            TicketSoporte.estado.in_(['Abierto', 'En Proceso'])
        ).count()
        
        return jsonify({
            'success': True,
            'metricas_generales': {
                'total_gestorias': total_gestorias,
                'gestorias_activas': gestorias_activas,
                'total_usuarios': total_usuarios,
                'usuarios_online': usuarios_online,
                'total_empresas': total_empresas,
                'total_documentos': total_documentos,
                'tickets_pendientes': tickets_pendientes
            },
            'gestorias_activas_hoy': [
                {'nombre': g[0], 'documentos': g[1]}
                for g in gestorias_activas_hoy
            ],
            'uso_ia': [
                {
                    'nombre': u[0],
                    'tokens_usados': u[1],
                    'tokens_limite': u[2],
                    'porcentaje': round((u[1] / u[2]) * 100, 1) if u[2] > 0 else 0
                }
                for u in uso_ia
            ],
            'alertas': {
                'total': alertas_count,
                'criticas': alertas_criticas
            }
        })
    except Exception as e:
        log_error(f"Error en dashboard global: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/metricas-avanzadas', methods=['GET'])
@login_required
@require_super_admin
def metricas_avanzadas():
    """Métricas avanzadas para gráficos del dashboard"""
    try:
        from sqlalchemy import extract
        
        # 1. Ingresos mensuales (últimos 6 meses)
        ingresos_mensuales = []
        for i in range(5, -1, -1):
            fecha = datetime.now() - timedelta(days=30*i)
            periodo = fecha.strftime('%Y-%m')
            
            # Calcular ingresos del mes
            total_ingresos = db.session.query(
                func.sum(PlanGestoria.precio_mensual)
            ).join(GestoriaPlan).filter(
                GestoriaPlan.estado == 'activo'
            ).scalar() or 0
            
            ingresos_mensuales.append({
                'mes': periodo,
                'ingresos': float(total_ingresos)
            })
        
        # 2. Distribución de planes
        distribucion_planes = db.session.query(
            PlanGestoria.nombre,
            func.count(GestoriaPlan.id).label('count')
        ).join(GestoriaPlan).group_by(
            PlanGestoria.nombre
        ).all()
        
        # 3. Crecimiento de usuarios (últimos 6 meses)
        crecimiento_usuarios = []
        for i in range(5, -1, -1):
            fecha = datetime.now() - timedelta(days=30*i)
            periodo = fecha.strftime('%Y-%m')
            
            # Contar usuarios del mes
            total_usuarios = User.query.count()
            
            crecimiento_usuarios.append({
                'mes': periodo,
                'usuarios': total_usuarios
            })
        
        # 4. Top 5 gestorías por uso de IA (mes actual)
        periodo_actual = datetime.now().strftime('%Y-%m')
        top_uso_ia = db.session.query(
            Gestoria.nombre,
            UsoGestoria.tokens_ia_usados
        ).join(UsoGestoria).filter(
            UsoGestoria.periodo == periodo_actual
        ).order_by(
            desc(UsoGestoria.tokens_ia_usados)
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'ingresos_mensuales': ingresos_mensuales,
            'distribucion_planes': [
                {'plan': p[0], 'count': p[1]}
                for p in distribucion_planes
            ],
            'crecimiento_usuarios': crecimiento_usuarios,
            'top_uso_ia': [
                {'gestoria': g[0], 'tokens': g[1]}
                for g in top_uso_ia
            ]
        })
    except Exception as e:
        log_error(f"Error en métricas avanzadas: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# GESTIÓN DE GESTORÍAS
# ============================================

@super_admin_bp.route('/gestorias', methods=['GET'])
@login_required
@require_super_admin
def listar_gestorias():
    """Lista todas las gestorías con sus métricas"""
    try:
        gestorias = Gestoria.query.all()
        periodo = datetime.now().strftime('%Y-%m')
        
        resultado = []
        for g in gestorias:
            # Obtener plan actual
            plan_actual = GestoriaPlan.query.filter_by(gestoria_id=g.id).first()
            
            # Obtener uso del mes
            uso = UsoGestoria.query.filter_by(
                gestoria_id=g.id,
                periodo=periodo
            ).first()
            
            # Contar recursos
            usuarios_count = User.query.filter_by(gestoria_id=g.id).count()
            empresas_count = Empresa.query.filter_by(gestoria_id=g.id).count()
            documentos_count = Documento.query.filter_by(gestoria_id=g.id).count()
            
            resultado.append({
                'id': g.id,
                'nombre': g.nombre,
                'activa': g.activa,
                'plan': plan_actual.plan.nombre if plan_actual else None,
                'plan_id': plan_actual.plan_id if plan_actual else None,
                'usuarios': {
                    'actuales': usuarios_count,
                    'max': plan_actual.plan.usuarios_max if plan_actual else 0,
                    'porcentaje': round((usuarios_count / plan_actual.plan.usuarios_max) * 100, 1) if plan_actual and plan_actual.plan.usuarios_max > 0 else 0
                },
                'empresas': {
                    'actuales': empresas_count,
                    'max': plan_actual.plan.empresas_max if plan_actual else 0,
                    'porcentaje': round((empresas_count / plan_actual.plan.empresas_max) * 100, 1) if plan_actual and plan_actual.plan.empresas_max > 0 else 0
                },
                'tokens_ia': {
                    'usados': uso.tokens_ia_usados if uso else 0,
                    'max': plan_actual.plan.tokens_ia_mes if plan_actual else 0,
                    'porcentaje': round((uso.tokens_ia_usados / plan_actual.plan.tokens_ia_mes) * 100, 1) if plan_actual and uso and plan_actual.plan.tokens_ia_mes > 0 else 0
                } if plan_actual else None,
                'certificados': {
                    'max': g.max_certificados if g.max_certificados is not None else (plan_actual.plan.certificados_max if plan_actual else 5)
                },
                'documentos_totales': documentos_count,
                'fecha_creacion': g.fecha_creacion.isoformat() if hasattr(g, 'fecha_creacion') and g.fecha_creacion else None
            })
        
        return jsonify({'success': True, 'gestorias': resultado})
    except Exception as e:
        log_error(f"Error listando gestorías: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/gestorias/<int:gestoria_id>', methods=['GET'])
@login_required
@require_super_admin
def obtener_gestoria(gestoria_id):
    """Obtiene detalles completos de una gestoría"""
    try:
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        plan_actual = GestoriaPlan.query.filter_by(gestoria_id=gestoria_id).first()
        
        # Uso de los últimos 6 meses
        uso_historico = []
        for i in range(6):
            fecha = datetime.now() - timedelta(days=30*i)
            periodo = fecha.strftime('%Y-%m')
            uso = UsoGestoria.query.filter_by(
                gestoria_id=gestoria_id,
                periodo=periodo
            ).first()
            if uso:
                uso_historico.append(uso.to_dict())
        
        # Alertas recientes
        alertas = AlertaSistema.query.filter_by(
            gestoria_id=gestoria_id
        ).order_by(desc(AlertaSistema.fecha_creacion)).limit(10).all()
        
        return jsonify({
            'success': True,
            'gestoria': {
                'id': gestoria.id,
                'nombre': gestoria.nombre,
                'activa': gestoria.activa,
                'max_certificados': gestoria.max_certificados,
                'plan_actual': plan_actual.to_dict() if plan_actual else None,
                'uso_historico': uso_historico,
                'alertas_recientes': [a.to_dict() for a in alertas]
            }
        })
    except Exception as e:
        log_error(f"Error obteniendo gestoría: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/clientes-conecta', methods=['POST'])
@login_required
@require_super_admin
def crear_cliente_conecta():
    """Crea un cliente (Gestoria + User) en un solo paso."""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        plan = data.get('plan', 'basico')
        iages_active = data.get('iages_active', False)
        max_certificados = data.get('max_certificados', 5)
        
        if not email:
            return jsonify({'error': 'Email requerido'}), 400
            
        # Si no hay password, generamos una aleatoria (ej: clientes solo Conecta)
        if not password:
            import secrets
            password = secrets.token_urlsafe(12)
            
        # Verificar si ya existe el usuario
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'El email ya está registrado'}), 400
            
        # Crear slug automático
        import re
        slug = re.sub(r'[^a-zA-Z0-9]', '-', email.split('@')[0].lower())
        base_slug = slug
        counter = 1
        while Gestoria.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        # Generar API Key
        import secrets
        api_key = f"JS-{secrets.token_hex(16)}"
        
        # Crear Gestoria
        nueva_gestoria = Gestoria(
            nombre=email.split('@')[0],
            slug=slug,
            email=email,
            plan=plan,
            iages_active=iages_active,
            max_certificados=max_certificados,
            api_key=api_key,
            activa=True,
            fecha_expiracion=datetime.utcnow() + timedelta(days=365) # 1 año por defecto
        )
        db.session.add(nueva_gestoria)
        db.session.flush()
        
        # Crear Usuario
        nuevo_usuario = User(
            nombre=email.split('@')[0],
            email=email,
            gestoria_id=nueva_gestoria.id,
            departamento_id=5, # Jefatura
            activo=True
        )
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente creado correctamente',
            'api_key': api_key,
            'gestoria_id': nueva_gestoria.id,
            'email': email,
            'username': email, # En este sistema el login suele ser el email
            'password_generated': not data.get('password') # Informamos si se generó
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"Error creando cliente conecta: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/clientes-conecta', methods=['GET'])
@login_required
@require_super_admin
def listar_clientes_conecta():
    """Lista gestorías que tienen API Key (clientes de Conecta/Iages)."""
    try:
        # Filtramos gestorías que tienen api_key asignada
        clientes = Gestoria.query.filter(Gestoria.api_key.isnot(None)).order_by(Gestoria.id.desc()).all()
        
        resultado = []
        for c in clientes:
            resultado.append({
                'id': c.id,
                'nombre': c.nombre,
                'email': c.email,
                'api_key': c.api_key,
                'plan': c.plan,
                'iages_active': c.iages_active,
                'max_certificados': c.max_certificados,
                'fecha_expiracion': c.fecha_expiracion.isoformat() if c.fecha_expiracion else None,
                'activa': c.activa
            })
            
        return jsonify({
            'success': True,
            'clientes': resultado
        })
    except Exception as e:
        log_error(f"Error listando clientes conecta: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/clientes-conecta/<int:gestoria_id>', methods=['PUT'])
@login_required
@require_super_admin
def actualizar_cliente_conecta(gestoria_id):
    """Actualiza los detalles de suscripción de un cliente conecta."""
    try:
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        data = request.json
        
        if 'plan' in data:
            gestoria.plan = data['plan']
        if 'max_certificados' in data:
            gestoria.max_certificados = data['max_certificados']
        if 'iages_active' in data:
            gestoria.iages_active = data['iages_active']
        if 'activa' in data:
            gestoria.activa = data['activa']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cliente actualizado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error actualizando cliente conecta: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/gestorias/<int:gestoria_id>', methods=['PUT'])
@login_required
@require_super_admin
def actualizar_gestoria(gestoria_id):
    """Actualiza una gestoría"""
    try:
        gestoria = Gestoria.query.get_or_404(gestoria_id)
        data = request.json
        
        if 'nombre' in data:
            gestoria.nombre = data['nombre']
        if 'email' in data:
            gestoria.email = data['email']
        if 'slug' in data:
            gestoria.slug = data['slug']
        if 'telefono' in data:
            gestoria.telefono = data['telefono']
        if 'direccion' in data:
            gestoria.direccion = data['direccion']
        if 'cif' in data:
            gestoria.cif = data['cif']
        if 'activa' in data:
            gestoria.activa = data['activa']
        if 'max_certificados' in data:
            gestoria.max_certificados = data['max_certificados']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Gestoría actualizada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error actualizando gestoría: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/gestorias/<int:gestoria_id>/cambiar-plan', methods=['POST'])
@login_required
@require_super_admin
def cambiar_plan_gestoria(gestoria_id):
    """Cambia el plan de una gestoría"""
    try:
        data = request.json
        nuevo_plan_id = data.get('plan_id')
        
        if not nuevo_plan_id:
            return jsonify({'error': 'plan_id requerido'}), 400
        
        # Verificar que el plan existe
        plan = PlanGestoria.query.get_or_404(nuevo_plan_id)
        
        # 🚀 Usar BillingService para sincronizar todos los modelos
        from services.billing_service import BillingService
        
        # El endpoint recibe plan_id, pero BillingService usa plan_codigo
        resultado = BillingService.cambiar_plan(
            gestoria_id=gestoria_id,
            nuevo_plan_codigo=plan.codigo,
            usuario_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': f'Plan cambiado a {plan.nombre} correctamente',
            'resultado': resultado
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error cambiando plan: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# GESTIÓN DE PLANES
# ============================================

@super_admin_bp.route('/planes', methods=['GET'])
@login_required
@require_super_admin
def listar_planes():
    """Lista todos los planes disponibles"""
    try:
        planes = PlanGestoria.query.filter_by(activo=True).all()
        return jsonify({
            'success': True,
            'planes': [p.to_dict() for p in planes]
        })
    except Exception as e:
        log_error(f"Error listando planes: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/planes/<int:plan_id>', methods=['PUT'])
@login_required
@require_super_admin
def actualizar_plan(plan_id):
    """Actualiza un plan existente"""
    try:
        plan = PlanGestoria.query.get_or_404(plan_id)
        data = request.json
        
        # Guardar valores anteriores para notificaciones
        cambios = []
        
        # Actualizar campos permitidos y registrar cambios
        if 'precio_mensual' in data:
            if plan.precio_mensual != float(data['precio_mensual']):
                cambios.append({
                    'campo': 'precio_mensual',
                    'anterior': str(plan.precio_mensual),
                    'nuevo': str(data['precio_mensual'])
                })
            plan.precio_mensual = float(data['precio_mensual'])
            
        if 'usuarios_max' in data:
            if plan.usuarios_max != int(data['usuarios_max']):
                cambios.append({
                    'campo': 'usuarios_max',
                    'anterior': str(plan.usuarios_max),
                    'nuevo': str(data['usuarios_max'])
                })
            plan.usuarios_max = int(data['usuarios_max'])
            
        if 'empresas_max' in data:
            if plan.empresas_max != int(data['empresas_max']):
                cambios.append({
                    'campo': 'empresas_max',
                    'anterior': str(plan.empresas_max),
                    'nuevo': str(data['empresas_max'])
                })
            plan.empresas_max = int(data['empresas_max'])
            
        if 'almacenamiento_gb' in data:
            if plan.almacenamiento_gb != int(data['almacenamiento_gb']):
                cambios.append({
                    'campo': 'almacenamiento_gb',
                    'anterior': str(plan.almacenamiento_gb),
                    'nuevo': str(data['almacenamiento_gb'])
                })
            plan.almacenamiento_gb = int(data['almacenamiento_gb'])
            
        if 'tokens_ia_mes' in data:
            if plan.tokens_ia_mes != int(data['tokens_ia_mes']):
                cambios.append({
                    'campo': 'tokens_ia_mes',
                    'anterior': str(plan.tokens_ia_mes),
                    'nuevo': str(data['tokens_ia_mes'])
                })
            plan.tokens_ia_mes = int(data['tokens_ia_mes'])
            
        if 'certificados_max' in data:
            if plan.certificados_max != int(data['certificados_max']):
                cambios.append({
                    'campo': 'certificados_max',
                    'anterior': str(plan.certificados_max),
                    'nuevo': str(data['certificados_max'])
                })
            plan.certificados_max = int(data['certificados_max'])
            
        if 'descripcion' in data:
            plan.descripcion = data['descripcion']
            
        if 'soporte_nivel' in data:
            if plan.soporte_nivel != data['soporte_nivel']:
                cambios.append({
                    'campo': 'soporte_nivel',
                    'anterior': plan.soporte_nivel,
                    'nuevo': data['soporte_nivel']
                })
            plan.soporte_nivel = data['soporte_nivel']
            
        if 'permite_branding' in data:
            if plan.permite_branding != bool(data['permite_branding']):
                cambios.append({
                    'campo': 'permite_branding',
                    'anterior': str(plan.permite_branding),
                    'nuevo': str(data['permite_branding'])
                })
            plan.permite_branding = bool(data['permite_branding'])
        
        db.session.commit()
        
        # Enviar notificaciones si hubo cambios
        if cambios:
            try:
                from services.notificaciones_planes import notificar_cambio_plan
                for cambio in cambios:
                    notificar_cambio_plan(
                        plan_id,
                        cambio['campo'],
                        cambio['anterior'],
                        cambio['nuevo']
                    )
            except Exception as e:
                log_warning(f"Error enviando notificaciones: {e}")
                # No fallar si las notificaciones fallan
        
        return jsonify({
            'success': True,
            'message': f'Plan {plan.nombre} actualizado correctamente',
            'plan': plan.to_dict(),
            'cambios_notificados': len(cambios)
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error actualizando plan: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/planes/<int:plan_id>/historial', methods=['GET'])
@login_required
@require_super_admin
def obtener_historial_plan(plan_id):
    """Obtiene el historial de cambios de un plan"""
    try:
        # Verificar que el plan existe
        plan = PlanGestoria.query.get_or_404(plan_id)
        
        # Obtener historial
        historial = PlanHistorial.query.filter_by(
            plan_id=plan_id
        ).order_by(desc(PlanHistorial.fecha_cambio)).limit(50).all()
        
        return jsonify({
            'success': True,
            'plan': {
                'id': plan.id,
                'nombre': plan.nombre
            },
            'historial': [h.to_dict() for h in historial]
        })
    except Exception as e:
        log_error(f"Error obteniendo historial: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# GESTIÓN DE USUARIOS GLOBAL
# ============================================

@super_admin_bp.route('/usuarios', methods=['GET'])
@login_required
@require_super_admin
def listar_usuarios_global():
    """Lista todos los usuarios de todas las gestorías"""
    try:
        # Filtros opcionales
        gestoria_id = request.args.get('gestoria_id', type=int)
        search = request.args.get('search', '')
        
        query = User.query
        
        if gestoria_id:
            query = query.filter_by(gestoria_id=gestoria_id)
        
        if search:
            query = query.filter(
                db.or_(
                    User.nombre.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        usuarios = query.all()
        
        resultado = []
        for u in usuarios:
            resultado.append({
                'id': u.id,
                'nombre': u.nombre,
                'email': u.email,
                'gestoria_id': u.gestoria_id,
                'gestoria_nombre': u.gestoria.nombre if u.gestoria else None,
                'departamento': u.departamento.nombre if u.departamento else None,
                'is_super_admin': u.is_super_admin,
                'activo': u.activo if hasattr(u, 'activo') else True
            })
        
        return jsonify({'success': True, 'usuarios': resultado})
    except Exception as e:
        log_error(f"Error listando usuarios: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# AUDITORÍA
# ============================================

@super_admin_bp.route('/auditoria', methods=['GET'])
@login_required
@require_super_admin
def listar_auditoria():
    """Lista registros de auditoría"""
    try:
        # Filtros
        gestoria_id = request.args.get('gestoria_id', type=int)
        dias = request.args.get('dias', 7, type=int)
        
        fecha_desde = datetime.utcnow() - timedelta(days=dias)
        
        query = AuditoriaAccesoGestoria.query.filter(
            AuditoriaAccesoGestoria.fecha >= fecha_desde
        )
        
        if gestoria_id:
            query = query.filter_by(gestoria_destino=gestoria_id)
        
        registros = query.order_by(desc(AuditoriaAccesoGestoria.fecha)).limit(100).all()
        
        return jsonify({
            'success': True,
            'registros': [r.to_dict() for r in registros]
        })
    except Exception as e:
        log_error(f"Error listando auditoría: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# ALERTAS
# ============================================

@super_admin_bp.route('/alertas', methods=['GET'])
@login_required
@require_super_admin
def listar_alertas():
    """Lista alertas del sistema"""
    try:
        # Filtros
        gestoria_id = request.args.get('gestoria_id', type=int)
        solo_no_leidas = request.args.get('solo_no_leidas', 'true') == 'true'
        
        query = AlertaSistema.query
        
        if gestoria_id:
            query = query.filter_by(gestoria_id=gestoria_id)
        
        if solo_no_leidas:
            query = query.filter_by(leida=False)
        
        alertas = query.order_by(desc(AlertaSistema.fecha_creacion)).limit(50).all()
        
        return jsonify({
            'success': True,
            'alertas': [a.to_dict() for a in alertas]
        })
    except Exception as e:
        log_error(f"Error listando alertas: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/alertas/<int:alerta_id>/marcar-leida', methods=['PUT'])
@login_required
@require_super_admin
def marcar_alerta_leida(alerta_id):
    """Marca una alerta como leída"""
    try:
        alerta = AlertaSistema.query.get_or_404(alerta_id)
        alerta.leida = True
        alerta.fecha_leida = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        log_error(f"Error marcando alerta: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# VERIFICACIÓN DE ALERTAS AUTOMÁTICAS
# ============================================

@super_admin_bp.route('/verificar-alertas', methods=['POST'])
@login_required
@require_super_admin
def verificar_alertas_manual():
    """Ejecuta la verificación de límites y genera alertas automáticamente"""
    try:
        from services.alertas_automaticas import verificar_limites_y_generar_alertas
        
        alertas_generadas = verificar_limites_y_generar_alertas()
        
        return jsonify({
            'success': True,
            'alertas_generadas': alertas_generadas,
            'mensaje': f'Verificación completada. {alertas_generadas} alertas generadas.'
        })
    except Exception as e:
        log_error(f"Error verificando alertas: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/limpiar-alertas', methods=['POST'])
@login_required
@require_super_admin
def limpiar_alertas_antiguas():
    """Limpia alertas leídas antiguas"""
    try:
        from services.alertas_automaticas import limpiar_alertas_antiguas
        
        dias = request.json.get('dias', 30) if request.json else 30
        alertas_eliminadas = limpiar_alertas_antiguas(dias)
        
        return jsonify({
            'success': True,
            'alertas_eliminadas': alertas_eliminadas,
            'mensaje': f'{alertas_eliminadas} alertas antiguas eliminadas.'
        })
    except Exception as e:
        log_error(f"Error limpiando alertas: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# CELERY MONITORING
# ============================================

@super_admin_bp.route('/celery/status', methods=['GET'])
@login_required
@require_super_admin
def celery_status():
    """Obtiene el estado de Celery y las tareas programadas"""
    try:
        from celery_config import celery
        
        # Obtener información de workers activos
        inspect = celery.control.inspect()
        
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        registered_tasks = inspect.registered()
        
        # Obtener configuración de beat
        beat_schedule = celery.conf.beat_schedule
        
        return jsonify({
            'success': True,
            'workers_activos': list(active_tasks.keys()) if active_tasks else [],
            'tareas_activas': active_tasks or {},
            'tareas_programadas': scheduled_tasks or {},
            'tareas_registradas': registered_tasks or {},
            'schedule': {
                name: {
                    'task': config['task'],
                    'schedule': str(config['schedule'])
                }
                for name, config in beat_schedule.items()
            }
        })
    except Exception as e:
        log_error(f"Error obteniendo estado de Celery: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'mensaje': 'Celery no está disponible o no está corriendo'
        }), 500

@super_admin_bp.route('/celery/ejecutar-tarea', methods=['POST'])
@login_required
@require_super_admin
def ejecutar_tarea_manual():
    """Ejecuta una tarea de Celery manualmente"""
    try:
        data = request.json
        tarea_nombre = data.get('tarea')
        
        if not tarea_nombre:
            return jsonify({'error': 'Nombre de tarea requerido'}), 400
        
        # Importar tareas disponibles
        from tasks import (
            verificar_limites_gestorias,
            limpiar_alertas_antiguas,
            generar_reporte_uso_mensual,
            actualizar_metricas_uso,
            test_task
        )
        
        tareas_disponibles = {
            'verificar_limites': verificar_limites_gestorias,
            'limpiar_alertas': limpiar_alertas_antiguas,
            'reporte_mensual': generar_reporte_uso_mensual,
            'actualizar_metricas': actualizar_metricas_uso,
            'test': test_task
        }
        
        if tarea_nombre not in tareas_disponibles:
            return jsonify({
                'error': f'Tarea no encontrada: {tarea_nombre}',
                'tareas_disponibles': list(tareas_disponibles.keys())
            }), 400
        
        # Ejecutar tarea
        tarea = tareas_disponibles[tarea_nombre]
        result = tarea.delay()
        
        return jsonify({
            'success': True,
            'tarea': tarea_nombre,
            'task_id': result.id,
            'mensaje': f'Tarea {tarea_nombre} ejecutada en background'
        })
    except Exception as e:
        log_error(f"Error ejecutando tarea: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================
# EXPORTACIÓN DE REPORTES
# ============================================

@super_admin_bp.route('/exportar-reporte', methods=['GET'])
@login_required
@require_super_admin
def exportar_reporte():
    """Exporta reportes en CSV o Excel"""
    try:
        from flask import send_file
        from services.reportes import (
            generar_reporte_uso,
            generar_reporte_alertas,
            generar_reporte_cambios_planes,
            exportar_a_csv,
            exportar_a_excel,
            generar_nombre_archivo
        )
        
        # Parámetros
        tipo = request.args.get('tipo', 'uso')
        formato = request.args.get('formato', 'csv')
        gestoria_id = request.args.get('gestoria_id', type=int)
        fecha_inicio_str = request.args.get('fecha_inicio')
        fecha_fin_str = request.args.get('fecha_fin')
        
        # Parsear fechas
        fecha_inicio = None
        fecha_fin = None
        
        if fecha_inicio_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
        
        if fecha_fin_str:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
        
        # Generar reporte según tipo
        if tipo == 'uso':
            df = generar_reporte_uso(fecha_inicio, fecha_fin, gestoria_id)
            nombre_hoja = 'Reporte de Uso'
        elif tipo == 'alertas':
            df = generar_reporte_alertas(fecha_inicio, fecha_fin, gestoria_id)
            nombre_hoja = 'Alertas'
        elif tipo == 'planes':
            df = generar_reporte_cambios_planes(fecha_inicio, fecha_fin, gestoria_id)
            nombre_hoja = 'Cambios de Planes'
        else:
            return jsonify({'error': 'Tipo de reporte no válido'}), 400
        
        # Verificar que hay datos
        if df.empty:
            return jsonify({'error': 'No hay datos para exportar'}), 404
        
        # Exportar según formato
        if formato == 'csv':
            output = exportar_a_csv(df)
            mimetype = 'text/csv'
        elif formato == 'excel':
            output = exportar_a_excel(df, nombre_hoja)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            return jsonify({'error': 'Formato no válido'}), 400
        
        # Generar nombre de archivo
        nombre_archivo = generar_nombre_archivo(tipo, formato, fecha_inicio, fecha_fin)
        
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        log_error(f"Error exportando reporte: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
# ============================================

# GESTIÓN DE USUARIOS SISTEMA (SUPER-ADMIN Y SOPORTE)

# ============================================



@super_admin_bp.route('/usuarios-sistema', methods=['GET'])

@login_required

@require_super_admin

def listar_usuarios_sistema():

    """Lista todos los usuarios super-admin y soporte"""

    try:

        # Solo usuarios super-admin y soporte (sin gestoria)

        usuarios = User.query.filter(

            db.or_(

                User.is_super_admin == True,

                User.is_soporte == True

            )

        ).order_by(User.id.desc()).all()

        

        return jsonify({

            'usuarios': [{

                'id': u.id,

                'nombre': u.nombre,

                'email': u.email,

                'is_super_admin': u.is_super_admin,

                'is_soporte': u.is_soporte,

                'activo': u.activo

            } for u in usuarios]

        })

        

    except Exception as e:

        log_error(f"Error listando usuarios: {e}")

        traceback.print_exc()

        return jsonify({'error': str(e)}), 500





@super_admin_bp.route('/usuarios-sistema', methods=['POST'])

@login_required

@require_super_admin

def crear_usuario_sistema():

    """Crea un nuevo usuario super-admin o soporte"""

    try:

        data = request.get_json()

        

        # Validaciones

        nombre = data.get('nombre', '').strip()

        email = data.get('email', '').strip().lower()

        password = data.get('password', '').strip()

        rol = data.get('rol', '').strip()  # 'super_admin' o 'soporte'

        

        if not all([nombre, email, password, rol]):

            return jsonify({'error': 'Todos los campos son requeridos'}), 400

        

        if rol not in ['super_admin', 'soporte']:

            return jsonify({'error': 'Rol inv��lido'}), 400

        

        if len(password) < 8:

            return jsonify({'error': 'La contraséa debe tener al menos 8 caracteres'}), 400

        

        # Verificar email único

        if User.query.filter_by(email=email).first():

            return jsonify({'error': 'El email ya está registrado'}), 400

        

        # Verificar límite de super-admins (máximo 5)

        if rol == 'super_admin':

            count_super_admins = User.query.filter_by(is_super_admin=True, activo=True).count()

            if count_super_admins >= 5:

                return jsonify({'error': 'Se ha alcanzado el límite máximo de 5 super-admins'}), 400

        

        # Crear usuario

        nuevo_usuario = User(

            nombre=nombre,

            email=email,

            password=generate_password_hash(password),

            is_super_admin=(rol == 'super_admin'),

            is_soporte=(rol == 'soporte'),

            activo=True,

            gestoria_id=None  # Sin gestoria

        )

        

        db.session.add(nuevo_usuario)

        db.session.commit()

        

        log_success(f"Usuario {rol} creado: {email}")

        

        return jsonify({

            'success': True,

            'usuario': {

                'id': nuevo_usuario.id,

                'nombre': nuevo_usuario.nombre,

                'email': nuevo_usuario.email,

                'is_super_admin': nuevo_usuario.is_super_admin,

                'is_soporte': nuevo_usuario.is_soporte,

                'activo': nuevo_usuario.activo

            }

        }), 201

        

    except Exception as e:

        db.session.rollback()

        log_error(f"Error creando usuario: {e}")

        traceback.print_exc()

        return jsonify({'error': str(e)}), 500





@super_admin_bp.route('/usuarios-sistema/<int:user_id>', methods=['PUT'])

@login_required

@require_super_admin

def editar_usuario_sistema(user_id):

    """Edita un usuario existente"""

    try:

        usuario = User.query.get_or_404(user_id)

        

        # No permitir editar usuarios de gestoria

        if usuario.gestoria_id is not None:

            return jsonify({'error': 'No se pueden editar usuarios de gestoria desde aqú'}), 400

        

        data = request.get_json()

        

        # Actualizar nombre

        if 'nombre' in data:

            nombre = data['nombre'].strip()

            if not nombre:

                return jsonify({'error': 'El nombre no puede estar vacío'}), 400

            usuario.nombre = nombre

        

        # Actualizar email

        if 'email' in data:

            email = data['email'].strip().lower()

            if not email:

                return jsonify({'error': 'El email no puede estar vacío'}), 400

            

            # Verificar que el email no está en uso por otro usuario

            otro_usuario = User.query.filter_by(email=email).first()

            if otro_usuario and otro_usuario.id != user_id:

                return jsonify({'error': 'El email ya está en uso'}), 400

            

            usuario.email = email

        

        # Actualizar contraseña (opcional)

        if 'password' in data and data['password']:

            password = data['password'].strip()

            if len(password) < 8:

                return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400

            usuario.password = generate_password_hash(password)

        

        db.session.commit()

        

        log_success(f"Usuario actualizado: {usuario.email}")

        

        return jsonify({

            'success': True,

            'usuario': {

                'id': usuario.id,

                'nombre': usuario.nombre,

                'email': usuario.email,

                'is_super_admin': usuario.is_super_admin,

                'is_soporte': usuario.is_soporte,

                'activo': usuario.activo

            }

        })

        

    except Exception as e:

        db.session.rollback()

        log_error(f"Error editando usuario: {e}")

        traceback.print_exc()

        return jsonify({'error': str(e)}), 500
        



@super_admin_bp.route('/usuarios/<int:user_id>', methods=['PUT'])
@login_required
@require_super_admin
def update_usuario_global(user_id):
    """Actualiza cualquier usuario del sistema (solo Super-Admin)"""
    try:
        usuario = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # No permitir que un super-admin se quite el privilegio de super-admin a sí mismo accidentalmente aquí
        # (Aunque usualmente hay otros mecanismos, es mejor ser prevenido)
        
        if 'nombre' in data:
            usuario.nombre = data['nombre'].strip()
            
        if 'email' in data:
            email = data['email'].strip().lower()
            existing = User.query.filter(User.email == email, User.id != user_id).first()
            if existing:
                return jsonify({'error': 'El email ya está en uso'}), 400
            usuario.email = email
            
        if 'rol_id' in data:
            # Si se asigna rol_id 0 o null, se quita el rol
            rol_id = data['rol_id']
            if rol_id and rol_id > 0:
                rol = Rol.query.get(rol_id)
                if rol:
                    usuario.rol_id = rol_id
                    # Sincronizar is_super_admin si el rol es el de sistema 'super-admin'
                    if rol.nombre == 'super-admin':
                        usuario.is_super_admin = True
                    else:
                        # Si se cambia a otro rol, quitar super_admin (opcional, depende de la lógica deseada)
                        # Por ahora mantenemos coherencia con routes_permisos.py
                        usuario.is_super_admin = False
                else:
                    return jsonify({'error': 'Rol no encontrado'}), 404
            else:
                usuario.rol_id = None
                usuario.is_super_admin = False

        if 'departamento_id' in data:
            dept_id = data['departamento_id']
            if dept_id and dept_id > 0:
                dept = Departamento.query.get(dept_id)
                if dept:
                    usuario.departamento_id = dept_id
                else:
                    return jsonify({'error': 'Departamento no encontrado'}), 404
            else:
                usuario.departamento_id = None

        if 'is_soporte' in data:
            usuario.is_soporte = bool(data['is_soporte'])

        if 'password' in data and data['password']:
            usuario.set_password(data['password'].strip())
            from auditoria import registrar_auditoria
            from flask_login import current_user
            registrar_auditoria('password_reset_superadmin', 'user', usuario.id, f'SuperAdmin {current_user.email} cambió la contraseña de {usuario.email}')

        db.session.commit()
        log_success(f"Usuario {usuario.email} actualizado globalmente por {current_user.email}")
        
        return jsonify({
            'success': True,
            'usuario': usuario.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"Error en update_usuario_global: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500





@super_admin_bp.route('/usuarios-sistema/<int:user_id>/toggle-status', methods=['POST'])

@login_required

@require_super_admin

def toggle_usuario_status(user_id):

    """Activa/desactiva un usuario"""

    try:

        usuario = User.query.get_or_404(user_id)

        

        # No permitir desactivar usuarios de gestoria

        if usuario.gestoria_id is not None:

            return jsonify({'error': 'No se pueden desactivar usuarios de gestoria desde aqú'}), 400

        

        # No permitir desactivarse a sí mismo

        if usuario.id == current_user.id:

            return jsonify({'error': 'No puedes desactivar tu propia cuenta'}), 400

        

        # Si es el último super-admin activo, no permitir desactivar

        if usuario.is_super_admin and usuario.activo:

            count_activos = User.query.filter_by(is_super_admin=True, activo=True).count()

            if count_activos <= 1:

                return jsonify({'error': 'No puedes desactivar el último super-admin activo'}), 400

        

        # Toggle status

        usuario.activo = not usuario.activo

        db.session.commit()

        

        estado = "activado" if usuario.activo else "desactivado"

        log_success(f"Usuario {estado}: {usuario.email}")

        

        return jsonify({

            'success': True,

            'activo': usuario.activo,

            'mensaje': f'Usuario {estado} correctamente'

        })

        

    except Exception as e:

        db.session.rollback()

        log_error(f"Error cambiando estado: {e}")

        traceback.print_exc()

        return jsonify({'error': str(e)}), 500



# Endpoints de Modo de Mantenimiento para Super-Admin
# Agregar a routes_super_admin.py

@super_admin_bp.route('/maintenance/status', methods=['GET'])
@login_required
@require_super_admin
def get_maintenance_status():
    """
    Obtiene el estado actual del modo de mantenimiento
    
    Returns:
        JSON con estado, mensaje y fechas programadas
    """
    try:
        from models import SystemConfig
        
        return jsonify({
            'success': True,
            'maintenance_mode': SystemConfig.is_maintenance_mode(),
            'message': SystemConfig.get_value('maintenance_message'),
            'start': SystemConfig.get_value('maintenance_start'),
            'end': SystemConfig.get_value('maintenance_end')
        })
    except Exception as e:
        print(f"❌ Error obteniendo estado de mantenimiento: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/maintenance/toggle', methods=['POST'])
@login_required
@require_super_admin
def toggle_maintenance_mode():
    """
    Activa o desactiva el modo de mantenimiento
    
    Body:
        enabled (bool): True para activar, False para desactivar
        delay_minutes (int): Minutos de advertencia antes de activar (default: 0)
        
    Returns:
        JSON con resultado de la operación
    """
    try:
        from models import SystemConfig
        from datetime import datetime, timedelta
        import threading
        
        data = request.get_json()
        enabled = data.get('enabled', False)
        delay_minutes = data.get('delay_minutes', 0)
        
        if not enabled:
            # Desactivar mantenimiento inmediatamente
            SystemConfig.set_value(
                'maintenance_mode',
                'false',
                current_user.id
            )
            # Limpiar token de programación al desactivar manualmente
            SystemConfig.set_value('maintenance_scheduled_token', '', current_user.id)
            
            # Emitir evento de desactivación
            try:
                socketio = current_app.extensions.get('socketio')
                if socketio:
                    socketio.emit('maintenance_deactivated', {
                        'message': 'El mantenimiento ha sido desactivado'
                    })
            except Exception as e:
                print(f"⚠️ Error emitiendo evento WebSocket: {e}")
            
            print(f"🛠️ Modo de mantenimiento desactivado por {current_user.nombre} (ID: {current_user.id})")
            
            return jsonify({
                'success': True,
                'maintenance_mode': False,
                'message': 'Modo de mantenimiento desactivado exitosamente'
            })
        
        # Activar mantenimiento
        if delay_minutes == 0:
            # Activación inmediata
            SystemConfig.set_value(
                'maintenance_mode',
                'true',
                current_user.id
            )
            
            # Emitir evento de activación inmediata
            try:
                socketio = current_app.extensions.get('socketio')
                if socketio:
                    socketio.emit('maintenance_activated', {
                        'message': SystemConfig.get_value('maintenance_message', 'Sistema en mantenimiento')
                    })
            except Exception as e:
                print(f"⚠️ Error emitiendo evento WebSocket: {e}")
            
            print(f"🛠️ Modo de mantenimiento activado INMEDIATAMENTE por {current_user.nombre}")
            
            return jsonify({
                'success': True,
                'maintenance_mode': True,
                'message': 'Modo de mantenimiento activado inmediatamente'
            })
        else:
            # Generar token único para esta programación
            import uuid
            scheduled_token = str(uuid.uuid4())
            SystemConfig.set_value('maintenance_scheduled_token', scheduled_token, current_user.id)
            
            # Activación programada con advertencia
            scheduled_time = datetime.utcnow() + timedelta(minutes=delay_minutes)
            
            # Emitir advertencia a todos los usuarios
            try:
                socketio = current_app.extensions.get('socketio')
                if socketio:
                    socketio.emit('maintenance_warning', {
                        'message': SystemConfig.get_value('maintenance_message', 'El sistema entrará en mantenimiento'),
                        'delay_minutes': delay_minutes,
                        'scheduled_time': scheduled_time.isoformat() + 'Z'
                    })
                    print(f"📢 Advertencia de mantenimiento enviada a todos los usuarios ({delay_minutes} min)")
            except Exception as e:
                print(f"⚠️ Error emitiendo advertencia WebSocket: {e}")
            
            # Programar activación automática con Celery
            try:
                from celery_worker import activate_scheduled_maintenance
                
                # Programar tarea con countdown en segundos (incluyendo el token)
                task = activate_scheduled_maintenance.apply_async(
                    args=[current_user.id],
                    kwargs={'scheduled_token': scheduled_token},
                    countdown=delay_minutes * 60
                )
                
                print(f"⏰ Mantenimiento programado con Celery (task_id: {task.id}) para dentro de {delay_minutes} min")
            except Exception as e:
                print(f"❌ Error programando tarea Celery: {e}")
                import traceback
                traceback.print_exc()
            
            return jsonify({
                'success': True,
                'maintenance_mode': False,  # Aún no activado
                'scheduled': True,
                'delay_minutes': delay_minutes,
                'scheduled_time': scheduled_time.isoformat() + 'Z',
                'message': f'Mantenimiento programado para dentro de {delay_minutes} minutos'
            })
        
    except Exception as e:
        print(f"❌ Error cambiando modo de mantenimiento: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/maintenance/message', methods=['PUT'])
@login_required
@require_super_admin
def update_maintenance_message():
    """
    Actualiza el mensaje mostrado durante el mantenimiento
    
    Body:
        message (str): Nuevo mensaje de mantenimiento
        
    Returns:
        JSON con resultado de la operación
    """
    try:
        from models import SystemConfig
        
        data = request.get_json()
        message = data.get('message', '')
        
        if not message or len(message.strip()) == 0:
            return jsonify({
                'error': 'El mensaje no puede estar vacío'
            }), 400
        
        # Actualizar mensaje
        SystemConfig.set_value('maintenance_message', message, current_user.id)
        
        print(f"📝 Mensaje de mantenimiento actualizado por {current_user.nombre}")
        
        return jsonify({
            'success': True,
            'message': 'Mensaje actualizado exitosamente',
            'new_message': message
        })
        
    except Exception as e:
        print(f"❌ Error actualizando mensaje de mantenimiento: {e}")
        return jsonify({'error': str(e)}), 500


@super_admin_bp.route('/maintenance/schedule', methods=['POST'])
@login_required
@require_super_admin
def schedule_maintenance():
    """
    Programa un mantenimiento futuro
    
    Body:
        start (str): Fecha/hora de inicio (ISO format)
        end (str): Fecha/hora de fin (ISO format)
        
    Returns:
        JSON con resultado de la operación
    """
    try:
        from models import SystemConfig
        from datetime import datetime
        
        data = request.get_json()
        start = data.get('start')
        end = data.get('end')
        
        # Validar fechas
        if start:
            try:
                datetime.fromisoformat(start.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Formato de fecha de inicio inválido'}), 400
        
        if end:
            try:
                datetime.fromisoformat(end.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'Formato de fecha de fin inválido'}), 400
        
        # Actualizar fechas
        if start:
            SystemConfig.set_value('maintenance_start', start, current_user.id)
        if end:
            SystemConfig.set_value('maintenance_end', end, current_user.id)
        
        print(f"📅 Mantenimiento programado por {current_user.username}: {start} - {end}")
        
        return jsonify({
            'success': True,
            'message': 'Mantenimiento programado exitosamente',
            'start': start,
            'end': end
        })
        
    except Exception as e:
        print(f"❌ Error programando mantenimiento: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================
# CONFIGURACIONES DE VERSIÓN (WEB & DESKTOP)
# ============================================

@super_admin_bp.route('/version-config', methods=['GET'])
@login_required
@require_super_admin
def get_version_config():
    """Obtiene las versiones actuales de Conecta y Web App y sus configuraciones"""
    try:
        claves = [
            'conecta_version', 'conecta_url', 'conecta_notes', 
            'conecta_mandatory', 'conecta_sha256', 'webapp_version'
        ]
        
        configs = ConfiguracionGlobal.query.filter(ConfiguracionGlobal.clave.in_(claves)).all()
        config_dict = {c.clave: c.valor for c in configs}
        
        return jsonify({
            'success': True,
            'config': {
                'conecta_version': config_dict.get('conecta_version', '1.2.0'),
                'conecta_url': config_dict.get('conecta_url', 'https://iages.es/updates/conecta-1.2.0-setup.exe'),
                'conecta_notes': config_dict.get('conecta_notes', ''),
                'conecta_mandatory': config_dict.get('conecta_mandatory', 'false') == 'true',
                'conecta_sha256': config_dict.get('conecta_sha256', ''),
                'webapp_version': config_dict.get('webapp_version', '1.4.7')
            }
        })
    except Exception as e:
        log_error(f"Error obteniendo version_config: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/version-config', methods=['POST'])
@login_required
@require_super_admin
def update_version_config():
    """Actualiza las configuraciones de versiones e inyecta webapp_version si cambió"""
    try:
        data = request.json
        claves_permitidas = {
            'conecta_version': 'string',
            'conecta_url': 'string',
            'conecta_notes': 'string',
            'conecta_mandatory': 'boolean',
            'conecta_sha256': 'string',
            'webapp_version': 'string'
        }
        
        # Verificar si la webapp_version cambiará para inyectar en el sw.js
        old_webapp_version = None
        new_webapp_version = data.get('webapp_version')
        webapp_record = ConfiguracionGlobal.query.filter_by(clave='webapp_version').first()
        if webapp_record:
            old_webapp_version = webapp_record.valor

        for clave, tipo in claves_permitidas.items():
            if clave in data:
                valor = str(data[clave]).lower() if tipo == 'boolean' else str(data[clave])
                config = ConfiguracionGlobal.query.filter_by(clave=clave).first()
                if config:
                    config.valor = valor
                    config.fecha_modificacion = datetime.utcnow()
                else:
                    db.session.add(ConfiguracionGlobal(
                        clave=clave, valor=valor, tipo=tipo,
                        modificable_por_gestoria=False
                    ))
        
        db.session.commit()
        
        # Inyectar versión en frontend/public/sw.js y frontend/dist/sw.js
        inject_success = True
        if new_webapp_version and new_webapp_version != old_webapp_version:
            import os
            import subprocess
            logger.info(f"Actualizando sw.js a la versión {new_webapp_version}")
            try:
                script_path = os.path.join(os.path.dirname(__file__), 'update_sw_version.py')
                # Run the script with the new version argument
                subprocess.run(['python3', script_path, new_webapp_version], check=True)
                
                # Emitir notificación websocket a todos los clientes conectados
                try:
                    socketio = current_app.extensions.get('socketio')
                    if socketio:
                        socketio.emit('pwa_update_available', {
                            'titulo': 'Actualización del Sistema',
                            'mensaje': f'Hay una nueva versión de la aplicación ({new_webapp_version}). Se aplicará en breves momentos.',
                            'version': new_webapp_version
                        })
                except Exception as ws_e:
                    logger.error(f"Fallo emitiendo notificación WS de PWA: {ws_e}")
                    
            except Exception as e_sw:
                logger.error(f"Fallo actualizando sw.js: {e_sw}")
                inject_success = False

        return jsonify({
            'success': True,
            'message': 'Configuraciones actualizadas correctamente' + (' (sw.js inyectado)' if inject_success else ' (falla inyección sw.js)'),
            'sw_updated': inject_success
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error actualizando version_config: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/upload-conecta-exe', methods=['POST'])
@login_required
@require_super_admin
def upload_conecta_exe():
    """Sube el archivo instalador de Conecta (.exe) al servidor"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró archivo en la petición'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
            
        if not file.filename.endswith('.exe'):
            return jsonify({'error': 'El archivo debe ser un instalador .exe'}), 400

        import os
        from werkzeug.utils import secure_filename
        
        filename = secure_filename(file.filename)
        
        # Determinar directorio de actualizaciones público
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(backend_dir)
        
        # Preferir ruta VPS si existe, sino ruta local
        vps_updates_dir = '/var/www/iages/frontend/public/updates'
        local_updates_dir = os.path.join(project_root, 'frontend', 'public', 'updates')
        
        # Intentaremos guardar también en dist para Nginx en VPS
        vps_dist_updates_dir = '/var/www/iages/frontend/dist/updates'
        
        save_dir = vps_updates_dir if os.path.exists('/var/www/iages') else local_updates_dir
        
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, filename)
        
        file.save(file_path)
        logger.info(f"Instalador guardado en: {file_path}")
        
        # Si estamos en VPS, copiar también a dist para que Nginx lo sirva inmediatamente 
        # sin necesidad de npm run build
        if os.path.exists('/var/www/iages'):
            os.makedirs(vps_dist_updates_dir, exist_ok=True)
            dist_file_path = os.path.join(vps_dist_updates_dir, filename)
            shutil.copy2(file_path, dist_file_path)
            logger.info(f"Instalador copiado a dist: {dist_file_path}")
            
        # Calcular hash SHA256 opcional
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
        file_hash = sha256_hash.hexdigest()
        
        public_url = f"https://iages.es/updates/{filename}"
        
        return jsonify({
            'success': True,
            'url': public_url,
            'sha256': file_hash,
            'message': 'Instalador subido correctamente'
        })
        
    except Exception as e:
        log_error(f"Error subiendo instalador: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# CONFIGURACIÓN DE FACTURACIÓN (IAGES)
# ============================================

@super_admin_bp.route('/billing-config', methods=['GET'])
@login_required
@require_super_admin
def get_billing_config():
    """Obtiene los datos de EmpresaEmisora (IAGES)"""
    try:
        from models_billing import EmpresaEmisora
        empresa = EmpresaEmisora.get_datos_iages()
        
        if not empresa:
            return jsonify({'success': True, 'config': None})
            
        return jsonify({
            'success': True,
            'config': {
                'nombre': empresa.nombre,
                'cif': empresa.cif,
                'direccion': empresa.direccion,
                'codigo_postal': empresa.codigo_postal,
                'ciudad': empresa.ciudad,
                'provincia': empresa.provincia,
                'pais': empresa.pais,
                'telefono': empresa.telefono,
                'email': empresa.email,
                'web': empresa.web,
                'iban': empresa.iban_decrypted,
                'swift': empresa.swift_decrypted,
                'banco': empresa.banco_decrypted
            }
        })
    except Exception as e:
        log_error(f"Error obteniendo billing config: {e}")
        return jsonify({'error': str(e)}), 500

@super_admin_bp.route('/billing-config', methods=['PUT'])
@login_required
@require_super_admin
def update_billing_config():
    """Actualiza los datos de EmpresaEmisora (IAGES)"""
    try:
        from models_billing import EmpresaEmisora
        data = request.json
        
        empresa = EmpresaEmisora.get_datos_iages()
        if not empresa:
            # Crear si no existe (raro, pero posible en un setup nuevo)
            empresa = EmpresaEmisora()
            db.session.add(empresa)
            
        # Actualizar campos básicos
        fields = ['nombre', 'cif', 'direccion', 'codigo_postal', 'ciudad', 'provincia', 'pais', 'telefono', 'email', 'web']
        for field in fields:
            if field in data:
                setattr(empresa, field, data[field])
                
        # Actualizar campos encriptados usando setters de propiedad
        if 'iban' in data:
            empresa.iban_decrypted = data['iban']
        if 'swift' in data:
            empresa.swift_decrypted = data['swift']
        if 'banco' in data:
            empresa.banco_decrypted = data['banco']
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Configuración de facturación actualizada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        log_error(f"Error actualizando billing config: {e}")
        return jsonify({'error': str(e)}), 500
