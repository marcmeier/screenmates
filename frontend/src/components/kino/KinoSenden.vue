<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
import { INHALT, QUALITAET } from '../../webrtc'
import FilmPicker from '../FilmPicker.vue'
import Icon from '../Icon.vue'

// The host's desk: what's on, and how to send it – browser or OBS.
const kino = useKino()
const ui = useUi()
const quelle = ref('browser')
const mitTon = ref(true)
const titel = ref(kino.titel)
const film = ref(kino.movie)
const filmWaehlen = ref(false)
const obs = ref(null)
const zeigeKey = ref(false)

// Remember the host's sending choices on this device.
const STORAGE = 'screenmates.senden'
function gespeichert() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE) || '{}')
  } catch {
    return {}
  }
}
const qualitaet = ref(QUALITAET[gespeichert().qualitaet] ? gespeichert().qualitaet : 'hoch')
const inhalt = ref(INHALT[gespeichert().inhalt] ? gespeichert().inhalt : 'film')
watch([qualitaet, inhalt], () => {
  try {
    localStorage.setItem(STORAGE, JSON.stringify({ qualitaet: qualitaet.value, inhalt: inhalt.value }))
  } catch {
    /* private mode */
  }
})
const upload = computed(() => QUALITAET[qualitaet.value].maxBitrate / 1e6)

// What the encoder really does, and a plain-language hint when the browser holds back.
const statsZeile = computed(() => {
  const s = kino.sendStats
  if (!s?.breite) return null
  const mbit = s.kbps != null ? ` · ${(s.kbps / 1000).toFixed(1).replace('.', ',')} Mbit/s` : ''
  const ton = s.tonKbps != null ? ` · Ton ${s.tonKbps} kbit/s${s.stereo ? ' Stereo' : ''}` : ''
  return `${s.breite}×${s.hoehe} · ${s.fps} fps${mbit} · ${s.codec}${ton}`
})
const GRENZE = {
  cpu: 'Dein Rechner kommt beim Kodieren nicht hinterher – „Mittel“ wählen oder andere Programme schließen.',
  bandwidth: 'Die Verbindung zum Server bremst gerade – das Bild wird kurz weicher.',
}

watch(() => [kino.titel, kino.movie?.id], () => {
  titel.value = kino.titel
  film.value = kino.movie
})

async function programm(movie = film.value) {
  await api.post('/api/kino/programm', { titel: titel.value, movie_id: movie?.id ?? null })
  await kino.refresh()
}

function waehleFilm(m) {
  film.value = m
  if (!titel.value.trim()) titel.value = m.title
  filmWaehlen.value = false
  programm(m)
}

function filmWeg() {
  film.value = null
  programm(null)
}

async function ladeObs() {
  obs.value = await api.get('/api/kino/obs')
}
onMounted(ladeObs)

async function neuerKey() {
  if (!confirm('Neuen Stream-Key erzeugen? Der alte funktioniert dann in OBS nicht mehr.')) return
  obs.value.key = (await api.post('/api/kino/obs/neu')).key
  zeigeKey.value = true
}

async function kopiere(text, was) {
  try {
    await navigator.clipboard.writeText(text)
    ui.toast(`${was} kopiert`, 'ok')
  } catch {
    ui.toast('Kopieren ging nicht – bitte markieren und kopieren.', 'error')
  }
}

// Who is on air: this browser, the same person on another device, someone else's browser, or OBS.
const app = useApp()
const liveText = computed(() => {
  if (kino.sende) return 'Du bist live'
  if (kino.quelle === 'obs') return 'Live über OBS'
  if (kino.sender && kino.sender === app.me?.id) return 'Du sendest von einem anderen Gerät'
  const wer = app.userById(kino.sender)?.name
  return wer ? `${wer} sendet aus dem Browser` : 'Live'
})

// "Kurze Pause": a sign over everyone's picture until the host goes on.
async function pause() {
  await api.post('/api/kino/pause', { an: !kino.pause })
  await kino.refresh()
}

async function beenden() {
  if (!confirm('Übertragung für alle beenden?')) return
  await kino.endShow()
}
</script>

