<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApp } from './stores/app'
import { useKino } from './stores/kino'
import { useUi } from './stores/ui'
import { navigate, useRoute } from './composables/useRoute'
import Icon from './components/Icon.vue'
import MovieDetail from './components/MovieDetail.vue'
import NamensWahl from './components/NamensWahl.vue'
import Toasts from './components/Toasts.vue'
import UserAvatar from './components/UserAvatar.vue'
import AbendTab from './components/tabs/AbendTab.vue'
import FindenTab from './components/tabs/FindenTab.vue'

const lazy = (loader) => defineAsyncComponent(loader)

// Three places for the three things you come here to do; the rest is secondary.
const PRIMARY = [
  { id: 'abend', label: 'Filmabend', icon: 'abend', comp: AbendTab },
  { id: 'finden', label: 'Finden', icon: 'suche', comp: FindenTab },
  { id: 'sammlung', label: 'Unsere Filme', icon: 'sammlung', comp: lazy(() => import('./components/tabs/SammlungTab.vue')) },
  { id: 'kino', label: 'Kino', icon: 'kino', comp: lazy(() => import('./components/tabs/KinoTab.vue')) },
]
const SECONDARY = [
  { id: 'wuensche', label: 'Wünsche & Ideen', icon: 'wuensche', comp: lazy(() => import('./components/tabs/WuenscheTab.vue')) },
  { id: 'einstellungen', label: 'Einstellungen', icon: 'verwaltung', comp: lazy(() => import('./components/tabs/EinstellungenTab.vue')) },
]
const ALL = [...PRIMARY, ...SECONDARY]

const app = useApp()
const kino = useKino()
// The Kino entry only exists once a media server is configured.
const primary = computed(() => PRIMARY.filter((t) => t.id !== 'kino' || kino.enabled))
const ui = useUi()
const route = useRoute()
const failed = ref(false)

const current = computed(() => ALL.find((t) => t.id === route.value.tab) || PRIMARY[0])
const reload = () => window.location.reload()

// List counts in the navigation follow every change.
watch(() => ui.changes, () => app.refreshStatus())

// Ctrl+Shift+H: straight to host mode, like the original's secret key combo.
function onKey(e) {
  if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'h') {
    e.preventDefault()
    navigate('einstellungen')
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    await app.bootstrap()
    if (!app.me) ui.loginOpen = true
    kino.startPolling()
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

      <nav class="primary-nav" aria-label="Hauptbereiche">
        <a
          v-for="t in primary"
          :key="t.id"
          :href="`#/${t.id}`"
          class="nav"
          :class="{ active: current.id === t.id }"
          :aria-current="current.id === t.id ? 'page' : undefined"
        >
          <Icon :name="t.icon" :size="20" />
          <span>{{ t.label }}</span>
          <span v-if="t.id === 'kino' && kino.live" class="live" :title="`Läuft gerade: ${kino.titel || 'Live'}`">
            <span class="dot"></span>{{ kino.zuschauer.length || 'live' }}
          </span>
        </a>
      </nav>

      <div class="bottom">
        <nav class="secondary-nav" aria-label="Weiteres">
          <a
            v-for="t in SECONDARY"
            :key="t.id"
            :href="`#/${t.id}`"
            class="nav small"
            :class="{ active: current.id === t.id }"
            :aria-current="current.id === t.id ? 'page' : undefined"
          >
            <Icon :name="t.icon" :size="16" />
            <span>{{ t.label }}</span>
          </a>
        </nav>

        <button v-if="app.me" class="me" title="Profil & Einstellungen" @click="navigate('einstellungen')">
          <UserAvatar :user="app.me" />
          <span class="name">{{ app.me.name }}</span>
          <span v-if="app.host" class="host-badge">Host</span>
        </button>
        <button v-else class="primary pick" @click="ui.loginOpen = true">Namen wählen</button>

        <p class="status">
          {{ app.status.movie_count.toLocaleString('de-DE') }} Filme im Katalog
          <span v-if="!app.status.tmdb" class="warn">Demo-Katalog · TMDB nicht verbunden</span>
        </p>
      </div>
    </aside>

    <main class="main">
      <KeepAlive :include="['FindenTab']">
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
.brand { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.03em; text-decoration: none; padding: 0 0.6rem; }
.brand span { color: var(--accent); }
.brand.big { font-size: 2.4rem; animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.55; } }

