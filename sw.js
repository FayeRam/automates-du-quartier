/* Service worker : garde le jeu et Python dans le téléphone pour jouer sans connexion.
   Change VERSION (ici ET dans app.js) à chaque mise à jour du site. */
const VERSION = "1.0.0";
const CACHE_JEU = "automates-jeu-" + VERSION;
const CACHE_PYTHON = "automates-pyodide";            // fichiers de Python (ne changent pas pour une version donnée)
const FICHIERS = [
  "./", "index.html", "style.css", "app.js", "manifest.webmanifest",
  "icones/icone-192.png", "icones/icone-512.png", "icones/apple-touch-icon.png",
  ...["moteur.py", "niveaux.py", "ladder.py", "grafcet.py", "dessins_svg.py", "pont.py"]
    .map((f) => "python/" + f + "?v=" + VERSION),
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE_JEU).then((c) => c.addAll(FICHIERS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((noms) => Promise.all(noms.filter((n) => n.startsWith("automates-jeu-") && n !== CACHE_JEU).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  // Python (Pyodide) : d'abord le cache, sinon Internet puis on garde une copie
  if (url.hostname === "cdn.jsdelivr.net") {
    e.respondWith(
      caches.open(CACHE_PYTHON).then(async (cache) => {
        const garde = await cache.match(e.request);
        if (garde) return garde;
        const reponse = await fetch(e.request);
        if (reponse.ok) cache.put(e.request, reponse.clone());
        return reponse;
      })
    );
    return;
  }

  // Le jeu : d'abord Internet (pour recevoir les mises à jour), sinon la copie gardée
  if (url.origin === self.location.origin) {
    e.respondWith(
      fetch(e.request)
        .then((reponse) => {
          if (reponse.ok) { const copie = reponse.clone(); caches.open(CACHE_JEU).then((c) => c.put(e.request, copie)); }
          return reponse;
        })
        .catch(() => caches.match(e.request, { ignoreSearch: false }).then((r) => r || caches.match("index.html")))
    );
  }
});
