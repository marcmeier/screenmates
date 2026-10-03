<script setup>
import { ref, watch } from 'vue'
import { api } from '../../api'
import MovieGrid from '../MovieGrid.vue'

const props = defineProps({ id: { type: String, required: true } })
defineEmits(['name'])

const films = ref([])
const person = ref(null)
const loading = ref(false)
const nurHorror = ref(true)

watch(
  () => [props.id, nurHorror.value],
  async () => {
    loading.value = true
    try {
      const r = await api.get(`/api/personen/${props.id}/filme?nur_horror=${nurHorror.value}`)
      films.value = r.results
      person.value = r.person
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)
</script>

<template>
  <section>
    <div class="row head">
      <h2>{{ person?.name || 'Filmografie' }}</h2>
      <span class="spacer"></span>
      <label class="check"><input v-model="nurHorror" type="checkbox" /> Nur Horror</label>
    </div>
    <MovieGrid
      :movies="films"
      :loading="loading"
      :empty-title="nurHorror ? `Keine Horrorfilme mit ${person?.name || 'dieser Person'}` : 'Keine Filme gefunden'"
    >
      <template #card="{ movie }">
        <div class="roles">{{ movie.rollen.join(', ') }}</div>
      </template>
    </MovieGrid>
    <p v-if="!loading && !films.length && nurHorror" class="center">
      <button class="small" @click="nurHorror = false">Alle Filme zeigen</button>
    </p>
  </section>
</template>

<style scoped>
.head { margin-bottom: 1.2rem; }
h2 { margin: 0; font-size: 1.3rem; }
.check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; color: var(--muted); }
.check input { width: auto; }
.center { text-align: center; }
.roles { font-size: 0.72rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