<template>
  <section class="panel desk">
    <header class="kopf">
      <h2>Senden</h2>
      <nav v-if="!kino.live" class="segments" aria-label="Quelle">
        <button :class="{ active: quelle === 'browser' }" @click="quelle = 'browser'">Bildschirm teilen</button>
        <button :class="{ active: quelle === 'obs' }" @click="quelle = 'obs'">OBS</button>
      </nav>
    </header>

    <div v-if="kino.live" class="onair">
      <span class="live-dot"></span>
      <strong>{{ liveText }}</strong>
      <span v-if="statsZeile" class="stats">{{ statsZeile }}</span>
      <span class="spacer"></span>
      <button :class="{ on: kino.pause }" @click="pause">{{ kino.pause ? '▶ Weiter geht’s' : '⏸ Pause ansagen' }}</button>
      <button class="danger" @click="beenden">Übertragung beenden</button>
      <span v-if="GRENZE[kino.sendStats?.grenze]" class="warn">{{ GRENZE[kino.sendStats.grenze] }}</span>
    </div>

    <div class="spalten">
      <div class="programme">
        <label class="field">Was läuft?
          <input v-model="titel" maxlength="120" placeholder="z. B. Shining, oder: Marc spielt Resident Evil" @change="programm()" />
        </label>
        <div class="row film">
          <template v-if="film">
            <span class="chip">🎬 {{ film.title }} <span class="muted">{{ film.year }}</span></span>
            <button class="ghost small" @click="filmWeg">Verknüpfung lösen</button>
          </template>
          <button v-else class="ghost small" @click="filmWaehlen = !filmWaehlen">
            <Icon name="plus" :size="14" /> Mit Film aus dem Katalog verknüpfen
          </button>
        </div>
        <p v-if="film" class="muted small">Danach kannst du ihn mit einem Klick als gesehen eintragen – alle Zuschauenden als dabei.</p>
        <FilmPicker v-if="filmWaehlen" placeholder="Film suchen …" @pick="waehleFilm" />
      </div>

      <template v-if="!kino.live">
        <div v-if="quelle === 'browser'" class="source">
          <p class="muted">
            Teile einen Bildschirm, ein Fenster oder einen Browser-Tab – zum Beispiel deinen Videoplayer oder ein Spiel.
            Am einfachsten für den Ton: einen Tab teilen und „Audio teilen“ anhaken.
          </p>
          <div class="choices">
            <label class="field">Qualität
              <select v-model="qualitaet">
                <option v-for="(q, key) in QUALITAET" :key="key" :value="key">{{ q.label }}</option>
              </select>
            </label>
            <label class="field">Inhalt
              <select v-model="inhalt">
                <option v-for="(m, key) in INHALT" :key="key" :value="key">{{ m.label }}</option>
              </select>
            </label>
          </div>
          <p class="muted small">Der Server braucht bis zu {{ upload }} Mbit/s Upload je zuschauender Person.</p>
          <label class="check"><input v-model="mitTon" type="checkbox" /> Ton mitsenden</label>
          <button class="primary go" @click="kino.startSending({ audio: mitTon, qualitaet, inhalt })"><Icon name="kino" :size="18" /> Übertragung starten</button>
        </div>

        <div v-else class="source">
          <p class="muted">
            Mit OBS (ab Version 30) bekommst du Szenen, Spielaufnahme, Filmdateien und vollen Ton.
            In OBS unter <strong>Einstellungen → Stream</strong>:
          </p>
          <p v-if="obs?.persoenlich" class="notice klein">
            Das ist dein persönlicher Schlüssel: Er funktioniert nur, solange du den Gastgeber-Stab hast.
          </p>
          <ol v-if="obs" class="steps">
            <li>Dienst: <code>WHIP</code></li>
            <li>
              Server:
              <span class="copy"><code>{{ obs.server }}</code><button class="ghost small" aria-label="Server kopieren" @click="kopiere(obs.server, 'Server')"><Icon name="kopieren" :size="14" /></button></span>
            </li>
            <li>
              Bearer-Token:
              <span class="copy">
                <code>{{ zeigeKey ? obs.key : '•'.repeat(16) }}</code>
                <button class="ghost small" @click="zeigeKey = !zeigeKey">{{ zeigeKey ? 'verbergen' : 'zeigen' }}</button>
                <button class="ghost small" aria-label="Token kopieren" @click="kopiere(obs.key, 'Token')"><Icon name="kopieren" :size="14" /></button>
              </span>
            </li>
            <li>
              Unter <strong>Ausgabe</strong>: Encoder x264 (oder Hardware-H.264), Bitrate <strong>6000–8000 kbit/s</strong> für 1080p,
              Keyframe-Intervall 1 s, B-Frames 0 (WebRTC kennt keine B-Frames)
            </li>
            <li>„Streaming starten“ – hier erscheint dann „Du bist live“.</li>
          </ol>
          <button class="ghost small" @click="neuerKey">Neuen Stream-Key erzeugen</button>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
/* Lies under the screen: wide, in columns – what's on | how to send. */
.desk { display: flex; flex-direction: column; gap: 1rem; }
.kopf { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
h2 { margin: 0; font-size: 1.05rem; }
.spalten { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr)); gap: 1.2rem 2rem; align-items: start; }
.programme { display: flex; flex-direction: column; gap: 0.5rem; }
.film { min-height: 2rem; }
.small { font-size: 0.8rem; margin: 0; }
.onair { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; padding: 0.8rem 1rem; border-radius: 8px; background: var(--accent-soft); border: 1px solid rgba(229, 9, 20, 0.4); }
.onair strong { white-space: nowrap; }
.onair .stats { font-size: 0.8rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.onair .warn { flex-basis: 100%; font-size: 0.8rem; color: var(--gold); }
.choices { display: flex; gap: 0.6rem; flex-wrap: wrap; }
.choices select { width: auto; }
.live-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.35; } }
.segments { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg); border: 1px solid var(--line); border-radius: 9px; }
.segments button { border: none; background: none; padding: 0.4rem 0.9rem; color: var(--muted); }
.segments button.active { background: var(--bg-raised); color: var(--text); font-weight: 600; }
.source { display: flex; flex-direction: column; gap: 0.7rem; align-items: flex-start; }
.source p { margin: 0; font-size: 0.88rem; line-height: 1.5; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.88rem; }
.check input { width: auto; }
.go { padding: 0.65rem 1.2rem; }
.steps { margin: 0; padding-left: 1.2rem; font-size: 0.88rem; display: flex; flex-direction: column; gap: 0.45rem; }
.copy { display: inline-flex; align-items: center; gap: 0.2rem; flex-wrap: wrap; }
code { background: var(--bg); border: 1px solid var(--line); padding: 1px 6px; border-radius: 4px; font-size: 0.8rem; word-break: break-all; }
</style>
