# backend/routes_mesa_trabajo.py
"""
Mesa de Trabajo - Command Center para procesamiento unificado de documentos
Endpoints para gestión centralizada de documentos pendientes
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from datetime import datetime
import re
import os
import shutil
import traceback

from extensions import db
from models import Documento, Empresa, User, Plantilla
from models_fiscal import DocumentoFiscal, TipoDocumentoFiscal
from auditoria import auditar, registrar_auditoria, AccionesAuditoria
from decorators import admin_required
from constants import DocumentCategories, NotificationTypes
import logging

logger = logging.getLogger(__name__)


def register_mesa_trabajo_routes(app):
    """Registrar rutas de Mesa de Trabajo"""
    
    @app.route('/api/mesa-trabajo/pendientes', methods=['GET'])
    @login_required
    def get_documentos_pendientes():
        """
        Obtiene todos los documentos pendientes de procesamiento de todas las empresas
        con filtros y paginación
        """
        try:
            # Parámetros de filtrado
            empresa_id = request.args.get('empresa_id', type=int)
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            search = request.args.get('search', '').strip()
            
                        # MULTI-TENANT: Filtrar por gestoría del usuario actual
            from tenant_utils import get_current_gestoria_id
            gestoria_id = get_current_gestoria_id()
            
            # ✅ CORRECCIÓN 1: Query base simplificado - Solo documentos en DocumentCategories.POR_PROCESAR
            # Una vez que se mueven a otra carpeta, desaparecen de la mesa de trabajo
            from sqlalchemy.orm import joinedload
            from constants import DocumentCategories
            
            query = Documento.query.options(
                joinedload(Documento.empresa)  # ✅ Eager loading para evitar N+1
            ).filter(
                Documento.categoria == DocumentCategories.POR_PROCESAR,
                Documento.gestoria_id == gestoria_id
            )
            
            # Aplicar permisos por departamento (solo si NO es Jefatura)
            # Jefatura ve TODOS los documentos pendientes
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                query = query.filter(
                    or_(
                        Documento.estado_tarea == None,
                        Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'),
                        Documento.asignado_a_id == current_user.id
                    )
                )
            # Si es Jefatura, no aplicar filtros - ve todo
            
            # Filtro por empresa
            if empresa_id:
                query = query.filter_by(empresa_id=empresa_id)
            
            # Búsqueda por nombre
            if search:
                query = query.filter(Documento.nombre_archivo.ilike(f'%{search}%'))
            
            # Ordenar por más recientes primero
            query = query.order_by(Documento.fecha_creacion.desc())
            
            # Paginación
            total = query.count()
            documentos = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # Serializar con datos de empresa
            docs_data = []
            for doc in documentos:
                doc_dict = doc.to_dict()
                doc_dict['empresa'] = {
                    'id': doc.empresa.id,
                    'nombre': doc.empresa.nombre,
                    'nif': doc.empresa.nif
                } if doc.empresa else None
                docs_data.append(doc_dict)
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'documentos': docs_data,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }), 200
            
        except Exception as e:
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/mesa-trabajo/accion-combinada', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_ACTUALIZADO,
        entidad_tipo='documento'
    )
    def ejecutar_accion_combinada():
        """
        Ejecuta múltiples acciones sobre un documento en una sola operación:
        1. Mover a carpeta
        2. Asignar tarea
        3. Procesar con IA
        4. Enviar email
        """
        try:
            data = request.json
            doc_id = data.get('documento_id')
            
            doc = db.session.get(Documento, doc_id)
            if not doc:
                return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
                
            # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
            from tenant_utils import get_current_gestoria_id
            if doc.gestoria_id != get_current_gestoria_id():
                return jsonify({NotificationTypes.ERROR: 'Acceso denegado: El documento pertenece a otra gestoría'}), 403
            
            acciones_realizadas = []
            task_id = None
            
            # ============================================
            # ACCIÓN 1: MOVER A CARPETA (BD Y FÍSICO)
            # ============================================
            if data.get('mover_a_carpeta'):
                categoria_anterior = doc.categoria
                nueva_categoria = data['mover_a_carpeta']
                
                # 1. Asegurar que tenemos la ruta física real (auto-reparar si es necesario)
                from utils.storage_utils import resolve_document_path
                current_path = resolve_document_path(doc)
                
                # 2. Intentar mover el archivo físico si es posible
                if current_path and os.path.exists(current_path):
                    try:
                        from utils.storage_utils import get_empresa_storage_path
                        
                        # Obtener ruta base de la empresa
                        empresa_nombre = doc.empresa.nombre
                        gestoria_id = doc.gestoria_id
                        base_dir = get_empresa_storage_path(gestoria_id, empresa_nombre)
                        
                        # Carpeta destino (ej: storage/gestoria_1/Empresa/Seguros Sociales/)
                        dest_dir = os.path.join(base_dir, nueva_categoria)
                        os.makedirs(dest_dir, exist_ok=True)
                        
                        filename = doc.nombre_archivo
                        dest_path = os.path.join(dest_dir, filename)
                        
                        # Evitar colisión de nombres
                        if os.path.exists(dest_path) and dest_path != current_path:
                            name, ext = os.path.splitext(filename)
                            dest_path = os.path.join(dest_dir, f"{name}_rev1{ext}")
                            filename = os.path.basename(dest_path)
                        
                        # Mover físicamente
                        if dest_path != current_path:
                            shutil.move(current_path, dest_path)
                            doc.ruta_archivo = dest_path
                            doc.nombre_archivo = filename
                            logger.info(f"Archivo movido físicamente: {current_path} -> {dest_path}")
                            
                    except Exception as move_err:
                        logger.error(f"Error moviendo archivo físico: {move_err}")
                        # Si falla el movimiento físico crítico, podríamos lanzar error 500
                        # Pero por ahora logueamos y seguimos para no bloquear la BD si el usuario ya lo movió a mano
                else:
                    logger.warning(f"No se pudo encontrar el archivo físico para mover: {doc.ruta_archivo}")
                
                # Actualizar BD
                doc.categoria = nueva_categoria
                
                acciones_realizadas.append({
                    'tipo': 'mover',
                    'de': categoria_anterior,
                    'a': nueva_categoria,
                    'ruta_final': doc.ruta_archivo
                })
            
            # ============================================
            # ACCIÓN 2: ASIGNAR TAREA
            # ============================================
            if data.get('asignar_tarea'):
                tarea_data = data['asignar_tarea']
                
                # 1. Actualizar campos del documento (mantener compatibilidad)
                doc.estado_tarea = tarea_data.get('estado')
                doc.asignado_a_id = tarea_data.get('asignado_a_id')
                
                fecha_plazo = None
                if tarea_data.get('fecha_plazo'):
                    doc.fecha_plazo = datetime.fromisoformat(
                        tarea_data['fecha_plazo'].split('.')[0]
                    )
                    fecha_plazo = doc.fecha_plazo
                
                doc.guardado = False
                doc.email_enviado = False
                
                # 2. ⭐ NUEVO: Crear tarea real en tabla tareas
                from models import Tarea
                from constants import TaskStates
                from tenant_utils import get_current_gestoria_id
                
                # Determinar título descriptivo
                titulo = f"Procesar: {doc.nombre_archivo[:50]}"
                if len(doc.nombre_archivo) > 50:
                    titulo += "..."
                
                # Determinar descripción
                descripcion = f"Documento de {doc.empresa.nombre}"
                if doc.categoria:
                    descripcion += f" - Carpeta: {doc.categoria}"
                
                # Crear tarea
                nueva_tarea = Tarea(
                    titulo=titulo,
                    descripcion=descripcion,
                    estado=TaskStates.PENDIENTE,
                    prioridad='media',
                    asignado_a_id=tarea_data.get('asignado_a_id'),
                    fecha_vencimiento=fecha_plazo,
                    documento_id=doc.id,
                    empresa_id=doc.empresa_id,
                    origen='mesa_trabajo',
                    creado_por_id=current_user.id,
                    gestoria_id=get_current_gestoria_id(),
                    tags=['documento', doc.categoria.lower() if doc.categoria else 'sin_clasificar']
                )
                db.session.add(nueva_tarea)
                db.session.flush()  # Para obtener el ID
                
                # ⭐ Crear notificación Y emitir WebSocket si hay usuario asignado
                if tarea_data.get('asignado_a_id'):
                    try:
                        from flask import current_app
                        from tenant_utils import get_current_gestoria_id
                        from models import Notificacion
                        
                        # 1. Crear notificación en BD (para que aparezca en el dropdown)
                        titulo = "Nueva tarea asignada"
                        mensaje = f"📋 {nueva_tarea.titulo[:100]}"
                        link = "/calendario"  # Link al calendario donde está la tarea
                        
                        notificacion = Notificacion(
                            titulo=titulo,
                            mensaje=mensaje,
                            gestoria_id=get_current_gestoria_id(),
                            user_id=tarea_data.get('asignado_a_id'),
                            link=link,
                            tipo='info'
                        )
                        db.session.add(notificacion)
                        db.session.flush()  # Para obtener el ID
                        print(f"✅ Notificación creada en BD (ID: {notificacion.id}) para user_{tarea_data.get('asignado_a_id')}")
                        
                        # 2. Emitir WebSocket (toast + notificación push)
                        socketio = current_app.extensions.get('socketio')
                        if socketio:
                            # 2a. Toast tarea_asignada
                            toast_mensaje = f'📋 Nueva tarea asignada: {nueva_tarea.titulo[:50]}'
                            print(f"🔔 Emitiendo toast tarea_asignada a user_{tarea_data.get('asignado_a_id')}")
                            
                            socketio.emit('tarea_asignada', {
                                'tarea_id': nueva_tarea.id,
                                'mensaje': toast_mensaje
                            }, room=f'user_{tarea_data.get("asignado_a_id")}')
                            
                            # 2b. Notificación push (para contador)
                            socketio.emit('nueva_notificacion', notificacion.to_dict(), 
                                        room=f'user_{tarea_data.get("asignado_a_id")}')
                            print(f"📬 Emitiendo nueva_notificacion a user_{tarea_data.get('asignado_a_id')}")
                            
                            # 2c. Toast al usuario que asigna (para feedback inmediato)
                            if current_user.id != tarea_data.get('asignado_a_id'):
                                # Cargar el usuario explícitamente para evitar lazy loading tras flush
                                usuario_asignado = db.session.get(User, tarea_data.get('asignado_a_id'))
                                nombre_asignado = usuario_asignado.nombre if usuario_asignado else 'usuario'
                                socketio.emit('tarea_asignada', {
                                    'tarea_id': nueva_tarea.id,
                                    'mensaje': f'✅ Tarea asignada a {nombre_asignado}'
                                }, room=f'user_{current_user.id}')
                    except Exception as e:
                        print(f"⚠️ Error creando notificación/toast: {e}")
                        import traceback
                        traceback.print_exc()
                
                acciones_realizadas.append({
                    'tipo': 'asignar_tarea',
                    'estado': tarea_data.get('estado'),
                    'asignado_a': tarea_data.get('asignado_a_id'),
                    'tarea_id': nueva_tarea.id  # ⭐ Incluir ID de tarea creada
                })
            
            # ============================================
            # ACCIÓN 3: PROCESAR CON OCR/PERFILES (IA)
            # ============================================
            # Si se solicita procesar IA explícitamente O si se va a preparar un email
            # (necesitamos los datos extraídos para el email)
            if data.get('procesar_ia') or data.get('preparar_email'):
                tipo_plantilla = data.get('tipo_plantilla')

                # Si no hay plantilla explícita pero hay una sugerencia previa guardada en el doc o detectada
                if not tipo_plantilla and doc.datos_extraidos:
                    tipo_plantilla = doc.datos_extraidos.get('_metadata', {}).get('tipo_detectado')

                # Fallback a genérica si sigue siendo None
                if not tipo_plantilla:
                    tipo_plantilla = 'notificacion_generica'

                # ✅ Si el documento fue procesado antes con un perfil PROFILE:xxx (Path A),
                # reusar ese mismo perfil en el re-proceso manual para no caer en la extracción
                # genérica (Path B). El tipo_detectado guardado en _metadata es el profile_name
                # que usó el extractor de proximidad la primera vez.
                ia_plantilla = tipo_plantilla
                if not ia_plantilla.startswith('PROFILE:') and doc.datos_extraidos:
                    metadata = doc.datos_extraidos.get('_metadata', {})
                    tipo_previo = metadata.get('tipo_detectado', '')
                    # Los perfiles de auto-extracción tienen formato 'auto_GESTORID_tipo'
                    # Los perfiles de sistema son strings sin prefijo especial pero se usan como PROFILE:xxx
                    if tipo_previo and metadata.get('metodo') in ('PROXIMITY_EXTRACTOR', 'PROFILE'):
                        ia_plantilla = f"PROFILE:{tipo_previo}"

                # No lanzamos la tarea todavía, lo haremos después del commit para evitar race conditions
                # con el movimiento del archivo físico
                lanzar_ia = True
                
                acciones_realizadas.append({
                    'tipo': 'procesar_ia',
                    'plantilla': ia_plantilla,
                    'causa': 'manual' if data.get('procesar_ia') else 'requisito_email'
                })
            else:
                lanzar_ia = False
            
            # ============================================
            # ACCIÓN 4: ENVIAR EMAIL (preparar para envío)
            # ============================================
            if data.get('preparar_email'):
                doc.email_enviado = False  # Marcar como pendiente de envío

                # Si no se asignó tarea, poner estado_tarea automático para que
                # aparezca en el badge "Pendientes Tareas" de EmpresasDashboard
                # (el filtro ptarea requiere estado_tarea != None)
                if not data.get('asignar_tarea') and not doc.estado_tarea:
                    doc.estado_tarea = 'Pendiente (Email)'

                # Guardar destinatarios en metadatos para pre-cargarlos en DetalleNotificacionModal
                destinatarios = data.get('destinatarios', [])
                if not doc.datos_extraidos:
                    doc.datos_extraidos = {}

                # Actualizar el JSON manteniendo otros datos (hacemos una copia para disparar SQLAlchemy)
                nuevos_datos = dict(doc.datos_extraidos)
                nuevos_datos['email_preparado'] = {
                    'destinatarios': destinatarios,
                    'fecha_preparacion': datetime.utcnow().isoformat(),
                    'listo_para_enviar': True
                }
                doc.datos_extraidos = nuevos_datos
                
                acciones_realizadas.append({
                    'tipo': 'preparar_email',
                    'destinatarios': destinatarios
                })
            
            # Guardar cambios en BD antes de lanzar tareas asíncronas
            db.session.commit()

            # ============================================
            # DISPATCH DE TAREAS CELERY (Después del Commit)
            # ============================================
            if lanzar_ia:
                from celery_worker import procesar_documento_async
                task = procesar_documento_async.delay(doc_id, ia_plantilla)
                task_id = task.id
                
                # Actualizar las acciones con el ID de tarea real
                for a in acciones_realizadas:
                    if a['tipo'] == 'procesar_ia':
                        a['task_id'] = task_id
            
            # Registrar detalles para auditoría
            request.auditoria_detalles = {
                'documento_id': doc_id,
                'documento_nombre': doc.nombre_archivo,
                'acciones': acciones_realizadas,
                'empresa_id': doc.empresa_id
            }
            request.auditoria_entidad_id = doc_id
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': f'{len(acciones_realizadas)} acciones ejecutadas',
                'acciones': acciones_realizadas,
                'task_id': task_id,
                'documento': doc.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    # ✅ ELIMINAR LA RUTA DUPLICADA /api/departamentos
    # Esta ruta ya existe en otro archivo, no la duplicar aquí
    
    @app.route('/api/mesa-trabajo/sugerir-clasificacion', methods=['POST'])
    @login_required
    def sugerir_clasificacion():
        """
        Usa IA para sugerir la carpeta correcta basándose en el contenido del documento
        """
        try:
            data = request.json
            doc_id = data.get('documento_id')
            
            doc = db.session.get(Documento, doc_id)
            if not doc:
                return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404

            # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
            from tenant_utils import get_current_gestoria_id
            if doc.gestoria_id != get_current_gestoria_id():
                return jsonify({NotificationTypes.ERROR: 'Acceso denegado: el documento pertenece a otra gestoría'}), 403

            # 1. Intentar detectar plantilla con el extractor inteligente
            from services.notificacion_extractor import NotificacionExtractor
            from utils.storage_utils import resolve_document_path
            
            # Asegurar que la ruta es válida (auto-reparación si es necesario)
            pdf_path = resolve_document_path(doc)
            
            extractor = NotificacionExtractor()
            
            automation_match = None
            try:
                automation_match = extractor.detectar_plantilla(pdf_path)
            except Exception as e:
                logger.warning(f"Error en detección de automatización: {e}")

            if automation_match:
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'sugerencia': automation_match.categoria_default or DocumentCategories.NOTIFICACIONES,
                    'prioridad_sugerida': automation_match.prioridad_default or 'informativa',
                    'confianza': 0.95,
                    'razon': f'Coincidencia con regla: {automation_match.nombre}',
                    'departamento_sugerido': automation_match.departamento_default,
                    'plantilla_id': automation_match.id,
                    'plantilla_codigo': automation_match.codigo
                }), 200

            # 2. Si no hay regla, usar lógica antigua de palabras clave
            try:
                texto = extractor.extract_text_from_pdf(pdf_path)
            except:
                texto = ""
            
            if not texto or len(texto) < 20:
                return jsonify({
                    NotificationTypes.SUCCESS: True,
                    'sugerencia': DocumentCategories.NOTIFICACIONES,
                    'confianza': 0.3,
                    'razon': 'Documento con poco texto legible'
                }), 200
            
            # Analizar contenido con palabras clave
            texto_lower = texto.lower()
            
            # Diccionario de categorías con palabras clave
            categorias = {
                'Nominas': ['nómina', 'salario', 'sueldo', 'líquido a percibir', 'seguridad social', 'irpf'],
                'Impuestos': ['hacienda', 'impuesto', 'iva', 'irpf', 'declaración', 'tributaria', 'modelo', 'aeat'],
                DocumentCategories.SEGUROS_SOCIALES: ['tesorería general', 'seguridad social', 'cotización', 'rgss', 'red direct@'],
                'Inspecciones': ['inspección', 'requerimiento', 'acta', 'infracción'],
                'Contratos Trabajo': ['contrato', 'alta trabajador', 'contratación'],
                'Finiquitos': ['finiquito', 'liquidación', 'baja trabajador'],
                'Certificados Retenciones 180-190': ['certificado', 'retenciones', '180', '190'],
                'Aplazamiento': ['aplazamiento', 'fraccionamiento', 'pago'],
                'Notificaciones': ['notificación', 'comunicación', 'resolución', 'procedimiento'],
                'Documentos Empresa': ['escritura', 'poderes', 'estatutos', 'identificación']
            }
            
            # Calcular scores
            scores = {}
            for categoria, keywords in categorias.items():
                score = sum(1 for kw in keywords if kw in texto_lower)
                if score > 0:
                    scores[categoria] = score
            
            # Determinar sugerencia
            if scores:
                mejor_categoria = max(scores, key=scores.get)
                confianza = min(scores[mejor_categoria] / 3, 0.85)  # Máximo 85% para estas sugerencias
            else:
                mejor_categoria = DocumentCategories.NOTIFICACIONES
                confianza = 0.5
            
            # Si es Impuestos, detectar modelo fiscal
            modelo_fiscal_sugerido = None
            if mejor_categoria == 'Impuestos':
                from procesar_documentos_fiscales import detectar_tipo_documento
                try:
                    modelo_fiscal_sugerido = detectar_tipo_documento(texto)
                except:
                    modelo_fiscal_sugerido = None
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'sugerencia': mejor_categoria,
                'confianza': confianza,
                'razon': f'Análisis de contenido ({scores.get(mejor_categoria, 0)} coincidencias)',
                'scores': scores,
                'modelo_fiscal_sugerido': modelo_fiscal_sugerido
            }), 200
            
        except Exception as e:
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
    
    @app.route('/api/mesa-trabajo/batch-process', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_ACTUALIZADO,
        entidad_tipo='batch'
    )
    def batch_process():
        """
        Procesa múltiples documentos con la misma acción
        """
        try:
            data = request.json
            doc_ids = data.get('documento_ids', [])
            accion = data.get('accion')  # 'mover', 'asignar', 'procesar_ia'
            parametros = data.get('parametros', {})
            
            if not doc_ids or not accion:
                return jsonify({NotificationTypes.ERROR: 'Faltan parámetros'}), 400

            # MULTI-TENANT: obtener gestoría una sola vez fuera del loop
            from tenant_utils import get_current_gestoria_id
            gestoria_id_actual = get_current_gestoria_id()

            resultados = []
            task_ids = []

            for doc_id in doc_ids:
                doc = db.session.get(Documento, doc_id)
                if not doc:
                    continue

                # MULTI-TENANT: verificar que el doc pertenece a esta gestoría
                if doc.gestoria_id != gestoria_id_actual:
                    resultados.append({
                        'doc_id': doc_id,
                        'status': NotificationTypes.ERROR,
                        NotificationTypes.ERROR: 'Acceso denegado'
                    })
                    continue
                
                try:
                    if accion == 'mover':
                        nueva_categoria = parametros.get('categoria')
                        
                        # 1. Intentar mover el archivo físico también (igual que accion-combinada)
                        from utils.storage_utils import resolve_document_path, get_empresa_storage_path
                        current_path = resolve_document_path(doc)
                        
                        if current_path and os.path.exists(current_path):
                            try:
                                empresa_nombre = doc.empresa.nombre
                                base_dir = get_empresa_storage_path(doc.gestoria_id, empresa_nombre)
                                dest_dir = os.path.join(base_dir, nueva_categoria)
                                os.makedirs(dest_dir, exist_ok=True)
                                
                                filename = doc.nombre_archivo
                                dest_path = os.path.join(dest_dir, filename)
                                
                                # Evitar colisión de nombres
                                if os.path.exists(dest_path) and dest_path != current_path:
                                    name, ext = os.path.splitext(filename)
                                    dest_path = os.path.join(dest_dir, f"{name}_rev1{ext}")
                                    filename = os.path.basename(dest_path)
                                    
                                if dest_path != current_path:
                                    shutil.move(current_path, dest_path)
                                    doc.ruta_archivo = dest_path
                                    doc.nombre_archivo = filename
                                    logger.info(f"Batch mover: físico {current_path} -> {dest_path}")
                            except Exception as move_err:
                                logger.error(f"Error moviendo archivo en batch para doc {doc.id}: {move_err}")
                        
                        # Actualizar BD
                        doc.categoria = nueva_categoria
                        doc.fecha_procesado = datetime.utcnow()
                        
                        resultados.append({
                            'doc_id': doc_id,
                            'status': NotificationTypes.SUCCESS,
                            'accion': 'movido',
                            'ruta_final': doc.ruta_archivo
                        })
                    
                    elif accion == 'asignar':
                        doc.estado_tarea = parametros.get('estado')
                        doc.asignado_a_id = parametros.get('asignado_a_id')

                        fecha_plazo_batch = None
                        if parametros.get('fecha_plazo'):
                            doc.fecha_plazo = datetime.fromisoformat(
                                parametros['fecha_plazo'].split('.')[0]
                            )
                            fecha_plazo_batch = doc.fecha_plazo

                        # Crear Tarea real (igual que accion-combinada)
                        from models import Tarea
                        from constants import TaskStates
                        titulo_batch = f"Procesar: {doc.nombre_archivo[:50]}"
                        if len(doc.nombre_archivo) > 50:
                            titulo_batch += "..."
                        descripcion_batch = f"Documento de {doc.empresa.nombre}" if doc.empresa else "Documento"
                        if doc.categoria:
                            descripcion_batch += f" - Carpeta: {doc.categoria}"

                        tarea_batch = Tarea(
                            titulo=titulo_batch,
                            descripcion=descripcion_batch,
                            estado=TaskStates.PENDIENTE,
                            prioridad='media',
                            asignado_a_id=parametros.get('asignado_a_id'),
                            fecha_vencimiento=fecha_plazo_batch,
                            documento_id=doc.id,
                            empresa_id=doc.empresa_id,
                            origen='mesa_trabajo',
                            creado_por_id=current_user.id,
                            gestoria_id=gestoria_id_actual,
                            tags=['documento', doc.categoria.lower() if doc.categoria else 'sin_clasificar']
                        )
                        db.session.add(tarea_batch)
                        db.session.flush()

                        # Notificar por WebSocket si hay usuario asignado
                        if parametros.get('asignado_a_id'):
                            try:
                                from flask import current_app
                                from models import Notificacion
                                _socketio = current_app.extensions.get('socketio')
                                notif_batch = Notificacion(
                                    titulo="Nueva tarea asignada",
                                    mensaje=f"📋 {tarea_batch.titulo[:100]}",
                                    gestoria_id=gestoria_id_actual,
                                    user_id=parametros.get('asignado_a_id'),
                                    link="/calendario",
                                    tipo='info'
                                )
                                db.session.add(notif_batch)
                                db.session.flush()
                                if _socketio:
                                    _socketio.emit('tarea_asignada', {
                                        'tarea_id': tarea_batch.id,
                                        'mensaje': f'📋 Nueva tarea: {tarea_batch.titulo[:50]}'
                                    }, room=f'user_{parametros.get("asignado_a_id")}')
                                    _socketio.emit('nueva_notificacion', notif_batch.to_dict(),
                                                   room=f'user_{parametros.get("asignado_a_id")}')
                            except Exception as _ne:
                                logger.warning(f"Error notificando en batch asignar: {_ne}")

                        resultados.append({
                            'doc_id': doc_id,
                            'status': NotificationTypes.SUCCESS,
                            'accion': 'asignado',
                            'tarea_id': tarea_batch.id
                        })
                    
                    elif accion == 'procesar_ia':
                        from celery_worker import procesar_documento_async
                        
                        tipo = parametros.get('tipo', 'notificacion_generica')
                        task = procesar_documento_async.delay(doc_id, tipo)
                        task_ids.append(task.id)
                        
                        resultados.append({
                            'doc_id': doc_id,
                            'status': 'processing',
                            'task_id': task.id
                        })
                
                    elif accion == 'automatizar':
                        from services.extraction_profiles.notification_profiles import PROFILES
                        from models import ConfiguracionPerfil
                        
                        # Determinar perfil de sistema
                        perfil_sistema = parametros.get('perfil_sistema')
                        plantilla_id = parametros.get('plantilla_id')
                        
                        # --- A. Perfil de sistema explícito ---
                        if perfil_sistema:
                            from routes_tipos_documento import TIPOS_PREDEFINIDOS
                            from models import TipoDocumentoConfig
                            
                            es_estatico = any(t['codigo'] == perfil_sistema for t in TIPOS_PREDEFINIDOS)
                            config_data = {}
                            
                            if es_estatico:
                                config_estatica = TipoDocumentoConfig.query.filter_by(
                                    gestoria_id=doc.gestoria_id,
                                    codigo=perfil_sistema,
                                    activo=True
                                ).first()
                                if config_estatica:
                                    config_data = {
                                        'categoria': config_estatica.categoria_default,
                                        'departamento': config_estatica.departamento_default,
                                        'prioridad': getattr(config_estatica, 'prioridad_default', 'informativa'),
                                        'notificar_cliente': config_estatica.notificar_cliente
                                    }
                            else:
                                config_dinamica = ConfiguracionPerfil.query.filter_by(
                                    gestoria_id=doc.gestoria_id,
                                    perfil_clave=perfil_sistema,
                                    activo=True
                                ).first()
                                if config_dinamica:
                                    config_data = {
                                        'categoria': config_dinamica.categoria,
                                        'departamento': config_dinamica.departamento,
                                        'prioridad': getattr(config_dinamica, 'prioridad_default', 'informativa'),
                                        'notificar_cliente': config_dinamica.notificar_cliente
                                    }

                            if config_data.get('categoria'):
                                doc.categoria = config_data['categoria']
                                if doc.categoria == 'Notificaciones' and config_data.get('prioridad'):
                                    doc.prioridad = config_data['prioridad']
                                doc.fecha_procesado = datetime.utcnow()
                                
                                # ⭐ NUEVO: Marcar para notificar tras procesamiento asíncrono
                                if config_data.get('notificar_cliente') and not getattr(doc, 'email_enviado', False):
                                    doc._notificar_cliente_perfil = True
                                    doc.email_enviado = True # Evitar repetir logicamente en el loop si fuera el caso
                                
                            if config_data.get('departamento'):
                                doc.estado_tarea = f"Pendiente ({config_data['departamento']})"
                                
                            from celery_worker import procesar_documento_async
                            task = procesar_documento_async.delay(doc_id, f"PROFILE:{perfil_sistema}")
                            task_ids.append(task.id)
                            resultados.append({
                                'doc_id': doc_id,
                                'status': 'processing',
                                'accion': 'extraccion_forzada',
                                'perfil': perfil_sistema,
                                'task_id': task.id,
                                'destino': config_data.get('categoria')
                            })
                            continue

                        # --- B. Plantilla BD específica ---
                        if plantilla_id:
                            from models import Plantilla
                            match = db.session.get(Plantilla, plantilla_id)
                            if match:
                                if match.categoria_default:
                                    doc.categoria = match.categoria_default
                                    if doc.categoria == 'Notificaciones' and match.prioridad_default:
                                        doc.prioridad = match.prioridad_default
                                    doc.fecha_procesado = datetime.utcnow()
                                if match.departamento_default:
                                    doc.estado_tarea = f"Pendiente ({match.departamento_default})"
                                resultados.append({
                                    'doc_id': doc_id,
                                    'status': NotificationTypes.SUCCESS,
                                    'accion': 'automatizado',
                                    'regla': match.nombre
                                })
                                # ✅ FIX: Notificar invitados síncronamente si notificar_cliente=True
                                # La ruta plantilla_id no lanza Celery, por lo que hay que emitir aquí
                                if getattr(match, 'notificar_cliente', False):
                                    try:
                                        from flask import current_app
                                        from models import Notificacion
                                        from socketio_events import notify_guests_of_document
                                        from tenant_utils import get_current_gestoria_id
                                        _socketio = current_app.extensions.get('socketio')
                                        if _socketio:
                                            _gestoria_id = get_current_gestoria_id()
                                            _notif = Notificacion(
                                                gestoria_id=_gestoria_id,
                                                empresa_id=doc.empresa_id,
                                                titulo="Nuevo Documento Disponible",
                                                mensaje=f"Se ha clasificado un documento: {doc.nombre_archivo}",
                                                tipo="info",
                                                link=f"/empresa/{doc.empresa_id}"
                                            )
                                            db.session.add(_notif)
                                            db.session.flush()
                                            notify_guests_of_document(_socketio, doc, _notif.to_dict())
                                            logger.info(f"✅ Invitados notificados síncronamente para doc {doc_id} (plantilla {match.nombre})")
                                    except Exception as _ne:
                                        logger.warning(f"Error notificando invitados (plantilla {plantilla_id}): {_ne}")
                                continue

                        # --- C. Autodetección: intentar perfiles Python ---
                        texto = doc.texto_ocr or ''
                        perfil_detectado = None
                        config_detectada = None
                        
                        for profile in PROFILES:
                            if texto and profile.matches(texto):
                                clase = type(profile).__name__
                                config_detectada = ConfiguracionPerfil.query.filter_by(
                                    gestoria_id=doc.gestoria_id,
                                    perfil_clave=clase,
                                    activo=True
                                ).first()
                                perfil_detectado = clase
                                break
                        
                        if perfil_detectado and config_detectada and config_detectada.categoria:
                            doc.categoria = config_detectada.categoria
                            if doc.categoria == 'Notificaciones' and config_detectada.prioridad_default:
                                doc.prioridad = config_detectada.prioridad_default
                            doc.fecha_procesado = datetime.now()
                            if config_detectada.departamento:
                                doc.estado_tarea = f"Pendiente ({config_detectada.departamento})"
                            from celery_worker import procesar_documento_async
                            task = procesar_documento_async.delay(doc_id, f"PROFILE:{perfil_detectado}")
                            task_ids.append(task.id)
                            resultados.append({
                                'doc_id': doc_id,
                                'status': 'processing',
                                'status': 'processing',
                                'accion': 'autodetectado',
                                'perfil': perfil_detectado,
                                'destino': config_detectada.categoria,
                                'task_id': task.id
                            })
                        else:
                            # --- D. Fallback: buscar config por defecto de la gestoría ---
                            config_default = ConfiguracionPerfil.query.filter_by(
                                gestoria_id=doc.gestoria_id,
                                perfil_clave='_default_',
                                activo=True
                            ).first()
                            if config_default and config_default.categoria:
                                doc.categoria = config_default.categoria
                                if doc.categoria == 'Notificaciones' and config_default.prioridad_default:
                                    doc.prioridad = config_default.prioridad_default
                                doc.fecha_procesado = datetime.utcnow()
                            if config_default and config_default.departamento:
                                doc.estado_tarea = f"Pendiente ({config_default.departamento})"
                            from celery_worker import procesar_documento_async
                            task = procesar_documento_async.delay(doc_id, 'notificacion_generica')
                            task_ids.append(task.id)
                            resultados.append({
                                'doc_id': doc_id,
                                'status': 'processing',
                                'accion': 'extraccion_generica',
                                'message': 'Sin perfil específico — extracción genérica',
                                'destino': config_default.categoria if config_default else '(sin destino configurado)',
                                'task_id': task.id
                            })




                    elif accion == 'eliminar':
                        # Lógica de eliminación física y BD (basada en eliminar_documento de app.py)
                        if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                            try:
                                os.remove(doc.ruta_archivo)
                                logger.info(f"🗑️ Archivo eliminado físicamente (batch): {doc.ruta_archivo}")
                                
                                # Eliminar copias en Aplazamientos si existen
                                directorio_base = os.path.dirname(doc.ruta_archivo)
                                nombre_archivo = os.path.basename(doc.ruta_archivo)
                                
                                # Rutas posibles
                                rutas_posibles = [
                                    os.path.join(directorio_base, 'Aplazamientos', nombre_archivo),
                                ]
                                if os.path.basename(directorio_base) == 'Impuestos':
                                    ruta_raiz = os.path.dirname(directorio_base)
                                    rutas_posibles.append(os.path.join(ruta_raiz, 'Aplazamientos', nombre_archivo))
                                
                                for r in rutas_posibles:
                                    if os.path.exists(r):
                                        os.remove(r)
                                        logger.info(f"🗑️ Copia eliminada (batch): {r}")
                            except Exception as fe:
                                logger.error(f"⚠️ Error eliminando archivo físico {doc.ruta_archivo}: {fe}")

                        db.session.delete(doc)
                        resultados.append({
                            'doc_id': doc_id,
                            'status': NotificationTypes.SUCCESS,
                            'accion': 'eliminado'
                        })
                
                except Exception as e:
                    resultados.append({
                        'doc_id': doc_id,
                        'status': NotificationTypes.ERROR,
                        NotificationTypes.ERROR: str(e)
                    })
            
            db.session.commit()
            
            # Auditoría
            request.auditoria_detalles = {
                'total_documentos': len(doc_ids),
                'accion': accion,
                'exitosos': len([r for r in resultados if r['status'] == NotificationTypes.SUCCESS]),
                'errores': len([r for r in resultados if r['status'] == NotificationTypes.ERROR])
            }
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': f'Procesados {len(resultados)} documentos',
                'resultados': resultados,
                'task_ids': task_ids
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"🔥 Error FATAL en batch_process: {traceback.format_exc()}")
            return jsonify({NotificationTypes.ERROR: f"Error interno: {str(e)}"}), 500
    
    
    @app.route('/api/mesa-trabajo/stats', methods=['GET'])
    @login_required
    def get_stats_mesa_trabajo():
        """
        Estadísticas de la mesa de trabajo
        """
        try:
            # MULTI-TENANT: Filtrar por gestoría del usuario actual
            from tenant_utils import get_current_gestoria_id
            from sqlalchemy.orm import joinedload
            from constants import DocumentCategories
            gestoria_id = get_current_gestoria_id()
            
                      # ✅ CORRECCIÓN 1: Total pendientes solo en DocumentCategories.POR_PROCESAR
            query = Documento.query.options(
                joinedload(Documento.empresa)  # ✅ Eager loading
            ).filter(
                Documento.categoria == DocumentCategories.POR_PROCESAR,
                Documento.gestoria_id == gestoria_id
            )
            
            # Aplicar filtros solo si NO es Jefatura
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                query = query.filter(
                    or_(
                        Documento.estado_tarea == None,
                        Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%'),
                        Documento.asignado_a_id == current_user.id
                    )
                )
            
            total_pendientes = query.count()
            
                        # ✅ CORRECCIÓN 2: Procesados hoy con filtros de permisos aplicados
            from datetime import date, datetime as dt
            # Usar datetime con hora 00:00:00 para comparación correcta
            hoy_inicio = dt.combine(date.today(), dt.min.time())
            
                        # Documentos procesados hoy (sin importar cuándo fueron creados)
            procesados_hoy_query = Documento.query.options(
                joinedload(Documento.empresa)  # ✅ Eager loading
            ).filter(
                Documento.fecha_procesado >= hoy_inicio,
                Documento.fecha_procesado != None,
                Documento.gestoria_id == gestoria_id
            )
            
            # Aplicar mismo filtro de permisos que los pendientes
            if current_user.departamento and current_user.departamento.nombre != 'Jefatura':
                procesados_hoy_query = procesados_hoy_query.filter(
                    or_(
                        Documento.asignado_a_id == current_user.id,
                        Documento.estado_tarea == None,
                        Documento.estado_tarea.ilike(f'%{current_user.departamento.nombre}%')
                    )
                )
            
            procesados_hoy = procesados_hoy_query.count()
            
                        # ✅ CORRECCIÓN 3: Por empresa usando la misma lógica simplificada
            from sqlalchemy import func
            por_empresa = db.session.query(
                Empresa.nombre,
                func.count(Documento.id).label('count')
            ).join(Documento).filter(
                Documento.categoria == DocumentCategories.POR_PROCESAR,
                Documento.gestoria_id == gestoria_id
            ).group_by(Empresa.nombre).order_by(func.count(Documento.id).desc()).limit(5).all()
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'stats': {
                    'total_pendientes': total_pendientes,
                    'procesados_hoy': procesados_hoy,
                    'top_empresas': [
                        {'empresa': e.nombre, 'count': e.count}
                        for e in por_empresa
                    ]
                }
            }), 200
            
        except Exception as e:
            return jsonify({NotificationTypes.ERROR: str(e)}), 500
    
        
    @app.route('/api/mesa-trabajo/mover-a-fiscal', methods=['POST'])
    @login_required
    @auditar(
        accion=AccionesAuditoria.DOCUMENTO_CREADO,
        entidad_tipo='DocumentoFiscal'
    )
    def mover_documento_a_fiscal():
        """
        Mueve un documento de Mesa de Trabajo a Gestión Fiscal
        
        Body:
            - documento_id: ID del documento en mesa_trabajo
            - modelo_fiscal: Tipo de modelo seleccionado por usuario
            - ejercicio_fiscal: Año fiscal
            - periodo: Periodo (T1, T2, 1P, etc.) - opcional
        """
        try:
            data = request.json
            doc_id = data.get('documento_id')
            modelo = data.get('modelo_fiscal')
            ejercicio = data.get('ejercicio_fiscal')
            periodo = data.get('periodo')
            
            if not doc_id or not modelo or not ejercicio:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'Faltan parámetros requeridos'
                }), 400
            
            # 1. Obtener documento de mesa_trabajo
            documento = db.session.get(Documento, doc_id)
            if not documento:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'Documento no encontrado'
                }), 404

            # MULTI-TENANT: Validar que el documento pertenece a la gestoría actual
            from tenant_utils import get_current_gestoria_id
            if documento.gestoria_id != get_current_gestoria_id():
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'Acceso denegado: el documento pertenece a otra gestoría'
                }), 403

            # 2. Verificar que no exista ya en fiscal
            doc_fiscal_existente = DocumentoFiscal.query.filter_by(
                empresa_id=documento.empresa_id,
                tipo_documento=modelo,
                ejercicio_fiscal=ejercicio,
                periodo=periodo
            ).first()
            
            if doc_fiscal_existente:
                return jsonify({
                    NotificationTypes.SUCCESS: False,
                    NotificationTypes.ERROR: 'Ya existe un documento fiscal con estos datos'
                }), 400
            
            # 3. Crear DocumentoFiscal
            doc_fiscal = DocumentoFiscal(
                empresa_id=documento.empresa_id,
                tipo_documento=modelo,
                ejercicio_fiscal=ejercicio,
                periodo=periodo,
                estado='CONFIRMADO',  # Ya confirmado por usuario
                archivo_pdf_path=documento.ruta_archivo,
                clasificacion_confirmada='INFORMATIVO',  # Por defecto
                clasificacion_sugerida='INFORMATIVO',
                confianza_ia=1.0,  # Usuario confirmó manualmente
                confirmado_por_usuario_id=current_user.id,
                confirmado_at=datetime.utcnow(),
                procesado_por_ia_at=datetime.utcnow()
            )
            
            db.session.add(doc_fiscal)
            
            # Solo actualizar BD, archivo permanece en su ubicación
            documento.categoria = 'Impuestos'
            documento.estado_tarea = 'COMPLETADA'
            # documento.fecha_procesado = datetime.utcnow() # ❌ ELIMINADO
            
            db.session.commit()
            
            # Auditoría
            request.auditoria_detalles = {
                'documento_id': doc_id,
                'documento_nombre': documento.nombre_archivo,
                'modelo_fiscal': modelo,
                'ejercicio': ejercicio,
                'periodo': periodo,
                'empresa_id': documento.empresa_id,
                'documento_fiscal_id': doc_fiscal.id
            }
            request.auditoria_entidad_id = doc_fiscal.id
            
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'message': 'Documento movido a Gestión Fiscal',
                'documento_fiscal_id': doc_fiscal.id,
                'documento_fiscal': doc_fiscal.to_dict()
            }), 200
            
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return jsonify({
                NotificationTypes.SUCCESS: False,
                NotificationTypes.ERROR: str(e)
            }), 500

    
    print("✅ Rutas de Mesa de Trabajo registradas")