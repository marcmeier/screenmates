const einsNachKomma = new Intl.NumberFormat('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** 4.66 -> "4,7": ratings everywhere look the same, with a German decimal comma. */
export function dezimal(x) {
  return x == null || Number.isNaN(x) ? '–' : einsNachKomma.format(x)
}

const dateFmt = new Intl.DateTimeFormat('de-DE', { day: 'numeric', month: 'short', year: 'numeric' })
const rel = new Intl.RelativeTimeFormat('de-DE', { numeric: 'auto' })

export function datum(iso) {
  return iso ? dateFmt.format(new Date(iso)) : ''
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
    if (Math.abs(value) < size) return rel.format(Math.round(value), unit)
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
