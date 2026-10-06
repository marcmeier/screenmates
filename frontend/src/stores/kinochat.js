import { defineStore } from 'pinia'
import { api } from '../api'

// The Kino's chat and reactions (backend routers/kinochat.py): polled while the Kino page
// is open. Messages stay in the list; reactions fly across the picture for a moment.
const SCHNELL = 1500
const LANGSAM = 6000 // background tab
const MAX_FLIEGEND = 30
let timer = null
let schluessel = 0

export const useKinoChat = defineStore('kinochat', {
  state: () => ({
    nachrichten: [], // [{ id, user_id, inhalt, at }]
    fliegend: [], // reactions on their way up: [{ key, inhalt, user_id, links, dauer, kippen }]
    reaktionen: [],
    letzte: null, // id of the newest entry seen; null: nothing fetched yet
    offen: false,
  }),
  actions: {
    async abrufen() {
      const anfang = this.letzte === null
      let r
      try {
        // The first call gets the conversation so far, later ones everything new.
        r = await api.get(anfang ? '/api/kino/chat' : `/api/kino/chat?seit=${this.letzte}`, { quiet: true })
      } catch {
        return
      }
      this.reaktionen = r.reaktionen
      for (const e of r.eintraege) this.aufnehmen(e, !anfang)
      this.letzte = Math.max(this.letzte ?? 0, r.letzte)
    },
    aufnehmen(e, frisch = true) {
      if (e.typ === 'text') {
        if (this.nachrichten.some((n) => n.id === e.id)) return
        this.nachrichten.push(e)
        if (this.nachrichten.length > 200) this.nachrichten.splice(0, this.nachrichten.length - 200)
      } else if (frisch && !this.fliegend.some((f) => f.id === e.id)) {
        this.fliegen(e)
      }
    },
    fliegen(e) {
      const f = {
        ...e,
        key: ++schluessel,
        links: 6 + Math.random() * 82,
        dauer: 2600 + Math.random() * 1400,
        kippen: Math.round(Math.random() * 30 - 15),
      }
      this.fliegend.push(f)
      if (this.fliegend.length > MAX_FLIEGEND) this.fliegend.shift()
      setTimeout(() => (this.fliegend = this.fliegend.filter((x) => x.key !== f.key)), f.dauer)
    },
    async senden(text) {
      this.aufnehmen(await api.post('/api/kino/chat', { text }))
    },
    async reagieren(emoji) {
      const e = await api.post('/api/kino/reaktion', { emoji }, { quiet: true }).catch(() => null)
      if (e) this.fliegen(e) // at once; the poll brings it again, but it's known by then
    },
    starten() {
      if (this.offen) return
      this.offen = true
      this.letzte = null
      this.nachrichten = []
      const schritt = async () => {
        await this.abrufen()
        if (this.offen) timer = setTimeout(schritt, document.hidden ? LANGSAM : SCHNELL)
      }
      schritt()
    },
    stoppen() {
      this.offen = false
      clearTimeout(timer)
      this.fliegend = []
    },
  },
})