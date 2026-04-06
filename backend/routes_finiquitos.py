from flask import jsonify, request
from flask_login import login_required, current_user
from models import db, Documento, Empresa, FiniquitoLinea, FiniquitoLaboral
from datetime import datetime, date, timezone
from sqlalchemy import case, func, and_, or_
from constants import NotificationTypes, TaskStates, DocumentCategories
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from utils.storage_utils import get_empresa_storage_path
from utils.file_utils import get_file_hash
from services.procesar_finiquitos import procesar_finiquitos
from flask import current_app

def register_finiquitos_routes(app):
    """Registra rutas para la gestión de finiquitos"""
    
    @app.route('/api/finiquitos/stats', methods=['GET'])
    @login_required
    def get_finiquitos_stats():
        """Estadísticas generales de finiquitos"""
        
        empresa_id = request.args.get('empresa_id', type=int)
        
        # MULTI-TENANT: Filtrar por gestoría
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # Total de documentos en Finiquitos
        query_docs = Documento.query.filter_by(categoria='Finiquitos', gestoria_id=gestoria_id)
        if empresa_id:
            query_docs = query_docs.filter_by(empresa_id=empresa_id)
        total_documentos = query_docs.count()
        
        # Documentos procesados (que tienen líneas o finiquitos laborales)
        procesados_fiscales = db.session.query(Documento.id).join(FiniquitoLinea).filter(
            Documento.categoria == 'Finiquitos',
            Documento.gestoria_id == gestoria_id
        )
        procesados_laborales = db.session.query(Documento.id).join(FiniquitoLaboral).filter(
            Documento.categoria == 'Finiquitos',
            Documento.gestoria_id == gestoria_id
        )
        
        if empresa_id:
            procesados_fiscales = procesados_fiscales.filter(Documento.empresa_id == empresa_id)
            procesados_laborales = procesados_laborales.filter(Documento.empresa_id == empresa_id)
        
        procesados = procesados_fiscales.union(procesados_laborales).count()
        
        # Estadísticas de finiquitos fiscales (líneas)
        query_lineas = FiniquitoLinea.query.join(Documento)
        if empresa_id:
            query_lineas = query_lineas.filter(Documento.empresa_id == empresa_id)
        
        lineas_pendientes = query_lineas.filter(FiniquitoLinea.estado == TaskStates.PENDIENTE).count()
        lineas_pagadas = query_lineas.filter(FiniquitoLinea.estado == 'pagado').count()
        
        total_pendiente_fiscal = db.session.query(
            func.sum(FiniquitoLinea.importe_total_plazo)
        ).join(Documento).filter(FiniquitoLinea.estado == TaskStates.PENDIENTE)
        
        total_pagado_fiscal = db.session.query(
            func.sum(FiniquitoLinea.importe_total_plazo)
        ).join(Documento).filter(FiniquitoLinea.estado == 'pagado')
        
        if empresa_id:
            total_pendiente_fiscal = total_pendiente_fiscal.filter(Documento.empresa_id == empresa_id)
            total_pagado_fiscal = total_pagado_fiscal.filter(Documento.empresa_id == empresa_id)
        
        # Estadísticas de finiquitos laborales
        query_laborales = FiniquitoLaboral.query.join(Documento)
        if empresa_id:
            query_laborales = query_laborales.filter(Documento.empresa_id == empresa_id)
        
        laborales_pendientes = query_laborales.filter(FiniquitoLaboral.estado == TaskStates.PENDIENTE).count()
        laborales_pagados = query_laborales.filter(FiniquitoLaboral.estado == 'pagado').count()
        
        total_pendiente_laboral = db.session.query(
            func.sum(FiniquitoLaboral.importe_liquido)
        ).join(Documento).filter(FiniquitoLaboral.estado == TaskStates.PENDIENTE)
        
        total_pagado_laboral = db.session.query(
            func.sum(FiniquitoLaboral.importe_liquido)
        ).join(Documento).filter(FiniquitoLaboral.estado == 'pagado')
        
        if empresa_id:
            total_pendiente_laboral = total_pendiente_laboral.filter(Documento.empresa_id == empresa_id)
            total_pagado_laboral = total_pagado_laboral.filter(Documento.empresa_id == empresa_id)
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'stats': {
                'total_documentos': total_documentos,
                'procesados': procesados,
                'lineas_fiscales_pendientes': lineas_pendientes,
                'lineas_fiscales_pagadas': lineas_pagadas,
                'finiquitos_laborales_pendientes': laborales_pendientes,
                'finiquitos_laborales_pagados': laborales_pagados,
                'total_pendiente': round((total_pendiente_fiscal.scalar() or 0) + (total_pendiente_laboral.scalar() or 0), 2),
                'total_pagado': round((total_pagado_fiscal.scalar() or 0) + (total_pagado_laboral.scalar() or 0), 2)
            }
        })
    
    @app.route('/api/finiquitos/documentos', methods=['GET'])
    @login_required
    def get_finiquitos_documentos():
        """Lista todos los documentos de finiquitos con sus datos"""
        empresa_id = request.args.get('empresa_id', type=int)
        
        # MULTI-TENANT: Filtrar por gestoría
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # Query base
        query = db.session.query(
            Documento,
            Empresa.nombre.label('empresa_nombre'),
            func.count(FiniquitoLinea.id).label('total_lineas'),
            func.sum(case((FiniquitoLinea.estado == TaskStates.PENDIENTE, 1), else_=0)).label('lineas_pendientes'),
            func.sum(case((FiniquitoLinea.estado == 'pagado', 1), else_=0)).label('lineas_pagadas'),
            func.sum(case((FiniquitoLinea.estado == TaskStates.PENDIENTE, FiniquitoLinea.importe_total_plazo), else_=0)).label('importe_pendiente')
        ).join(Empresa).outerjoin(FiniquitoLinea).filter(
            Documento.categoria == 'Finiquitos',
            Documento.gestoria_id == gestoria_id
        )

        if empresa_id:
            query = query.filter(Documento.empresa_id == empresa_id)
    
        query = query.group_by(Documento.id, Empresa.nombre).order_by(Documento.fecha_creacion.desc())
    
        resultados = query.all()
        
        documentos = []
        for doc, empresa_nombre, total_lineas, lineas_pendientes, lineas_pagadas, importe_pendiente in resultados:
            documentos.append({
                'id': doc.id,
                'nombre_archivo': doc.nombre_archivo,
                'empresa_id': doc.empresa_id,
                'empresa_nombre': empresa_nombre,
                'fecha_creacion': doc.fecha_creacion.isoformat() if doc.fecha_creacion else None,
                'procesado': doc.procesado,
                'total_lineas': total_lineas or 0,
                'lineas_pendientes': lineas_pendientes or 0,
                'lineas_pagadas': lineas_pagadas or 0,
                'importe_pendiente': round(importe_pendiente or 0, 2)
            })
        
        return jsonify({NotificationTypes.SUCCESS: True, 'documentos': documentos})
    
    @app.route('/api/finiquitos/documentos/<int:doc_id>/lineas', methods=['GET'])
    @login_required
    def get_finiquito_lineas(doc_id):
        """Obtiene todas las líneas de un finiquito"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc or doc.categoria != 'Finiquitos':
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        lineas = FiniquitoLinea.query.filter_by(documento_id=doc_id).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'documento': {
                'id': doc.id,
                'nombre_archivo': doc.nombre_archivo,
                'empresa_nombre': doc.empresa.nombre if doc.empresa else None
            },
            'lineas': [linea.to_dict() for linea in lineas]
        })
    
    @app.route('/api/finiquitos/lineas/<int:linea_id>/estado', methods=['PUT'])
    @login_required
    def actualizar_estado_linea(linea_id):
        """Cambia el estado de una línea (pendiente/pagado)"""
        
        linea = db.session.get(FiniquitoLinea, linea_id)
        if not linea:
            return jsonify({NotificationTypes.ERROR: 'Línea no encontrada'}), 404
        
        data = request.json
        nuevo_estado = data.get('estado')
        
        if nuevo_estado not in [TaskStates.PENDIENTE, 'pagado']:
            return jsonify({NotificationTypes.ERROR: 'Estado inválido'}), 400
        
        linea.estado = nuevo_estado
        
        if nuevo_estado == 'pagado':
            linea.fecha_pago = date.today()
        else:
            linea.fecha_pago = None
        
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, 'linea': linea.to_dict()})
    
    @app.route('/api/finiquitos/documentos/<int:doc_id>/procesar', methods=['POST'])
    @login_required
    def procesar_finiquito(doc_id):
        """Procesa un finiquito y extrae las líneas de la tabla"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc or doc.categoria != 'Finiquitos':
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # Llamar a tarea asíncrona de Celery
        from celery_worker import procesar_finiquito_inteligente
        task = procesar_finiquito_inteligente.delay(doc_id)
        
        return jsonify({NotificationTypes.SUCCESS: True, 'task_id': task.id, 'message': 'Procesamiento iniciado'})
    
    @app.route('/api/finiquitos/todas-lineas', methods=['GET'])
    @login_required
    def get_todas_lineas_finiquitos():
        """Obtiene todas las líneas de todos los finiquitos (para vista general)"""
        
        estado_filtro = request.args.get('estado')  # TaskStates.PENDIENTE o 'pagado'
        empresa_id = request.args.get('empresa_id', type=int)
        
        query = db.session.query(
            FiniquitoLinea,
            Documento.nombre_archivo,
            Empresa.nombre.label('empresa_nombre'),
            Empresa.id.label('empresa_id')
        ).select_from(FiniquitoLinea).join(Documento).join(Empresa)
        
        if estado_filtro:
            query = query.filter(FiniquitoLinea.estado == estado_filtro)
        
        if empresa_id:
            query = query.filter(Empresa.id == empresa_id)
        
        resultados = query.order_by(FiniquitoLinea.fecha_vencimiento.asc()).all()
        
        lineas_con_info = []
        for linea, nombre_archivo, empresa_nombre, emp_id in resultados:
            linea_dict = linea.to_dict()
            linea_dict['nombre_archivo'] = nombre_archivo
            linea_dict['empresa_nombre'] = empresa_nombre
            linea_dict['empresa_id'] = emp_id
            lineas_con_info.append(linea_dict)
        
        return jsonify({NotificationTypes.SUCCESS: True, 'lineas': lineas_con_info})
    
    @app.route('/api/finiquitos/finiquitos-laborales', methods=['GET'])
    @login_required
    def get_finiquitos_laborales():
        """Obtiene todos los finiquitos laborales"""
        
        empresa_id = request.args.get('empresa_id', type=int)
        estado_filtro = request.args.get('estado')
        
        query = db.session.query(
            FiniquitoLaboral,
            Documento.nombre_archivo,
            Empresa.nombre.label('empresa_nombre'),
            Empresa.id.label('empresa_id')
        ).select_from(FiniquitoLinea).join(Documento).join(Empresa)
        
        if estado_filtro:
            query = query.filter(FiniquitoLaboral.estado == estado_filtro)
        
        if empresa_id:
            query = query.filter(Empresa.id == empresa_id)
        
        resultados = query.all()
        
        finiquitos_con_info = []
        for finiquito, nombre_archivo, empresa_nombre, emp_id in resultados:
            finiquito_dict = finiquito.to_dict()
            finiquito_dict['nombre_archivo'] = nombre_archivo
            finiquito_dict['empresa_nombre'] = empresa_nombre
            finiquito_dict['empresa_id'] = emp_id
            finiquitos_con_info.append(finiquito_dict)
        
        return jsonify({NotificationTypes.SUCCESS: True, 'finiquitos': finiquitos_con_info})
    
    @app.route('/api/finiquitos/documentos/<int:doc_id>/laboral', methods=['GET'])
    @login_required
    def get_finiquito_laboral(doc_id):
        """Obtiene el finiquito laboral de un documento"""
        finiquito = FiniquitoLaboral.query.filter_by(documento_id=doc_id).first()
        if not finiquito:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No encontrado'}), 404
        
        return jsonify({NotificationTypes.SUCCESS: True, 'finiquito': finiquito.to_dict()})
    
    @app.route('/api/finiquitos/finiquito-laboral/<int:finiquito_id>/estado', methods=['PUT'])
    @login_required
    def actualizar_estado_finiquito_laboral(finiquito_id):
        """Actualiza el estado de un finiquito laboral"""
        finiquito = db.session.get(FiniquitoLaboral, finiquito_id)
        if not finiquito:
            return jsonify({NotificationTypes.SUCCESS: False, NotificationTypes.ERROR: 'No encontrado'}), 404
        
        data = request.get_json()
        finiquito.estado = data.get('estado')
        
        if finiquito.estado == 'pagado':
            finiquito.fecha_pago = date.today()
        else:
            finiquito.fecha_pago = None
        
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True})

    @app.route('/api/finiquitos/upload', methods=['POST'])
    @login_required
    def upload_finiquitos():
        """Sube y procesa finiquitos"""
        files = request.files.getlist('files') if 'files' in request.files else []
        if not files and 'file' in request.files:
            files = [request.files['file']]
            
        if not files:
            return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
            
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        current_app.logger.info(f"[FINIQUITO UPLOAD] Iniciando para gestoria_id: {gestoria_id}")
        
        # Directorio temporal
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        app_temp_dir = os.path.join(backend_dir, 'temp')
        os.makedirs(app_temp_dir, exist_ok=True)

        processed_details = []
        total_archivos_generados = 0
        unique_companies = set()

        new_docs_to_process = []

        for file in files:
            temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
            temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_pdf_path)
            
            # --- VALIDACIÓN DE TIPO DE DOCUMENTO ---
            force_guardado = request.form.get('force', 'false').lower() == 'true'
            if not force_guardado:
                from utils.document_detector import predecir_categoria_documento
                deteccion = predecir_categoria_documento(temp_pdf_path)
                
                # Si estamos en Finiquitos, esperamos 'finiquito'. 
                if deteccion.get("analizado") and deteccion.get("tipo_detectado") not in ["finiquito", "desconocido"]:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    return jsonify({
                        'success': False,
                        'estado': 'confirmacion',
                        'detectado': deteccion.get("tipo_detectado"),
                        'empresa_detectada': deteccion.get("empresa_detectada"),
                        'filename': file.filename,
                        'message': f'El archivo {file.filename} parece ser de tipo {deteccion.get("tipo_detectado").replace("_", " ")}. ¿Continuar como Finiquito?'
                    }), 400
            # ---------------------------------------
            
            try:
                resultados = procesar_finiquitos(
                    pdf_path=temp_pdf_path, 
                    gestoria_id=gestoria_id
                )
                
                for res in resultados:
                    empresa_id = res.get('empresa_id')
                    nombre_empresa = res.get('nombre_empresa', 'Empresa_Desconocida')
                    pdf_final_path = res.get('pdf_path')
                    nombre_trabajador = res.get('nombre_trabajador', 'Trabajador_Desconocido')
                    nif_trabajador = res.get('nif_trabajador', 'SinNIF')
                    fecha_str = res.get('fecha', '').replace('/', '-') if res.get('fecha') else "SinFecha"
                    
                    if empresa_id:
                        unique_companies.add(empresa_id)
                        empresa = db.session.get(Empresa, empresa_id)
                        emp_nombre = empresa.nombre
                    else:
                        emp_nombre = nombre_empresa
                    
                    # Ruta de almacenamiento: /storage/{gestoria}/{empresa}/Finiquitos/
                    empresa_base = get_empresa_storage_path(gestoria_id, emp_nombre)
                    finiquitos_dir = os.path.join(empresa_base, "Finiquitos")
                    os.makedirs(finiquitos_dir, exist_ok=True)
                    
                    new_filename = f"FINIQUITO_{nif_trabajador}_{fecha_str}.pdf"
                    final_path = os.path.join(finiquitos_dir, new_filename)
                    
                    # Evitar sobreescribir si ya existe el nombre
                    counter = 1
                    base, ext = os.path.splitext(final_path)
                    while os.path.exists(final_path):
                        final_path = f"{base}_{counter}{ext}"
                        counter += 1
                        
                    shutil.copy2(pdf_final_path, final_path)
                    
                    if empresa_id:
                        hash_archivo = get_file_hash(final_path)
                        
                        doc_existente = Documento.query.filter_by(
                            empresa_id=empresa_id,
                            file_hash=hash_archivo
                        ).first()

                        if not doc_existente:
                            nuevo_doc = Documento(
                                empresa_id=empresa_id,
                                gestoria_id=gestoria_id,
                                nombre_archivo=os.path.basename(final_path),
                                ruta_archivo=final_path,
                                categoria=DocumentCategories.FINIQUITOS,
                                fecha_creacion=datetime.utcnow(),
                                guardado=True,
                                procesado=True,
                                periodo=str(datetime.now().year),
                                file_hash=hash_archivo,
                                datos_extraidos=res
                            )
                            db.session.add(nuevo_doc)
                            db.session.flush() # Para obtener el ID

                            total_archivos_generados += 1
                            processed_details.append({
                                'nombre_trabajador': nombre_trabajador,
                                'empresa': emp_nombre,
                                'estado': 'exito',
                                'mensaje': 'Finiquito subido correctamente.'
                            })
                        else:
                            processed_details.append({
                                'nombre_trabajador': nombre_trabajador,
                                'empresa': emp_nombre,
                                'estado': 'duplicado',
                                'mensaje': 'El finiquito ya existe'
                            })
                    else:
                        processed_details.append({
                            'nombre_trabajador': nombre_trabajador,
                            'empresa': nombre_empresa,
                            'estado': 'warning',
                            'mensaje': 'Empresa no identificada'
                        })
                
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error procesando Finiquito {file.filename}: {e}")
                processed_details.append({
                    'nombre_trabajador': 'Error',
                    'empresa': '-',
                    'estado': 'error',
                    'mensaje': str(e)
                })
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)

        return jsonify({
            'success': total_archivos_generados > 0,
            'message': f'Subidos {total_archivos_generados} finiquitos.' if total_archivos_generados > 0 else 'No se pudo procesar ningún archivo.',
            'results': processed_details
        })
