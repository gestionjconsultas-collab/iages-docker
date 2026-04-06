# backend/routes_nominas.py
"""
Rutas para procesamiento de nóminas
"""
from importlib.resources import files
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
import re
from pypdf import PdfReader
import pdfplumber
from datetime import datetime

from procesar_nominas import procesar_nominas, asociar_con_empresas_bd, guardar_en_carpetas_empresas, registrar_en_bd, extraer_info_empresa_nomina
from auditoria import auditar
from tenant_utils import get_current_gestoria_id
from extensions import limiter

nominas_bp = Blueprint('nominas', __name__)

# Límite de páginas para procesamiento síncrono
LIMITE_SINCRONO = 100


@nominas_bp.route('/api/procesar-nominas', methods=['POST'])
@login_required
@auditar(accion='procesar_nominas')
def procesar_nominas_endpoint():
    """
    Procesa archivo consolidado de nóminas
    - Si tiene < 100 páginas: procesamiento síncrono
    - Si tiene >= 100 páginas: procesamiento asíncrono con Celery
    """
    # Soporta tanto 'file' (único) como 'files' (múltiples)
    files = request.files.getlist('files') if 'files' in request.files else []
    if not files and 'file' in request.files:
        files = [request.files['file']]  # Compatibilidad con versión anterior
    if not files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
    for file in files:
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Nombre de archivo vacío'}), 400
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'message': f'Solo PDF: {file.filename}'}), 400
            
    # --- VALIDACIÓN DE TIPO DE DOCUMENTO ---
    force_guardado = request.form.get('force', 'false').lower() == 'true'
    if not force_guardado:
        from utils.document_detector import predecir_categoria_documento
        for file in files:
            temp_dir_val = tempfile.mkdtemp()
            temp_pdf_path_val = os.path.join(temp_dir_val, secure_filename(file.filename))
            file.save(temp_pdf_path_val)
            
            deteccion = predecir_categoria_documento(temp_pdf_path_val)
            file.seek(0)
            shutil.rmtree(temp_dir_val, ignore_errors=True)
            
            if deteccion.get("analizado") and deteccion.get("tipo_detectado") not in ["nominas", "desconocido"]:
                return jsonify({
                    'success': False,
                    'estado': 'confirmacion',
                    'detectado': deteccion.get("tipo_detectado"),
                    'empresa_detectada': deteccion.get("empresa_detectada"),
                    'filename': file.filename,
                    'message': f'El archivo {file.filename} parece ser de tipo {deteccion.get("tipo_detectado").replace("_", " ")}. ¿Continuar como Nóminas?'
                }), 400
    
    periodo_manual = request.form.get('periodo')
    print("=" * 60)
    print(f"🔐 Usuario: {current_user.nombre}")
    print(f"📁 {len(files)} archivo(s) de nóminas")
    for f in files:
        print(f"   - {f.filename}")
    print("=" * 60)
    
    # Procesar múltiples archivos
    from tasks_nominas import procesar_nominas_async
    from models import TareaNomina, db
    
    try:
        tasks_info = []
        gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1

        # Verificar si es modo empresa única
        empresa_unica_mode = request.form.get('empresa_unica') == 'true'

        if empresa_unica_mode:
            print("🚀 MODO EMPRESA ÚNICA ACTIVADO")
            from procesar_nominas import extraer_info_empresa_nomina, get_or_create_inbox_empresa
            from models import Empresa, Documento, db
            from utils import limpiar_nombre_carpeta

            storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
            processed_files = []
            processed_details = []
            unique_companies = set()

            for file in files:
                # Guardar temporalmente para leer
                temp_dir = tempfile.mkdtemp()
                temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
                file.save(temp_pdf_path)

                try:
                    # Leer primera página para detectar empresa
                    with pdfplumber.open(temp_pdf_path) as pdf:
                        if len(pdf.pages) > 0:
                            info = extraer_info_empresa_nomina(pdf.pages[0])
                        else:
                            info = {}
                    
                    empresa = None
                    if info.get('nif'):
                        empresa = Empresa.query.filter_by(nif=info['nif'], gestoria_id=gestoria_id).first()
                    
                    if not empresa and info.get('razon_social'):
                         # Intentar por nombre (búsqueda difusa simple o exacta)
                         empresa = Empresa.query.filter(Empresa.nombre.ilike(f"%{info['razon_social']}%"), Empresa.gestoria_id==gestoria_id).first()

                    if not empresa:
                        # Fallback a inbox si no se encuentra
                        print(f"⚠️ Empresa no encontrada para {file.filename}, enviando a Inbox.")
                        empresa = get_or_create_inbox_empresa(db, Empresa, gestoria_id)
                    
                    if empresa:
                        unique_companies.add(empresa.id)

                    # Destino final
                    empresa_dir = os.path.join(storage_dir, limpiar_nombre_carpeta(empresa.nombre), "Nominas")
                    os.makedirs(empresa_dir, exist_ok=True)
                    
                    final_path = os.path.join(empresa_dir, secure_filename(file.filename))
                    shutil.move(temp_pdf_path, final_path)
                    
                    # Registrar en BD
                    nuevo_doc = Documento(
                        empresa_id=empresa.id,
                        gestoria_id=gestoria_id,
                        nombre_archivo=os.path.basename(final_path),
                        ruta_archivo=final_path,
                        categoria='Nominas',
                        fecha_creacion=datetime.utcnow(),
                        guardado=True,
                        procesado=True,
                        periodo=periodo_manual or info.get('periodo')
                    )
                    db.session.add(nuevo_doc)
                    db.session.flush() # Para obtener ID
                    
                    processed_files.append(file.filename)
                    processed_details.append({
                        'documento_id': nuevo_doc.id,
                        'nombre_trabajador': 'Archivo Completo (Modo Empresa Única)',
                        'empresa': empresa.nombre,
                        'estado': 'exito'
                    })
                    
                except Exception as e:
                    print(f"❌ Error en modo empresa única para {file.filename}: {e}")
                    import traceback; traceback.print_exc()
                    processed_details.append({
                        'documento_id': None,
                        'nombre_trabajador': f'Error: {file.filename}',
                        'empresa': empresa.nombre if empresa else 'Desconocida',
                        'estado': 'error',
                        'mensaje': str(e)
                    })
                finally:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)

            db.session.commit()
            
            final_success = len(processed_files) > 0
            
            return jsonify({
                'success': final_success,
                'message': f'Procesados {len(processed_files)} archivos en Modo Empresa Única' if final_success else 'No se pudo procesar el archivo. Revise los detalles.',
                'async': False,
                'total_empresas': len(unique_companies),
                'total_trabajadores': len(processed_files),
                'empresas_clasificadas': len(unique_companies),
                'empresas_no_encontradas': 0,
                'detalles': processed_details,
                'periodo': periodo_manual,
                'documentos_creados': len(processed_files)
            })



        # Crear directorio de procesamiento dentro del proyecto si no existe
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        app_temp_dir = os.path.join(backend_dir, 'temp')
        os.makedirs(app_temp_dir, exist_ok=True)

        is_async = False  # Se marca True una vez que se lancen tareas Celery
        
        for file in files:
            # Crear subdirectorio temporal único para este archivo
            temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
            temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_pdf_path)
            
            # Detectar número de páginas
            try:
                with open(temp_pdf_path, 'rb') as f:
                    pdf = PdfReader(f)
                    num_pages = len(pdf.pages)
            except:
                num_pages = 0
            
            print(f"📄 {file.filename}: {num_pages} páginas")
            
            # ⭐ DIVISIÓN AUTOMÁTICA para PDFs grandes (>1000 páginas)
            files_to_process = []
            if num_pages > 1000:
                print(f"⚠️  PDF grande detectado ({num_pages} páginas). Dividiendo automáticamente...")
                try:
                    from pypdf import PdfWriter  # Usar pypdf en lugar de PyPDF2
                    pages_per_file = 500
                    num_parts = (num_pages + pages_per_file - 1) // pages_per_file
                    
                    base_name = os.path.splitext(os.path.basename(temp_pdf_path))[0]
                    
                    # Reabrir el PDF para división (el anterior se cerró)
                    with open(temp_pdf_path, 'rb') as f:
                        pdf_for_split = PdfReader(f)
                        
                        for part_num in range(num_parts):
                            start_page = part_num * pages_per_file
                            end_page = min((part_num + 1) * pages_per_file, num_pages)
                            
                            writer = PdfWriter()
                            for page_num in range(start_page, end_page):
                                writer.add_page(pdf_for_split.pages[page_num])
                            
                            part_filename = f"{base_name}_parte{part_num + 1}_pag{start_page + 1}-{end_page}.pdf"
                            part_path = os.path.join(temp_dir, part_filename)
                            
                            with open(part_path, 'wb') as output_file:
                                writer.write(output_file)
                            
                            files_to_process.append((part_path, part_filename, end_page - start_page))
                            print(f"  ✅ Parte {part_num + 1}/{num_parts}: {part_filename} ({end_page - start_page} páginas)")
                    
                    print(f"✅ PDF dividido en {len(files_to_process)} partes")
                except Exception as e:
                    print(f"❌ Error dividiendo PDF: {e}. Procesando archivo completo...")
                    files_to_process = [(temp_pdf_path, file.filename, num_pages)]
            else:
                files_to_process = [(temp_pdf_path, file.filename, num_pages)]
            
            # Procesar cada archivo (original o partes)
            for pdf_path, pdf_filename, pdf_pages in files_to_process:
                # Lanzar tarea asíncrona
                is_async = True
                output_dir = tempfile.mkdtemp(dir=app_temp_dir)
                storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
                
                task = procesar_nominas_async.apply_async(
                    args=[pdf_path, output_dir, storage_dir, current_user.id, gestoria_id],
                    kwargs={'periodo_override': periodo_manual}
                )
                
                print(f"⚡ Tarea creada: {task.id} para {pdf_filename} ({pdf_pages} páginas)")
                
                # Guardar en historial
                tarea_registro = TareaNomina(
                    task_id=task.id,
                    user_id=current_user.id,
                    gestoria_id=gestoria_id,
                    filename=pdf_filename,  # Usar pdf_filename en lugar de file.filename
                    status='PENDING'
                )
                db.session.add(tarea_registro)
                
                tasks_info.append({
                    'task_id': task.id,
                    'filename': pdf_filename,  # Usar pdf_filename en lugar de file.filename
                    'num_pages': pdf_pages  # Usar pdf_pages en lugar de num_pages
                })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'async': True,
            'tasks': tasks_info,
            'task_id': tasks_info[0]['task_id'] if tasks_info else None,  # Mantener por compatibilidad
            'total_parts': len(tasks_info),  # Número total de partes
            'is_split': len(tasks_info) > 1,  # Indica si el PDF fue dividido
            'message': f'{len(tasks_info)} archivo(s) en procesamiento'
        })
        
    except Exception as e:
        # Limpiar solo si NO es asíncrono (si es asíncrono, Celery lo limpiará)
        if not is_async and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        print(f"❌ Error procesando nóminas: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'Error procesando nóminas: {str(e)}'
        }), 500


