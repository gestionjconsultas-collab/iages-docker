# backend/services/dehu_session_manager.py
"""
Gestor de sesiones DEHú para múltiples usuarios
Mantiene instancias activas de DEHuService por usuario
"""
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
from dehu_service import DEHuService

logger = logging.getLogger(__name__)

class DEHuSessionManager:
    """Gestiona sesiones DEHú por usuario con timeout automático"""
    
    def __init__(self, session_timeout_minutes: int = 30):
        self.sessions: Dict[int, dict] = {}  # user_id -> session_data
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task = None
    
    def get_session(self, user_id: int) -> Optional[DEHuService]:
        """Obtiene la sesión activa de un usuario"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # Verificar si no ha expirado
            if datetime.now() - session['last_activity'] < self.session_timeout:
                # Actualizar última actividad
                session['last_activity'] = datetime.now()
                return session['service']
            else:
                # Sesión expirada, limpiar
                logger.info(f"Sesión expirada para usuario {user_id}")
                asyncio.create_task(self.disconnect_user(user_id))
        return None
    
    async def create_session(self, user_id: int, pfx_path: str, 
                            pfx_passphrase: str, headless: bool = True) -> tuple[bool, Optional[DEHuService], str]:
        """
        Crea una nueva sesión DEHú para un usuario
        
        Returns:
            (success, service, message)
        """
        # Cerrar sesión existente si hay
        if user_id in self.sessions:
            await self.disconnect_user(user_id)
        
        try:
            # -------------------------------------------------------------------------
            # CONVERSIÓN DE CERTIFICADO (Fix OpenSSL 3.0+ Legacy PFX)
            # -------------------------------------------------------------------------
            # Estrategia robusta: PFX -> PEM (Legacy) -> PFX (Modern)
            # Usamos archivos temporales para evitar problemas de piping/quoting en shell
            import subprocess
            
            print(f"DEBUG: Iniciando conversión certificado {pfx_path}", flush=True)
            
            pem_path = pfx_path.replace('.pfx', '.pem')
            new_pfx_path = pfx_path.replace('.pfx', '_modern.pfx')
            
            # Paso 1: PFX -> PEM (Desencriptado, usando legacy provider)
            # openssl pkcs12 -in input.pfx -out temp.pem -nodes -legacy -passin pass:...
            proc1 = await asyncio.create_subprocess_exec(
                '/usr/bin/openssl', 'pkcs12', '-in', pfx_path, '-out', pem_path,
                '-nodes', '-legacy', '-passin', f'pass:{pfx_passphrase}',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out1, err1 = await proc1.communicate()
            
            if proc1.returncode != 0:
                print(f"DEBUG: Error paso 1 (PFX->PEM): {err1.decode()}", flush=True)
                # Si falla el paso 1, quizás ya es moderno o la password es incorrecta.
                # Intentamos usarlo tal cual como fallback
            else:
                print(f"DEBUG: Paso 1 OK. Creando PFX moderno...", flush=True)
                
                # Paso 2: PEM -> PFX (Encriptado con AES-256)
                # openssl pkcs12 -export -in temp.pem -out output.pfx -keypbe AES-256-CBC -certpbe AES-256-CBC -macalg SHA256 -passout pass:...
                proc2 = await asyncio.create_subprocess_exec(
                    '/usr/bin/openssl', 'pkcs12', '-export', '-in', pem_path, '-out', new_pfx_path,
                    '-keypbe', 'AES-256-CBC', '-certpbe', 'AES-256-CBC', '-macalg', 'SHA256',
                    '-passout', f'pass:{pfx_passphrase}',
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                out2, err2 = await proc2.communicate()
                
                # Limpiar PEM (contiene clave privada sin encriptar, importante borrar rápido)
                try:
                    if os.path.exists(pem_path):
                        os.unlink(pem_path)
                except:
                    pass

                if proc2.returncode == 0 and os.path.exists(new_pfx_path):
                    print(f"DEBUG: Conversión EXITOSA. Usando {new_pfx_path}", flush=True)
                    pfx_path = new_pfx_path
                else:
                    print(f"DEBUG: Error paso 2 (PEM->PFX): {err2.decode()}", flush=True)

            # -------------------------------------------------------------------------

            # Crear servicio
            service = DEHuService(pfx_path, pfx_passphrase, 
                                 session_dir=f"./tmp-dehu-{user_id}")
            
            # Conectar
            logger.info(f"Conectando DEHú para usuario {user_id}...")
            success = await service.connect(headless=headless)
            
            if not success:
                return False, None, "No se pudo autenticar con DEHú"
            
            # Obtener info del usuario
            user_info = await service.get_user_info()
            
            # Guardar sesión
            self.sessions[user_id] = {
                'service': service,
                'user_info': user_info,
                'created_at': datetime.now(),
                'last_activity': datetime.now()
            }
            
            logger.info(f"Sesión DEHú creada para usuario {user_id}")
            return True, service, "Conectado exitosamente"
            
        except Exception as e:
            logger.error(f"Error creando sesión DEHú: {e}")
            return False, None, f"Error: {str(e)}"
    
    async def disconnect_user(self, user_id: int):
        """Desconecta y limpia la sesión de un usuario"""
        if user_id in self.sessions:
            try:
                service = self.sessions[user_id]['service']
                await service.disconnect()
                logger.info(f"Sesión DEHú cerrada para usuario {user_id}")
            except Exception as e:
                logger.error(f"Error cerrando sesión: {e}")
            finally:
                del self.sessions[user_id]
    
    async def cleanup_expired_sessions(self):
        """Limpia sesiones expiradas (ejecutar periódicamente)"""
        now = datetime.now()
        expired_users = []
        
        for user_id, session in self.sessions.items():
            if now - session['last_activity'] >= self.session_timeout:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            logger.info(f"Limpiando sesión expirada de usuario {user_id}")
            await self.disconnect_user(user_id)
    
    def get_user_info(self, user_id: int) -> Optional[dict]:
        """Obtiene la info del usuario de la sesión"""
        if user_id in self.sessions:
            return self.sessions[user_id].get('user_info')
        return None
    
    def is_connected(self, user_id: int) -> bool:
        """Verifica si un usuario tiene sesión activa"""
        return self.get_session(user_id) is not None


# Instancia global del gestor
dehu_manager = DEHuSessionManager(session_timeout_minutes=30)
