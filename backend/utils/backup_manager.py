"""
Sistema de backups automáticos con encriptación y rotación
Ejecutar diariamente con cron o Celery Beat
"""
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Gestor de backups con encriptación y rotación"""
    
    def __init__(self, 
                 backup_dir: str = '/backups',
                 gpg_recipient: str = None,
                 retention_days: int = 30,
                 retention_weekly: int = 4,
                 retention_monthly: int = 12):
        """
        Args:
            backup_dir: Directorio donde guardar backups
            gpg_recipient: Email/ID de la clave GPG para encriptar
            retention_days: Días de backups diarios a mantener
            retention_weekly: Semanas de backups semanales a mantener
            retention_monthly: Meses de backups mensuales a mantener
        """
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.gpg_recipient = gpg_recipient or os.getenv('BACKUP_GPG_RECIPIENT')
        self.retention_days = retention_days
        self.retention_weekly = retention_weekly
        self.retention_monthly = retention_monthly
    
    def create_backup(self, database_uri: str) -> str:
        """
        Crea un backup de la base de datos
        
        Args:
            database_uri: URI de conexión a PostgreSQL
        
        Returns:
            str: Ruta del archivo de backup creado
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"backup_{timestamp}.sql"
        encrypted_file = self.backup_dir / f"backup_{timestamp}.sql.gpg"
        
        try:
            # 1. Crear dump de PostgreSQL
            logger.info(f"Creando backup de base de datos...")
            
            # Extraer componentes de la URI
            # postgresql://user:pass@host:port/dbname
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_uri)
            if not match:
                raise ValueError("URI de base de datos inválida")
            
            user, password, host, port, dbname = match.groups()
            
            # Configurar variable de entorno para password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Ejecutar pg_dump
            with open(backup_file, 'w') as f:
                subprocess.run([
                    'pg_dump',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', dbname,
                    '--no-owner',
                    '--no-acl',
                    '--clean',
                    '--if-exists'
                ], stdout=f, env=env, check=True)
            
            logger.info(f"✅ Backup creado: {backup_file}")
            
            # 2. Encriptar con GPG (si está configurado)
            if self.gpg_recipient:
                logger.info(f"Encriptando backup con GPG...")
                subprocess.run([
                    'gpg',
                    '--encrypt',
                    '--recipient', self.gpg_recipient,
                    '--output', str(encrypted_file),
                    str(backup_file)
                ], check=True)
                
                # Eliminar archivo sin encriptar
                backup_file.unlink()
                logger.info(f"✅ Backup encriptado: {encrypted_file}")
                return str(encrypted_file)
            else:
                logger.warning("⚠️ GPG no configurado, backup sin encriptar")
                return str(backup_file)
        
        except Exception as e:
            logger.error(f"❌ Error creando backup: {e}")
            # Limpiar archivos parciales
            if backup_file.exists():
                backup_file.unlink()
            if encrypted_file.exists():
                encrypted_file.unlink()
            raise
    
    def rotate_backups(self):
        """
        Rota backups según política de retención
        
        Estrategia:
        - Diarios: Últimos N días
        - Semanales: Primer backup de cada semana (últimas N semanas)
        - Mensuales: Primer backup de cada mes (últimos N meses)
        """
        logger.info("Iniciando rotación de backups...")
        
        now = datetime.now()
        backups = sorted(self.backup_dir.glob('backup_*.sql*'))
        
        # Clasificar backups por fecha
        daily_cutoff = now - timedelta(days=self.retention_days)
        weekly_cutoff = now - timedelta(weeks=self.retention_weekly)
        monthly_cutoff = now - timedelta(days=self.retention_monthly * 30)
        
        backups_to_keep = set()
        weekly_backups = {}
        monthly_backups = {}
        
        for backup_file in backups:
            # Extraer fecha del nombre: backup_YYYYMMDD_HHMMSS.sql.gpg
            try:
                date_str = backup_file.stem.split('_')[1]  # YYYYMMDD
                backup_date = datetime.strptime(date_str, '%Y%m%d')
            except (IndexError, ValueError):
                logger.warning(f"Nombre de backup inválido: {backup_file}")
                continue
            
            # 1. Mantener todos los backups diarios recientes
            if backup_date >= daily_cutoff:
                backups_to_keep.add(backup_file)
                continue
            
            # 2. Mantener backups semanales (primer backup de cada semana)
            if backup_date >= weekly_cutoff:
                week_key = backup_date.strftime('%Y-W%W')
                if week_key not in weekly_backups:
                    weekly_backups[week_key] = backup_file
                    backups_to_keep.add(backup_file)
                continue
            
            # 3. Mantener backups mensuales (primer backup de cada mes)
            if backup_date >= monthly_cutoff:
                month_key = backup_date.strftime('%Y-%m')
                if month_key not in monthly_backups:
                    monthly_backups[month_key] = backup_file
                    backups_to_keep.add(backup_file)
        
        # Eliminar backups que no están en la lista de mantener
        deleted_count = 0
        for backup_file in backups:
            if backup_file not in backups_to_keep:
                logger.info(f"🗑️  Eliminando backup antiguo: {backup_file.name}")
                backup_file.unlink()
                deleted_count += 1
        
        logger.info(f"✅ Rotación completada. Backups eliminados: {deleted_count}, Backups mantenidos: {len(backups_to_keep)}")
    
    def restore_backup(self, backup_file: str, database_uri: str):
        """
        Restaura un backup
        
        Args:
            backup_file: Ruta del archivo de backup
            database_uri: URI de la base de datos donde restaurar
        """
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup no encontrado: {backup_file}")
        
        try:
            # Si está encriptado, desencriptar primero
            if backup_path.suffix == '.gpg':
                logger.info("Desencriptando backup...")
                decrypted_file = backup_path.with_suffix('')
                subprocess.run([
                    'gpg',
                    '--decrypt',
                    '--output', str(decrypted_file),
                    str(backup_path)
                ], check=True)
                sql_file = decrypted_file
            else:
                sql_file = backup_path
            
            # Extraer componentes de la URI
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_uri)
            if not match:
                raise ValueError("URI de base de datos inválida")
            
            user, password, host, port, dbname = match.groups()
            
            # Configurar variable de entorno para password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Restaurar con psql
            logger.info(f"Restaurando backup en {dbname}...")
            with open(sql_file, 'r') as f:
                subprocess.run([
                    'psql',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', dbname
                ], stdin=f, env=env, check=True)
            
            logger.info("✅ Backup restaurado exitosamente")
            
            # Limpiar archivo desencriptado temporal
            if backup_path.suffix == '.gpg' and sql_file.exists():
                sql_file.unlink()
        
        except Exception as e:
            logger.error(f"❌ Error restaurando backup: {e}")
            raise


