<script setup>
import { t as tr } from '../../i18n'
import { computed, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useMovieList } from '../../composables/useMovieList'
import { navigate, useRoute } from '../../composables/useRoute'
import { debounce } from '../../format'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'
import EntdeckenPanel from '../finden/EntdeckenPanel.vue'
import NachOben from '../NachOben.vue'
import KiErgebnisse from '../finden/KiErgebnisse.vue'
import PersonView from '../finden/PersonView.vue'

defineOptions({ name: 'FindenTab' })

// One field for every way of finding a film. What appears below depends on
// the state: nothing typed → discover; typed → titles and people;
// "KI fragen" → the AI reads the text as a mood; a person → their films.
const app = useApp()
const route = useRoute()
const q = ref('')
const kiFrage = ref(null)
const people = ref([])
const films = useMovieList('/api/search', 24)
let peopleCtrl = null

const term = computed(() => q.value.trim())
const mode = computed(() => {
  if (route.value.sub === 'person' && route.value.id) return 'person'
  if (kiFrage.value) return 'ki'
  return term.value ? 'suche' : 'entdecken'
})
// Several words read like a description rather than a title.
const klingtNachBeschreibung = computed(() => app.status.ki && term.value.split(/\s+/).length >= 4)

async function searchPeople(t) {
  peopleCtrl?.abort()
  if (!app.status.tmdb || !t) return (people.value = [])
  peopleCtrl = new AbortController()
  try {
    const r = await api.get(`/api/personen?q=${encodeURIComponent(t)}`, { signal: peopleCtrl.signal, quiet: true })
    people.value = r.results.filter((p) => p.bild).slice(0, 8)
  } catch {
    /* people are a bonus; title results still show */
  }
}

const run = debounce((t) => {
  if (!t) {
    films.reset()
    people.value = []
    return
  }
  films.load({ q: t })
  searchPeople(t)
}, 300)

watch(term, (t) => {
  kiFrage.value = null // editing the text goes back to title search
  run(t)
})

function frageKi() {
  if (term.value) kiFrage.value = term.value
}

function onEnter() {
  if (klingtNachBeschreibung.value) frageKi()
}

const placeholder = computed(() =>
  app.status.ki
    ? tr('findentab.titelPersonOderBeschreib')
    : app.status.tmdb
      ? tr('findentab.titelOderPersonSuchen')
      : tr('findentab.titelSuchen'),
)
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>{{ $t('nav.finden') }}</h1>
        <p>{{ $t('findentab.stoebernGezieltSuchenOder') }}</p>
      </div>
    </header>

    <div v-if="mode === 'person'" class="back">
      <button class="ghost small" @click="navigate('finden')"><Icon name="pfeil" :size="14" /> {{ $t('allg.zurueck') }}</button>
    </div>

    <form v-else class="search" role="search" @submit.prevent="onEnter">
      <Icon name="suche" class="icon" />
      <input v-model="q" type="search" :placeholder="placeholder" :aria-label="$t('findentab.suchen')" />
      <button
        v-if="app.status.ki"
        type="button"
        class="ki"
        :class="{ primary: klingtNachBeschreibung, on: mode === 'ki' }"
        :disabled="!term"
        :title="$t('findentab.denTextAlsStimmung')"
        @click="frageKi"
      >
        <Icon name="ki" :size="16" /> {{ $t('findentab.kiFragen') }}
      </button>
    </form>

    <PersonView v-if="mode === 'person'" :id="route.id" />

    <KiErgebnisse v-else-if="mode === 'ki'" :frage="kiFrage" />

    <template v-else-if="mode === 'suche'">
      <p v-if="klingtNachBeschreibung" class="hint">
        {{ $t('findentab.klingtNachEinerBeschreibung') }} <button class="linklike" @click="frageKi">{{ $t('findentab.dieKiFragen') }}</button> {{ $t('findentab.oderEnter') }}
      </p>

      <template v-if="people.length">
        <h2 class="section-title">{{ $t('findentab.personen') }}</h2>
        <ul class="people">
          <li v-for="p in people" :key="p.id">
            <button class="person" @click="navigate('finden', 'person', p.id)">
              <img :src="p.bild" alt="" loading="lazy" />
              <span class="pname">{{ p.name }}</span>
              <span class="muted">{{ p.bereich }}</span>
            </button>
          </li>
        </ul>
        <h2 class="section-title">{{ $t('findentab.filme') }}</h2>
      </template>

      <MovieGrid
        :movies="films.items.value"
        :loading="films.loading.value"
        :failed="films.failed.value"
        :more="films.more.value"
        :empty-title="$t('findentab.keinFilmHeisstTerm', { term })"
        :empty-text="app.status.ki ? $t('findentab.wennDuEineStimmung') : ''"
        @more="films.loadMore"
        @retry="films.load({ q: term })"
      />
    </template>

    <EntdeckenPanel v-else />

    <NachOben />
  </div>
</template>

<style scoped>
.search { position: relative; max-width: 720px; margin-bottom: 0.9rem; display: flex; gap: 0.5rem; }
.search input { padding: 0.65rem 1rem 0.65rem 2.6rem; font-size: 0.98rem; border-radius: 10px; }
.icon { position: absolute; left: 0.9rem; top: 50%; transform: translateY(-50%); color: var(--muted); pointer-events: none; }
.ki { flex: none; border-radius: 10px; padding: 0 1rem; }
.back { margin: -0.6rem 0 0.8rem -0.5rem; }
.hint { margin: -0.6rem 0 1.4rem; color: var(--muted); font-size: 0.9rem; }
.linklike { padding: 0; border: none; background: none; color: var(--accent); font-size: inherit; text-decoration: underline; }
.linklike:hover { background: none; }
.people { list-style: none; padding: 0; margin: 0 0 0.5rem; display: flex; gap: 0.6rem; overflow-x: auto; padding-bottom: 4px; }
.person { flex-direction: column; gap: 3px; width: 112px; padding: 0.6rem 0.4rem; font-size: 0.75rem; text-align: center; }
.person img { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; margin-bottom: 0.2rem; }
.pname { font-weight: 600; font-size: 0.82rem; line-height: 1.2; }
.section-title:first-of-type { margin-top: 0; }
</style>
