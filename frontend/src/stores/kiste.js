import { defineStore } from 'pinia'
import { api } from '../api'

// The shared case opening: comes with every live poll (stores/live.js), so every member of
// the group sees the host open the case – at the same moment, with the same strip.
const DAUER = 14_000 // countdown + strip + reveal, roughly
const GESEHEN = 'screenmates.kisteGesehen'
const PROBEN = 8 // clock samples kept

function gesehen() {
  try {
    return Number(localStorage.getItem(GESEHEN)) || 0
  } catch {
    return 0
  }
}

export const useKiste = defineStore('kiste', {
  state: () => ({
    aktuell: null, // the group's current opening: { id, start, seed, von, pool, gewinner }
    darfOeffnen: false,
    versatz: 0, // server clock minus local clock (ms)
    proben: [], // recent samples of it
    buehne: null, // the opening shown full-screen right now
    probe: null, // a practice spin, only on this device
    zuletzt: gesehen(), // the last opening shown here
  }),
  getters: {
    // The server's start time on this device's clock.
    lokal: (s) => (ms) => ms - s.versatz,
  },
  actions: {
    uebernehmen(r) {
      // Every sample is late by the answer's way here; the largest one was the quickest,
      // so it's the closest to the truth – and it doesn't wobble with every poll.
      this.proben = [...this.proben.slice(-(PROBEN - 1)), r.jetzt - Date.now()]
      this.versatz = Math.max(...this.proben)
      this.aktuell = r.aktuell
      if (r.darf_oeffnen !== undefined) this.darfOeffnen = r.darf_oeffnen
      const k = r.aktuell
      // A new opening that is still on (or about to start): show it, wherever you are in the app.
      // Its start on this device's clock is fixed once: re-reckoned every poll, the strip jumped.
      if (k && k.id > this.zuletzt && !this.buehne && k.start + DAUER > r.jetzt) this.buehne = { ...k, lokalStart: this.lokal(k.start) }
    },
    async oeffnen() {
      this.uebernehmen(await api.post('/api/kiste'))
    },
    async zuruecknehmen() {
      await api.del(`/api/kiste/${this.aktuell.id}`)
      this.aktuell = null
    },
    fertig() {
      if (this.buehne) {
        this.zuletzt = this.buehne.id
        try {
          localStorage.setItem(GESEHEN, String(this.buehne.id))
        } catch {
          /* private mode: it may show once more */
        }
      }
      this.buehne = null
    },
  },
})
