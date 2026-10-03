<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { useMovieActions } from '../composables/useMovieActions'
import { navigate } from '../composables/useRoute'
import { laufzeit, dezimal } from '../format'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import Poster from './Poster.vue'
import WatchedEntry from './WatchedEntry.vue'
import WemGefaellts from './WemGefaellts.vue'
import WoLaeuft from './WoLaeuft.vue'

const app = useApp()
const ui = useUi()
const { toggleMerken, toggleVorschlag, alsGesehen, istVorgeschlagen } = useMovieActions()

const film = ref(null)
const credits = ref({ cast: [], crew: [] })
const similar = ref([])
const abende = ref([]) // our watched entries for this film, newest first
const anbieter = ref(null) // where it streams (null without TMDB)
const trailer = ref(null)
const trailerAn = ref(false) // YouTube is only contacted once someone presses play
let ctrl = null

// Ratings and guestbook belong where people look at a film, not only in "Gesehen".
async function ladeAbende(id = film.value?.id) {
  if (!id) return
  abende.value = (await api.get(`/api/watched?movie_id=${id}`, { quiet: true }).catch(() => ({ watched: [] }))).watched
}
watch(() => ui.changes, () => ladeAbende())

function ersetze(entry) {
  const i = abende.value.findIndex((e) => e.id === entry.id)
  if (i >= 0) abende.value[i] = entry
}

// Average over every evening and every person, like the group's own score.
const unserSchnitt = computed(() => {
  const stars = abende.value.flatMap((e) => e.ratings.map((r) => r.stars))
  return stars.length ? { wert: dezimal(stars.reduce((a, b) => a + b, 0) / stars.length), n: stars.length } : null
})

watch(
  () => ui.detail,
  async (m) => {
    ctrl?.abort()
    if (!m) return
    ctrl = new AbortController()
    const { signal } = ctrl
    // Show what we already have immediately; the card is the source object for flags.
    film.value = m
    credits.value = { cast: [], crew: [] }
    similar.value = []
    abende.value = []
    anbieter.value = null
    trailer.value = null
    trailerAn.value = false
    ladeAbende(m.id)
    const [full, c, s, w, t] = await Promise.allSettled([
      api.get(`/api/movies/${m.id}`, { signal, quiet: true }),
      api.get(`/api/movies/${m.id}/credits`, { signal, quiet: true }),
      api.get(`/api/movies/${m.id}/aehnliche?limit=12`, { signal, quiet: true }),
      api.get(`/api/movies/${m.id}/anbieter`, { signal, quiet: true }),
      api.get(`/api/movies/${m.id}/trailer`, { signal, quiet: true }),
    ])
    if (signal.aborted) return
    if (full.status === 'fulfilled') Object.assign(m, full.value)
    if (c.status === 'fulfilled') credits.value = c.value
    if (s.status === 'fulfilled') similar.value = s.value.results
    if (w.status === 'fulfilled' && w.value.verfuegbar) anbieter.value = w.value
    if (t.status === 'fulfilled') trailer.value = t.value.trailer
  },
  { immediate: true },
)

const regie = computed(() => credits.value.crew.filter((c) => c.rolle === 'Director'))

function person(p) {
  ui.detail = null
  navigate('finden', 'person', p.id)
}
</script>

<template>
  <Modal v-if="film" :label="film.title" width="820px" @close="ui.detail = null">
    <div v-if="trailerAn" class="player">
      <iframe
        :src="`https://www.youtube-nocookie.com/embed/${trailer.key}?autoplay=1&rel=0&hl=de`"
        :title="`Trailer: ${film.title}`"
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        allowfullscreen
      ></iframe>
      <button class="close" aria-label="Trailer schließen" @click="trailerAn = false"><Icon name="x" /></button>
    </div>
    <div v-else class="hero" :style="film.backdrop_url ? { backgroundImage: `url(${film.backdrop_url})` } : {}">
      <button class="close" aria-label="Schließen" @click="ui.detail = null"><Icon name="x" /></button>
      <button v-if="trailer" class="trailer-btn" @click="trailerAn = true">
        <Icon name="play" :size="18" /> Trailer{{ trailer.sprache && trailer.sprache !== 'de' ? ` (${trailer.sprache.toUpperCase()})` : '' }}
      </button>
    </div>

    <div class="body" :class="{ 'unter-trailer': trailerAn }">
      <div class="frame"><Poster :movie="film" /></div>
      <div class="info">
        <h2>{{ film.title }}</h2>
        <p v-if="film.original_title && film.original_title !== film.title" class="muted orig">{{ film.original_title }}</p>
        <div class="row facts">
          <span v-if="film.year">{{ film.year }}</span>
          <span v-if="film.runtime">{{ laufzeit(film.runtime) }}</span>
          <span v-if="film.vote_average" class="gold" title="Bewertung bei TMDB">★ {{ dezimal(film.vote_average) }} <span class="muted">({{ film.vote_count }})</span></span>
          <span v-if="unserSchnitt" class="ours" :title="`${unserSchnitt.n} Bewertungen aus eurer Gruppe`">Ihr: ★ {{ unserSchnitt.wert }}</span>
          <span v-for="g in film.genres" :key="g" class="chip">{{ g }}</span>
        </div>
        <p v-if="regie.length" class="muted">
          Regie:
          <template v-for="(p, i) in regie" :key="p.id">
            <a href="#" @click.prevent="person(p)">{{ p.name }}</a><span v-if="i < regie.length - 1">, </span>
          </template>
        </p>

        <div v-if="app.me" class="row actions">
          <button v-if="!film.gesehen" class="primary" @click="alsGesehen(film)"><Icon name="gesehen" /> Gesehen</button>
          <span v-else class="chip seen"><Icon name="gesehen" :size="14" /> Schon gesehen</span>
          <button :class="{ on: film.gemerkt }" @click="toggleMerken(film)">
            <Icon name="merken" /> {{ film.gemerkt ? 'Gemerkt' : 'Merken' }}
          </button>
          <button :class="{ on: istVorgeschlagen(film) }" @click="toggleVorschlag(film)">
            <Icon name="hand" /> {{ istVorgeschlagen(film) ? 'Vorgeschlagen' : 'Vorschlagen' }}
          </button>
        </div>
        <p v-else class="muted"><a href="#" @click.prevent="ui.loginOpen = true">Namen wählen</a>, um mitzumachen.</p>
      </div>
    </div>

    <div class="sections">
      <p class="overview">{{ film.overview || 'Keine Beschreibung vorhanden.' }}</p>

      <WoLaeuft v-if="anbieter" :anbieter="anbieter" />

      <WemGefaellts :movie-id="film.id" />

      <template v-if="abende.length">
        <h3 class="section-title">Eure Bewertung</h3>
        <div class="abende">
          <WatchedEntry v-for="e in abende" :key="e.id" :entry="e" kompakt @update="ersetze" @removed="ladeAbende()" />
        </div>
      </template>

      <template v-if="credits.cast.length">
        <h3 class="section-title">Besetzung</h3>
        <div class="cast">
          <button v-for="p in credits.cast" :key="p.id" class="person" @click="person(p)">
            <img v-if="p.bild" :src="p.bild" alt="" loading="lazy" />
            <span v-else class="noimg"></span>
            <span class="pname">{{ p.name }}</span>
            <span class="prole">{{ p.rolle }}</span>
          </button>
        </div>
      </template>

      <template v-if="similar.length">
        <h3 class="section-title">Ähnliche Filme</h3>
        <div class="similar">
          <button v-for="s in similar" :key="s.id" class="sim" :title="s.title" @click="ui.open(s)">
            <span class="simposter"><Poster :movie="s" /></span>
            <span class="simtitle">{{ s.title }}</span>
          </button>
        </div>
      </template>
    </div>
  </Modal>
