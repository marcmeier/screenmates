<script setup>
import { ref, watch } from 'vue'
import { useMovieList } from '../../composables/useMovieList'
import { debounce } from '../../format'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'

const q = ref('')
const { items, loading, failed, more, load, loadMore, reset } = useMovieList('/api/search', 24)

const run = debounce((v) => (v.trim() ? load({ q: v.trim() }) : reset()), 300)
watch(q, run)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Suche</h1>
        <p>Jeder Film, nicht nur Horror – für den Fall der Fälle.</p>
      </div>
    </header>

    <div class="search">
      <Icon name="suche" class="icon" />
      <input v-model="q" type="search" placeholder="Titel suchen …" autofocus aria-label="Film suchen" />
    </div>

    <div v-if="!q.trim()" class="empty">
      <strong>Wonach suchst du?</strong>
      Deutsche und Originaltitel funktionieren beide.
    </div>
    <MovieGrid
      v-else
      :movies="items"
      :loading="loading"
      :failed="failed"
      :more="more"
      :empty-title="`Nichts gefunden für „${q.trim()}“`"
      @more="loadMore"
      @retry="load({ q: q.trim() })"
    />
  </div>
</template>

<style scoped>
.search { position: relative; max-width: 560px; margin-bottom: 1.8rem; }
.search input { padding: 0.8rem 1rem 0.8rem 2.6rem; font-size: 1rem; border-radius: 10px; }
.icon { position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%); color: var(--muted); }
</style>
