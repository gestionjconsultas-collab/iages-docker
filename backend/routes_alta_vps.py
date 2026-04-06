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
from services.procesar_altas import procesar_altas

alta_bp = Blueprint('alta', __name__)

@alta_bp.route('/api/procesar-alta', methods=['POST'])
@login_required
def api_procesar_alta():
    """
    Endpoint para procesar documentos de Alta (TA / IDC).
    """
    files = request.files.getlist('files') if 'files' in request.files else []
    if not files and 'file' in request.files:
        files = [request.files['file']]
        
    if not files:
        return jsonify({'success': False, 'message': 'No se envió ningún archivo'}), 400
        
    gestoria_id = get_current_gestoria_id()
    storage_dir = current_app.config['RUTA_RAIZ_NOTIFICACIONES']
    
    # Directorio temporal para descarga/procesamiento
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

        # Directorio para fragmentos (aunque en Alta solemos manejar el archivo entero)
        output_fragments_dir = os.path.join(temp_dir, "fragments")
        
        try:
            resultados = procesar_altas(
                pdf_path=temp_pdf_path, 
                output_dir=output_fragments_dir, 
                gestoria_id=gestoria_id
            )
            
            current_app.logger.info(f"[ALTA ROUTE] Resultados de procesar_altas: {resultados}")
            
            for res in resultados:
                empresa_id = res.get('empresa_id')
                nombre_empresa = res.get('nombre_empresa', 'Empresa_Desconocida')
                pdf_final_path = res.get('pdf_path')
                nif_trabajador = res.get('nif_trabajador')
                nombre_trabajador = res.get('nombre_trabajador', 'Trabajador_Desconocido')
                ejercicio_extraido = res.get('ejercicio')
                tipo_doc = res.get('tipo_documento', 'Alta')
                
                # Carpeta: /storage/{gestoria_slug}/{empresa}/Laboral/
                current_app.logger.info(f"[ALTA ROUTE] empresa_id={empresa_id}, nombre_empresa={nombre_empresa}, nif_trabajador={nif_trabajador}")
                if empresa_id:
                    unique_companies.add(empresa_id)
                    empresa = db.session.get(Empresa, empresa_id)
                    emp_nombre = empresa.nombre if empresa else nombre_empresa
                else:
                    emp_nombre = nombre_empresa
                
                # Usa storage_utils para path con gestoria subfolder
                empresa_base = get_empresa_storage_path(gestoria_id, emp_nombre)
                laboral_dir = os.path.join(empresa_base, "Laboral")
                os.makedirs(laboral_dir, exist_ok=True)
                
                # UNIFICACIÓN: Nombre de archivo basado en NIF + Fecha de Alta
                fecha_str_file = res.get('fecha_alta').replace('/', '-') if res.get('fecha_alta') else "SinFecha"
                tipo_corto = "IDC" if "IDC" in tipo_doc else "TA"
                new_filename = f"ALTA_{tipo_corto}_{nif_trabajador}_{fecha_str_file}.pdf"
                
                final_path = os.path.join(laboral_dir, new_filename)
                shutil.copy2(pdf_final_path, final_path)
                
                if empresa_id:
                    hash_archivo = get_file_hash(final_path)
                    
                    # Evitar duplicado en la misma empresa
                    doc_existente = Documento.query.filter_by(
                        empresa_id=empresa_id,
                        file_hash=hash_archivo
                    ).first()

                    if not doc_existente:
                        nuevo_doc = Documento(
                            empresa_id=empresa_id,
                            gestoria_id=gestoria_id,
                            nombre_archivo=new_filename,
                            ruta_archivo=final_path,
                            categoria='Altas de Trabajadores',
                            fecha_creacion=datetime.utcnow(),
                            guardado=True,
                            procesado=True,
                            periodo=str(ejercicio_extraido) if ejercicio_extraido else str(datetime.now().year),
                            file_hash=hash_archivo,
                            datos_extraidos={
                                'nif_empleado': nif_trabajador,
                                'nombre_empleado': nombre_trabajador,
                                'tipo_especifico': tipo_doc,
                                'fecha_alta': res.get('fecha_alta'),
                                'nss': res.get('nss'),
                                'grupo_cotizacion': res.get('grupo_cotizacion'),
                                'tipo_contrato': res.get('tipo_contrato')
                            }
                        )
                        db.session.add(nuevo_doc)
                
                total_archivos_generados += 1
                processed_details.append({
                    'nombre_trabajador': nombre_trabajador,
                    'empresa': nombre_empresa,
                    'estado': 'exito',
                    'mensaje': f'{tipo_doc} procesada correctamente'
                })
                
            db.session.commit()
            
        except Exception as e:
            current_app.logger.error(f"Error procesando Alta {file.filename}: {e}")
            processed_details.append({
                'nombre_trabajador': 'Error',
                'empresa': '-',
                'estado': 'error',
                'mensaje': str(e)
            })
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    success = total_archivos_generados > 0
    return jsonify({
        'success': success,
        'message': f'Procesadas {total_archivos_generados} altas' if success else 'No se pudo procesar ningún archivo.',
        'total_empresas': len(unique_companies),
        'results': processed_details
    }), 200
