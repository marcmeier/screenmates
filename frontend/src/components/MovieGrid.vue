<script setup>
import MovieCard from './MovieCard.vue'

defineProps({
  movies: { type: Array, required: true },
  loading: Boolean,
  failed: Boolean,
  more: Boolean,
  emptyTitle: { type: String, default: 'Nichts gefunden' },
  emptyText: { type: String, default: '' },
})
defineEmits(['more', 'retry'])
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
      <strong>Das hat nicht geklappt</strong>
      <button class="small" style="margin-top: 0.6rem" @click="$emit('retry')">Nochmal versuchen</button>
    </div>
    <div v-else-if="!movies.length" class="empty">
      <strong>{{ emptyTitle }}</strong>
      <span v-if="emptyText">{{ emptyText }}</span>
    </div>

    <div v-if="more && !loading" class="more">
      <button @click="$emit('more')">Mehr laden</button>
    </div>
  </div>
</template>

<style scoped>
.more { display: flex; justify-content: center; margin-top: 1.8rem; }
</style>
