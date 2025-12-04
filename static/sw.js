const CACHE_NAME = 'credinet-v2';

const ASSETS_TO_CACHE = [
  '/', 
  '/templates/homeshell.html',                               // Ruta principal -> Flask responde index
  '/static/manifest.json',            // Manifest correcto
  '/static/sw.js',                    // Service Worker
  '/static/icons/icono-credinet.jpeg' // Ícono PWA
];

// --- INSTALACIÓN ---
self.addEventListener('install', event => {
  console.log('🛠️ Instalando Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('📦 Cacheando rutas:', ASSETS_TO_CACHE);
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// --- ACTIVACIÓN ---
self.addEventListener('activate', event => {
  console.log('🚀 Activando Service Worker...');
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

// --- FETCH ---
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        console.log('📡 No está en cache, buscando:', event.request.url);
        return fetch(event.request);
      })
  );
});
