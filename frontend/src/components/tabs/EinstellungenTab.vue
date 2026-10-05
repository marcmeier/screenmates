<script setup>
import { ref } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import AdminBereich from '../AdminBereich.vue'
import FilmPicker from '../FilmPicker.vue'
import Icon from '../Icon.vue'
import MeineAbos from '../MeineAbos.vue'
import ProfilBild from '../ProfilBild.vue'

const app = useApp()
const ui = useUi()
const pickSchutz = ref(false)
const busy = ref(false)

async function setSchutz(movie) {
  await api.post(`/api/users/${app.me.id}/schutz`, { movie_id: movie?.id ?? null })
  pickSchutz.value = false
  await app.refreshUsers()
  ui.toast(movie ? `Dein Name ist jetzt durch „${movie.title}“ geschützt` : 'Schutz entfernt', 'ok')
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
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>Einstellungen</h1>
        <p>Dein Profil, und für Admins alles rund um Zugang, Gruppe und Katalog.</p>
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
          <strong class="ich">{{ app.me.name }}</strong>
          <span class="spacer"></span>
          <button class="ghost small" @click="app.logout()"><Icon name="logout" :size="14" /> Abmelden</button>
        </div>
        <ProfilBild :user="app.me" class="bild" />
        <p class="ideas muted">
          Ideen, was screenmates noch können soll? <a href="#/wuensche">Wünsche & Ideen</a>
        </p>

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

      <MeineAbos v-if="app.status.tmdb" />

      <template v-if="app.admin">
        <AdminBereich />

        <section class="panel">
          <h2>Katalog</h2>
          <p class="muted">
            {{ app.status.movie_count }} Filme, davon {{ app.status.canon_count }} aus dem TMDB-Abgleich.
            <template v-if="app.status.last_sync">Letzter Abgleich {{ vorWann(app.status.last_sync) }}.</template>
          </p>
          <button v-if="app.status.tmdb" :disabled="busy" @click="sync">
            <Icon name="sync" :size="16" /> {{ busy ? 'Gleiche ab …' : 'Mit TMDB abgleichen' }}
          </button>
          <p v-else class="notice">Ohne <code>TMDB_API_KEY</code> läuft screenmates auf dem mitgelieferten Seed-Katalog.</p>
        </section>

        <section class="panel">
          <h2>Nächster Abend</h2>
          <div class="row">
            <button class="small" @click="resetDabei">Teilnahme für den nächsten Abend zurücksetzen</button>
          </div>
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
.ideas { margin: 1rem 0 0; }
.ich { font-size: 1.05rem; }
.bild { margin-top: 0.9rem; }
.ideas a { color: var(--text); }
.small { font-size: 0.78rem; }
</style>
