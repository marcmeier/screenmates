<script setup>
import { computed, onMounted } from 'vue'
import { api, inReihe } from '../api'
import { useApp } from '../stores/app'
import { SCHRIFTEN, anwenden } from '../design'
import SprachWahl from './SprachWahl.vue'
import ThemeWahl from './ThemeWahl.vue'

// Your screenmates: language, colour theme and font. Stays dark; saved with your profile.
const app = useApp()
const design = computed(() => ({ theme: 'kino', schrift: 'inter', ...(app.me?.design || {}) }))

// Every font button shows itself in its font.
onMounted(() => Object.values(SCHRIFTEN).forEach((s) => s.laden?.()))

// Applied and remembered at once; the server gets only the font, so a theme picked a moment
// earlier (its answer still on the way) is never sent back as the old one. Fonts clicked in
// quick succession reach the server in that order.
const reihe = inReihe()
async function schrift(key) {
  app.me.design = { ...app.me.design, schrift: key }
  anwenden(design.value)
  await reihe(() => api.put('/api/users/me/design', { schrift: key }))
}
</script>

<template>
  <section class="panel">
    <h2>{{ $t('darstellung.titel') }}</h2>
    <p class="muted">{{ $t('darstellung.nurFuerDich') }}</p>
    <h3>{{ $t('sprache.wahl') }}</h3>
    <SprachWahl />
    <p class="muted klein">{{ $t('sprache.filmdaten') }}</p>
    <h3>{{ $t('darstellung.farbschema') }}</h3>
    <ThemeWahl />
    <h3>{{ $t('darstellung.schrift') }}</h3>
    <div class="schriften" role="radiogroup" :aria-label="$t('darstellung.schrift')">
      <button
        v-for="(s, key) in SCHRIFTEN"
        :key="key"
        role="radio"
        :aria-checked="design.schrift === key"
        :class="{ aktiv: design.schrift === key }"
        :style="{ fontFamily: s.familie || 'system-ui' }"
        @click="schrift(key)"
      >
        {{ $t(`schrift.${key}`) }}
      </button>
    </div>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; }
h3 { margin: 1.1rem 0 0.5rem; font-size: 0.95rem; }
p { margin: 0; font-size: 0.85rem; }
.klein { font-size: 0.78rem; margin-top: 0.4rem; }
.schriften { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.aktiv { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
</style>
