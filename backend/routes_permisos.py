"""
Endpoints para Sistema de Roles y Permisos (RBAC)
Agregar estas rutas a app.py usando: register_permisos_routes(app)
"""

from flask import jsonify, request
from flask_login import login_required, current_user
from extensions import db
from models import Rol, Permiso, RolPermiso, User
from decorators import super_admin_required
import logging
from constants import NotificationTypes

logger = logging.getLogger(__name__)

def register_permisos_routes(app):
    """Registrar todas las rutas de permisos y roles"""
    
    # =========================================================================
    # ENDPOINTS DE ROLES
    # =========================================================================
    
    @app.route('/api/admin/roles', methods=['GET'])
    @login_required
    @super_admin_required
    def get_roles():
        """Listar todos los roles (solo super-admin)"""
        try:
            roles = Rol.query.order_by(Rol.es_sistema.desc(), Rol.nombre).all()
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'roles': [r.to_dict() for r in roles]
            })
        except Exception as e:
            logger.error(f"Error al obtener roles: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles', methods=['POST'])
    @login_required
    @super_admin_required
    def create_rol():
        """Crear nuevo rol"""
        try:
            data = request.json
            
            # Validaciones
            if not data.get('nombre'):
                return jsonify({NotificationTypes.ERROR: 'El nombre es requerido'}), 400
            
            # Verificar que no exista
            existing = Rol.query.filter_by(
                nombre=data['nombre'],
                gestoria_id=data.get('gestoria_id')
            ).first()
            
            if existing:
                return jsonify({NotificationTypes.ERROR: 'Ya existe un rol con ese nombre'}), 400
            
            rol = Rol(
                nombre=data['nombre'],
                descripcion=data.get('descripcion'),
                gestoria_id=data.get('gestoria_id'),
                es_sistema=False,
                activo=True
            )
            
            db.session.add(rol)
            db.session.commit()
            
            logger.info(f"Rol creado: {rol.nombre} (ID={rol.id})")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'rol': rol.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear rol: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles/<int:rol_id>', methods=['PUT'])
    @login_required
    @super_admin_required
    def update_rol(rol_id):
        """Actualizar rol"""
        try:
            rol = Rol.query.get_or_404(rol_id)
            
            if rol.es_sistema:
                return jsonify({NotificationTypes.ERROR: 'No se pueden editar roles del sistema'}), 403
            
            data = request.json
            
            if 'nombre' in data:
                rol.nombre = data['nombre']
            if 'descripcion' in data:
                rol.descripcion = data['descripcion']
            if 'activo' in data:
                rol.activo = data['activo']
            
            db.session.commit()
            
            logger.info(f"Rol actualizado: {rol.nombre} (ID={rol.id})")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'rol': rol.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar rol: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles/<int:rol_id>', methods=['DELETE'])
    @login_required
    @super_admin_required
    def delete_rol(rol_id):
        """Eliminar rol"""
        try:
            rol = Rol.query.get_or_404(rol_id)
            
            if rol.es_sistema:
                return jsonify({NotificationTypes.ERROR: 'No se pueden eliminar roles del sistema'}), 403
            
            # Verificar que no haya usuarios con este rol
            if rol.usuarios:
                return jsonify({
                    NotificationTypes.ERROR: f'No se puede eliminar un rol con {len(rol.usuarios)} usuario(s) asignado(s)'
                }), 400
            
            nombre = rol.nombre
            db.session.delete(rol)
            db.session.commit()
            
            logger.info(f"Rol eliminado: {nombre} (ID={rol_id})")
            
            return jsonify({NotificationTypes.SUCCESS: True})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al eliminar rol: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINTS DE PERMISOS
    # =========================================================================
    
    @app.route('/api/admin/permisos', methods=['GET'])
    @login_required
    @super_admin_required
    def get_permisos():
        """Listar todos los permisos"""
        try:
            # Agrupar por módulo
            modulo = request.args.get('modulo')
            
            query = Permiso.query
            if modulo:
                query = query.filter_by(modulo=modulo)
            
            permisos = query.order_by(Permiso.modulo, Permiso.recurso, Permiso.accion).all()
            
            # Agrupar por módulo para mejor organización
            permisos_por_modulo = {}
            for p in permisos:
                mod = p.modulo or 'otros'
                if mod not in permisos_por_modulo:
                    permisos_por_modulo[mod] = []
                permisos_por_modulo[mod].append(p.to_dict())
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'permisos': [p.to_dict() for p in permisos],
                'permisos_por_modulo': permisos_por_modulo
            })
            
        except Exception as e:
            logger.error(f"Error al obtener permisos: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/permisos', methods=['POST'])
    @login_required
    @super_admin_required
    def create_permiso():
        """Crear nuevo permiso"""
        try:
            data = request.json
            
            # Validaciones
            if not data.get('codigo'):
                return jsonify({NotificationTypes.ERROR: 'El código es requerido'}), 400
            if not data.get('nombre'):
                return jsonify({NotificationTypes.ERROR: 'El nombre es requerido'}), 400
            
            # Verificar que no exista
            existing = Permiso.query.filter_by(codigo=data['codigo']).first()
            if existing:
                return jsonify({NotificationTypes.ERROR: 'Ya existe un permiso con ese código'}), 400
            
            permiso = Permiso(
                codigo=data['codigo'],
                nombre=data['nombre'],
                descripcion=data.get('descripcion'),
                modulo=data.get('modulo'),
                recurso=data.get('recurso'),
                accion=data.get('accion'),
                ruta=data.get('ruta'),
                icono=data.get('icono'),
                es_sistema=False,
                activo=True
            )
            
            db.session.add(permiso)
            db.session.commit()
            
            logger.info(f"Permiso creado: {permiso.codigo} (ID={permiso.id})")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'permiso': permiso.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al crear permiso: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/permisos/<int:permiso_id>', methods=['PUT'])
    @login_required
    @super_admin_required
    def update_permiso(permiso_id):
        """Actualizar permiso"""
        try:
            permiso = Permiso.query.get_or_404(permiso_id)
            
            if permiso.es_sistema:
                return jsonify({NotificationTypes.ERROR: 'No se pueden editar permisos del sistema'}), 403
            
            data = request.json
            
            if 'nombre' in data:
                permiso.nombre = data['nombre']
            if 'descripcion' in data:
                permiso.descripcion = data['descripcion']
            if 'modulo' in data:
                permiso.modulo = data['modulo']
            if 'activo' in data:
                permiso.activo = data['activo']
            
            db.session.commit()
            
            logger.info(f"Permiso actualizado: {permiso.codigo} (ID={permiso.id})")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'permiso': permiso.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al actualizar permiso: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/permisos/<int:permiso_id>', methods=['DELETE'])
    @login_required
    @super_admin_required
    def delete_permiso(permiso_id):
        """Eliminar permiso"""
        try:
            permiso = Permiso.query.get_or_404(permiso_id)
            
            if permiso.es_sistema:
                return jsonify({NotificationTypes.ERROR: 'No se pueden eliminar permisos del sistema'}), 403
            
            codigo = permiso.codigo
            db.session.delete(permiso)
            db.session.commit()
            
            logger.info(f"Permiso eliminado: {codigo} (ID={permiso_id})")
            
            return jsonify({NotificationTypes.SUCCESS: True})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al eliminar permiso: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINTS DE ASIGNACIÓN ROL-PERMISO
    # =========================================================================
    
    @app.route('/api/admin/roles/<int:rol_id>/permisos', methods=['GET'])
    @login_required
    @super_admin_required
    def get_rol_permisos(rol_id):
        """Obtener permisos de un rol"""
        try:
            rol = Rol.query.get_or_404(rol_id)
            permisos = [rp.permiso.to_dict() for rp in rol.permisos if rp.permiso.activo]
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'rol': rol.to_dict(),
                'permisos': permisos
            })
            
        except Exception as e:
            logger.error(f"Error al obtener permisos del rol: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles/<int:rol_id>/permisos/<int:permiso_id>', methods=['POST'])
    @login_required
    @super_admin_required
    def assign_permiso_to_rol(rol_id, permiso_id):
        """Asignar permiso a rol"""
        try:
            rol = Rol.query.get_or_404(rol_id)
            permiso = Permiso.query.get_or_404(permiso_id)
            
            # Verificar que no exista ya
            existing = RolPermiso.query.filter_by(
                rol_id=rol_id,
                permiso_id=permiso_id
            ).first()
            
            if existing:
                return jsonify({NotificationTypes.ERROR: 'Permiso ya asignado a este rol'}), 400
            
            rol_permiso = RolPermiso(
                rol_id=rol_id,
                permiso_id=permiso_id
            )
            
            db.session.add(rol_permiso)
            db.session.commit()
            
            logger.info(f"Permiso {permiso.codigo} asignado a rol {rol.nombre}")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': f'Permiso {permiso.nombre} asignado a {rol.nombre}'
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al asignar permiso: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles/<int:rol_id>/permisos/<int:permiso_id>', methods=['DELETE'])
    @login_required
    @super_admin_required
    def remove_permiso_from_rol(rol_id, permiso_id):
        """Remover permiso de rol"""
        try:
            rol_permiso = RolPermiso.query.filter_by(
                rol_id=rol_id,
                permiso_id=permiso_id
            ).first_or_404()
            
            rol_nombre = rol_permiso.rol.nombre
            permiso_codigo = rol_permiso.permiso.codigo
            
            db.session.delete(rol_permiso)
            db.session.commit()
            
            logger.info(f"Permiso {permiso_codigo} removido de rol {rol_nombre}")
            
            return jsonify({NotificationTypes.SUCCESS: True})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al remover permiso: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/roles/<int:rol_id>/permisos/batch', methods=['POST'])
    @login_required
    @super_admin_required
    def assign_permisos_batch(rol_id):
        """Asignar múltiples permisos a un rol de una vez"""
        try:
            rol = Rol.query.get_or_404(rol_id)
            data = request.json
            permisos_ids = data.get('permisos_ids', [])
            
            if not permisos_ids:
                return jsonify({NotificationTypes.ERROR: 'No se proporcionaron permisos'}), 400
            
            # Eliminar asignaciones existentes si replace=true
            if data.get('replace', False):
                RolPermiso.query.filter_by(rol_id=rol_id).delete()
            
            # Agregar nuevas asignaciones
            added = 0
            for permiso_id in permisos_ids:
                # Verificar que no exista
                existing = RolPermiso.query.filter_by(
                    rol_id=rol_id,
                    permiso_id=permiso_id
                ).first()
                
                if not existing:
                    rol_permiso = RolPermiso(
                        rol_id=rol_id,
                        permiso_id=permiso_id
                    )
                    db.session.add(rol_permiso)
                    added += 1
            
            db.session.commit()
            
            logger.info(f"{added} permisos asignados a rol {rol.nombre}")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': f'{added} permisos asignados',
                'total': added
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al asignar permisos en batch: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINT DE PERMISOS DEL USUARIO ACTUAL
    # =========================================================================
    
    @app.route('/api/mis-permisos', methods=['GET'])
    @login_required
    def get_mis_permisos():
        """Obtener permisos del usuario actual"""
        try:
            permisos = current_user.obtener_permisos()
            
            # Simplificar objeto rol para no exponer metadatos innecesarios al frontend
            rol_simplificado = None
            if current_user.rol:
                rol_simplificado = {
                    'nombre': current_user.rol.nombre,
                    'descripcion': current_user.rol.descripcion
                }

            return jsonify({
                NotificationTypes.SUCCESS: True,
                'permisos': permisos,
                'is_super_admin': current_user.is_super_admin,
                'rol': rol_simplificado
            })
            
        except Exception as e:
            logger.error(f"Error al obtener permisos del usuario: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINT DE USUARIOS CON ROLES
    # =========================================================================
    
    @app.route('/api/admin/usuarios/<int:user_id>/rol', methods=['PUT'])
    @login_required
    @super_admin_required
    def assign_rol_to_user(user_id):
        """Asignar rol a usuario"""
        try:
            user = User.query.get_or_404(user_id)
            data = request.json
            rol_id = data.get('rol_id')
            
            # Guardar estado anterior para logging
            was_super_admin = user.is_super_admin
            old_rol = user.rol.nombre if user.rol else 'Sin rol'
            
            if rol_id:
                rol = Rol.query.get_or_404(rol_id)
                user.rol_id = rol_id
                
                # IMPORTANTE: Si el usuario era super-admin y se le asigna otro rol,
                # debe perder el privilegio de super-admin
                if was_super_admin and rol.nombre != 'super-admin':
                    user.is_super_admin = False
                    logger.warning(f"Usuario {user.nombre} degradado de super-admin a {rol.nombre}")
                
                mensaje = f'Rol {rol.nombre} asignado a {user.nombre}'
            else:
                user.rol_id = None
                # Si se remueve el rol, también remover super-admin
                if was_super_admin:
                    user.is_super_admin = False
                mensaje = f'Rol removido de {user.nombre}'
            
            db.session.commit()
            
            logger.info(f"{mensaje} (anterior: {old_rol}, super-admin: {was_super_admin} -> {user.is_super_admin})")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': mensaje,
                'user': user.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al asignar rol a usuario: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/usuarios', methods=['GET'])
    @login_required
    @super_admin_required
    def get_all_usuarios_rbac():
        """Obtener TODOS los usuarios para gestión RBAC (sin filtro de gestoría)"""
        try:
            users = User.query.order_by(User.nombre).all()
            
            # Enriquecer con información del rol
            users_data = []
            for user in users:
                user_dict = user.to_dict()
                # Agregar nombre del rol
                if user.rol:
                    user_dict['rol_nombre'] = user.rol.nombre
                    user_dict['rol_id'] = user.rol.id
                else:
                    user_dict['rol_nombre'] = None
                    user_dict['rol_id'] = None
                
                # Agregar permisos
                user_dict['permisos'] = user.obtener_permisos()
                
                users_data.append(user_dict)
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'users': users_data
            })
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios para RBAC: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # =========================================================================
    # ENDPOINTS DE PERMISOS INDIVIDUALES DE USUARIOS
    # =========================================================================
    
    @app.route('/api/admin/usuarios/<int:user_id>/permisos-individuales', methods=['GET'])
    @login_required
    @super_admin_required
    def get_user_permisos_individuales(user_id):
        """Obtener permisos individuales de un usuario"""
        try:
            from models import UserPermiso
            user = User.query.get_or_404(user_id)
            permisos = UserPermiso.query.filter_by(user_id=user_id).all()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'user': user.to_dict(),
                'permisos_individuales': [p.to_dict() for p in permisos]
            })
            
        except Exception as e:
            logger.error(f"Error al obtener permisos individuales: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/usuarios/<int:user_id>/permisos-individuales/<int:permiso_id>', methods=['POST'])
    @login_required
    @super_admin_required
    def add_user_permiso_individual(user_id, permiso_id):
        """Asignar permiso individual a usuario"""
        try:
            from models import UserPermiso
            user = User.query.get_or_404(user_id)
            permiso = Permiso.query.get_or_404(permiso_id)
            
            # Verificar que no exista ya
            existing = UserPermiso.query.filter_by(
                user_id=user_id,
                permiso_id=permiso_id
            ).first()
            
            if existing:
                return jsonify({NotificationTypes.ERROR: 'Permiso ya asignado a este usuario'}), 400
            
            data = request.json or {}
            user_permiso = UserPermiso(
                user_id=user_id,
                permiso_id=permiso_id,
                asignado_por=current_user.id,
                notas=data.get('notas')
            )
            
            db.session.add(user_permiso)
            db.session.commit()
            
            logger.info(f"Permiso individual {permiso.codigo} asignado a {user.nombre} por {current_user.nombre}")
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': f'Permiso {permiso.nombre} asignado a {user.nombre}',
                'permiso': user_permiso.to_dict()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al asignar permiso individual: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    @app.route('/api/admin/usuarios/<int:user_id>/permisos-individuales/<int:permiso_id>', methods=['DELETE'])
    @login_required
    @super_admin_required
    def remove_user_permiso_individual(user_id, permiso_id):
        """Remover permiso individual de usuario"""
        try:
            from models import UserPermiso
            user_permiso = UserPermiso.query.filter_by(
                user_id=user_id,
                permiso_id=permiso_id
            ).first_or_404()
            
            user_nombre = user_permiso.user.nombre
            permiso_codigo = user_permiso.permiso.codigo
            
            db.session.delete(user_permiso)
            db.session.commit()
            
            logger.info(f"Permiso individual {permiso_codigo} removido de {user_nombre}")
            
            return jsonify({NotificationTypes.SUCCESS: True})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al remover permiso individual: {e}")
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    logger.info("✅ Rutas de permisos y roles registradas")
