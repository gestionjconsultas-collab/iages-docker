import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from sqlalchemy import text

def add_is_soporte_column():
    """Añade la columna is_soporte a la tabla users"""
    with app.app_context():
        try:
            db.session.execute(text(
                "ALTER TABLE users ADD COLUMN is_soporte BOOLEAN NOT NULL DEFAULT FALSE;"
            ))
            db.session.commit()
            print("✅ Columna 'is_soporte' añadida correctamente a 'users'")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower() or "duplicada" in str(e).lower() or "duplicate" in str(e).lower():
                print("ℹ️  La columna 'is_soporte' ya existe — no se requiere acción.")
            else:
                print(f"❌ Error: {e}")

if __name__ == '__main__':
    add_is_soporte_column()
