# backend/routes_grupos_documentos.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, GrupoDocumentos, GrupoDocumentosItem, Documento
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from constants import NotificationTypes

grupos_bp = Blueprint('grupos', __name__)

# ==========================================
# GESTIÓN DE GRUPOS
# ==========================================

@grupos_bp.route('/api/grupos-documentos', methods=['POST'])
@login_required
def crear_grupo():
    """Crear un nuevo grupo de documentos"""
    try:
        data = request.json
        
        nuevo_grupo = GrupoDocumentos(
            nombre=data.get('nombre'),
            descripcion=data.get('descripcion'),
            empresa_id=data.get('empresa_id'),
            color=data.get('color', 'blue'),
            created_by=current_user.id
        )
        
        db.session.add(nuevo_grupo)
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'grupo': nuevo_grupo.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@grupos_bp.route('/api/grupos-documentos', methods=['GET'])
@login_required
def listar_grupos():
    """Listar grupos de documentos (opcionalmente filtrados por empresa)"""
    try:
        empresa_id = request.args.get('empresa_id', type=int)
        
        query = GrupoDocumentos.query
        
        if empresa_id:
            query = query.filter_by(empresa_id=empresa_id)
        
        grupos = query.order_by(GrupoDocumentos.created_at.desc()).all()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'grupos': [g.to_dict() for g in grupos]
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@grupos_bp.route('/api/grupos-documentos/<int:id>', methods=['GET'])
@login_required
def obtener_grupo(id):
    """Obtener un grupo con todos sus documentos"""
    try:
        grupo = db.session.get(GrupoDocumentos, id)
        
        if not grupo:
            return jsonify({NotificationTypes.ERROR: 'Grupo no encontrado'}), 404
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'grupo': grupo.to_dict_full()
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@grupos_bp.route('/api/grupos-documentos/<int:id>', methods=['PATCH'])
@login_required
def actualizar_grupo(id):
    """Actualizar nombre/descripción de un grupo"""
    try:
        grupo = db.session.get(GrupoDocumentos, id)
        if not grupo:
            return jsonify({NotificationTypes.ERROR: 'Grupo no encontrado'}), 404
        data = request.get_json() or {}
        if 'nombre' in data and data['nombre'].strip():
            grupo.nombre = data['nombre'].strip()
        if 'descripcion' in data:
            grupo.descripcion = data['descripcion']
        db.session.commit()
        return jsonify({NotificationTypes.SUCCESS: True, 'grupo': grupo.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@grupos_bp.route('/api/grupos-documentos/<int:id>', methods=['DELETE'])
@login_required
def eliminar_grupo(id):
    """Eliminar un grupo (los documentos no se eliminan, solo la relación)"""
    try:
        grupo = db.session.get(GrupoDocumentos, id)
        
        if not grupo:
            return jsonify({NotificationTypes.ERROR: 'Grupo no encontrado'}), 404
        
        db.session.delete(grupo)
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# GESTIÓN DE DOCUMENTOS EN GRUPO
# ==========================================

@grupos_bp.route('/api/grupos-documentos/<int:id>/documentos', methods=['POST'])
@login_required
def agregar_documento_a_grupo(id):
    """Agregar un documento a un grupo"""
    try:
        grupo = db.session.get(GrupoDocumentos, id)
        
        if not grupo:
            return jsonify({NotificationTypes.ERROR: 'Grupo no encontrado'}), 404
        
        data = request.json
        documento_id = data.get('documento_id')
        
        # Verificar que el documento existe
        documento = db.session.get(Documento, documento_id)
        if not documento:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado'}), 404
        
        # Verificar que no esté ya en el grupo
        existe = GrupoDocumentosItem.query.filter_by(
            grupo_id=id,
            documento_id=documento_id
        ).first()
        
        if existe:
            return jsonify({NotificationTypes.ERROR: 'El documento ya está en este grupo'}), 400
        
        # Agregar documento al grupo
        item = GrupoDocumentosItem(
            grupo_id=id,
            documento_id=documento_id,
            agregado_by=current_user.id
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'item': item.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


@grupos_bp.route('/api/grupos-documentos/<int:id>/documentos/<int:documento_id>', methods=['DELETE'])
@login_required
def quitar_documento_de_grupo(id, documento_id):
    """Quitar un documento de un grupo"""
    try:
        item = GrupoDocumentosItem.query.filter_by(
            grupo_id=id,
            documento_id=documento_id
        ).first()
        
        if not item:
            return jsonify({NotificationTypes.ERROR: 'Documento no encontrado en este grupo'}), 404
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({NotificationTypes.SUCCESS: True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# OBTENER GRUPOS DE UN DOCUMENTO
# ==========================================

@grupos_bp.route('/api/documentos/<int:documento_id>/grupos', methods=['GET'])
@login_required
def obtener_grupos_de_documento(documento_id):
    """Obtener todos los grupos a los que pertenece un documento"""
    try:
        items = GrupoDocumentosItem.query.filter_by(documento_id=documento_id).all()
        
        grupos = [item.grupo.to_dict() for item in items if item.grupo]
        
        return jsonify({
            NotificationTypes.SUCCESS: True,
            'grupos': grupos
        })
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500


# ==========================================
# ENVÍO MASIVO POR EMAIL
# ==========================================

@grupos_bp.route('/api/grupos-documentos/<int:id>/enviar-email', methods=['POST'])
@login_required
def enviar_email_masivo(id):
    """Enviar todos los documentos de un grupo por email"""
    try:
        grupo = db.session.get(GrupoDocumentos, id)
        
        if not grupo:
            return jsonify({NotificationTypes.ERROR: 'Grupo no encontrado'}), 404
        
        data = request.json
        destinatarios = data.get('destinatarios', [])
        asunto = data.get('asunto', f'Documentos: {grupo.nombre}')
        mensaje = data.get('mensaje', '')
        
        if not destinatarios:
            return jsonify({NotificationTypes.ERROR: 'Debe especificar al menos un destinatario'}), 400
        
        # Obtener todos los documentos del grupo
        documentos = [item.documento for item in grupo.items if item.documento]
        
        if not documentos:
            return jsonify({NotificationTypes.ERROR: 'El grupo no tiene documentos'}), 400
        
        # Importar función de envío de email
        from email_sender import enviar_email_con_adjuntos
        
        # Preparar lista de archivos adjuntos
        adjuntos = []
        for doc in documentos:
            if doc.ruta_archivo and os.path.exists(doc.ruta_archivo):
                adjuntos.append({
                    'ruta': doc.ruta_archivo,
                    'nombre': doc.nombre_archivo
                })
        
        if not adjuntos:
            return jsonify({NotificationTypes.ERROR: 'No se encontraron archivos para enviar'}), 400
        
        # Generar cuerpo del email con lista de documentos
        cuerpo_completo = f"{mensaje}\n\n"
        cuerpo_completo += f"Documentos incluidos ({len(adjuntos)}):\n"
        for i, doc in enumerate(documentos, 1):
            cuerpo_completo += f"{i}. {doc.nombre_archivo}\n"
        
        # Enviar email con HTML template
        resultado = enviar_email_con_adjuntos(
            destinatarios=destinatarios,
            asunto=asunto,
            cuerpo=mensaje,
            adjuntos=adjuntos,
            usar_html=True,
            empresa_nombre=grupo.empresa.nombre if grupo.empresa else 'Empresa',
            gestoria_id=grupo.empresa.gestoria_id if grupo.empresa else None
        )
        
        if resultado[NotificationTypes.SUCCESS]:
            return jsonify({
                NotificationTypes.SUCCESS: True,
                'mensaje': f'Email enviado con {len(adjuntos)} documentos',
                'total_documentos': len(adjuntos)
            })
        else:
            return jsonify({NotificationTypes.ERROR: resultado.get(NotificationTypes.ERROR, 'Error al enviar email')}), 500
        
    except Exception as e:
        return jsonify({NotificationTypes.ERROR: str(e)}), 500