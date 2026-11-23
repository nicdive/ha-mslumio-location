/* Maison PWA — install-eligible worker. Do not proxy fetches:
   intercepting SSE/API under a site-wide scope broke the guest UI. */
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});
