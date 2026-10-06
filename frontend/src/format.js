import { locale } from './i18n'

// Formatters follow the app's language (German or English); made once per language.
const cache = new Map()
function fmt(art, optionen) {
  const key = `${art}|${locale()}|${JSON.stringify(optionen)}`
  if (!cache.has(key)) cache.set(key, new Intl[art](locale(), optionen))
  return cache.get(key)
}
export const zahlFmt = (optionen = {}) => fmt('NumberFormat', optionen)
export const datumFmt = (optionen = {}) => fmt('DateTimeFormat', optionen)

/** 4.66 -> "4,7" (or "4.7"): ratings everywhere look the same. */
export function dezimal(x) {
  return x == null || Number.isNaN(x) ? '–' : zahlFmt({ minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(x)
}

export function zahl(x) {
  return zahlFmt().format(x ?? 0)
}

export function datum(iso) {
  return iso ? datumFmt({ day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso)) : ''
}

export function vorWann(iso) {
  if (!iso) return ''
  const sec = (new Date(iso).getTime() - Date.now()) / 1000
  const steps = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
    [4.35, 'week'],
    [12, 'month'],
    [Infinity, 'year'],
  ]
  let value = sec
  for (const [size, unit] of steps) {
    if (Math.abs(value) < size) return fmt('RelativeTimeFormat', { numeric: 'auto' }).format(Math.round(value), unit)
    value /= size
  }
  return ''
}

export function laufzeit(min) {
  if (!min) return ''
  const h = Math.floor(min / 60)
  return h ? `${h} h ${min % 60} min` : `${min} min`
}

export function initialen(name = '') {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

/** Debounce for search inputs. */
export function debounce(fn, ms = 300) {
  let t
  return (...args) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}
