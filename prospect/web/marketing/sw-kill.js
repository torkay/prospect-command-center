/*
  Root scope service worker kill-switch.

  If an older version of the app registered a PWA service worker at /sw.js (scope: /),
  that SW can keep controlling the marketing homepage at /. This script deletes caches
  and unregisters itself on activation.

  Note: The LeadSwarm product app registers its own SW at /app/sw.js (scope: /app/).
*/

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.map((k) => caches.delete(k)));
    } catch {
      // ignore
    }

    try {
      await self.registration.unregister();
    } catch {
      // ignore
    }

    try {
      const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of clients) {
        try { await client.navigate(client.url); } catch { /* ignore */ }
      }
    } catch {
      // ignore
    }
  })());
});

// Pass-through; this SW exists only to self-destruct.
self.addEventListener('fetch', () => {});
