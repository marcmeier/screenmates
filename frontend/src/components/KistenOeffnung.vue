<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'
import Icon from './Icon.vue'
import Poster from './Poster.vue'

// The movie night's "case opening", after Counter-Strike: a strip of posters
// races past a marker, slows down and stops on the winner. The server draws the
// winner (weighted by votes, like the wheel before); the strip only animates to it.
// Rarity colours follow the real odds: the less likely a film, the rarer it looks.
const props = defineProps({ pool: { type: Array, required: true } })
const emit = defineEmits(['result'])

const SELTENHEIT = [
  { ab: 0.5, name: 'Standard', farbe: '#4b69ff' },
  { ab: 0.3, name: 'Limitiert', farbe: '#8847ff' },
  { ab: 0.18, name: 'Geheim', farbe: '#d32ce6' },
  { ab: 0.08, name: 'Verdeckt', farbe: '#eb4b4b' },
  { ab: 0, name: '★ Legendär', farbe: '#e4ae39' },
]

const gesamt = computed(() => props.pool.reduce((s, m) => s + m.gewicht, 0) || 1)
const chance = (m) => m.gewicht / gesamt.value
const seltenheit = (m) => SELTENHEIT.find((s) => chance(m) >= s.ab)
const inhalt = computed(() => [...props.pool].sort((a, b) => b.gewicht - a.gewicht))
const prozent = (m) => `${Math.round(chance(m) * 100)} %`

// --- Opening -----------------------------------------------------------------

const ANZAHL = 64 // items on the strip
const ZIEL = 56 // index of the winner on the strip
const offen = ref(false)
const phase = ref('') // 'laeuft' | 'enthuellt'
const band = ref([])
const gewinner = ref(null)
const versatz = ref(0)
const fenster = ref(null)
const itemBreite = ref(150)
let raf = 0
let ueberspringen = null

const wenigerBewegung = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function ziehen() {
  let r = Math.random() * gesamt.value
  for (const m of props.pool) if ((r -= m.gewicht) < 0) return m
  return props.pool.at(-1)
}

function bandBauen(sieger) {
  const items = Array.from({ length: ANZAHL }, ziehen)
  items[ZIEL] = sieger
  // A near miss now and then: the rarest film right next to the winner.
  const seltenster = inhalt.value.at(-1)
  if (props.pool.length > 1 && seltenster.id !== sieger.id && Math.random() < 0.5) {
    items[ZIEL + (Math.random() < 0.5 ? -1 : 1)] = seltenster
  }
  return items.map((m, i) => ({ m, key: `${i}-${m.id}` }))
}

// --- Sound (WebAudio, no files) ------------------------------------------------

const TON_KEY = 'screenmates.kisteTon'
const ton = ref(true)
try {
  ton.value = localStorage.getItem(TON_KEY) !== 'aus'
} catch {
  /* private mode: sound stays on */
}
function tonUmschalten() {
  ton.value = !ton.value
  try {
    localStorage.setItem(TON_KEY, ton.value ? 'an' : 'aus')
  } catch {
    /* ignore */
  }
}
let audio = null
function klang(freq, dauer, typ = 'square', lautst = 0.05, start = 0) {
  if (!ton.value) return
  audio ??= new (window.AudioContext || window.webkitAudioContext)()
  const t = audio.currentTime + start
  const osc = audio.createOscillator()
  const gain = audio.createGain()
  osc.type = typ
  osc.frequency.setValueAtTime(freq, t)
  gain.gain.setValueAtTime(lautst, t)
  gain.gain.exponentialRampToValueAtTime(0.0001, t + dauer)
  osc.connect(gain).connect(audio.destination)
  osc.start(t)
  osc.stop(t + dauer)
}
const tick = () => klang(1400, 0.03, 'square', 0.035)
function fanfare(farbe) {
  const hoch = farbe === SELTENHEIT.at(-1).farbe ? 1.5 : 1 // legendary sounds brighter
  ;[523, 659, 784, 1047].forEach((f, i) => klang(f * hoch, 0.45, 'triangle', 0.08, i * 0.09))
}

// --- Animation ------------------------------------------------------------------

// Fast start, very long slowdown – the part everyone stares at.
const ease = (x) => 1 - Math.pow(1 - x, 4.2)

async function oeffnen() {
  if (offen.value || !props.pool.length) return
  // Browsers only allow sound that starts with a click: create the audio now, not later.
  if (ton.value) audio ??= new (window.AudioContext || window.webkitAudioContext)()
  // Few distinct posters, many copies on the strip: load them before it starts moving.
  for (const m of props.pool) if (m.poster_url) new Image().src = m.poster_url
  const { pick } = await api.post('/api/spin')
  if (!pick) return
  gewinner.value = pick
  band.value = bandBauen(pick)
  versatz.value = 0
  phase.value = 'laeuft'
  offen.value = true
  await nextTick()
  audio?.resume?.()

  const breite = fenster.value.clientWidth
  itemBreite.value = fenster.value.querySelector('.item')?.offsetWidth + 8 || 158
  const w = itemBreite.value
  // Land somewhere on the winner, not always dead centre.
  const jitter = (Math.random() - 0.5) * (w - 8) * 0.8
  const ende = ZIEL * w + w / 2 - breite / 2 + jitter
  const dauer = wenigerBewegung() ? 1500 : 6800
  const t0 = performance.now()
  let letztes = -1

  await new Promise((fertig) => {
    ueberspringen = () => {
      cancelAnimationFrame(raf)
      versatz.value = ende
      fertig()
    }
    const schritt = (jetzt) => {
      const x = Math.min(1, (jetzt - t0) / dauer)
      versatz.value = ende * ease(x)
      const unterMarke = Math.floor((versatz.value + breite / 2) / w)
      if (unterMarke !== letztes) {
        if (letztes >= 0) tick()
        letztes = unterMarke
      }
      if (x < 1) raf = requestAnimationFrame(schritt)
      else fertig()
    }
    raf = requestAnimationFrame(schritt)
  })
  ueberspringen = null
  await new Promise((r) => setTimeout(r, wenigerBewegung() ? 100 : 450))
  phase.value = 'enthuellt'
  fanfare(seltenheit(pick).farbe)
}

