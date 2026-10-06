<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import MovieCard from './MovieCard.vue'

const props = defineProps({
  movies: { type: Array, required: true },
  loading: Boolean,
  failed: Boolean,
  more: Boolean,
  emptyTitle: { type: String, default: null },
  emptyText: { type: String, default: '' },
  emptyLink: { type: Object, default: null }, // { href, label }: one way on from an empty list
})
const emit = defineEmits(['more', 'retry'])

// Endless scrolling: when the "Mehr laden" button comes near the viewport,
// the next page loads by itself. The button stays for keyboards and old browsers.
const knopf = ref(null)
let beobachter = null
let inReichweite = false
const weiter = () => inReichweite && props.more && !props.loading && emit('more')
watch(knopf, (el) => {
  beobachter?.disconnect()
  inReichweite = false
  if (!el || !('IntersectionObserver' in window)) return
  beobachter = new IntersectionObserver(
    ([e]) => {
      inReichweite = e.isIntersecting
      weiter()
    },
    { rootMargin: '600px 0px' },
  )
  beobachter.observe(el)
})
// The observer only reports changes. If the button was already in reach while a
// page was loading, ask again once loading is done – otherwise scrolling stalls.
watch(() => props.loading, (laedt) => !laedt && weiter())
onBeforeUnmount(() => beobachter?.disconnect())
</script>

<template>
  <div>
    <div v-if="movies.length" class="grid">
      <MovieCard v-for="m in movies" :key="m.id" :movie="m">
        <slot name="card" :movie="m" />
      </MovieCard>
    </div>

    <div v-if="loading" class="grid" :style="{ marginTop: movies.length ? '1.3rem' : 0 }" aria-busy="true">
      <div v-for="i in 12" :key="i" class="skeleton" style="aspect-ratio: 2 / 3"></div>
    </div>
    <div v-else-if="failed" class="empty">
      <strong>{{ $t('moviegrid.dasHatNichtGeklappt') }}</strong>
      <button class="small" style="margin-top: 0.6rem" @click="$emit('retry')">{{ $t('moviegrid.nochmalVersuchen') }}</button>
    </div>
    <div v-else-if="!movies.length" class="empty">
      <strong>{{ emptyTitle ?? $t('moviegrid.nichtsGefunden') }}</strong>
      <span v-if="emptyText">{{ emptyText }}</span>
      <a v-if="emptyLink" :href="emptyLink.href" class="button small leer-los">{{ emptyLink.label }}</a>
    </div>

    <div v-if="more && !loading" ref="knopf" class="more">
      <button @click="$emit('more')">{{ $t('moviegrid.mehrLaden') }}</button>
    </div>
  </div>
</template>

<style scoped>
.more { display: flex; justify-content: center; margin-top: 1.8rem; }
.leer-los { margin-top: 0.8rem; }
</style>
