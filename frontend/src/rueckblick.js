// Wording for the year in review, shared by the overview and the story.

const zahl = new Intl.NumberFormat('de-DE')
export const n = (x) => zahl.format(x)
export const stunden = (minuten) => Math.round(minuten / 60)
export const sterne = (x) => (x == null ? '–' : `${String(x).replace('.', ',')} ★`)

// The friendly titles: label, what the number means, and an emoji.
export const TITEL = [
  { key: 'stammgast', name: 'Stammgast', emoji: '🛋️', einheit: (w) => `${n(w)} ${w === 1 ? 'Abend' : 'Abende'} dabei` },
  { key: 'streng', name: 'Strengste Kritik', emoji: '🧐', einheit: (w) => `Ø ${sterne(w)}` },
  { key: 'grosszuegig', name: 'Großzügigste Sterne', emoji: '🌟', einheit: (w) => `Ø ${sterne(w)}` },
  { key: 'plaudertasche', name: 'Plaudertasche', emoji: '📖', einheit: (w) => `${n(w)} ${w === 1 ? 'Kommentar' : 'Kommentare'}` },
  { key: 'herzensbrecher', name: 'Herzensbrecher', emoji: '❤️', einheit: (w) => `${n(w)} ${w === 1 ? 'Herz' : 'Herzen'} bekommen` },
  { key: 'trendsetter', name: 'Trendsetter', emoji: '🎯', einheit: (w) => `${n(w)} ${w === 1 ? 'Vorschlag' : 'Vorschläge'} geschaut` },
]

// Film highlights in the order they're shown.
export const FILME = [
  { key: 'bester', name: 'Euer bester Film', text: (f) => `Ø ${sterne(f.sterne)}` },
  { key: 'einig', name: 'Da wart ihr euch einig', text: (f) => `alle ${sterne(f.sterne)}` },
  { key: 'umstritten', name: 'Der umstrittenste', text: (f, name) => `${name(f.hoch)} liebte ihn, ${name(f.tief)} eher nicht` },
  { key: 'schlechtester', name: 'Lieber vergessen', text: (f) => `Ø ${sterne(f.sterne)}` },
  { key: 'erster', name: 'Der erste des Jahres', text: (f) => datum(f.am) },
  { key: 'letzter', name: 'Der letzte bisher', text: (f) => datum(f.am) },
  { key: 'laengster', name: 'Sitzfleisch', text: (f) => `${f.movie.runtime} Minuten` },
  { key: 'kuerzester', name: 'Schnell durch', text: (f) => `${f.movie.runtime} Minuten` },
  { key: 'aeltester', name: 'Ältester Film', text: (f) => `von ${f.movie.year}` },
]

const tag = new Intl.DateTimeFormat('de-DE', { day: 'numeric', month: 'long', timeZone: 'Europe/Berlin' })
export const datum = (iso) => tag.format(new Date(iso))