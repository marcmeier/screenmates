<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useApp } from './stores/app'
import { useKino } from './stores/kino'
import { useUi } from './stores/ui'
import { navigate, useRoute } from './composables/useRoute'
import Icon from './components/Icon.vue'
import MovieDetail from './components/MovieDetail.vue'
import NamensWahl from './components/NamensWahl.vue'
import Toasts from './components/Toasts.vue'
import UserAvatar from './components/UserAvatar.vue'
import Zugang from './components/Zugang.vue'
import ErfolgPopup from './components/ErfolgPopup.vue'
import GemeinsameKiste from './components/GemeinsameKiste.vue'
import Statistiken from './components/Statistiken.vue'
import StabWechsel from './components/StabWechsel.vue'
import Glocke from './components/Glocke.vue'
import { anwenden } from './design'
import { useLive } from './stores/live'
import { useErfolge } from './stores/erfolge'
import { debounce } from './format'
import { api, beiAenderung } from './api'
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
  { id: 'profil', label: 'Profil & Erfolge', icon: 'profil', comp: lazy(() => import('./components/tabs/ProfilTab.vue')) },
  { id: 'wuensche', label: 'Wünsche & Ideen', icon: 'wuensche', comp: lazy(() => import('./components/tabs/WuenscheTab.vue')) },
  // Only for (group) admins: kept apart from everyone's own profile.
  { id: 'verwaltung', label: 'Verwaltung', icon: 'verwaltung', comp: lazy(() => import('./components/tabs/VerwaltungTab.vue')) },
]
// Not in the navigation: linked from the sidebar's footer and the profile menu.
const VERSTECKT = [{ id: 'ueber', label: 'Über', icon: 'info', comp: lazy(() => import('./components/tabs/UeberTab.vue')) }]
const ALL = [...PRIMARY, ...SECONDARY, ...VERSTECKT]

const app = useApp()
// Your theme and font follow you from device to device.
watch(() => app.me?.design, (d) => d && anwenden(d), { deep: true })
const kino = useKino()
// The Kino entry only exists once a media server is configured.
const primary = computed(() => PRIMARY.filter((t) => t.id !== 'kino' || kino.enabled))
const secondary = computed(() => SECONDARY.filter((t) => t.id !== 'verwaltung' || app.verwaltetGruppen))
const ui = useUi()
const route = useRoute()
const failed = ref(false)

const current = computed(() => ALL.find((t) => t.id === route.value.tab) || PRIMARY[0])
// Movie-night areas need a group; the rest of the app works without one.
const ohneGruppe = computed(() => (!app.me || !app.gruppe) && ['abend', 'sammlung', 'kino'].includes(current.value.id))

// Icon-only sidebar, remembered per device. Phones keep their own top bar.
const LEISTE = 'screenmates.leiste'
function gemerkt() {
  try {
    return localStorage.getItem(LEISTE) === 'schmal'
  } catch {
    return false
  }
}
const schmal = ref(gemerkt())
watch(schmal, (v) => {
  try {
    localStorage.setItem(LEISTE, v ? 'schmal' : 'breit')
  } catch {
    /* private mode */
  }
})
const breitQuery = window.matchMedia('(min-width: 861px)')
const breit = ref(breitQuery.matches)
breitQuery.addEventListener('change', (e) => (breit.value = e.matches))
const eingeklappt = computed(() => schmal.value && breit.value)
const reload = () => window.location.reload()
// Phones hide the secondary navigation: there the profile button opens a menu instead.
const menue = ref(false)
function profilKlick() {
  if (breit.value) navigate('profil')
  else menue.value = !menue.value
}
watch(() => route.value.tab, () => (menue.value = false))
const kuerzel = (name) => name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()

// Someone new (name younger than two weeks) gets a short welcome – once, on whichever device.
const Willkommen = lazy(() => import('./components/Willkommen.vue'))
const willkommen = computed(
  () => !!app.me && !app.me.design?.willkommen && Date.now() - new Date(app.me.created_at).getTime() < 14 * 864e5,
)
async function willkommenFertig() {
  // Closed once the server knows – a reload right after must not bring it back.
  try {
    await api.post('/api/users/me/willkommen', undefined, { quiet: true })
  } finally {
    app.me.design = { ...(app.me.design || {}), willkommen: true }
  }
}

