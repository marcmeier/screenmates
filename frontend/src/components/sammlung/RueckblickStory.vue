<script setup>
import { t as tr } from '../../i18n'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApp } from '../../stores/app'
import { FILME, TITEL, monatName, n, sterne, stunden, wochentagName } from '../../rueckblick'
import Icon from '../Icon.vue'
import Poster from '../Poster.vue'
import UserAvatar from '../UserAvatar.vue'

// The year as a story: one card at a time, on by itself, tap right for the next,
// left for the previous, hold to pause.
const props = defineProps({ daten: { type: Object, required: true } })
const emit = defineEmits(['close'])
const app = useApp()
const DAUER = 6000
const name = (id) => app.userById(id)?.name ?? tr('allg.jemand')

const karten = computed(() => {
  const d = props.daten
  const k = [{ art: 'start' }, { art: 'zahlen' }]
  if (d.genres.length) k.push({ art: 'genres' })
  for (const f of FILME.slice(0, 4)) if (d[f.key]) k.push({ art: 'film', f })
  const titel = TITEL.filter((t) => d.titel[t.key])
  if (titel.length) k.push({ art: 'titel', titel })
  k.push({ art: 'rekorde' })
  k.push({ art: 'ende' })
  return k
})
const i = ref(0)
const pause = ref(false)
const fortschritt = ref(0)
let start = performance.now()
let schon = 0
let rahmen = null

function zeigen(j) {
  if (j < 0) j = 0
  if (j >= karten.value.length) return emit('close')
  i.value = j
  schon = 0
  start = performance.now()
  fortschritt.value = 0
}
function laufen(t) {
  if (!pause.value) {
    fortschritt.value = Math.min(1, (schon + t - start) / DAUER)
    if (fortschritt.value >= 1 && i.value < karten.value.length - 1) zeigen(i.value + 1)
  }
  rahmen = requestAnimationFrame(laufen)
}
watch(pause, (p) => {
  if (p) schon += performance.now() - start
  else start = performance.now()
})

// Holding pauses; letting go after a hold only resumes, it doesn't skip.
let gedrueckt = 0
function halten() {
  gedrueckt = performance.now()
  pause.value = true
}
function tippen(e) {
  if (performance.now() - gedrueckt > 350) return
  const links = e.clientX < window.innerWidth / 3
  zeigen(i.value + (links ? -1 : 1))
}
function taste(e) {
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowRight' || e.key === ' ') zeigen(i.value + 1)
  else if (e.key === 'ArrowLeft') zeigen(i.value - 1)
  else return
  e.preventDefault()
}
onMounted(() => {
  window.addEventListener('keydown', taste)
  document.body.style.overflow = 'hidden'
  rahmen = requestAnimationFrame(laufen)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', taste)
  document.body.style.overflow = ''
  cancelAnimationFrame(rahmen)
})
const karte = computed(() => karten.value[i.value])
</script>

