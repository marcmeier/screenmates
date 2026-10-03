<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { debounce } from '../format'

// Which streaming services I pay for. Together they make "Läuft bei uns".
const app = useApp()
const ui = useUi()
const alle = ref([])
const gewaehlt = ref(new Set(app.me?.abos ?? []))
const mehr = ref(false)

onMounted(async () => {
  alle.value = (await api.get('/api/anbieter?limit=40')).anbieter
})

const sichtbar = computed(() => (mehr.value ? alle.value : alle.value.slice(0, 16)))

const speichern = debounce(async () => {
  await api.post('/api/abos', { anbieter: [...gewaehlt.value] })
  await app.refreshUsers()
  ui.changed()
  ui.toast('Abos gespeichert', 'ok')
}, 600)

function umschalten(id) {
  const neu = new Set(gewaehlt.value)
  neu.has(id) ? neu.delete(id) : neu.add(id)
  gewaehlt.value = neu
  speichern()
}

// Everyone's subscriptions combined: what the group can watch without paying extra.
const gruppe = computed(() => {
  const bei = new Map()
  for (const u of app.users) for (const id of u.abos ?? []) bei.set(id, [...(bei.get(id) ?? []), u.name])
  return [...bei.entries()].map(([id, namen]) => ({ p: alle.value.find((a) => a.id === id), namen })).filter((x) => x.p)
})
</script>

<template>
  <section class="panel abos">
    <h2>Meine Abos</h2>
    <p class="muted">Wähl deine Streamingdienste. Daraus wird „Läuft bei uns“ beim Suchen und in jeder Filmansicht.</p>
    <ul class="grid-logos" role="group" aria-label="Streamingdienste">
      <li v-for="p in sichtbar" :key="p.id">
        <button :class="{ on: gewaehlt.has(p.id) }" :aria-pressed="gewaehlt.has(p.id)" :title="p.name" @click="umschalten(p.id)">
          <img v-if="p.logo" :src="p.logo" :alt="p.name" loading="lazy" />
          <span v-else>{{ p.name }}</span>
        </button>
      </li>
    </ul>
    <button v-if="alle.length > 16" class="ghost small" @click="mehr = !mehr">{{ mehr ? 'Weniger zeigen' : 'Mehr Dienste zeigen' }}</button>

    <div v-if="gruppe.length" class="gruppe">
      <h3>Die Gruppe hat</h3>
      <ul>
        <li v-for="g in gruppe" :key="g.p.id">
          <img v-if="g.p.logo" :src="g.p.logo" alt="" />
          <span>{{ g.p.name }}</span>
          <span class="muted">{{ g.namen.join(', ') }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; }
h3 { margin: 1.2rem 0 0.5rem; font-size: 0.95rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.grid-logos { list-style: none; padding: 0; margin: 0 0 0.6rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 0.5rem; }
.grid-logos button { width: 52px; height: 52px; padding: 0; border-radius: 11px; overflow: hidden; border: 2px solid transparent; opacity: 0.45; filter: grayscale(0.6); transition: all 0.15s; }
.grid-logos button:hover { opacity: 0.8; }
.grid-logos button.on { opacity: 1; filter: none; border-color: var(--ok); }
.grid-logos img { width: 100%; height: 100%; object-fit: cover; }
.grid-logos span { font-size: 0.55rem; }
.gruppe ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.gruppe li { display: flex; align-items: center; gap: 0.6rem; font-size: 0.88rem; }
.gruppe img { width: 24px; height: 24px; border-radius: 6px; }
</style>
