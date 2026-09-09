const CACHE_NAME = "daily-goals-v2";
const APP_SHELL = [
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/app.js",
  "/static/app-ui.css",
  "/static/flashcards.js",
  "/static/lesson.js",
  "/static/reader.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never cache API calls or auth pages — always go to the network so data stays live.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/login") || url.pathname.startsWith("/register") || url.pathname.startsWith("/logout")) {
    return;
  }

  // App shell (static assets): cache-first for speed.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
    return;
  }

  // Pages (e.g. "/"): network-first, fall back to cache when offline.
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes("/flashcards") && "focus" in client) return client.focus();
      }
      return self.clients.openWindow("/flashcards");
    })
  );
});
