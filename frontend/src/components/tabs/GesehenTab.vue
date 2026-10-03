<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import WatchedEntry from '../WatchedEntry.vue'

const app = useApp()
const ui = useUi()
const entries = ref([])
const loading = ref(true)
const filter = ref('')
const sort = ref('datum')

async function load() {
  try {
    entries.value = (await api.get(`/api/watched?alle=${app.host}`)).watched
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => [ui.changes, app.host], load)

function replace(updated) {
  const i = entries.value.findIndex((e) => e.id === updated.id)
  if (i >= 0) entries.value[i] = updated
}

const shown = computed(() => {
  const q = filter.value.trim().toLowerCase()
  let list = q ? entries.value.filter((e) => e.movie?.title.toLowerCase().includes(q)) : [...entries.value]
  if (sort.value === 'wertung') list.sort((a, b) => (b.rating_avg ?? -1) - (a.rating_avg ?? -1))
  return list
})

const stats = computed(() => {
  const rated = entries.value.filter((e) => e.rating_avg)
  const minutes = entries.value.reduce((s, e) => s + (e.movie?.runtime || 0), 0)
  return {
    filme: entries.value.length,
    stunden: Math.round(minutes / 60),
    schnitt: rated.length ? (rated.reduce((s, e) => s + e.rating_avg, 0) / rated.length).toFixed(1) : '–',
  }
})
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Gesehen</h1>
        <p>Unsere Filmabend-Chronik mit Bewertungen und Gästebuch.</p>
      </div>
      <div class="stats">
        <div><strong>{{ stats.filme }}</strong><span>Filme</span></div>
        <div><strong>{{ stats.stunden }}</strong><span>Stunden</span></div>
        <div><strong>{{ stats.schnitt }}</strong><span>⌀ Sterne</span></div>
      </div>
    </header>

    <div v-if="entries.length > 3" class="row tools">
      <input v-model="filter" type="search" placeholder="In der Chronik suchen …" aria-label="Chronik durchsuchen" />
      <select v-model="sort" aria-label="Sortierung">
        <option value="datum">Neueste zuerst</option>
        <option value="wertung">Beste Wertung</option>
      </select>
    </div>

    <div v-if="loading" class="list">
      <div v-for="i in 3" :key="i" class="skeleton" style="height: 190px"></div>
    </div>
    <div v-else-if="!entries.length" class="empty">
      <strong>Noch nichts geschaut</strong>
      Markier einen Film als „Gesehen“, dann beginnt hier die Chronik.
    </div>
    <div v-else class="list">
      <WatchedEntry
        v-for="e in shown"
        :key="e.id"
        :entry="e"
        @update="replace"
        @removed="entries = entries.filter((x) => x.id !== $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.stats { display: flex; gap: 1.6rem; }
.stats div { display: flex; flex-direction: column; align-items: flex-end; }
.stats strong { font-size: 1.5rem; line-height: 1; }
.stats span { font-size: 0.75rem; color: var(--muted); }
.tools { margin-bottom: 1.2rem; flex-wrap: nowrap; }
.tools input { max-width: 360px; }
.tools select { width: auto; }
.list { display: flex; flex-direction: column; gap: 1rem; }
</style>
