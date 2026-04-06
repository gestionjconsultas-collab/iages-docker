const APP_VERSION = '1.4.7'; // 👈 Incrementa esto en cada deploy
const CACHE_NAME = `iages-v${APP_VERSION}`;
const RUNTIME_CACHE = `iages-runtime-v${APP_VERSION}`;

// Archivos esenciales para cachear durante la instalación
const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/favicon.png'
];

// Instalación del Service Worker
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Precaching app shell');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activación del Service Worker
self.addEventListener('activate', (event) => {
    console.log(`[SW v${APP_VERSION}] Activating Service Worker...`);

    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => {
                        // Eliminar cachés antiguos
                        return cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE;
                    })
                    .map((cacheName) => {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    })
            );
        }).then(() => {
            console.log(`[SW v${APP_VERSION}] Activated and claiming clients...`);
            return self.clients.claim();
        })
    );
});

// Estrategia de caché MEJORADA: Network First con fallback
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignorar peticiones que no sean GET
    if (request.method !== 'GET') {
        return;
    }

    // Ignorar peticiones a APIs externas
    if (!url.origin.includes('localhost') && !url.origin.includes(self.location.origin)) {
        return;
    }

    // ⭐ NO CACHEAR archivos JS/CSS/JSON - siempre fresh (Network First)
    if (url.pathname.endsWith('.js') ||
        url.pathname.endsWith('.css') ||
        url.pathname.endsWith('.json') ||
        url.pathname.includes('chunk-') ||
        url.pathname.includes('assets/')) {

        event.respondWith(
            fetch(request).catch(() => {
                // Solo si falla la red, intentar caché
                return caches.match(request);
            })
        );
        return;
    }
    // Estrategia Network First para APIs
    if (url.pathname.startsWith('/api/')) {
        // NO cachear banners - siempre fresh
        if (url.pathname.includes('/banners/')) {
            event.respondWith(fetch(request));
            return;
        }

        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cachear respuestas exitosas
                    if (response.status === 200) {
                        const responseClone = response.clone();
                        caches.open(RUNTIME_CACHE).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return response;
                })
                .catch(() => {
                    // Si falla la red, intentar desde caché
                    return caches.match(request).then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // Si no hay caché, devolver respuesta offline
                        return new Response(
                            JSON.stringify({
                                success: false,
                                error: 'Sin conexión a internet',
                                offline: true
                            }),
                            {
                                status: 503,
                                headers: { 'Content-Type': 'application/json' }
                            }
                        );
                    });
                })
        );
        return;
    }

    // Estrategia Cache First para assets estáticos
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return fetch(request).then((response) => {
                // No cachear respuestas que no sean 200
                if (!response || response.status !== 200 || response.type === 'error') {
                    return response;
                }

                const responseClone = response.clone();
                caches.open(RUNTIME_CACHE).then((cache) => {
                    cache.put(request, responseClone);
                });

                return response;
            });
        })
    );
});

// Escuchar mensajes del cliente
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// ==========================================
// BACKGROUND SYNC - Sincronización en segundo plano
// ==========================================

// Cola de peticiones fallidas
const SYNC_QUEUE = 'sync-queue';

// Interceptar peticiones POST/PUT/DELETE que fallen
self.addEventListener('fetch', (event) => {
    const { request } = event;

    // Solo para peticiones de modificación
    if (!['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method)) {
        return;
    }

    event.respondWith(
        fetch(request.clone())
            .catch(async (error) => {
                // Si falla, guardar en IndexedDB para Background Sync
                console.log('[SW] Request failed, queuing for sync:', request.url);

                // Clonar request para guardar
                const requestClone = request.clone();
                const body = await requestClone.text();

                // Guardar en IndexedDB
                const db = await openSyncDB();
                const tx = db.transaction(SYNC_QUEUE, 'readwrite');
                const store = tx.objectStore(SYNC_QUEUE);

                await store.add({
                    url: request.url,
                    method: request.method,
                    headers: Object.fromEntries(request.headers.entries()),
                    body: body,
                    timestamp: Date.now()
                });

                // Registrar sync si está disponible
                if ('sync' in self.registration) {
                    await self.registration.sync.register('sync-requests');
                }

                // Devolver respuesta indicando que se guardó para sync
                return new Response(
                    JSON.stringify({
                        success: false,
                        error: 'Sin conexión. La acción se sincronizará cuando vuelva la conexión.',
                        queued: true
                    }),
                    {
                        status: 202, // Accepted
                        headers: { 'Content-Type': 'application/json' }
                    }
                );
            })
    );
});

// Evento de Background Sync
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-requests') {
        event.waitUntil(syncQueuedRequests());
    }
});

