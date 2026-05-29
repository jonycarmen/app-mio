// APP MIO — Service Worker v1
// Permite instalar la app en móvil y funcionar offline básico

const CACHE = 'app-mio-v1';

// Archivos propios a pre-cachear al instalar
const PRECACHE = [
  '/app-mio/',
  '/app-mio/index.html',
  '/app-mio/usuario.html',
  '/app-mio/manifest-admin.json',
  '/app-mio/manifest-user.json',
  '/app-mio/icons/icon-192.png',
  '/app-mio/icons/icon-512.png',
  '/app-mio/icons/user-192.png',
  '/app-mio/icons/user-512.png',
];

// Dominios externos que siempre van a la red (Firebase, CDNs)
const NETWORK_ONLY = [
  'firebase',
  'googleapis',
  'gstatic',
  'jsdelivr',
  'cdnjs',
  'sheetjs',
  'jspdf',
  'bootstrapcdn',
  'wa.me',
];

// ── INSTALL ──────────────────────────────────────────────────
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(PRECACHE))
      .catch(() => {}) // no bloquear si falla algún recurso
  );
  self.skipWaiting();
});

// ── ACTIVATE — limpiar caches viejas ─────────────────────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// ── FETCH ────────────────────────────────────────────────────
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = e.request.url;

  // Recursos externos → solo red
  if (NETWORK_ONLY.some(d => url.includes(d))) return;

  // Recursos propios → caché primero, luego red
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (response && response.ok && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return response;
      }).catch(() => cached); // sin conexión → devuelve caché si existe
    })
  );
});