// List counts in the navigation follow every change; achievements are checked after every write.
const erfolge = useErfolge()
const erfolgeCheck = debounce(() => erfolge.pruefen(), 1200)
beiAenderung(erfolgeCheck)
watch(() => ui.changes, () => app.refreshStatus())
watch(() => app.me?.id, (id) => id && erfolgeCheck())

// #/einladung/<code>: come in, or (with a name) join that group.
async function einladung() {
  if (route.value.tab !== 'einladung' || !route.value.sub) return
  const token = route.value.sub
  history.replaceState(null, '', '#/abend')
  route.value = { tab: 'abend', sub: null, id: null }
  try {
    await app.refreshZugang()
    if (app.me) {
      const r = await app.annehmen(token)
      if (r.status === 'aufgenommen') {
        ui.toast(`Willkommen in „${r.gruppe}“!`, 'ok')
        await app.wechseln(r.gruppe_id)
      } else if (r.status === 'angefragt') ui.toast(`Anfrage an „${r.gruppe}“ gestellt – ein Admin der Gruppe entscheidet.`, 'ok', 6000)
      else ui.toast(`Du bist schon in „${r.gruppe}“.`)
      return
    }
    await app.einlassen(token)
  } catch (e) {
    app.einladungFehler = e.message
  }
}

