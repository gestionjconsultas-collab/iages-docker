#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: Encriptar campos sensibles en BD (IBAN, SWIFT, banco + Saltra)
==========================================================================

INSTRUCCIONES DE EJECUCIÓN:
    cd backend
    python migrations/migrate_encrypt_sensitive_fields.py

Qué hace este script:
    1. Amplía las columnas iban/swift/banco a VARCHAR(500) para aceptar texto cifrado
    2. Encripta los valores existentes en texto plano
    3. Encripta las credenciales Saltra existentes en Gestoria.configuracion

IMPORTANTE:
    - Ejecutar en producción con la BD detenida o en modo mantenimiento
    - Hacer backup ANTES de ejecutar
    - Requiere que FIELD_ENCRYPTION_KEY o TOTP_ENCRYPTION_KEY esté en el entorno
"""

import sys
import os

# Ajustar path para importar desde el backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from utils.encryption_utils import encrypt_field, decrypt_field

def run_migration():
    app = create_app()
    with app.app_context():
        print("=== Migración: Encriptación de campos sensibles ===\n")

        # ── 1. Ampliar columnas en empresa_emisora ────────────────────────────
        print("[1/3] Ampliando columnas VARCHAR en empresa_emisora...")
        try:
            with db.engine.connect() as conn:
                # PostgreSQL
                for col in ['iban', 'swift', 'banco']:
                    conn.execute(db.text(
                        f"ALTER TABLE empresa_emisora ALTER COLUMN {col} TYPE VARCHAR(500)"
                    ))
                conn.commit()
            print("    ✅ Columnas ampliadas a VARCHAR(500)")
        except Exception as e:
            print(f"    ⚠️  Error al ampliar columnas (pueden ya ser suficientemente grandes): {e}")

        # ── 2. Encriptar IBAN/SWIFT/banco existentes ──────────────────────────
        print("\n[2/3] Encriptando datos bancarios en empresa_emisora...")
        from models_billing import EmpresaEmisora
        emisoras = EmpresaEmisora.query.all()
        for e in emisoras:
            changed = False
            for field in ['iban', 'swift', 'banco']:
                val = getattr(e, field)
                if val and not val.startswith('enc:'):
                    setattr(e, field, encrypt_field(val))
                    changed = True
            if changed:
                print(f"    → EmpresaEmisora id={e.id} encriptada")

        db.session.commit()
        print("    ✅ Datos bancarios encriptados")

        # ── 3. Encriptar credenciales Saltra en Gestoria.configuracion ─────────
        print("\n[3/3] Encriptando credenciales Saltra en gestorías...")
        from models import Gestoria
        gestorias = Gestoria.query.all()
        updated = 0
        for g in gestorias:
            config = g.configuracion or {}
            saltra = config.get('saltra', {})
            if not saltra:
                continue

            needs_update = False
            new_saltra = dict(saltra)
            for field in ['email', 'password', 'cert_secret']:
                val = saltra.get(field)
                if val and not str(val).startswith('enc:'):
                    new_saltra[field] = encrypt_field(val)
                    needs_update = True

            if needs_update:
                new_config = dict(config)
                new_config['saltra'] = new_saltra
                g.configuracion = new_config
                updated += 1
                print(f"    → Gestoría id={g.id} ({g.nombre}) Saltra encriptada")

        db.session.commit()
        print(f"    ✅ {updated} gestoría(s) con credenciales Saltra encriptadas")

        print("\n=== Migración completada con éxito ===")


if __name__ == '__main__':
    run_migration()
