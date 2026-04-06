# backend/services/saltra_service.py
"""
Servicio de integración con Saltra DEHU
Gestiona autenticación, sincronización de notificaciones y descarga de PDFs
"""

import os
import base64
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from tenant_utils import get_current_gestoria_id
from constants import NotificationTypes

# ⭐ Circuit Breaker para protección contra fallos
from utils.circuit_breaker import saltra_breaker

logger = logging.getLogger(__name__)


class SaltraService:
    """
    Servicio para conectar con la API de Saltra DEHU
    
    Funcionalidades:
    - Autenticación automática con renovación de token
    - Obtener notificaciones pendientes y realizadas
    - Descargar PDFs de notificaciones
    - Obtener detalle de notificaciones
    
    Uso:
        saltra = SaltraService()
        notificaciones = saltra.get_notifications_done(page=1, limit=50)
    """
    
    BASE_URL = "https://api.saltra.es/api/v4"
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, cert_secret: Optional[str] = None):
        """
        Inicializa el servicio con credenciales
        
        Args:
            api_key: API Key de SALTRA. Si no se proporciona, usa SALTRA_EMAIL del .env
            api_secret: API Secret de SALTRA. Si no se proporciona, usa SALTRA_PASSWORD del .env
            cert_secret: Cert-Secret específico de Saltra. Si no se proporciona,
                        usa el valor de SALTRA_CERT_SECRET del .env
        """
        # Usar credenciales proporcionadas o fallback a .env
        self.email = api_key or os.getenv('SALTRA_EMAIL')
        self.password = api_secret or os.getenv('SALTRA_PASSWORD')
        
        # Usar cert-secret específico o el del .env como fallback
        self.cert_secret = cert_secret or os.getenv('SALTRA_CERT_SECRET')
        
        # Token y expiración
        self._token = None
        self._token_expires = None
        
        # Validar configuración
        if not all([self.email, self.password, self.cert_secret]):
            logger.warning("⚠️ Credenciales de Saltra no configuradas")
    
    def _get_token(self) -> str:
        """
        Obtiene un token válido, renovándolo si es necesario
        
        Returns:
            str: Token de acceso válido
        """
        # Si tenemos token válido, usarlo
        if self._token and self._token_expires:
            if datetime.now() < self._token_expires - timedelta(hours=1):
                return self._token
        
        # Obtener nuevo token
        logger.info("🔑 Obteniendo nuevo token de Saltra...")
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/auth/login",
                json={
                    "email": self.email,
                    "password": self.password
                },
                timeout=30
            )
            
            data = response.json()
            
            if data.get(NotificationTypes.SUCCESS):
                self._token = data["data"]["access_token"]
                expires_str = data["data"]["expires_in"]
                self._token_expires = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
                logger.info(f"✅ Token obtenido, expira: {expires_str}")
                return self._token
            else:
                logger.error(f"❌ Error en login: {data.get('message')}")
                raise Exception(f"Error login Saltra: {data.get('message')}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión: {str(e)}")
            raise
    
    @saltra_breaker  # ⭐ Circuit Breaker: Protege contra fallos en API
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict:
        """
        Realiza una petición autenticada a la API de Saltra
        
        Args:
            method: GET, POST, etc.
            endpoint: Ruta del endpoint (sin base URL)
            params: Parámetros de query string
            json_data: Datos JSON para el body
        
        Returns:
            dict: Respuesta JSON de la API
        """
        token = self._get_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Cert-Secret": self.cert_secret,
            "Content-Type": "application/json"
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=60
            )
            
            # ✅ MEJORA 1: Rate Limiting Inteligente
            rate_limit = response.headers.get('X-Ratelimit-Limit')
            rate_remaining = response.headers.get('X-Ratelimit-Remaining')
            
            if rate_remaining:
                remaining = int(rate_remaining)
                limit = int(rate_limit) if rate_limit else 60
                
                # Advertencia si quedan pocas peticiones
                if remaining < 10:
                    logger.warning(f"⚠️ Rate limit bajo: {remaining}/{limit} peticiones restantes")
                    
                # Throttling preventivo si quedan muy pocas
                if remaining < 5:
                    logger.warning(f"🚨 Rate limit crítico: {remaining}/{limit} - Aplicando throttling")
                    import time
                    time.sleep(2)  # Esperar 2 segundos
                
                # Log informativo
                logger.debug(f"📊 Rate limit: {remaining}/{limit}")
            
            # Manejar error 429 (Too Many Requests)
            if response.status_code == 429:
                logger.error("🚨 Rate limit excedido (429 Too Many Requests)")
                return {NotificationTypes.SUCCESS: False, "message": "Rate limit excedido. Intenta en 1 minuto."}
            
            # Manejar errores HTTP (4xx, 5xx)
            if response.status_code >= 400:
                logger.error(f"❌ Error HTTP {response.status_code} en {endpoint}: {response.text[:200]}")
                try:
                    error_data = response.json()
                    return {NotificationTypes.SUCCESS: False, "message": error_data.get("message", f"Error {response.status_code}")}
                except:
                    return {NotificationTypes.SUCCESS: False, "message": f"Error {response.status_code}: {response.text[:100]}"}
            
            # Intentar parsear JSON
            try:
                return response.json()
            except ValueError:
                logger.error(f"❌ Respuesta no es JSON válido: {response.text[:200]}")
                return {NotificationTypes.SUCCESS: False, "message": "Respuesta inválida del servidor"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en request {endpoint}: {str(e)}")
            return {NotificationTypes.SUCCESS: False, "message": str(e)}
    
    # ==========================================
    # NOTIFICACIONES
    # ==========================================
    
    def get_notifications_done(
        self,
        page: int = 1,
        limit: int = 50,
        titular_nif: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Obtiene notificaciones realizadas (ya aceptadas)
        
        Args:
            page: Número de página (desde 1)
            limit: Registros por página (max 50)
            titular_nif: Filtrar por NIF del titular
            start_date: Fecha inicio (Y-m-d)
            end_date: Fecha fin (Y-m-d)
        
        Returns:
            {
                NotificationTypes.SUCCESS: True,
                "data": {
                    "total": 249,
                    "count": 50,
                    "page": 1,
                    "items": [...]
                }
            }
        """
        params = {"page": page, "limit": limit}
        
        if titular_nif:
            params["titularNif"] = titular_nif
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        logger.info(f"📥 Obteniendo notificaciones realizadas (página {page})...")
        return self._make_request("GET", "/dehu/notifications-done", params=params)
    
    def get_notifications_pending(
        self,
        page: int = 1,
        limit: int = 50,
        titular_nif: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        Obtiene notificaciones pendientes (sin aceptar)
        """
        params = {"page": page, "limit": limit}
        
        if titular_nif:
            params["titularNif"] = titular_nif
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        
        logger.info(f"📥 Obteniendo notificaciones pendientes (página {page})...")
        return self._make_request("GET", "/dehu/notifications-pending", params=params)
    
    def get_communications(
        self,
        page: int = 1,
        limit: int = 50,
        titular_nif: Optional[str] = None
    ) -> Dict:
        """
        Obtiene comunicaciones (no requieren aceptación)
        """
        params = {"page": page, "limit": limit}
        
        if titular_nif:
            params["titularNif"] = titular_nif
        
        logger.info(f"📥 Obteniendo comunicaciones (página {page})...")
        return self._make_request("GET", "/dehu/communications", params=params)
    
    # ==========================================
    # DETALLE Y DOCUMENTOS
    # ==========================================
    
    def get_notification_detail(
        self,
        sent_reference: str,
        include_document: bool = False,
        include_voucher: bool = False
    ) -> Dict:
        """
        Obtiene detalle completo de una notificación
        
        Args:
            sent_reference: ID único de la notificación
            include_document: Si True, incluye el PDF en base64
            include_voucher: Si True, incluye el resguardo en base64
        
        Returns:
            Detalle completo de la notificación
        """
        params = {"id": sent_reference}
        
        if include_document:
            params["duplicate"] = 1
        if include_voucher:
            params["voucher"] = 1
        
        logger.info(f"📄 Obteniendo detalle: {sent_reference[:20]}...")
        return self._make_request("GET", "/dehu/notification-detail", params=params)
    
    def download_notification_pdf(self, sent_reference: str) -> Optional[Tuple[bytes, str]]:
        """
        Descarga el PDF de una notificación
        
        Args:
            sent_reference: ID único de la notificación
        
        Returns:
            Tuple (bytes del PDF, nombre del archivo) o None si falla
        """
        logger.info(f"📥 Descargando PDF: {sent_reference[:20]}...")
        
        response = self._make_request(
            "GET", 
            "/dehu/notification-document",
            params={"id": sent_reference}
        )
        
        if response.get(NotificationTypes.SUCCESS) and response.get("data"):
            data = response["data"]
            content_b64 = data.get("content")
            filename = data.get("name", f"notificacion_{sent_reference[:10]}.pdf")
            
            if content_b64:
                pdf_bytes = base64.b64decode(content_b64)
                logger.info(f"✅ PDF descargado: {filename} ({len(pdf_bytes)} bytes)")
                return (pdf_bytes, filename)
        
        logger.error(f"❌ Error descargando PDF: {response.get('message')}")
        return None
    
    def download_notification_voucher(self, sent_reference: str) -> Optional[Tuple[bytes, str]]:
        """
        Descarga el resguardo de una notificación
        
        Args:
            sent_reference: ID único de la notificación
        
        Returns:
            Tuple (bytes del PDF, nombre del archivo) o None si falla
        """
        logger.info(f"📥 Descargando resguardo: {sent_reference[:20]}...")
        
        response = self._make_request(
            "GET",
            "/dehu/notification-voucher",
            params={"id": sent_reference}
        )
        
        if response.get(NotificationTypes.SUCCESS) and response.get("data"):
            data = response["data"]
            content_b64 = data.get("content")
            filename = data.get("name", f"resguardo_{sent_reference[:10]}.pdf")
            
            if content_b64:
                pdf_bytes = base64.b64decode(content_b64)
                logger.info(f"✅ Resguardo descargado: {filename}")
                return (pdf_bytes, filename)
        
        logger.error(f"❌ Error descargando resguardo: {response.get('message')}")
        return None
    
    # ✅ MEJORA 3: Descarga Optimizada (1 petición en lugar de 2)
    def download_notification_files_optimized(self, sent_reference: str) -> Dict:
        """
        Descarga documento y resguardo de una notificación (2 peticiones separadas)
        
        Args:
            sent_reference: ID único de la notificación
        
        Returns:
            {
                'document': (bytes, filename) or None,
                'voucher': (bytes, filename) or None,
                NotificationTypes.SUCCESS: bool,
                'errors': []
            }
        """
        logger.info(f"📦 Descargando archivos: {sent_reference[:20]}...")
        
        result = {
            'document': None,
            'voucher': None,
            NotificationTypes.SUCCESS: False,
            'errors': []
        }
        
        # 1. Descargar documento principal
        try:
            doc_response = self._make_request(
                "GET",
                "/dehu/notification-document",
                params={"id": sent_reference}
            )
            
            if doc_response.get(NotificationTypes.SUCCESS) and doc_response.get("data"):
                data = doc_response["data"]
                content_b64 = data.get("content")
                filename = data.get("name", "documento.pdf")
                
                if content_b64:
                    pdf_bytes = base64.b64decode(content_b64)
                    result['document'] = (pdf_bytes, filename)
                    logger.info(f"  ✅ Documento descargado ({len(pdf_bytes)} bytes)")
                else:
                    result['errors'].append("Documento sin contenido")
            else:
                error_msg = doc_response.get("message", "Error desconocido")
                result['errors'].append(f"Error descargando documento: {error_msg}")
                logger.error(f"  ❌ {error_msg}")
        except Exception as e:
            error_msg = f"Excepción descargando documento: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(f"  ❌ {error_msg}")
        
        # 2. Descargar resguardo
        try:
            voucher_response = self._make_request(
                "GET",
                "/dehu/notification-voucher",
                params={"id": sent_reference}
            )
            
            if voucher_response.get(NotificationTypes.SUCCESS) and voucher_response.get("data"):
                data = voucher_response["data"]
                content_b64 = data.get("content")
                filename = data.get("name", "resguardo.pdf")
                
                if content_b64:
                    pdf_bytes = base64.b64decode(content_b64)
                    result['voucher'] = (pdf_bytes, filename)
                    logger.info(f"  ✅ Resguardo descargado ({len(pdf_bytes)} bytes)")
                else:
                    result['errors'].append("Resguardo sin contenido")
            else:
                error_msg = voucher_response.get("message", "Resguardo no disponible")
                result['errors'].append(error_msg)
                logger.warning(f"  ⚠️ {error_msg}")
        except Exception as e:
            error_msg = f"Resguardo no disponible: {str(e)}"
            result['errors'].append(error_msg)
            logger.warning(f"  ⚠️ {error_msg}")
        
        # Considerar exitoso si al menos el documento se descargó
        result[NotificationTypes.SUCCESS] = bool(result['document'])
        
        if result[NotificationTypes.SUCCESS]:
            archivos = []
            if result['document']: archivos.append("documento")
            if result['voucher']: archivos.append("resguardo")
            logger.info(f"✅ Descarga completada: {', '.join(archivos)}")
        else:
            logger.error(f"❌ No se pudo descargar el documento")
        
        return result
    
    def download_notification_files(self, sent_reference: str, skip_voucher: bool = False) -> Dict:
        """
        Descarga AMBOS archivos de una notificación (documento principal + resguardo)
        
        Args:
            sent_reference: ID único de la notificación
            skip_voucher: Si True, no intenta descargar el resguardo (más rápido)
        
        Returns:
            {
                'document': (bytes, filename) or None,
                'voucher': (bytes, filename) or None,
                NotificationTypes.SUCCESS: bool,
                'errors': []
            }
        """
        logger.info(f"📦 Descargando archivos completos: {sent_reference[:20]}...")
        
        result = {
            'document': None,
            'voucher': None,
            NotificationTypes.SUCCESS: False,
            'errors': []
        }
        
        # 1. Intentar descargar documento principal
        try:
            doc = self.download_notification_pdf(sent_reference)
            if doc:
                result['document'] = doc
                logger.info(f"  ✅ Documento principal descargado")
            else:
                result['errors'].append("Documento principal no disponible")
                logger.warning(f"  ⚠️ Documento principal no disponible")
        except Exception as e:
            error_msg = f"Error descargando documento: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(f"  ❌ {error_msg}")
        
        # 2. Intentar descargar resguardo (solo si no se salta)
        if not skip_voucher:
            try:
                voucher = self.download_notification_voucher(sent_reference)
                if voucher:
                    result['voucher'] = voucher
                    logger.info(f"  ✅ Resguardo descargado")
                else:
                    result['errors'].append("Resguardo no disponible")
                    logger.warning(f"  ⚠️ Resguardo no disponible")
            except Exception as e:
                error_msg = f"Error descargando resguardo: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(f"  ❌ {error_msg}")
        else:
            logger.info(f"  ⏭️ Resguardo omitido (skip_voucher=True)")
        
        # Considerar exitoso si al menos uno se descargó
        result[NotificationTypes.SUCCESS] = bool(result['document'] or result['voucher'])
        
        if result[NotificationTypes.SUCCESS]:
            archivos = []
            if result['document']: archivos.append("documento")
            if result['voucher']: archivos.append("resguardo")
            logger.info(f"✅ Descarga completada: {', '.join(archivos)}")
        else:
            logger.error(f"❌ No se pudo descargar ningún archivo")
        
        return result
    
    def accept_notification(self, sent_reference: str) -> Dict:
        """
        Acepta una notificación pendiente
        
        Args:
            sent_reference: ID único de la notificación
        
        Returns:
            Dict con resultado de la operación
        """
        logger.info(f"📝 Aceptando notificación: {sent_reference[:20]}...")
        
        response = self._make_request(
            "POST",
            "https://api.saltra.es/api/v4/dehu/notification-accept",
            params={"id": sent_reference}
        )
        
        if response.get(NotificationTypes.SUCCESS):
            logger.info(f"✅ Notificación aceptada")
            return {NotificationTypes.SUCCESS: True, "message": "Notificación aceptada correctamente"}
        else:
            logger.error(f"❌ Error aceptando: {response.get('message')}")
            return {NotificationTypes.SUCCESS: False, "message": response.get("message", "Error desconocido")}
    
    # ==========================================
    # UTILIDADES
    # ==========================================
    
    def get_all_notifications(
        self,
        notification_type: str = "done",
        max_pages: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Obtiene todas las notificaciones paginando automáticamente
        
        Args:
            notification_type: "done", "pending" o "communications"
            max_pages: Máximo de páginas a obtener
            start_date: Fecha inicio (Y-m-d)
            end_date: Fecha fin (Y-m-d)
        
        Returns:
            Lista con todas las notificaciones
        """
        all_items = []
        page = 1
        
        # Seleccionar método según tipo
        if notification_type == "done":
            fetch_method = self.get_notifications_done
        elif notification_type == "pending":
            fetch_method = self.get_notifications_pending
        else:
            fetch_method = self.get_communications
        
        while page <= max_pages:
            response = fetch_method(
                page=page,
                limit=50,
                start_date=start_date,
                end_date=end_date
            )
            
            if not response.get(NotificationTypes.SUCCESS):
                logger.error(f"Error en página {page}")
                break
            
            items = response.get("data", {}).get("items", [])
            all_items.extend(items)
            
            total = response.get("data", {}).get("total", 0)
            count = response.get("data", {}).get("count", 0)
            
            logger.info(f"Página {page}: {count} items (total: {total})")
            
            # Si ya obtuvimos todo, salir
            if len(all_items) >= total or count == 0:
                break
            
            page += 1
        
        logger.info(f"✅ Total obtenido: {len(all_items)} notificaciones")
        return all_items
    
    def check_voucher_availability(self, sent_reference: str) -> Dict:
        """
        Verifica si el resguardo está disponible para descarga
        
        Args:
            sent_reference: ID único de la notificación
        
        Returns:
            {
                "available": True/False,
                "name": "nombre_archivo.pdf",
                "message": "Resguardo disponible" / "Resguardo no disponible"
            }
        """
        logger.info(f"🔍 Verificando disponibilidad de resguardo: {sent_reference[:20]}...")
        
        response = self._make_request(
            "GET",
            "/dehu/notification-detail",
            params={"id": sent_reference, "voucher": 0}  # Sin descargar el content
        )
        
        if response.get(NotificationTypes.SUCCESS) and response.get("data"):
            data = response["data"]
            voucher = data.get("voucher", {})
            
            if voucher.get("enabled"):
                logger.info(f"✅ Resguardo disponible: {voucher.get('name')}")
                return {
                    "available": True,
                    "name": voucher.get("name", "resguardo.pdf"),
                    "message": "Resguardo disponible"
                }
            else:
                logger.info(f"❌ Resguardo no disponible (enabled=False)")
                return {
                    "available": False,
                    "message": "Resguardo no disponible para esta notificación"
                }
        else:
            logger.warning(f"⚠️ No se pudo verificar: {response.get('message')}")
            return {
                "available": False,
                "message": response.get("message", "Error al verificar disponibilidad")
            }
    
    def test_connection(self) -> Dict:
        """
        Prueba la conexión con Saltra
        
        Returns:
            {
                NotificationTypes.SUCCESS: True/False,
                "message": "...",
                "token_expires": "2025-12-23 07:54:40",
                "total_notifications": 249
            }
        """
        try:
            # Probar login
            token = self._get_token()
            
            # Probar obtener notificaciones
            response = self.get_notifications_done(page=1, limit=1)
            
            if response.get(NotificationTypes.SUCCESS):
                total = response.get("data", {}).get("total", 0)
                return {
                    NotificationTypes.SUCCESS: True,
                    "message": "Conexión exitosa",
                    "token_expires": self._token_expires.strftime("%Y-%m-%d %H:%M:%S") if self._token_expires else None,
                    "total_notifications": total
                }
            else:
                return {
                    NotificationTypes.SUCCESS: False,
                    "message": response.get("message", "Error desconocido")
                }
                
        except Exception as e:
            return {
                NotificationTypes.SUCCESS: False,
                "message": str(e)
            }
    
    # ==========================================
    # MULTI-CERTIFICADO
    # ==========================================
    
    @staticmethod
    def for_empresa(empresa):
        """
        Crea instancia de SaltraService con el cert-secret de la empresa
        
        Args:
            empresa: Instancia de Empresa con saltra_cert_secret configurado
        
        Returns:
            SaltraService configurado para esa empresa
        
        Raises:
            ValueError: Si la empresa no tiene cert-secret configurado
        
        Example:
            empresa = Empresa.query.filter_by(nif='38092900R', gestoria_id=get_current_gestoria_id()).first()
            saltra = SaltraService.for_empresa(empresa)
            notificaciones = saltra.get_notifications_done(titular_nif=empresa.nif)
        """
        if not hasattr(empresa, 'saltra_cert_secret') or not empresa.saltra_cert_secret:
            raise ValueError(
                f"Empresa '{empresa.nombre}' (NIF: {empresa.nif}) no tiene "
                f"cert-secret de Saltra configurado. Registra el certificado "
                f"en Saltra y actualiza la BD."
            )
        
        logger.info(f"🔑 Creando servicio Saltra para {empresa.nombre} ({empresa.nif})")
        return SaltraService(cert_secret=empresa.saltra_cert_secret)
    
    @staticmethod
    def get_empresas_con_certificado():
        """
        Obtiene lista de empresas que tienen cert-secret configurado
        
        Returns:
            List[Empresa]: Lista de empresas con acceso a DEHU
        
        Example:
            empresas = SaltraService.get_empresas_con_certificado()
            for empresa in empresas:
                saltra = SaltraService.for_empresa(empresa)
                # Sincronizar notificaciones...
        """
        from models import Empresa
        
        empresas = Empresa.query.filter_by(gestoria_id=get_current_gestoria_id()).filter(
            Empresa.saltra_cert_secret.isnot(None),
            Empresa.saltra_cert_secret != ''
        ).all()
        
        logger.info(f"📊 Empresas con certificado DEHU: {len(empresas)}")
        return empresas


    # ✅ MEJORA 2: Endpoint de Estadísticas DEHU
    def get_dehu_stats(self) -> Dict:
        """
        Obtiene estadísticas en tiempo real de DEHU
        
        Returns:
            Dict con estadísticas:
            - totalNotReadCommunications: Comunicaciones no leídas
            - totalPendingNotifications: Notificaciones pendientes
            - newDeviceForPushNotify: Nuevos dispositivos para push
            - userHasUnverifiedEmail: Email no verificado
            - userHasNotContact: Sin contacto
        """
        logger.info("📊 Obteniendo estadísticas DEHU...")
        
        response = self._make_request("GET", "/dehu/stats")
        
        if response.get(NotificationTypes.SUCCESS):
            stats = response.get("data", {})
            logger.info(f"✅ Stats obtenidas: {stats.get('totalPendingNotifications', 0)} pendientes")
            return {NotificationTypes.SUCCESS: True, "stats": stats}
        else:
            logger.error(f"❌ Error obteniendo stats: {response.get('message')}")
            return {NotificationTypes.SUCCESS: False, "message": response.get("message", "Error desconocido")}


# Instancia global del servicio
saltra_service = SaltraService()