// Función para sincronizar peticiones en cola
async function syncQueuedRequests() {
    console.log('[SW] Syncing queued requests...');

    const db = await openSyncDB();
    const tx = db.transaction(SYNC_QUEUE, 'readonly');
    const store = tx.objectStore(SYNC_QUEUE);
    const requests = await store.getAll();

    for (const req of requests) {
        try {
            // Reintentar la petición
            const response = await fetch(req.url, {
                method: req.method,
                headers: req.headers,
                body: req.body
            });

            if (response.ok) {
                // Si fue exitosa, eliminar de la cola
                const deleteTx = db.transaction(SYNC_QUEUE, 'readwrite');
                const deleteStore = deleteTx.objectStore(SYNC_QUEUE);
                await deleteStore.delete(req.id);

                console.log('[SW] Request synced successfully:', req.url);

                // Notificar al cliente
                const clients = await self.clients.matchAll();
                clients.forEach(client => {
                    client.postMessage({
                        type: 'SYNC_SUCCESS',
                        url: req.url
                    });
                });
            }
        } catch (error) {
            console.error('[SW] Sync failed for:', req.url, error);
        }
    }
}

// Abrir base de datos IndexedDB para sync
function openSyncDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('iages-sync', 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(SYNC_QUEUE)) {
                const store = db.createObjectStore(SYNC_QUEUE, {
                    keyPath: 'id',
                    autoIncrement: true
                });
                store.createIndex('timestamp', 'timestamp', { unique: false });
            }
        };
    });
}

// ==========================================
// PUSH NOTIFICATIONS
// ==========================================

self.addEventListener('push', (event) => {
    console.log(`[SW v${APP_VERSION}] Push Received:`, event);

    if (!event.data) {
        console.warn(`[SW v${APP_VERSION}] Push event received but data is empty.`);
        return;
    }

    try {
        const data = event.data.json();
        console.log('[SW] Push content:', data);

        const title = data.title || 'Nueva Notificación';
        const options = {
            body: data.body || 'Tienes un nuevo mensaje en IAGES',
            icon: data.icon || '/favicon.png',
            badge: data.badge || '/notification-badge.png',
            vibrate: [100, 50, 100],
            data: {
                url: data.data?.url || data.link || '/', // Soportar ambos formatos
                type: data.data?.type || 'general'
            },
            actions: data.actions || []
        };

        event.waitUntil(
            self.registration.showNotification(title, options)
        );
    } catch (e) {
        console.error('[SW] Error parsing push data:', e);

        // Fallback si no es JSON
        event.waitUntil(
            self.registration.showNotification('Nueva Notificación', {
                body: event.data.text()
            })
        );
    }
});

// Manejar clic en la notificación
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification Clicked:', event.notification.data);

    event.notification.close();

    const targetUrl = event.notification.data?.url || event.notification.data?.link || '/';

    // Abrir la app o enfocar una pestaña existente
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            // Resolver URL relativa a absoluta si es necesario
            const absoluteUrl = new URL(targetUrl, self.location.origin).href;

            // Si ya hay una pestaña abierta con la app, enfocarla
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    // Si la URL es diferente, navegar a la nueva página
                    if (client.url !== absoluteUrl && 'navigate' in client) {
                        client.navigate(absoluteUrl);
                    }
                    return client.focus();
                }
            }
            // Si no, abrir una nueva
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});
