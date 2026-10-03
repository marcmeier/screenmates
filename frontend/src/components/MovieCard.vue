<script setup>
import { computed } from 'vue'
const props = defineProps({ movie: Object })
const emit = defineEmits(['open', 'action'])
const year = computed(() => props.movie.year || (props.movie.release_date || '').slice(0, 4))
const rating = computed(() => (props.movie.vote_average || 0).toFixed(1))
</script>

<template>
  <div class="card" @click="emit('open', movie)">
    <div class="poster" :class="{ placeholder: !movie.poster_url }">
      <img v-if="movie.poster_url" :src="movie.poster_url" :alt="movie.title" loading="lazy" />
      <span v-else class="ph-title">{{ movie.title }}</span>
      <div class="badge" v-if="movie.vote_average">★ {{ rating }}</div>
      <div class="hover">
        <slot name="actions" :movie="movie" />
      </div>
    </div>
    <div class="meta">
      <div class="title" :title="movie.title">{{ movie.title }}</div>
      <div class="sub muted">{{ year }}<span v-if="movie.runtime"> · {{ movie.runtime }} min</span></div>
    </div>
  </div>
</template>

<style scoped>
.card { cursor: pointer; }
.poster {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--bg-soft);
  border: 1px solid var(--line);
}
.poster img { width: 100%; height: 100%; object-fit: cover; display: block; }
.poster.placeholder {
  display: flex; align-items: center; justify-content: center;
  padding: 0.8rem; text-align: center;
  background: linear-gradient(160deg, #1b1b22, #0e0e12);
}
.ph-title { font-weight: 600; font-size: 0.95rem; color: #d0d0dc; }
.badge {
  position: absolute; top: 8px; left: 8px;
  background: rgba(0,0,0,0.7); color: #f5a623;
  padding: 2px 7px; border-radius: 6px; font-size: 0.75rem; font-weight: 600;
}
.hover {
  position: absolute; inset: 0; display: flex; gap: 6px;
  align-items: flex-end; justify-content: center; padding: 10px;
  opacity: 0; transition: opacity 0.15s;
  background: linear-gradient(transparent 50%, rgba(0,0,0,0.85));
}
.card:hover .hover { opacity: 1; }
.card:hover .poster { border-color: var(--accent); }
.meta { padding: 0.5rem 0.2rem; }
.title { font-size: 0.9rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub { font-size: 0.78rem; margin-top: 2px; }
</style>
