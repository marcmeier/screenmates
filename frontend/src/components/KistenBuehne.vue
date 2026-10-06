<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { zufall } from '../zufall'
import { SELTENHEIT, seltenheitFuer } from '../seltenheit'
import Icon from './Icon.vue'
import { audioJetzt, audioKontext } from '../audio'
import Poster from './Poster.vue'

// The case opening on stage, after Counter-Strike: a strip of posters races past a
// marker, slows down and stops on the winner. Everything random comes from `seed`
// and everything is timed from `start` – so every device that gets the same opening
// shows the same strip at the same moment (a practice spin just starts right away).
const props = defineProps({
  pool: { type: Array, required: true },
  gewinner: { type: Object, required: true },
  seed: { type: Number, required: true },
  start: { type: Number, required: true }, // local clock (ms) when the strip starts moving
  probe: { type: Boolean, default: false },
  von: { type: String, default: '' }, // who opened it
})
const emit = defineEmits(['fertig'])

const gesamt = computed(() => props.pool.reduce((s, m) => s + m.gewicht, 0) || 1)
const seltenheit = (m) => seltenheitFuer(m.gewicht / gesamt.value)
const prozent = (m) => `${Math.round((m.gewicht / gesamt.value) * 100)} %`

const ANZAHL = 64 // items on the strip
const ZIEL = 56 // index of the winner on the strip
const DAUER = 6800
const phase = ref('countdown') // 'countdown' | 'laeuft' | 'enthuellt'
const rest = ref(0) // seconds left in the countdown
const band = ref([])
const versatz = ref(0)
const fenster = ref(null)
const itemBreite = ref(150)
let raf = 0
let uebersprungen = false

const wenigerBewegung = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const dauer = () => (wenigerBewegung() ? 1500 : DAUER)

// Same seed, same strip – on every device.
const rng = zufall(props.seed)
function ziehen() {
  let r = rng() * gesamt.value
  for (const m of props.pool) if ((r -= m.gewicht) < 0) return m
  return props.pool.at(-1)
}
function bandBauen() {
  const items = Array.from({ length: ANZAHL }, ziehen)
  items[ZIEL] = props.gewinner
  // A near miss now and then: the rarest film right next to the winner.
  const seltenster = [...props.pool].sort((a, b) => a.gewicht - b.gewicht)[0]
  if (props.pool.length > 1 && seltenster.id !== props.gewinner.id && rng() < 0.5) {
    items[ZIEL + (rng() < 0.5 ? -1 : 1)] = seltenster
  }
  return items.map((m, i) => ({ m, key: `${i}-${m.id}` }))
}
const jitterAnteil = rng() - 0.5 // where on the winner it lands, also the same everywhere

// --- Sound (WebAudio, no files) ------------------------------------------------

// A new key: the old one could be "aus" without anyone meaning it (tapping the speaker to get
// sound on an iPhone used to switch it off) – so everyone starts with sound on once more.
const TON_KEY = 'screenmates.kisteTon2'
const ton = ref(true)
try {
  ton.value = localStorage.getItem(TON_KEY) !== 'aus'
} catch {
  /* private mode: sound stays on */
}
// The app-wide audio context (see audio.js): unlocked by the first tap anywhere.
let audio = audioKontext()
const blockiert = ref(false) // sound is on, but the browser hasn't allowed it yet (iPhone without a tap)
function tonUmschalten() {
  // On but still blocked: the tap brings the sound instead of switching it off.
  if (ton.value && blockiert.value) {
    audio = audioJetzt()
    blockiert.value = audio?.state !== 'running'
    return
  }
  ton.value = !ton.value
  try {
    localStorage.setItem(TON_KEY, ton.value ? 'an' : 'aus')
  } catch {
    /* ignore */
  }
  // A click is what browsers need before they play sound.
  if (ton.value) {
    audio = audioJetzt()
    blockiert.value = audio?.state !== 'running'
  }
}
function klang(freq, d, typ = 'square', lautst = 0.05, start = 0) {
  audio = audioKontext() ?? audio // a tap elsewhere may have unlocked it meanwhile
  blockiert.value = ton.value && (!audio || audio.state !== 'running')
  if (!ton.value || !audio || audio.state !== 'running') return
  const t = audio.currentTime + start
  const osc = audio.createOscillator()
  const gain = audio.createGain()
  osc.type = typ
  osc.frequency.setValueAtTime(freq, t)
  gain.gain.setValueAtTime(lautst, t)
  gain.gain.exponentialRampToValueAtTime(0.0001, t + d)
  osc.connect(gain).connect(audio.destination)
  osc.start(t)
  osc.stop(t + d)
}
const tick = () => klang(1400, 0.03, 'square', 0.035)
function fanfare(farbe) {
  const hoch = farbe === SELTENHEIT.at(-1).farbe ? 1.5 : 1 // legendary sounds brighter
  ;[523, 659, 784, 1047].forEach((f, i) => klang(f * hoch, 0.45, 'triangle', 0.08, i * 0.09))
}

