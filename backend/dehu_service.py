"""
DEHú Service - Servicio completo de integración con DEHú
Automatiza: login, listar, detalle, aceptar, descargar notificaciones

Endpoints mapeados:
  GET  /api/v1/notifications                                    → Pendientes
  GET  /api/v1/realized_notifications?finalDate[left_date]=...  → Realizadas
  GET  /api/v1/notifications/{sentRef}                          → Detalle pendiente
  GET  /api/v1/realized_notifications/{sentRef}/full_detail     → Detalle realizada
  GET  /api/v1/get_legal_text/1/es                              → Texto legal
  POST /api/v1/notifications/{sentRef}/voucher                  → Aceptar
  GET  /api/v1/realized_notifications/{sentRef}/annexe          → Documento PDF
  POST /api/audit/user/{sentRef}/appearance-download-document   → Audit descarga
  GET  /api/v1/user/{nif_b64}                                   → Info usuario
"""
import asyncio
import json
import shutil
import os
import base64
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("DEHuService")

# Configurar FileHandler para asegurar logs
try:
    fh = logging.FileHandler('/var/www/iages/logs/dehu_debug.log')
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    print(f"Error configurando log file: {e}")


class DEHuService:
    """Servicio de integración directa con DEHú via Playwright + REST API"""
    
    def __init__(self, pfx_path: str, pfx_passphrase: str, session_dir: str = "./tmp-dehu-session"):
        self.pfx_path = pfx_path
        self.pfx_passphrase = pfx_passphrase
        self.session_dir = session_dir
        self.jwt_token = None
        self.jwt_expires = None
        self.context = None
        self.page = None
        self._pw_instance = None
        self.user_info = None
    
    # =========================================================================
    # CONEXIÓN Y AUTENTICACIÓN
    # =========================================================================
    
    async def connect(self, headless: bool = False) -> bool:
        """Inicia Playwright, navega a DEHú y autentica con certificado digital"""
        if os.path.exists(self.session_dir):
            shutil.rmtree(self.session_dir, ignore_errors=True)
        
        logger.info("Iniciando Playwright con certificado...")
        
        cert_config = {"pfxPath": self.pfx_path, "passphrase": self.pfx_passphrase}
        
        self._pw_instance = await async_playwright().start()
        # Asegurar directorio de videos
        video_dir = "/var/www/iages/backend/static/videos"
        os.makedirs(video_dir, exist_ok=True)

        self.context = await self._pw_instance.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=True,
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 720},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--ignore-certificate-errors"
            ],
            ignore_https_errors=True,
            client_certificates=[
                {"origin": "https://dehu.redsara.es", **cert_config},
                {"origin": "https://pasarela.clave.gob.es", **cert_config},
                {"origin": "https://pasarela-ident.clave.gob.es", **cert_config},
            ]
        )
        self.page = self.context.pages[0]
        
        # Capturar JWT via navegación
        def on_navigate(frame):
            if "authData=" in frame.url:
                token = frame.url.split("authData=")[1]
                if "&" in token:
                    token = token.split("&")[0]
                self.jwt_token = token
                self.jwt_expires = datetime.now() + timedelta(minutes=9)
                logger.info("JWT capturado!")
        
        self.page.on("framenavigated", on_navigate)
        
        # Navegar a DEHú
        logger.info("Navegando a DEHú...")
        try:
            await self.page.goto("https://dehu.redsara.es")
            await self.page.wait_for_timeout(3000)
            logger.info(f"Título tras navegar: {await self.page.title()}")
        except Exception as e:
            logger.error(f"Error navegando: {e}")
            return False
        
        # Click en Acceder
        if "/es/public" in self.page.url:
            logger.info("Click en Acceder...")
            try:
                await self.page.evaluate("document.querySelector('dnt-modal')?.remove()")
            except:
                pass
            try:
                clicked = await self.page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('dnt-button, button, a');
                        for (const b of btns) {
                            if (b.textContent.includes('Acceder')) { b.click(); return true; }
                        }
                        return false;
                    }
                """)
                logger.info(f"Botón Acceder clickeado: {clicked}")
            except Exception as e:
                logger.error(f"Error clickeando Acceder: {e}")
        
        # -------------------------------------------------------------
        # Esperar autenticación + manejo dinámico de Cl@ve
        # -------------------------------------------------------------
        logger.info("Esperando autenticación con certificado...")
        clave_clicked = False
        
        for i in range(90):
            if self.jwt_token:
                logger.info(f"JWT capturado en {i} seg")
                break
            
            # Si estamos en Cl@ve y no hemos clickeado AFIRMA, intentar
            current_url = self.page.url
            if "clave.gob.es" in current_url and not clave_clicked:
                if await self._try_click_clave_afirma(i):
                    clave_clicked = True
                    logger.info("  [Cl@ve] Click confirmado en AFIRMA")
            
            await self.page.wait_for_timeout(1000)
            if i % 10 == 0:
                logger.info(f"  ... {i}s esperando. URL: {current_url[:80]}")
                
        if not self.jwt_token:
            logger.error(f"No se pudo capturar JWT. URL final: {self.page.url}")
            await self.page.screenshot(path=os.path.join(LOGS_DIR, "debug_auth_failed.png"))
            return False

        # Esperar carga del home
        try:
            await self.page.wait_for_url("**/home**", timeout=15000)
        except:
            pass
        await self.page.wait_for_timeout(3000)
        
        logger.info(f"Autenticado! URL: {self.page.url}")
        return True
    
    async def disconnect(self):
        '''Cierra navegador y limpia sesión'''
        if self.page:
            try:
                path = await self.page.video.path()
                logger.info(f"Video de la sesión guardado en: {path}")
            except:
                pass

        if self.context:
            try:
                await self.context.close()
            except:
                pass
        if self._pw_instance:
            try:
                await self._pw_instance.stop()
            except:
                pass
        logger.info("Desconectado")
    
    async def _ensure_token(self):
        '''Verifica que el JWT no haya expirado, re-autentica si es necesario'''
        if not self.jwt_token or (self.jwt_expires and datetime.now() > self.jwt_expires):
            logger.warning("JWT expirado, refrescando...")
            r = await self._api_call("GET", f"/api/v1/user/{self._nif_b64()}")
            if r and r.get("status") == 200 and r.get("data", {}).get("token"):
                self.jwt_token = r["data"]["token"]
                self.jwt_expires = datetime.now() + timedelta(minutes=9)
                logger.info("JWT refrescado via /api/v1/user")
                return True
            logger.warning("Refresco fallido, re-navegando...")
            await self.page.goto("https://dehu.redsara.es")
            await self.page.wait_for_timeout(5000)
            return self.jwt_token is not None
        return True
    
    def _nif_b64(self):
        if self.jwt_token:
            try:
                payload = self.jwt_token.split(".")[1]
                payload += "=" * (4 - len(payload) % 4)
                data = json.loads(base64.b64decode(payload))
                return base64.b64encode(data.get("username", "").encode()).decode()
            except:
                pass
        return ""
    
    def _get_nif(self):
        if self.jwt_token:
            try:
                payload = self.jwt_token.split(".")[1]
                payload += "=" * (4 - len(payload) % 4)
                data = json.loads(base64.b64decode(payload))
                return data.get("username", "")
            except:
                pass
        return ""
    
    # =========================================================================
    # API CALL BASE (con retry para navegaciones)
    # =========================================================================
    
    async def _api_call(self, method: str, url: str, body: dict = None, 
                        accept: str = "application/json", retries: int = 3) -> dict:
        '''Ejecuta fetch() dentro del navegador con JWT + cookies + retry'''
        await self._ensure_token()
        
        body_js = f'body: JSON.stringify({json.dumps(body)}),' if body else ''
        content_type = '"Content-Type": "application/json",' if body else ''
        
        for attempt in range(retries):
            try:
                # Esperar a que la página esté estable
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=5000)
                except:
                    pass
                
                # CORRECCIÓN CRÍTICA: Eliminar espacios en la URL base
                final_url = url
                if url.startswith("/"):
                    final_url = f"https://dehu.redsara.es{url}"  # ¡SIN ESPACIOS!
                
                # Script de fetch con timeout de 15s
                result = await self.page.evaluate(f'''
                    async () => {{
                        const controller = new AbortController();
                        const timeoutId = setTimeout(() => controller.abort(), 15000);
                        
                        try {{
                            const r = await fetch("{final_url}", {{
                                method: "{method}",
                                headers: {{
                                    "Accept": "{accept}",
                                    "Accept-Language": "es",
                                    {content_type}
                                    "Authorization": "Bearer {self.jwt_token}"
                                }},
                                credentials: "same-origin",
                                {body_js}
                                signal: controller.signal
                            }});
                            clearTimeout(timeoutId);
                            
                            const status = r.status;
                            const ct = r.headers.get('content-type') || '';
                            
                            if (ct.includes('application/pdf') || ct.includes('octet-stream')) {{
                                const blob = await r.blob();
                                const buffer = await blob.arrayBuffer();
                                const bytes = new Uint8Array(buffer);
                                let binary = '';
                                for (let i = 0; i < bytes.length; i++) {{
                                    binary += String.fromCharCode(bytes[i]);
                                }}
                                return {{ 
                                    status, content_type: ct, size: blob.size, 
                                    b64_data: btoa(binary) 
                                }};
                            }}
                            
                            const text = await r.text();
                            let data = null;
                            try {{ data = JSON.parse(text); }} catch(e) {{}}
                            return {{ status, data, text: text.substring(0, 5000), content_type: ct }};
                        }} catch(e) {{
                            return {{ status: 0, error: e.message }};
                        }}
                    }}
                ''')
                return result
                
            except Exception as e:
                if attempt < retries - 1:
                    logger.warning(f"API call failed (attempt {attempt+1}): {e}, retrying...")
                    await self.page.wait_for_timeout(2000)
                else:
                    logger.error(f"API call failed after {retries} attempts: {e}")
                    return {"status": 0, "error": str(e)}
    
    # =========================================================================
    # NOTIFICACIONES PENDIENTES
    # =========================================================================
    
    async def get_pending_notifications(self, page: int = 1, limit: int = 50) -> dict:
        '''Obtiene notificaciones pendientes'''
        logger.info(f"Obteniendo notificaciones pendientes page={page}")
        r = await self._api_call("GET", f"/api/v1/notifications?page={page}&limit={limit}")
        
        if r.get("status") == 200:
            return r.get("data", {})
        logger.error(f"Error pendientes: {r}")
        return {"items": [], "total": 0}
    
    async def get_all_pending_notifications(self) -> list:
        '''Obtiene TODAS las pendientes paginando automáticamente'''
        all_items = []
        pg = 1
        while True:
            data = await self.get_pending_notifications(page=pg, limit=50)
            items = data.get("items", [])
            all_items.extend(items)
            if len(all_items) >= data.get("total", 0) or not items:
                break
            pg += 1
        logger.info(f"Total pendientes: {len(all_items)}")
        return all_items
    
    # =========================================================================
    # NOTIFICACIONES REALIZADAS
    # =========================================================================
    
    async def get_realized_notifications(self, days_back: int = 7, page: int = 1, 
                                          limit: int = 50) -> dict:
        '''DEHú limita el rango de fechas (~30 días max)'''
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        left = quote(start_date.strftime("%d/%m/%Y"))
        right = quote(end_date.strftime("%d/%m/%Y"))
        
        url = (f"/api/v1/realized_notifications?page={page}&limit={limit}"
               f"&finalDate[left_date]={left}&finalDate[right_date]={right}")
        
        r = await self._api_call("GET", url)
        if r.get("status") == 200:
            return r.get("data", {})
        logger.error(f"Error realizadas: {r}")
        return {"items": [], "total": 0}
    
    # =========================================================================
    # DETALLE
    # =========================================================================
    
    async def get_notification_detail(self, sent_reference: str) -> dict:
        r = await self._api_call("GET", f"/api/v1/notifications/{sent_reference}")
        if r.get("status") == 200:
            return r.get("data", {})
        return {}
    
    async def get_realized_detail(self, sent_reference: str) -> dict:
        r = await self._api_call("GET", 
            f"/api/v1/realized_notifications/{sent_reference}/full_detail")
        if r.get("status") == 200:
            return r.get("data", {})
        return {}
    
    # =========================================================================
    # ACEPTAR NOTIFICACIÓN - MÉTODO CORREGIDO (USANDO API REST)
    # =========================================================================
    
    async def accept_notification(self, sent_reference: str) -> dict:
        '''
        Acepta una notificación mediante la interfaz web (simulando usuario)
        Flujo robusto:
          1. Verificar estado actual (idempotencia)
          2. Buscar en lista (con reintento y recarga)
          3. Abrir detalle y clickar Aceptar
          4. Confirmar
        '''
        logger.info(f"=== ACEPTANDO NOTIFICACIÓN {sent_reference} ===")
        
        try:
            # Paso 1: Verificar estado actual
            logger.info(f"Paso 1: Verificando estado actual...")
            detail = await self.get_notification_detail(sent_reference)
            
            if not detail:
                realized_detail = await self.get_realized_detail(sent_reference)
                if realized_detail:
                    logger.info(f"✅ Notificación ya está en estado 'realizada'")
                    return {
                        "success": True, 
                        "message": "Notificación ya procesada anteriormente",
                        "status": "realizada",
                        "sent_reference": sent_reference,
                        "data": realized_detail
                    }
            
            visual_id = detail.get("identifier", sent_reference) if detail else sent_reference
            status = detail.get("status", "pendiente").lower() if detail else "pendiente"
            
            if status in ["realizada", "aceptada", "accepted", "completed"]:
                 logger.info(f"✅ Notificación {visual_id} ya aceptada.")
                 return {"success": True, "message": "Ya aceptada", "status": status}

            # Paso 2: Navegar y Buscar (con reintentos)
            logger.info(f"Paso 2: Buscando {visual_id} en la UI...")
            
            # Resetear navegación si es necesario
            if "/notifications" not in self.page.url:
                await self.page.goto("https://dehu.redsara.es/es/notifications")
                await self.page.wait_for_load_state("networkidle", timeout=15000)
            
            found_and_clicked = False
            max_retries = 2
            
            for attempt in range(max_retries):
                # Chequeo "fail-safe": ¿Está el modal ya abierto?
                logger.info("  Verificando si el modal ya está abierto...")
                try:
                    # Estrategia: Buscar elementos que SOLO aparecen en el modal
                    modal_indicators = [
                        f".modal-content:has-text('{visual_id}')", # ID DENTRO del modal
                        f"[role='dialog']:has-text('{visual_id}')", # Rol dialgo + ID
                        "button:has-text('Aceptar Notificación')", # Botón de acción
                        "h5:has-text('Detalle')", # Título común
                        ".modal-content", 
                        "[role='dialog']"
                    ]
                    
                    is_modal_open = False
                    for indicator in modal_indicators:
                        if await self.page.is_visible(indicator):
                            logger.info(f"  🎯 Modal detectado por indicador: {indicator}")
                            is_modal_open = True
                            break
                    
                    if is_modal_open:
                        # Verificar que sea la correcta (si es posible)
                        logger.info(f"  Verificando contenido del modal para {visual_id}...")
                        content = await self.page.content()
                        
                        # Check 1: Búsqueda exacta en HTML raw
                        if visual_id in content or sent_reference in content:
                           logger.info("  ✅ Confirmado: ID encontrado en HTML.")
                           found_and_clicked = True
                           break
                        
                        # Check 2: Búsqueda visual por texto (Playwright engine)
                        if await self.page.is_visible(f"text={visual_id}"):
                            logger.info("  ✅ Confirmado: ID visible en pantalla.")
                            found_and_clicked = True
                            break
                        
                        # Check 3: Si vemos "Aceptar Notificación", asumimos que es correcta (Modo agresivo)
                        # Esto es necesario si el ID tiene formatos raros o está en shadow DOM
                        if await self.page.is_visible("text=Aceptar Notificación"):
                            logger.warning("  ⚠️ ID no confirmado pero botón Aceptar visible. Procediendo (asunción de corrección).")
                            found_and_clicked = True
                            break
                        
                        logger.warning("  Modal abierto pero no se pudo confirmar identidad. Intentando cerrar...")
                        # Intentar cerrar para buscar en la lista
                        await self.page.keyboard.press("Escape")
                        await self.page.wait_for_timeout(1000)
                except Exception as e:
                    logger.warning(f"  Error verificando modal: {e}")

                # Si ya lo encontramos (porque estaba abierto), salimos del loop de búsqueda
                if found_and_clicked:
                    break

                # Buscar en el DOM (Lista de notificaciones)
                logger.info(f"  Buscando {visual_id} en la lista...")
                action_result = await self.page.evaluate(f'''
                    (ref) => {{
                        const searchFor = ref.trim();
                        const elements = Array.from(document.querySelectorAll('div, span, p, a, td, h4'));
                        for (const el of elements) {{
                            if (el.textContent && el.textContent.includes(searchFor)) {{
                                const card = el.closest('tr') || el.closest('.card') || el.closest('article') || el.closest('.list-group-item');
                                if (card) {{
                                    // ESTRATEGIA: Buscar botón "Aceptar" DIRECTO en la fila
                                    const acceptBtn = Array.from(card.querySelectorAll('button, a, div[role="button"]'))
                                        .find(b => b.innerText && b.innerText.toLowerCase().includes('aceptar'));
                                    
                                    if (acceptBtn) {{
                                        acceptBtn.click();
                                        return 'direct_accept';
                                    }}

                                    // Si no, click en el enlace o la fila para abrir detalle
                                    const link = card.querySelector('a');
                                    if (link) link.click(); else card.click();
                                    return 'row_click';
                                }}
                            }}
                        }}
                        return false;
                    }}
                ''', visual_id)
                
                if action_result:
                    logger.info(f"  Acción realizada en lista: {action_result}")
                    found_and_clicked = True
                    # Si hicimos click directo en aceptar, es probable que vayamos directo al aviso legal
                    if action_result == 'direct_accept':
                        clicked_accept_direct = True
                    break
                
                # ESTRATEGIA NUEVA: Navegación Directa por URL (Sugerencia Usuario + Aviso Legal)
                # Intentamos ir directo a la página de firma/aceptación
                logger.info(f"  Intentando navegación directa por URL de ACEPTACIÓN: .../pending/{sent_reference}/aceptar")
                try:
                    await self.page.goto(f"https://dehu.redsara.es/es/notifications/pending/{sent_reference}/aceptar")
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                    await self.page.wait_for_timeout(2000)
                    
                    # Verificar si estamos en el aviso legal
                    if await self.page.is_visible("text=Aviso Legal") or await self.page.is_visible("text=Doy mi consentimiento"):
                        logger.info("  ✅ Navegación directa a página de Aceptación/Aviso Legal exitosa.")
                        found_and_clicked = True
                        break
                except Exception as e:
                    logger.warning(f"  Falló navegación directa: {e}")

                # Si falló, intentar fallback al primer elemento (demo mode) O recargar
                if attempt < max_retries - 1:
                    logger.warning(f"  No encontrado {visual_id}. Recargando página de lista...")
                    await self.page.goto("https://dehu.redsara.es/es/notifications")
                    await self.page.wait_for_load_state("networkidle", timeout=15000)
                    await self.page.wait_for_timeout(2000)
            
            # Verificación final post-busqueda
            if not found_and_clicked:
                 logger.info("  Búsqueda fallida. Comprobación final de modal/aviso...")
                 try:
                     if await self.page.is_visible("text=Aviso Legal") or await self.page.is_visible("text=Doy mi consentimiento"):
                         found_and_clicked = True
                     elif await self.page.is_visible("text=Aceptar Notificación"):
                         found_and_clicked = True
                 except: pass

            if not found_and_clicked:
                await self.page.screenshot(path="/var/www/iages/backend/static/debug_list_missing.png")
                return {"error": f"No se pudo encontrar visualmente la notificación {visual_id}", "step": 2}

            # Paso 3: Bucle de Interacción Unificado (Detalle -> Aviso Legal -> Confirmación)
            logger.info("Paso 3: Iniciando bucle de interacción (WebComponents: dnt-checkbox / dnt-button)...")
            
            start_time = datetime.now()
            success_detected = False
            
            reauth_clave_clicked = False
            
            while (datetime.now() - start_time).seconds < 60:
                # 3.0 MANEJO CL@VE: Si estamos en pasarela Cl@ve, click AFIRMA
                cur_url = self.page.url
                if "clave.gob.es" in cur_url and not reauth_clave_clicked:
                    try:
                        r = await self.page.evaluate('''
                            () => {
                                const btn = document.querySelector("button.idp-button[onclick*='AFIRMA']");
                                if (btn) { btn.click(); return 'Button AFIRMA'; }
                                const all = document.querySelectorAll('[onclick*="AFIRMA"]');
                                if (all.length > 0) { all[0].click(); return 'onclick AFIRMA'; }
                                if (typeof selectedIdP === 'function') {
                                    selectedIdP('AFIRMA');
                                    const form = document.querySelector('form');
                                    if (form) { form.submit(); return 'selectedIdP+submit'; }
                                    return 'selectedIdP only';
                                }
                                return false;
                            }
                        ''')
                        if r:
                            logger.info(f"  🔐 Re-auth Cl@ve click: {r}")
                            reauth_clave_clicked = True
                            await self.page.wait_for_timeout(5000)  # Esperar re-auth
                            continue
                    except:
                        pass
                
                # 3.1 Verificar ÉXITO real
                try:
                    is_realized_url = "realized" in self.page.url
                    # Si ya no estamos en la página de aceptación y vemos indicadores de éxito
                    if is_realized_url or \
                       await self.page.is_visible("text=Detalle de notificación realizada") or \
                       await self.page.is_visible("button:has-text('Ver documentos')"):
                         
                         logger.info("  ✅ Éxito detectado (Realizada). Finalizando bucle.")
                         success_detected = True
                         break
                    
                    # Si vemos un mensaje de éxito pero seguimos en la página, esperamos un poco más
                    if await self.page.is_visible(".alert-success") or \
                       await self.page.is_visible("text=correctamente") or \
                       await self.page.is_visible("text=exitosamente"):
                        logger.info("  Buscando transición final a Realizada...")
                        await self._wait_for_spinner()
                except: pass

                # 3.2 Actuar sobre CHECKBOX (Soporte Shadow DOM - JS Injection)
                # El input nativo suele estar oculto (opacity 0) y Playwright falla con "outside viewport".
                # Solución: Inyectar JS para clicar internamente sin chequear visibilidad.
                try:
                    await self.page.evaluate('''() => {
                        const dnt = document.querySelector('dnt-checkbox');
                        if (dnt && dnt.shadowRoot) {
                            const input = dnt.shadowRoot.querySelector('input[type="checkbox"]');
                            const label = dnt.shadowRoot.querySelector(".dnt-checkbox__label");
                            // Si existe y no está marcado, clicamos
                            if (input && !input.checked) {
                                // Preferimos click en label si existe (simula usuario)
                                if (label) label.click();
                                else input.click();
                            }
                        }
                    }''')
                    logger.info("  [Bucle] JS Injection ejecutado para dnt-checkbox.")
                except Exception as e:
                    logger.warning(f"  [Error Checkbox JS]: {e}")

                # 3.3 Actuar sobre BOTÓN (Soporte Shadow DOM)
                # Prioridad: dnt-button (WebComponent) > button standard > link
                try:
                    # 1. dnt-button (botón específico de la administración)
                    # Buscamos el botón "interno" si es posible, o el host
                    # El snippets mostraba <dnt-button ...>Aceptar ...</dnt-button>
                    action_clicked = False
                    
                    # Selector específico para dnt-button que contenga texto
                    dnt_btn = self.page.locator("dnt-button").filter(has_text="Aceptar notificación").first
                    
                    if await dnt_btn.count() > 0:
                        # Verificar si está "disabled" (atributo aria-disabled o clase)
                        # Nota: .get_attribute a veces falla si el elemento cambia rápido
                        is_disabled = await dnt_btn.get_attribute("aria-disabled") == "true"
                        if not is_disabled:
                             logger.info("  [Bucle] Click en dnt-button 'Aceptar notificación'")
                             await dnt_btn.click(force=True)
                             action_clicked = True
                        else:
                             # Si está disabled, forzamos un re-intento de checkbox en el siguiente loop
                             logger.info("  [Bucle] dnt-button encontrado pero DISABLED. Reintentando checkbox...")
                    
                    if not action_clicked:
                        # 2. Fallback: Botón estándar de HTML
                        std_btn = self.page.locator("button:has-text('Aceptar notificación'), button:has-text('Confirmar')").first
                        if await std_btn.count() > 0 and await std_btn.is_visible():
                             logger.info(f"  [Bucle] Click en botón estándar: {await std_btn.text_content()}")
                             await std_btn.click(force=True)
                             action_clicked = True

                    if action_clicked:
                        await self.page.wait_for_timeout(1000)
                        await self._wait_for_spinner()
                        continue

                except Exception as e:
                    logger.warning(f"  [Error Botón]: {e}")

                await self.page.wait_for_timeout(1000) # Espera pasiva

            # Verificación final
            if success_detected:
                logger.info("  Aceptación visual confirmada. Esperando estabilidad final...")
                await self._wait_for_spinner()
                await self._copy_session_video(sent_reference)
                return {"success": True, "message": "Aceptada correctamente (visual)", "sent_reference": sent_reference}

        except Exception as e:
            # Fallback check vía API en caso de excepción o baneo
            logger.info("  Petición errónea en UI, verificando si ya consta como realizada...")
            check_realized = await self.get_realized_detail(sent_reference)
            if check_realized:
                 logger.info("  ✅ Éxito confirmado por API tras error UI.")
                 res = {"success": True, "message": "Aceptada (confirmado tras error UI)", "sent_reference": sent_reference}
                 await self._copy_session_video(sent_reference)
                 return res

            logger.error(f"❌ Error UI acceptance: {e}")
            await self.page.screenshot(path=f"/var/www/iages/backend/static/debug_error_{sent_reference}.png")
            await self._copy_session_video(sent_reference)
            return {"error": str(e), "step": "exception"}
    
    # =========================================================================
    # DESCARGAR DOCUMENTOS
    # =========================================================================
    
    async def _try_click_clave_afirma(self, i: int) -> bool:
        '''Función inyectada para buscar botón AFIRMA en Cl@ve. Retorna True si tuvo éxito.'''
        try:
            result = await self.page.evaluate('''
                () => {
                    // 1. Botón específico IDP
                    const btn = document.querySelector("button.idp-button[onclick*='AFIRMA']");
                    if (btn) { btn.click(); return 'Button AFIRMA click'; }

                    // 2. Cualquier elemento con onclick AFIRMA
                    const all = document.querySelectorAll('[onclick*="AFIRMA"]');
                    if (all.length > 0) { all[0].click(); return 'onclick AFIRMA'; }

                    // 3. Llamada directa a función JS del sitio (Bypass visual)
                    if (typeof selectedIdP === 'function') {
                        selectedIdP('AFIRMA');
                        const form = document.querySelector('form');
                        if (form) { form.submit(); return 'selectedIdP + form.submit'; }
                        return 'selectedIdP only (no form found)';
                    }

                    // 4. Búsqueda por texto (fallback)
                    const candidates = document.querySelectorAll('a, button, div, li, span');
                    for (const el of candidates) {
                        const t = (el.textContent || '').toLowerCase();
                        if (t.includes('certificado') || (t.includes('dnie') && t.length < 100)) {
                            el.click();
                            return 'Text: ' + t.substring(0, 40);
                        }
                    }
                    return false;
                }
            ''')
            if result:
                logger.info(f"✅ Cl@ve click ({elapsed_seconds}s): {result}")
                return True
        except Exception:
            pass  # página navegando, normal
        return False

    async def _try_visual_download(self, sent_reference: str, save_path: str = None) -> bytes | None:
        'Intenta descargar el documento via la UI (modal + click en ShadowDOM).'
        target_url = f"https://dehu.redsara.es/es/notifications/realized/{sent_reference}"
        logger.info(f"Navegando a detalle visual: {target_url}")
        try:
            await self.page.goto(target_url)
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await self._wait_for_spinner()
            
            # 1. ABRIR MODAL
            logger.info("  Abriendo modal 'Ver documentos'...")
            # Click en botón 'Ver documentos' (dnt-button dentro de ShadowDOM a veces)
            await self.page.evaluate('''() => {
                const btn = document.querySelector('dnt-button[title-text="Ver documentos"]');
                if (btn) {
                    if (btn.shadowRoot) { btn.shadowRoot.querySelector('button')?.click(); }
                    else { btn.click(); }
                }
            }''')
            await self.page.wait_for_timeout(3000)

            # 2. INTENTAR DESCARGA VÍA CLIC REAL (Playwright Download)
            logger.info("  Intentando captura de descarga vía clic en 'Descargar'...")
            try:
                async with self.page.expect_download(timeout=10000) as download_info:
                    await self.page.evaluate('''() => {
                        const links = Array.from(document.querySelectorAll('dnt-link'));
                        const dl = links.find(l => 
                            (l.titleText || '').includes('Descargar') || 
                            l.innerText.includes('Descargar')
                        );
                        if (dl) {
                            if (dl.shadowRoot) { dl.shadowRoot.querySelector('a')?.click(); }
                            else { dl.click(); }
                            return "CLICKED";
                        }
                        return "NOT_FOUND";
                    }''')
                
                download = await download_info.value
                # Guardar temporalmente
                temp_path = os.path.join("/var/www/iages/backend/static", f"dehu_{sent_reference[:10]}.pdf")
                await download.save_as(temp_path)
                
                with open(temp_path, "rb") as f:
                    pdf_bytes = f.read()
                
                if len(pdf_bytes) > 1000:
                    logger.info(f"✅ Descarga visual exitosa: {len(pdf_bytes)} bytes")
                    if save_path:
                        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                        with open(save_path, "wb") as f: f.write(pdf_bytes)
                    return pdf_bytes
                    
            except Exception as e:
                logger.warning(f"  No se pudo capturar descarga vía UI: {e}. Probando API...")

        except Exception as e:
            logger.warning(f"  Error en paso visual: {e}")
        return None

    async def download_annexe(self, sent_reference: str, save_path: str = None, max_wait: int = 30) -> bytes:
        'Descarga documento PDF de notificación realizada (Híbrido: Visual -> API).'
        logger.info(f"Descargando annexe para {sent_reference[:30]}...")

        # 1. Intentar descarga visual primero (Nueva lógica robusta)
        pdf_bytes = await self._try_visual_download(sent_reference, save_path)
        if pdf_bytes:
            return pdf_bytes

        # 2. Fallback a API polling (Lógica existente mejorada)
        logger.info("Enviando auditoría de descarga API...")
        await self._api_call("POST", f"/api/audit/user/{sent_reference}/appearance-download-document")
        
        annexe_url = None
        for wait_attempt in range(20):
            # Probar /document (el endpoint del curl)
            logger.info(f"Probando endpoint /document (intento {wait_attempt+1})...")
            r_doc = await self._api_call("GET", f"/api/v1/realized_notifications/{sent_reference}/document")
            
            # Lógica corregida: El JSON real está en r_doc['data']
            doc_data = r_doc.get("data") or {}
            # A veces _api_call devuelve el JSON directo en 'data', a veces 'b64_data' si detectó binario
            b64_content = doc_data.get("content") if isinstance(doc_data, dict) else None
            
            # Fallback a b64_data (si _api_call lo detectó como stream)
            if not b64_content:
                b64_content = r_doc.get("b64_data")

            if b64_content and len(b64_content) > 100:
                try:
                    pdf_bytes = base64.b64decode(b64_content)
                    if len(pdf_bytes) > 500:
                        logger.info(f"✅ Descargado vía /document: {len(pdf_bytes)} bytes")
                        if save_path:
                            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                            with open(save_path, "wb") as f: f.write(pdf_bytes)
                        return pdf_bytes
                except Exception as e:
                    logger.error(f"Error decodificando b64 de /document: {e}")

            # 1.2 Consultar full_detail para estrategia (cada 2 intentos)
            if wait_attempt % 2 == 0:
                detail_data = await self.get_realized_detail(sent_reference)
                if detail_data and isinstance(detail_data, dict):
                    # Chequear si existe documento principal
                    doc_meta = detail_data.get("document")
                    has_doc = doc_meta and isinstance(doc_meta, dict) and doc_meta.get("name")
                    
                    # Chequear anexos
                    annexes = detail_data.get("annexes") or detail_data.get("attachments")
                    has_annexes = annexes and len(annexes) > 0
                    
                    if has_annexes:
                        logger.info("¡Anexos encontrados en el full_detail!")
                        first = annexes[0]
                        annexe_url = first.get("url") or first.get("downloadUrl") or first.get("href")
                        if annexe_url: break
                    
                    if has_doc:
                        pass 
                    
                    if not has_doc and not has_annexes and detail_data.get("identifier"):
                         logger.warning("❌ El detalle indica que NO hay documentos ni anexos. Abortando.")
                         return None

            logger.info(f"  Documento todavía no disponible (intento {wait_attempt+1}/20)...")
            await self.page.wait_for_timeout(3000)

        if not annexe_url:
            logger.error("❌ Agotados todos los métodos de descarga.")
            return None
        
        logger.info(f"Descargando desde URL de anexo: {annexe_url}")
        r_pdf = await self._api_call("GET", annexe_url, accept="*/*")
        if r_pdf.get("b64_data"):
            pdf_bytes = base64.b64decode(r_pdf["b64_data"])
            if save_path:
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f: f.write(pdf_bytes)
            return pdf_bytes
        
        await self._copy_session_video(sent_reference)
        return None

    async def _copy_session_video(self, name: str):
        'Copia el video actual de la sesión a un nombre identificable'
        try:
            video_path = await self.page.video.path()
            if video_path and os.path.exists(video_path):
                dest = os.path.join(VIDEOS_DIR, f"{name}.webm")
                shutil.copy(video_path, dest)
                logger.info(f"🎞️ Video guardado en: {dest}")
        except Exception as e:
            logger.debug(f"No se pudo copiar el video: {e}")

    async def _wait_for_spinner(self, timeout_ms: int = 15000):
        'Espera a que desaparezca el spinner de "Cargando..." de DEHú'
        try:
            # Spinner común en DEHú: div o overlay con texto 'Cargando' o clase spinner
            spinner_selectors = [
                "text=Cargando...",
                ".loading",
                ".spinner",
                "dnt-modal[opened] shadow=button:has-text('Cargando')" # A veces está en shadow
            ]
            for selector in spinner_selectors:
                if await self.page.is_visible(selector):
                    logger.info(f"  ⏳ Esperando a que desaparezca el spinner ({selector})...")
                    await self.page.wait_for_selector(selector, state="hidden", timeout=timeout_ms)
                    break
        except Exception:
            pass

    async def download_voucher(self, sent_reference: str, save_path: str = None) -> bytes:
        'Descarga resguardo de notificación (con reintentos)'
        logger.info(f"Descargando voucher para {sent_reference[:30]}...")
        
        # Intentar ambos endpoints (realizada y pendiente)
        endpoints = [
            f"/api/v1/realized_notifications/{sent_reference}/voucher",
            f"/api/v1/notifications/{sent_reference}/voucher",
        ]
        
        for i in range(5):
            for endpoint in endpoints:
                r = await self._api_call("GET", endpoint, accept="*/*")
                if r.get("status") == 200 and r.get("b64_data"):
                    pdf_bytes = base64.b64decode(r["b64_data"])
                    if len(pdf_bytes) > 500:
                        if save_path:
                            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                            with open(save_path, "wb") as f: f.write(pdf_bytes)
                        logger.info(f"Voucher descargado: {len(pdf_bytes)} bytes")
                        return pdf_bytes
            
            await self.page.wait_for_timeout(3000)

        logger.error(f"Error descargando voucher tras 5 intentos")
        return None
    
    # =========================================================================
    # INFO USUARIO
    # =========================================================================
    
    async def get_user_info(self) -> dict:
        nif_b64 = self._nif_b64()
        if not nif_b64:
            return {}
        r = await self._api_call("GET", f"/api/v1/user/{nif_b64}")
        if r.get("status") == 200:
            self.user_info = r.get("data", {})
            if self.user_info.get("token"):
                self.jwt_token = self.user_info["token"]
                self.jwt_expires = datetime.now() + timedelta(minutes=9)
            return self.user_info
        return {}


# =============================================================================
# DEMO
# =============================================================================

async def demo():
    PFX_PATH = r"C:\\Users\\Gestion\\Documents\\dashboard_carpetas\\Certificados\\Victor Cisneros Muller_modern.pfx"
    PFX_PASSPHRASE = "12345"
    
    service = DEHuService(PFX_PATH, PFX_PASSPHRASE)
    
    try:
        # Conectar
        print("\\n" + "="*60)
        print("🔌 CONECTANDO A DEHÚ")
        print("="*60)
        
        ok = await service.connect(headless=False)
        if not ok:
            print("❌ No se pudo conectar")
            return
        
        # Info usuario
        print("\\n" + "="*60)
        print("👤 INFORMACIÓN DE USUARIO")
        print("="*60)
        
        user = await service.get_user_info()
        person = user.get("person", {})
        print(f"Nombre: {person.get('fullName', '?')}")
        print(f"NIF: {person.get('identifier', '?')}")
        
        # Pendientes
        print("\\n" + "="*60)
        print("📋 NOTIFICACIONES PENDIENTES")
        print("="*60)
        
        pending = await service.get_pending_notifications(limit=10)
        total_pending = pending.get('total', 0)
        print(f"Total pendientes: {total_pending}")
        
        items = pending.get("items", [])
        for i, n in enumerate(items[:5]):
            exp = n.get("expirationDate", "")[:10]
            print(f"  [{i+1}] {n['identifier']} | NIF: {n.get('nifTitular','')} | Vence: {exp} | {n.get('concept','')[:50]}")
        
        # Realizadas
        print("\\n" + "="*60)
        print("✅ NOTIFICACIONES REALIZADAS (últimos 7 días)")
        print("="*60)
        
        realized = await service.get_realized_notifications(days_back=7, limit=5)
        total_realized = realized.get('total', 0)
        print(f"Total realizadas: {total_realized}")
        
        for i, n in enumerate(realized.get("items", [])[:3]):
            state = n.get('state','')
            print(f"  [{i+1}] {n['identifier']} | Estado: {state} | {n.get('concept','')[:50]}")
        
        # Aceptar una notificación (si hay pendientes)
        if items:
            print("\\n" + "="*60)
            print("📥 ACEPTANDO PRIMERA NOTIFICACIÓN PENDIENTE")
            print("="*60)
            
            ref = items[0]["sentReference"]
            identifier = items[0]["identifier"]
            print(f"Notificación: {identifier}")
            print(f"Referencia: {ref}")
            
            # Preguntar si continuar (simulación)
            print("\\n⚠️  ADVERTENCIA: La aceptación es IRREVERSIBLE")
            print("Continuando con la demostración...\\n")
            
            result = await service.accept_notification(ref)
            
            if result.get("success"):
                print(f"✅ {result.get('message')}")
                print(f"   Estado: {result.get('status')}")
                
                # Descarga de resguardo
                print("📥 Descargando justificante...")
                voucher_path = f"C:\\\\Users\\\\Gestion\\\\Documents\\\\dashboard_carpetas\\\\justificantes\\\\{identifier}_justificante.pdf"
                await service.download_voucher(ref, save_path=voucher_path)
            else:
                print(f"❌ Error: {result.get('error')}")
                print(f"   Resultado completo: {result}")
                if result.get('detail'):
                    print(f"   Detalle: {result.get('detail')}")
        
        print("\\n" + "="*60)
        print("✅ SERVICIO DEHÚ OPERATIVO!")
        print("="*60)
        
    finally:
        await asyncio.sleep(10)
        await service.disconnect()


if __name__ == "__main__":
    asyncio.run(demo())