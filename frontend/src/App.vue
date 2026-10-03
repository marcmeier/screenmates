<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import { useApp } from './stores/app'
import { useUi } from './stores/ui'
import { navigate, useRoute } from './composables/useRoute'
import Icon from './components/Icon.vue'
import MovieDetail from './components/MovieDetail.vue'
import NamensWahl from './components/NamensWahl.vue'
import Toasts from './components/Toasts.vue'
import UserAvatar from './components/UserAvatar.vue'
import AbendTab from './components/tabs/AbendTab.vue'
import EntdeckenTab from './components/tabs/EntdeckenTab.vue'
import SucheTab from './components/tabs/SucheTab.vue'

const lazy = (loader) => defineAsyncComponent(loader)

const TABS = [
  { id: 'abend', label: 'Filmabend', icon: 'abend', comp: AbendTab },
  { id: 'entdecken', label: 'Entdecken', icon: 'entdecken', comp: EntdeckenTab },
  { id: 'suche', label: 'Suche', icon: 'suche', comp: SucheTab },
  { id: 'merkliste', label: 'Merkliste', icon: 'merken', comp: lazy(() => import('./components/tabs/MerklisteTab.vue')) },
  { id: 'gesehen', label: 'Gesehen', icon: 'gesehen', comp: lazy(() => import('./components/tabs/GesehenTab.vue')) },
  { id: 'personen', label: 'Personen', icon: 'personen', comp: lazy(() => import('./components/tabs/PersonenTab.vue')) },
  { id: 'ki', label: 'KI-Suche', icon: 'ki', comp: lazy(() => import('./components/tabs/KiTab.vue')) },
  { id: 'wuensche', label: 'Wünsche', icon: 'wuensche', comp: lazy(() => import('./components/tabs/WuenscheTab.vue')) },
  { id: 'info', label: 'Info', icon: 'info', comp: lazy(() => import('./components/tabs/InfoTab.vue')) },
  { id: 'verwaltung', label: 'Verwaltung', icon: 'verwaltung', comp: lazy(() => import('./components/tabs/VerwaltungTab.vue')) },
]

const app = useApp()
const ui = useUi()
const route = useRoute()
const failed = ref(false)

// Discover and search keep their filters and scroll results when you switch away.
const KEEP = ['EntdeckenTab', 'SucheTab']
const reload = () => window.location.reload()

const current = computed(() => TABS.find((t) => t.id === route.value.tab) || TABS[0])

// Ctrl+Shift+H: straight to host mode, like the original's secret key combo.
function onKey(e) {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'h') {
    e.preventDefault()
    navigate('verwaltung')
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    await app.bootstrap()
    if (!app.me) ui.loginOpen = true
  } catch {
    failed.value = true
  }
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div v-if="failed" class="splash">
    <div class="brand big">screen<span>mates</span></div>
    <p>Der Server ist nicht erreichbar.</p>
    <button @click="reload">Neu laden</button>
  </div>

  <div v-else-if="!app.ready" class="splash" aria-busy="true">
    <div class="brand big">screen<span>mates</span></div>
  </div>

  <div v-else class="shell">
    <aside class="sidebar">
      <a href="#/abend" class="brand">screen<span>mates</span></a>

      <button v-if="app.me" class="me" title="Profil & Verwaltung" @click="navigate('verwaltung')">
        <UserAvatar :user="app.me" />
        <span class="name">{{ app.me.name }}</span>
        <span v-if="app.host" class="host-badge">Host</span>
      </button>
      <button v-else class="primary pick" @click="ui.loginOpen = true">Namen wählen</button>

      <nav aria-label="Bereiche">
        <a
          v-for="t in TABS"
          :key="t.id"
          :href="`#/${t.id}`"
          class="nav"
          :class="{ active: current.id === t.id }"
          :aria-current="current.id === t.id ? 'page' : undefined"
        >
          <Icon :name="t.icon" />
          <span>{{ t.label }}</span>
        </a>
      </nav>

      <footer class="status">
        <span>{{ app.status.movie_count.toLocaleString('de-DE') }} Filme im Katalog</span>
        <span v-if="!app.status.tmdb" class="warn">Demo-Katalog · TMDB nicht verbunden</span>
      </footer>
    </aside>

    <main class="main">
      <KeepAlive :include="KEEP">
        <component :is="current.comp" :key="current.id" />
      </KeepAlive>
    </main>
  </div>

  <NamensWahl v-if="ui.loginOpen" />
  <MovieDetail v-if="ui.detail" />
  <Toasts />
</template>

<style scoped>
.splash { min-height: 100vh; display: grid; place-content: center; justify-items: center; gap: 1rem; color: var(--muted); }
.brand { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.03em; text-decoration: none; }
.brand span { color: var(--accent); }
.brand.big { font-size: 2.4rem; animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.55; } }

.shell { display: grid; grid-template-columns: var(--sidebar) minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  border-right: 1px solid var(--line); padding: 1.5rem 1.1rem;
  display: flex; flex-direction: column; gap: 1.3rem;
  background: linear-gradient(180deg, #0d0d10, var(--bg));
}
.me { justify-content: flex-start; width: 100%; padding: 0.5rem 0.7rem; background: var(--bg-soft); }
.me .name { font-weight: 600; flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.host-badge { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 1px 5px; }
.pick { width: 100%; justify-content: center; }
nav { display: flex; flex-direction: column; gap: 2px; }
.nav {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.8rem; border-radius: 8px;
  color: var(--muted); text-decoration: none; font-size: 0.95rem; position: relative;
}
.nav:hover { background: var(--bg-soft); color: var(--text); }
.nav.active { background: var(--bg-soft); color: var(--text); font-weight: 600; }
.nav.active::before { content: ''; position: absolute; left: 0; top: 8px; bottom: 8px; width: 3px; border-radius: 3px; background: var(--accent); }
.nav.active svg { color: var(--accent); }
.status { margin-top: auto; font-size: 0.76rem; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }
.warn { color: var(--gold); }
.main { padding: 2.2rem clamp(1rem, 3vw, 2.8rem) 4rem; min-width: 0; }

@media (max-width: 860px) {
  .shell { grid-template-columns: 1fr; }
  .sidebar {
    position: sticky; z-index: 20; height: auto; flex-direction: row; flex-wrap: wrap; align-items: center;
    padding: 0.7rem 1rem 0; gap: 0.6rem 1rem; border-right: none; border-bottom: 1px solid var(--line);
    background: rgba(10, 10, 12, 0.94); backdrop-filter: blur(8px);
  }
  .me, .pick { width: auto; margin-left: auto; }
  nav { flex-direction: row; overflow-x: auto; width: 100%; scrollbar-width: none; }
  .nav { white-space: nowrap; padding: 0.55rem 0.7rem; }
  .nav.active::before { left: 8px; right: 8px; top: auto; bottom: 0; width: auto; height: 3px; }
  .status { display: none; }
  .main { padding-top: 1.4rem; }
}
</style>