# Función para usar con Celery Beat
def run_daily_backup():
    """
    Tarea para ejecutar backup diario
    Configurar en celery_worker.py con beat_schedule
    """
    from config import Config
    
    manager = BackupManager(
        backup_dir=os.getenv('BACKUP_DIR', '/backups'),
        gpg_recipient=os.getenv('BACKUP_GPG_RECIPIENT'),
        retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30')),
        retention_weekly=int(os.getenv('BACKUP_RETENTION_WEEKLY', '4')),
        retention_monthly=int(os.getenv('BACKUP_RETENTION_MONTHLY', '12'))
    )
    
    try:
        # Crear backup
        backup_file = manager.create_backup(Config.SQLALCHEMY_DATABASE_URI)
        logger.info(f"✅ Backup diario completado: {backup_file}")
        
        # Rotar backups antiguos
        manager.rotate_backups()
        
        return {'success': True, 'backup_file': backup_file}
    except Exception as e:
        logger.error(f"❌ Error en backup diario: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == '__main__':
    # Ejemplo de uso
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python backup_manager.py [create|rotate|restore]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    manager = BackupManager()
    
    if command == 'create':
        database_uri = os.getenv('DATABASE_URI')
        if not database_uri:
            print("Error: DATABASE_URI no configurada")
            sys.exit(1)
        backup_file = manager.create_backup(database_uri)
        print(f"Backup creado: {backup_file}")
    
    elif command == 'rotate':
        manager.rotate_backups()
        print("Rotación completada")
    
    elif command == 'restore':
        if len(sys.argv) < 3:
            print("Uso: python backup_manager.py restore <backup_file>")
            sys.exit(1)
        backup_file = sys.argv[2]
        database_uri = os.getenv('DATABASE_URI')
        manager.restore_backup(backup_file, database_uri)
        print("Backup restaurado")
    
    else:
        print(f"Comando desconocido: {command}")
        sys.exit(1)