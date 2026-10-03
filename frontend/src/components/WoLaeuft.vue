<script setup>
import { computed } from 'vue'
import { useApp } from '../stores/app'
import Icon from './Icon.vue'

// Where a film streams in Germany (JustWatch data via TMDB). Subscriptions someone
// in the group already has are listed first and marked with their names.
const props = defineProps({ anbieter: { type: Object, required: true } })
const app = useApp()

const GRUPPEN = [
  { key: 'abo', label: 'Im Abo' },
  { key: 'kostenlos', label: 'Kostenlos' },
  { key: 'leihen', label: 'Leihen' },
  { key: 'kaufen', label: 'Kaufen' },
]
const gruppen = computed(() => GRUPPEN.filter((g) => props.anbieter[g.key]?.length))
const beiUns = computed(() => props.anbieter.abo.filter((p) => p.bei?.length))
const namen = (ids) => ids.map((id) => app.userById(id)?.name ?? '?').join(', ')
</script>

<template>
  <section class="wo">
    <h3 class="section-title">Wo läuft's?</h3>

    <p v-if="beiUns.length" class="treffer">
      <Icon name="gesehen" :size="15" />
      Läuft bei uns: <strong>{{ beiUns.map((p) => p.name).join(', ') }}</strong>
      <span class="muted">({{ namen([...new Set(beiUns.flatMap((p) => p.bei))]) }})</span>
    </p>

    <template v-if="gruppen.length">
      <div v-for="g in gruppen" :key="g.key" class="gruppe">
        <span class="label">{{ g.label }}</span>
        <ul class="logos">
          <li
            v-for="p in anbieter[g.key]"
            :key="p.id"
            :class="{ unser: p.bei?.length }"
            :title="p.bei?.length ? `${p.name} – hat: ${namen(p.bei)}` : p.name"
          >
            <img v-if="p.logo" :src="p.logo" :alt="p.name" loading="lazy" />
            <span v-else class="name">{{ p.name }}</span>
          </li>
        </ul>
      </div>
    </template>
    <p v-else class="muted">In Deutschland gerade nirgends zu sehen.</p>

    <p class="quelle muted">
      <a v-if="anbieter.link" :href="anbieter.link" target="_blank" rel="noopener noreferrer">Alle Angebote <Icon name="extern" :size="12" /></a>
      Daten: JustWatch
    </p>
  </section>
</template>

<style scoped>
.treffer { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin: 0 0 0.8rem; color: var(--ok); font-size: 0.9rem; }
.treffer strong { color: var(--text); }
.gruppe { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.6rem; }
.label { width: 5.5rem; flex: none; font-size: 0.8rem; color: var(--muted); }
.logos { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.45rem; }
.logos li { width: 40px; height: 40px; border-radius: 9px; overflow: hidden; background: var(--bg-raised); display: grid; place-items: center; }
.logos li.unser { box-shadow: 0 0 0 2px var(--bg-soft), 0 0 0 4px var(--ok); }
.logos img { width: 100%; height: 100%; object-fit: cover; }
.name { font-size: 0.55rem; text-align: center; padding: 2px; line-height: 1.1; }
.quelle { font-size: 0.75rem; margin: 0.4rem 0 0; display: flex; gap: 0.8rem; align-items: center; }
.quelle a { color: var(--text); display: inline-flex; align-items: center; gap: 3px; }
</style>
