<script setup>
import { reactive, ref, watch } from 'vue'
import { api } from '../../api'
import MovieGrid from '../MovieGrid.vue'

// Results for a free-text mood. The question comes from the shared search field.
const props = defineProps({ frage: { type: String, required: true } })
const opts = reactive({ ohne_gesehene: true, mit_sammlung: false })
const results = ref([])
const loading = ref(false)
const failed = ref(false)

async function ask() {
  loading.value = true
  failed.value = false
  results.value = []
  try {
    results.value = (await api.post('/api/ki-suche', { beschreibung: props.frage, ...opts })).results
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
watch(() => [props.frage, opts.ohne_gesehene, opts.mit_sammlung], ask, { immediate: true })
</script>

<template>
  <section>
    <div class="row opts">
      <span class="muted">Die KI schlägt vor zu „{{ frage }}“</span>
      <span class="spacer"></span>
      <label class="check"><input v-model="opts.ohne_gesehene" type="checkbox" /> ohne Gesehene</label>
      <label class="check"><input v-model="opts.mit_sammlung" type="checkbox" /> nur aus unserem Katalog</label>
    </div>
    <p v-if="loading" class="muted thinking">Die KI denkt nach … das dauert ein paar Sekunden.</p>
    <MovieGrid
      :movies="results"
      :loading="loading"
      :failed="failed"
      empty-title="Keine passenden Filme gefunden"
      empty-text="Formulier es anders oder lockere die Optionen."
      @retry="ask"
    >
      <template #card="{ movie }">
        <p class="why">{{ movie.warum }}</p>
      </template>
    </MovieGrid>
  </section>
</template>

<style scoped>
.opts { margin-bottom: 1.2rem; font-size: 0.88rem; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); }
.check input { width: auto; }
.thinking { margin: 0 0 1rem; }
.why { font-size: 0.78rem; color: var(--muted); margin: 0.3rem 0 0; line-height: 1.35; }
</style>
