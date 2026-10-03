<script setup>
import { reactive, ref } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import Icon from '../Icon.vue'
import MovieGrid from '../MovieGrid.vue'

const app = useApp()
const form = reactive({ beschreibung: '', ohne_gesehene: true, mit_sammlung: false, jahr_min: null, note_min: null, dauer_max: null })
const results = ref([])
const loading = ref(false)
const asked = ref(false)

const BEISPIELE = [
  'Langsamer Folk-Horror mit beklemmender Atmosphäre',
  'Spaßiger 80er-Creature-Feature für einen lockeren Abend',
  'Psychohorror, der einen noch Tage beschäftigt',
  'Found Footage, aber bitte gut',
]

async function ask() {
  loading.value = true
  asked.value = true
  results.value = []
  try {
    const body = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== null && v !== ''))
    results.value = (await api.post('/api/ki-suche', body)).results
  } catch {
    asked.value = false
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>KI-Suche</h1>
        <p>Beschreib die Stimmung – die KI schlägt passende Filme vor.</p>
      </div>
    </header>

    <div v-if="!app.status.ki" class="notice">
      Die KI-Suche ist nicht eingerichtet. Trag <code>LLM_API_KEY</code> (Anthropic) in <code>backend/.env</code> ein und starte das Backend neu.
    </div>

    <template v-else>
      <form class="panel ask" @submit.prevent="ask">
        <textarea
          v-model="form.beschreibung"
          rows="3"
          maxlength="1000"
          placeholder="Worauf habt ihr heute Lust?"
          aria-label="Beschreibung"
          @keydown.ctrl.enter="ask"
        ></textarea>
        <div class="row examples">
          <button v-for="b in BEISPIELE" :key="b" type="button" class="chip" @click="form.beschreibung = b">{{ b }}</button>
        </div>
        <div class="row">
          <label class="field">Jahr ab<input v-model.number="form.jahr_min" type="number" min="1900" max="2100" /></label>
          <label class="field">Note ab<input v-model.number="form.note_min" type="number" min="0" max="10" step="0.5" /></label>
          <label class="field">Länge bis<input v-model.number="form.dauer_max" type="number" min="0" step="5" /></label>
          <label class="check"><input v-model="form.ohne_gesehene" type="checkbox" /> ohne Gesehene</label>
          <label class="check"><input v-model="form.mit_sammlung" type="checkbox" /> nur aus unserem Katalog</label>
          <span class="spacer"></span>
          <button class="primary" :disabled="loading"><Icon name="ki" :size="16" /> {{ loading ? 'Denkt nach …' : 'Vorschläge holen' }}</button>
        </div>
      </form>

      <MovieGrid v-if="asked" :movies="results" :loading="loading" empty-title="Keine passenden Filme gefunden" empty-text="Formulier es anders oder lockere die Filter.">
        <template #card="{ movie }">
          <p class="why">{{ movie.warum }}</p>
        </template>
      </MovieGrid>
    </template>
  </div>
</template>

<style scoped>
.ask { display: flex; flex-direction: column; gap: 0.9rem; margin-bottom: 2rem; }
.ask .field input { width: 110px; }
.examples .chip:hover { color: var(--text); border-color: #44444f; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); align-self: flex-end; padding-bottom: 0.55rem; }
.check input { width: auto; }
.why { font-size: 0.78rem; color: var(--muted); margin: 0.3rem 0 0; line-height: 1.35; }
</style>
