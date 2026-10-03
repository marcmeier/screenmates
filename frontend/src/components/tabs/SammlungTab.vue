<script setup>
import { computed } from 'vue'
import { useApp } from '../../stores/app'
import { useRoute } from '../../composables/useRoute'
import GesehenView from '../sammlung/GesehenView.vue'
import MerklisteView from '../sammlung/MerklisteView.vue'

// The group's two lists on one page: what we want to see, and what we've seen.
const app = useApp()
const route = useRoute()
const VIEWS = [
  { id: 'merkliste', label: 'Merkliste', count: () => app.status.wishlist_count },
  { id: 'gesehen', label: 'Gesehen', count: () => app.status.watched_count },
]
const current = computed(() => (route.value.sub === 'gesehen' ? 'gesehen' : 'merkliste'))
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Unsere Filme</h1>
        <p>Was wir sehen wollen – und was wir schon gesehen haben.</p>
      </div>
    </header>

    <nav class="segments" aria-label="Liste">
      <a
        v-for="v in VIEWS"
        :key="v.id"
        :href="`#/sammlung/${v.id}`"
        :class="{ active: current === v.id }"
        :aria-current="current === v.id ? 'page' : undefined"
      >
        {{ v.label }} <span class="count">{{ v.count() ?? '' }}</span>
      </a>
    </nav>

    <MerklisteView v-if="current === 'merkliste'" />
    <GesehenView v-else />
  </div>
</template>

<style scoped>
.segments {
  display: inline-flex; gap: 2px; padding: 3px; margin-bottom: 1.4rem;
  background: var(--bg-soft); border: 1px solid var(--line); border-radius: 10px;
}
.segments a {
  padding: 0.45rem 1rem; border-radius: 7px; text-decoration: none; color: var(--muted); font-size: 0.92rem;
  display: inline-flex; align-items: center; gap: 0.45rem;
}
.segments a:hover { color: var(--text); }
.segments a.active { background: var(--bg-raised); color: var(--text); font-weight: 600; box-shadow: inset 0 -2px 0 var(--accent); }
.count { font-size: 0.75rem; color: var(--muted); font-weight: 600; }
</style>
