<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import Icon from '../Icon.vue'
import UserAvatar from '../UserAvatar.vue'
import KinoPlayer from '../kino/KinoPlayer.vue'
import KinoSenden from '../kino/KinoSenden.vue'

const app = useApp()
const kino = useKino()
const ui = useUi()

// Poll faster while the Kino is open, so going live shows up within seconds.
onMounted(() => kino.startPolling(3000))
onBeforeUnmount(() => kino.startPolling())

// Someone who joined after this page loaded the user list: fetch names once.
watch(
  () => kino.zuschauer,
  (ids) => ids.some((id) => !app.userById(id)) && app.refreshUsers(),
)

const vorbei = computed(() => !kino.live && app.admin && kino.movie && kino.publikum.length > 0)

async function alsGesehen() {
  const entry = await api.post('/api/watched', { movie_id: kino.movie.id })
  await api.post(`/api/watched/${entry.id}/dabei`, { user_ids: kino.publikum })
  ui.toast(`„${kino.movie.title}“ eingetragen – mit ${kino.publikum.length} Zuschauenden`, 'ok')
  await api.post('/api/kino/programm', { titel: '', movie_id: null })
  ui.changed()
  await kino.refresh()
}
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Kino</h1>
        <p>Gemeinsam schauen, egal wo ihr sitzt – alle sehen dasselbe Bild zur selben Zeit.</p>
      </div>
    </header>

    <div v-if="!kino.enabled" class="notice">
      Das Kino ist noch nicht eingerichtet. Es braucht den Medienserver MediaMTX neben screenmates
      (bei <code>docker compose up</code> ist er dabei) und <code>MEDIAMTX_WEBRTC_URL</code> in <code>backend/.env</code>.
      Details stehen in der README unter „Kino“.
    </div>

    <div v-else class="layout" :class="{ withDesk: app.admin }">
      <section class="stage">
        <div v-if="kino.live" class="row onair">
          <span class="badge"><span class="dot"></span>LIVE</span>
          <h2>{{ kino.titel || 'Ohne Titel' }}</h2>
          <span v-if="kino.seit" class="muted since">seit {{ vorWann(kino.seit).replace('vor ', '') }}</span>
          <span class="spacer"></span>
          <span v-if="kino.zuschauer.length" class="viewers" :title="kino.zuschauer.map((id) => app.userById(id)?.name).join(', ')">
            <span class="avatars"><UserAvatar v-for="id in kino.zuschauer" :key="id" :user-id="id" /></span>
            {{ kino.zuschauer.length }} {{ kino.zuschauer.length === 1 ? 'schaut' : 'schauen' }}
          </span>
        </div>

        <template v-if="kino.live || kino.sende">
          <KinoPlayer v-if="app.me" />
          <div v-else class="screen empty-screen">
            <p>Wähl einen Namen, um zuzuschauen.</p>
            <button class="primary" @click="ui.loginOpen = true">Namen wählen</button>
          </div>
          <button v-if="kino.movie" class="ghost small movie" @click="ui.open(kino.movie)">
            <Icon name="info" :size="14" /> Über „{{ kino.movie.title }}“
          </button>
        </template>

        <div v-else class="screen empty-screen">
          <Icon name="kino" :size="44" />
          <p><strong>Gerade läuft nichts.</strong></p>
          <p class="muted">
            {{ app.admin ? 'Starte rechts eine Übertragung.' : 'Sobald jemand sendet, erscheint das Bild hier von selbst.' }}
          </p>
        </div>

        <div v-if="vorbei" class="panel done">
          <span>Vorstellung vorbei – <strong>{{ kino.movie.title }}</strong> als gesehen eintragen?</span>
          <span class="spacer"></span>
          <span class="avatars"><UserAvatar v-for="id in kino.publikum" :key="id" :user-id="id" /></span>
          <button class="primary small" @click="alsGesehen"><Icon name="gesehen" :size="14" /> Eintragen</button>
        </div>
      </section>

      <KinoSenden v-if="app.admin" />
    </div>
  </div>
</template>

<style scoped>
.layout { display: grid; gap: 1.6rem; align-items: start; }
.layout.withDesk { grid-template-columns: minmax(0, 1fr) 360px; }
.stage { display: flex; flex-direction: column; gap: 0.8rem; min-width: 0; }
.onair h2 { margin: 0; font-size: 1.2rem; }
.badge {
  display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff;
  font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; padding: 3px 8px; border-radius: 5px;
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: pulse 1.4s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.since { font-size: 0.85rem; }
.viewers { display: inline-flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--muted); }
.avatars .avatar { width: 24px; height: 24px; font-size: 0.6rem; }
.screen { aspect-ratio: 16 / 9; width: 100%; border-radius: var(--radius); border: 1px solid var(--line); }
.empty-screen {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.3rem; text-align: center;
  background: radial-gradient(80% 80% at 50% 40%, #16161c, #08080a); color: var(--muted); padding: 1rem;
}
.empty-screen p { margin: 0; }
.empty-screen strong { color: var(--text); font-size: 1.1rem; }
.movie { align-self: flex-start; }
.done { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
@media (max-width: 1100px) { .layout.withDesk { grid-template-columns: 1fr; } }
</style>
