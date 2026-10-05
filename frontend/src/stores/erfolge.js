import { defineStore } from 'pinia'
import { api } from '../api'
import { useApp } from './app'

// Achievements: the unlock pop-up queue, and the check after every change.
export const useErfolge = defineStore('erfolge', {
  state: () => ({
    popups: [], // unlocks waiting to be shown, one after another
  }),
  actions: {
    async pruefen() {
      const app = useApp()
      if (!app.me) return
      let r
      try {
        r = await api.post('/api/erfolge/neu', undefined, { quiet: true })
      } catch {
        return
      }
      if (!r.neu.length) return
      const alt = r.neu.filter((e) => e.rueckwirkend)
      const frisch = r.neu.filter((e) => !e.rueckwirkend)
      // The first visit after the launch: one summary instead of a flood.
      if (alt.length > 2) {
        this.popups.push({ key: 'rueckwirkend', zusammenfassung: alt.length, punkte: alt.reduce((s, e) => s + e.punkte, 0) })
      } else frisch.unshift(...alt)
      this.popups.push(...frisch)
      if (r.level !== app.me.level) await app.refreshUsers()
    },
    weiter() {
      this.popups.shift()
    },
  },
})
