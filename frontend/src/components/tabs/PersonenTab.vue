<script setup>
import { ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { navigate, useRoute } from '../../composables/useRoute'
import { debounce } from '../../format'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'

const app = useApp()
const route = useRoute()
const q = ref('')
const people = ref([])
const searching = ref(false)
const films = ref([])
const loadingFilms = ref(false)
const nurHorror = ref(true)
const person = ref(null)

const search = debounce(async (v) => {
  if (!v.trim()) return (people.value = [])
  searching.value = true
  try {
    people.value = (await api.get(`/api/personen?q=${encodeURIComponent(v.trim())}`)).results
  } finally {
    searching.value = false
  }
}, 300)
watch(q, search)

async function loadFilms() {
  const id = route.value.param
  if (!id) return
  loadingFilms.value = true
  try {
    const r = await api.get(`/api/personen/${id}/filme?nur_horror=${nurHorror.value}`)
    films.value = r.results
    person.value = r.person
  } finally {
    loadingFilms.value = false
  }
}
watch(() => [route.value.param, nurHorror.value], loadFilms, { immediate: true })

const choose = (p) => navigate('personen', p.id)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Personen</h1>
        <p>Regie, Cast, Komponisten – und wofür man sie kennt.</p>
      </div>
    </header>

    <div v-if="!app.status.tmdb" class="notice">
      Die Personensuche braucht TMDB. Trag <code>TMDB_API_KEY</code> in <code>backend/.env</code> ein und starte das Backend neu.
    </div>

    <template v-else-if="route.param">
      <div class="row">
        <button class="ghost small" @click="navigate('personen')"><Icon name="pfeil" :size="14" /> Andere Person</button>
        <h2 class="who">{{ person?.name || 'Filmografie' }}</h2>
        <span class="spacer"></span>
        <label class="check"><input v-model="nurHorror" type="checkbox" /> Nur Horror</label>
      </div>
      <MovieGrid :movies="films" :loading="loadingFilms" empty-title="Keine passenden Filme">
        <template #card="{ movie }">
          <div class="roles">{{ movie.rollen.join(', ') }}</div>
        </template>
      </MovieGrid>
    </template>

    <template v-else>
      <div class="search">
        <Icon name="suche" class="icon" />
        <input v-model="q" type="search" placeholder="z. B. John Carpenter, Toni Collette …" autofocus aria-label="Person suchen" />
      </div>
      <ul class="people">
        <li v-for="p in people" :key="p.id">
          <button class="person" @click="choose(p)">
            <img v-if="p.bild" :src="p.bild" alt="" loading="lazy" />
            <span v-else class="noimg"></span>
            <span class="pname">{{ p.name }}</span>
            <span class="muted small">{{ p.bereich }}</span>
            <span class="muted small known">{{ p.bekannt_fuer.join(' · ') }}</span>
          </button>
        </li>
      </ul>
      <p v-if="q && !searching && !people.length" class="muted">Niemand gefunden.</p>
    </template>
  </div>
</template>

<style scoped>
.search { position: relative; max-width: 560px; margin-bottom: 1.8rem; }
.search input { padding: 0.8rem 1rem 0.8rem 2.6rem; font-size: 1rem; border-radius: 10px; }
.icon { position: absolute; left: 0.85rem; top: 50%; transform: translateY(-50%); color: var(--muted); }
.people { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem; }
.person { flex-direction: column; align-items: flex-start; width: 100%; padding: 0.6rem; text-align: left; gap: 2px; }
.person img, .noimg { width: 100%; aspect-ratio: 3/4; object-fit: cover; border-radius: 6px; background: var(--bg-raised); margin-bottom: 0.4rem; }
.pname { font-weight: 600; }
.small { font-size: 0.75rem; }
.known { line-height: 1.3; }
.who { margin: 0; font-size: 1.3rem; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); }
.check input { width: auto; }
.roles { font-size: 0.72rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row { margin-bottom: 1.4rem; }
</style>
