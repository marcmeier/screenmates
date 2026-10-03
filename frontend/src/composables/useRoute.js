import { ref } from 'vue'

// Minimal hash router: "#/personen/42" -> { tab: 'personen', param: '42' }.
// Keeps the current tab across reloads and makes views linkable, without a dependency.
function parse() {
  const [tab, param] = location.hash.replace(/^#\/?/, '').split('/')
  return { tab: tab || 'abend', param: param ? decodeURIComponent(param) : null }
}

const route = ref(parse())
window.addEventListener('hashchange', () => (route.value = parse()))

export function useRoute() {
  return route
}

export function navigate(tab, param = null) {
  location.hash = `#/${tab}${param != null ? '/' + encodeURIComponent(param) : ''}`
}
