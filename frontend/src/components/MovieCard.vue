<script setup>
import { dezimal } from '../format'
import Icon from './Icon.vue'
import Poster from './Poster.vue'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { useMovieActions } from '../composables/useMovieActions'

const props = defineProps({ movie: { type: Object, required: true }, actions: { type: Boolean, default: true } })
const app = useApp()
const ui = useUi()
const { toggleMerken, toggleVorschlag, istVorgeschlagen } = useMovieActions()
</script>

<template>
  <article class="card" :class="{ seen: movie.gesehen }">
    <button class="cover" :aria-label="$t('allg.detailsVon', { title: movie.title })" @click="ui.open(movie)">
      <Poster :movie="movie" />
      <span v-if="movie.vote_average" class="score">★ {{ dezimal(movie.vote_average) }}</span>
      <span v-if="movie.gesehen" class="ribbon"><Icon name="gesehen" :size="13" /> gesehen</span>
    </button>

    <div v-if="actions && app.me && !movie.gesehen" class="quick">
      <button
        class="small"
        :class="{ on: movie.gemerkt }"
        :aria-pressed="!!movie.gemerkt"
        :title="movie.gemerkt ? $t('moviecard.vonDerMerklisteNehmen') : $t('moviecard.merken')"
        @click="toggleMerken(movie)"
      >
        <Icon name="merken" :size="15" /><span class="sr-only">{{ $t('moviecard.merken2') }}</span>
      </button>
      <button
        class="small"
        :class="{ on: istVorgeschlagen(props.movie) }"
        :aria-pressed="istVorgeschlagen(props.movie)"
        :title="istVorgeschlagen(props.movie) ? $t('moviecard.vorschlagZurueckziehen') : $t('moviecard.fuerDenNaechstenAbend')"
        @click="toggleVorschlag(movie)"
      >
        <Icon name="hand" :size="15" /><span class="sr-only">{{ $t('moviecard.vorschlagen') }}</span>
      </button>
    </div>

    <div class="meta">
      <div class="title" :title="movie.title">{{ movie.title }}</div>
      <div class="sub">
        {{ movie.year || '—' }}
        <span v-if="movie.vorgeschlagen_von?.length" class="votes" :title="$t('moviecard.lengthVorschlaege', { length: movie.vorgeschlagen_von.length })">
          · <Icon name="hand" :size="12" /> {{ movie.vorgeschlagen_von.length }}
        </span>
      </div>
      <slot />
    </div>
  </article>
</template>

<style scoped>
.card { position: relative; min-width: 0; }
.cover {
  position: relative; display: block; width: 100%; padding: 0;
  aspect-ratio: 2 / 3; border-radius: var(--radius); overflow: hidden;
  background: linear-gradient(160deg, #1d1d25, #0e0e12); border: 1px solid var(--line);
  transition: transform 0.18s ease, border-color 0.18s, box-shadow 0.18s;
}
.cover:hover { transform: translateY(-3px); border-color: #44444f; box-shadow: 0 12px 30px rgba(0, 0, 0, 0.5); background: #15151b; }
.score {
  position: absolute; top: 7px; left: 7px; background: rgba(0, 0, 0, 0.72); color: var(--gold);
  padding: 2px 7px; border-radius: 6px; font-size: 0.72rem; font-weight: 700;
}
.ribbon {
  position: absolute; bottom: 0; left: 0; right: 0; display: flex; align-items: center; justify-content: center; gap: 4px;
  background: rgba(10, 10, 12, 0.85); color: var(--ok); font-size: 0.72rem; font-weight: 600; padding: 4px;
}
.seen .cover :deep(.poster) { filter: grayscale(0.6) brightness(0.75); }
.quick {
  position: absolute; top: 6px; right: 6px; display: flex; flex-direction: column; gap: 5px;
  opacity: 0; transition: opacity 0.15s;
}
.quick button { background: rgba(10, 10, 12, 0.8); padding: 0.35rem; backdrop-filter: blur(4px); }
.quick button.on { background: var(--accent); border-color: var(--accent); }
.card:hover .quick, .card:focus-within .quick { opacity: 1; }
@media (hover: none) { .quick { opacity: 1; } }
.meta { padding: 0.55rem 0.15rem 0; }
.title { font-size: 0.9rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub { font-size: 0.78rem; color: var(--muted); display: flex; align-items: center; gap: 3px; }
.votes { display: inline-flex; align-items: center; gap: 3px; color: var(--text); }
</style>
