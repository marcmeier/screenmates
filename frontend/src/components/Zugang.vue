<script setup>
import { ref } from 'vue'
import { useApp } from '../stores/app'
import FilmPicker from './FilmPicker.vue'
import Icon from './Icon.vue'

// The group's front door: answer the access question by clicking the right film.
const app = useApp()
const error = ref('')
const busy = ref(false)

async function pick(movie) {
  error.value = ''
  busy.value = true
  try {
    await app.answer(movie.id)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="door">
    <div class="card panel">
      <div class="brand">screen<span>mates</span></div>
      <p class="lock"><Icon name="schloss" :size="15" /> Nur für unsere Gruppe</p>
      <h1>{{ app.zugang.frage }}</h1>
      <p class="muted">Such den Film und klick ihn an.</p>
      <FilmPicker endpoint="/api/zugang/suche" :busy="busy" @pick="pick" />
      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
  </main>
</template>

<style scoped>
.door { min-height: 100vh; display: grid; place-items: center; padding: 1.5rem; }
.card { width: min(480px, 100%); padding: 2rem; text-align: center; }
.brand { font-weight: 800; font-size: 1.6rem; letter-spacing: -0.03em; }
.brand span { color: var(--accent); }
.lock { display: inline-flex; align-items: center; gap: 0.35rem; color: var(--muted); font-size: 0.8rem; margin: 0.4rem 0 1.4rem; }
h1 { font-size: 1.3rem; font-weight: 650; margin: 0 0 0.3rem; }
.card > .muted { margin: 0 0 1rem; font-size: 0.9rem; }
.card :deep(.picker) { text-align: left; }
.error { color: #ff6b6b; margin: 1rem 0 0; }
</style>
