<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useKiste } from '../../stores/kiste'
import { useUi } from '../../stores/ui'
import { INHALT, QUALITAET } from '../../webrtc'
import FilmPicker from '../FilmPicker.vue'
import Icon from '../Icon.vue'

// The host's desk, kept slim under the screen: what's on, and how to send it – browser or OBS.
// Quality, content type and sound sit behind "Einstellungen"; the OBS steps show only for OBS.
const kino = useKino()
const kiste = useKiste()
const mehr = ref(false)
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

// The film of the evening goes on the programme by itself, as long as nothing else is set.
const ausKiste = computed(() => !!film.value && film.value.id === kiste.aktuell?.gewinner?.id)
watch(
  () => kiste.aktuell?.gewinner?.id,
  () => {
    const g = kiste.aktuell?.gewinner
    if (g && !kino.live && !kino.titel && !kino.movie && !film.value) {
      titel.value = g.title
      film.value = g
      programm(g)
    }
  },
  { immediate: true },
)

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
    <div v-if="kino.live" class="onair">
      <span class="live-dot"></span>
      <strong>{{ liveText }}</strong>
      <span v-if="statsZeile" class="stats">{{ statsZeile }}</span>
      <span class="spacer"></span>
      <button class="small" :class="{ on: kino.pause }" @click="pause">{{ kino.pause ? '▶ Weiter geht’s' : '⏸ Pause' }}</button>
      <button class="small danger" @click="beenden">Übertragung beenden</button>
      <span v-if="GRENZE[kino.sendStats?.grenze]" class="warn">{{ GRENZE[kino.sendStats.grenze] }}</span>
    </div>

    <div class="zeile">
      <h2>Senden</h2>
      <input v-model="titel" class="titel" maxlength="120" aria-label="Was läuft?" placeholder="Was läuft? z. B. Shining" @change="programm()" />
      <span v-if="film" class="chip film">
        🎬 {{ film.title }} <span class="muted">{{ film.year }}</span>
        <span v-if="ausKiste" class="kiste">aus der Kiste</span>
        <button class="ghost los" aria-label="Verknüpfung lösen" @click="filmWeg"><Icon name="x" :size="12" /></button>
      </span>
      <button v-else class="ghost small" aria-label="Mit Film aus dem Katalog verknüpfen" @click="filmWaehlen = !filmWaehlen">
        <Icon name="plus" :size="14" /> <span class="lang">Mit Film aus dem Katalog verknüpfen</span>
      </button>
      <template v-if="!kino.live">
        <span class="spacer"></span>
        <nav class="segments" aria-label="Quelle">
          <button :class="{ active: quelle === 'browser' }" @click="quelle = 'browser'">Bildschirm</button>
          <button :class="{ active: quelle === 'obs' }" @click="quelle = 'obs'">OBS</button>
        </nav>
        <button v-if="quelle === 'browser'" class="ghost small" :aria-expanded="mehr" @click="mehr = !mehr">
          <Icon name="verwaltung" :size="14" /> Einstellungen
        </button>
        <button v-if="quelle === 'browser'" class="primary go" @click="kino.startSending({ audio: mitTon, qualitaet, inhalt })">
          <Icon name="kino" :size="16" /> Übertragung starten
        </button>
      </template>
    </div>
    <FilmPicker v-if="filmWaehlen" placeholder="Film suchen …" @pick="waehleFilm" />

    <div v-if="!kino.live && quelle === 'browser' && mehr" class="optionen">
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
      <label class="check"><input v-model="mitTon" type="checkbox" /> Ton mitsenden</label>
      <p class="muted klein">
        Bis zu {{ upload }} Mbit/s Upload je Zuschauer. Für den Ton am einfachsten einen Browser-Tab teilen und „Audio teilen“ anhaken.
      </p>
    </div>

    <div v-if="!kino.live && quelle === 'obs'" class="optionen obs">
      <p v-if="obs?.persoenlich" class="notice klein">Dein persönlicher Schlüssel – er funktioniert nur, solange du den Gastgeber-Stab hast.</p>
      <ol v-if="obs" class="steps">
        <li>OBS ab Version 30: <strong>Einstellungen → Stream</strong>, Dienst <code>WHIP</code></li>
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
        <li>Ausgabe: x264 oder Hardware-H.264, <strong>6000–8000 kbit/s</strong> für 1080p, Keyframe-Intervall 1 s, B-Frames 0</li>
        <li>„Streaming starten“ – hier erscheint dann „Du bist live“.</li>
      </ol>
      <button class="ghost small" @click="neuerKey">Neuen Stream-Key erzeugen</button>
    </div>
  </section>
</template>

<style scoped>
/* One slim row under the screen: the picture and the chat are what matter. */
.desk { display: flex; flex-direction: column; gap: 0.6rem; padding: 0.7rem 0.9rem; }
h2 { margin: 0; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 700; }
.zeile { display: flex; align-items: center; gap: 0.5rem 0.7rem; flex-wrap: wrap; }
.titel { flex: 1 1 14rem; min-width: 10rem; max-width: 26rem; padding: 0.4rem 0.6rem; font-size: 0.88rem; }
.film { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.8rem; }
.film .kiste { font-size: 0.66rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--gold); }
.film .los { padding: 0 2px; }
.go { padding: 0.45rem 0.9rem; }
.segments { display: inline-flex; gap: 2px; padding: 2px; background: var(--bg); border: 1px solid var(--line); border-radius: 8px; }
.segments button { border: none; background: none; padding: 0.3rem 0.7rem; color: var(--muted); font-size: 0.82rem; }
.segments button.active { background: var(--bg-raised); color: var(--text); font-weight: 600; }
.onair { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem 0.7rem; padding: 0.5rem 0.8rem; border-radius: 8px; background: var(--accent-soft); border: 1px solid rgba(229, 9, 20, 0.4); }
.onair strong { white-space: nowrap; font-size: 0.9rem; }
.onair .stats { font-size: 0.76rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.onair .warn { flex-basis: 100%; font-size: 0.78rem; color: var(--gold); }
.live-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.35; } }
.optionen { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 0.6rem 1rem; padding-top: 0.6rem; border-top: 1px solid var(--line); }
.optionen select { width: auto; }
.optionen.obs { flex-direction: column; align-items: flex-start; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; }
.check input { width: auto; }
.klein { font-size: 0.78rem; margin: 0; flex-basis: 100%; }
.steps { margin: 0; padding-left: 1.2rem; font-size: 0.85rem; display: flex; flex-direction: column; gap: 0.4rem; }
.copy { display: inline-flex; align-items: center; gap: 0.2rem; flex-wrap: wrap; }
code { background: var(--bg); border: 1px solid var(--line); padding: 1px 6px; border-radius: 4px; font-size: 0.78rem; word-break: break-all; }
@media (max-width: 600px) { .lang { display: none; } }
</style>
