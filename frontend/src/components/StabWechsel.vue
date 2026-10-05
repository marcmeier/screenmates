<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useApp } from '../stores/app'
import { useGastgeber } from '../stores/gastgeber'
import { useKiste } from '../stores/kiste'

// A change of hands in progress, wherever you are in the app: the offer to the one
// who'd get the baton, the vote for everyone present, the tally for the candidate.
const app = useApp()
const g = useGastgeber()
const kiste = useKiste()
const jetzt = ref(Date.now())
let uhr = null
onMounted(() => (uhr = setInterval(() => (jetzt.value = Date.now()), 500)))
onBeforeUnmount(() => clearInterval(uhr))

const w = computed(() => g.wechsel)
const name = (id) => app.userById(id)?.name || 'Jemand'
const rest = computed(() => Math.max(0, Math.ceil((w.value.frist - kiste.versatz - jetzt.value) / 1000)))
const zeit = computed(() => `${Math.floor(rest.value / 60)}:${String(rest.value % 60).padStart(2, '0')}`)
const binHost = computed(() => g.gastgeber === app.me?.id)
const art = computed(() => {
  const x = w.value
  if (!x || !app.me) return null
  if (x.art === 'uebergabe') return x.an === app.me.id ? 'angebot' : x.von === app.me.id ? 'warte' : null
  if (x.an === app.me.id) return 'kandidat'
  return x.darf_stimmen ? 'stimme' : x.meine != null ? 'abgestimmt' : null
})
</script>

<template>
  <Transition name="hoch">
    <div v-if="art" class="stabwechsel panel" role="alertdialog" aria-label="Gastgeber-Stab">
      <span class="stab" aria-hidden="true">🎬</span>
      <div class="text">
        <template v-if="art === 'angebot'">
          <strong>{{ name(w.von) }} reicht dir den Gastgeber-Stab.</strong>
          <span class="muted">Damit öffnest du die Kiste für alle und bespielst das Kino.</span>
        </template>
        <template v-else-if="art === 'warte'">
          <strong>Stab angeboten an {{ name(w.an) }}</strong>
          <span class="muted">Wartet auf Antwort …</span>
        </template>
        <template v-else-if="art === 'kandidat'">
          <strong>Abstimmung: Du als Gastgeber?</strong>
          <span class="muted">{{ w.ja }} Ja · {{ w.nein }} Nein – ohne Widerspruch bekommst du den Stab.</span>
        </template>
        <template v-else>
          <strong>{{ name(w.an) }} möchte den Gastgeber-Stab übernehmen.</strong>
          <span class="muted">
            {{ w.ja }} Ja · {{ w.nein }} Nein<template v-if="binHost"> · deine Stimme zählt doppelt, dein Ja entscheidet sofort</template><template v-if="art === 'abgestimmt'"> · du hast abgestimmt</template>
          </span>
        </template>
      </div>
      <span class="uhr" :aria-label="`noch ${rest} Sekunden`">{{ zeit }}</span>
      <div class="knoepfe">
        <template v-if="art === 'angebot'">
          <button class="small primary" @click="g.antworten(true)">Annehmen</button>
          <button class="small ghost" @click="g.antworten(false)">Ablehnen</button>
        </template>
        <button v-else-if="art === 'warte' || art === 'kandidat'" class="small ghost" @click="g.zurueckziehen()">Zurückziehen</button>
        <template v-else-if="art === 'stimme'">
          <button class="small primary" @click="g.antworten(true)">{{ binHost ? 'Stab übergeben' : 'Ja' }}</button>
          <button class="small ghost" @click="g.antworten(false)">Nein</button>
        </template>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.stabwechsel {
  position: fixed; z-index: 150; left: 50%; bottom: 1.2rem; transform: translateX(-50%); width: min(560px, calc(100% - 2rem));
  display: flex; align-items: center; gap: 0.8rem; padding: 0.8rem 1rem; box-shadow: var(--shadow); border-color: var(--accent);
}
.stab { font-size: 1.6rem; }
.text { flex: 1; display: flex; flex-direction: column; gap: 0.15rem; font-size: 0.88rem; min-width: 0; }
.text .muted { font-size: 0.78rem; }
.uhr { font-variant-numeric: tabular-nums; color: var(--muted); font-size: 0.85rem; }
.knoepfe { display: flex; gap: 0.35rem; }
@media (max-width: 600px) {
  .stabwechsel { flex-wrap: wrap; bottom: 4.6rem; }
  .knoepfe { width: 100%; justify-content: flex-end; }
}
.hoch-enter-active, .hoch-leave-active { transition: opacity 0.25s, transform 0.25s; }
.hoch-enter-from, .hoch-leave-to { opacity: 0; transform: translate(-50%, 12px); }
</style>
