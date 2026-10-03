<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../../api'
import { useMovieList } from '../../composables/useMovieList'
import { debounce } from '../../format'
import MovieGrid from '../MovieGrid.vue'

const STORAGE = 'screenmates.entdecken'
const DEFAULTS = { sort: 'popularity.desc', include: [], jahr_min: null, jahr_max: null, note_min: null, dauer_max: null, ohneGesehene: false }

function restore() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE) || '{}') }
  } catch {
    return { ...DEFAULTS }
  }
}

const f = reactive(restore())
const genres = ref([])
const { items, loading, failed, more, load, loadMore } = useMovieList('/api/discover', 24)

// `ohneGesehene` is applied client-side; everything else goes to the API.
function query() {
  const { sort, jahr_min, jahr_max, note_min, dauer_max, include } = f
  return { sort, jahr_min, jahr_max, note_min, dauer_max, include: include.join(',') }
}

const reload = debounce(() => load(query()), 250)
watch(f, () => {
  try {
    localStorage.setItem(STORAGE, JSON.stringify(f))
  } catch {
    /* private mode: filters just aren't remembered */
  }
  reload()
}, { deep: true })

onMounted(async () => {
  load(query())
  genres.value = (await api.get('/api/genres')).genres.filter((g) => g.name !== 'Horror')
})

function toggleGenre(id) {
  f.include = f.include.includes(id) ? f.include.filter((g) => g !== id) : [...f.include, id]
}

const sichtbar = computed(() => (f.ohneGesehene ? items.value.filter((m) => !m.gesehen) : items.value))
const aktiv = computed(() => JSON.stringify({ ...f, sort: DEFAULTS.sort }) !== JSON.stringify({ ...DEFAULTS }))
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Entdecken</h1>
        <p>Horror quer durch die Jahrzehnte – mit Filtern für jeden Geschmack.</p>
      </div>
      <label class="field sort">Sortierung
        <select v-model="f.sort">
          <option value="popularity.desc">Beliebtheit</option>
          <option value="vote_average.desc">Beste Bewertung</option>
          <option value="primary_release_date.desc">Neueste zuerst</option>
          <option value="primary_release_date.asc">Älteste zuerst</option>
        </select>
      </label>
    </header>

    <div class="filters panel">
      <div class="row genres" role="group" aria-label="Zusätzliche Genres">
        <span class="muted label">Horror +</span>
        <button
          v-for="g in genres"
          :key="g.id"
          class="chip"
          :class="{ on: f.include.includes(g.id) }"
          :aria-pressed="f.include.includes(g.id)"
          @click="toggleGenre(g.id)"
        >{{ g.name }}</button>
      </div>
      <div class="row ranges">
        <label class="field">Jahr ab<input v-model.number="f.jahr_min" type="number" min="1900" max="2100" placeholder="1970" /></label>
        <label class="field">Jahr bis<input v-model.number="f.jahr_max" type="number" min="1900" max="2100" placeholder="2025" /></label>
        <label class="field">Note ab<input v-model.number="f.note_min" type="number" min="0" max="10" step="0.5" placeholder="6.5" /></label>
        <label class="field">Länge bis (min)<input v-model.number="f.dauer_max" type="number" min="0" step="5" placeholder="120" /></label>
        <label class="check"><input v-model="f.ohneGesehene" type="checkbox" /> Gesehene ausblenden</label>
        <span class="spacer"></span>
        <button v-if="aktiv" class="ghost small" @click="Object.assign(f, DEFAULTS)">Filter zurücksetzen</button>
      </div>
    </div>

    <MovieGrid
      :movies="sichtbar"
      :loading="loading"
      :failed="failed"
      :more="more"
      empty-title="Keine Filme für diese Filter"
      empty-text="Versuch es mit weniger Einschränkungen."
      @more="loadMore"
      @retry="load(query())"
    />
  </div>
</template>

<style scoped>
.sort select { min-width: 190px; }
.filters { margin-bottom: 1.6rem; display: flex; flex-direction: column; gap: 0.9rem; }
.label { font-size: 0.8rem; font-weight: 600; }
.ranges .field input { width: 120px; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); align-self: flex-end; padding-bottom: 0.55rem; }
.check input { width: auto; }
</style>
