// APP MIO — Service Worker v2
// v2: HTML en network-first para recibir siempre el código más reciente

const CACHE = 'app-mio-v2';

// Archivos estáticos (iconos, manifests) — cache-first
const PRECACHE = [
  '/app-mio/manifest-admin.json',
  '/app-mio/manifest-user.json',
  '/app-mio/icons/icon-192.png',
  '/app-mio/icons/icon-512.png',
  '/app-mio/icons/user-192.png',
  '/app-mio/icons/user-512.png',
];

// Archivos HTML — network-first (siempre la versión más reciente)
const NETWORK_FIRST = [
  '/app-mio/',
  '/app-mio/index.html',
  '/app-mio/usuario.html',
];

// Dominios externos → siempre red
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
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).catch(() => {})
  );
  self.skipWaiting();
});

// ── ACTIVATE — limpiar caches antiguas ───────────────────────
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

  // Recursos externos → solo red, sin interceptar
  if (NETWORK_ONLY.some(d => url.includes(d))) return;

  // HTML → network-first (código siempre actualizado)
  const isHtml = NETWORK_FIRST.some(p => url.endsWith(p) || url.includes(p));
  if (isHtml) {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(CACHE).then(c => c.put(e.request, clone));
          }
          return res;
        })
        .catch(() => caches.match(e.request)) // sin red → caché como fallback
    );
    return;
  }

  // Resto → cache-first
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(res => {
        if (res && res.ok && res.type === 'basic') {
          caches.open(CACHE).then(c => c.put(e.request, res.clone()));
        }
        return res;
      }).catch(() => cached);
    })
  );
});
