// screenmates' service worker: shows push notifications and brings the app up when one
// is tapped. It caches nothing on purpose – the app always comes fresh from the server.

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('push', (event) => {
  let d
  try {
    d = event.data ? event.data.json() : {}
  } catch {
    d = { text: event.data ? event.data.text() : '' }
  }
  event.waitUntil(
    self.registration.showNotification(d.titel || 'screenmates', {
      body: d.text || '',
      icon: '/icon-512.png',
      badge: '/favicon-32.png',
      tag: d.tag || undefined,
      renotify: Boolean(d.tag), // a newer message of the same kind replaces the old one, and still rings
      data: { url: d.url || '/#/abend' },
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const ziel = new URL(event.notification.data?.url || '/', self.location.origin).href
  event.waitUntil(
    (async () => {
      const fenster = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      const offen = fenster.find((c) => new URL(c.url).origin === self.location.origin)
      if (!offen) return self.clients.openWindow(ziel)
      await offen.focus()
      offen.postMessage({ typ: 'oeffnen', url: ziel }) // the app switches to the right page
    })(),
  )
})

// The push service replaced the subscription (keys expire now and then): tell the server.
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(
    (async () => {
      const alt = event.oldSubscription
      const neu =
        event.newSubscription ||
        (alt?.options && (await self.registration.pushManager.subscribe(alt.options)))
      if (!neu) return
      const j = neu.toJSON()
      await fetch('/api/push/abo', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: j.endpoint, keys: j.keys }),
      })
    })(),
  )
})