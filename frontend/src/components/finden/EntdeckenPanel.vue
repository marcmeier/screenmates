<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useMovieList } from '../../composables/useMovieList'
import { debounce } from '../../format'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'

// Browsing without a query: horror with genre chips up front and the numeric
// filters folded away, so the page starts calm.
const STORAGE = 'screenmates.entdecken'
const DEFAULTS = { sort: 'popularity.desc', include: [], jahr_min: null, jahr_max: null, note_min: null, dauer_max: null, ohneGesehene: false, beiUns: false }
const RANGES = ['jahr_min', 'jahr_max', 'note_min', 'dauer_max', 'ohneGesehene']

function restore() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE) || '{}') }
  } catch {
    return { ...DEFAULTS }
  }
}

const f = reactive(restore())
const genres = ref([])
const app = useApp()
const { items, loading, failed, more, hinweis, load, loadMore } = useMovieList('/api/discover', 24)

const rangesActive = computed(() => RANGES.some((k) => f[k] !== DEFAULTS[k] && f[k] !== ''))
const showRanges = ref(rangesActive.value)
const anyActive = computed(() => rangesActive.value || f.include.length > 0 || f.beiUns)

// `ohneGesehene` is applied client-side; everything else goes to the API.
function query() {
  const { sort, jahr_min, jahr_max, note_min, dauer_max, include, beiUns } = f
  return { sort, jahr_min, jahr_max, note_min, dauer_max, include: include.join(','), abos: beiUns || undefined }
}

const reload = debounce(() => load(query()), 250)
watch(
  f,
  () => {
    try {
      localStorage.setItem(STORAGE, JSON.stringify(f))
    } catch {
      /* private mode: filters just aren't remembered */
    }
    reload()
  },
  { deep: true },
)

onMounted(async () => {
  load(query())
  genres.value = (await api.get('/api/genres')).genres.filter((g) => g.name !== 'Horror')
})

function toggleGenre(id) {
  f.include = f.include.includes(id) ? f.include.filter((g) => g !== id) : [...f.include, id]
}

function reset() {
  Object.assign(f, { ...DEFAULTS, sort: f.sort })
}

const sichtbar = computed(() => (f.ohneGesehene ? items.value.filter((m) => !m.gesehen) : items.value))
</script>

<template>
  <section>
    <div class="bar">
      <div class="chips" role="group" aria-label="Zusätzliche Genres">
        <button
          v-for="g in genres"
          :key="g.id"
          class="chip"
          :class="{ on: f.include.includes(g.id) }"
          :aria-pressed="f.include.includes(g.id)"
          @click="toggleGenre(g.id)"
        >{{ g.name }}</button>
      </div>
      <div class="controls">
        <button
          v-if="app.status.tmdb"
          class="small"
          :class="{ on: f.beiUns }"
          :aria-pressed="f.beiUns"
          title="Nur Filme, die bei einem Abo aus eurer Gruppe laufen"
          @click="f.beiUns = !f.beiUns"
        >
          <Icon name="gesehen" :size="14" /> Läuft bei uns
        </button>
        <button class="small" :class="{ on: rangesActive }" :aria-expanded="showRanges" @click="showRanges = !showRanges">
          <Icon name="filter" :size="14" /> Filter
        </button>
        <select v-model="f.sort" aria-label="Sortierung">
          <option value="popularity.desc">Beliebt</option>
          <option value="vote_average.desc">Beste Bewertung</option>
          <option value="primary_release_date.desc">Neueste</option>
          <option value="primary_release_date.asc">Älteste</option>
        </select>
      </div>
    </div>

    <div v-if="showRanges" class="ranges panel">
      <label class="field">Jahr ab<input v-model.number="f.jahr_min" type="number" min="1900" max="2100" placeholder="1970" /></label>
      <label class="field">Jahr bis<input v-model.number="f.jahr_max" type="number" min="1900" max="2100" placeholder="2025" /></label>
      <label class="field">Note ab<input v-model.number="f.note_min" type="number" min="0" max="10" step="0.5" placeholder="6.5" /></label>
      <label class="field">Länge bis (min)<input v-model.number="f.dauer_max" type="number" min="0" step="5" placeholder="120" /></label>
      <label class="check"><input v-model="f.ohneGesehene" type="checkbox" /> Gesehene ausblenden</label>
    </div>
    <div v-if="anyActive" class="active">
      <button class="ghost small" @click="reset"><Icon name="x" :size="13" /> Filter zurücksetzen</button>
    </div>

    <p v-if="hinweis" class="notice hinweis">
      {{ hinweis }} <a v-if="hinweis.includes('Abos')" href="#/einstellungen">Zu den Einstellungen</a>
    </p>
    <MovieGrid
      v-else
      :movies="sichtbar"
      :loading="loading"
      :failed="failed"
      :more="more"
      empty-title="Keine Filme für diese Filter"
      empty-text="Versuch es mit weniger Einschränkungen."
      @more="loadMore"
      @retry="load(query())"
    />
  </section>
</template>

<style scoped>
.bar { display: flex; gap: 1rem; align-items: flex-start; justify-content: space-between; margin-bottom: 1rem; }
.chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.controls { display: flex; gap: 0.5rem; flex: none; }
.controls select { width: auto; padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.ranges { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: flex-end; margin-bottom: 1rem; }
.ranges .field input { width: 120px; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); padding-bottom: 0.55rem; }
.check input { width: auto; }
.hinweis { margin-bottom: 1rem; }
.hinweis a { color: inherit; margin-left: 0.4rem; }
.active { margin: -0.4rem 0 1rem -0.5rem; }
@media (max-width: 700px) {
  .bar { flex-direction: column-reverse; }
  .chips { flex-wrap: nowrap; overflow-x: auto; max-width: 100%; padding-bottom: 4px; scrollbar-width: none; }
  .chip { white-space: nowrap; }
}
</style>
