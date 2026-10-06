<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useMovieList } from '../../composables/useMovieList'
import { debounce } from '../../format'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'
import Regale from './Regale.vue'

// Browsing without a query. "Stöbern" shows shelves (per streaming service and
// theme); "Alle Filme" is the grid. Its controls fit one bar: where it runs and the
// genres open as small menus, the finer filters fold out below.
const STORAGE = 'screenmates.entdecken'
const DEFAULTS = {
  ansicht: 'stoebern',
  sort: 'popularity.desc',
  include: [],
  exclude: [], // set by shelves only (e.g. no animation among the hidden gems)
  sprachen: [], // ditto: original languages
  jahr_min: null,
  jahr_max: null,
  note_min: null,
  stimmen_min: null,
  stimmen_max: null,
  dauer_max: null,
  ohneGesehene: false,
  beiUns: false,
  anbieter: null, // one streaming service
  kostenlos: false,
}
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
const dienste = ref([])
const app = useApp()
const { items, loading, failed, more, hinweis, gesamt, load, loadMore } = useMovieList('/api/discover', 24)
const anzahl = new Intl.NumberFormat('de-DE')
// TMDB caps its count (20.001) and serves at most 500 pages of 20.
const gesamtText = computed(() =>
  gesamt.value > 10000 ? 'Mehr als 10.000 Filme' : `${anzahl.format(gesamt.value)} ${gesamt.value === 1 ? 'Film' : 'Filme'}`,
)

const rangesActive = computed(() => RANGES.some((k) => f[k] !== DEFAULTS[k] && f[k] !== ''))
const showRanges = ref(rangesActive.value)
const anyActive = computed(
  () => rangesActive.value || f.include.length > 0 || f.exclude.length > 0 || f.sprachen.length > 0 || f.beiUns || f.anbieter || f.kostenlos || f.stimmen_min,
)

// `ohneGesehene` is applied client-side; everything else goes to the API.
function query() {
  const { sort, jahr_min, jahr_max, note_min, stimmen_min, stimmen_max, dauer_max, include, exclude, beiUns, anbieter, kostenlos } = f
  return {
    sort,
    jahr_min,
    jahr_max,
    note_min,
    stimmen_min,
    stimmen_max,
    dauer_max,
    include: include.join(','),
    exclude: exclude.join(',') || undefined,
    sprachen: f.sprachen.join(',') || undefined,
    abos: beiUns || undefined,
    anbieter: anbieter || undefined,
    kostenlos: kostenlos || undefined,
  }
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
    if (f.ansicht === 'raster') reload()
  },
  { deep: true },
)

onMounted(async () => {
  if (f.ansicht === 'raster') load(query())
  genres.value = (await api.get('/api/genres')).genres
  if (app.status.tmdb) dienste.value = (await api.get('/api/anbieter?limit=10&zum_stoebern=true', { quiet: true })).anbieter
})

// A shelf's "Alle zeigen": its filter becomes the grid.
function alleZeigen(regal) {
  Object.assign(f, { ...DEFAULTS, ...regal.filter, ansicht: 'raster' })
  window.scrollTo({ top: 0 })
}

// Where it streams: one service, all of ours, or free – one at a time.
function dienst(id) {
  Object.assign(f, { anbieter: f.anbieter === id ? null : id, beiUns: false, kostenlos: false })
}
function beiUnsUmschalten() {
  Object.assign(f, { beiUns: !f.beiUns, anbieter: null, kostenlos: false })
}
function kostenlosUmschalten() {
  Object.assign(f, { kostenlos: !f.kostenlos, anbieter: null, beiUns: false })
}

// The two menus in the bar: one open at a time, closed by a click elsewhere or Escape.
const offen = ref(null) // 'wo' | 'genre' | null
const umschalten = (welches) => (offen.value = offen.value === welches ? null : welches)
const zu = () => (offen.value = null)
const taste = (e) => e.key === 'Escape' && zu()
onMounted(() => {
  document.addEventListener('click', zu)
  window.addEventListener('keydown', taste)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', zu)
  window.removeEventListener('keydown', taste)
})

