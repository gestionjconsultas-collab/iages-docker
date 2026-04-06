from flask import jsonify, request, send_file
from flask_login import login_required, current_user
from models import db, Documento, Empresa
from datetime import datetime, date
from sqlalchemy import func, and_, or_, cast, Text
from constants import NotificationTypes
import os

def register_aplazamientos_routes(app):
    """Registra rutas para la gestión de aplazamientos"""
    
    @app.route('/api/aplazamientos/documentos', methods=['GET'])
    @login_required
    def get_aplazamientos_documentos():
        """Lista todos los documentos de aplazamientos"""
        empresa_id = request.args.get('empresa_id', type=int)
        
        # MULTI-TENANT: Filtrar por gestoría
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        # Query: documentos con is_aplazamiento = True
        query = Documento.query.join(Empresa).filter(
            Documento.gestoria_id == gestoria_id,
            cast(Documento.datos_extraidos['is_aplazamiento'], Text) == 'true'
        )
        
        # Filtro de ocultos (por defecto NO mostrar ocultos)
        mostrar_ocultos = request.args.get('mostrar_ocultos', 'false').lower() == 'true'
        if not mostrar_ocultos:
            # Excluir si 'omitir_aplazamiento' es 'true'
            # Usamos or_ para incluir los que no tienen la clave o es false
            query = query.filter(
                or_(
                    cast(Documento.datos_extraidos['omitir_aplazamiento'], Text).is_(None),
                    cast(Documento.datos_extraidos['omitir_aplazamiento'], Text) != 'true'
                )
            )
        
        if empresa_id:
            query = query.filter(Documento.empresa_id == empresa_id)
        
        query = query.order_by(Documento.fecha_creacion.desc())
        documentos = query.all()
        
        resultado = []
        for doc in documentos:
            datos = doc.datos_extraidos or {}
            detalle = datos.get('detalle_liquidacion', [])
            
            # Calcular totales (nueva estructura: detalle = lista de liquidaciones con plazos[])
            total_deuda = 0
            total_intereses = 0
            num_cuotas = 0
            if detalle:
                for liq in detalle:
                    plazos = liq.get('plazos', [])
                    num_cuotas += len(plazos)
                    for p in plazos:
                        total_deuda += p.get('importe_total_plazo', 0)
                        total_intereses += p.get('importe_intereses', 0)
            
            resultado.append({
                'id': doc.id,
                'nombre_archivo': doc.nombre_archivo,
                'empresa_id': doc.empresa_id,
                'empresa_nombre': doc.empresa.nombre if doc.empresa else None,
                'nif': doc.empresa.nif if doc.empresa and doc.empresa.nif else datos.get('nif'),
                'expediente': datos.get('expediente'),
                'fecha_presentacion': datos.get('fecha_presentacion'),
                'fecha_creacion': doc.fecha_creacion.isoformat() if doc.fecha_creacion else None,
                'total_deuda': round(total_deuda, 2),
                'total_intereses': round(total_intereses, 2),
                'num_cuotas': num_cuotas,
                'detalle_liquidacion': detalle,
                'omitido': datos.get('omitir_aplazamiento', False)
            })
        
        return jsonify({NotificationTypes.SUCCESS: True, 'documentos': resultado})

    # ... (Resto de endpoints sin cambios hasta el final) ...

    @app.route('/api/aplazamientos/documentos/<int:doc_id>/toggle-omitir', methods=['POST'])
    @login_required
    def toggle_omitir_aplazamiento(doc_id):
        """Alterna el estado de omitir de un aplazamiento"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # MULTI-TENANT: Verificar que pertenece a la gestoría actual
        from tenant_utils import get_current_gestoria_id
        if doc.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
        
        datos = dict(doc.datos_extraidos or {})
        estado_actual = datos.get('omitir_aplazamiento', False)
        nuevo_estado = not estado_actual
        
        datos['omitir_aplazamiento'] = nuevo_estado
        doc.datos_extraidos = datos
        
        # Necesario force update para JSONfield en algunas BDs
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(doc, "datos_extraidos")
        
        db.session.commit()
        
        action = "ocultado" if nuevo_estado else "restaurado"
        return jsonify({
            NotificationTypes.SUCCESS: True, 
            'message': f'Aplazamiento {action} correctamente',
            'omitido': nuevo_estado
        })

    @app.route('/api/aplazamientos/documentos/<int:doc_id>', methods=['GET'])
    @login_required
    def get_aplazamiento_detalle(doc_id):
        """Obtiene el detalle completo de un aplazamiento"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # MULTI-TENANT: Verificar que pertenece a la gestoría actual
        from tenant_utils import get_current_gestoria_id
        if doc.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
        
        datos = doc.datos_extraidos or {}
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'documento': {
                'id': doc.id,
                'nombre_archivo': doc.nombre_archivo,
                'empresa_nombre': doc.empresa.nombre if doc.empresa else None,
                'nif': doc.empresa.nif if doc.empresa and doc.empresa.nif else datos.get('nif'),
                'expediente': datos.get('expediente'),
                'csv': datos.get('csv'),
                'fecha_presentacion': datos.get('fecha_presentacion'),
                'razon_social': datos.get('razon_social'),
                'detalle_liquidacion': datos.get('detalle_liquidacion', []),
                'omitido': datos.get('omitir_aplazamiento', False)
            }
        })
    
    @app.route('/api/aplazamientos/documentos/<int:doc_id>/pdf', methods=['GET'])
    @login_required
    def servir_pdf_aplazamiento(doc_id):
        """Sirve el archivo PDF del aplazamiento"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # MULTI-TENANT: Verificar que pertenece a la gestoría actual
        from tenant_utils import get_current_gestoria_id
        if doc.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
        
        if not os.path.exists(doc.ruta_archivo):
            return jsonify({NotificationTypes.ERROR: 'Archivo no encontrado'}), 404
        
        return send_file(
            doc.ruta_archivo,
            mimetype='application/pdf',
            as_attachment=False
        )
    
    @app.route('/api/aplazamientos/stats', methods=['GET'])
    @login_required
    def get_aplazamientos_stats():
        """Estadísticas generales de aplazamientos"""
        
        empresa_id = request.args.get('empresa_id', type=int)
        
        # MULTI-TENANT: Filtrar por gestoría
        from tenant_utils import get_current_gestoria_id
        gestoria_id = get_current_gestoria_id()
        
        query = Documento.query.filter(
            Documento.gestoria_id == gestoria_id,
            cast(Documento.datos_extraidos['is_aplazamiento'], Text) == 'true'
        )
        
        # También filtrar ocultos en stats
        query = query.filter(
            or_(
                cast(Documento.datos_extraidos['omitir_aplazamiento'], Text).is_(None),
                cast(Documento.datos_extraidos['omitir_aplazamiento'], Text) != 'true'
            )
        )
        
        if empresa_id:
            query = query.filter(Documento.empresa_id == empresa_id)
        
        total_documentos = query.count()
        
        # Calcular totales sumando desde JSON
        documentos = query.all()
        total_deuda = 0
        total_intereses = 0
        total_cuotas = 0
        
        for doc in documentos:
            detalle = doc.datos_extraidos.get('detalle_liquidacion', [])
            if detalle:
                total_deuda += sum(cuota.get('importe_principal', 0) for cuota in detalle)
                total_intereses += sum(cuota.get('total_intereses', 0) for cuota in detalle)
                total_cuotas += len(detalle)
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'stats': {
                'total_documentos': total_documentos,
                'total_deuda': round(total_deuda, 2),
                'total_intereses': round(total_intereses, 2),
                'total_cuotas': total_cuotas
            }
        })
    
    @app.route('/api/aplazamientos/documentos/<int:doc_id>', methods=['DELETE'])
    @login_required
    def eliminar_aplazamiento(doc_id):
        """Elimina un documento de aplazamiento"""
        
        doc = db.session.get(Documento, doc_id)
        if not doc:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # MULTI-TENANT: Verificar que pertenece a la gestoría actual
        from tenant_utils import get_current_gestoria_id
        if doc.gestoria_id != get_current_gestoria_id():
            return jsonify({NotificationTypes.ERROR: 'Acceso denegado'}), 403
        
        # Eliminar archivo físico si existe
        if os.path.exists(doc.ruta_archivo):
            try:
                os.remove(doc.ruta_archivo)
            except Exception as e:
                pass # Si falla borrado fisico continuamos
        
        # Eliminar relaciones con grupos para evitar FK violation
        from models import GrupoDocumentosItem
        GrupoDocumentosItem.query.filter_by(documento_id=doc_id).delete()

        # Eliminar registro de BD
        db.session.delete(doc)
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True, 'message': 'Aplazamiento eliminado'})
