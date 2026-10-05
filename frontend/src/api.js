import { useUi } from './stores/ui'

/** Error thrown for every failed request. It has already been shown to the user. */
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function describe(status, body) {
  const detail = body?.detail
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc, msg, ...}]
    return 'Ungültige Eingabe: ' + detail.map((d) => d.msg).join(', ')
  }
  if (typeof detail === 'string') return detail
  if (status >= 500) return 'Der Server hat ein Problem. Bitte später nochmal versuchen.'
  return `Anfrage fehlgeschlagen (${status}).`
}

// Called after every successful write (achievements check whether something unlocked).
// Not for the Kino heartbeat, the door, or the achievements' own calls.
const nachSchreiben = new Set()
export function beiAenderung(fn) {
  nachSchreiben.add(fn)
}
const STILL = ['/api/kino/da', '/api/erfolge', '/api/zugang']

async function req(method, path, body, { signal, quiet = false } = {}) {
  const opts = { method, credentials: 'same-origin', headers: {}, signal }
  if (body instanceof Blob) {
    opts.headers['Content-Type'] = body.type || 'application/octet-stream'
    opts.body = body
  } else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(path, opts)
  } catch (e) {
    if (e.name === 'AbortError') throw e
    const err = new ApiError(0, 'Keine Verbindung zum Server.')
    if (!quiet) useUi().toast(err.message, 'error')
    throw err
  }

  const isJson = (res.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await res.json().catch(() => null) : await res.text()
  if (!res.ok) {
    const err = new ApiError(res.status, describe(res.status, data))
    const ui = useUi()
    if (res.status === 401) ui.loginOpen = true
    // 423: this browser lost its access (e.g. logged out everywhere) – back to the door.
    if (res.status === 423) window.location.reload()
    if (!quiet) ui.toast(err.message, 'error')
    throw err
  }
  if (method !== 'GET' && !STILL.some((p) => path.startsWith(p))) nachSchreiben.forEach((fn) => fn())
  return data
}

export const api = {
  get: (p, o) => req('GET', p, undefined, o),
  post: (p, b, o) => req('POST', p, b, o),
  put: (p, b, o) => req('PUT', p, b, o),
  patch: (p, b, o) => req('PATCH', p, b, o),
  del: (p, o) => req('DELETE', p, undefined, o),
}

export const qs = (params) =>
  new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ''),
  ).toString()
