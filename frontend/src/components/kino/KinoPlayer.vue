<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useKinoChat } from '../../stores/kinochat'
import { createViewer } from '../../webrtc'
import Icon from '../Icon.vue'

// The screen. Viewers get the relayed stream; the host who is sending sees the
// local capture instead (no extra delay, no extra upload).
const kino = useKino()
const app = useApp()
const chat = useKinoChat()
const box = ref(null)
// Full screen hides the chat panel: the latest messages show on the picture instead.
const vollbildAn = ref(false)
const jetzt = ref(Date.now())
let uhr = null
const einblendungen = computed(() => chat.nachrichten.filter((n) => jetzt.value - n.at < 8000).slice(-4))
// The host's break: how long it's been, ticking while it lasts.
const uhrPause = ref(Date.now())
let pauseTimer = null
watch(
  () => kino.pause,
  (p) => {
    clearInterval(pauseTimer)
    if (p) pauseTimer = setInterval(() => (uhrPause.value = Date.now()), 1000)
  },
  { immediate: true },
)
const pauseDauer = computed(() => {
  const s = Math.max(0, Math.floor((uhrPause.value - (kino.pause || 0)) / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
})
function vollbildGeaendert() {
  vollbildAn.value = document.fullscreenElement === box.value
  clearInterval(uhr)
  if (vollbildAn.value) uhr = setInterval(() => (jetzt.value = Date.now()), 1000)
}
const video = ref(null)
const state = ref('verbinde')
const muted = ref(true) // browsers only autoplay muted video
const volume = ref(1)
let viewer = null
let beat = null

function heartbeat() {
  api.post('/api/kino/da', undefined, { quiet: true }).then((r) => (kino.zuschauer = r.zuschauer)).catch(() => {})
}

function startHeartbeat() {
  if (beat) return
  heartbeat()
  beat = setInterval(heartbeat, 10_000)
}

function watchStream() {
  stopWatching()
  viewer = createViewer(video.value, (s) => {
    state.value = s
    if (s === 'live') startHeartbeat()
  })
  viewer.start()
}

function stopWatching() {
  viewer?.stop()
  viewer = null
  clearInterval(beat)
  beat = null
}

function attach() {
  if (kino.sende) {
    stopWatching()
    video.value.srcObject = kino.localStream
    state.value = 'live'
    startHeartbeat() // the host watches along and belongs to the audience too
  } else if (kino.live) {
    watchStream()
  } else {
    stopWatching()
  }
}

onMounted(() => {
  attach()
  document.addEventListener('fullscreenchange', vollbildGeaendert)
})
watch(() => [kino.live, kino.sende], attach)
onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', vollbildGeaendert)
  clearInterval(uhr)
  clearInterval(pauseTimer)
  stopWatching()
  api.del('/api/kino/da', { quiet: true }).catch(() => {})
})

function tonAn() {
  muted.value = false
  video.value.play().catch(() => {})
}

watch(volume, (v) => {
  muted.value = v === 0
})

function vollbild() {
  if (document.fullscreenElement) document.exitFullscreen()
  else box.value.requestFullscreen?.()
}
</script>

<template>
  <div ref="box" class="screen" @dblclick="vollbild">
    <video ref="video" autoplay playsinline :muted="muted || kino.sende" :volume="volume"></video>

    <div class="flug" aria-hidden="true">
      <span
        v-for="f in chat.fliegend"
        :key="f.key"
        :style="{ left: `${f.links}%`, animationDuration: `${f.dauer}ms`, '--kippen': `${f.kippen}deg` }"
      >
        {{ f.inhalt }}<small v-if="vollbildAn">{{ app.userById(f.user_id)?.name }}</small>
      </span>
    </div>
    <div v-if="kino.pause" class="pause" role="status">
      <span class="symbol" aria-hidden="true">⏸</span>
      <strong>Kurze Pause – gleich geht’s weiter</strong>
      <small>seit {{ pauseDauer }}</small>
    </div>
    <ol v-if="chat.momente.length" class="momente" aria-live="polite">
      <li v-for="m in chat.momente" :key="m.id">✋ <strong>{{ app.userById(m.user_id)?.name ?? 'Jemand' }}</strong>: Moment, bin gleich da</li>
    </ol>
    <ol v-if="vollbildAn && einblendungen.length" class="einblendungen" aria-live="polite">
      <li v-for="n in einblendungen" :key="n.id">
        <strong :style="{ color: app.userById(n.user_id)?.color }">{{ app.userById(n.user_id)?.name ?? 'Jemand' }}</strong> {{ n.inhalt }}
      </li>
    </ol>

    <div v-if="state !== 'live'" class="overlay">
      <span class="spinner" aria-hidden="true"></span>
      {{ state === 'verbinde' ? 'Verbinde …' : 'Verbindung unterbrochen – versuche es erneut …' }}
    </div>
    <button v-else-if="muted && !kino.sende" class="primary unmute" @click="tonAn">
      <Icon name="ton" :size="18" /> Ton an
    </button>

    <div class="controls">
      <span v-if="kino.sende" class="hint">Deine Vorschau – du hörst dich selbst nicht</span>
      <template v-else>
        <button class="ghost" :aria-label="muted ? 'Ton an' : 'Stumm'" @click="muted = !muted">
          <Icon :name="muted ? 'stumm' : 'ton'" />
        </button>
        <input v-model.number="volume" type="range" min="0" max="1" step="0.05" aria-label="Lautstärke" />
      </template>
      <span class="spacer"></span>
      <span v-if="vollbildAn" class="schnell" role="group" aria-label="Reaktion ins Bild schicken">
        <button v-for="r in chat.reaktionen.slice(0, 6)" :key="r" class="ghost" :aria-label="`Reaktion ${r}`" @click="chat.reagieren(r)">{{ r }}</button>
      </span>
      <button class="ghost" aria-label="Vollbild" @click="vollbild"><Icon name="vollbild" /></button>
    </div>
  </div>
