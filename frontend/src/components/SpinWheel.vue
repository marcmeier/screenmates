<script setup>
import { computed, ref } from 'vue'
import { api } from '../api'

// Segment sizes follow the server's weights (number of people who suggested a
// film), so the wheel shows the real odds. The server draws the winner; the
// wheel only animates to it.
const props = defineProps({ pool: { type: Array, required: true } })
const emit = defineEmits(['result'])

const SIZE = 320
const C = SIZE / 2
const R = C - 6
const COLORS = ['#7a0a10', '#1f1f27', '#a30d17', '#2a2a33', '#5c070c', '#18181e']

const rotation = ref(0)
const spinning = ref(false)

const segments = computed(() => {
  const total = props.pool.reduce((s, m) => s + m.gewicht, 0) || 1
  let start = 0
  return props.pool.map((m, i) => {
    const sweep = (360 * m.gewicht) / total
    const seg = { movie: m, start, sweep, center: start + sweep / 2, color: COLORS[i % COLORS.length] }
    start += sweep
    return seg
  })
})

function point(deg, r = R) {
  const rad = (deg * Math.PI) / 180
  return [C + r * Math.sin(rad), C - r * Math.cos(rad)]
}

function arc(seg) {
  const [x1, y1] = point(seg.start)
  const [x2, y2] = point(seg.start + seg.sweep)
  const large = seg.sweep > 180 ? 1 : 0
  return `M${C},${C} L${x1},${y1} A${R},${R} 0 ${large} 1 ${x2},${y2} Z`
}

const short = (t) => (t.length > 18 ? t.slice(0, 17) + '…' : t)

// Labels run along their radius. Those that end up on the left half (judged by
// where the wheel comes to rest) are turned around so they never read upside down.
function labelTransform(seg) {
  const resting = (((seg.center + rotation.value) % 360) + 360) % 360
  const flip = resting > 180
  return {
    transform: `rotate(${seg.center + (flip ? 90 : -90)} ${C} ${C})`,
    x: flip ? C - 34 : C + 34,
    anchor: flip ? 'end' : 'start',
  }
}

async function spin() {
  if (spinning.value || !props.pool.length) return
  spinning.value = true
  try {
    const { pick } = await api.post('/api/spin')
    const seg = segments.value.find((s) => s.movie.id === pick.id) || segments.value[0]
    const jitter = (Math.random() - 0.5) * seg.sweep * 0.7
    const target = 360 - ((seg.center + jitter) % 360)
    const current = rotation.value % 360
    rotation.value += 360 * 6 + ((target - current + 360) % 360)
    setTimeout(() => {
      spinning.value = false
      emit('result', pick)
    }, 4600)
  } catch {
    spinning.value = false
  }
}
</script>

<template>
  <div class="wheel">
    <div class="pointer" aria-hidden="true"></div>
    <svg
      :viewBox="`0 0 ${SIZE} ${SIZE}`"
      :style="{ transform: `rotate(${rotation}deg)` }"
      role="img"
      :aria-label="`Glücksrad mit ${pool.length} Filmen`"
    >
      <circle v-if="segments.length === 1" :cx="C" :cy="C" :r="R" :fill="COLORS[0]" />
      <template v-else>
        <path v-for="s in segments" :key="s.movie.id" :d="arc(s)" :fill="s.color" stroke="#0a0a0c" stroke-width="2" />
      </template>
      <template v-if="segments.length > 1">
        <g v-for="s in segments" :key="'t' + s.movie.id" :transform="labelTransform(s).transform">
          <text :x="labelTransform(s).x" :y="C" :text-anchor="labelTransform(s).anchor" dominant-baseline="middle" class="label">
            {{ short(s.movie.title) }}
          </text>
        </g>
      </template>
      <circle :cx="C" :cy="C" r="26" fill="#0a0a0c" stroke="#e50914" stroke-width="3" />
    </svg>
    <div v-if="segments.length === 1" class="single">{{ pool[0].title }}</div>
    <button class="primary spin" :disabled="spinning || !pool.length" @click="spin">
      {{ spinning ? 'Dreht …' : 'Drehen' }}
    </button>
  </div>
</template>

<style scoped>
.wheel { position: relative; width: min(340px, 100%); margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
svg { width: 100%; height: auto; transition: transform 4.5s cubic-bezier(0.12, 0.8, 0.12, 1); filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.6)); }
.pointer {
  position: absolute; top: -6px; left: 50%; transform: translateX(-50%); z-index: 2;
  width: 0; height: 0; border-left: 12px solid transparent; border-right: 12px solid transparent; border-top: 22px solid var(--text);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
}
.single {
  position: absolute; left: 10%; right: 10%; top: calc(50% - 4.5rem); text-align: center;
  font-weight: 700; font-size: 1.05rem; pointer-events: none; text-shadow: 0 1px 6px rgba(0, 0, 0, 0.6);
}
.label { fill: #f2f2f6; font-size: 11px; font-weight: 600; }
.spin { min-width: 140px; justify-content: center; }
</style>
