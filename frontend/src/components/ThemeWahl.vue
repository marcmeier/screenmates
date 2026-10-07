<script setup>
import { computed } from 'vue'
import { api, inReihe } from '../api'
import { useApp } from '../stores/app'
import { THEMES, anwenden } from '../design'

// The colour themes as small previews. Applies at once, saved with your profile.
const app = useApp()
const design = computed(() => ({ theme: 'kino', schrift: 'inter', ...(app.me?.design || {}) }))

// Applied and remembered at once; the server gets only the theme, in click order (see Darstellung.vue).
const reihe = inReihe()
async function waehlen(theme) {
  app.me.design = { ...app.me.design, theme }
  anwenden(design.value)
  await reihe(() => api.put('/api/users/me/design', { theme }))
}
</script>

<template>
  <div class="themes" role="radiogroup" :aria-label="$t('darstellung.farbschema')">
    <button
      v-for="(t, key) in THEMES"
      :key="key"
      class="theme"
      role="radio"
      :aria-checked="design.theme === key"
      :class="{ aktiv: design.theme === key }"
      :style="{ '--t-bg': t.bg, '--t-raised': t.raised, '--t-accent': t.accent }"
      @click="waehlen(key)"
    >
      <span class="vorschau" aria-hidden="true"><span></span></span>
      {{ $t(`theme.${key}`) }}
    </button>
  </div>
</template>

<style scoped>
.themes { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 0.5rem; }
.theme { flex-direction: column; align-items: stretch; gap: 0.35rem; padding: 0.45rem; font-size: 0.8rem; }
.vorschau { display: block; height: 38px; border-radius: 6px; background: var(--t-bg); border: 1px solid var(--t-raised); position: relative; overflow: hidden; }
.vorschau span { position: absolute; left: 8px; right: 40%; bottom: 8px; height: 8px; border-radius: 4px; background: var(--t-accent); }
.aktiv { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
</style>
