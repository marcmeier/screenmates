<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import MovieCard from './MovieCard.vue'

const emit = defineEmits(['open'])
const movies = ref([])
const loading = ref(true)
const sort = ref('popularity.desc')
const jahrMin = ref(null)
const noteMin = ref(null)

async function load() {
  loading.value = true
  const params = new URLSearchParams({ limit: '36', sort: sort.value })
  if (jahrMin.value) params.set('jahr_min', jahrMin.value)
  if (noteMin.value) params.set('note_min', noteMin.value)
  try {
    const r = await api.get(`/api/discover?${params}`)
    movies.value = r.results || []
  } finally { loading.value = false }
}
onMounted(load)

async function wish(m) { await api.post('/api/wishlist', { movie_id: m.id }) }
async function suggest(m) { await api.post('/api/suggestions', { movie_id: m.id }) }
</script>

<template>
  <div>
    <h1>Entdecken</h1>
    <div class="filters">
      <label>Sortierung
        <select v-model="sort" @change="load">
          <option value="popularity.desc">Beliebtheit</option>
          <option value="vote_average.desc">Beste Bewertung</option>
          <option value="primary_release_date.desc">Neueste</option>
        </select>
      </label>
      <label>Ab Jahr <input type="number" v-model="jahrMin" @change="load" placeholder="z. B. 1980" /></label>
      <label>Min. Note <input type="number" step="0.5" v-model="noteMin" @change="load" placeholder="z. B. 7" /></label>
    </div>
    <p v-if="loading" class="muted">Lade …</p>
    <div class="grid" style="margin-top:1.4rem">
      <MovieCard v-for="m in movies" :key="m.id" :movie="m" @open="emit('open', $event)">
        <template #actions="{ movie }">
          <button class="ghost" @click.stop="wish(movie)">+ Merken</button>
          <button class="ghost" @click.stop="suggest(movie)">Vorschlag</button>
        </template>
      </MovieCard>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.filters { display: flex; gap: 1rem; flex-wrap: wrap; }
.filters label { display: flex; flex-direction: column; gap: 4px; font-size: 0.8rem; color: var(--muted); }
.filters input, .filters select { width: 160px; }
</style>
