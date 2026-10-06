<script setup>
import { api } from '../api'
import { SPRACHEN, sprache, spracheSetzen } from '../i18n'
import { useApp } from '../stores/app'

// German or English: switches at once and is kept with your profile (all your devices).
const app = useApp()
const FLAGGEN = { de: '🇩🇪', en: '🇬🇧' }

async function waehlen(s) {
  spracheSetzen(s)
  if (app.me) app.me.design = (await api.put('/api/users/me/sprache', { sprache: s })).design
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
