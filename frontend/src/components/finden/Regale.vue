<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import Icon from '../Icon.vue'
import MovieCard from '../MovieCard.vue'

// Browsing without knowing what you want: shelves like a streaming service's
// start page. One per service (yours first), plus "Läuft bei uns" and a few themes.
const emit = defineEmits(['alle'])
const app = useApp()
const ui = useUi()
const regale = ref(null)
const fehler = ref(false)

async function laden() {
  fehler.value = false
  try {
    regale.value = (await api.get('/api/stoebern', { quiet: true })).regale
    await nextTick()
    for (const r of regale.value) pruefe(r.id)
  } catch {
    fehler.value = true
  }
}
onMounted(laden)
watch(() => ui.changes, laden) // seen / bookmarked flags on the cards

// Scroll arrows for mouse users; touch and trackpads just swipe.
const reihen = ref({})
const rand = ref({})
function merke(id, el) {
  if (el) reihen.value[id] = el
}
function pruefe(id) {
  const el = reihen.value[id]
  if (el) rand.value[id] = { links: el.scrollLeft > 4, rechts: el.scrollLeft + el.clientWidth < el.scrollWidth - 4 }
}
function blaettern(id, richtung) {
  const el = reihen.value[id]
  el?.scrollBy({ left: richtung * el.clientWidth * 0.85, behavior: 'smooth' })
}
const hatUns = () => regale.value?.some((r) => r.id === 'bei-uns')
</script>

<template>
  <div class="regale">
    <p v-if="regale && app.status.tmdb && !hatUns()" class="notice tipp">
      Tragt eure Streaming-Abos ein, dann zeigt screenmates hier zuerst, was bei euch ohne Aufpreis läuft.
      <a href="#/einstellungen">Zu den Einstellungen</a>
    </p>

    <template v-if="!regale && !fehler">
      <section v-for="i in 3" :key="i" class="regal">
        <div class="skeleton kopf-skeleton"></div>
        <div class="reihe"><div v-for="j in 8" :key="j" class="skeleton karte-skeleton"></div></div>
      </section>
    </template>

    <div v-else-if="fehler" class="empty">
      <strong>Die Regale ließen sich nicht laden</strong>
      <button class="small" @click="laden">Nochmal</button>
    </div>

    <section v-for="r in regale" v-else :key="r.id" class="regal" :aria-label="r.titel">
      <header>
        <img v-if="r.anbieter?.logo" :src="r.anbieter.logo" alt="" class="logo" />
        <Icon v-else-if="r.id === 'bei-uns'" name="gesehen" class="symbol uns" />
        <div class="titel">
          <h2>{{ r.titel }} <span v-if="r.unser" class="euer">Euer Abo</span></h2>
          <span class="muted">{{ r.untertitel }}</span>
        </div>
        <span class="spacer"></span>
        <button class="ghost small" @click="emit('alle', r)">Alle zeigen <Icon name="pfeil" :size="13" class="rechts" /></button>
      </header>
      <div class="rahmen">
        <button v-if="rand[r.id]?.links" class="pfeil links" aria-label="Zurückblättern" @click="blaettern(r.id, -1)">
          <Icon name="pfeil" />
        </button>
        <ul :ref="(el) => merke(r.id, el)" class="reihe" @scroll.passive="pruefe(r.id)">
          <li v-for="m in r.filme" :key="m.id"><MovieCard :movie="m" /></li>
        </ul>
        <button v-if="rand[r.id]?.rechts" class="pfeil rechts" aria-label="Weiterblättern" @click="blaettern(r.id, 1)">
          <Icon name="pfeil" />
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.regale { display: flex; flex-direction: column; gap: 1.8rem; }
.tipp a { color: inherit; margin-left: 0.4rem; }
header { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.7rem; }
.logo { width: 34px; height: 34px; border-radius: 8px; flex: none; }
.symbol { width: 34px; height: 34px; padding: 7px; border-radius: 8px; background: var(--bg-raised); flex: none; }
.symbol.uns { color: var(--ok); }
.titel { display: flex; flex-direction: column; min-width: 0; }
h2 { margin: 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; }
.titel .muted { font-size: 0.8rem; }
.euer { font-size: 0.68rem; font-weight: 700; color: var(--ok); border: 1px solid currentColor; border-radius: 99px; padding: 1px 7px; }
.rechts :deep(svg), .ghost .rechts { transform: rotate(180deg); }
.rahmen { position: relative; }
.reihe {
  list-style: none; margin: 0; padding: 0 0 6px; display: flex; gap: 0.8rem; overflow-x: auto;
  scroll-snap-type: x proximity; scrollbar-width: none; overscroll-behavior-x: contain;
}
.reihe::-webkit-scrollbar { display: none; }
.reihe li { flex: none; width: 158px; scroll-snap-align: start; }
.pfeil {
  position: absolute; z-index: 2; top: 0; bottom: 6px; width: 44px; padding: 0; justify-content: center; border: none; border-radius: 0;
  color: #fff; opacity: 0; transition: opacity 0.2s;
}
.pfeil.links { left: 0; background: linear-gradient(90deg, rgba(10, 10, 12, 0.95), transparent); }
.pfeil.rechts { right: 0; background: linear-gradient(270deg, rgba(10, 10, 12, 0.95), transparent); }
.pfeil.rechts :deep(svg) { transform: rotate(180deg); }
.rahmen:hover .pfeil, .pfeil:focus-visible { opacity: 1; }
.pfeil:hover:not(:disabled) { background-color: transparent; }
.kopf-skeleton { height: 34px; width: 240px; margin-bottom: 0.7rem; }
.karte-skeleton { flex: none; width: 158px; aspect-ratio: 2 / 3; }
@media (hover: none) {
  .pfeil { display: none; }
}
@media (max-width: 600px) {
  .reihe li, .karte-skeleton { width: 124px; }
}
</style>
