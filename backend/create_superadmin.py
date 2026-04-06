#!/usr/bin/env python3
"""
Script para crear un usuario Super-Admin en la base de datos
Uso: python create_superadmin.py
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Departamento, Gestoria
from werkzeug.security import generate_password_hash

def create_superadmin():
    """Crear usuario super-admin si no existe"""
    
    with app.app_context():
        # Verificar si ya existe un super-admin
        existing = User.query.filter_by(email='superadmin@spainflow.com').first()
        if existing:
            print("❌ Ya existe un super-admin con email: superadmin@spainflow.com")
            print(f"   ID: {existing.id}, Nombre: {existing.nombre}")
            
            respuesta = input("\n¿Deseas actualizar la contraseña? (s/n): ")
            if respuesta.lower() != 's':
                print("Operación cancelada.")
                return
            
            # Actualizar contraseña
            nueva_password = input("Nueva contraseña: ")
            existing.password_hash = generate_password_hash(nueva_password)
            db.session.commit()
            print(f"✅ Contraseña actualizada para: {existing.email}")
            return
        
        # Verificar que existe la gestoría principal
        gestoria_principal = Gestoria.query.filter_by(id=1).first()
        if not gestoria_principal:
            print("⚠️  No existe la gestoría principal (ID=1)")
            print("   Creando gestoría principal...")
            
            gestoria_principal = Gestoria(
                nombre='SpainFlow',
                slug='spainflow',
                email='admin@spainflow.com',
                plan='enterprise',
                activa=True,
                configuracion={}
            )
            db.session.add(gestoria_principal)
            db.session.commit()
            print(f"✅ Gestoría principal creada (ID={gestoria_principal.id})")
        
        # Verificar que existe el departamento Jefatura
        departamento_jefatura = Departamento.query.filter_by(nombre='Jefatura').first()
        if not departamento_jefatura:
            print("❌ No existe el departamento 'Jefatura'")
            print("   Por favor, crea el departamento primero.")
            return
        
        # Solicitar datos del super-admin
        print("\n📝 Crear nuevo Super-Admin")
        print("-" * 50)
        
        nombre = input("Nombre completo [Super Admin]: ").strip() or "Super Admin"
        email = input("Email [superadmin@spainflow.com]: ").strip() or "superadmin@spainflow.com"
        password = input("Contraseña [SuperAdmin123!]: ").strip() or "SuperAdmin123!"
        
        # Crear usuario
        nuevo_admin = User(
            nombre=nombre,
            email=email,
            password_hash=generate_password_hash(password),
            is_super_admin=True,  # Flag de super-admin
            departamento_id=departamento_jefatura.id,
            gestoria_id=gestoria_principal.id,
            activo=True
        )
        
        db.session.add(nuevo_admin)
        db.session.commit()
        
        print("\n✅ Super-Admin creado exitosamente!")
        print("-" * 50)
        print(f"   ID: {nuevo_admin.id}")
        print(f"   Nombre: {nuevo_admin.nombre}")
        print(f"   Email: {nuevo_admin.email}")
        print(f"   Super-Admin: {nuevo_admin.is_super_admin}")
        print(f"   Gestoría: {gestoria_principal.nombre} (ID={gestoria_principal.id})")
        print(f"   Departamento: {departamento_jefatura.nombre} (ID={departamento_jefatura.id})")
        print("\n🔐 Credenciales de acceso:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print("\n⚠️  IMPORTANTE: Cambia la contraseña después del primer login!")

if __name__ == '__main__':
    try:
        create_superadmin()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
