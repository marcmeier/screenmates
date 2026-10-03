<script setup>
import { ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { datum, vorWann } from '../../format'
import FilmPicker from '../FilmPicker.vue'
import Icon from '../Icon.vue'
import UserAvatar from '../UserAvatar.vue'

const app = useApp()
const ui = useUi()
const pickSchutz = ref(false)
const pickHostFilm = ref(false)
const hostFilm = ref(null)
const hostError = ref('')
const busy = ref(false)

watch(
  () => app.host,
  async (host) => {
    hostFilm.value = host ? (await api.get('/api/host/film')).movie : null
  },
  { immediate: true },
)

async function setSchutz(movie) {
  await api.post(`/api/users/${app.me.id}/schutz`, { movie_id: movie?.id ?? null })
  pickSchutz.value = false
  await app.refreshUsers()
  ui.toast(movie ? `Dein Name ist jetzt durch „${movie.title}“ geschützt` : 'Schutz entfernt', 'ok')
}

async function unlock(movie) {
  hostError.value = ''
  busy.value = true
  try {
    await app.unlockHost(movie.id)
    ui.toast('Host-Modus aktiv', 'ok')
  } catch (e) {
    hostError.value = e.message
  } finally {
    busy.value = false
  }
}

async function changeHostFilm(movie) {
  await api.post('/api/host/film', { movie_id: movie.id })
  hostFilm.value = movie
  pickHostFilm.value = false
  ui.toast(`Neuer Host-Film: „${movie.title}“`, 'ok')
}

async function sync() {
  busy.value = true
  try {
    const r = await api.post('/api/sync')
    ui.toast(`Katalog aktualisiert: ${r.neu} neue Filme, ${r.gesamt} insgesamt`, 'ok')
    await app.refreshStatus()
    ui.changed()
  } finally {
    busy.value = false
  }
}

async function resetDabei() {
  await api.del('/api/dabei')
  await app.refreshUsers()
  ui.toast('Teilnahme zurückgesetzt')
}

async function removeUser(u) {
  if (!confirm(`„${u.name}“ löschen? Bewertungen und Stimmen gehen verloren, Kommentare bleiben anonym erhalten.`)) return
  await api.del(`/api/users/${u.id}`)
  await app.refreshUsers()
  ui.changed()
}

async function removeSchutz(u) {
  await api.post(`/api/users/${u.id}/schutz`, { movie_id: null })
  await app.refreshUsers()
  ui.toast(`Schutz von ${u.name} entfernt`)
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>Verwaltung</h1>
        <p>Dein Profil, und für den Host alles rund um Katalog und Gruppe.</p>
      </div>
    </header>

    <div v-if="!app.me" class="empty">
      <strong>Erst Namen wählen</strong>
      <button class="primary" style="margin-top: 0.8rem" @click="ui.loginOpen = true">Namen wählen</button>
    </div>

    <template v-else>
      <section class="panel">
        <h2>Profil</h2>
        <div class="row">
          <UserAvatar :user="app.me" />
          <strong>{{ app.me.name }}</strong>
          <span class="spacer"></span>
          <button class="ghost small" @click="app.logout()"><Icon name="logout" :size="14" /> Abmelden</button>
        </div>

        <h3>Film-Schutz</h3>
        <p class="muted">
          Ohne Schutz kann sich jeder als {{ app.me.name }} ausgeben. Mit Schutz muss man beim Anmelden deinen Film anklicken –
          den Film verrät screenmates niemandem, auch dir nicht.
        </p>
        <div class="row">
          <span class="chip" :class="{ ok: app.me.hat_schutz }">
            <Icon name="schloss" :size="13" /> {{ app.me.hat_schutz ? 'geschützt' : 'ungeschützt' }}
          </span>
          <button class="small" @click="pickSchutz = !pickSchutz">{{ app.me.hat_schutz ? 'Film ändern' : 'Schutz einrichten' }}</button>
          <button v-if="app.me.hat_schutz" class="ghost small" @click="setSchutz(null)">Entfernen</button>
        </div>
        <div v-if="pickSchutz" class="picker"><FilmPicker placeholder="Deinen Passwort-Film suchen …" @pick="setSchutz" /></div>
      </section>

      <section class="panel">
        <h2>Host-Modus</h2>
        <template v-if="!app.host">
          <p class="muted">
            {{
              app.hostEingerichtet
                ? 'Klick den Host-Film an, um Host zu werden. Tipp: Strg+Shift+H führt jederzeit hierher.'
                : 'Noch gibt es keinen Host. Wähl einen Host-Film – wer ihn kennt, kann künftig verwalten.'
            }}
          </p>
          <FilmPicker :busy="busy" placeholder="Host-Film suchen …" @pick="unlock" />
          <p v-if="hostError" class="error" role="alert">{{ hostError }}</p>
        </template>
        <template v-else>
          <div class="row">
            <span class="chip ok">aktiv</span>
            <span class="muted">Host-Film: <strong class="secret">{{ hostFilm?.title || '–' }}</strong></span>
            <button class="ghost small" @click="pickHostFilm = !pickHostFilm">Ändern</button>
            <span class="spacer"></span>
            <button class="small" @click="app.lockHost()">Host-Modus beenden</button>
          </div>
          <div v-if="pickHostFilm" class="picker"><FilmPicker placeholder="Neuen Host-Film suchen …" @pick="changeHostFilm" /></div>
        </template>
      </section>

      <template v-if="app.host">
        <section class="panel">
          <h2>Katalog</h2>
          <p class="muted">
            {{ app.status.movie_count }} Filme, davon {{ app.status.canon_count }} im Horror-Kanon.
            <template v-if="app.status.last_sync">Letzter Abgleich {{ vorWann(app.status.last_sync) }}.</template>
          </p>
          <button v-if="app.status.tmdb" :disabled="busy" @click="sync">
            <Icon name="sync" :size="16" /> {{ busy ? 'Gleiche ab …' : 'Mit TMDB abgleichen' }}
          </button>
          <p v-else class="notice">Ohne <code>TMDB_API_KEY</code> läuft screenmates auf dem mitgelieferten Seed-Katalog.</p>
        </section>

        <section class="panel">
          <h2>Gruppe</h2>
          <div class="row" style="margin-bottom: 1rem">
            <button class="small" @click="resetDabei">Teilnahme für den nächsten Abend zurücksetzen</button>
          </div>
          <ul class="users">
            <li v-for="u in app.users" :key="u.id" class="row">
              <UserAvatar :user="u" />
              <span>{{ u.name }}</span>
              <span v-if="u.hat_schutz" class="muted"><Icon name="schloss" :size="13" /></span>
              <span class="muted small">seit {{ datum(u.created_at) }}</span>
              <span class="spacer"></span>
              <button v-if="u.hat_schutz && u.id !== app.me.id" class="ghost small" @click="removeSchutz(u)">Schutz entfernen</button>
              <button v-if="u.id !== app.me.id" class="ghost small danger" @click="removeUser(u)"><Icon name="muell" :size="14" /></button>
            </li>
          </ul>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 760px; display: flex; flex-direction: column; gap: 1.2rem; }
.page-head { margin-bottom: 0.2rem; }
section h2 { margin: 0 0 1rem; font-size: 1.1rem; }
section h3 { margin: 1.4rem 0 0.3rem; font-size: 0.95rem; }
section p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.chip.ok { color: var(--ok); border-color: var(--ok); }
.picker { margin-top: 0.9rem; }
.error { color: #ff6b6b; }
.secret { color: var(--text); }
.users { list-style: none; padding: 0; margin: 0; }
.users li { padding: 0.5rem 0; border-top: 1px solid var(--line); }
.small { font-size: 0.78rem; }
</style>
