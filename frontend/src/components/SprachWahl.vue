<script setup>
import { api, inReihe } from '../api'
import { SPRACHEN, sprache, spracheSetzen } from '../i18n'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'

// German or English: switches at once and is kept with your profile (all your devices).
const app = useApp()
const FLAGGEN = { de: '🇩🇪', en: '🇬🇧' }
const reihe = inReihe()

// Switched and remembered at once; the answers may come back in any order, so they don't
// overwrite what's on screen, and the requests go out one after the other.
async function waehlen(s) {
  spracheSetzen(s)
  if (app.me) {
    app.me.design = { ...app.me.design, sprache: s }
    await reihe(() => api.put('/api/users/me/sprache', { sprache: s }))
  }
  // Texts from the server (awards, shelves, facts …) come again in the new language.
  useUi().changed()
}
</script>

<template>
  <div class="sprachen" role="radiogroup" :aria-label="$t('sprache.wahl')">
    <button
      v-for="(name, key) in SPRACHEN"
      :key="key"
      role="radio"
      :aria-checked="sprache() === key"
      :class="{ aktiv: sprache() === key }"
      @click="waehlen(key)"
    >
      <span aria-hidden="true">{{ FLAGGEN[key] }}</span> {{ name }}
    </button>
  </div>
</template>

<style scoped>
.sprachen { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.sprachen button { gap: 0.45rem; }
.aktiv { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
</style>
