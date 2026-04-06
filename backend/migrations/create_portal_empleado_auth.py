"""
Migración: Crear tabla portal_empleado_auth
Ejecutar: python migrations/create_portal_empleado_auth.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app
from extensions import db


def run():
    with app.app_context():
        sql = """
        CREATE TABLE IF NOT EXISTS portal_empleado_auth (
            id                SERIAL PRIMARY KEY,
            empleado_id       INTEGER UNIQUE NOT NULL
                                REFERENCES empleados(id) ON DELETE CASCADE,
            email             VARCHAR(150) UNIQUE NOT NULL,
            password_hash     VARCHAR(256),
            activo            BOOLEAN NOT NULL DEFAULT FALSE,
            token_activacion  VARCHAR(100),
            token_expiry      TIMESTAMP,
            ultimo_acceso     TIMESTAMP,
            created_at        TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_portal_empleado_auth_empleado_id
            ON portal_empleado_auth(empleado_id);
        CREATE INDEX IF NOT EXISTS ix_portal_empleado_auth_email
            ON portal_empleado_auth(email);
        """
        db.session.execute(db.text(sql))
        db.session.commit()
        print("✅ Tabla portal_empleado_auth creada correctamente")


if __name__ == '__main__':
    run()
