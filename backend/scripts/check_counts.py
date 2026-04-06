# backend/scripts/check_counts.py
import os
import sys
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from models import Gestoria, Documento
from extensions import db

with app.app_context():
    g = Gestoria.query.filter(Gestoria.nombre.ilike('%Jurisconsultas%')).first()
    if g:
        print(f"Gestoria ID: {g.id}")
        count = Documento.query.filter_by(gestoria_id=g.id, categoria='Impuestos').count()
        print(f"Count Impuestos: {count}")
        
        # También contar el total de la gestoría
        total = Documento.query.filter_by(gestoria_id=g.id).count()
        print(f"Total Documentos Gestoria: {total}")
        
        # Ver categorías existentes
        from sqlalchemy import func
        cats = db.session.query(Documento.categoria, func.count(Documento.id)).filter_by(gestoria_id=g.id).group_by(Documento.categoria).all()
        print("Categorías encontradas:")
        for cat, c_count in cats:
            print(f" - {cat}: {c_count}")
    else:
        print("Gestoria 'Jurisconsultas' no encontrada.")
