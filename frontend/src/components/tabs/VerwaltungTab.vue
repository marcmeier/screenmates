<script setup>
import { ref } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import AdminBereich from '../AdminBereich.vue'
import Gefahrenzone from '../Gefahrenzone.vue'
import GruppenVerwaltung from '../GruppenVerwaltung.vue'
import Icon from '../Icon.vue'
import KiNutzung from '../KiNutzung.vue'

// For admins only: groups, access, catalogue and KI usage – kept apart from everyone's own profile.
const app = useApp()
const ui = useUi()
const busy = ref(false)

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
        <h1>Verwaltung</h1>
        <p>{{ app.admin ? 'Zugang, Gruppen, Katalog und KI – nur für Admins sichtbar.' : 'Deine Gruppen – nur für Gruppen-Admins sichtbar.' }}</p>
      </div>
    </header>

    <div v-if="!app.verwaltetGruppen" class="empty">
      <strong>Nur für Admins</strong>
      <p class="muted">Dein eigenes Profil findest du unter <a href="#/profil/einstellungen">Profil → Einstellungen</a>.</p>
    </div>
    <template v-else>

      <GruppenVerwaltung v-if="app.verwaltetGruppen" />
      <section v-if="app.gruppenAdmin && app.gruppe" class="panel">
        <h2>Nächster Abend{{ app.gruppe ? ` – ${app.gruppe.name}` : '' }}</h2>
        <div class="row">
          <button class="small" @click="resetDabei">Teilnahme für den nächsten Abend zurücksetzen</button>
        </div>
      </section>
      <template v-if="app.admin">
        <AdminBereich />

        <KiNutzung />

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

        <Gefahrenzone />
      </template>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 760px; display: flex; flex-direction: column; gap: 1.2rem; }
.page-head { margin-bottom: 0.2rem; }
section h2 { margin: 0 0 1rem; font-size: 1.1rem; }
section p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.small { font-size: 0.78rem; }
</style>
