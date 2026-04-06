#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migración: Encriptar backup_codes 2FA en BD
============================================

INSTRUCCIONES DE EJECUCIÓN:
    cd backend
    python migrations/migrate_encrypt_backup_codes.py

Qué hace este script:
    1. Amplía la columna backup_codes a TEXT(500) para aceptar JSON encriptado
    2. Encripta los backup_codes existentes (actualmente en JSON plano)

IMPORTANTE:
    - Ejecutar DESPUÉS de desplegar el código nuevo (models.py con Text(500))
    - Hacer backup ANTES de ejecutar
    - Requiere que FIELD_ENCRYPTION_KEY o TOTP_ENCRYPTION_KEY esté en el entorno
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from utils.encryption_utils import encrypt_field


def run_migration():
    app = create_app()
    with app.app_context():
        print("=== Migración: Encriptación de backup_codes 2FA ===\n")

        # ── 1. Cambiar tipo de columna ────────────────────────────────────────────
        print("[1/2] Modificando columna backup_codes a TEXT en tabla users...")
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text(
                    "ALTER TABLE users ALTER COLUMN backup_codes TYPE TEXT USING backup_codes::TEXT"
                ))
                conn.commit()
            print("    ✅ Columna backup_codes cambiada a TEXT")
        except Exception as e:
            print(f"    ⚠️  Error al cambiar columna (puede que ya sea TEXT): {e}")

        # ── 2. Encriptar backup_codes existentes ──────────────────────────────────
        print("\n[2/2] Encriptando backup_codes existentes...")
        from models import User

        usuarios = User.query.filter(User.backup_codes.isnot(None)).all()
        actualizados = 0
        errores = 0

        for u in usuarios:
            raw = u.backup_codes
            if not raw:
                continue

            # Si ya está encriptado (tiene prefijo enc:), saltar
            if raw.startswith('enc:'):
                continue

            # Intentar parsear como JSON (formato actual: lista de strings)
            try:
                codes = json.loads(raw)
                if not isinstance(codes, list):
                    print(f"    ⚠️  User id={u.id}: backup_codes no es una lista, omitiendo")
                    continue
                u.backup_codes = encrypt_field(json.dumps(codes))
                actualizados += 1
                print(f"    → User id={u.id} ({u.email}): {len(codes)} código(s) encriptados")
            except Exception as e:
                print(f"    ❌ User id={u.id}: error al procesar — {e}")
                errores += 1

        db.session.commit()
        print(f"\n    ✅ {actualizados} usuario(s) con backup_codes encriptados")
        if errores:
            print(f"    ⚠️  {errores} usuario(s) con errores — revisar manualmente")

        print("\n=== Migración completada ===")


if __name__ == '__main__':
    run_migration()
