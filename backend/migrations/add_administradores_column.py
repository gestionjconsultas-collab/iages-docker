import os
import sys

# Agregar el directorio raíz al path para poder importar la aplicación
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db
from sqlalchemy import text

def add_administradores_column():
    """Añade la columna administradores a la tabla empresas"""
    with app.app_context():
        # Ejecutar SQL directo
        try:
            db.session.execute(text("ALTER TABLE empresas ADD COLUMN administradores JSON DEFAULT '[]';"))
            db.session.commit()
            print("✅ Columna 'administradores' añadida correctamente a 'empresas'")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower() or "duplicada" in str(e).lower():
                print("ℹ️ La columna 'administradores' ya existe.")
            else:
                print(f"❌ Error al añadir la columna: {e}")

if __name__ == '__main__':
    add_administradores_column()
