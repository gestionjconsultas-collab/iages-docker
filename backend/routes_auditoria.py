"""
Endpoints para Sistema de Auditoría y Status de Lectura
Agregar estas rutas a app.py usando: register_auditoria_routes(app)
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, desc, func
from extensions import db
from models import Documento, User, AuditoriaLog  # ✅ Importar desde models
from auditoria import registrar_auditoria, AccionesAuditoria  # ✅ Solo funciones helper
from decorators import admin_required, departamento_required
import logging
from constants import NotificationTypes

logger = logging.getLogger(__name__)

def register_auditoria_routes(app):
    """Registrar todas las rutas de auditoría y lectura"""
    
    # =========================================================================
    # ENDPOINTS DE STATUS DE LECTURA
    # =========================================================================
    
    @app.route('/api/documentos/<int:documento_id>/marcar-leido', methods=['POST'])
    @login_required
    def marcar_documento_leido(documento_id):
        """
        Marcar un documento como leído
        """
        try:
            documento = Documento.query.get_or_404(documento_id)
            
            # Verificar permisos
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                # Usuarios normales solo pueden marcar sus propios documentos
                if documento.asignado_a_id != current_user.id:
                    return jsonify({NotificationTypes.ERROR: "No tienes permiso para marcar este documento"}), 403
            
            # Marcar como leído
            documento.leido = True
            documento.fecha_lectura = datetime.utcnow()
            documento.leido_por_id = current_user.id
            
            db.session.commit()
            
            # Registrar en auditoría
            registrar_auditoria(
                accion=AccionesAuditoria.DOCUMENTO_LEIDO,
                entidad_tipo="documento",
                entidad_id=documento_id,
                descripcion=f"{current_user.nombre} leyó el documento {documento.nombre_archivo}",
                detalles={
                    "nombre_archivo": documento.nombre_archivo,
                    "categoria": documento.categoria,
                    "empresa_id": documento.empresa_id
                }
            )
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "mensaje": "Documento marcado como leído",
                "documento": documento.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Error al marcar documento como leído: {e}")
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/documentos/<int:documento_id>/marcar-no-leido', methods=['POST'])
    @login_required
    def marcar_documento_no_leido(documento_id):
        """
        Marcar un documento como no leído
        """
        try:
            documento = Documento.query.get_or_404(documento_id)
            
            # Verificar permisos
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                if documento.asignado_a_id != current_user.id:
                    return jsonify({NotificationTypes.ERROR: "No tienes permiso para modificar este documento"}), 403
            
            # Marcar como no leído
            documento.leido = False
            documento.fecha_lectura = None
            documento.leido_por_id = None
            
            db.session.commit()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                "mensaje": "Documento marcado como no leído",
                "documento": documento.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Error al marcar documento como no leído: {e}")
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/documentos/estadisticas-lectura', methods=['GET'])
    @login_required
    def estadisticas_lectura():
        """
        Estadísticas de lectura de documentos
        """
        try:
            gestoria_id = current_user.gestoria_id

            # FIX A-5: Siempre filtrar por gestoría para no mezclar datos entre tenants
            if current_user.departamento and current_user.departamento.nombre.strip().lower() == 'jefatura':
                # Jefatura ve todos los documentos de SU gestoría (no del sistema global)
                total = Documento.query.filter_by(gestoria_id=gestoria_id).count()
                leidos = Documento.query.filter_by(gestoria_id=gestoria_id, leido=True).count()
                no_leidos = Documento.query.filter_by(gestoria_id=gestoria_id, leido=False).count()
            else:
                total = Documento.query.filter_by(
                    asignado_a_id=current_user.id, gestoria_id=gestoria_id
                ).count()
                leidos = Documento.query.filter(
                    Documento.asignado_a_id == current_user.id,
                    Documento.gestoria_id == gestoria_id,
                    Documento.leido == True
                ).count()
                no_leidos = Documento.query.filter(
                    Documento.asignado_a_id == current_user.id,
                    Documento.gestoria_id == gestoria_id,
                    Documento.leido == False
                ).count()

            # Documentos leídos últimos 7 días (filtrado por gestoría)
            hace_7_dias = datetime.utcnow() - timedelta(days=7)
            leidos_recientes = Documento.query.filter(
                Documento.gestoria_id == gestoria_id,
                Documento.fecha_lectura >= hace_7_dias
            ).count()
            
            return jsonify({
                "total": total,
                "leidos": leidos,
                "no_leidos": no_leidos,
                "porcentaje_leidos": round((leidos / total * 100) if total > 0 else 0, 1),
                "leidos_ultimos_7_dias": leidos_recientes
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas de lectura: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINTS DE AUDITORÍA
    # =========================================================================
    
    @app.route('/api/auditoria/logs', methods=['GET'])
    @login_required
    @departamento_required('Jefatura')
    def obtener_logs_auditoria():
        """
        Obtener logs de auditoría con filtros
        Solo accesible por Jefatura
        
        Query params:
            - user_id: Filtrar por usuario
            - accion: Filtrar por tipo de acción
            - entidad_tipo: Filtrar por tipo de entidad
            - fecha_desde: Fecha inicio (ISO format)
            - fecha_hasta: Fecha fin (ISO format)
            - page: Número de página (default: 1)
            - per_page: Registros por página (default: 50)
        """
        try:
            # MULTI-TENANT: Filtrar por gestoria_id
            gestoria_id = current_user.gestoria_id
            
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 50, type=int), 200)
            
            # Construir query base con filtro de gestoría
            from sqlalchemy.orm import joinedload
            query = AuditoriaLog.query.options(
                joinedload(AuditoriaLog.user)  # ✅ Eager loading (relación correcta: 'user')
            ).filter(AuditoriaLog.gestoria_id == gestoria_id)
            
            # Filtros
            user_id = request.args.get('user_id', type=int)
            if user_id:
                query = query.filter(AuditoriaLog.user_id == user_id)
            
            accion = request.args.get('accion')
            if accion:
                query = query.filter(AuditoriaLog.accion == accion)
            
            entidad_tipo = request.args.get('entidad_tipo')
            if entidad_tipo:
                query = query.filter(AuditoriaLog.entidad_tipo == entidad_tipo)
            
            fecha_desde = request.args.get('fecha_desde')
            if fecha_desde:
                try:
                    # Parsear fecha y establecer hora al inicio del día
                    fecha_inicio = datetime.fromisoformat(fecha_desde).replace(hour=0, minute=0, second=0, microsecond=0)
                    query = query.filter(AuditoriaLog.fecha_creacion >= fecha_inicio)
                except ValueError:
                    pass  # Ignorar si el formato es inválido
            
            fecha_hasta = request.args.get('fecha_hasta')
            if fecha_hasta:
                try:
                    # Parsear fecha y establecer hora al final del día
                    fecha_fin = datetime.fromisoformat(fecha_hasta).replace(hour=23, minute=59, second=59, microsecond=999999)
                    query = query.filter(AuditoriaLog.fecha_creacion <= fecha_fin)
                except ValueError:
                    pass  # Ignorar si el formato es inválido
            
            # Ordenar por fecha descendente
            query = query.order_by(desc(AuditoriaLog.fecha_creacion))
            
            # Paginar
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                "logs": [log.to_dict() for log in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "total_pages": pagination.pages
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener logs de auditoría: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/auditoria/estadisticas', methods=['GET'])
    @login_required
    @departamento_required('Jefatura')
    def estadisticas_auditoria():
        """
        Estadísticas generales de auditoría
        """
        try:
            # MULTI-TENANT: Filtrar por gestoria_id
            gestoria_id = current_user.gestoria_id
            
            # Total de logs de esta gestoría
            total_logs = AuditoriaLog.query.filter_by(gestoria_id=gestoria_id).count()
            
            # Logs últimos 7 días de esta gestoría
            hace_7_dias = datetime.utcnow() - timedelta(days=7)
            logs_recientes = AuditoriaLog.query.filter(
                AuditoriaLog.gestoria_id == gestoria_id,
                AuditoriaLog.fecha_creacion >= hace_7_dias
            ).count()
            
            # Top 5 acciones más frecuentes de esta gestoría
            top_acciones = db.session.query(
                AuditoriaLog.accion,
                func.count(AuditoriaLog.id).label('count')
            ).filter(
                AuditoriaLog.gestoria_id == gestoria_id
            ).group_by(AuditoriaLog.accion).order_by(desc('count')).limit(5).all()
            
            # Top 5 usuarios más activos de esta gestoría
            top_usuarios = db.session.query(
                AuditoriaLog.user_nombre,
                AuditoriaLog.user_email,
                func.count(AuditoriaLog.id).label('count')
            ).filter(
                AuditoriaLog.gestoria_id == gestoria_id
            ).group_by(
                AuditoriaLog.user_nombre,
                AuditoriaLog.user_email
            ).order_by(desc('count')).limit(5).all()
            
            # Logs por día (últimos 30 días) de esta gestoría
            hace_30_dias = datetime.utcnow() - timedelta(days=30)
            logs_por_dia = db.session.query(
                func.date(AuditoriaLog.fecha_creacion).label('fecha'),
                func.count(AuditoriaLog.id).label('count')
            ).filter(
                AuditoriaLog.gestoria_id == gestoria_id,
                AuditoriaLog.fecha_creacion >= hace_30_dias
            ).group_by(
                func.date(AuditoriaLog.fecha_creacion)
            ).order_by('fecha').all()
            
            return jsonify({
                "total_logs": total_logs,
                "logs_ultimos_7_dias": logs_recientes,
                "top_acciones": [{"accion": a, "count": c} for a, c in top_acciones],
                "top_usuarios": [{"nombre": n, "email": e, "count": c} for n, e, c in top_usuarios],
                "actividad_diaria": [{"fecha": str(f), "count": c} for f, c in logs_por_dia]
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas de auditoría: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/auditoria/usuario/<int:user_id>', methods=['GET'])
    @login_required
    def historial_usuario(user_id):
        """
        Ver historial de un usuario específico
        Jefatura puede ver cualquier usuario
        Usuarios normales solo pueden ver su propio historial
        """
        try:
            # Verificar permisos
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura' and current_user.id != user_id:
                return jsonify({NotificationTypes.ERROR: "No tienes permiso para ver este historial"}), 403
            
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 200)
            
            # MULTI-TENANT: Filtrar por gestoria_id
            gestoria_id = current_user.gestoria_id
            
            # Obtener logs del usuario filtrando por gestoria_id
            pagination = AuditoriaLog.query.filter_by(
                user_id=user_id,
                gestoria_id=gestoria_id
            ).order_by(
                desc(AuditoriaLog.fecha_creacion)
            ).paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                "logs": [log.to_dict() for log in pagination.items],
                "total": pagination.total,
                "page": page,
                "per_page": per_page,
                "total_pages": pagination.pages
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener historial de usuario: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/auditoria/tipos-accion', methods=['GET'])
    @login_required
    @departamento_required('Jefatura')
    def tipos_accion_disponibles():
        """
        Obtener lista de todos los tipos de acciones disponibles
        """
        try:
            # MULTI-TENANT: Filtrar por gestoria_id
            gestoria_id = current_user.gestoria_id
            
            # Obtener acciones únicas que existen en la BD de esta gestoría
            acciones_en_uso = db.session.query(
                AuditoriaLog.accion,
                func.count(AuditoriaLog.id).label('count')
            ).filter(
                AuditoriaLog.gestoria_id == gestoria_id
            ).group_by(AuditoriaLog.accion).all()
            
            return jsonify({
                "acciones_en_uso": [{"accion": a, "count": c} for a, c in acciones_en_uso]
            }), 200
            
        except Exception as e:
            logger.error(f"Error al obtener tipos de acción: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    logger.info("✅ Rutas de auditoría y lectura registradas")