async function start() {
  try {
    await einladung()
    await app.bootstrap()
    if (app.draussen) return
    if (!app.me) ui.loginOpen = true
    kino.startPolling()
    useLive().starten()
  } catch {
    failed.value = true
  }
}
onMounted(start)
// A link opened while the app is already open (only the part after # changes).
watch(
  () => route.value.tab,
  async (tab) => {
    if (tab !== 'einladung') return
    await einladung()
    await app.bootstrap()
    if (!app.draussen && !app.me) ui.loginOpen = true
  },
)
// Through the door: now the app itself starts.
watch(
  () => app.draussen,
  (draussen, vorher) => vorher && !draussen && start(),
)
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

  <Zugang v-else-if="app.draussen" />

  <div v-else class="shell" :class="{ schmal: eingeklappt }">
    <aside class="sidebar">
      <a href="#/abend" class="brand" aria-label="screenmates – zum Filmabend">
        <template v-if="eingeklappt">s<span>m</span></template>
        <template v-else>screen<span>mates</span></template>
      </a>

      <div v-if="app.gruppe" class="gruppenwahl">
        <button v-if="eingeklappt" class="kurz" :title="`Gruppe: ${app.gruppe.name}`" @click="schmal = false">
          {{ kuerzel(app.gruppe.name) }}<span class="sr-only">Gruppe: {{ app.gruppe.name }}</span>
        </button>
        <select v-else-if="app.gruppen.length > 1" :value="app.gruppe.id" aria-label="Gruppe wechseln" @change="app.wechseln(Number($event.target.value))">
          <option v-for="g in app.gruppen" :key="g.id" :value="g.id">{{ g.name }}</option>
        </select>
        <span v-else class="muted name">{{ app.gruppe.name }}</span>
      </div>

      <nav class="primary-nav" aria-label="Hauptbereiche">
        <a
          v-for="t in primary"
          :key="t.id"
          :href="`#/${t.id}`"
          class="nav"
          :class="{ active: current.id === t.id }"
          :aria-current="current.id === t.id ? 'page' : undefined"
          :title="eingeklappt ? t.label : undefined"
        >
          <Icon :name="t.icon" :size="20" />
          <span :class="{ 'sr-only': eingeklappt }">{{ t.label }}</span>
          <span v-if="t.id === 'kino' && kino.live" class="live" :title="`Läuft gerade: ${kino.titel || 'Live'}`">
            <span class="dot"></span>{{ kino.zuschauer.length || 'live' }}
          </span>
        </a>
      </nav>

      <div class="bottom">
        <nav class="secondary-nav" aria-label="Weiteres">
          <a
            v-for="t in secondary"
            :key="t.id"
            :href="`#/${t.id}`"
            class="nav small"
            :class="{ active: current.id === t.id }"
            :aria-current="current.id === t.id ? 'page' : undefined"
            :title="eingeklappt ? t.label : undefined"
          >
            <Icon :name="t.icon" :size="16" />
            <span :class="{ 'sr-only': eingeklappt }">{{ t.label }}</span>
            <span v-if="t.id === 'verwaltung' && app.antraege" class="antraege" aria-hidden="true" :title="`${app.antraege} offene Anträge`">{{ app.antraege }}</span>
          </a>
          <button
            class="nav small collapse"
            :aria-expanded="!eingeklappt"
            :title="eingeklappt ? 'Leiste ausklappen' : undefined"
            @click="schmal = !schmal"
          >
            <Icon name="pfeil" :size="16" :class="{ gedreht: eingeklappt }" />
            <span :class="{ 'sr-only': eingeklappt }">{{ eingeklappt ? 'Leiste ausklappen' : 'Leiste einklappen' }}</span>
          </button>
        </nav>

        <Glocke v-if="app.me" :schmal="eingeklappt" />
        <button v-if="app.me" class="me" :class="{ admin: app.admin }" :aria-expanded="breit ? undefined : menue" :title="eingeklappt ? `${app.me.name}${app.admin ? ' (Admin)' : ''} – Profil` : 'Profil & Erfolge'" @click="profilKlick">
          <UserAvatar :user="app.me" />
          <span class="name" :class="{ 'sr-only': eingeklappt }">{{ app.me.name }}</span>
          <span v-if="app.admin && !eingeklappt" class="admin-badge">Admin</span>
        </button>
        <div v-if="menue && !breit" class="menue panel" role="menu" @click="menue = false">
          <a href="#/profil" role="menuitem" class="eintrag">
            <Icon name="pokal" :size="18" /> Profil & Erfolge <span v-if="app.me?.level" class="muted">Level {{ app.me.level }}</span>
          </a>
          <a href="#/profil/einstellungen" role="menuitem" class="eintrag"><Icon name="profil" :size="18" /> Einstellungen</a>
          <a href="#/wuensche" role="menuitem" class="eintrag"><Icon name="wuensche" :size="18" /> Wünsche & Ideen</a>
          <a v-if="app.verwaltetGruppen" href="#/verwaltung" role="menuitem" class="eintrag">
            <Icon name="verwaltung" :size="18" /> Verwaltung
            <span v-if="app.antraege" class="antraege">{{ app.antraege }}</span>
          </a>
          <a href="#/ueber" role="menuitem" class="eintrag"><Icon name="info" :size="18" /> Über · Impressum</a>
          <button role="menuitem" class="eintrag ghost" @click="app.logout()"><Icon name="logout" :size="18" /> Abmelden</button>
        </div>
        <button v-if="!app.me" class="primary pick" :title="eingeklappt ? 'Namen wählen' : undefined" @click="ui.loginOpen = true">
          <template v-if="eingeklappt"><Icon name="plus" :size="16" /><span class="sr-only">Namen wählen</span></template>
          <template v-else>Namen wählen</template>
        </button>

        <div class="status" :class="{ leer: eingeklappt }" :aria-hidden="eingeklappt">
          <Statistiken v-if="!eingeklappt" />
        </div>
      </div>
    </aside>

    <main class="main">
      <div v-if="ohneGruppe" class="empty keine-gruppe">
        <template v-if="!app.me">
          <strong>Erst Namen wählen</strong>
          <p class="muted">Filmabend, Chronik und Kino gehören deiner Gruppe – wähl deinen Namen, dann geht’s los.</p>
          <button class="primary" @click="ui.loginOpen = true">Namen wählen</button>
        </template>
        <template v-else>
          <strong>Du bist noch in keiner Gruppe</strong>
          <p class="muted">Filmabende, die Chronik und das Kino gehören einer Gruppe. Sobald dich ein Admin aufnimmt, geht’s hier los. Finden, Erfolge und Wünsche gehen schon jetzt.</p>
        </template>
      </div>
      <KeepAlive v-else :include="['FindenTab']">
        <component :is="current.comp" :key="current.id" />
      </KeepAlive>
    </main>
  </div>

  <NamensWahl v-if="ui.loginOpen && !app.draussen" />
  <Willkommen v-if="willkommen && !ui.loginOpen && !app.draussen" @fertig="willkommenFertig" />
  <ErfolgPopup v-if="!app.draussen" />
  <GemeinsameKiste v-if="!app.draussen" />
  <StabWechsel v-if="!app.draussen" />
  <MovieDetail v-if="ui.detail" />
  <Toasts />
</template>

