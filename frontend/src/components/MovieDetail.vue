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
const trailerSprache = computed(() => (trailer.value?.sprache && trailer.value.sprache !== 'de' ? ` (${trailer.value.sprache.toUpperCase()})` : ''))
let ctrl = null

// Ratings and guestbook belong where people look at a film, not only in "Gesehen".
async function ladeAbende(id = film.value?.id) {
  if (!id) return
  // The group's evenings with this film (the catalogue is open to everyone, the chronicle isn't).
  abende.value = app.gruppe
    ? (await api.get(`/api/watched?movie_id=${id}`, { quiet: true }).catch(() => ({ watched: [] }))).watched
    : []
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
        :title="$t('moviedetail.trailerTitle', { title: film.title })"
        allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
        allowfullscreen
      ></iframe>
      <button class="close" :aria-label="$t('moviedetail.trailerSchliessen')" @click="trailerAn = false"><Icon name="x" /></button>
    </div>
    <div v-else class="hero" :style="film.backdrop_url ? { backgroundImage: `url(${film.backdrop_url})` } : {}">
      <button class="close" :aria-label="$t('einladung.schliessen')" @click="ui.detail = null"><Icon name="x" /></button>
      <!-- Hard to miss: a big play button on the picture (and "Trailer" among the actions below). -->
      <button v-if="trailer" class="trailer-btn" :aria-label="$t('moviedetail.trailerAnsehen')" @click="trailerAn = true">
        <span class="play-kreis"><Icon name="play" :size="28" /></span>
        <span class="play-text">Trailer{{ trailerSprache }}</span>
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
          <span v-if="film.vote_average" class="gold" :title="$t('moviedetail.bewertungBeiTmdb')">★ {{ dezimal(film.vote_average) }} <span class="muted">({{ film.vote_count }})</span></span>
          <span v-if="unserSchnitt" class="ours" :title="$t('moviedetail.nBewertungenAusEurer', { n: unserSchnitt.n })">{{ $t('moviedetail.ihrWert', { wert: unserSchnitt.wert }) }}</span>
          <span v-for="g in film.genres" :key="g" class="chip">{{ g }}</span>
        </div>
        <p v-if="regie.length" class="muted">
          {{ $t('moviedetail.regie') }}
          <template v-for="(p, i) in regie" :key="p.id">
            <a href="#" @click.prevent="person(p)">{{ p.name }}</a><span v-if="i < regie.length - 1">, </span>
          </template>
        </p>

        <div v-if="app.me" class="row actions">
          <button v-if="trailer && !trailerAn" @click="trailerAn = true"><Icon name="play" /> Trailer{{ trailerSprache }}</button>
          <button v-if="!film.gesehen" class="primary" @click="alsGesehen(film)"><Icon name="gesehen" /> {{ $t('moviedetail.gesehen') }}</button>
          <span v-else class="chip seen"><Icon name="gesehen" :size="14" /> {{ $t('moviedetail.schonGesehen') }}</span>
          <button :class="{ on: film.gemerkt }" @click="toggleMerken(film)">
            <Icon name="merken" /> {{ film.gemerkt ? $t('moviedetail.gemerkt') : $t('moviedetail.merken') }}
          </button>
          <button :class="{ on: istVorgeschlagen(film) }" @click="toggleVorschlag(film)">
            <Icon name="hand" /> {{ istVorgeschlagen(film) ? $t('moviedetail.vorgeschlagen') : $t('moviedetail.vorschlagen') }}
          </button>
        </div>
        <p v-else class="muted"><a href="#" @click.prevent="ui.loginOpen = true">{{ $t('moviedetail.namenWaehlen') }}</a>{{ $t('moviedetail.umMitzumachen') }}</p>
      </div>
    </div>

    <div class="sections">
      <p class="overview">{{ film.overview || $t('moviedetail.keineBeschreibungVorhanden') }}</p>

      <WoLaeuft v-if="anbieter" :anbieter="anbieter" />

      <WemGefaellts :movie-id="film.id" />

      <template v-if="abende.length">
        <h3 class="section-title">{{ $t('moviedetail.eureBewertung') }}</h3>
        <div class="abende">
          <WatchedEntry v-for="e in abende" :key="e.id" :entry="e" kompakt @update="ersetze" @removed="ladeAbende()" />
        </div>
      </template>

      <template v-if="credits.cast.length">
        <h3 class="section-title">{{ $t('moviedetail.besetzung') }}</h3>
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
        <h3 class="section-title">{{ $t('moviedetail.aehnlicheFilme') }}</h3>
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
  position: absolute; z-index: 2; left: 50%; top: 40%; transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center; gap: 0.4rem; padding: 0; border: none; background: none;
  font-weight: 700; color: #fff; text-shadow: 0 2px 10px rgba(0, 0, 0, 0.8);
}
.play-kreis {
  width: 68px; height: 68px; border-radius: 50%; display: grid; place-items: center; padding-left: 4px;
  background: color-mix(in srgb, var(--accent) 85%, transparent); border: 2px solid rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 0 6px rgba(0, 0, 0, 0.25), 0 8px 30px color-mix(in srgb, var(--accent) 60%, transparent);
  transition: transform 0.15s, background 0.15s;
}
.trailer-btn:hover .play-kreis { transform: scale(1.08); background: var(--accent); }
.play-text { font-size: 0.9rem; letter-spacing: 0.02em; }
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
  .trailer-btn { top: 36%; }
  .play-kreis { width: 56px; height: 56px; }
}
</style>