.shell { display: grid; grid-template-columns: var(--sidebar) minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  border-right: 1px solid var(--line); padding: 1.6rem 1rem 1.2rem;
  display: flex; flex-direction: column; gap: 2rem;
  background: linear-gradient(180deg, #0d0d10, var(--bg));
}
nav { display: flex; flex-direction: column; gap: 4px; }
.nav {
  display: flex; align-items: center; gap: 0.85rem; padding: 0.7rem 0.8rem; border-radius: 9px;
  color: var(--muted); text-decoration: none; font-size: 1rem; position: relative;
}
.nav:hover { background: var(--bg-soft); color: var(--text); }
.nav.active { background: var(--bg-soft); color: var(--text); font-weight: 600; }
.nav.active::before { content: ''; position: absolute; left: 0; top: 9px; bottom: 9px; width: 3px; border-radius: 3px; background: var(--accent); }
.nav.active svg { color: var(--accent); }
.live {
  margin-left: auto; display: inline-flex; align-items: center; gap: 5px;
  font-size: 0.72rem; font-weight: 700; color: #fff; background: var(--accent); padding: 2px 7px; border-radius: 999px;
}
.live .dot { width: 6px; height: 6px; border-radius: 50%; background: #fff; animation: pulse 1.4s ease-in-out infinite; }
.nav.small { font-size: 0.85rem; padding: 0.45rem 0.8rem; gap: 0.7rem; }

.bottom { margin-top: auto; display: flex; flex-direction: column; gap: 0.9rem; }
.secondary-nav { gap: 0; padding-bottom: 0.9rem; border-bottom: 1px solid var(--line); }
.me { justify-content: flex-start; width: 100%; padding: 0.5rem 0.7rem; background: var(--bg-soft); }
.me .name { font-weight: 600; flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.host-badge { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 1px 5px; }
.pick { width: 100%; justify-content: center; }
.status { margin: 0; padding: 0 0.6rem; font-size: 0.74rem; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }
.warn { color: var(--gold); }
.main { padding: 2.2rem clamp(1rem, 3vw, 2.8rem) 4rem; min-width: 0; }

/* Phone: brand and profile on top, the three main areas as tabs below. */
@media (max-width: 860px) {
  /* Header row hugs its content; the page gets the rest of the height. */
  .shell { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .sidebar {
    z-index: 20; height: auto; padding: 0.7rem 1rem 0; gap: 0.4rem;
    display: grid; grid-template-columns: 1fr auto; align-items: center;
    border-right: none; border-bottom: 1px solid var(--line);
    background: rgba(10, 10, 12, 0.94); backdrop-filter: blur(8px);
  }
  .brand { padding: 0; }
  .bottom { margin: 0; grid-column: 2; grid-row: 1; }
  .secondary-nav, .status { display: none; }
  .me, .pick { width: auto; }
  .primary-nav { grid-column: 1 / -1; flex-direction: row; justify-content: space-around; }
  /* Bottom-tab style: icon above label, so four areas fit a phone. */
  .nav { flex: 1; flex-direction: column; justify-content: center; padding: 0.5rem 0.2rem 0.6rem; font-size: 0.72rem; gap: 0.2rem; white-space: nowrap; }
  .live { position: absolute; top: 2px; left: calc(50% + 6px); margin: 0; padding: 0 5px; font-size: 0.62rem; }
  .nav.active { background: none; }
  .nav.active::before { left: 12px; right: 12px; top: auto; bottom: 0; width: auto; height: 3px; }
  .main { padding-top: 1.4rem; }
}
</style>
