<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
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

async function beenden() {
  if (!confirm('Übertragung für alle beenden?')) return
  await kino.endShow()
}
</script>

<template>
  <section class="panel desk">
    <h2>Senden</h2>

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

    <div v-if="kino.live" class="onair">
      <span class="live-dot"></span>
      <strong>Du bist live</strong>
      <span v-if="!kino.sende" class="muted">(über OBS)</span>
      <button class="danger" @click="beenden">Übertragung beenden</button>
    </div>

    <template v-else>
      <nav class="segments" aria-label="Quelle">
        <button :class="{ active: quelle === 'browser' }" @click="quelle = 'browser'">Bildschirm teilen</button>
        <button :class="{ active: quelle === 'obs' }" @click="quelle = 'obs'">OBS</button>
      </nav>

      <div v-if="quelle === 'browser'" class="source">
        <p class="muted">
          Teile einen Bildschirm, ein Fenster oder einen Browser-Tab – zum Beispiel deinen Videoplayer oder ein Spiel.
          Am einfachsten für den Ton: einen Tab teilen und „Audio teilen“ anhaken.
        </p>
        <label class="check"><input v-model="mitTon" type="checkbox" /> Ton mitsenden</label>
        <button class="primary go" @click="kino.startSending({ audio: mitTon })"><Icon name="kino" :size="18" /> Übertragung starten</button>
      </div>

      <div v-else class="source">
        <p class="muted">
          Mit OBS (ab Version 30) bekommst du Szenen, Spielaufnahme, Filmdateien und vollen Ton.
          In OBS unter <strong>Einstellungen → Stream</strong>:
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
          <li>Unter <strong>Ausgabe</strong>: Keyframe-Intervall 1 s, B-Frames 0 (WebRTC kennt keine B-Frames)</li>
          <li>„Streaming starten“ – hier erscheint dann „Du bist live“.</li>
        </ol>
        <button class="ghost small" @click="neuerKey">Neuen Stream-Key erzeugen</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.desk { display: flex; flex-direction: column; gap: 1rem; }
h2 { margin: 0; font-size: 1.05rem; }
.programme { display: flex; flex-direction: column; gap: 0.5rem; }
.film { min-height: 2rem; }
.small { font-size: 0.8rem; margin: 0; }
.onair { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; padding: 0.8rem 1rem; border-radius: 8px; background: var(--accent-soft); border: 1px solid rgba(229, 9, 20, 0.4); }
.onair strong { white-space: nowrap; }
.onair .danger { width: 100%; justify-content: center; }
.live-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--accent); animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.35; } }
.segments { display: inline-flex; gap: 2px; padding: 3px; background: var(--bg); border: 1px solid var(--line); border-radius: 9px; align-self: flex-start; }
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
