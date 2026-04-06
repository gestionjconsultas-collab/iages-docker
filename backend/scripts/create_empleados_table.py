import os
import sys

# Añadir el directorio `backend/` al sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app import create_app
from extensions import db

def create_table():
    app = create_app('production')
    with app.app_context():
        try:
            from models import Empleado
            # Crear la tabla solo si no existe
            Empleado.__table__.create(db.engine, checkfirst=True)
            print("✅ Tabla 'empleados' verificada/creada con éxito.")
        except Exception as e:
            print(f"❌ Error al crear la tabla: {e}")

if __name__ == "__main__":
    create_table()
