<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { useApp } from '../store'

const app = useApp()
const emit = defineEmits(['close'])
const newName = ref('')
const error = ref('')
// Film-as-PIN: when a guarded user is picked, they must click the right film.
const schutzFor = ref(null)
const schutzQuery = ref('')
const schutzResults = ref([])

async function pick(u) {
  error.value = ''
  if (u.hat_schutz) { schutzFor.value = u; schutzQuery.value = ''; schutzResults.value = []; return }
  try { await app.choose(u.id); emit('close') } catch (e) { error.value = e.message }
}

async function searchFilm() {
  if (!schutzQuery.value.trim()) { schutzResults.value = []; return }
  const r = await api.get(`/api/search?q=${encodeURIComponent(schutzQuery.value.trim())}&limit=8`)
  schutzResults.value = r.results || []
}

async function confirmSchutz(movie) {
  try {
    await app.choose(schutzFor.value.id, movie.id)
    schutzFor.value = null
    emit('close')
  } catch (e) { error.value = 'Falscher Film – versuch es nochmal.' }
}

async function create() {
  error.value = ''
  if (!newName.value.trim()) return
  try {
    const u = await api.post('/api/users', { name: newName.value.trim() })
    newName.value = ''
    await app.refreshUsers()
    await app.choose(u.id)
    emit('close')
  } catch (e) { error.value = e.message }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="panel">
      <div class="brand"><span class="logo">screenmates</span></div>
      <h2 v-if="!schutzFor">Wer schaut mit?</h2>

      <template v-if="!schutzFor">
        <div class="users">
          <button v-for="u in app.users" :key="u.id" class="userbtn" @click="pick(u)">
            <span class="dot" :style="{ background: u.color }"></span>
            {{ u.name }}
            <span v-if="u.hat_schutz" class="lock" title="Durch Film geschützt">🔒</span>
          </button>
        </div>
        <div class="create">
          <input v-model="newName" placeholder="Neuer Name …" @keyup.enter="create" />
          <button class="primary" @click="create">Anlegen</button>
        </div>
      </template>

      <template v-else>
        <h2>Film-Passwort für {{ schutzFor.name }}</h2>
        <p class="muted">Klick den Film an, den {{ schutzFor.name }} als Passwort gewählt hat.</p>
        <input v-model="schutzQuery" placeholder="Film suchen …" @input="searchFilm" autofocus />
        <div class="schutzlist">
          <button v-for="m in schutzResults" :key="m.id" class="filmbtn" @click="confirmSchutz(m)">
            {{ m.title }} <span class="muted">{{ m.year }}</span>
          </button>
        </div>
        <button class="ghost" @click="schutzFor = null">Abbrechen</button>
      </template>

      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(5,5,8,0.92); display: flex; align-items: center; justify-content: center; z-index: 50; }
.panel { background: var(--bg-soft); border: 1px solid var(--line); border-radius: 14px; padding: 2rem; width: min(440px, 92vw); }
.brand { text-align: center; margin-bottom: 0.4rem; }
.logo { color: var(--accent); font-weight: 800; letter-spacing: -0.5px; font-size: 1.4rem; }
h2 { text-align: center; font-weight: 600; margin: 0.5rem 0 1.4rem; }
.users { display: flex; flex-wrap: wrap; gap: 0.6rem; justify-content: center; margin-bottom: 1.4rem; }
.userbtn { display: flex; align-items: center; gap: 0.5rem; }
.dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
.lock { font-size: 0.8rem; }
.create { display: flex; gap: 0.5rem; }
.schutzlist { display: flex; flex-direction: column; gap: 0.4rem; margin: 0.8rem 0; max-height: 240px; overflow: auto; }
.filmbtn { text-align: left; }
.error { color: var(--accent); text-align: center; margin-top: 1rem; }
</style>