const woAktiv = computed(() => !!(f.anbieter || f.beiUns || f.kostenlos))
const gewaehlterDienst = computed(() => dienste.value.find((d) => d.id === f.anbieter) || null)
const woText = computed(() => {
  if (f.beiUns) return 'Läuft bei uns'
  if (f.kostenlos) return 'Kostenlos'
  if (f.anbieter) return gewaehlterDienst.value?.name ?? 'Ein Dienst'
  return 'Wo läuft’s?'
})
function alleDienste() {
  Object.assign(f, { anbieter: null, beiUns: false, kostenlos: false })
}
const genreText = computed(() => {
  const namen = f.include.map((id) => genres.value.find((g) => g.id === id)?.name).filter(Boolean)
  if (!namen.length) return 'Genre'
  return namen.length <= 2 ? namen.join(', ') : `${namen.length} Genres`
})

function toggleGenre(id) {
  f.include = f.include.includes(id) ? f.include.filter((g) => g !== id) : [...f.include, id]
}

function reset() {
  Object.assign(f, { ...DEFAULTS, sort: f.sort, ansicht: 'raster' })
}

const sichtbar = computed(() => (f.ohneGesehene ? items.value.filter((m) => !m.gesehen) : items.value))
</script>

<template>
  <section>
    <!-- One bar instead of five rows: view, where it runs, genres, filters, order, how many. -->
    <div class="leiste">
      <div class="ansicht" role="tablist" aria-label="Ansicht">
        <button role="tab" :aria-selected="f.ansicht === 'stoebern'" :class="{ on: f.ansicht === 'stoebern' }" @click="f.ansicht = 'stoebern'">
          Stöbern
        </button>
        <button role="tab" :aria-selected="f.ansicht === 'raster'" :class="{ on: f.ansicht === 'raster' }" @click="f.ansicht = 'raster'">
          Alle Filme
        </button>
      </div>

      <template v-if="f.ansicht === 'raster'">
        <div class="aufklapp">
          <button class="small wahl" :class="{ on: woAktiv }" :aria-expanded="offen === 'wo'" aria-label="Wo läuft's?" @click.stop="umschalten('wo')">
            <img v-if="gewaehlterDienst?.logo" :src="gewaehlterDienst.logo" alt="" class="mini" />
            <span>{{ woText }}</span>
            <Icon name="pfeil" :size="12" class="pfeil" />
          </button>
          <div v-if="offen === 'wo'" class="menue panel" role="group" aria-label="Streamingdienst" @click.stop>
            <div class="optionen">
              <button class="small" :class="{ on: !woAktiv }" @click="alleDienste">Überall</button>
              <button
                v-if="app.status.tmdb"
                class="small"
                :class="{ on: f.beiUns }"
                :aria-pressed="f.beiUns"
                title="Nur Filme, die bei einem Abo aus eurer Gruppe laufen"
                @click="beiUnsUmschalten"
              >
                <Icon name="gesehen" :size="14" /> Läuft bei uns
              </button>
              <button class="small" :class="{ on: f.kostenlos }" :aria-pressed="f.kostenlos" @click="kostenlosUmschalten">Kostenlos</button>
            </div>
            <div v-if="dienste.length" class="dienste">
              <button
                v-for="d in dienste"
                :key="d.id"
                class="dienst"
                :class="{ on: f.anbieter === d.id }"
                :aria-pressed="f.anbieter === d.id"
                :title="d.name"
                @click="dienst(d.id)"
              >
                <img :src="d.logo" :alt="d.name" />
              </button>
            </div>
          </div>
        </div>

        <div class="aufklapp">
          <button class="small wahl" :class="{ on: f.include.length }" :aria-expanded="offen === 'genre'" aria-label="Genres" @click.stop="umschalten('genre')">
            <span>{{ genreText }}</span>
            <Icon name="pfeil" :size="12" class="pfeil" />
          </button>
          <div v-if="offen === 'genre'" class="menue panel breit" @click.stop>
            <div class="chips" role="group" aria-label="Genres">
              <button
                v-for="g in genres"
                :key="g.id"
                class="chip"
                :class="{ on: f.include.includes(g.id) }"
                :aria-pressed="f.include.includes(g.id)"
                @click="toggleGenre(g.id)"
              >{{ g.name }}</button>
            </div>
            <button v-if="f.include.length" class="ghost small" @click="f.include = []">Alle Genres</button>
          </div>
        </div>

        <button class="small" :class="{ on: rangesActive }" :aria-expanded="showRanges" @click="showRanges = !showRanges">
          <Icon name="filter" :size="14" /> Filter
        </button>
        <select v-model="f.sort" aria-label="Sortierung">
          <option value="popularity.desc">Beliebt</option>
          <option value="vote_average.desc">Beste Bewertung</option>
          <option value="primary_release_date.desc">Neueste</option>
          <option value="primary_release_date.asc">Älteste</option>
        </select>
        <button v-if="anyActive" class="ghost small" @click="reset"><Icon name="x" :size="13" /> Filter zurücksetzen</button>
        <span class="spacer"></span>
        <span v-if="gesamt && !hinweis" class="muted gesamt">{{ gesamtText }}</span>
      </template>
    </div>

    <Regale v-if="f.ansicht === 'stoebern'" @alle="alleZeigen" />

    <template v-else>
      <div v-if="showRanges" class="ranges panel">
        <label class="field">Jahr ab<input v-model.number="f.jahr_min" type="number" min="1900" max="2100" placeholder="1970" /></label>
        <label class="field">Jahr bis<input v-model.number="f.jahr_max" type="number" min="1900" max="2100" placeholder="2025" /></label>
        <label class="field">Note ab<input v-model.number="f.note_min" type="number" min="0" max="10" step="0.5" placeholder="6.5" /></label>
        <label class="field">Länge bis (min)<input v-model.number="f.dauer_max" type="number" min="0" step="5" placeholder="120" /></label>
        <label class="check"><input v-model="f.ohneGesehene" type="checkbox" /> Gesehene ausblenden</label>
      </div>

      <p v-if="hinweis" class="notice hinweis">
        {{ hinweis }} <a v-if="hinweis.includes('Abos')" href="#/profil/einstellungen">Zu den Einstellungen</a>
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
    </template>
  </section>