function schliessen() {
  if (phase.value === 'laeuft') return ueberspringen?.()
  offen.value = false
  phase.value = ''
  emit('result', gewinner.value)
}

function taste(e) {
  if (!offen.value) return
  if (e.key === 'Escape' || (e.key === 'Enter' && phase.value === 'enthuellt')) {
    e.preventDefault()
    schliessen()
  }
}
window.addEventListener('keydown', taste)
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('keydown', taste)
  audio?.close?.()
})
</script>

<template>
  <div class="kiste">
    <ul class="inhalt" :aria-label="`Kiste mit ${pool.length} ${pool.length === 1 ? 'Film' : 'Filmen'}`">
      <li v-for="m in inhalt" :key="m.id" :style="{ '--farbe': seltenheit(m).farbe }">
        <span class="mini"><Poster :movie="m" :title="false" /></span>
        <span class="titel">{{ m.title }}</span>
        <span class="chance">{{ prozent(m) }}</span>
      </li>
    </ul>
    <button class="primary oeffnen" :disabled="offen" @click="oeffnen"><Icon name="kiste" :size="18" /> Kiste öffnen</button>

    <Teleport to="body">
      <div v-if="offen" class="buehne" role="dialog" aria-modal="true" aria-label="Kiste öffnen" :class="phase">
        <div class="kopf">
          <span class="label">Filmabend-Kiste</span>
          <span class="spacer"></span>
          <button class="ghost" :aria-label="ton ? 'Ton aus' : 'Ton an'" @click="tonUmschalten"><Icon :name="ton ? 'ton' : 'stumm'" /></button>
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
        </div>

        <div class="fuss" aria-live="polite">
          <template v-if="phase === 'enthuellt'">
            <div class="enthuellung" :style="{ '--farbe': seltenheit(gewinner).farbe }">
              <span class="stufe">{{ seltenheit(gewinner).name }} · {{ prozent(gewinner) }}</span>
              <strong>{{ gewinner.title }}</strong>
            </div>
            <button class="primary" @click="schliessen">Weiter</button>
          </template>
          <button v-else class="ghost" @click="schliessen">Überspringen</button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.inhalt { list-style: none; margin: 0 0 1rem; padding: 0; display: flex; flex-direction: column; gap: 0.35rem; }
.inhalt li {
  display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 0.6rem; padding: 0.3rem 0.6rem 0.3rem 0.3rem;
  border-radius: 6px; background: linear-gradient(90deg, color-mix(in srgb, var(--farbe) 22%, transparent), transparent 70%);
  border-left: 3px solid var(--farbe); font-size: 0.86rem;
}
.mini { width: 28px; height: 42px; border-radius: 3px; overflow: hidden; display: block; background: var(--bg-raised); }
.titel { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chance { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 0.8rem; }
.oeffnen { width: 100%; justify-content: center; padding: 0.7rem; font-size: 1rem; }

.buehne {
  position: fixed; inset: 0; z-index: 200; display: flex; flex-direction: column; justify-content: center; gap: 1.6rem;
  background: radial-gradient(ellipse at center, rgba(30, 30, 40, 0.97), rgba(5, 5, 8, 0.98)); backdrop-filter: blur(6px);
}
.kopf { position: absolute; top: 0; left: 0; right: 0; display: flex; align-items: center; padding: 1rem 1.4rem; }
.label { font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); font-size: 0.85rem; }

.fenster {
  position: relative; overflow: hidden; height: 270px; border-block: 1px solid rgba(255, 255, 255, 0.08);
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

.enthuellt .item:not(.sieger) { opacity: 0.25; }
.enthuellt .item.sieger { transform: scale(1.08); box-shadow: 0 0 0 2px var(--farbe), 0 0 60px var(--farbe); z-index: 1; }

.fuss { min-height: 110px; display: flex; flex-direction: column; align-items: center; gap: 0.9rem; }
.enthuellung { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; animation: auf 0.5s cubic-bezier(0.2, 1.4, 0.4, 1); }
.enthuellung .stufe { color: var(--farbe); font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; font-size: 0.8rem; }
.enthuellung strong { font-size: clamp(1.4rem, 4vw, 2.2rem); text-align: center; padding: 0 1rem; text-shadow: 0 0 30px var(--farbe); }
@keyframes auf { from { opacity: 0; transform: translateY(12px) scale(0.9); } }

@media (max-width: 600px) {
  .fenster { height: 210px; }
  .item { width: 110px; height: 180px; }
  .item :deep(.poster) { height: 145px; }
}
@media (prefers-reduced-motion: reduce) {
  .item, .enthuellung { transition: none; animation: none; }
}
</style>
