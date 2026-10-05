import { ref } from 'vue'

// Minimal hash router: "#/finden/person/42" -> { tab: 'finden', sub: 'person', id: '42' }.
// Keeps the current view across reloads and makes views linkable, without a dependency.

// Old flat tabs (before the navigation was regrouped) still resolve.
const ALIASES = {
  entdecken: ['finden'],
  suche: ['finden'],
  ki: ['finden'],
  personen: ['finden', 'person'],
  merkliste: ['sammlung', 'merkliste'],
  gesehen: ['sammlung', 'gesehen'],
  info: ['abend'],
  erfolge: ['profil'],
  einstellungen: ['profil', 'einstellungen'],
}

function parse() {
  let parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent)
  if (ALIASES[parts[0]]) {
    const [, ...rest] = parts
    parts = [...ALIASES[parts[0]], ...rest]
    // "#/personen" without an id is just the search page.
    if (parts[1] === 'person' && !parts[2]) parts = ['finden']
    history.replaceState(null, '', '#/' + parts.map(encodeURIComponent).join('/'))
  }
  const [tab = 'abend', sub = null, id = null] = parts
  return { tab, sub, id }
}

const route = ref(parse())
window.addEventListener('hashchange', () => (route.value = parse()))

export function useRoute() {
  return route
}

export function navigate(...parts) {
  location.hash = '#/' + parts.filter((p) => p != null).map((p) => encodeURIComponent(p)).join('/')
}
