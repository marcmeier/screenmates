<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useUi } from '../../stores/ui'
import { navigate } from '../../composables/useRoute'
import MovieGrid from '../MovieGrid.vue'
import UserAvatar from '../UserAvatar.vue'

const ui = useUi()
const movies = ref([])
const loading = ref(true)
const failed = ref(false)
const sort = ref('neu')

async function load() {
  failed.value = false
  try {
    movies.value = (await api.get('/api/wishlist')).wishlist
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => ui.changes, load)

const sorted = computed(() => {
  const list = [...movies.value]
  if (sort.value === 'note') list.sort((a, b) => b.vote_average - a.vote_average)
  if (sort.value === 'kurz') list.sort((a, b) => (a.runtime || 999) - (b.runtime || 999))
  if (sort.value === 'titel') list.sort((a, b) => a.title.localeCompare(b.title, 'de'))
  return list
})
</script>

<template>
  <section>
    <div v-if="movies.length > 1" class="row tools">
      <span class="muted">Filme, die wir irgendwann sehen wollen.</span>
      <span class="spacer"></span>
      <select v-model="sort" aria-label="Sortierung">
        <option value="neu">Zuletzt gemerkt</option>
        <option value="note">Beste Bewertung</option>
        <option value="kurz">Kürzeste zuerst</option>
        <option value="titel">Titel A–Z</option>
      </select>
    </div>

    <MovieGrid :movies="sorted" :loading="loading && !movies.length" :failed="failed" empty-title="Die Merkliste ist leer" empty-text="Bei jedem Film gibt es den Merken-Knopf." @retry="load">
      <template #card="{ movie }">
        <div v-if="movie.gemerkt_von" class="by"><UserAvatar :user-id="movie.gemerkt_von" /></div>
      </template>
    </MovieGrid>
    <p v-if="!loading && !movies.length" class="center">
      <button class="small" @click="navigate('finden')">Filme finden</button>
    </p>
  </section>
</template>

<style scoped>
.tools { margin-bottom: 1.2rem; font-size: 0.9rem; }
.tools select { width: auto; }
.by { margin-top: 4px; }
.by .avatar { width: 20px; height: 20px; font-size: 0.56rem; }
.center { text-align: center; }
</style>
