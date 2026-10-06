import { defineStore } from 'pinia'
import { markRaw } from 'vue'
import { api } from '../api'
import { pickScreen, publish } from '../webrtc'
import { useUi } from './ui'
import { t } from '../i18n'

let timer = null
let publisher = null
let statsTimer = null

// The live state of the Kino, polled app-wide so the navigation can show that
// something is on air on every page. Sending lives here too, not in the Kino
// page: the host can browse the app while the show keeps running.
const WIE_ALLE = 'screenmates.kino.wieAlle'
function wieAlleGemerkt() {
  try {
    return localStorage.getItem(WIE_ALLE) !== 'nein'
  } catch {
    return true
  }
}

export const useKino = defineStore('kino', {
  state: () => ({
    enabled: false,
    live: false,
    seit: null,
    titel: '',
    movie: null,
    zuschauer: [],
    publikum: [],
    pause: null, // since when (ms) the host called a break
    quelle: null, // 'browser' | 'obs' – where the show on air comes from
    sender: null, // who sends it (user id)
    localStream: null, // what this browser is sending, for the host's preview
    sendStats: null, // what the encoder actually produces, refreshed every 2 s
    // The host watches the stream like everyone (same delay, with sound) – or the instant preview.
    wieAlle: wieAlleGemerkt(),
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

    async startSending({ audio = true, qualitaet = 'hoch', inhalt = 'film' } = {}) {
      const ui = useUi()
      let stream
      try {
        // Watching the stream like everyone: the shared tab's own sound would come twice.
        stream = await pickScreen({ audio, inhalt, leise: this.wieAlle })
      } catch {
        return // the user cancelled the picker
      }
      try {
        publisher = await publish(
          stream,
          () => {
            publisher = null
            clearInterval(statsTimer)
            this.localStream = null
            this.sendStats = null
            this.refresh()
          },
          { qualitaet, inhalt },
        )
        this.localStream = markRaw(stream)
        clearInterval(statsTimer)
        statsTimer = setInterval(async () => {
          this.sendStats = (await publisher?.stats().catch(() => null)) ?? null
        }, 2000)
        if (audio && !stream.getAudioTracks().length) {
          ui.toast(t('kino.ohneTonBeimTeilen'), 'info', 7000)
        } else {
          ui.toast(t('kino.duBistLive'), 'ok')
        }
        setTimeout(() => this.refresh(), 1200)
      } catch (e) {
        ui.toast(e.message, 'error')
      }
    },

    stopSending() {
      try {
        publisher?.stop()
      } catch {
        /* already gone */
      }
    },

    setWieAlle(an) {
      this.wieAlle = an
      try {
        localStorage.setItem(WIE_ALLE, an ? 'ja' : 'nein')
      } catch {
        /* private mode */
      }
      // The shared tab plays its own sound only when the host watches the instant preview.
      for (const t of this.localStream?.getAudioTracks() ?? []) t.applyConstraints({ suppressLocalAudioPlayback: an }).catch(() => {})
    },

    // Ends whatever is on air, including an OBS the host can't reach directly. The server goes
    // first: tearing down the local stream changes the page, and the show must end regardless.
    async endShow() {
      try {
        await api.del('/api/kino')
      } finally {
        this.stopSending()
        await this.refresh()
      }
      useUi().toast(t('kino.beendet'), 'ok')
    },
  },
})