<template>
  <Teleport to="body">
    <div class="story" role="dialog" aria-modal="true" :aria-label="$t('rueckblickstory.euerFilmjahrJahr', { jahr: daten.jahr })">
      <div class="balken" aria-hidden="true">
        <span v-for="(k, j) in karten" :key="j"><span :style="{ width: `${j < i ? 100 : j === i ? fortschritt * 100 : 0}%` }"></span></span>
      </div>
      <button class="zu ghost" :aria-label="$t('rueckblickstory.schliessen')" @click="emit('close')"><Icon name="x" /></button>

      <div
        class="buehne"
        :class="`karte-${karte.art} farbe-${i % 4}`"
        @click="tippen"
        @pointerdown="halten"
        @pointerup="pause = false"
        @pointerleave="pause = false"
      >
        <Transition name="karte" mode="out-in">
          <div :key="i" class="inhalt" aria-live="polite">
            <template v-if="karte.art === 'start'">
              <span class="klein">{{ app.gruppe?.name }}</span>
              <h2 class="riesig">{{ daten.jahr }}</h2>
              <p class="gross">{{ $t('rueckblickstory.euerFilmjahr') }}<br />{{ $t('rueckblickstory.tipptEuchDurch') }}</p>
            </template>

            <template v-else-if="karte.art === 'zahlen'">
              <p class="gross">{{ $t('rueckblickstory.ihrHabt') }}</p>
              <h2 class="riesig">{{ n(daten.filme) }}</h2>
              <p class="gross">{{ $t(daten.filme === 1 ? 'rueckblickstory.geschautFilm' : 'rueckblickstory.geschautFilme', { abende: n(daten.abende) }, daten.abende) }}</p>
              <p class="mittel">{{ $t('rueckblickstory.dasSind') }} <strong>{{ $t('rueckblickstory.stunden', { n: n(stunden(daten.minuten)) }) }}</strong> {{ $t('rueckblickstory.sofa') }}</p>
            </template>

            <template v-else-if="karte.art === 'genres'">
              <p class="gross">{{ $t('rueckblickstory.euerGenreWar') }}</p>
              <h2 class="riesig wort">{{ daten.genres[0].name }}</h2>
              <ol class="liste">
                <li v-for="(g, j) in daten.genres.slice(1, 5)" :key="g.name"><span>{{ j + 2 }}</span> {{ g.name }} <em>{{ g.anzahl }}</em></li>
              </ol>
            </template>

            <template v-else-if="karte.art === 'film'">
              <span class="klein">{{ karte.f.name }}</span>
              <div class="plakat"><Poster :movie="daten[karte.f.key].movie" /></div>
              <h2 class="titel">{{ daten[karte.f.key].movie.title }}</h2>
              <p class="mittel">{{ karte.f.text(daten[karte.f.key], name) }}</p>
            </template>

            <template v-else-if="karte.art === 'titel'">
              <p class="gross">{{ $t('rueckblickstory.undDieAuszeichnungenGehen') }}</p>
              <ul class="preise">
                <li v-for="t in karte.titel" :key="t.key">
                  <span class="emoji">{{ t.emoji }}</span>
                  <UserAvatar :user-id="daten.titel[t.key].user_id" />
                  <div><strong>{{ name(daten.titel[t.key].user_id) }}</strong><span>{{ t.name }} · {{ t.einheit(daten.titel[t.key].wert) }}</span></div>
                </li>
              </ul>
            </template>

            <template v-else-if="karte.art === 'rekorde'">
              <p class="gross">{{ $t('rueckblickstory.rekorde') }}</p>
              <ul class="rekorde">
                <li><strong>{{ n(daten.serie) }}</strong> {{ $t('rueckblickstory.serie', daten.serie) }}</li>
                <li><strong>{{ wochentagName(daten.wochentag) }}</strong> {{ $t('rueckblickstory.tag') }}</li>
                <li><strong>{{ monatName(daten.monat) }}</strong> {{ $t('rueckblickstory.monat', { n: n(daten.monat.anzahl) }) }}</li>
                <li v-if="daten.schnitt"><strong>{{ sterne(daten.schnitt) }}</strong> {{ $t('rueckblickstory.imSchnittAusX', { x: n(daten.bewertungen) }) }}</li>
                <li v-if="daten.kisten"><strong>{{ n(daten.kisten) }}</strong> {{ $t('rueckblickstory.kisten', daten.kisten) }}</li>
                <li v-if="daten.herzen"><strong>{{ n(daten.herzen) }}</strong> {{ $t('rueckblickstory.herzenImGaestebuch') }}</li>
              </ul>
            </template>

            <template v-else>
              <h2 class="riesig wort">{{ $t('rueckblickstory.danke') }}</h2>
              <p class="gross">{{ $t('rueckblickstory.aufEinNeuesFilmjahr') }}</p>
              <div class="row ende" @click.stop>
                <button @click="zeigen(0)"><Icon name="sync" :size="16" /> {{ $t('rueckblickstory.nochmal') }}</button>
                <button class="primary" @click="emit('close')">{{ $t('rueckblickstory.fertig') }}</button>
              </div>
            </template>
          </div>
        </Transition>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.story {
  position: fixed; inset: 0; z-index: 70; background: #000; display: flex; justify-content: center;
  animation: auf 0.25s ease-out;
}
@keyframes auf { from { opacity: 0; } }
.balken { position: absolute; top: 10px; left: 50%; transform: translateX(-50%); width: min(560px, 94vw); display: flex; gap: 4px; z-index: 2; }
.balken > span { flex: 1; height: 3px; border-radius: 2px; background: rgba(255, 255, 255, 0.25); overflow: hidden; }
.balken > span > span { display: block; height: 100%; background: #fff; }
.zu { position: absolute; top: 20px; right: max(12px, calc(50% - 290px)); z-index: 3; color: #fff; }
.buehne {
  width: min(560px, 100vw); height: 100%; display: flex; align-items: center; justify-content: center; padding: 3.5rem 1.8rem 2rem;
  user-select: none; cursor: pointer; color: #fff; text-align: center; transition: background 0.5s;
}
.farbe-0 { background: radial-gradient(120% 80% at 10% 0%, #e50914 0%, #3b0306 55%, #0a0a0c 100%); }
.farbe-1 { background: radial-gradient(120% 80% at 90% 10%, #f5a623 0%, #5a2a00 50%, #0a0a0c 100%); }
.farbe-2 { background: radial-gradient(120% 80% at 50% 0%, #8e2de2 0%, #2a0845 55%, #0a0a0c 100%); }
.farbe-3 { background: radial-gradient(120% 80% at 0% 100%, #11998e 0%, #053b36 55%, #0a0a0c 100%); }
.inhalt { display: flex; flex-direction: column; align-items: center; gap: 0.8rem; width: 100%; }
.klein { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.14em; font-weight: 700; opacity: 0.8; }
.riesig { margin: 0; font-size: clamp(4.5rem, 24vw, 8.5rem); font-weight: 900; letter-spacing: -0.05em; line-height: 0.95; }
.riesig.wort { font-size: clamp(2.8rem, 13vw, 4.6rem); letter-spacing: -0.03em; }
.gross { margin: 0; font-size: clamp(1.25rem, 5vw, 1.7rem); font-weight: 700; line-height: 1.25; }
.mittel { margin: 0; font-size: 1.05rem; opacity: 0.9; }
.titel { margin: 0; font-size: 1.7rem; letter-spacing: -0.02em; }
.plakat { width: min(240px, 58vw); aspect-ratio: 2 / 3; border-radius: 14px; overflow: hidden; box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6); }
.liste { list-style: none; margin: 0.5rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; font-size: 1.1rem; font-weight: 600; }
.liste span { opacity: 0.6; margin-right: 0.4rem; }
.liste em { font-style: normal; opacity: 0.6; margin-left: 0.4rem; }
.preise, .rekorde { list-style: none; margin: 0.6rem 0 0; padding: 0; display: flex; flex-direction: column; gap: 0.75rem; text-align: left; width: 100%; }
.preise li { display: flex; align-items: center; gap: 0.7rem; background: rgba(0, 0, 0, 0.25); padding: 0.55rem 0.8rem; border-radius: 12px; }
.preise .emoji { font-size: 1.5rem; }
.preise .avatar { width: 34px; height: 34px; }
.preise div { display: flex; flex-direction: column; }
.preise span { font-size: 0.85rem; opacity: 0.85; }
.rekorde li { font-size: 1.05rem; background: rgba(0, 0, 0, 0.25); padding: 0.6rem 0.9rem; border-radius: 12px; }
.rekorde strong { font-size: 1.3rem; margin-right: 0.3rem; }
.ende { justify-content: center; margin-top: 1rem; }
.karte-enter-active, .karte-leave-active { transition: opacity 0.25s, transform 0.25s; }
.karte-enter-from { opacity: 0; transform: translateY(14px) scale(0.98); }
.karte-leave-to { opacity: 0; transform: translateY(-10px); }
@media (prefers-reduced-motion: reduce) { .karte-enter-active, .karte-leave-active { transition: none; } }
</style>