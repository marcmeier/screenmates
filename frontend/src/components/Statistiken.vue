<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'

// The sidebar's footer: little facts about screenmates, one after another.
const app = useApp()
const fakten = ref([])
const i = ref(0)
let wechsel = null
let laden = null

async function holen() {
  try {
    fakten.value = (await api.get('/api/statistik', { quiet: true })).fakten
  } catch {
    /* keep the old ones */
  }
}
onMounted(() => {
  holen()
  laden = setInterval(holen, 5 * 60_000)
  wechsel = setInterval(() => weiter(), 7000)
})
onBeforeUnmount(() => {
  clearInterval(wechsel)
  clearInterval(laden)
})
function weiter() {
  if (fakten.value.length) i.value = (i.value + 1) % fakten.value.length
}
const fakt = computed(() => fakten.value[i.value % Math.max(1, fakten.value.length)])
</script>

<template>
  <div class="statistik">
    <button v-if="fakt" class="fakt" title="Nächste Zahl" @click="weiter">
      <Transition name="blende" mode="out-in">
        <span :key="i"><strong>{{ fakt.wert }}</strong> {{ fakt.text }}</span>
      </Transition>
    </button>
    <span v-if="!app.status.tmdb" class="warn">Demo-Katalog · TMDB nicht verbunden</span>
    <a href="#/ueber" class="ueber">Über · Impressum</a>
  </div>
</template>

<style scoped>
.statistik { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.75rem; color: var(--muted); }
.fakt {
  all: unset; cursor: pointer; display: block; min-height: 2.2em; line-height: 1.35;
}
.fakt strong { color: var(--text); font-variant-numeric: tabular-nums; }
.fakt:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.warn { color: var(--gold); }
.ueber { color: var(--muted); text-decoration: none; font-size: 0.72rem; }
.ueber:hover { color: var(--text); text-decoration: underline; }
.blende-enter-active, .blende-leave-active { transition: opacity 0.35s, transform 0.35s; }
.blende-enter-from { opacity: 0; transform: translateY(4px); }
.blende-leave-to { opacity: 0; transform: translateY(-4px); }
@media (prefers-reduced-motion: reduce) {
  .blende-enter-active, .blende-leave-active { transition: none; }
}
</style>
