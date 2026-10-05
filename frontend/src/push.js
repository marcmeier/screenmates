import { api } from './api'

// Push notifications on this device: the browser side of backend/app/push.py.
// The service worker (public/sw.js) shows what arrives.

export const pushMoeglich = () => 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
export const istIos = () =>
  /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
export const installiert = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true

/** Register the service worker once at start (notifications and the home-screen app need it). */
export function registrieren() {
  if (!('serviceWorker' in navigator)) return
  navigator.serviceWorker.register('/sw.js').catch(() => {})
  // A tapped notification while the app is open: go to the page it is about.
  navigator.serviceWorker.addEventListener('message', (e) => {
    if (e.data?.typ !== 'oeffnen') return
    const url = new URL(e.data.url)
    if (url.origin === location.origin && url.hash) location.hash = url.hash
  })
}

function bytes(b64) {
  const roh = atob((b64 + '='.repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(roh, (c) => c.charCodeAt(0))
}

function gleich(a, b) {
  if (!a) return false
  const x = new Uint8Array(a)
  return x.length === b.length && x.every((v, i) => v === b[i])
}

export function geraetName() {
  const ua = navigator.userAgent
  const browser = /Edg\//.test(ua) ? 'Edge' : /Firefox\//.test(ua) ? 'Firefox' : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : 'Browser'
  const system = /Android/.test(ua) ? 'Android' : istIos() ? 'iOS' : /Mac OS X/.test(ua) ? 'macOS' : /Windows/.test(ua) ? 'Windows' : /Linux/.test(ua) ? 'Linux' : ''
  return system ? `${browser} auf ${system}` : browser
}

export async function aboHier() {
  if (!pushMoeglich()) return null
  const reg = await navigator.serviceWorker.getRegistration()
  return reg ? reg.pushManager.getSubscription() : null
}

/** Ask for permission, subscribe this device and tell the server. Returns the server's push state. */
export async function einschalten(schluessel) {
  const erlaubnis = await Notification.requestPermission()
  if (erlaubnis !== 'granted') {
    throw new Error(
      erlaubnis === 'denied'
        ? 'Benachrichtigungen sind für screenmates blockiert – erlaube sie in den Website-Einstellungen des Browsers.'
        : 'Ohne deine Erlaubnis gibt es keine Benachrichtigungen.',
    )
  }
  const reg = (await navigator.serviceWorker.getRegistration()) || (await navigator.serviceWorker.register('/sw.js'))
  await navigator.serviceWorker.ready
  const key = bytes(schluessel)
  let abo = await reg.pushManager.getSubscription()
  // Subscribed for another server key (e.g. a reinstalled server): that one can't reach us.
  if (abo && !gleich(abo.options?.applicationServerKey, key)) {
    await abo.unsubscribe()
    abo = null
  }
  abo ||= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: key })
  const j = abo.toJSON()
  return api.post('/api/push/abo', { endpoint: j.endpoint, keys: j.keys, geraet: geraetName() })
}

/** This device gets no more notifications. Returns the server's push state (or null). */
export async function ausschalten({ quiet = false } = {}) {
  const abo = await aboHier()
  if (!abo) return null
  const r = await api.post('/api/push/abmelden', { endpoint: abo.endpoint }, { quiet }).catch(() => null)
  await abo.unsubscribe().catch(() => {})
  return r
}