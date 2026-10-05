// How screenmates looks for you: a colour theme (always dark) and a font.
// Applied before the app mounts (from this device's last choice), then from your profile.

export const THEMES = {
  kino: { name: 'Kino', accent: '#e50914', hover: '#f6121e', bg: '#0a0a0c', soft: '#141419', raised: '#1b1b22', line: '#26262e' },
  nacht: { name: 'Nacht', accent: '#3b82f6', hover: '#5b9bff', bg: '#080b12', soft: '#0f1522', raised: '#172033', line: '#222c40' },
  neon: { name: 'Neon', accent: '#ff2bd6', hover: '#ff5ae0', bg: '#0b0812', soft: '#140f1f', raised: '#1d1630', line: '#2c2240' },
  wald: { name: 'Wald', accent: '#22c55e', hover: '#3ddc76', bg: '#070b09', soft: '#0f1612', raised: '#16201a', line: '#223027', auf: '#04140a' },
  bernstein: { name: 'Bernstein', accent: '#f59e0b', hover: '#ffb52e', bg: '#0c0a07', soft: '#17130d', raised: '#211b12', line: '#30281c', auf: '#1a1200' },
  violett: { name: 'Violett', accent: '#8b5cf6', hover: '#a17cff', bg: '#0a0912', soft: '#13111f', raised: '#1c1930', line: '#2a2640' },
  oled: { name: 'Schwarz', accent: '#f2f2f2', hover: '#ffffff', bg: '#000000', soft: '#0b0b0b', raised: '#151515', line: '#232323', auf: '#000000' },
}

export const SCHRIFTEN = {
  inter: { name: 'Inter', familie: "'Inter Variable'" },
  grotesk: { name: 'Space Grotesk', familie: "'Space Grotesk Variable'", laden: () => import('@fontsource-variable/space-grotesk') },
  lesbar: {
    name: 'Atkinson (gut lesbar)',
    familie: "'Atkinson Hyperlegible Next Variable'",
    laden: () => import('@fontsource-variable/atkinson-hyperlegible-next'),
  },
  serif: { name: 'Fraunces (Serif)', familie: "'Fraunces Variable'", laden: () => import('@fontsource-variable/fraunces') },
  rund: { name: 'Nunito (rund)', familie: "'Nunito Variable'", laden: () => import('@fontsource-variable/nunito') },
  mono: { name: 'JetBrains Mono', familie: "'JetBrains Mono Variable'", laden: () => import('@fontsource-variable/jetbrains-mono') },
  system: { name: 'Systemschrift', familie: '' },
}

const KEY = 'screenmates.design'
const FALLBACK = "system-ui, -apple-system, 'Segoe UI', sans-serif"

function rgba(hex, a) {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

export function anwenden(design = {}) {
  const t = THEMES[design.theme] || THEMES.kino
  const s = SCHRIFTEN[design.schrift] || SCHRIFTEN.inter
  const r = document.documentElement.style
  r.setProperty('--accent', t.accent)
  r.setProperty('--accent-hover', t.hover)
  r.setProperty('--accent-soft', rgba(t.accent, 0.14))
  r.setProperty('--on-accent', t.auf || '#ffffff')
  r.setProperty('--bg', t.bg)
  r.setProperty('--bg-soft', t.soft)
  r.setProperty('--bg-raised', t.raised)
  r.setProperty('--line', t.line)
  r.setProperty('--schrift', s.familie ? `${s.familie}, ${FALLBACK}` : FALLBACK)
  s.laden?.()
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', t.bg)
  try {
    localStorage.setItem(KEY, JSON.stringify({ theme: design.theme, schrift: design.schrift }))
  } catch {
    /* private mode: only for this visit */
  }
}

export function gemerkt() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {}
  } catch {
    return {}
  }
}
