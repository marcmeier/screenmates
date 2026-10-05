<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useGastgeber } from '../../stores/gastgeber'
import GastgeberLeiste from '../GastgeberLeiste.vue'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import Icon from '../Icon.vue'
import UserAvatar from '../UserAvatar.vue'
import KinoChat from '../kino/KinoChat.vue'
import KinoPlayer from '../kino/KinoPlayer.vue'
import KinoSenden from '../kino/KinoSenden.vue'
import { useKinoChat } from '../../stores/kinochat'

const app = useApp()
// Sending is for whoever holds the host's baton (and the group's admins).
const gast = useGastgeber()
const kino = useKino()
const ui = useUi()

// Poll faster while the Kino is open, so going live shows up within seconds.
// The chat runs only while this page is open.
const chat = useKinoChat()
onMounted(() => {
  kino.startPolling(3000)
  if (app.me && app.gruppe) chat.starten()
})
onBeforeUnmount(() => {
  kino.startPolling()
  chat.stoppen()
})

// Someone who joined after this page loaded the user list: fetch names once.
watch(
  () => kino.zuschauer,
  (ids) => ids.some((id) => !app.userById(id)) && app.refreshUsers(),
)

const vorbei = computed(() => !kino.live && gast.darfModerieren && kino.movie && kino.publikum.length > 0)

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
    <GastgeberLeiste v-if="kino.enabled" class="panel stableiste" />

    <div v-if="!kino.enabled" class="notice">
      Das Kino ist noch nicht eingerichtet. Es braucht den Medienserver MediaMTX neben screenmates
      (bei <code>docker compose up</code> ist er dabei) und <code>MEDIAMTX_WEBRTC_URL</code> in <code>backend/.env</code>.
      Details stehen in der README unter „Kino“.
    </div>

    <div v-else class="layout" :class="{ withDesk: gast.darfModerieren, mitChat: app.me }">
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
            {{ gast.darfModerieren ? 'Starte rechts eine Übertragung.' : 'Sobald jemand sendet, erscheint das Bild hier von selbst.' }}
          </p>
        </div>

        <div v-if="vorbei" class="panel done">
          <span>Vorstellung vorbei – <strong>{{ kino.movie.title }}</strong> als gesehen eintragen?</span>
          <span class="spacer"></span>
          <span class="avatars"><UserAvatar v-for="id in kino.publikum" :key="id" :user-id="id" /></span>
          <button class="primary small" @click="alsGesehen"><Icon name="gesehen" :size="14" /> Eintragen</button>
        </div>
      </section>

      <div v-if="gast.darfModerieren || app.me" class="seite">
        <KinoSenden v-if="gast.darfModerieren" />
        <KinoChat v-if="app.me" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.stableiste { margin-bottom: 1rem; padding: 0.6rem 0.9rem; }
.layout { display: grid; gap: 1.6rem; align-items: start; }
.layout.withDesk, .layout.mitChat { grid-template-columns: minmax(0, 1fr) 360px; }
.seite { display: flex; flex-direction: column; gap: 1.2rem; min-width: 0; position: sticky; top: 1rem; }
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
.screen { aspect-ratio: 16 / 9; width: var(--kino-breite); border-radius: var(--radius); border: 1px solid var(--line); }
.empty-screen {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.3rem; text-align: center;
  background: radial-gradient(80% 80% at 50% 40%, #16161c, #08080a); color: var(--muted); padding: 1rem;
}
.empty-screen p { margin: 0; }
.empty-screen strong { color: var(--text); font-size: 1.1rem; }
.movie { align-self: flex-start; }
.done { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
@media (max-width: 1100px) {
  .layout.withDesk, .layout.mitChat { grid-template-columns: 1fr; }
  .seite { position: static; }
}
</style>
