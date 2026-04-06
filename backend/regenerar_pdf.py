from app import app
from utils.pdf_invoice_generator import generar_pdf_factura
from models_billing import Factura

with app.app_context():
    # Buscar la última factura
    factura = Factura.query.order_by(Factura.id.desc()).first()
    
    if factura:
        print(f"📄 Regenerando PDF para factura: {factura.numero_factura}")
        print(f"   - Gestoría ID: {factura.gestoria_id}")
        print(f"   - Total: €{factura.total}")
        
        # Regenerar PDF con nuevo diseño
        pdf_path = generar_pdf_factura(factura.id)
        
        print(f"\n✅ PDF regenerado con nuevo diseño!")
        print(f"   - Ubicación: {pdf_path}")
        print(f"\n🎨 Mejoras aplicadas:")
        print(f"   ✓ Logo IAGES en encabezado")
        print(f"   ✓ Colores corporativos (naranja/gris)")
        print(f"   ✓ Diseño moderno y profesional")
        print(f"   ✓ Línea decorativa superior")
        print(f"   ✓ Numeración de páginas")
        print(f"   ✓ Tablas con fondos alternados")
        print(f"   ✓ Total destacado en naranja")
        print(f"\n📥 Descarga el PDF desde la interfaz para verlo!")
    else:
        print("❌ No se encontraron facturas")
