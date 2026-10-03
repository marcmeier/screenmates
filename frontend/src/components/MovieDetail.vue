<script setup>
import { ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({ movie: Object })
const emit = defineEmits(['close'])
const full = ref(null)
const credits = ref([])

watch(() => props.movie, async (m) => {
  if (!m) return
  full.value = m
  try {
    full.value = await api.get(`/api/movies/${m.id}`)
    const c = await api.get(`/api/movies/${m.id}/credits`)
    credits.value = (c.cast || []).slice(0, 8)
  } catch {}
}, { immediate: true })

async function wish() { await api.post('/api/wishlist', { movie_id: props.movie.id }) }
async function watched() { await api.post('/api/watched', { movie_id: props.movie.id }) }
async function suggest() { await api.post('/api/suggestions', { movie_id: props.movie.id }) }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="sheet">
      <button class="x" @click="emit('close')">✕</button>
      <div class="hero" :style="full?.backdrop_url ? { backgroundImage: `url(${full.backdrop_url})` } : {}"></div>
      <div class="content">
        <h2>{{ full?.title }} <span class="muted">{{ full?.year }}</span></h2>
        <div class="tags">
          <span v-if="full?.vote_average" class="stars">★ {{ full.vote_average }}</span>
          <span v-if="full?.runtime" class="muted">{{ full.runtime }} min</span>
          <span v-for="g in full?.genres || []" :key="g" class="genre">{{ g }}</span>
        </div>
        <p class="overview">{{ full?.overview || 'Keine Beschreibung.' }}</p>
        <div v-if="credits.length" class="cast">
          <span class="muted">Besetzung:</span> {{ credits.map(c => c.name).join(', ') }}
        </div>
        <div class="actions">
          <button class="primary" @click="watched">Als gesehen</button>
          <button @click="wish">+ Merken</button>
          <button class="ghost" @click="suggest">Vorschlagen</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(5,5,8,0.8); display: flex; align-items: center; justify-content: center; z-index: 40; padding: 1rem; }
.sheet { background: var(--bg-soft); border: 1px solid var(--line); border-radius: 14px; width: min(680px, 96vw); max-height: 90vh; overflow: auto; position: relative; }
.x { position: absolute; top: 12px; right: 12px; z-index: 2; border-radius: 50%; width: 34px; height: 34px; padding: 0; }
.hero { height: 240px; background-size: cover; background-position: center; background-color: #1b1b22; border-radius: 14px 14px 0 0; }
.content { padding: 1.4rem; }
h2 { margin: 0 0 0.6rem; }
.tags { display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center; margin-bottom: 1rem; }
.genre { font-size: 0.75rem; border: 1px solid var(--line); padding: 2px 8px; border-radius: 20px; }
.overview { line-height: 1.6; }
.cast { font-size: 0.85rem; margin: 0.8rem 0; }
.actions { display: flex; gap: 0.6rem; margin-top: 1.2rem; flex-wrap: wrap; }
</style>
