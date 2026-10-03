<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { useApp } from '../store'

const app = useApp()
const entries = ref([])
const noteDraft = ref({})

async function load() { entries.value = (await api.get('/api/watched')).watched || [] }
onMounted(load)

function userName(id) { return app.users.find(u => u.id === id)?.name || '?' }
function stars(n) { return '★'.repeat(n) + '☆'.repeat(5 - n) }

async function rate(entry, n) { await api.post(`/api/watched/${entry.id}/rating`, { stars: n }); await load() }
async function addNote(entry) {
  const text = (noteDraft.value[entry.id] || '').trim()
  if (!text) return
  await api.post(`/api/watched/${entry.id}/notes`, { text })
  noteDraft.value[entry.id] = ''
  await load()
}
async function remove(entry) {
  if (!confirm(`„${entry.movie?.title}" aus der Watched-Liste löschen?`)) return
  await api.del(`/api/watched/${entry.id}`); await load()
}
</script>

<template>
  <div>
    <h1>Gesehen</h1>
    <p v-if="!entries.length" class="muted">Noch keine Filme als gesehen markiert.</p>
    <div class="list">
      <div v-for="e in entries" :key="e.id" class="entry">
        <div class="poster" :class="{ ph: !e.movie?.poster_url }">
          <img v-if="e.movie?.poster_url" :src="e.movie.poster_url" />
          <span v-else>{{ e.movie?.title }}</span>
        </div>
        <div class="body">
          <div class="head">
            <h3>{{ e.movie?.title }} <span class="muted year">{{ e.movie?.year }}</span></h3>
            <button class="ghost small" @click="remove(e)">Löschen</button>
          </div>
          <div class="ratingrow">
            <span class="stars big" v-if="e.rating_avg">{{ e.rating_avg }} ⌀</span>
            <span class="muted" style="font-size:.8rem">Deine Wertung:</span>
            <span class="pick">
              <button v-for="n in 5" :key="n" class="starbtn" @click="rate(e, n)" :disabled="!app.me" :title="app.me ? '' : 'Erst Namen wählen'">★</button>
            </span>
          </div>
          <div class="notes">
            <div v-for="n in e.notes" :key="n.id" class="note">
              <b :style="{ color: app.users.find(u=>u.id===n.user_id)?.color }">{{ userName(n.user_id) }}</b>
              <span>{{ n.text }}</span>
              <span class="muted hearts" v-if="n.hearts.length">♥ {{ n.hearts.length }}</span>
            </div>
            <div class="noteadd" v-if="app.me">
              <input v-model="noteDraft[e.id]" placeholder="Gästebuch …" @keyup.enter="addNote(e)" />
              <button class="ghost small" @click="addNote(e)">Senden</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.list { display: flex; flex-direction: column; gap: 1rem; }
.entry { display: grid; grid-template-columns: 92px 1fr; gap: 1rem; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.9rem; }
.poster { aspect-ratio: 2/3; border-radius: 8px; overflow: hidden; background: #1b1b22; display: flex; align-items: center; justify-content: center; text-align: center; font-size: .72rem; padding: 4px; }
.poster img { width: 100%; height: 100%; object-fit: cover; }
.head { display: flex; justify-content: space-between; align-items: center; }
.head h3 { margin: 0; font-size: 1.05rem; }
.year { font-weight: 400; font-size: .85rem; }
.small { padding: 0.3rem 0.6rem; font-size: 0.78rem; }
.ratingrow { display: flex; align-items: center; gap: 0.6rem; margin: 0.5rem 0; }
.stars.big { color: #f5a623; font-weight: 700; }
.starbtn { border: none; background: none; color: #555; font-size: 1.1rem; padding: 0 1px; }
.starbtn:hover, .starbtn:hover ~ .starbtn { color: #f5a623; }
.pick { display: inline-flex; flex-direction: row-reverse; }
.pick .starbtn:hover, .pick .starbtn:hover ~ .starbtn { color: #f5a623; }
.notes { display: flex; flex-direction: column; gap: 4px; margin-top: 0.4rem; }
.note { font-size: 0.85rem; display: flex; gap: 0.5rem; }
.hearts { margin-left: auto; }
.noteadd { display: flex; gap: 0.5rem; margin-top: 0.3rem; }
</style>
