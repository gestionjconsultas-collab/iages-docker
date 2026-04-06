"""
DEHú API Endpoint Discovery
Intercepta todas las llamadas a /api/ mientras navega la UI
para descubrir endpoints de detalle, aceptar, descargar, etc.
"""
import asyncio
import json
import shutil
import os
from playwright.async_api import async_playwright

PFX_PATH = r"C:\Users\Gestion\Documents\dashboard_carpetas\Certificados\Victor Cisneros Muller_modern.pfx"
PFX_PASSPHRASE = "12345"
CERT_CONFIG = {"pfxPath": PFX_PATH, "passphrase": PFX_PASSPHRASE}
SESSION_DIR = "./tmp-dehu-session"

# Almacén de endpoints descubiertos
discovered_endpoints = []


async def discover_dehu():
    jwt_token = None
    
    if os.path.exists(SESSION_DIR):
        shutil.rmtree(SESSION_DIR, ignore_errors=True)
    
    print("🔑 Iniciando Playwright...")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            client_certificates=[
                {"origin": "https://dehu.redsara.es", **CERT_CONFIG},
                {"origin": "https://pasarela.clave.gob.es", **CERT_CONFIG},
                {"origin": "https://pasarela-ident.clave.gob.es", **CERT_CONFIG},
            ]
        )
        page = context.pages[0]
        
        # === INTERCEPTAR TODAS LAS PETICIONES API ===
        def on_request(request):
            url = request.url
            if "/api/" in url and "dehu.redsara.es" in url:
                method = request.method
                headers = dict(request.headers)
                post_data = request.post_data
                entry = {
                    "method": method,
                    "url": url,
                    "auth": "Bearer" if "authorization" in headers else "No auth",
                    "content_type": headers.get("content-type", ""),
                    "post_data": post_data[:500] if post_data else None,
                }
                discovered_endpoints.append(entry)
                print(f"   🔵 {method} {url[:120]}")
                if post_data:
                    print(f"      📦 Body: {post_data[:300]}")
        
        def on_response(response):
            url = response.url
            if "/api/" in url and "dehu.redsara.es" in url:
                status = response.status
                content_type = response.headers.get("content-type", "")
                # Marcar el endpoint con su status
                for ep in reversed(discovered_endpoints):
                    if ep["url"] == url:
                        ep["status"] = status
                        ep["response_type"] = content_type
                        break
                symbol = "✅" if status == 200 else "⚠️"
                print(f"   {symbol} {status} ← {url[:100]} [{content_type[:30]}]")
        
        page.on("request", on_request)
        page.on("response", on_response)
        
        # === CAPTURAR JWT ===
        def on_navigate(frame):
            nonlocal jwt_token
            if "authData=" in frame.url:
                jwt_token = frame.url.split("authData=")[1]
                print(f"   🎯 JWT CAPTURADO!")
        
        page.on("framenavigated", on_navigate)
        
        # === LOGIN ===
        print("🌐 Navegando a DEHú...")
        await page.goto("https://dehu.redsara.es")
        await page.wait_for_timeout(3000)
        
        if "/es/public" in page.url:
            print("🔍 Click en 'Acceder'...")
            try:
                await page.evaluate("document.querySelector('dnt-modal')?.remove()")
            except: pass
            try:
                await page.evaluate("""
                    const btns = document.querySelectorAll('dnt-button, button, a');
                    for (const b of btns) {
                        if (b.textContent.includes('Acceder')) { b.click(); break; }
                    }
                """)
            except: pass
        
        print("⏳ Esperando autenticación...")
        for i in range(90):
            if jwt_token: break
            await page.wait_for_timeout(1000)
            if i % 10 == 0 and i > 0:
                print(f"   ... {i} seg")
        
        if not jwt_token:
            print("❌ No se pudo autenticar")
            await context.close()
            return
        
        try:
            await page.wait_for_url("**/home**", timeout=15000)
        except: pass
        await page.wait_for_timeout(3000)
        print(f"\n✅ Autenticado! URL: {page.url}")
        
        # =============================================
        # FASE 1: Capturar lo que carga el home
        # =============================================
        print("\n" + "="*60)
        print("📡 FASE 1: Endpoints del HOME (carga inicial)")
        print("="*60)
        await page.wait_for_timeout(3000)
        
        # =============================================
        # FASE 2: Click en primera notificación pendiente
        # =============================================
        print("\n" + "="*60)
        print("📡 FASE 2: Click en primera notificación (detalle)")
        print("="*60)
        
        # Buscar y clickear la primera notificación en la lista
        clicked = await page.evaluate("""
            () => {
                // Buscar enlaces o filas clickeables de notificaciones
                const candidates = [
                    ...document.querySelectorAll('tr[class*="notif"], div[class*="notif"], a[href*="notif"]'),
                    ...document.querySelectorAll('tr.clickable, tr[role="row"], tbody tr'),
                    ...document.querySelectorAll('[class*="notification"] a, [class*="notification"] tr'),
                    ...document.querySelectorAll('dnt-table-row, dnt-row'),
                ];
                if (candidates.length > 0) {
                    candidates[0].click();
                    return 'clicked: ' + candidates[0].tagName + '.' + candidates[0].className;
                }
                // Intentar con cualquier enlace que tenga referencia a notificación
                const links = document.querySelectorAll('a[href*="notification"], a[href*="detail"]');
                if (links.length > 0) {
                    links[0].click();
                    return 'clicked link: ' + links[0].href;
                }
                return 'no_candidates_found';
            }
        """)
        print(f"   Click result: {clicked}")
        await page.wait_for_timeout(5000)
        
        # Si no funcionó el click automático, intentar navegar directamente
        if "no_candidates" in clicked:
            print("   ⚠️ No se encontró elemento clickeable. Buscando en DOM...")
            dom_info = await page.evaluate("""
                () => {
                    const all = document.querySelectorAll('*');
                    const interesting = [];
                    for (const el of all) {
                        const text = el.textContent?.substring(0, 50) || '';
                        const tag = el.tagName;
                        const cls = el.className?.toString()?.substring(0, 50) || '';
                        if (text.includes('N273') || cls.includes('notif') || cls.includes('table') || cls.includes('row')) {
                            interesting.push(`${tag}.${cls} = ${text.substring(0,60)}`);
                        }
                    }
                    return interesting.slice(0, 30);
                }
            """)
            for item in dom_info:
                print(f"      {item}")
        
        # =============================================
        # FASE 3: Intentar navegar al detalle via URL
        # =============================================
        print("\n" + "="*60)
        print("📡 FASE 3: Navegar a detalle de notificación via URL")
        print("="*60)
        
        # Primero obtener una notificación real
        import base64
        r = await page.evaluate(f"""
            async () => {{
                const r = await fetch("/api/v1/notifications?page=1&limit=3", {{
                    headers: {{
                        "Accept": "application/json",
                        "Authorization": "Bearer {jwt_token}"
                    }},
                    credentials: "same-origin"
                }});
                return await r.json();
            }}
        """)
        
        if r and r.get("items"):
            first_notif = r["items"][0]
            notif_id = first_notif.get("identifier", "")
            sent_ref = first_notif.get("sentReference", "")
            nif = first_notif.get("nifTitular", "")
            print(f"\n   📋 Notificación: {notif_id}")
            print(f"   📋 sentReference: {sent_ref}")
            print(f"   📋 NIF titular: {nif}")
            print(f"   📋 Concepto: {first_notif.get('concept', '')[:80]}")
            print(f"   📋 Todos los campos: {json.dumps(first_notif, ensure_ascii=False)[:600]}")
            
            # Probar varias URLs posibles de detalle
            print("\n   🔍 Probando endpoints de detalle...")
            
            test_urls = [
                f"/api/v1/notifications/{sent_ref}",
                f"/api/v1/notifications/{notif_id}",
                f"/api/v1/notification/{sent_ref}",
                f"/api/v1/notification/{notif_id}",
                f"/api/v1/notifications/{sent_ref}/detail",
                f"/api/v1/notifications/{notif_id}/detail",
                f"/api/v1/notifications/detail/{sent_ref}",
            ]
            
            for test_url in test_urls:
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch("{test_url}", {{
                                headers: {{
                                    "Accept": "application/json",
                                    "Authorization": "Bearer {jwt_token}"
                                }},
                                credentials: "same-origin"
                            }});
                            const text = await r.text();
                            return {{ status: r.status, body: text.substring(0, 400) }};
                        }} catch(e) {{
                            return {{ status: 0, error: e.message }};
                        }}
                    }}
                """)
                status = result['status']
                symbol = "✅" if status == 200 else "❌" if status >= 400 else "⚠️"
                print(f"   {symbol} {status} GET {test_url}")
                if status == 200:
                    print(f"      📦 {result['body'][:300]}")
            
            # Probar endpoints de aceptar/comparecer
            print("\n   🔍 Probando endpoints de aceptar...")
            accept_urls = [
                ("PUT", f"/api/v1/notifications/{sent_ref}/accept"),
                ("POST", f"/api/v1/notifications/{sent_ref}/accept"),
                ("PUT", f"/api/v1/notifications/{sent_ref}"),
                ("PATCH", f"/api/v1/notifications/{sent_ref}"),
                ("PUT", f"/api/v1/notification/{sent_ref}/accept"),
                ("POST", f"/api/v1/notification/{sent_ref}/accept"),
            ]
            
            for method, test_url in accept_urls:
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch("{test_url}", {{
                                method: "{method}",
                                headers: {{
                                    "Accept": "application/json",
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer {jwt_token}"
                                }},
                                credentials: "same-origin"
                            }});
                            const text = await r.text();
                            return {{ status: r.status, body: text.substring(0, 400) }};
                        }} catch(e) {{
                            return {{ status: 0, error: e.message }};
                        }}
                    }}
                """)
                status = result['status']
                symbol = "✅" if status == 200 else "⚠️" if status < 400 else "❌"
                print(f"   {symbol} {status} {method} {test_url[:80]}")
                if status < 400:
                    print(f"      📦 {result['body'][:300]}")
            
            # Probar endpoints de descarga PDF
            print("\n   🔍 Probando endpoints de descarga...")
            download_urls = [
                f"/api/v1/notifications/{sent_ref}/document",
                f"/api/v1/notifications/{sent_ref}/pdf",
                f"/api/v1/notifications/{sent_ref}/download",
                f"/api/v1/notifications/{sent_ref}/content",
                f"/api/v1/notifications/{sent_ref}/file",
                f"/api/v1/notifications/{sent_ref}/receipt",
                f"/api/v1/notifications/{sent_ref}/resguardo",
                f"/api/v1/notification/{sent_ref}/document",
            ]
            
            for test_url in download_urls:
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch("{test_url}", {{
                                headers: {{
                                    "Accept": "*/*",
                                    "Authorization": "Bearer {jwt_token}"
                                }},
                                credentials: "same-origin"
                            }});
                            const ct = r.headers.get('content-type') || '';
                            const text = ct.includes('json') ? await r.text() : ct + ' (' + r.headers.get('content-length') + ' bytes)';
                            return {{ status: r.status, body: text.substring(0, 400), content_type: ct }};
                        }} catch(e) {{
                            return {{ status: 0, error: e.message }};
                        }}
                    }}
                """)
                status = result['status']
                symbol = "✅" if status == 200 else "⚠️" if status < 400 else "❌"
                ct = result.get('content_type', '')
                print(f"   {symbol} {status} GET {test_url[:80]} [{ct[:30]}]")
                if status == 200:
                    print(f"      📦 {result['body'][:300]}")
        
        # =============================================
        # FASE 4: Navegar via UI y capturar requests
        # =============================================
        print("\n" + "="*60)
        print("📡 FASE 4: Navegar a notificación via UI (Angular routing)")
        print("="*60)
        
        # Intentar navegar a la ruta Angular del detalle
        angular_routes = [
            f"https://dehu.redsara.es/es/notification/{sent_ref}" if r and r.get("items") else None,
            f"https://dehu.redsara.es/es/notifications/{sent_ref}" if r and r.get("items") else None,
            f"https://dehu.redsara.es/es/detail/{sent_ref}" if r and r.get("items") else None,
        ]
        
        for route in angular_routes:
            if not route:
                continue
            print(f"\n   🌐 Navegando a: {route[:80]}")
            try:
                await page.goto(route, timeout=10000)
                await page.wait_for_timeout(3000)
                current = page.url
                print(f"   → Redirigió a: {current[:80]}")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")
        
        # =============================================
        # RESUMEN
        # =============================================
        print("\n" + "="*60)
        print("📊 RESUMEN: Todos los endpoints descubiertos")
        print("="*60)
        
        seen = set()
        for ep in discovered_endpoints:
            key = f"{ep['method']} {ep['url']}"
            if key not in seen:
                seen.add(key)
                status = ep.get('status', '?')
                print(f"   {ep['method']:6s} {status} {ep['url'][:120]}")
        
        print(f"\n   Total endpoints únicos: {len(seen)}")
        
        # Guardar resultados
        with open("dehu_endpoints.json", "w", encoding="utf-8") as f:
            json.dump(discovered_endpoints, f, indent=2, ensure_ascii=False)
        print("\n   💾 Guardado en dehu_endpoints.json")
        
        print("\n⏳ Navegador abierto 30seg para inspección manual...")
        await page.wait_for_timeout(30000)
        await context.close()


if __name__ == "__main__":
    asyncio.run(discover_dehu())
