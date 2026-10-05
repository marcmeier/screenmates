import { defineStore } from 'pinia'
import { api } from '../api'
import { useApp } from './app'
import { useUi } from './ui'

// The host's baton (see backend routers/gastgeber.py): comes with every live poll.
export const useGastgeber = defineStore('gastgeber', {
  state: () => ({
    gastgeber: null, // user id
    da: false, // the host has the app open
    wechsel: null, // { id, art, von, an, frist, ja, nein, meine, darf_stimmen }
    darfModerieren: false,
    darfUebergeben: false,
    uebernehmen: null, // 'sofort' | 'abstimmung' | null
    geladen: false,
  }),
  actions: {
    uebernehmenVon(z) {
      const app = useApp()
      const vorher = this.gastgeber
      Object.assign(this, {
        gastgeber: z.gastgeber,
        da: z.da,
        wechsel: z.wechsel,
        darfModerieren: z.darf_moderieren,
        darfUebergeben: z.darf_uebergeben,
        uebernehmen: z.uebernehmen,
      })
      if (this.geladen && vorher !== z.gastgeber && z.gastgeber) {
        const wer = z.gastgeber === app.me?.id ? 'Du hast' : `${app.userById(z.gastgeber)?.name || 'Jemand'} hat`
        useUi().toast(`🎬 ${wer} jetzt den Gastgeber-Stab`, 'ok', 5000)
      }
      this.geladen = true
    },
    async uebergeben(an) {
      this.uebernehmenVon(await api.post('/api/gastgeber/uebergeben', { an }))
    },
    async nehmen() {
      this.uebernehmenVon(await api.post('/api/gastgeber/uebernehmen'))
    },
    async antworten(ja) {
      this.uebernehmenVon(await api.post(`/api/gastgeber/wechsel/${this.wechsel.id}`, { ja }))
    },
    async zurueckziehen() {
      this.uebernehmenVon(await api.del(`/api/gastgeber/wechsel/${this.wechsel.id}`))
    },
  },
})
