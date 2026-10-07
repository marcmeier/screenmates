// Wording for the year in review, shared by the overview and the story.
import { datumFmt, dezimal, zahl } from './format'
import { t } from './i18n'
import { zeitzone } from './zeitzone'

export const n = (x) => zahl(x)
export const stunden = (minuten) => Math.round(minuten / 60)
export const sterne = (x) => (x == null ? '–' : `${dezimal(x)} ★`)

// Each entry's name, always in the current language.
function benannt(art, liste) {
  return liste.map((x) => Object.defineProperty(x, 'name', { get: () => t(`rueckblick.${art}.${x.key}`) }))
}

// The friendly titles: label, what the number means, and an emoji.
export const TITEL = benannt('titel', [
  { key: 'stammgast', emoji: '🛋️', einheit: (w) => t('rueckblick.einheit.abende', { n: n(w) }, w) },
  { key: 'streng', emoji: '🧐', einheit: (w) => `Ø ${sterne(w)}` },
  { key: 'grosszuegig', emoji: '🌟', einheit: (w) => `Ø ${sterne(w)}` },
  { key: 'plaudertasche', emoji: '📖', einheit: (w) => t('rueckblick.einheit.kommentare', { n: n(w) }, w) },
  { key: 'herzensbrecher', emoji: '❤️', einheit: (w) => t('rueckblick.einheit.herzen', { n: n(w) }, w) },
  { key: 'trendsetter', emoji: '🎯', einheit: (w) => t('rueckblick.einheit.vorschlaege', { n: n(w) }, w) },
])

// Film highlights in the order they're shown.
export const FILME = benannt('film', [
  { key: 'bester', text: (f) => `Ø ${sterne(f.sterne)}` },
  { key: 'einig', text: (f) => t('rueckblick.text.alle', { sterne: sterne(f.sterne) }) },
  { key: 'umstritten', text: (f, name) => t('rueckblick.text.umstritten', { hoch: name(f.hoch), tief: name(f.tief) }) },
  { key: 'schlechtester', text: (f) => `Ø ${sterne(f.sterne)}` },
  { key: 'erster', text: (f) => datum(f.am) },
  { key: 'letzter', text: (f) => datum(f.am) },
  { key: 'laengster', text: (f) => t('rueckblick.text.minuten', { n: f.movie.runtime }) },
  { key: 'kuerzester', text: (f) => t('rueckblick.text.minuten', { n: f.movie.runtime }) },
  { key: 'aeltester', text: (f) => t('rueckblick.text.von', { jahr: f.movie.year }) },
])

export const datum = (iso) => datumFmt({ day: 'numeric', month: 'long', timeZone: zeitzone() }).format(new Date(iso))
// Month 1–12 and weekday 0 = Monday (as the server counts) in the current language.
export const monatName = (m) => datumFmt({ month: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2024, m.nr - 1, 15)))
export const wochentagName = (d) => datumFmt({ weekday: 'long', timeZone: 'UTC' }).format(new Date(Date.UTC(2024, 0, 1 + d.nr)))
