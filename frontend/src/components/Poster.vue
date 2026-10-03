<script setup>
import { computed } from 'vue'

// One poster everywhere. Without an image (no TMDB key, or TMDB has none) we
// draw a deliberate placeholder: a per-film colour so lists don't look broken.
const props = defineProps({
  movie: { type: Object, required: true },
  title: { type: Boolean, default: true },
})

const HUES = [350, 8, 268, 205, 28, 162, 320, 190]
const hue = computed(() => HUES[Math.abs(props.movie.id) % HUES.length])
</script>

<template>
  <img v-if="movie.poster_url" class="poster" :src="movie.poster_url" alt="" loading="lazy" />
  <div v-else class="poster placeholder" :style="{ '--h': hue }" aria-hidden="true">
    <template v-if="title">
      <span class="t">{{ movie.title }}</span>
      <span v-if="movie.year" class="y">{{ movie.year }}</span>
    </template>
  </div>
</template>

<style scoped>
.poster { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder {
  display: flex; flex-direction: column; justify-content: flex-end; gap: 0.25rem;
  padding: 12% 10%; container-type: inline-size;
  background:
    radial-gradient(120% 70% at 20% 0%, hsl(var(--h) 70% 30% / 0.65), transparent 60%),
    radial-gradient(90% 60% at 100% 100%, hsl(var(--h) 60% 12%), transparent 70%),
    linear-gradient(170deg, hsl(var(--h) 25% 13%), #09090b);
}
.t { font-weight: 800; line-height: 1.05; letter-spacing: -0.02em; color: #f4f1f1; font-size: clamp(0.6rem, 13cqi, 1.35rem); overflow-wrap: anywhere; }
.y { font-size: clamp(0.5rem, 8cqi, 0.8rem); color: hsl(var(--h) 40% 72%); font-weight: 600; }
</style>
