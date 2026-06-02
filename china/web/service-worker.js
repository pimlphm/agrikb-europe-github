const AGRIKB_CACHE = "agrikb-pwa-20260525-v92";
const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./style.css?v=20260525agri93",
  "./app.js?v=20260525agri93",
  "./manifest.webmanifest",
  "./assets/mobile-wifi-qr.png",
  "./assets/new-farmer-icons/bureau.svg",
  "./assets/new-farmer-icons/company.svg",
  "./assets/new-farmer-icons/crop.svg",
  "./assets/new-farmer-icons/market.svg",
  "./assets/new-farmer-icons/new_farmer.svg",
  "./assets/new-farmer-icons/policy.svg",
  "./assets/new-farmer-icons/traceability.svg",
  "./assets/new-farmer-icons/weather.svg"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(AGRIKB_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== AGRIKB_CACHE).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith("/api/") || event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        const copy = response.clone();
        caches.open(AGRIKB_CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      });
    })
  );
});
