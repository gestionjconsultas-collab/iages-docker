# backend/utils/pdf_invoice_generator.py
"""
Generador de PDFs de facturas con cumplimiento legal español
Versión mejorada con diseño profesional y branding IAGES
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from models_billing import Factura, EmpresaEmisora
from models import Gestoria
from datetime import datetime
import os

# Colores corporativos IAGES
COLOR_PRIMARIO = colors.HexColor('#f97316')  # Naranja
COLOR_SECUNDARIO = colors.HexColor('#111827')  # Gris oscuro
COLOR_FONDO = colors.HexColor('#f9fafb')  # Gris claro
COLOR_BORDE = colors.HexColor('#e5e7eb')  # Gris borde

class NumberedCanvas(canvas.Canvas):
    """Canvas personalizado con encabezado y pie de página"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        """Dibuja decoraciones en cada página"""
        # Línea superior naranja
        self.setStrokeColor(COLOR_PRIMARIO)
        self.setLineWidth(3)
        self.line(2*cm, A4[1] - 2*cm, A4[0] - 2*cm, A4[1] - 2*cm)
        
        # Pie de página
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#6b7280'))
        page_num = f"Página {self._pageNumber} de {page_count}"
        self.drawCentredString(A4[0]/2, 1.5*cm, page_num)

def generar_pdf_factura(factura_id):
    """
    Genera PDF de una factura con diseño profesional y branding IAGES
    
    Args:
        factura_id: ID de la factura
    
    Returns:
        str: Ruta del PDF generado
    """
    factura = Factura.query.get(factura_id)
    if not factura:
        raise ValueError(f"Factura {factura_id} no encontrada")
    
    gestoria = Gestoria.query.get(factura.gestoria_id)
    empresa_emisora = EmpresaEmisora.get_datos_iages()
    
    if not empresa_emisora:
        raise ValueError("Datos de empresa emisora no configurados")
    
    # Crear directorio para facturas si no existe
    facturas_dir = os.path.join('uploads', 'facturas')
    os.makedirs(facturas_dir, exist_ok=True)
    
    # Nombre del archivo
    filename = f"{factura.numero_factura}.pdf"
    filepath = os.path.join(facturas_dir, filename)
    
    # Crear PDF con canvas personalizado
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=2*cm,
        bottomMargin=1.5*cm
    )
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo para logo/título
    logo_style = ParagraphStyle(
        'LogoStyle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=COLOR_PRIMARIO,
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        letterSpacing=2
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_SECUNDARIO,
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=COLOR_PRIMARIO,
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=COLOR_SECUNDARIO,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        borderPadding=5,
        leftIndent=0
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_SECUNDARIO,
        fontName='Helvetica'
    )
    
    # ==========================================
    # ENCABEZADO ESTILO ANTHROPIC
    # ==========================================
    # Intentar cargar logo
    logo_path = os.path.join('..', 'frontend', 'public', 'logo-light.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend', 'public', 'logo-light.png')
    
    # Estilo para título FACTURA
    factura_title_style = ParagraphStyle(
        'FacturaTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=COLOR_SECUNDARIO,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
        spaceAfter=2
    )
    
    # Estilo para datos de factura pequeños
    factura_info_style = ParagraphStyle(
        'FacturaInfo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=COLOR_PRIMARIO,
        alignment=TA_LEFT,
        fontName='Helvetica'
    )
    
    # Crear contenido izquierdo: Título + Info de factura
    left_content = f"""<b>Factura</b><br/>
<font color="#f97316"><b>Número:</b> {factura.numero_factura}</font><br/>
<font color="#f97316"><b>Fecha:</b> {factura.fecha_emision.strftime('%d/%m/%Y')}</font><br/>
<font color="#f97316"><b>Vencimiento:</b> {factura.fecha_vencimiento.strftime('%d/%m/%Y')}</font>"""
    
    left_paragraph = Paragraph(left_content, ParagraphStyle(
        'LeftHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_SECUNDARIO,
        alignment=TA_LEFT,
        leading=14
    ))
    
    # Crear título grande separado
    titulo_factura = Paragraph("<b>Factura</b>", factura_title_style)
    
    # Info debajo del título
    info_header = f"""<font color="#f97316"><b>Número</b>  {factura.numero_factura}</font><br/>
<font color="#f97316"><b>Fecha</b>  {factura.fecha_emision.strftime('%B %d, %Y')}</font><br/>
<font color="#f97316"><b>Vence</b>  {factura.fecha_vencimiento.strftime('%B %d, %Y')}</font>"""
    
    info_paragraph = Paragraph(info_header, ParagraphStyle(
        'InfoHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_PRIMARIO,
        alignment=TA_LEFT,
        leading=15
    ))
    
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=9*cm, height=4*cm, kind='proportional')
    else:
        logo_img = Paragraph("<b>IAGES</b>", ParagraphStyle('LogoFallback', fontSize=24, textColor=COLOR_PRIMARIO, fontName='Helvetica-Bold'))
    
    # Tabla encabezado: Título izq + Logo der
    header_data = [
        [titulo_factura, logo_img],
        [info_paragraph, '']
    ]
    header_table = Table(header_data, colWidths=[12*cm, 6*cm])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (1, 0), (1, 1)),  # Logo ocupa 2 filas
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))
    
    # ==========================================
    # DATOS DEL EMISOR Y RECEPTOR (estilo Anthropic)
    # ==========================================
    emisor_text = f"""<b>{empresa_emisora.nombre}</b><br/>
{empresa_emisora.direccion}<br/>
{empresa_emisora.codigo_postal} {empresa_emisora.ciudad}<br/>
{empresa_emisora.email}<br/>
CIF: {empresa_emisora.cif}"""
    
    receptor_text = f"""<b>Facturar a</b><br/>