@nominas_bp.route('/api/procesar-nominas-multiple', methods=['POST'])
@login_required
@auditar(accion='procesar_nominas_multiple')
def procesar_nominas_multiple():
    """
    Procesa múltiples archivos de nóminas de forma asíncrona
    """
    files = request.files.getlist('files')
    
    if not files or len(files) == 0:
        return jsonify({'success': False, 'message': 'No se enviaron archivos'}), 400
    
    periodo_manual = request.form.get('periodo')
    
    print("=" * 60)
    print(f"🔐 Usuario: {current_user.nombre} ({current_user.email})")
    print(f"📁 Archivos: {len(files)}")
    if periodo_manual:
        print(f"📅 Periodo manual: {periodo_manual}")
    print("=" * 60)
    
    from tasks_nominas import procesar_nominas_async
    
    tasks = []
    storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
    
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue
        
        # Guardar archivo temporal
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_pdf_path)
        
        # Crear directorio de salida
        output_dir = tempfile.mkdtemp()
        
        # Enviar a Celery
        task = procesar_nominas_async.apply_async(
            args=[temp_pdf_path, output_dir, storage_dir, current_user.id],
            kwargs={'periodo_override': periodo_manual}
        )
        
        tasks.append({
            'task_id': task.id,
            'filename': file.filename
        })
    
    return jsonify({
        'success': True,
        'total_files': len(tasks),
        'tasks': tasks
    })