</template>

<style scoped>
.hero {
  position: relative; height: 260px; background: linear-gradient(135deg, #24161a, #0e0e12) center / cover;
  border-radius: 14px 14px 0 0;
}
.hero::after { content: ''; position: absolute; inset: 0; background: linear-gradient(transparent 35%, var(--bg-soft)); }
.close { position: absolute; top: 12px; right: 12px; z-index: 2; border-radius: 50%; padding: 0.45rem; background: rgba(0, 0, 0, 0.6); }
.player { position: relative; aspect-ratio: 16 / 9; background: #000; border-radius: 14px 14px 0 0; overflow: hidden; }
.player iframe { width: 100%; height: 100%; border: 0; display: block; }
.trailer-btn {
  position: absolute; left: 1.6rem; top: 1.2rem; z-index: 2; background: rgba(0, 0, 0, 0.65);
  border-color: rgba(255, 255, 255, 0.25); backdrop-filter: blur(4px); font-weight: 600;
}
.trailer-btn:hover { background: var(--accent); border-color: var(--accent); }
.body.unter-trailer { margin-top: 1.2rem; }
.body.unter-trailer .info { padding-top: 0; }
.body { display: flex; gap: 1.4rem; padding: 0 1.6rem; margin-top: -110px; position: relative; z-index: 1; }
.frame { width: 150px; aspect-ratio: 2/3; border-radius: 10px; overflow: hidden; box-shadow: var(--shadow); flex: none; border: 1px solid var(--line); }
.info { padding-top: 70px; min-width: 0; }
h2 { margin: 0; font-size: 1.7rem; letter-spacing: -0.02em; }
.orig { margin: 0.2rem 0 0; font-style: italic; }
.facts { margin: 0.8rem 0; font-size: 0.9rem; }
.gold { color: var(--gold); font-weight: 600; }
.info a { color: var(--text); }
.actions { margin-top: 1rem; }
.chip.seen { color: var(--ok); border-color: var(--ok); padding: 6px 12px; }
.sections { padding: 0.4rem 1.6rem 1.8rem; }
.overview { line-height: 1.65; margin: 1.2rem 0 0; }
.ours { color: var(--gold); font-weight: 700; border: 1px solid rgba(245, 166, 35, 0.4); border-radius: 999px; padding: 1px 9px; font-size: 0.85rem; }
.abende { display: flex; flex-direction: column; gap: 1.4rem; }
.abende > * + * { border-top: 1px solid var(--line); padding-top: 1.2rem; }
.cast, .similar { display: flex; gap: 0.8rem; overflow-x: auto; padding-bottom: 0.5rem; }
.person, .sim { flex: none; flex-direction: column; align-items: flex-start; gap: 4px; padding: 0; border: none; background: none; text-align: left; }
.person:hover, .sim:hover { background: none; }
.person { width: 92px; }
.person img, .noimg { width: 92px; height: 120px; object-fit: cover; border-radius: 8px; background: var(--bg-raised); }
.pname { font-size: 0.8rem; font-weight: 600; }
.prole { font-size: 0.72rem; color: var(--muted); line-height: 1.2; }
.sim { width: 110px; }
.simposter { display: block; width: 110px; aspect-ratio: 2/3; border-radius: 8px; overflow: hidden; }
.sim:hover .simposter { outline: 2px solid var(--accent); }
.simtitle { font-size: 0.78rem; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 640px) {
  .body { flex-direction: column; margin-top: -80px; }
  .frame { width: 110px; }
  .info { padding-top: 0; }
  .hero { height: 180px; }
}
</style>