// Where the strip stops: the winner under the marker. Measured every frame, so a resize
// (or a stage not laid out yet when mounted) can't move the marker off the winner.
function breite() {
  return Math.min(fenster.value?.clientWidth || window.innerWidth, window.innerWidth)
}
function ende() {
  const w = itemBreite.value
  return ZIEL * w + w / 2 - breite() / 2 + jitterAnteil * (w - 8) * 0.8
}

// --- Timeline ---------------------------------------------------------------------

// A soft pull-away (no jolt out of the countdown), then a very long slowdown – the part everyone stares at.
const ANLAUF = 0.07 // share of the run spent getting up to speed
const ease = (x) => (1 - Math.pow(1 - x, 4.2)) * Math.min(1, x / ANLAUF) ** 1.6
// While counting down the strip already creeps along, so the start is one movement.
const KRIECHEN = 18 // px per second

function enthuellen() {
  cancelAnimationFrame(raf)
  versatz.value = ende()
  if (phase.value === 'enthuellt') return
  phase.value = 'enthuellt'
  fanfare(seltenheit(props.gewinner).farbe)
}

function schritt() {
  if (phase.value === 'enthuellt') return // skipped: the strip stays on the winner
  const jetzt = Date.now()
  if (jetzt < props.start) {
    phase.value = 'countdown'
    rest.value = Math.ceil((props.start - jetzt) / 1000)
    versatz.value = wenigerBewegung() ? 0 : -((props.start - jetzt) / 1000) * KRIECHEN
    raf = requestAnimationFrame(schritt)
    return
  }
  phase.value = 'laeuft'
  const x = Math.min(1, (jetzt - props.start) / dauer())
  const vorher = versatz.value
  // From the creeping start (0) on, carrying its little speed into the run.
  versatz.value = ende() * ease(x) + Math.min(jetzt - props.start, 400) * (KRIECHEN / 1000) * (1 - x)
  const w = itemBreite.value
  const mitte = breite() / 2
  if (Math.floor((vorher + mitte) / w) !== Math.floor((versatz.value + mitte) / w)) tick()
  if (x < 1) raf = requestAnimationFrame(schritt)
  // A short breath before the reveal; late arrivals (x was 1 at once) see it right away.
  else setTimeout(() => !uebersprungen && enthuellen(), jetzt - props.start - dauer() > 1000 ? 0 : 450)
}

onMounted(async () => {
  for (const m of props.pool) if (m.poster_url) new Image().src = m.poster_url
  band.value = bandBauen()
  await nextTick()
  itemBreite.value = fenster.value.querySelector('.item')?.offsetWidth + 8 || 158
  if (phase.value === 'enthuellt') {
    versatz.value = ende() // skipped before the strip was even measured
    return
  }
  if (ton.value) {
    // Unlocked by an earlier tap in the app; otherwise one tap on the speaker brings it.
    audio = audioKontext()
    audio?.resume?.()
    blockiert.value = !audio || audio.state !== 'running'
  }
  raf = requestAnimationFrame(schritt)
})

