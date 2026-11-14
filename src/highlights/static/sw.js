// Offline shell: static files from cache, pages from the network with a cached fallback.
const CACHE = "highlights-v1";
const SCOPE = self.registration.scope;
const SHELL = ["static/app.css?v=1", "static/app.js?v=1", "static/icon-192.png"].map((p) => SCOPE + p);

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.includes("/api/") || url.pathname.endsWith("/video")) return;
  if (url.pathname.includes("/static/") || url.pathname.includes("/thumb/")) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
        return res;
      })),
    );
    return;
  }
  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); return res; })
        .catch(() => caches.match(req).then((hit) => hit || new Response(
          "<!doctype html><meta name=viewport content='width=device-width'><title>Offline</title>" +
          "<body style='font-family:system-ui;padding:24px'><h1>Can't reach Highlights</h1>" +
          "<p>Check your connection to the server, then pull to refresh.</p></body>",
          { headers: { "Content-Type": "text/html" } },
        ))),
    );
  }
});
