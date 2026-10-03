<script setup>
import { ref, onMounted, shallowRef } from 'vue'
import { useApp } from './store'
import SearchTab from './components/SearchTab.vue'
import DiscoverTab from './components/DiscoverTab.vue'
import MerklisteTab from './components/MerklisteTab.vue'
import WatchedTab from './components/WatchedTab.vue'
import WuenscheTab from './components/WuenscheTab.vue'
import InfoTab from './components/InfoTab.vue'
import NamensWahl from './components/NamensWahl.vue'
import MovieDetail from './components/MovieDetail.vue'

const app = useApp()
const tab = ref('discover')
const showLogin = ref(false)
const detail = shallowRef(null)

const TABS = [
  { id: 'discover', label: 'Entdecken', comp: DiscoverTab },
  { id: 'search', label: 'Suche', comp: SearchTab },
  { id: 'merkliste', label: 'Merkliste', comp: MerklisteTab },
  { id: 'watched', label: 'Gesehen', comp: WatchedTab },
  { id: 'wuensche', label: 'Wünsche', comp: WuenscheTab },
  { id: 'info', label: 'Info', comp: InfoTab },
]

onMounted(() => app.bootstrap())
function current() { return TABS.find(t => t.id === tab.value)?.comp }
</script>

<template>
  <div class="shell" v-if="app.ready">
    <aside class="sidebar">
      <div class="brand">screen<span>mates</span></div>

      <div class="who" v-if="app.me">
        <span class="dot" :style="{ background: app.me.color }"></span>
        <span>{{ app.me.name }}</span>
        <button class="ghost tiny" @click="app.logout()">wechseln</button>
      </div>
      <button v-else class="primary pickbtn" @click="showLogin = true">Namen wählen</button>

      <nav>
        <button v-for="t in TABS" :key="t.id" class="navbtn" :class="{ active: tab === t.id }" @click="tab = t.id">
          {{ t.label }}
        </button>
      </nav>

      <div class="status muted">
        <div>{{ app.status.movie_count }} Filme im Katalog</div>
        <div v-if="!app.status.tmdb" class="warn">⚠︎ TMDB nicht konfiguriert – Seed-Daten</div>
      </div>
    </aside>

    <main class="main">
      <component :is="current()" @open="detail = $event" />
    </main>

    <NamensWahl v-if="showLogin || (!app.me && !app.users.length)" @close="showLogin = false" />
    <MovieDetail v-if="detail" :movie="detail" @close="detail = null" />
  </div>
  <div v-else class="loading">Lade screenmates …</div>
</template>

<style scoped>
.shell { display: grid; grid-template-columns: var(--sidebar) 1fr; min-height: 100vh; }
.sidebar { border-right: 1px solid var(--line); padding: 1.4rem 1.2rem; display: flex; flex-direction: column; gap: 1.4rem; position: sticky; top: 0; height: 100vh; }
.brand { font-size: 1.5rem; font-weight: 800; letter-spacing: -0.5px; }
.brand span { color: var(--accent); }
.who { display: flex; align-items: center; gap: 0.5rem; font-weight: 600; }
.dot { width: 12px; height: 12px; border-radius: 50%; }
.tiny { padding: 0.2rem 0.5rem; font-size: 0.72rem; margin-left: auto; }
.pickbtn { width: 100%; }
nav { display: flex; flex-direction: column; gap: 0.3rem; }
.navbtn { text-align: left; border: none; background: transparent; padding: 0.6rem 0.8rem; border-radius: 8px; font-size: 0.95rem; color: var(--muted); }
.navbtn:hover { background: var(--bg-soft); color: var(--text); }
.navbtn.active { background: var(--bg-soft); color: var(--text); border-left: 3px solid var(--accent); }
.status { margin-top: auto; font-size: 0.78rem; line-height: 1.6; }
.warn { color: #f5a623; }
.main { padding: 2rem 2.4rem; overflow: auto; }
.loading { display: flex; align-items: center; justify-content: center; height: 100vh; color: var(--muted); }
@media (max-width: 720px) {
  .shell { grid-template-columns: 1fr; }
  .sidebar { position: static; height: auto; flex-direction: column; }
}
</style>
