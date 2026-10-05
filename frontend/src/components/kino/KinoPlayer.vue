<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useKino } from '../../stores/kino'
import { createViewer } from '../../webrtc'
import Icon from '../Icon.vue'

// The screen. Viewers get the relayed stream; the host who is sending sees the
// local capture instead (no extra delay, no extra upload).
const kino = useKino()
const box = ref(null)
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

onMounted(attach)
watch(() => [kino.live, kino.sende], attach)
onBeforeUnmount(() => {
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
</style>
