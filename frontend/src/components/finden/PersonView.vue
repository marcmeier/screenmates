<script setup>
import { onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import MovieGrid from '../MovieGrid.vue'

const props = defineProps({ id: { type: String, required: true } })
defineEmits(['name'])

const films = ref([])
const person = ref(null)
const loading = ref(false)
// Everything someone made, narrowed to one genre on request.
const genre = ref('')
const genres = ref([])
onMounted(async () => (genres.value = (await api.get('/api/genres')).genres))
const genreName = () => genres.value.find((g) => String(g.id) === genre.value)?.name

watch(
  () => [props.id, genre.value],
  async () => {
    loading.value = true
    try {
      const r = await api.get(`/api/personen/${props.id}/filme${genre.value ? `?genre=${genre.value}` : ''}`)
      films.value = r.results
      person.value = r.person
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <section>
    <div class="row head">
      <h2>{{ person?.name || 'Filmografie' }}</h2>
      <span class="spacer"></span>
      <select v-model="genre" aria-label="Genre" class="genre">
        <option value="">Alle Genres</option>
        <option v-for="g in genres" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
      </select>
    </div>
    <MovieGrid
      :movies="films"
      :loading="loading"
      :empty-title="genre ? `Keine Filme im Genre ${genreName()} mit ${person?.name || 'dieser Person'}` : 'Keine Filme gefunden'"
    >
      <template #card="{ movie }">
        <div class="roles">{{ movie.rollen.join(', ') }}</div>
      </template>
    </MovieGrid>
    <p v-if="!loading && !films.length && genre" class="center">
      <button class="small" @click="genre = ''">Alle Genres zeigen</button>
    </p>
  </section>
</template>

<style scoped>
.genre { width: auto; padding: 0.3rem 0.6rem; font-size: 0.85rem; }
.head { margin-bottom: 1.2rem; }
h2 { margin: 0; font-size: 1.3rem; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); }
.check input { width: auto; }
.center { text-align: center; }
.roles { font-size: 0.72rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