<style scoped>
.splash { min-height: 100vh; display: grid; place-content: center; justify-items: center; gap: 1rem; color: var(--muted); }
.brand { font-size: 1.55rem; font-weight: 800; letter-spacing: -0.03em; text-decoration: none; padding: 0 0.6rem; line-height: 36px; height: 36px; white-space: nowrap; }
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
  display: flex; align-items: center; gap: 0.85rem; padding: 0 0.8rem; border-radius: 9px; height: 46px;
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
.collapse { width: 100%; border: none; background: none; text-align: left; font: inherit; cursor: pointer; }
.collapse svg { transition: transform 0.2s; }
.collapse .gedreht { transform: rotate(180deg); }

/* Icon-only sidebar (desktop) */
.shell.schmal { grid-template-columns: 72px minmax(0, 1fr); }
/* Folding only changes widths: every row keeps its height, so nothing jumps. */
.schmal .sidebar { padding: 1.6rem 0.6rem 1.2rem; align-items: stretch; }
.schmal .brand { padding: 0; text-align: center; }
.schmal .nav { justify-content: center; padding: 0; gap: 0; }
.schmal .nav.small { padding: 0; }
.schmal .live { position: absolute; top: 3px; right: 6px; margin: 0; padding: 0 5px; font-size: 0.62rem; }
.schmal .live .dot { display: none; }
.schmal .antraege { position: absolute; top: 0; right: 10px; }
.schmal .me { justify-content: center; padding: 0 0; }
.schmal .me.admin :deep(.avatar) { box-shadow: 0 0 0 2px var(--bg-soft), 0 0 0 4px var(--accent); }
.schmal .pick { padding: 0; }
.nav.small { font-size: 0.85rem; padding: 0 0.8rem; gap: 0.7rem; height: 34px; }
.antraege { margin-left: auto; font-size: 0.68rem; font-weight: 700; color: #fff; background: var(--accent); border-radius: 999px; padding: 0 6px; }

.bottom { margin-top: auto; display: flex; flex-direction: column; gap: 0.9rem; }
.secondary-nav { gap: 0; padding-bottom: 0.9rem; border-bottom: 1px solid var(--line); }
.me { justify-content: flex-start; width: 100%; padding: 0 0.7rem; height: 44px; background: var(--bg-soft); }
.me .name { font-weight: 600; flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-badge { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); border: 1px solid var(--accent); border-radius: 4px; padding: 1px 5px; }
.pick { width: 100%; justify-content: center; height: 44px; }
.gruppenwahl { margin-top: -1.2rem; padding: 0 0.6rem; font-size: 0.82rem; height: 32px; display: flex; align-items: center; }
.gruppenwahl select { width: 100%; height: 32px; padding: 0 0.5rem; font-size: 0.82rem; }
.gruppenwahl .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.schmal .gruppenwahl { padding: 0; justify-content: center; }
.gruppenwahl .kurz {
  height: 32px; min-width: 40px; padding: 0 6px; border-radius: 8px; font-size: 0.72rem; font-weight: 700;
  letter-spacing: 0.04em; color: var(--muted); background: var(--bg-soft); border: 1px solid var(--line);
}
.keine-gruppe { max-width: 560px; }
.menue { display: none; }
/* Fixed height: the folded bar keeps an empty block here, so the profile button doesn't move. */
.status { margin: 0; padding: 0 0.6rem; font-size: 0.74rem; line-height: 1.35; color: var(--muted); display: flex; flex-direction: column; gap: 2px; height: 4.6rem; overflow: hidden; }
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
  .secondary-nav, .status, .collapse { display: none; }
  /* Phones stack icon and label: their own heights. */
  .nav, .me, .pick { height: auto; }
  .bottom { position: relative; flex-direction: row; align-items: center; gap: 0.3rem; }
  .sidebar { overflow: visible; } /* the profile menu hangs below the header */
  .menue {
    display: flex; flex-direction: column; position: absolute; right: 0; top: calc(100% + 6px); z-index: 30;
    min-width: 220px; padding: 0.4rem; gap: 2px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
  }
  .eintrag {
    display: flex; align-items: center; gap: 0.7rem; padding: 0.7rem 0.8rem; border-radius: 8px; width: 100%;
    color: var(--text); text-decoration: none; font-size: 0.95rem; border: none; background: none; justify-content: flex-start;
  }
  .eintrag:hover { background: var(--bg-raised); }
  .eintrag .muted { margin-left: auto; font-size: 0.8rem; }
  .eintrag .antraege { margin-left: auto; }
  .gruppenwahl { grid-column: 1 / -1; margin: 0; padding: 0; }
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
