#!/usr/bin/env python3
"""
Utilidad para dividir PDFs grandes en archivos más pequeños
Uso: python split_pdf.py <archivo.pdf> --pages-per-file 500
"""

import sys
import os
from PyPDF2 import PdfReader, PdfWriter
import argparse

def split_pdf(input_path, pages_per_file=500, output_dir=None):
    """
    Divide un PDF grande en archivos más pequeños
    
    Args:
        input_path: Ruta al PDF original
        pages_per_file: Número de páginas por archivo (default: 500)
        output_dir: Directorio de salida (default: mismo directorio que input)
    
    Returns:
        Lista de archivos creados
    """
    # Validar que el archivo existe
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Archivo no encontrado: {input_path}")
    
    # Determinar directorio de salida
    if output_dir is None:
        output_dir = os.path.dirname(input_path) or '.'
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Leer PDF
    print(f"📄 Leyendo PDF: {input_path}")
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    
    print(f"📊 Total de páginas: {total_pages}")
    print(f"✂️  Dividiendo en archivos de {pages_per_file} páginas...")
    
    # Obtener nombre base del archivo
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # Dividir en partes
    created_files = []
    num_parts = (total_pages + pages_per_file - 1) // pages_per_file
    
    for part_num in range(num_parts):
        start_page = part_num * pages_per_file
        end_page = min((part_num + 1) * pages_per_file, total_pages)
        
        # Crear writer para esta parte
        writer = PdfWriter()
        
        # Agregar páginas
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])
        
        # Guardar archivo
        output_filename = f"{base_name}_parte{part_num + 1}_pag{start_page + 1}-{end_page}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"✅ Parte {part_num + 1}/{num_parts}: {output_filename} ({end_page - start_page} páginas, {file_size:.1f} MB)")
        
        created_files.append(output_path)
    
    print(f"\n🎉 ¡Listo! Se crearon {len(created_files)} archivos")
    print(f"📁 Ubicación: {output_dir}")
    
    return created_files

def main():
    parser = argparse.ArgumentParser(
        description='Divide un PDF grande en archivos más pequeños',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python split_pdf.py NOMINAS_202511.pdf
  python split_pdf.py NOMINAS_202511.pdf --pages-per-file 1000
  python split_pdf.py NOMINAS_202511.pdf --pages-per-file 500 --output-dir ./partes
        """
    )
    
    parser.add_argument('input_file', help='Archivo PDF a dividir')
    parser.add_argument('--pages-per-file', '-p', type=int, default=500,
                        help='Número de páginas por archivo (default: 500)')
    parser.add_argument('--output-dir', '-o', type=str, default=None,
                        help='Directorio de salida (default: mismo que input)')
    
    args = parser.parse_args()
    
    try:
        created_files = split_pdf(
            args.input_file,
            pages_per_file=args.pages_per_file,
            output_dir=args.output_dir
        )
        
        print("\n📋 Archivos creados:")
        for i, file_path in enumerate(created_files, 1):
            print(f"  {i}. {os.path.basename(file_path)}")
        
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