function weiter() {
  if (phase.value !== 'enthuellt') {
    uebersprungen = true // only here: the others keep watching
    return enthuellen()
  }
  emit('fertig')
}

function taste(e) {
  if (e.key === 'Escape' || (e.key === 'Enter' && phase.value === 'enthuellt')) {
    e.preventDefault()
    weiter()
  }
}
window.addEventListener('keydown', taste)
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', taste)

})
</script>

<template>
  <Teleport to="body">
    <div class="buehne" role="dialog" aria-modal="true" :aria-label="$t('kistenbuehne.kisteOeffnen')" :class="phase">
      <div class="kopf">
        <span class="label">{{ $t('abendtab.filmabendKiste') }}</span>
        <span v-if="probe" class="probe">{{ $t('kistenbuehne.probeZaehltNicht') }}</span>
        <span v-else-if="von" class="wer">{{ $t('kistenbuehne.vonOeffnetDieKiste', { von }) }}</span>
        <span class="spacer"></span>
        <button class="ghost" :class="{ blockiert }" :aria-label="blockiert ? $t('kistenbuehne.tonEinschalten') : ton ? $t('kistenbuehne.tonAus') : $t('kistenbuehne.tonAn')" @click="tonUmschalten">
          <Icon :name="ton && !blockiert ? 'ton' : 'stumm'" /><span v-if="blockiert" class="ton-hinweis">{{ $t('kistenbuehne.tonAntippen') }}</span>
        </button>
      </div>

      <div ref="fenster" class="fenster" :style="{ '--w': `${itemBreite}px` }">
        <div class="marke" aria-hidden="true"></div>
        <div class="band" :style="{ transform: `translate3d(${-versatz}px, 0, 0)` }">
          <div
            v-for="(it, i) in band"
            :key="it.key"
            class="item"
            :class="{ sieger: phase === 'enthuellt' && i === ZIEL }"
            :style="{ '--farbe': seltenheit(it.m).farbe }"
          >
            <Poster :movie="it.m" :title="!it.m.poster_url" />
            <span class="name">{{ it.m.title }}</span>
          </div>
        </div>
        <Transition name="countdown">
          <div v-if="phase === 'countdown'" class="countdown" aria-live="assertive">
            <span :key="rest" class="zahl">{{ rest }}</span>
          </div>
        </Transition>
      </div>

      <div class="fuss" aria-live="polite">
        <template v-if="phase === 'enthuellt'">
          <div class="enthuellung" :style="{ '--farbe': seltenheit(gewinner).farbe }">
            <span class="stufe">{{ seltenheit(gewinner).name }} · {{ prozent(gewinner) }}</span>
            <strong>{{ gewinner.title }}</strong>
            <span v-if="!probe" class="muted">{{ $t('abendtab.filmDesAbends') }}</span>
          </div>
          <button class="primary" @click="weiter">{{ $t('kistenbuehne.weiter') }}</button>
        </template>
        <button v-else class="ghost" :class="{ unsichtbar: phase === 'countdown' }" :disabled="phase === 'countdown'" @click="weiter">
          {{ phase === 'countdown' ? $t('kistenbuehne.gleichGehtSLos') : $t('kistenbuehne.ueberspringen') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.buehne {
  /* The strip sits in the exact middle and never moves: the rows above and below share the
     rest equally, whatever appears underneath (countdown note, skip button, the winner). */
  position: fixed; inset: 0; z-index: 200; display: grid; grid-template-rows: minmax(0, 1fr) auto minmax(0, 1fr);
  background: radial-gradient(ellipse at center, rgba(30, 30, 40, 0.97), rgba(5, 5, 8, 0.98)); backdrop-filter: blur(6px);
}
.kopf { position: absolute; top: 0; left: 0; right: 0; display: flex; align-items: center; gap: 0.8rem; padding: 1rem 1.4rem; }
.label { font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); font-size: 0.85rem; }
.probe { font-size: 0.75rem; font-weight: 700; color: var(--gold); border: 1px solid var(--gold); border-radius: 999px; padding: 1px 8px; }
.wer { font-size: 0.85rem; color: var(--text); }
.blockiert { color: var(--gold); border: 1px solid color-mix(in srgb, var(--gold) 50%, transparent); }
.ton-hinweis { font-size: 0.8rem; font-weight: 600; }

.fenster {
  position: relative; overflow: hidden; width: 100%; min-width: 0; height: 270px; border-block: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.35);
  -webkit-mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
  mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent);
}
.band { display: flex; gap: 8px; padding: 15px 0; will-change: transform; }
.item {
  flex: none; width: 150px; height: 240px; border-radius: 6px; overflow: hidden; position: relative;
  background: linear-gradient(180deg, #1b1b22 55%, color-mix(in srgb, var(--farbe) 45%, #1b1b22));
  border-bottom: 5px solid var(--farbe); display: flex; flex-direction: column;
  transition: transform 0.5s cubic-bezier(0.2, 1.4, 0.4, 1), box-shadow 0.5s, opacity 0.4s;
}
.item :deep(.poster) { height: 200px; }
.item .name { font-size: 0.72rem; font-weight: 600; padding: 4px 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.marke { position: absolute; z-index: 2; left: 50%; top: 0; bottom: 0; width: 3px; transform: translateX(-50%); background: #f5c518; box-shadow: 0 0 12px #f5c518; }
.marke::before, .marke::after { content: ''; position: absolute; left: 50%; transform: translateX(-50%); border: 9px solid transparent; }
.marke::before { top: 0; border-top-color: #f5c518; }
.marke::after { bottom: 0; border-bottom-color: #f5c518; }
/* The countdown sits over the strip without blacking it out, beats once a second and fades away. */
.countdown {
  position: absolute; inset: 0; z-index: 3; display: grid; place-items: center; pointer-events: none;
  background: radial-gradient(circle at center, rgba(0, 0, 0, 0.55) 0, rgba(0, 0, 0, 0.15) 45%, transparent 70%);
}
.zahl {
  font-size: 5.5rem; font-weight: 800; color: #fff; line-height: 1; font-variant-numeric: tabular-nums;
  text-shadow: 0 0 40px var(--accent), 0 2px 12px rgba(0, 0, 0, 0.6); animation: schlag 1s ease-out;
}
@keyframes schlag {
  0% { transform: scale(1.35); opacity: 0; }
  18% { transform: scale(1); opacity: 1; }
  80% { opacity: 1; }
  100% { transform: scale(0.92); opacity: 0.35; }
}
.countdown-leave-active { transition: opacity 0.45s ease-out; }
.countdown-leave-to { opacity: 0; }
.fuss .unsichtbar:disabled { opacity: 0.55; cursor: default; }

.enthuellt .item:not(.sieger) { opacity: 0.25; }
.enthuellt .item.sieger { transform: scale(1.08); box-shadow: 0 0 0 2px var(--farbe), 0 0 60px var(--farbe); z-index: 1; }

.fenster { grid-row: 2; }
.fuss { grid-row: 3; align-self: start; padding-top: 1.6rem; display: flex; flex-direction: column; align-items: center; gap: 0.9rem; }
.enthuellung { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; animation: auf 0.5s cubic-bezier(0.2, 1.4, 0.4, 1); }
.enthuellung .stufe { color: var(--farbe); font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; font-size: 0.8rem; }
.enthuellung strong { font-size: clamp(1.4rem, 4vw, 2.2rem); text-align: center; padding: 0 1rem; text-shadow: 0 0 30px var(--farbe); }
@keyframes auf { from { opacity: 0; transform: translateY(12px) scale(0.9); } }

@media (max-width: 600px) {
  .fenster { height: 210px; }
  .item { width: 110px; height: 180px; }
  .item :deep(.poster) { height: 145px; }
  .kopf { flex-wrap: wrap; }
}
@media (prefers-reduced-motion: reduce) {
  .item, .enthuellung, .zahl { transition: none; animation: none; }
}
</style>
