"""
Servicio de Generación de Reportes
Genera reportes en CSV y Excel para exportación
"""
import pandas as pd
from io import BytesIO
from datetime import datetime
from models import (db, Gestoria, UsoGestoria, AlertaSistema, PlanHistorial,
                   GestoriaPlan, PlanGestoria, User, Empresa, Documento)


def generar_reporte_uso(fecha_inicio=None, fecha_fin=None, gestoria_id=None):
    """
    Genera reporte de uso de gestorías
    
    Returns:
        pandas.DataFrame con datos de uso
    """
    # Query base
    query = db.session.query(
        Gestoria.nombre.label('gestoria'),
        PlanGestoria.nombre.label('plan'),
        UsoGestoria.periodo,
        UsoGestoria.usuarios_activos,
        UsoGestoria.empresas_count,
        UsoGestoria.documentos_procesados,
        UsoGestoria.tokens_ia_usados,
        UsoGestoria.almacenamiento_usado_gb
    ).join(
        UsoGestoria, Gestoria.id == UsoGestoria.gestoria_id
    ).outerjoin(
        GestoriaPlan, Gestoria.id == GestoriaPlan.gestoria_id
    ).outerjoin(
        PlanGestoria, GestoriaPlan.plan_id == PlanGestoria.id
    )
    
    # Filtros
    if gestoria_id:
        query = query.filter(Gestoria.id == gestoria_id)
    
    if fecha_inicio:
        query = query.filter(UsoGestoria.periodo >= fecha_inicio.strftime('%Y-%m'))
    
    if fecha_fin:
        query = query.filter(UsoGestoria.periodo <= fecha_fin.strftime('%Y-%m'))
    
    # Ejecutar query
    resultados = query.all()
    
    # Convertir a DataFrame
    df = pd.DataFrame([
        {
            'Gestoría': r.gestoria,
            'Plan': r.plan or 'Sin plan',
            'Período': r.periodo,
            'Usuarios Activos': r.usuarios_activos,
            'Empresas': r.empresas_count,
            'Documentos Procesados': r.documentos_procesados,
            'Tokens IA Usados': r.tokens_ia_usados,
            'Almacenamiento (GB)': float(r.almacenamiento_usado_gb)
        }
        for r in resultados
    ])
    
    return df


def generar_reporte_alertas(fecha_inicio=None, fecha_fin=None, gestoria_id=None):
    """
    Genera reporte de alertas del sistema
    
    Returns:
        pandas.DataFrame con alertas
    """
    query = db.session.query(
        Gestoria.nombre.label('gestoria'),
        AlertaSistema.tipo,
        AlertaSistema.nivel,
        AlertaSistema.titulo,
        AlertaSistema.mensaje,
        AlertaSistema.leida,
        AlertaSistema.fecha_creacion,
        AlertaSistema.fecha_leida
    ).join(
        Gestoria, AlertaSistema.gestoria_id == Gestoria.id
    )
    
    # Filtros
    if gestoria_id:
        query = query.filter(Gestoria.id == gestoria_id)
    
    if fecha_inicio:
        query = query.filter(AlertaSistema.fecha_creacion >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(AlertaSistema.fecha_creacion <= fecha_fin)
    
    resultados = query.order_by(AlertaSistema.fecha_creacion.desc()).all()
    
    df = pd.DataFrame([
        {
            'Gestoría': r.gestoria,
            'Tipo': r.tipo,
            'Nivel': r.nivel,
            'Título': r.titulo,
            'Mensaje': r.mensaje,
            'Estado': 'Leída' if r.leida else 'No leída',
            'Fecha Creación': r.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S'),
            'Fecha Leída': r.fecha_leida.strftime('%Y-%m-%d %H:%M:%S') if r.fecha_leida else ''
        }
        for r in resultados
    ])
    
    return df


def generar_reporte_cambios_planes(fecha_inicio=None, fecha_fin=None, gestoria_id=None):
    """
    Genera reporte de cambios de planes
    
    Returns:
        pandas.DataFrame con cambios de planes
    """
    query = db.session.query(
        PlanGestoria.nombre.label('plan_nombre'),
        PlanHistorial.campo_modificado,
        PlanHistorial.valor_anterior,
        PlanHistorial.valor_nuevo,
        PlanHistorial.fecha_cambio,
        User.nombre.label('usuario_nombre')
    ).join(
        PlanGestoria, PlanHistorial.plan_id == PlanGestoria.id
    ).outerjoin(
        User, PlanHistorial.usuario_id == User.id
    )
    
    # Filtros
    if fecha_inicio:
        query = query.filter(PlanHistorial.fecha_cambio >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(PlanHistorial.fecha_cambio <= fecha_fin)
    
    resultados = query.order_by(PlanHistorial.fecha_cambio.desc()).all()
    
    df = pd.DataFrame([
        {
            'Plan': r.plan_nombre,
            'Campo Modificado': r.campo_modificado,
            'Valor Anterior': r.valor_anterior,
            'Valor Nuevo': r.valor_nuevo,
            'Fecha Cambio': r.fecha_cambio.strftime('%Y-%m-%d %H:%M:%S'),
            'Usuario': r.usuario_nombre or 'Sistema'
        }
        for r in resultados
    ])
    
    return df


def exportar_a_csv(df):
    """
    Exporta DataFrame a CSV
    
    Returns:
        BytesIO con contenido CSV
    """
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return output


def exportar_a_excel(df, nombre_hoja='Reporte'):
    """
    Exporta DataFrame a Excel
    
    Returns:
        BytesIO con contenido Excel
    """
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=nombre_hoja, index=False)
        
        # Ajustar ancho de columnas
        worksheet = writer.sheets[nombre_hoja]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output


def generar_nombre_archivo(tipo_reporte, formato, fecha_inicio=None, fecha_fin=None):
    """
    Genera nombre de archivo para el reporte
    
    Returns:
        str con nombre de archivo
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    nombre = f"reporte_{tipo_reporte}_{timestamp}"
    
    if fecha_inicio and fecha_fin:
        nombre += f"_{fecha_inicio.strftime('%Y%m')}_{fecha_fin.strftime('%Y%m')}"
    
    extension = 'csv' if formato == 'csv' else 'xlsx'
    
    return f"{nombre}.{extension}"
