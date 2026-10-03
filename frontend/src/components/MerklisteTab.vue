<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import MovieCard from './MovieCard.vue'

const emit = defineEmits(['open'])
const movies = ref([])

async function load() { movies.value = (await api.get('/api/wishlist')).wishlist || [] }
onMounted(load)

async function remove(m) { await api.del(`/api/wishlist/${m.id}`); await load() }
async function watched(m) { await api.post('/api/watched', { movie_id: m.id }); await remove(m) }
</script>

<template>
  <div>
    <h1>Merkliste</h1>
    <p v-if="!movies.length" class="muted">Noch nichts gemerkt. Füg über die Suche oder „Entdecken" Filme hinzu.</p>
    <div class="grid">
      <MovieCard v-for="m in movies" :key="m.id" :movie="m" @open="emit('open', $event)">
        <template #actions="{ movie }">
          <button class="primary" @click.stop="watched(movie)">Gesehen</button>
          <button class="ghost" @click.stop="remove(movie)">Entfernen</button>
        </template>
      </MovieCard>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 1rem; font-size: 1.5rem; }
</style>
