from app import create_app
from extensions import db
from models import Documento, Empresa, GrupoDocumentos, GrupoDocumentosItem
from constants import DocumentCategories
from services.procesar_altas import procesar_altas
from utils.document_utils import auto_group_altas
import os
import shutil

def process():
    app = create_app('production')
    with app.app_context():
        # RINKO INSTALACIONES is empresa_id=77 (found from IDC extraction)
        empresa = Empresa.query.get(77)
        if not empresa:
            empresa = Empresa.query.first()
        if not empresa:
            print("❌ No hay empresas en la BD.")
            return

        print(f"🏢 Usando empresa: {empresa.nombre} (ID={empresa.id})")

        files = [
            "TA_MOUSSA.pdf",
            "IDC_626309.pdf"
        ]
        
        storage_root = "/var/www/iages/notificaciones/altas_bajas"
        os.makedirs(storage_root, exist_ok=True)

        doc_ids = []
        
        for filename in files:
            source = os.path.join("/var/www/iages/backend", filename)
            dest = os.path.join(storage_root, filename)
            
            if not os.path.exists(source):
                print(f"❌ No existe: {source}")
                continue

            shutil.copy2(source, dest)
            print(f"📄 Procesando {filename}...")
            
            resultados = procesar_altas(dest, storage_root, gestoria_id=empresa.gestoria_id)
            if resultados:
                res = resultados[0]
                cat_str = res.get('categoria_final', 'Bajas de Trabajadores')
                # Resolve to constant
                if 'baja' in cat_str.lower():
                    cat = DocumentCategories.BAJAS_TRABAJADORES
                else:
                    cat = DocumentCategories.ALTAS_TRABAJADORES

                print(f"   → Categoría detectada: {cat_str} (is_baja={res.get('is_baja')})")
                print(f"   → NIF: {res.get('nif_trabajador')}, Fecha: {res.get('fecha_movimiento')}")
                
                # Check if already exists by filename+empresa
                exist = Documento.query.filter_by(nombre_archivo=filename, empresa_id=empresa.id).first()
                if exist:
                    print(f"   ⚠️  Ya existía (ID={exist.id}), actualizando categoría...")
                    exist.categoria = cat
                    exist.datos_extraidos = res
                    db.session.commit()
                    doc = exist
                else:
                    doc = Documento(
                        nombre_archivo=filename,
                        ruta_archivo=dest,
                        empresa_id=empresa.id,
                        gestoria_id=empresa.gestoria_id,
                        categoria=cat,
                        procesado=True,
                        datos_extraidos=res
                    )
                    db.session.add(doc)
                    db.session.commit()
                    print(f"   ✅ Guardado (ID={doc.id})")
                
                doc_ids.append(doc.id)
            else:
                print(f"   ❌ procesar_altas no devolvió resultados para {filename}")

        print(f"\n📦 IDs procesados: {doc_ids}")
        print("🔗 Intentando agrupación...")
        
        for doc_id in doc_ids:
            resultado = auto_group_altas(doc_id, empresa.gestoria_id)
            if resultado:
                print(f"   ✅ Doc {doc_id} → grupo '{resultado.nombre}' (ID={resultado.id})")
            else:
                doc = db.session.get(Documento, doc_id)
                datos = doc.datos_extraidos or {}
                print(f"   ❌ Doc {doc_id} no agrupado. NIF={datos.get('nif_trabajador')}, Fecha={datos.get('fecha_movimiento')}, Cat={doc.categoria}")
        
        print("\n🔍 Grupos de Bajas en BD:")
        bajas_grupos = GrupoDocumentos.query.filter(GrupoDocumentos.nombre.ilike("Baja - %")).all()
        for g in bajas_grupos:
            items = GrupoDocumentosItem.query.filter_by(grupo_id=g.id).all()
            print(f"   📂 {g.nombre} ({len(items)} docs)")

if __name__ == "__main__":
    process()
