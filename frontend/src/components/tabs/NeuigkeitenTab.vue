<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import { ereignisText } from '../../aktivitaet'
import Icon from '../Icon.vue'

// Everything that is news, on its own page: what screenmates told you (the bell), and
// what happened in the group – new since your last visit first, the rest folded away.
const app = useApp()
const ui = useUi()
const meine = ref(null)
const events = ref([])
const alleZeigen = ref(false)

const GESEHEN = () => `screenmates.feedGesehen.${app.gruppe?.id}`
function feedStand() {
  try {
    return Number(localStorage.getItem(GESEHEN())) || 0
  } catch {
    return 0
  }
}
const zuletzt = ref(feedStand())

async function laden() {
  const [g, e] = await Promise.all([
    api.get('/api/glocke'),
    app.gruppe ? api.get('/api/events?limit=50') : Promise.resolve({ events: [] }),
  ])
  meine.value = g.eintraege
  events.value = e.events
  if (g.ungelesen) {
    await api.post('/api/glocke/gelesen', undefined, { quiet: true }).catch(() => {})
    app.glocke = 0
  }
}
onMounted(laden)
watch(() => ui.changes, laden)
onBeforeUnmount(() => {
  try {
    localStorage.setItem(GESEHEN(), String(Date.now()))
  } catch {
    /* private mode */
  }
})

const neu = (e) => zuletzt.value && new Date(e.at).getTime() > zuletzt.value
const neueEvents = computed(() => events.value.filter(neu))
const sichtbare = computed(() => {
  if (alleZeigen.value) return events.value
  return neueEvents.value.length ? neueEvents.value : events.value.slice(0, 8)
})
function oeffnen(e) {
  if (e.url) location.hash = new URL(e.url, location.origin).hash
}
</script>

<template>
  <div class="seite">
    <header class="page-head">
      <div>
        <h1>Neuigkeiten</h1>
        <p>Was dir screenmates mitgeteilt hat – und was in der Gruppe passiert ist.</p>
      </div>
    </header>

    <section class="panel" aria-labelledby="fuer-dich">
      <h2 id="fuer-dich"><Icon name="glocke" :size="17" /> Für dich</h2>
      <div v-if="meine === null" class="skeleton" style="height: 80px"></div>
      <p v-else-if="!meine.length" class="muted">Noch nichts – hier landet, was screenmates dir mitteilt, auch ohne Push.</p>
      <ul v-else class="liste">
        <li v-for="b in meine" :key="b.id" :class="{ neu: b.neu }">
          <button class="eintrag" @click="oeffnen(b)">
            <strong>{{ b.titel }}</strong>
            <span v-if="b.text" class="muted">{{ b.text }}</span>
          </button>
          <time class="muted" :datetime="b.am">{{ vorWann(b.am) }}</time>
        </li>
      </ul>
    </section>

    <section v-if="app.gruppe" class="panel" aria-labelledby="in-der-gruppe">
      <h2 id="in-der-gruppe">
        <Icon name="personen" :size="17" /> In der Gruppe
        <span v-if="neueEvents.length" class="neu-zahl">{{ neueEvents.length }} neu seit deinem letzten Besuch</span>
      </h2>
      <ul v-if="events.length" class="feed">
        <li v-for="(e, i) in sichtbare" :key="i" :class="{ neu: neu(e) }">
          <span>{{ ereignisText(e) }}</span>
          <time class="muted" :datetime="e.at">{{ vorWann(e.at) }}</time>
        </li>
      </ul>
      <p v-else class="muted">Hier passiert noch nichts.</p>
      <button v-if="events.length > sichtbare.length" class="ghost small" @click="alleZeigen = true">
        Ältere Aktivität ({{ events.length - sichtbare.length }})
      </button>
    </section>
  </div>
</template>

<style scoped>
.seite { max-width: 820px; display: flex; flex-direction: column; gap: 1.2rem; }
h2 { margin: 0 0 0.8rem; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.neu-zahl { font-size: 0.75rem; font-weight: 600; color: var(--accent); }
.liste, .feed { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.liste li, .feed li { display: flex; gap: 1rem; justify-content: space-between; align-items: flex-start; padding: 0.55rem 0; border-bottom: 1px solid var(--line); font-size: 0.88rem; }
.liste li:last-child, .feed li:last-child { border-bottom: none; }
.eintrag { all: unset; cursor: pointer; display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
.eintrag:hover strong { text-decoration: underline; }
time { flex: none; font-size: 0.78rem; }
/* New since you last looked: a red dot in front. */
.liste li.neu strong::before, .feed li.neu span::before {
  content: ''; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--accent); margin-right: 0.5rem; vertical-align: middle;
}
</style>