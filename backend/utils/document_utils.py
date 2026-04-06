import logging
from datetime import datetime
from models import db, Documento, GrupoDocumentos, GrupoDocumentosItem, User
from constants import DocumentCategories

logger = logging.getLogger(__name__)

def auto_group_altas(documento_id, gestoria_id, user_id=None):
    """
    Agrupa automáticamente documentos de Alta o Baja (TA/IDC) del mismo trabajador y fecha.
    """
    doc = db.session.get(Documento, documento_id)
    if not doc:
        return None
        
    is_alta = doc.categoria == DocumentCategories.ALTAS_TRABAJADORES
    is_baja = doc.categoria == DocumentCategories.BAJAS_TRABAJADORES
    
    if not is_alta and not is_baja:
        return None

    # Extraer NIF y Fecha de los datos extraídos
    datos = doc.datos_extraidos or {}
    nif = datos.get('nif_trabajador') or datos.get('nif_empleado')
    # Usamos fecha_alta como campo genérico para el movimiento (en bajas se extrae como fecha_alta/movimiento)
    fecha_mov = datos.get('fecha_movimiento') or datos.get('fecha_alta')

    if not nif or not fecha_mov:
        logger.warning(f"No se puede agrupar doc {documento_id}: NIF o Fecha faltante.")
        return None

    # 1. Buscar si ya existe un grupo para este trabajador y fecha
    # El nombre del grupo será estandarizado: "Alta - [NIF] - [Fecha]" o "Baja - [NIF] - [Fecha]"
    prefijo = "Alta" if is_alta else "Baja"
    nombre_grupo = f"{prefijo} - {nif} - {fecha_mov}"
    
    grupo = GrupoDocumentos.query.filter_by(
        empresa_id=doc.empresa_id,
        nombre=nombre_grupo
    ).first()

    if grupo:
        # Verificar si el documento ya está en el grupo
        existente = GrupoDocumentosItem.query.filter_by(
            grupo_id=grupo.id,
            documento_id=doc.id
        ).first()
        
        if not existente:
            nuevo_item = GrupoDocumentosItem(
                grupo_id=grupo.id,
                documento_id=doc.id,
                agregado_by=user_id or doc.asignado_a_id
            )
            db.session.add(nuevo_item)
            db.session.commit()
            logger.info(f"Documento {doc.id} agregado al grupo existente: {nombre_grupo}")
        return grupo

    # 2. Si no existe el grupo, buscar otros documentos del mismo trabajador/fecha
    # que NO estén agrupados para crear el grupo
    # Usamos filtrado en Python para evitar problemas de compatibilidad con JSON en diferentes BDs
    categoria_busqueda = DocumentCategories.ALTAS_TRABAJADORES if is_alta else DocumentCategories.BAJAS_TRABAJADORES
    
    otros_docs_raw = Documento.query.filter(
        Documento.id != doc.id,
        Documento.empresa_id == doc.empresa_id,
        Documento.categoria == categoria_busqueda,
    ).all()

    otros_docs = [
        d for d in otros_docs_raw
        if d.datos_extraidos
        and (d.datos_extraidos.get('nif_trabajador') == nif or d.datos_extraidos.get('nif_empleado') == nif)
        and (d.datos_extraidos.get('fecha_movimiento') == fecha_mov or d.datos_extraidos.get('fecha_alta') == fecha_mov)
    ]

    if otros_docs:
        # Crear nuevo grupo
        tipo_label = "Alta" if is_alta else "Baja"
        nombre_empleado_val = datos.get('nombre_trabajador') or datos.get('nombre_empleado') or nif
        nuevo_grupo = GrupoDocumentos(
            nombre=nombre_grupo,
            descripcion=f"Expediente de {tipo_label} para {nombre_empleado_val}",
            empresa_id=doc.empresa_id,
            color='emerald' if is_alta else 'orange',
            created_by=user_id or doc.asignado_a_id
        )
        db.session.add(nuevo_grupo)
        db.session.flush() # Para obtener el ID

        # Agregar el documento actual
        item_actual = GrupoDocumentosItem(
            grupo_id=nuevo_grupo.id,
            documento_id=doc.id,
            agregado_by=user_id or doc.asignado_a_id
        )
        db.session.add(item_actual)

        # Agregar los otros documentos encontrados
        for otro in otros_docs:
            item_otro = GrupoDocumentosItem(
                grupo_id=nuevo_grupo.id,
                documento_id=otro.id,
                agregado_by=user_id or doc.asignado_a_id
            )
            db.session.add(item_otro)
        
        db.session.commit()
        logger.info(f"Creado nuevo grupo {nombre_grupo} con {len(otros_docs) + 1} documentos")
        return nuevo_grupo

    return None

