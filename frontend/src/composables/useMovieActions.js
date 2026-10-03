import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'

/**
 * The three things you can do with any film, shared by cards and the detail sheet.
 * Each action updates the movie object in place, so every view showing it stays in sync.
 */
export function useMovieActions() {
  const app = useApp()
  const ui = useUi()

  const istVorgeschlagen = (m) => !!app.me && (m.vorgeschlagen_von || []).includes(app.me.id)

  async function toggleMerken(m) {
    if (m.gemerkt) {
      await api.del(`/api/wishlist/${m.id}`)
      m.gemerkt = false
      ui.toast(`„${m.title}“ von der Merkliste genommen`)
    } else {
      await api.post('/api/wishlist', { movie_id: m.id })
      m.gemerkt = true
      ui.toast(`„${m.title}“ gemerkt`, 'ok')
    }
    ui.changed()
  }

  async function toggleVorschlag(m) {
    if (istVorgeschlagen(m)) {
      await api.del(`/api/suggestions/${m.id}`)
      m.vorgeschlagen_von = m.vorgeschlagen_von.filter((id) => id !== app.me.id)
      ui.toast(`Vorschlag „${m.title}“ zurückgezogen`)
    } else {
      await api.post('/api/suggestions', { movie_id: m.id })
      m.vorgeschlagen_von = [...(m.vorgeschlagen_von || []), app.me?.id].filter(Boolean)
      ui.toast(`„${m.title}“ für den nächsten Abend vorgeschlagen`, 'ok')
    }
    ui.changed()
  }

  async function alsGesehen(m) {
    await api.post('/api/watched', { movie_id: m.id })
    Object.assign(m, { gesehen: true, gemerkt: false, vorgeschlagen_von: [] })
    ui.toast(`„${m.title}“ als gesehen eingetragen`, 'ok')
    ui.changed()
  }

  return { toggleMerken, toggleVorschlag, alsGesehen, istVorgeschlagen }
}
