self.addEventListener("install", e => {
  console.log("Service Worker installed");
  e.waitUntil(
    caches.open("bassam-cache").then(cache => {
      return cache.addAll(["/"]);
    })
  );
});

self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(response => {
      return response || fetch(e.request);
    })
  );
});
