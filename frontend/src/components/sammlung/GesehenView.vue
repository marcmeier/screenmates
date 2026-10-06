<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { datumFmt, dezimal } from '../../format'
import WatchedEntry from '../WatchedEntry.vue'

const app = useApp()
const ui = useUi()
const entries = ref([])
const loading = ref(true)
const filter = ref('')
const sort = ref('datum')

async function load() {
  try {
    entries.value = (await api.get(`/api/watched?alle=${app.gruppenAdmin}`)).watched
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => [ui.changes, app.gruppenAdmin], load)

function replace(updated) {
  const i = entries.value.findIndex((e) => e.id === updated.id)
  if (i >= 0) entries.value[i] = updated
}

const shown = computed(() => {
  const q = filter.value.trim().toLowerCase()
  const list = q ? entries.value.filter((e) => e.movie?.title.toLowerCase().includes(q)) : [...entries.value]
  if (sort.value === 'wertung') list.sort((a, b) => (b.rating_avg ?? -1) - (a.rating_avg ?? -1))
  return list
})

// Newest first, in months ("Oktober 2026 · 3"): easier to find your way than one long list.
const monate = computed(() => {
  if (sort.value !== 'datum' || filter.value.trim()) return [{ key: 'alle', titel: '', eintraege: shown.value }]
  const fmt = datumFmt({ month: 'long', year: 'numeric', timeZone: 'Europe/Berlin' })
  const gruppen = []
  for (const e of shown.value) {
    const titel = fmt.format(new Date(e.watched_at))
    if (gruppen.at(-1)?.titel !== titel) gruppen.push({ key: titel, titel, eintraege: [] })
    gruppen.at(-1).eintraege.push(e)
  }
  return gruppen
})

const stats = computed(() => {
  const rated = entries.value.filter((e) => e.rating_avg)
  const minutes = entries.value.reduce((s, e) => s + (e.movie?.runtime || 0), 0)
  return {
    stunden: Math.round(minutes / 60),
    schnitt: rated.length ? dezimal(rated.reduce((s, e) => s + e.rating_avg, 0) / rated.length) : '–',
  }
})
</script>

<template>
  <section>
    <div v-if="entries.length" class="row tools">
      <span class="stats muted">
        <strong>{{ stats.stunden }}</strong> {{ $t('gesehenview.stundenFilm') }} <strong>{{ stats.schnitt }}</strong> {{ $t('gesehenview.sterne') }}
      </span>
      <span class="spacer"></span>
      <input v-if="entries.length > 3" v-model="filter" type="search" :placeholder="$t('gesehenview.inDerChronikSuchen')" :aria-label="$t('gesehenview.chronikDurchsuchen')" />
      <select v-model="sort" :aria-label="$t('gesehenview.sortierung')">
        <option value="datum">{{ $t('gesehenview.neuesteZuerst') }}</option>
        <option value="wertung">{{ $t('gesehenview.besteWertung') }}</option>
      </select>
    </div>

    <div v-if="loading" class="list">
      <div v-for="i in 3" :key="i" class="skeleton" style="height: 190px"></div>
    </div>
    <div v-else-if="!entries.length" class="empty">
      <strong>{{ $t('gesehenview.nochNichtsGeschaut') }}</strong>
      {{ $t('gesehenview.markierEinenFilmAls') }}
      <a href="#/abend" class="button small leer-los">{{ $t('gesehenview.zumFilmabend') }}</a>
    </div>
    <template v-else>
      <section v-for="m in monate" :key="m.key" class="monat">
        <h3 v-if="m.titel" class="section-title">{{ m.titel }} <span class="zahl">· {{ m.eintraege.length }}</span></h3>
        <div class="list">
          <WatchedEntry
            v-for="e in m.eintraege"
            :key="e.id"
            :entry="e"
            @update="replace"
            @removed="entries = entries.filter((x) => x.id !== $event)"
          />
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.tools { margin-bottom: 1.2rem; flex-wrap: wrap; }
.tools input { width: 260px; }
.tools select { width: auto; }
.stats { font-size: 0.9rem; }
.stats strong { color: var(--text); }
.list { display: flex; flex-direction: column; gap: 1rem; }
.monat .section-title { margin: 1.4rem 0 0.7rem; }
.monat:first-of-type .section-title { margin-top: 0.4rem; }
.monat .zahl { color: var(--text); }
.leer-los { margin-top: 0.8rem; }
</style>
