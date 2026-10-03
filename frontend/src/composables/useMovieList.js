import { ref } from 'vue'
import { api, qs } from '../api'

/**
 * Paged movie list with cancellation: starting a new query aborts the one in
 * flight, so a slow old response can never overwrite a newer one.
 */
export function useMovieList(endpoint, pageSize = 24) {
  const items = ref([])
  const loading = ref(false)
  const failed = ref(false)
  const more = ref(false)
  const hinweis = ref(null) // server explanation for an empty result, e.g. "no subscriptions yet"
  const gesamt = ref(null) // how many films match in total, when the server knows
  let page = 1
  let params = {}
  let ctrl = null

  async function fetchPage() {
    ctrl?.abort()
    ctrl = new AbortController()
    loading.value = true
    failed.value = false
    try {
      const r = await api.get(`${endpoint}?${qs({ ...params, limit: pageSize, seite: page })}`, { signal: ctrl.signal })
      const fresh = r.results || []
      hinweis.value = r.hinweis ?? null
      const known = new Set(items.value.map((m) => m.id))
      items.value = page === 1 ? fresh : [...items.value, ...fresh.filter((m) => !known.has(m.id))]
      gesamt.value = r.gesamt ?? null
      // TMDB pages hold 20 films: only the server knows whether another page exists.
      more.value = r.mehr ?? fresh.length === pageSize
      loading.value = false
    } catch (e) {
      if (e.name === 'AbortError') return // superseded; the newer request owns `loading`
      failed.value = true
      loading.value = false
    }
  }

  function load(newParams = {}) {
    params = newParams
    page = 1
    return fetchPage()
  }

  function loadMore() {
    // A second trigger while a page is loading would abort it and skip that page.
    if (loading.value || !more.value) return
    page++
    return fetchPage()
  }

  function reset() {
    ctrl?.abort()
    items.value = []
    gesamt.value = null
    more.value = false
    loading.value = false
  }

  return { items, loading, failed, more, hinweis, gesamt, load, loadMore, reset }
}