<b>{gestoria.nombre}</b><br/>
{gestoria.direccion or 'N/A'}<br/>
{gestoria.email}<br/>
CIF: {gestoria.cif or 'N/A'}"""
    
    datos_tabla = [[
        Paragraph(emisor_text, normal_style),
        Paragraph(receptor_text, normal_style)
    ]]
    
    datos_table = Table(datos_tabla, colWidths=[9*cm, 9*cm])
    datos_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_SECUNDARIO),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(datos_table)
    story.append(Spacer(1, 0.5*cm))
    
    # ==========================================
    # CONCEPTO
    # ==========================================
    story.append(Paragraph("<b>CONCEPTO</b>", heading_style))
    story.append(Paragraph(factura.concepto, normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # LÍNEAS DE FACTURA
    # ==========================================
    lineas_data = [[
        Paragraph('<b>Descripción</b>', normal_style),
        Paragraph('<b>Cantidad</b>', normal_style),
        Paragraph('<b>Precio Unit.</b>', normal_style),
        Paragraph('<b>Subtotal</b>', normal_style)
    ]]
    
    if factura.lineas:
        for linea in factura.lineas:
            lineas_data.append([
                Paragraph(linea.get('descripcion', ''), normal_style),
                Paragraph(str(linea.get('cantidad', 1)), normal_style),
                Paragraph(f"{linea.get('precio_unitario', 0):.2f}€", normal_style),
                Paragraph(f"{linea.get('subtotal', 0):.2f}€", normal_style)
            ])
    else:
        lineas_data.append([
            Paragraph(factura.concepto, normal_style),
            Paragraph('1', normal_style),
            Paragraph(f"{factura.subtotal:.2f}€", normal_style),
            Paragraph(f"{factura.subtotal:.2f}€", normal_style)
        ])
    
    lineas_table = Table(lineas_data, colWidths=[9*cm, 2.5*cm, 2.75*cm, 2.75*cm])
    lineas_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Contenido
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_FONDO]),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDE)
    ]))
    
    story.append(lineas_table)
    story.append(Spacer(1, 0.5*cm))
    
    # ==========================================
    # TOTALES
    # ==========================================
    totales_data = [
        ['', Paragraph('Subtotal:', normal_style), Paragraph(f"{factura.subtotal:.2f}€", normal_style)],
        ['', Paragraph(f'IVA ({factura.iva_porcentaje}%):', normal_style), Paragraph(f"{factura.iva_importe:.2f}€", normal_style)],
    ]
    
    totales_table = Table(totales_data, colWidths=[9*cm, 5.25*cm, 2.75*cm])
    totales_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (0, 0), (-1, -1), COLOR_SECUNDARIO),
    ]))
    
    story.append(totales_table)
    
    # Total destacado
    total_data = [['', Paragraph('<b>TOTAL:</b>', normal_style), Paragraph(f'<b>{factura.total:.2f}€</b>', normal_style)]]
    total_table = Table(total_data, colWidths=[9*cm, 5.25*cm, 2.75*cm])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (-1, 0), COLOR_PRIMARIO),
        ('TEXTCOLOR', (1, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('FONTNAME', (1, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 0), (-1, 0), 14),
        ('TOPPADDING', (1, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (1, 0), (-1, 0), 12),
        ('LEFTPADDING', (1, 0), (-1, 0), 15),
        ('RIGHTPADDING', (1, 0), (-1, 0), 15),
    ]))
    
    story.append(total_table)
    story.append(Spacer(1, 0.4*cm))
    
    # ==========================================
    # DATOS BANCARIOS
    # ==========================================
    story.append(Paragraph("<b>DATOS PARA TRANSFERENCIA BANCARIA</b>", heading_style))
    
    datos_bancarios_text = f"""
<b>Titular:</b> {empresa_emisora.nombre}<br/>
<b>IBAN:</b> {empresa_emisora.iban or 'Pendiente de configurar'}<br/>
<b>SWIFT/BIC:</b> {empresa_emisora.swift or 'N/A'}<br/>
<b>Banco:</b> {empresa_emisora.banco or 'N/A'}<br/>
<b>Concepto:</b> {factura.numero_factura}
    """
    
    bancarios_data = [[Paragraph(datos_bancarios_text, normal_style)]]
    bancarios_table = Table(bancarios_data, colWidths=[17*cm])
    bancarios_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_FONDO),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 1, COLOR_BORDE)
    ]))
    
    story.append(bancarios_table)
    story.append(Spacer(1, 0.3*cm))
    
    # ==========================================
    # NOTAS
    # ==========================================
    if factura.notas:
        story.append(Paragraph("<b>NOTAS</b>", heading_style))
        story.append(Paragraph(factura.notas, normal_style))
        story.append(Spacer(1, 0.5*cm))
    
    # ==========================================
    # PIE DE PÁGINA
    # ==========================================
    pie_style = ParagraphStyle(
        'Pie',
        parent=normal_style,
        fontSize=8,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )
    
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"<b>Factura generada el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</b><br/>"
        f"Esta factura debe conservarse durante 4 años según la normativa española",
        pie_style
    ))
    
    # Construir PDF con canvas personalizado
    doc.build(story, canvasmaker=NumberedCanvas)
    
    return filepath
