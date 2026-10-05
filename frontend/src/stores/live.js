import { defineStore } from 'pinia'
import { api, beiAenderung } from '../api'
import { useApp } from './app'
import { useKiste } from './kiste'
import { useUi } from './ui'

// Live updates: every open app asks the server every 1.5 s (every 15 s in a background tab)
// whether something changed – a friend rated, hearted, suggested … – and then reloads what's
// on screen. The same answer carries the shared case opening.
const SCHNELL = 1500
const LANGSAM = 15_000
let timer = null

export const useLive = defineStore('live', {
  state: () => ({ stand: null, stillBis: 0 }),
  actions: {
    async abfragen() {
      const app = useApp()
      let r
      try {
        r = await api.get('/api/live', { quiet: true })
      } catch {
        return
      }
      if (r.kiste) useKiste().uebernehmen({ jetzt: r.jetzt, ...r.kiste })
      const alt = this.stand
      this.stand = r.stand
      // Our own writes have already updated this screen: adopt their count silently.
      if (alt === null || alt === r.stand || Date.now() < this.stillBis) return
      useUi().changed()
      app.refreshUsers().catch(() => {})
    },
    planen() {
      clearTimeout(timer)
      timer = setTimeout(async () => {
        await this.abfragen()
        this.planen()
      }, document.hidden ? LANGSAM : SCHNELL)
    },
    starten() {
      if (this.gestartet) return
      this.gestartet = true
      beiAenderung(() => (this.stillBis = Date.now() + 2500))
      // Coming back to the tab: catch up at once.
      document.addEventListener('visibilitychange', () => !document.hidden && this.abfragen())
      this.abfragen()
      this.planen()
    },
  },
})
