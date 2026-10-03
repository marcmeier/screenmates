<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
import { useApp } from '../store'

const app = useApp()
const features = ref([])
const draft = ref('')

async function load() { features.value = (await api.get('/api/features')).features || [] }
onMounted(load)

async function add() {
  if (!draft.value.trim()) return
  await api.post('/api/features', { text: draft.value.trim() })
  draft.value = ''; await load()
}
async function vote(f) { await api.post(`/api/features/${f.id}/vote`); await load() }
async function toggleDone(f) { await api.patch(`/api/features/${f.id}/done`, { done: !f.done }); await load() }
async function remove(f) { if (confirm('Wunsch löschen?')) { await api.del(`/api/features/${f.id}`); await load() } }
</script>

<template>
  <div>
    <h1>Wünsche</h1>
    <div class="add" v-if="app.me">
      <input v-model="draft" placeholder="Neuer Wunsch / Feature-Idee …" @keyup.enter="add" />
      <button class="primary" @click="add">Hinzufügen</button>
    </div>
    <p v-else class="muted">Wähle links einen Namen, um Wünsche zu erstellen und abzustimmen.</p>

    <div class="list">
      <div v-for="f in features" :key="f.id" class="wish" :class="{ done: f.done }">
        <button class="vote" :class="{ active: f.voted }" @click="vote(f)" :disabled="!app.me">
          ▲<span>{{ f.votes }}</span>
        </button>
        <div class="text">
          <div>{{ f.text }}</div>
          <div class="meta muted" v-if="f.notes.length">{{ f.notes.length }} Anmerkung(en)</div>
        </div>
        <div class="actions">
          <button class="ghost small" @click="toggleDone(f)">{{ f.done ? '↩︎' : '✓' }}</button>
          <button class="ghost small" @click="remove(f)">✕</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.add { display: flex; gap: 0.6rem; margin-bottom: 1.4rem; max-width: 620px; }
.list { display: flex; flex-direction: column; gap: 0.6rem; }
.wish { display: flex; align-items: center; gap: 0.9rem; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.7rem 0.9rem; }
.wish.done { opacity: 0.5; }
.wish.done .text { text-decoration: line-through; }
.vote { display: flex; flex-direction: column; align-items: center; min-width: 48px; line-height: 1.1; }
.vote.active { border-color: var(--accent); color: var(--accent); }
.vote span { font-size: 0.8rem; font-weight: 700; }
.text { flex: 1; }
.meta { font-size: 0.75rem; }
.actions { display: flex; gap: 0.4rem; }
.small { padding: 0.3rem 0.55rem; font-size: 0.8rem; }
</style>
