import os
import sys

# Agregar el directorio actual al sys.path para poder importar modulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import Documento
from constants import DocumentCategories
from services.procesar_finiquitos import procesar_finiquitos

def reprocesar():
    app = create_app('production')
    with app.app_context():
        # Obtener todos los documentos de Finiquitos
        finiquitos = Documento.query.filter_by(categoria=DocumentCategories.FINIQUITOS).all()
        print(f"Encontrados {len(finiquitos)} finiquitos para reprocesar.")
        
        for doc in finiquitos:
            print(f"Reprocesando documento ID {doc.id} - {doc.nombre_archivo}...")
            if not doc.ruta_archivo or not os.path.exists(doc.ruta_archivo):
                print(f"  [ERROR] Archivo no encontrado en {doc.ruta_archivo}")
                continue
                
            # Llamamos a procesar_finiquitos con el archivo fisico
            resultados = procesar_finiquitos(doc.ruta_archivo, gestoria_id=doc.gestoria_id, app_context=app.app_context())
            
            if resultados and len(resultados) > 0:
                res = resultados[0]
                doc.datos_extraidos = res
                doc.procesado = True
                print(f"  [EXITO] Trabajador: {res.get('nombre_trabajador')} - Empresa: {res.get('nombre_empresa')}")
            else:
                print(f"  [AVISO] No se obtuvieron resultados para el doc ID {doc.id}")
                
        db.session.commit()
        print("Proceso finalizado y cambios guardados en DB.")

if __name__ == '__main__':
    reprocesar()
