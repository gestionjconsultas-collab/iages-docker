# backend/descargar_pdfs_saltra.py
"""
Script para descargar PDFs (documentos + vouchers) de Saltra de forma síncrona
MEJORADO: Descarga AMBOS archivos y los organiza en carpetas separadas
"""
import os
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from extensions import db
from models import Empresa, Documento
from models_saltra import NotificacionSaltra
from services.saltra_service import SaltraService

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['RUTA_RAIZ_NOTIFICACIONES'] = os.getenv(
    'RUTA_RAIZ_NOTIFICACIONES', 
    os.path.join(os.path.dirname(__file__), 'storage')
)
db.init_app(app)

def descargar_pdfs(limit=20):
    """Descarga documentos principales + resguardos de notificaciones"""
    
    with app.app_context():
        saltra = SaltraService()
        
        # Buscar notificaciones con empresa pero sin PDF
        pendientes = NotificacionSaltra.query.filter(
            NotificacionSaltra.pdf_descargado == False,
            NotificacionSaltra.empresa_id != None,
            NotificacionSaltra.error_mensaje == None
        ).limit(limit).all()
        
        print(f"📥 Encontradas {len(pendientes)} notificaciones para descargar\n")
        
        descargados = 0
        errores = 0
        
        for notif in pendientes:
            try:
                print(f"⏳ Procesando: {notif.identifier} ({notif.empresa.nombre})...")
                
                # ✅ Usar descarga optimizada (1 petición en lugar de 2)
                result = saltra.download_notification_files_optimized(notif.sent_reference)
                
                if not result['success']:
                    print(f"   ❌ No se pudo descargar ningún archivo")
                    print(f"   Errores: {', '.join(result['errors'])}")
                    notif.error_mensaje = '; '.join(result['errors'])[:500]
                    errores += 1
                    db.session.commit()
                    continue
                
                # Ruta base para la empresa (incluir gestoría)
                import re
                
                # Sanitizar nombre de gestoría y empresa
                gestoria_slug = notif.empresa.gestoria.slug  # Ya está sanitizado
                nombre_empresa_safe = re.sub(r'[^\w\s-]', '', notif.empresa.nombre).strip().replace('_', ' ')  # Mantener espacios
                
                ruta_base = os.path.join(
                    app.config['RUTA_RAIZ_NOTIFICACIONES'],
                    gestoria_slug,           # Carpeta de gestoría
                    nombre_empresa_safe,     # Carpeta de empresa (con espacios)
                    'Por Procesar'           # Documentos DEHU van a Por Procesar
                )
                
                documentos_creados = []
                
                # 1. Guardar DOCUMENTO PRINCIPAL (si existe)
                if result['document']:
                    pdf_bytes, filename = result['document']
                    
                    # Crear carpeta DEHU dentro de Por Procesar
                    ruta_doc = os.path.join(ruta_base, 'DEHU_Documentos')
                    os.makedirs(ruta_doc, exist_ok=True)
                    
                    # Nombre descriptivo con identificador
                    safe_filename = f"DOC_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                    ruta_completa = os.path.join(ruta_doc, safe_filename)
                    
                    # Evitar duplicados
                    counter = 1
                    base_name, ext = os.path.splitext(ruta_completa)
                    while os.path.exists(ruta_completa):
                        ruta_completa = f"{base_name}_{counter}{ext}"
                        counter += 1
                    
                    # Guardar PDF
                    with open(ruta_completa, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    # Crear documento en BD
                    doc = Documento(
                        empresa_id=notif.empresa_id,
                        gestoria_id=notif.gestoria_id,
                        nombre_archivo=os.path.basename(ruta_completa),
                        ruta_archivo=ruta_completa,
                        categoria='Por Procesar',  # Para que aparezca en Mesa de Trabajo
                        procesado=False,  # Requiere clasificación
                        datos_extraidos={
                            'origen': 'DEHU_SALTRA',
                            'tipo': 'Documento Principal',
                            'subcategoria': 'Documentos',
                            'identifier': notif.identifier,
                            'emisor': notif.emitter_entity,
                            'concepto': notif.concept,
                            'fecha_notificacion': notif.availability_date.isoformat() if notif.availability_date else None,
                            'estado': notif.state,
                            'sent_reference': notif.sent_reference
                        }
                    )
                    db.session.add(doc)
                    documentos_creados.append(('Documento', os.path.basename(ruta_completa)))
                    print(f"   ✅ Documento guardado: {os.path.basename(ruta_completa)}")
                
                # 2. Guardar RESGUARDO (si existe)
                if result['voucher']:
                    pdf_bytes, filename = result['voucher']
                    
                    # Crear carpeta DEHU dentro de Por Procesar
                    ruta_resg = os.path.join(ruta_base, 'DEHU_Resguardos')
                    os.makedirs(ruta_resg, exist_ok=True)
                    
                    # Nombre descriptivo con identificador
                    safe_filename = f"RESG_{notif.identifier}_{filename}".replace('/', '_').replace('\\', '_')
                    ruta_completa = os.path.join(ruta_resg, safe_filename)
                    
                    # Evitar duplicados
                    counter = 1
                    base_name, ext = os.path.splitext(ruta_completa)
                    while os.path.exists(ruta_completa):
                        ruta_completa = f"{base_name}_{counter}{ext}"
                        counter += 1
                    
                    # Guardar PDF
                    with open(ruta_completa, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    # Crear documento en BD
                    doc = Documento(
                        empresa_id=notif.empresa_id,
                        gestoria_id=notif.gestoria_id,
                        nombre_archivo=os.path.basename(ruta_completa),
                        ruta_archivo=ruta_completa,
                        categoria='Por Procesar',  # Para que aparezca en Mesa de Trabajo
                        procesado=True,  # Resguardos no requieren clasificación
                        datos_extraidos={
                            'origen': 'DEHU_SALTRA',
                            'tipo': 'Resguardo',
                            'subcategoria': 'Resguardos',
                            'identifier': notif.identifier,
                            'emisor': notif.emitter_entity,
                            'concepto': notif.concept,
                            'sent_reference': notif.sent_reference
                        }
                    )
                    db.session.add(doc)
                    documentos_creados.append(('Resguardo', os.path.basename(ruta_completa)))
                    print(f"   ✅ Resguardo guardado: {os.path.basename(ruta_completa)}")
                
                # Vincular primer documento a la notificación
                db.session.flush()
                if documentos_creados:
                    # Buscar el primer documento creado para vincular
                    primer_doc = db.session.query(Documento).filter_by(
                        empresa_id=notif.empresa_id,
                        categoria='Por Procesar'
                    ).order_by(Documento.id.desc()).first()
                    
                    if primer_doc:
                        notif.documento_id = primer_doc.id
                
                # Marcar como descargado
                notif.pdf_descargado = True
                notif.procesado = True
                notif.error_mensaje = None
                
                db.session.commit()
                
                print(f"   📦 Total archivos: {len(documentos_creados)}")
                descargados += 1
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                notif.error_mensaje = str(e)[:500]
                db.session.commit()
                errores += 1
        
        print(f"\n{'='*60}")
        print(f"✅ DESCARGA COMPLETADA")
        print(f"   Notificaciones procesadas: {descargados}")
        print(f"   Errores: {errores}")
        print(f"   Pendientes: {len(pendientes) - descargados - errores}")
        print(f"{'='*60}")


if __name__ == '__main__':
    descargar_pdfs(limit=50)