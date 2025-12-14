/**
 * Service Worker for Prospect Command Center PWA
 * Provides basic offline support and caching
 */

const CACHE_NAME = 'prospect-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
];

// Install event - cache static assets
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME)
                    .map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// Fetch event - network first for API, cache first for static
self.addEventListener('fetch', (e) => {
    const url = new URL(e.request.url);

    // Network first for API calls
    if (url.pathname.startsWith('/api/')) {
        e.respondWith(
            fetch(e.request)
                .catch(() => {
                    // Return offline response for API failures
                    return new Response(
                        JSON.stringify({ error: 'Offline', message: 'You are currently offline' }),
                        { status: 503, headers: { 'Content-Type': 'application/json' } }
                    );
                })
        );
        return;
    }

    // Cache first for static assets
    e.respondWith(
        caches.match(e.request)
            .then(cached => cached || fetch(e.request))
    );
});
