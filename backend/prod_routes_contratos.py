from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from models import db, Documento, Empresa
from datetime import datetime, date
from sqlalchemy import func
from constants import NotificationTypes, DocumentCategories
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from utils.storage_utils import get_empresa_storage_path
from utils.file_utils import get_file_hash
from services.procesar_contratos import procesar_contratos

def register_contratos_routes(app):
    """Registra rutas para el importador de contratos"""

    @app.route('/api/contratos/upload', methods=['POST'])
    @login_required
    def upload_contratos():
        """Sube y procesa contratos de trabajo"""
        files = request.files.getlist('files') if 'files' in request.files else []
        if not files and 'file' in request.files:
            files = [request.files['file']]
            
        if not files:
            return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
            
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # Directorio temporal
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        app_temp_dir = os.path.join(backend_dir, 'temp')
        os.makedirs(app_temp_dir, exist_ok=True)

        processed_details = []
        total_archivos_generados = 0

        for file in files:
            temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
            temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_pdf_path)
            
            # --- VALIDACIÓN DE TIPO DE DOCUMENTO ---
            force_guardado = request.form.get('force', 'false').lower() == 'true'
            if not force_guardado:
                from utils.document_detector import predecir_categoria_documento
                deteccion = predecir_categoria_documento(temp_pdf_path)
                
                # Si estamos en Contratos, esperamos 'contratos'. 
                if deteccion.get("analizado") and deteccion.get("tipo_detectado") not in ["contratos", "desconocido"]:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    return jsonify({
                        'success': False,
                        'estado': 'confirmacion',
                        'detectado': deteccion.get("tipo_detectado"),
                        'empresa_detectada': deteccion.get("empresa_detectada"),
                        'filename': file.filename,
                        'message': f'El archivo {file.filename} parece ser de tipo {deteccion.get("tipo_detectado").replace("_", " ")}. ¿Continuar como Contrato?'
                    }), 400
            # ---------------------------------------
            
            try:
                resultados = procesar_contratos(
                    pdf_path=temp_pdf_path, 
                    gestoria_id=gestoria_id
                )
                
                for res in resultados:
                    empresa_id = res.get('empresa_id')
                    nombre_empresa = res.get('nombre_empresa', 'Empresa_Desconocida')
                    pdf_final_path = res.get('pdf_path')
                    nombre_trabajador = res.get('nombre_trabajador', 'Trabajador_Desconocido')
                    nif_trabajador = res.get('nif_trabajador', 'SinNIF')
                    fecha_inicio = res.get('fecha_inicio', '').replace('/', '-') if res.get('fecha_inicio') else "SinFecha"
                    
                    if empresa_id:
                        empresa = db.session.get(Empresa, empresa_id)
                        emp_nombre = empresa.nombre
                    else:
                        emp_nombre = nombre_empresa
                    
                    # Ruta de almacenamiento: /storage/{gestoria}/{empresa}/Contratos/
                    empresa_base = get_empresa_storage_path(gestoria_id, emp_nombre)
                    contratos_dir = os.path.join(empresa_base, "Contratos")
                    os.makedirs(contratos_dir, exist_ok=True)
                    
                    # Nombre normalizado: CONTRATO_[NIF]_[FECHA].pdf
                    new_filename = f"CONTRATO_{nif_trabajador}_{fecha_inicio}.pdf"
                    final_path = os.path.join(contratos_dir, new_filename)
                    
                    # Evitar sobreescribir
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
                                categoria=DocumentCategories.CONTRATOS,
                                fecha_creacion=datetime.utcnow(),
                                guardado=True,
                                procesado=True,
                                periodo=str(datetime.now().year),
                                file_hash=hash_archivo,
                                datos_extraidos=res
                            )
                            db.session.add(nuevo_doc)
                            total_archivos_generados += 1
                            processed_details.append({
                                'nombre_trabajador': nombre_trabajador,
                                'empresa': emp_nombre,
                                'estado': 'exito',
                                'mensaje': 'Contrato procesado correctamente'
                            })
                        else:
                            processed_details.append({
                                'nombre_trabajador': nombre_trabajador,
                                'empresa': emp_nombre,
                                'estado': 'duplicado',
                                'mensaje': 'El contrato ya existe'
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
                current_app.logger.error(f"Error procesando Contrato {file.filename}: {e}")
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
            'message': f'Procesados {total_archivos_generados} contratos' if total_archivos_generados > 0 else 'No se pudo procesar ningún archivo.',
            'results': processed_details
        })
