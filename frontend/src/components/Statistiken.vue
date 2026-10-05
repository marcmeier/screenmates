<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'

// The sidebar's footer: little facts about screenmates, one after another – and after
// every two of them something going on backstage (made up, of course).
const app = useApp()
const fakten = ref([])
const schritt = ref(0) // counts every change, also the key for the transition
const naechsterFakt = ref(0)
const aktuell = ref(null)
let wechsel = null
let laden = null

const HINTER_DEN_KULISSEN = [
  '🍿 Popcorn wird vorbereitet …',
  '🟥 Der rote Teppich wird ausgerollt …',
  '🕊️ Tauben werden von der Datenleitung verscheucht …',
  '🎞️ Filmrollen werden zurückgespult …',
  '🧹 Krümel werden aus dem Sofa gesaugt …',
  '🔦 Platzanweiser suchen ihre Taschenlampen …',
  '🥤 Strohhalme werden sortiert (nach Farbe)',
  '🎟️ Kinokarten werden abgerissen …',
  '📼 VHS-Kassetten werden höflich gebeten, zurückgespult zu werden',
  '🛋️ Die beste Sofaecke wird schon mal reserviert …',
  '🔇 Handys werden auf lautlos gestellt …',
  '🐈 Die Katze wird vom Laptop-Kabel gelockt …',
  '📡 Pixel werden nachgezählt – alle da',
  '🧂 Popcorn: süß oder salzig? Gremium tagt noch …',
  '🎬 Der Regisseur sucht seinen Stuhl …',
  '🌀 Spoiler werden aus dem Gruppenchat gefegt …',
  '🍕 Pizzaboten werden auf Spoiler geprüft …',
  '🧦 Kuschelsocken werden vorgewärmt …',
  '🦉 Nachteulen werden geweckt …',
  '🔊 Der Bass wird den Nachbarn schonend beigebracht …',
  '🎻 Das Orchester stimmt die Abspannmusik …',
  '🕯️ Das Licht wird langsam gedimmt …',
  '🧊 Getränke werden auf Filmtemperatur gebracht …',
  '🤫 Leute, die bei Filmen reden, werden sanft ermahnt …',
  '🦖 Der Dinosaurier aus dem Trailer wird wieder eingefangen …',
]
let letzterSpass = -1
function spass() {
  let n
  do n = Math.floor(Math.random() * HINTER_DEN_KULISSEN.length)
  while (n === letzterSpass && HINTER_DEN_KULISSEN.length > 1)
  letzterSpass = n
  return { text: HINTER_DEN_KULISSEN[n], spass: true }
}

async function holen() {
  try {
    fakten.value = (await api.get('/api/statistik', { quiet: true })).fakten
    aktuell.value ??= fakten.value[0] ?? spass()
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
  schritt.value++
  if (schritt.value % 3 === 2 || !fakten.value.length) {
    aktuell.value = spass()
  } else {
    naechsterFakt.value = (naechsterFakt.value + 1) % fakten.value.length
    aktuell.value = fakten.value[naechsterFakt.value]
  }
}
const fakt = computed(() => aktuell.value)
</script>

<template>
  <div class="statistik">
    <button v-if="fakt" class="fakt" title="Weiter" @click="weiter">
      <Transition name="blende" mode="out-in">
        <span v-if="fakt.spass" :key="`s${schritt}`" class="spass">{{ fakt.text }}</span>
        <span v-else :key="schritt"><strong>{{ fakt.wert }}</strong> {{ fakt.text }}</span>
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
.spass { font-style: italic; }
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
