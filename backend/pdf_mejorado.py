# Mejora del PDF - Reemplazar la función export_reporte_pdf en export_service.py

@staticmethod
def export_reporte_pdf(filters):
    """
    Genera reporte PDF profesional mejorado
    
    Args:
        filters: dict con filtros
        
    Returns:
        tuple: (bytes del PDF, nombre del archivo)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak
    from reportlab.lib.styles import ParagraphStyle
    
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, 
        pagesize=landscape(A4),
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos personalizados
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=20,
        alignment=1
    )
    
    elements = []
    
    # Header con estilo
    title = Paragraph("<b>IAGES</b> - Reporte de Documentos", title_style)
    elements.append(title)
    
    # Fecha de generación
    fecha_gen = Paragraph(
        f"Generado el {datetime.now().strftime('%d de %B de %Y a las %H:%M')}", 
        subtitle_style
    )
    elements.append(fecha_gen)
    elements.append(Spacer(1, 0.5*cm))
    
    # Query de documentos
    query = db.session.query(Documento, Empresa).join(Empresa)
    
    # Aplicar filtros
    if filters.get('empresa_ids') and len(filters['empresa_ids']) > 0:
        query = query.filter(Documento.empresa_id.in_(filters['empresa_ids']))
    if filters.get('fecha_desde'):
        query = query.filter(Documento.fecha_creacion >= filters['fecha_desde'])
    if filters.get('fecha_hasta'):
        query = query.filter(Documento.fecha_creacion <= filters['fecha_hasta'])
    if filters.get('categorias') and len(filters['categorias']) > 0:
        query = query.filter(Documento.categoria.in_(filters['categorias']))
    
    # Obtener documentos
    documentos = query.all()
    total_docs = len(documentos)
    
    # Calcular total de importes
    total_importe = sum(
        float(doc.importe or doc.importe_pagar or 0) 
        for doc, _ in documentos 
        if (doc.importe or doc.importe_pagar)
    )
    
    # Resumen con estilo
    resumen_data = [
        ['Total de Documentos', str(total_docs)],
        ['Total Importes', f"{total_importe:,.2f}€"]
    ]
    
    resumen_table = Table(resumen_data, colWidths=[5*cm, 4*cm])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3b82f6')),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#eff6ff')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1e40af')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
    ]))
    
    elements.append(resumen_table)
    elements.append(Spacer(1, 1*cm))
    
    if total_docs == 0:
        no_data = Paragraph(
            "<i>No se encontraron documentos con los filtros aplicados.</i>", 
            styles['Normal']
        )
        elements.append(no_data)
    else:
        # Tabla de documentos con mejor diseño
        data = [['Empresa', 'Categoría', 'Fecha', 'Importe (€)']]
        
        for documento, empresa in documentos:
            importe_val = float(documento.importe or documento.importe_pagar or 0)
            data.append([
                Paragraph(empresa.nombre[:40] if empresa.nombre else 'N/A', styles['Normal']),
                documento.categoria or 'Sin categoría',
                documento.fecha_creacion.strftime('%d/%m/%Y') if documento.fecha_creacion else 'N/A',
                f"{importe_val:,.2f}" if importe_val > 0 else '-'
            ])
        
        # Ajustar anchos de columna
        col_widths = [8*cm, 5*cm, 3*cm, 3*cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 14),
            ('TOPPADDING', (0, 0), (-1, 0), 14),
            
            # Body
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 1), (-1, -1), 8),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#1e40af')),
        ]))
        
        elements.append(table)
    
    # Construir PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    # Nombre del archivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Reporte_IAGES_{timestamp}.pdf"
    
    return pdf_buffer.getvalue(), filename