</template>

<style scoped>
.leiste { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
.ansicht { display: inline-flex; gap: 2px; padding: 3px; border-radius: 10px; background: var(--bg-soft); border: 1px solid var(--line); margin-right: 0.4rem; }
.ansicht button { border: none; background: none; padding: 0.35rem 0.9rem; border-radius: 7px; color: var(--muted); font-weight: 600; font-size: 0.88rem; }
.ansicht button.on { background: var(--bg-raised); color: var(--text); }
.leiste select { width: auto; padding: 0.3rem 0.6rem; font-size: 0.8rem; }
.aufklapp { position: relative; }
.wahl { gap: 0.4rem; max-width: 16rem; }
.wahl span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wahl .mini { width: 18px; height: 18px; border-radius: 4px; }
.pfeil { transform: rotate(-90deg); transition: transform 0.15s; opacity: 0.7; }
.wahl[aria-expanded='true'] .pfeil { transform: rotate(90deg); }
.menue {
  position: absolute; top: calc(100% + 6px); left: 0; z-index: 30; width: 320px; padding: 0.7rem;
  display: flex; flex-direction: column; gap: 0.7rem; box-shadow: var(--shadow);
}
.menue.breit { width: min(520px, 90vw); }
.optionen { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.dienste { display: grid; grid-template-columns: repeat(auto-fill, 40px); gap: 0.4rem; }
.dienst { width: 40px; height: 40px; padding: 0; border-radius: 9px; overflow: hidden; border: 2px solid transparent; opacity: 0.6; transition: opacity 0.15s, border-color 0.15s; }
.dienst img { width: 100%; height: 100%; object-fit: cover; }
.dienst:hover { opacity: 0.95; }
.dienst.on { opacity: 1; border-color: var(--accent); }
.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.gesamt { font-size: 0.82rem; }
.ranges { display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: flex-end; margin-bottom: 1rem; }
.ranges .field input { width: 120px; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); padding-bottom: 0.55rem; }
.check input { width: auto; }
.hinweis { margin-bottom: 1rem; }
.hinweis a { color: inherit; margin-left: 0.4rem; }
@media (max-width: 700px) {
  .ansicht { width: 100%; margin-right: 0; }
  .ansicht button { flex: 1; }
  .aufklapp { position: static; }
  .leiste { position: relative; }
  .menue, .menue.breit { left: 0; right: 0; width: auto; }
}
</style>
