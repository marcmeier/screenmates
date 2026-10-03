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
  const list = q ? entries.value.filter((e) => e.movie?.title.toLowerCase().includes(q)) : [...entries.value]
  if (sort.value === 'wertung') list.sort((a, b) => (b.rating_avg ?? -1) - (a.rating_avg ?? -1))
  return list
})

const stats = computed(() => {
  const rated = entries.value.filter((e) => e.rating_avg)
  const minutes = entries.value.reduce((s, e) => s + (e.movie?.runtime || 0), 0)
  return {
    stunden: Math.round(minutes / 60),
    schnitt: rated.length ? (rated.reduce((s, e) => s + e.rating_avg, 0) / rated.length).toFixed(1) : '–',
  }
})
</script>

<template>
  <section>
    <div v-if="entries.length" class="row tools">
      <span class="stats muted">
        <strong>{{ stats.stunden }}</strong> Stunden Horror · <strong>{{ stats.schnitt }}</strong> ⌀ Sterne
      </span>
      <span class="spacer"></span>
      <input v-if="entries.length > 3" v-model="filter" type="search" placeholder="In der Chronik suchen …" aria-label="Chronik durchsuchen" />
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
  </section>
</template>

<style scoped>
.tools { margin-bottom: 1.2rem; flex-wrap: wrap; }
.tools input { width: 260px; }
.tools select { width: auto; }
.stats { font-size: 0.9rem; }
.stats strong { color: var(--text); }
.list { display: flex; flex-direction: column; gap: 1rem; }
</style>
