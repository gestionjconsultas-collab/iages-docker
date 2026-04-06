# backend/routes_plantilla_test.py
"""
Endpoints del Test Bench de Plantillas.
Permite subir archivos de prueba, ejecutar tests con N pasadas y ver el historial de resultados.
"""
import os
import uuid
import time
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import Plantilla, PlantillaTestFile, PlantillaTestResult

plantilla_test_bp = Blueprint('plantilla_test', __name__)

ALLOWED_EXTENSIONS = {'pdf'}
TEST_FILES_DIR = '/var/www/iages/backend/plantilla_test_files'


def _get_test_files_dir():
    """Obtiene o crea el directorio de archivos de prueba."""
    d = current_app.config.get('PLANTILLA_TEST_FILES_DIR', TEST_FILES_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_gestoria_id():
    return current_user.gestoria_id if hasattr(current_user, 'gestoria_id') else 1


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/plantillas/<id>/test-files — Listar archivos de prueba
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/test-files', methods=['GET'])
@login_required
def listar_test_files(plantilla_id):
    plantilla = Plantilla.query.get_or_404(plantilla_id)
    return jsonify({
        'test_files': [f.to_dict() for f in plantilla.test_files],
        'total': len(plantilla.test_files)
    })


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/plantillas/<id>/test-files — Subir PDF de prueba
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/test-files', methods=['POST'])
@login_required
def subir_test_file(plantilla_id):
    plantilla = Plantilla.query.get_or_404(plantilla_id)

    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400

    file = request.files['file']
    if not file or not _allowed_file(file.filename):
        return jsonify({'error': 'Solo se permiten archivos PDF'}), 400

    descripcion = request.form.get('descripcion', '')
    campos_esperados = {}
    try:
        import json
        raw = request.form.get('campos_esperados', '{}')
        campos_esperados = json.loads(raw)
    except Exception:
        pass

    # Guardar archivo con nombre único
    test_dir = _get_test_files_dir()
    unique_name = f"{plantilla_id}_{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    ruta = os.path.join(test_dir, unique_name)
    file.save(ruta)

    test_file = PlantillaTestFile(
        plantilla_id=plantilla_id,
        nombre_archivo=file.filename,
        ruta_archivo=ruta,
        descripcion=descripcion,
        campos_esperados=campos_esperados
    )
    db.session.add(test_file)
    db.session.commit()

    return jsonify({'success': True, 'test_file': test_file.to_dict()}), 201


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/plantillas/<id>/test-files/<fid> — Eliminar archivo de prueba
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/test-files/<int:file_id>', methods=['DELETE'])
@login_required
def eliminar_test_file(plantilla_id, file_id):
    test_file = PlantillaTestFile.query.filter_by(id=file_id, plantilla_id=plantilla_id).first_or_404()

    # Eliminar archivo físico
    try:
        if os.path.exists(test_file.ruta_archivo):
            os.remove(test_file.ruta_archivo)
    except Exception as e:
        current_app.logger.warning(f"No se pudo eliminar el archivo físico: {e}")

    db.session.delete(test_file)
    db.session.commit()
    return jsonify({'success': True})


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/plantillas/<id>/run-test — Ejecutar Test Bench
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/run-test', methods=['POST'])
@login_required
def run_test(plantilla_id):
    """
    Ejecuta el Test Bench para una plantilla.
    Body JSON: { "n_pasadas": 5, "file_ids": [1, 2, 3] }  (file_ids opcional → usa todos)
    """
    plantilla = Plantilla.query.get_or_404(plantilla_id)

    data = request.get_json() or {}
    n_pasadas = max(1, min(int(data.get('n_pasadas', 5)), 20))  # entre 1 y 20
    file_ids = data.get('file_ids', None)

    # Seleccionar archivos de prueba
    if file_ids:
        test_files = PlantillaTestFile.query.filter(
            PlantillaTestFile.plantilla_id == plantilla_id,
            PlantillaTestFile.id.in_(file_ids)
        ).all()
    else:
        test_files = plantilla.test_files

    if not test_files:
        return jsonify({'error': 'No hay archivos de prueba. Sube al menos un PDF primero.'}), 400

    # Preparar plantilla como dict para el extractor
    plantilla_dict = {
        'nombre': plantilla.nombre,
        'campos': plantilla.campos or {},
        'prompt_template': plantilla.prompt_template,
        'patron_deteccion': plantilla.patron_deteccion,
    }

    from services.notificacion_extractor import NotificacionExtractor
    extractor = NotificacionExtractor()

    resultados_sesion = []
    total_tasa = 0.0
    total_runs = 0

    for test_file in test_files:
        if not os.path.exists(test_file.ruta_archivo):
            resultados_sesion.append({
                'nombre_archivo': test_file.nombre_archivo,
                'error': 'Archivo no encontrado en disco',
                'pasadas': []
            })
            continue

        pasadas_archivo = []

        for pasada in range(n_pasadas):
            # Pequeña pausa para evitar Rate Limit (429) de la API de IA
            if pasada > 0:
                time.sleep(2) 
            
            try:
                # 1. Verificar detección del patrón
                # 1. Verificar detección del patrón
                patron_detectado = False
                patron_str = (plantilla.patron_deteccion or "").strip()
                
                if patron_str:
                    texto = extractor.extract_text_from_pdf(test_file.ruta_archivo)
                    patron_detectado = patron_str.upper() in texto.upper()
                else:
                    patron_detectado = True  # Sin patrón → siempre pasa

                # 2. Extraer campo por campo (SIN IA - SOLO OCR + REGEX)
                # Primero obtenemos el texto crudo
                texto = extractor.extract_text_from_pdf(test_file.ruta_archivo)
                
                # Intentamos extracción por Regex (si hay reglas simples en la plantilla)
                # Si no hay reglas, devolverá diccionario vacío, pero tendremos el texto
                resultado_ia = extractor._extract_with_regex(texto, plantilla_dict) or {}
                
                # Metadata simulada
                resultado_ia['_metadata'] = {'metodo': 'OCR_ONLY', 'tipo_documento': plantilla_dict['nombre']}
                
                # 3. Calcular tasa de éxito comparando con campos esperados
                campos_esperados = test_file.campos_esperados or {}
                campos_extraidos = {k: v for k, v in resultado_ia.items() if not k.startswith('_')}

                if campos_esperados:
                    # Comparar campo a campo (tolerante: lower + strip)
                    correctos = 0
                    for campo, valor_esperado in campos_esperados.items():
                        valor_extraido = str(campos_extraidos.get(campo, '')).strip().lower()
                        valor_esp = str(valor_esperado).strip().lower()
                        if valor_extraido and valor_extraido == valor_esp:
                            correctos += 1
                    tasa = correctos / len(campos_esperados) if campos_esperados else 0.0
                    campos_totales = len(campos_esperados)
                    campos_correctos = correctos
                else:
                    # Sin campos esperados: éxito si se extrajeron campos
                    tiene_error = 'error' in resultado_ia
                    campos_extraidos_validos = sum(1 for v in campos_extraidos.values() if v and str(v).strip())
                    campos_totales = len(plantilla_dict['campos'])
                    campos_correctos = min(campos_extraidos_validos, campos_totales)
                    tasa = (campos_correctos / campos_totales) if campos_totales > 0 else (0.0 if tiene_error else 1.0)

                # 4. Guardar resultado en BD
                result_obj = PlantillaTestResult(
                    plantilla_id=plantilla_id,
                    test_file_id=test_file.id,
                    campos_extraidos=campos_extraidos,
                    patron_detectado=patron_detectado,
                    tasa_exito=tasa,
                    campos_correctos=campos_correctos,
                    campos_totales=campos_totales,
                    nombre_archivo=test_file.nombre_archivo
                )
                db.session.add(result_obj)

                pasadas_archivo.append({
                    'pasada': pasada + 1,
                    'patron_detectado': patron_detectado,
                    'campos_extraidos': campos_extraidos,
                    'tasa_exito': round(tasa, 4),
                    'campos_correctos': campos_correctos,
                    'campos_totales': campos_totales,
                })

                total_tasa += tasa
                total_runs += 1

            except Exception as e:
                # Si falla la IA (ej. 429), intentamos guardar el resultado con error pero CON el texto extraído
                # para que el usuario pueda al menos ver el OCR
                texto_err = texto if 'texto' in locals() else ""
                
                result_obj = PlantillaTestResult(
                    plantilla_id=plantilla_id,
                    test_file_id=test_file.id,
                    error=str(e),
                    nombre_archivo=test_file.nombre_archivo,
                    # No guardamos texto en BD por ahora si no hay campo, pero el objeto frontend lo necesita
                )
                db.session.add(result_obj)
                pasadas_archivo.append({
                    'pasada': pasada + 1,
                    'error': str(e),
                    'tasa_exito': 0.0,
                    'texto_completo': texto_err[:5000] if texto_err else "No extraído (Error previo a OCR)",
                    'campos_extraidos': {} 
                })
                total_runs += 1
                time.sleep(1) # Breve pausa extra en caso de error continuo

        resultados_sesion.append({
            'nombre_archivo': test_file.nombre_archivo,
            'n_pasadas': n_pasadas,
            'pasadas': pasadas_archivo,
            'tasa_media': round(sum(p.get('tasa_exito', 0) for p in pasadas_archivo) / len(pasadas_archivo), 4) if pasadas_archivo else 0.0
        })

    # 5. Actualizar score_confianza de la plantilla (promedio de los últimos 20 resultados)
    ultimos_resultados = PlantillaTestResult.query.filter_by(plantilla_id=plantilla_id)\
        .order_by(PlantillaTestResult.fecha_ejecucion.desc()).limit(20).all()

    if ultimos_resultados:
        nuevo_score = sum(r.tasa_exito or 0 for r in ultimos_resultados) / len(ultimos_resultados)
        plantilla.score_confianza = round(nuevo_score, 4)
        plantilla.total_tests_ejecutados = (plantilla.total_tests_ejecutados or 0) + total_runs

        # Desactivar automáticamente si baja del umbral
        if nuevo_score < (plantilla.umbral_activacion or 0.9) and plantilla.activa:
            plantilla.activa = False
            current_app.logger.warning(
                f"⚠️ Plantilla '{plantilla.nombre}' desactivada automáticamente. Score: {nuevo_score:.2%}"
            )

    db.session.commit()

    # Resumen global de la sesión
    tasa_global = total_tasa / total_runs if total_runs > 0 else 0.0
    return jsonify({
        'success': True,
        'tasa_global': round(tasa_global, 4),
        'tasa_global_pct': f"{tasa_global * 100:.1f}%",
        'total_runs': total_runs,
        'score_confianza': plantilla.score_confianza,
        'activa': plantilla.activa,
        'resultados': resultados_sesion
    })


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/plantillas/<id>/test-results — Historial de resultados
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/test-results', methods=['GET'])
@login_required
def listar_test_results(plantilla_id):
    Plantilla.query.get_or_404(plantilla_id)
    limit = min(int(request.args.get('limit', 50)), 200)

    results = PlantillaTestResult.query.filter_by(plantilla_id=plantilla_id)\
        .order_by(PlantillaTestResult.fecha_ejecucion.desc()).limit(limit).all()

    return jsonify({
        'results': [r.to_dict() for r in results],
        'total': len(results)
    })


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/plantillas/<id>/toggle-active — Activar/desactivar manualmente
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/toggle-active', methods=['POST'])
@login_required
def toggle_active(plantilla_id):
    plantilla = Plantilla.query.get_or_404(plantilla_id)
    plantilla.activa = not (plantilla.activa if plantilla.activa is not None else True)
    db.session.commit()
    return jsonify({
        'success': True,
        'activa': plantilla.activa,
        'mensaje': f"Plantilla {'activada' if plantilla.activa else 'desactivada'} correctamente"
    })


# ─────────────────────────────────────────────────────────────────────────────
# PUT /api/plantillas/<id>/test-files/<fid>/campos-esperados — Actualizar valores esperados
# ─────────────────────────────────────────────────────────────────────────────
@plantilla_test_bp.route('/api/plantillas/<int:plantilla_id>/test-files/<int:file_id>/campos-esperados', methods=['PUT'])
@login_required
def actualizar_campos_esperados(plantilla_id, file_id):
    test_file = PlantillaTestFile.query.filter_by(id=file_id, plantilla_id=plantilla_id).first_or_404()
    data = request.get_json() or {}
    test_file.campos_esperados = data.get('campos_esperados', {})
    test_file.descripcion = data.get('descripcion', test_file.descripcion)
    db.session.commit()
    return jsonify({'success': True, 'test_file': test_file.to_dict()})
