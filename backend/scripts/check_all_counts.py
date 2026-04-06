# backend/scripts/check_all_counts.py
import os
import sys
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from models import Gestoria, Documento
from sqlalchemy import func
from extensions import db

with app.app_context():
    gs = Gestoria.query.all()
    for g in gs:
        print(f"--- Gestoria: {g.nombre} (ID: {g.id}) ---")
        total = Documento.query.filter_by(gestoria_id=g.id).count()
        print(f"Total documentos: {total}")
        
        cats = db.session.query(Documento.categoria, func.count(Documento.id)).filter_by(gestoria_id=g.id).group_by(Documento.categoria).all()
        for cat, count in cats:
            print(f" - {cat}: {count}")
        print("\n")
