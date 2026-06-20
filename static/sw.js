// Pebbles College Admin — Service Worker
// Strategy: Cache-first for static assets, network-first for pages

const CACHE_NAME = 'pebbles-admin-v1';
const STATIC_ASSETS = [
  '/login',
  '/static/css/style.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap'
];

// Install — pre-cache the app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('SW: Some assets failed to cache', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network-first for HTML pages, cache-first for static assets
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip chrome-extension or non-http requests
  if (!event.request.url.startsWith('http')) return;

  // For same-origin HTML navigation — network first, fall back to cache
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache the fresh response
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request).then(cached => cached || caches.match('/login')))
    );
    return;
  }

  // For static assets — cache first, then network
  if (
    url.pathname.startsWith('/static/') ||
    url.hostname.includes('cdnjs') ||
    url.hostname.includes('fonts.gstatic') ||
    url.hostname.includes('fonts.googleapis')
  ) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(response => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        });
      })
    );
  }
});
