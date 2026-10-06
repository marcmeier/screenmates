import { defineStore } from 'pinia'
import { api } from '../api'

// The Kino's chat (kept 30 days) and reactions (a moment) – backend routers/kinochat.py.
// Polled while the Kino page is open; reactions fly across the picture for a moment.
const SCHNELL = 1500
const LANGSAM = 6000 // background tab
const MAX_FLIEGEND = 30
let timer = null
let schluessel = 0

export const useKinoChat = defineStore('kinochat', {
  state: () => ({
    nachrichten: [], // [{ id, user_id, inhalt, at }], oldest first
    fliegend: [], // reactions on their way up: [{ key, inhalt, user_id, links, dauer, kippen }]
    momente: [], // "Moment, bin gleich da" on the picture for a moment: [{ id, user_id }]
    reaktionen: [],
    letzte: null, // newest message id seen; null: nothing fetched yet
    rletzte: 0, // newest reaction id seen
    mehr: false, // older messages exist
    tage: 30,
    offen: false,
  }),
  actions: {
    async abrufen() {
      const anfang = this.letzte === null
      let r
      try {
        // The first call gets the latest messages, later ones everything new.
        r = await api.get(anfang ? '/api/kino/chat' : `/api/kino/chat?seit=${this.letzte}&rseit=${this.rletzte}`, { quiet: true })
      } catch {
        return
      }
      this.reaktionen = r.reaktionen
      this.tage = r.tage
      if (anfang) this.mehr = r.mehr
      for (const e of r.eintraege) this.aufnehmen(e)
      this.letzte = Math.max(this.letzte ?? 0, r.letzte)
      this.rletzte = Math.max(this.rletzte, r.rletzte)
    },
    async aelterLaden() {
      const erste = this.nachrichten[0]
      if (!erste) return
      const r = await api.get(`/api/kino/chat/aelter?vor=${erste.id}`)
      this.nachrichten = [...r.eintraege.filter((e) => !this.nachrichten.some((n) => n.id === e.id)), ...this.nachrichten]
      this.mehr = r.mehr
    },
    aufnehmen(e) {
      if (e.typ === 'text') {
        if (this.nachrichten.some((n) => n.id === e.id)) return
        this.nachrichten.push(e)
      } else if (e.typ === 'moment') {
        if (this.momente.some((m) => m.id === e.id)) return
        this.momente.push(e)
        setTimeout(() => (this.momente = this.momente.filter((m) => m.id !== e.id)), 7000)
      } else if (!this.fliegend.some((f) => f.id === e.id)) {
        this.fliegen(e)
      }
    },
    async moment() {
      const e = await api.post('/api/kino/moment', undefined, { quiet: true }).catch(() => null)
      if (e) this.aufnehmen(e)
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
      this.rletzte = 0
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