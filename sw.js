// Netwerk eerst (zodat updates meteen binnenkomen), cache als je offline bent.
const C = "topo-v1";
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(C).then(c => c.addAll(["./", "./index.html", "./manifest.webmanifest", "./icon.svg"]).catch(() => {}))); });
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== "GET") return;
  const same = u.origin === location.origin, font = /fonts\.(googleapis|gstatic)\.com$/.test(u.hostname);
  if (!same && !font) return;
  if (u.pathname.endsWith("version.json")) return;
  e.respondWith(fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); } return res; })
    .catch(() => caches.match(r).then(m => m || (r.mode === "navigate" ? caches.match("./index.html") : Response.error()))));
});
