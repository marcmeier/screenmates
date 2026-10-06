<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import { datum } from '../format'
import Poster from './Poster.vue'
import StarRating from './StarRating.vue'

// "Wie war's?": the last evenings you were at but haven't rated – stars right here.
// Ratings feed "Wem gefällt's?", the year in review and the achievements.
const ui = useUi()
const offen = ref([])
const WEG = 'screenmates.wiewarsWeg'
function weggeklickt() {
  try {
    return new Set(JSON.parse(localStorage.getItem(WEG) || '[]'))
  } catch {
    return new Set()
  }
}
const weg = ref(weggeklickt())
const sichtbar = computed(() => offen.value.filter((w) => !weg.value.has(w.id)).slice(0, 3))

async function laden() {
  offen.value = (await api.get('/api/watched/zu-bewerten', { quiet: true }).catch(() => ({ offen: [] }))).offen
}
onMounted(laden)
watch(() => ui.changes, laden)

async function bewerten(w, sterne) {
  await api.post(`/api/watched/${w.id}/rating`, { stars: sterne })
  offen.value = offen.value.filter((x) => x.id !== w.id)
  ui.toast(t('wiewars.sterneFuerTitleDanke', { sterne, title: w.movie.title }), 'ok')
  ui.changed()
}
function spaeter(w) {
  weg.value = new Set([...weg.value, w.id])
  try {
    localStorage.setItem(WEG, JSON.stringify([...weg.value].slice(-50)))
  } catch {
    /* private mode */
  }
}
</script>

<template>
  <section v-if="sichtbar.length" class="wiewars" :aria-label="$t('wiewars.wieWarS')">
    <div v-for="w in sichtbar" :key="w.id" class="eintrag">
      <span class="plakat"><Poster :movie="w.movie" :title="false" /></span>
      <div class="text">
        <strong>{{ $t('wiewars.wieWarTitle', { title: w.movie.title }) }}</strong>
        <small class="muted">{{ $t('wiewars.xDeineSterneFehlen', { x: datum(w.am) }) }}</small>
      </div>
      <StarRating :model-value="0" @update:model-value="(n) => bewerten(w, n)" />
      <button class="ghost small" @click="spaeter(w)">{{ $t('wiewars.spaeter') }}</button>
    </div>
  </section>
</template>

<style scoped>
.wiewars { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.eintrag {
  display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; padding: 0.6rem 0.9rem; border-radius: var(--radius);
  border: 1px solid color-mix(in srgb, var(--gold) 45%, var(--line)); background: linear-gradient(90deg, color-mix(in srgb, var(--gold) 14%, transparent), var(--bg-soft) 60%);
}
.plakat { width: 32px; height: 48px; border-radius: 4px; overflow: hidden; flex: none; background: var(--bg-raised); }
.text { display: flex; flex-direction: column; flex: 1; min-width: 12rem; }
.text small { font-size: 0.78rem; }
.eintrag :deep(.stars button) { font-size: 1.5rem; }
</style>