def auto_group_contratos(documento_id, gestoria_id, user_id=None):
    """
    Agrupa automáticamente documentos de Contratos del mismo trabajador y fecha.
    """
    doc = db.session.get(Documento, documento_id)
    if not doc or doc.categoria != DocumentCategories.CONTRATOS:
        return None

    # Extraer NIF y Fecha de los datos extraídos
    datos = doc.datos_extraidos or {}
    nif = datos.get('nif_trabajador') or datos.get('nif_empleado')
    fecha_inicio = datos.get('fecha_inicio')

    if not nif or not fecha_inicio:
        logger.warning(f"No se puede agrupar contrato {documento_id}: NIF o Fecha faltante.")
        return None

    # 1. Buscar si ya existe un grupo para este trabajador y fecha
    nombre_grupo = f"Contrato - {nif} - {fecha_inicio}"
    
    grupo = GrupoDocumentos.query.filter_by(
        empresa_id=doc.empresa_id,
        nombre=nombre_grupo
    ).first()

    if grupo:
        # Verificar si el documento ya está en el grupo
        existente = GrupoDocumentosItem.query.filter_by(
            grupo_id=grupo.id,
            documento_id=doc.id
        ).first()
        
        if not existente:
            nuevo_item = GrupoDocumentosItem(
                grupo_id=grupo.id,
                documento_id=doc.id,
                agregado_by=user_id or doc.asignado_a_id
            )
            db.session.add(nuevo_item)
            db.session.commit()
            logger.info(f"Contrato {doc.id} agregado al grupo existente: {nombre_grupo}")
        return grupo

    # 2. Si no existe el grupo, buscar otros contratos del mismo trabajador/fecha
    otros_docs_raw = Documento.query.filter(
        Documento.id != doc.id,
        Documento.empresa_id == doc.empresa_id,
        Documento.categoria == DocumentCategories.CONTRATOS,
    ).all()

    otros_docs = [
        d for d in otros_docs_raw
        if d.datos_extraidos
        and (d.datos_extraidos.get('nif_trabajador') == nif or d.datos_extraidos.get('nif_empleado') == nif)
        and d.datos_extraidos.get('fecha_inicio') == fecha_inicio
    ]

    if otros_docs:
        # Crear nuevo grupo
        nombre_empleado_val = datos.get('nombre_trabajador') or datos.get('nombre_empleado') or nif
        nuevo_grupo = GrupoDocumentos(
            nombre=nombre_grupo,
            descripcion=f"Expediente de Contrato para {nombre_empleado_val}",
            empresa_id=doc.empresa_id,
            color='blue',
            created_by=user_id or doc.asignado_a_id
        )
        db.session.add(nuevo_grupo)
        db.session.flush() # Para obtener el ID

        # Agregar el documento actual
        item_actual = GrupoDocumentosItem(
            grupo_id=nuevo_grupo.id,
            documento_id=doc.id,
            agregado_by=user_id or doc.asignado_a_id
        )
        db.session.add(item_actual)

        # Agregar los otros documentos encontrados
        for otro in otros_docs:
            item_otro = GrupoDocumentosItem(
                grupo_id=nuevo_grupo.id,
                documento_id=otro.id,
                agregado_by=user_id or doc.asignado_a_id
            )
            db.session.add(item_otro)
        
        db.session.commit()
        logger.info(f"Creado nuevo grupo {nombre_grupo} con {len(otros_docs) + 1} documentos de contrato")
        return nuevo_grupo

    return None
