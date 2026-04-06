#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sistema de envío automático de correos para Nóminas y Seguros Sociales
"""
import os
from datetime import datetime
from extensions import db
from models import Documento, Empresa
from email_sender import enviar_email_con_adjuntos
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from constants import DocumentCategories, NotificationTypes

class CorreoEnviado(db.Model):
    """Modelo para tracking de correos enviados"""
    __tablename__ = 'correos_enviados'
    
    id = Column(Integer, primary_key=True)
    documento_id = Column(Integer, ForeignKey('documentos.id', ondelete='CASCADE'), nullable=False)
    tipo_documento = Column(String(50), nullable=False)  # NOMINA, RNT, RLC
    email_destinatario = Column(String(255), nullable=False)
    fecha_envio = Column(DateTime, default=datetime.utcnow)
    enviado_por_usuario_id = Column(Integer, ForeignKey('users.id'))
    asunto = Column(String(500))
    adjuntos_enviados = Column(PG_ARRAY(String))

def verificar_correo_enviado(documento_id, tipo_documento, email):
    """
    Verifica si ya se envió un correo para este documento
    
    Args:
        documento_id: ID del documento
        tipo_documento: NOMINA, RNT, RLC
        email: Email destinatario
        
    Returns:
        bool: True si ya se envió, False si no
    """
    return CorreoEnviado.query.filter_by(
        documento_id=documento_id,
        tipo_documento=tipo_documento,
        email_destinatario=email
    ).first() is not None

def marcar_correo_enviado(documento_id, tipo_documento, email, usuario_id, asunto, adjuntos):
    """
    Marca un correo como enviado en la base de datos
    
    Args:
        documento_id: ID del documento
        tipo_documento: NOMINA, RNT, RLC
        email: Email destinatario
        usuario_id: ID del usuario que envió
        asunto: Asunto del correo
        adjuntos: Lista de nombres de archivos adjuntos
    """
    correo = CorreoEnviado(
        documento_id=documento_id,
        tipo_documento=tipo_documento,
        email_destinatario=email,
        enviado_por_usuario_id=usuario_id,
        asunto=asunto,
        adjuntos_enviados=adjuntos
    )
    db.session.add(correo)
    db.session.commit()

def buscar_rnt_periodo(empresa_id, periodo):
    """
    Busca el RNT correspondiente a un periodo
    
    Args:
        empresa_id: ID de la empresa
        periodo: Periodo (ej: "202412")
        
    Returns:
        dict: Datos del RNT o None
    """
    print(f"🔍 Buscando documento Seguros Sociales para empresa_id={empresa_id}, periodo={periodo}")
    
    # Buscar cualquier documento de Seguros Sociales que contenga el periodo
    doc = Documento.query.filter(
        Documento.empresa_id == empresa_id,
        Documento.categoria == DocumentCategories.SEGUROS_SOCIALES,
        Documento.nombre_archivo.like(f'%{periodo}%')
    ).first()
    
    if doc:
        print(f"✅ Documento Seguros Sociales encontrado: {doc.nombre_archivo}")
        return {
            'id': doc.id,
            'ruta_pdf': doc.ruta_archivo,
            'nombre_archivo': os.path.basename(doc.ruta_archivo),
            'importe': extraer_importe_rnt(doc),
            'fecha_cargo': extraer_fecha_cargo_rnt(doc)
        }
    
    print(f"❌ No se encontró documento Seguros Sociales con periodo {periodo}")
    return None

def extraer_importe_rnt(documento):
    """Extrae el importe del RNT del texto OCR"""
    # TODO: Implementar extracción real del importe
    # Por ahora retorna placeholder
    return "N/A"

def extraer_fecha_cargo_rnt(documento):
    """Extrae la fecha de cargo del RNT"""
    # TODO: Implementar extracción real de fecha
    # Por ahora retorna placeholder
    return "N/A"

def generar_cuerpo_email(nominas, seguros_data=None):
    """
    Genera el texto del correo electrónico (el HTML profesional se genera en email_sender)
    
    Args:
        nominas: Lista de nóminas a enviar (puede estar vacía)
        seguros_data: Lista de documentos de Seguros Sociales (RNT, RLC, etc.) o None
        
    Returns:
        str: Texto del correo
    """
    texto = f"Estimado/a cliente,\n\n"
    
    if nominas and len(nominas) > 0:
        periodo = nominas[0].get('periodo', 'N/A')
        texto += f"Adjuntamos las nóminas correspondientes al periodo {periodo}.\n\n"
    
    if seguros_data and len(seguros_data) > 0:
        if nominas and len(nominas) > 0:
            # Hay nóminas y seguros
            if len(seguros_data) == 1:
                texto += "También se incluye el documento de Seguros Sociales.\n\n"
            else:
                texto += f"También se incluyen {len(seguros_data)} documentos de Seguros Sociales.\n\n"
        else:
            # Solo seguros, sin nóminas
            if len(seguros_data) == 1:
                texto += "Adjuntamos el documento de Seguros Sociales solicitado.\n\n"
            else:
                texto += f"Adjuntamos {len(seguros_data)} documentos de Seguros Sociales.\n\n"
    
    texto += "Saludos cordiales,\n"
    texto += "Departamento de Gestión"
    
    return texto

def enviar_nominas_automatico(email_destino, nominas, rnt=None, usuario_id=None, forzar_reenvio=False):
    """
    Envía correo con nóminas y documentos de Seguros Sociales (RNT, RLC, etc.)
    
    Args:
        email_destino: Email ingresado por el usuario
        nominas: Lista de documentos de nóminas (puede estar vacía)
        rnt: Documento de Seguros Sociales (dict) o lista de documentos (list)
        usuario_id: ID del usuario que envía
        forzar_reenvio: Si True, permite reenviar aunque ya se haya enviado antes
        
    Returns:
        dict: Resultado del envío
    """
    adjuntos = []
    nominas_enviadas = []
    
    # Filtrar nóminas que no se han enviado (o todas si forzar_reenvio=True)
    if nominas:
        for nomina in nominas:
            if forzar_reenvio or not verificar_correo_enviado(nomina['id'], 'NOMINA', email_destino):
                # ✅ Verificación de existencia física
                if nomina.get('ruta_pdf') and os.path.exists(nomina['ruta_pdf']):
                    adjuntos.append({
                        'ruta': nomina['ruta_pdf'],
                        'nombre': nomina['nombre_archivo']
                    })
                    nominas_enviadas.append(nomina)
                else:
                    print(f"⚠️ Nómina no encontrada (omitida del envío): {nomina.get('ruta_pdf')}")
    
    # Agregar documentos de Seguros Sociales (RNT, RLC, etc.)
    # Puede ser un dict (compatibilidad) o una lista
    seguros_enviados = []
    if rnt:
        # Si es una lista, procesar todos
        if isinstance(rnt, list):
            print(f"📋 Analizando {len(rnt)} documentos de Seguros Sociales para adjuntar")
            for doc_seguro in rnt:
                if forzar_reenvio or not verificar_correo_enviado(doc_seguro['id'], 'SEGUROS', email_destino):
                    if doc_seguro.get('ruta_pdf') and os.path.exists(doc_seguro['ruta_pdf']):
                        adjuntos.append({
                            'ruta': doc_seguro['ruta_pdf'],
                            'nombre': doc_seguro['nombre_archivo']
                        })
                        seguros_enviados.append(doc_seguro)
                        print(f"  ✅ {doc_seguro['nombre_archivo']}")
                    else:
                        print(f"  ⚠️ Documento SS no encontrado: {doc_seguro.get('ruta_pdf')}")
        # Si es un dict (compatibilidad con código antiguo)
        elif isinstance(rnt, dict):
            if forzar_reenvio or not verificar_correo_enviado(rnt['id'], 'SEGUROS', email_destino):
                if rnt.get('ruta_pdf') and os.path.exists(rnt['ruta_pdf']):
                    adjuntos.append({
                        'ruta': rnt['ruta_pdf'],
                        'nombre': rnt['nombre_archivo']
                    })
                    seguros_enviados.append(rnt)
                else:
                    print(f"⚠️ Documento SS no encontrado: {rnt.get('ruta_pdf')}")
    
    # Validar que haya al menos un documento para enviar
    if not adjuntos:
        return {
            NotificationTypes.SUCCESS: False, 
            'message': 'Todos los documentos ya fueron enviados a este correo',
            'ya_enviados': len(nominas) + (len(rnt) if isinstance(rnt, list) else (1 if rnt else 0))
        }
    
    # Generar asunto
    if nominas_enviadas:
        periodo = nominas_enviadas[0]['periodo']
        asunto = f"Nóminas {periodo}"
        if seguros_enviados:
            asunto += f" + Seguros Sociales"
        empresa_nombre = nominas_enviadas[0].get('empresa_nombre', 'Cliente')
    elif seguros_enviados:
        # Solo seguros, sin nóminas
        asunto = "Documentos de Seguros Sociales"
        # Obtener empresa del primer seguro
        empresa = Empresa.query.get(seguros_enviados[0]['empresa_id'])
        empresa_nombre = empresa.nombre if empresa else 'Cliente'
    else:
        asunto = "Documentos"
        empresa_nombre = 'Cliente'
    
    # Generar cuerpo
    cuerpo = generar_cuerpo_email(nominas_enviadas, seguros_enviados)
    
    # Enviar correo
    try:
        enviar_email_con_adjuntos(
            destinatarios=[email_destino],
            asunto=asunto,
            cuerpo=cuerpo,
            adjuntos=adjuntos,
            usar_html=True,
            empresa_nombre=empresa_nombre
        )
        
        # Marcar como enviados (solo si NO es reenvío forzado)
        if not forzar_reenvio:
            for nomina in nominas_enviadas:
                marcar_correo_enviado(
                    nomina['id'], 'NOMINA', email_destino, 
                    usuario_id, asunto, [nomina['nombre_archivo']]
                )
            
            # Marcar todos los documentos de Seguros Sociales
            for seguro in seguros_enviados:
                marcar_correo_enviado(
                    seguro['id'], 'SEGUROS', email_destino,
                    usuario_id, asunto, [seguro['nombre_archivo']]
                )
        
        return {
            NotificationTypes.SUCCESS: True,
            'enviados': len(nominas_enviadas),
            'adjuntos': len(adjuntos),
            'email': email_destino,
            'incluyo_rnt': len(seguros_enviados) > 0
        }
    except Exception as e:
        return {
            NotificationTypes.SUCCESS: False, 
            NotificationTypes.ERROR: str(e),
            'message': f'Error al enviar correo: {str(e)}'
        }