</template>

<style scoped>
.screen {
  position: relative; aspect-ratio: 16 / 9; width: var(--kino-breite); background: #000;
  border-radius: var(--radius); overflow: hidden; border: 1px solid var(--line);
}
.screen:fullscreen { width: 100%; border-radius: 0; border: none; }
video { width: 100%; height: 100%; object-fit: contain; display: block; background: #000; }
.overlay {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; gap: 0.8rem;
  color: var(--muted); font-size: 0.95rem; background: rgba(0, 0, 0, 0.55);
}
.spinner { width: 18px; height: 18px; border: 2px solid var(--line); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.unmute { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); padding: 0.7rem 1.3rem; font-size: 1rem; box-shadow: var(--shadow); }
.controls {
  position: absolute; left: 0; right: 0; bottom: 0; display: flex; align-items: center; gap: 0.4rem;
  padding: 1.6rem 0.8rem 0.6rem; background: linear-gradient(transparent, rgba(0, 0, 0, 0.75));
  opacity: 0; transition: opacity 0.2s;
}
.screen:hover .controls, .screen:focus-within .controls { opacity: 1; }
@media (hover: none) { .controls { opacity: 1; } }
.controls button { color: #fff; padding: 0.35rem; }
.controls input[type='range'] { width: 110px; padding: 0; accent-color: var(--accent); }
.hint { font-size: 0.8rem; color: #ddd; }

/* Reactions rising across the picture. */
.flug { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.flug span {
  position: absolute; bottom: 4%; font-size: clamp(1.6rem, 3.2vw, 2.6rem); line-height: 1;
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  animation: steigen linear forwards; filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.6));
}
.flug small { font-size: 0.7rem; color: #fff; font-weight: 600; text-shadow: 0 1px 3px #000; }
@keyframes steigen {
  0% { transform: translateY(0) scale(0.4) rotate(0deg); opacity: 0; }
  12% { transform: translateY(-12%) scale(1.15) rotate(var(--kippen)); opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(-620%) scale(0.9) rotate(calc(var(--kippen) * -1)); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .flug span { animation-name: blinken; }
  @keyframes blinken { 0%, 100% { opacity: 0; } 20%, 80% { opacity: 1; } }
}
.einblendungen {
  position: absolute; left: 1.2rem; bottom: 4.2rem; margin: 0; padding: 0; list-style: none; max-width: min(40%, 28rem);
  display: flex; flex-direction: column; gap: 0.35rem; pointer-events: none;
}
.einblendungen li {
  background: rgba(0, 0, 0, 0.62); color: #fff; padding: 0.4rem 0.7rem; border-radius: 10px; font-size: 0.95rem;
  animation: auftauchen 0.25s ease-out; overflow-wrap: anywhere;
}
@keyframes auftauchen { from { opacity: 0; transform: translateY(6px); } }
.pause {
  position: absolute; inset: 0; z-index: 2; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.4rem;
  background: rgba(0, 0, 0, 0.72); color: #fff; text-align: center; backdrop-filter: blur(4px); pointer-events: none;
}
.pause .symbol { font-size: 3rem; line-height: 1; }
.pause strong { font-size: clamp(1.1rem, 2.4vw, 1.6rem); }
.pause small { opacity: 0.75; font-variant-numeric: tabular-nums; }
.momente { position: absolute; top: 0.8rem; left: 50%; transform: translateX(-50%); z-index: 3; margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 0.3rem; pointer-events: none; }
.momente li { background: rgba(0, 0, 0, 0.7); color: #fff; padding: 0.4rem 0.8rem; border-radius: 999px; font-size: 0.9rem; white-space: nowrap; animation: auftauchen 0.25s ease-out; }
.schnell { display: inline-flex; }
.schnell button { font-size: 1.15rem; padding: 0.2rem 0.3rem; }
</style>
