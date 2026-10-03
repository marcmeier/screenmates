<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'
import MovieCard from './MovieCard.vue'

const emit = defineEmits(['open'])
const q = ref('')
const results = ref([])
const loading = ref(false)
let timer

watch(q, (val) => {
  clearTimeout(timer)
  if (!val.trim()) { results.value = []; return }
  timer = setTimeout(run, 300)
})

async function run() {
  loading.value = true
  try {
    const r = await api.get(`/api/search?q=${encodeURIComponent(q.value.trim())}&limit=36`)
    results.value = r.results || []
  } finally { loading.value = false }
}

async function wish(m) { await api.post('/api/wishlist', { movie_id: m.id }) }
async function suggest(m) { await api.post('/api/suggestions', { movie_id: m.id }) }
</script>

<template>
  <div>
    <h1>Suche</h1>
    <input v-model="q" placeholder="Film oder Serie suchen …" autofocus />
    <p v-if="loading" class="muted" style="margin-top:1rem">Suche läuft …</p>
    <p v-else-if="q && !results.length" class="muted" style="margin-top:1rem">Nichts gefunden.</p>
    <div class="grid" style="margin-top:1.4rem">
      <MovieCard v-for="m in results" :key="m.id" :movie="m" @open="emit('open', $event)">
        <template #actions="{ movie }">
          <button class="ghost" @click.stop="wish(movie)" title="Merken">+ Merken</button>
          <button class="ghost" @click.stop="suggest(movie)" title="Vorschlagen">Vorschlag</button>
        </template>
      </MovieCard>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 1rem; font-size: 1.5rem; }
input { max-width: 520px; }
</style>