@nominas_bp.route('/api/preview-nominas', methods=['POST'])
@login_required
def preview_nominas():
    """
    Extrae el periodo de la primera página del PDF sin procesarlo completamente
    Compara con periodo manual si se proporciona
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
    
    file = request.files['file']
    periodo_manual = request.form.get('periodo_manual')
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Solo se permiten archivos PDF'}), 400
    
    # Guardar temporalmente
    temp_dir = tempfile.mkdtemp()
    temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
    file.save(temp_pdf_path)
    
    try:
        # Importar extractores de SS
        from procesar_seguros_sociales import extraer_info_empresa_rlc, extraer_info_empresa_rnt
        
        # Leer solo la primera página
        with pdfplumber.open(temp_pdf_path) as pdf:
            if len(pdf.pages) == 0:
                return jsonify({'success': False, 'message': 'PDF vacío'}), 400
            
            first_page = pdf.pages[0]
            full_text = first_page.extract_text() or ""
            
            # Detectar tipo de documento primero
            es_rlc = 'RECIBO DE LIQUIDACIÓN' in full_text.upper() or 'RLC' in full_text.upper()
            es_rnt = 'RELACIÓN NOMINAL' in full_text.upper() or 'RNT' in full_text.upper()
            
            periodo_detectado = None
            periodo_detectado_texto = None
            info = {}
            
            # 1. Intentar como Nómina primero
            if not es_rlc and not es_rnt:
                info = extraer_info_empresa_nomina(first_page)
                periodo_detectado = info.get('periodo')
                periodo_detectado_texto = info.get('periodo_texto')
            
            # 2. Si es RLC, usar extractor de RLC
            if es_rlc and not periodo_detectado:
                info_ss = extraer_info_empresa_rlc(first_page)
                if info_ss.get('periodo'):  # Cambiar condición a periodo en lugar de ccc
                    info = info_ss
                    periodo_detectado = info_ss.get('periodo')
                    periodo_detectado_texto = info_ss.get('periodo_texto')
            
            # Si es RNT, usar extractor de RNT
            if es_rnt and not periodo_detectado:
                info_ss = extraer_info_empresa_rnt(first_page)
                if info_ss.get('periodo'):
                    info = info_ss
                    periodo_detectado = info_ss.get('periodo')
                    periodo_detectado_texto = info_ss.get('periodo_texto')
        
        # ELIMINADO: Ya no confiamos en el nombre del archivo si hay duda, 
        # para evitar conflictos con periodos reales 12/2023 vs nombres 202511.
        hay_discrepancia = False
        mensaje_warning = None
        
        if periodo_manual and periodo_detectado:
            if periodo_manual != periodo_detectado:
                hay_discrepancia = True
                mensaje_warning = f"⚠️ Discrepancia detectada:\n\n"
                mensaje_warning += f"Periodo seleccionado: {periodo_manual}\n"
                mensaje_warning += f"Periodo detectado en el PDF: {periodo_detectado_texto or periodo_detectado}\n\n"
                mensaje_warning += f"¿Estás seguro de que quieres procesar este archivo con el periodo {periodo_manual}?"
        
        return jsonify({
            'success': True,
            'periodo_detectado': periodo_detectado,
            'periodo_detectado_texto': periodo_detectado_texto,
            'periodo_manual': periodo_manual,
            'hay_discrepancia': hay_discrepancia,
            'mensaje_warning': mensaje_warning
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error en preview: {str(e)}'
        }), 500
    
    finally:
        # Limpiar archivo temporal
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@nominas_bp.route('/api/nominas/historial', methods=['GET'])
@login_required
def get_historial_nominas():
    """
    Obtiene el historial de procesamiento de nóminas para la gestoría actual
    """
    try:
        from models import TareaNomina
        
        # Filtrar por gestoría del usuario
        gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1
        
        tareas = TareaNomina.query.filter_by(
            gestoria_id=gestoria_id
        ).order_by(TareaNomina.created_at.desc()).limit(100).all()
        
        return jsonify({
            'success': True,
            'tareas': [t.to_dict() for t in tareas]
        })
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@nominas_bp.route('/api/seguros/historial', methods=['GET'])
@login_required
def get_historial_seguros():
    """
    Obtiene el historial de procesamiento de seguros sociales
    """
    try:
        from models import TareaSeguros
        
        # Filtrar por gestoría del usuario
        gestoria_id = current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1
        
        tareas = TareaSeguros.query.filter_by(
            gestoria_id=gestoria_id
        ).order_by(TareaSeguros.created_at.desc()).limit(100).all()
        
        return jsonify({
            'success': True,
            'tareas': [t.to_dict() for t in tareas]
        })
    
    except Exception as e:
        print(f"❌ Error obteniendo historial: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@nominas_bp.route('/api/task-status/<task_id>', methods=['GET'])
@limiter.exempt
@login_required
def get_task_status(task_id):
    """
    Consulta el estado de una tarea Celery en progreso
    (Sin rate limit para permitir polling frecuente)
    """
    try:
        # MULTI-TENANT: Validar que la tarea pertenece a la gestoría del usuario
        from models import TareaNomina, TareaSeguros
        gestoria_id = get_current_gestoria_id()
        
        # Buscar en ambas tablas de tareas
        tarea = TareaNomina.query.filter_by(task_id=task_id, gestoria_id=gestoria_id).first()
        if not tarea:
            tarea = TareaSeguros.query.filter_by(task_id=task_id, gestoria_id=gestoria_id).first()
            
        if not tarea:
            # Si no es de este usuario/gestoría, denegar acceso
            return jsonify({'success': False, 'message': 'Tarea no encontrada o acceso denegado'}), 404
            
        # Importar desde celery_worker para tener acceso al broker configurado
        from celery_worker import celery
        
        task = celery.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            # Tarea en cola
            response = {
                'state': 'PENDING',
                'status': 'En cola, esperando procesamiento...',
                'current': 0,
                'total': 1,
                'percent': 0
            }
        elif task.state == 'PROGRESS':
            # Tarea en progreso
            response = {
                'state': 'PROGRESS',
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'percent': task.info.get('percentage', 0),
                'status': task.info.get('status', 'Procesando...'),
                'empresa_nif': task.info.get('empresa_nif', '')
            }
        elif task.state == 'SUCCESS':
            # Tarea completada
            response = {
                'state': 'SUCCESS',
                'status': 'Procesamiento completado',
                'result': task.info
            }
        elif task.state == 'FAILURE':
            # Tarea fallida
            response = {
                'state': 'FAILURE',
                'status': f'Error: {str(task.info)}',
                'error': str(task.info)
            }
        else:
            # Otro estado
            response = {
                'state': task.state,
                'status': str(task.info)
            }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"❌ Error en get_task_status: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'state': 'ERROR',
            'status': f'Error consultando estado: {str(e)}'
        }), 500
