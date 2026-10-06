<script setup>
import { computed, ref } from 'vue'
import { api } from '../api'
import { useKiste } from '../stores/kiste'
import { seltenheitFuer } from '../seltenheit'
import Icon from './Icon.vue'
import { audioJetzt } from '../audio'
import Poster from './Poster.vue'

// The movie night's case on the evening page: what's inside and with which odds.
// The host (or a group admin) opens it for everyone; anyone can spin on their own
// as practice. The opening itself plays in KistenBuehne (see GemeinsameKiste).
// `kompakt`: the odds are shown at the suggestions, so the list here can go.
const props = defineProps({ pool: { type: Array, required: true }, kompakt: { type: Boolean, default: false } })
const kiste = useKiste()
const busy = ref(false)

const gesamt = computed(() => props.pool.reduce((s, m) => s + m.gewicht, 0) || 1)
const chance = (m) => m.gewicht / gesamt.value
const inhalt = computed(() => [...props.pool].sort((a, b) => b.gewicht - a.gewicht))
const prozent = (m) => `${Math.round(chance(m) * 100)} %`
const laeuft = computed(() => !!(kiste.buehne || kiste.probe))

async function fuerAlle() {
  audioJetzt() // inside the click: the only moment an iPhone lets sound start
  busy.value = true
  try {
    await kiste.oeffnen()
  } finally {
    busy.value = false
  }
}

async function probe() {
  audioJetzt()
  busy.value = true
  try {
    const { pick, pool } = await api.post('/api/spin')
    if (pick) kiste.probe = { pool, gewinner: pick, seed: Math.floor(Math.random() * 2 ** 31), start: Date.now() + 300 }
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="kiste">
    <ul v-if="!kompakt" class="inhalt" :aria-label="$t('kistenoeffnung.kisteMit', { n: pool.length }, pool.length)">
      <li v-for="m in inhalt" :key="m.id" :style="{ '--farbe': seltenheitFuer(chance(m)).farbe }">
        <span class="mini"><Poster :movie="m" :title="false" /></span>
        <span class="titel">{{ m.title }}</span>
        <span class="chance">{{ prozent(m) }}</span>
      </li>
    </ul>
    <template v-if="kiste.darfOeffnen">
      <button class="primary oeffnen" :disabled="busy || laeuft" @click="fuerAlle"><Icon name="kiste" :size="18" /> {{ $t('kistenoeffnung.fuerAlleOeffnen') }}</button>
      <button class="ghost small probe" :disabled="busy || laeuft" @click="probe">{{ $t('kistenoeffnung.probedrehenNurFuerMich') }}</button>
    </template>
    <template v-else>
      <button class="oeffnen" :disabled="busy || laeuft" @click="probe"><Icon name="kiste" :size="18" /> {{ $t('kistenoeffnung.probedrehen') }}</button>
      <p class="muted hinweis">{{ $t('kistenoeffnung.fuerAlleOeffnetDer') }}</p>
    </template>
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
.probe { width: 100%; justify-content: center; margin-top: 0.3rem; }
.hinweis { font-size: 0.8rem; margin: 0.5rem 0 0; text-align: center; }
</style>
