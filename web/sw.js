const CACHE = "daily-office-v14";
const PRECACHE = [
  "./",
  "./index.html",
  "./styles.css",
  "./manifest.webmanifest",
  "./js/app.js",
  "./js/bible.js",
  "./js/liturgical.js",
  "./js/confession.js",
  "./icons/icon.svg",
  "./data/lectionary.json",
  "./data/midday.json",
  "./data/compline.json",
  "./data/audio.json",
  "./data/sentences.json",
  "./data/confessions/corpus.json",
  "./data/confessions/westminster_daily.json",
  "./data/confessions/echoes.json",
  "./data/confessions/benedictions.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetched = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(event.request, copy));
          }
          return response;
        })
        .catch(() => cached);
      return cached || fetched;
    })
  );
});
