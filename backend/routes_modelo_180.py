from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import tempfile
import shutil
from datetime import datetime

from extensions import db
from models import Documento, Empresa
from utils import limpiar_nombre_carpeta
from utils.storage_utils import get_empresa_storage_path
from utils.file_utils import get_file_hash
from tenant_utils import get_current_gestoria_id
from services.procesar_modelo_180 import procesar_certificados_180

modelo_180_bp = Blueprint('modelo_180', __name__)

@modelo_180_bp.route('/api/procesar-modelo-180', methods=['POST'])
@login_required
def procesar_modelo_180():
    """
    Endpoint para procesar Certificados Modelo 180.
    Recibe un PDF consolidado, lo fragmenta y vincula a arrendatarios (usando tabla Empleados).
    """
    files = request.files.getlist('files') if 'files' in request.files else []
    if not files and 'file' in request.files:
        files = [request.files['file']]
        
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
            
            if deteccion.get("analizado") and deteccion.get("tipo_detectado") not in ["certificados_180", "desconocido"]:
                return jsonify({
                    'success': False,
                    'estado': 'confirmacion',
                    'detectado': deteccion.get("tipo_detectado"),
                    'empresa_detectada': deteccion.get("empresa_detectada"),
                    'filename': file.filename,
                    'message': f'El archivo {file.filename} parece ser de tipo {deteccion.get("tipo_detectado").replace("_", " ")}. ¿Continuar como Certificados 180?'
                }), 400

    periodo_manual = request.form.get('periodo', str(datetime.now().year))
    gestoria_id = get_current_gestoria_id()
    
    storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    app_temp_dir = os.path.join(backend_dir, 'temp')
    os.makedirs(app_temp_dir, exist_ok=True)

    processed_details = []
    total_archivos_generados = 0
    unique_companies = set()

    for file in files:
        temp_dir = tempfile.mkdtemp(dir=app_temp_dir)
        temp_pdf_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_pdf_path)

        output_fragments_dir = os.path.join(temp_dir, "fragments")
        
        try:
            # Procesar el Modelo 180
            resultados = procesar_certificados_180(
                pdf_path=temp_pdf_path, 
                output_dir=output_fragments_dir, 
                gestoria_id=gestoria_id
            )
            
            for res in resultados:
                empresa_id = res.get('empresa_id')
                nif_empresa_ext = res.get('nif_empresa')
                nombre_empresa = res.get('nombre_empresa', 'Empresa_Desconocida')
                pdf_fragmento_path = res.get('pdf_path')
                nif_arrendatario = res.get('nif_arrendatario')
                nombre_arrendatario = res.get('nombre_arrendatario', 'Arrendatario_Desconocido')
                ejercicio_extraido = res.get('ejercicio')
                
                # Usar el año extraído si existe, sino el manual
                year_db = str(ejercicio_extraido) if ejercicio_extraido else str(periodo_manual)
                
                if nif_empresa_ext:
                    unique_companies.add(nif_empresa_ext)

                if empresa_id:
                    empresa = db.session.get(Empresa, empresa_id)
                    emp_nombre = empresa.nombre if empresa else nombre_empresa
                else:
                    emp_nombre = nombre_empresa
                
                empresa_dir = os.path.join(get_empresa_storage_path(gestoria_id, emp_nombre), "Fiscal")
                os.makedirs(empresa_dir, exist_ok=True)
                
                final_path = os.path.join(empresa_dir, os.path.basename(pdf_fragmento_path))
                shutil.copy2(pdf_fragmento_path, final_path)
                
                if empresa_id:
                    # Calcular hash del archivo
                    hash_archivo = get_file_hash(final_path)

                    # Verificar duplicado
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
                            categoria='Certificados de Retenciones 180',
                            fecha_creacion=datetime.utcnow(),
                            guardado=True,
                            procesado=True,
                            periodo=year_db,
                            file_hash=hash_archivo,
                            datos_extraidos={
                                'nif_empleado': nif_arrendatario, # Lo guardamos bajo esta key genérica por compatibilidad con UI
                                'nombre_empleado': nombre_arrendatario, # Nombre del Arrendatario
                                'ejercicio': year_db
                            }
                        )
                        db.session.add(nuevo_doc)
                
                total_archivos_generados += 1
                processed_details.append({
                    'nombre_trabajador': nombre_arrendatario,
                    'empresa': nombre_empresa,
                    'estado': 'exito',
                    'mensaje': f'Documento C-180 de {res.get("pages")} página(s)'
                })
                
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error procesando {file.filename}: {e}")
            processed_details.append({
                'nombre_trabajador': f'Error procesando archivo',
                'empresa': '-',
                'estado': 'error',
                'mensaje': str(e)
            })
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    final_success = total_archivos_generados > 0

    return jsonify({
        'success': final_success,
        'message': f'Procesados {total_archivos_generados} certificados' if final_success else 'No se pudo procesar ningún certificado.',
        'async': False,
        'total_empresas': len(unique_companies),
        'total_archivos_generados': total_archivos_generados,
        'results': processed_details
    }), 200
