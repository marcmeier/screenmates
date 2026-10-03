import { defineStore } from 'pinia'
import { markRaw } from 'vue'
import { api } from '../api'
import { pickScreen, publish } from '../webrtc'
import { useUi } from './ui'

let timer = null
let publisher = null

// The live state of the Kino, polled app-wide so the navigation can show that
// something is on air on every page. Sending lives here too, not in the Kino
// page: the host can browse the app while the show keeps running.
export const useKino = defineStore('kino', {
  state: () => ({
    enabled: false,
    live: false,
    seit: null,
    titel: '',
    movie: null,
    zuschauer: [],
    publikum: [],
    localStream: null, // what this browser is sending, for the host's preview
  }),
  getters: {
    sende: (s) => !!s.localStream,
  },
  actions: {
    async refresh() {
      try {
        Object.assign(this, await api.get('/api/kino', { quiet: true }))
      } catch {
        /* keep the last known state; polling retries */
      }
    },
    startPolling(ms = 8000) {
      this.refresh()
      clearInterval(timer)
      timer = setInterval(() => this.refresh(), ms)
    },

    async startSending({ audio = true } = {}) {
      const ui = useUi()
      let stream
      try {
        stream = await pickScreen({ audio })
      } catch {
        return // the user cancelled the picker
      }
      try {
        publisher = await publish(stream, () => {
          publisher = null
          this.localStream = null
          this.refresh()
        })
        this.localStream = markRaw(stream)
        if (audio && !stream.getAudioTracks().length) {
          ui.toast('Ohne Ton: Beim Teilen „Audio teilen“ anhaken (geht bei Tabs und unter Windows auch für den ganzen Bildschirm).', 'info', 7000)
        } else {
          ui.toast('Du bist live', 'ok')
        }
        setTimeout(() => this.refresh(), 1200)
      } catch (e) {
        ui.toast(e.message, 'error')
      }
    },

    stopSending() {
      publisher?.stop()
    },

    // Ends whatever is on air, including an OBS the host can't reach directly.
    async endShow() {
      this.stopSending()
      await api.del('/api/kino')
      await this.refresh()
    },
  },
})
