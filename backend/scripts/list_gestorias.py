# backend/scripts/list_gestorias.py
import os
import sys
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

from app import app
from models import Gestoria

with app.app_context():
    gs = Gestoria.query.all()
    print("Gestorías en el sistema:")
    for g in gs:
        print(f"ID: {g.id} | Nombre: {g.nombre} | Slug: {g.slug}")
