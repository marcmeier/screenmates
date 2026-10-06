<script setup>
import { t } from '../../i18n'
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
    ui.toast(t('verwaltungtab.katalogAktualisiertNeuNeue', { neu: r.neu, gesamt: r.gesamt }), 'ok')
    await app.refreshStatus()
    ui.changed()
  } finally {
    busy.value = false
  }
}

async function resetDabei() {
  await api.del('/api/dabei')
  await app.refreshUsers()
  ui.toast(t('verwaltungtab.teilnahmeZurueckgesetzt'))
}
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>{{ $t('nav.verwaltung') }}</h1>
        <p>{{ app.admin ? $t('verwaltungtab.zugangGruppenKatalogUnd') : $t('verwaltungtab.deineGruppenNurFuer') }}</p>
      </div>
    </header>

    <div v-if="!app.verwaltetGruppen" class="empty">
      <strong>{{ $t('verwaltungtab.nurFuerAdmins') }}</strong>
      <p class="muted">{{ $t('verwaltungtab.deinEigenesProfilFindest') }} <a href="#/profil/einstellungen">{{ $t('verwaltungtab.profilEinstellungen') }}</a>.</p>
    </div>
    <template v-else>

      <GruppenVerwaltung v-if="app.verwaltetGruppen" />
      <section v-if="app.gruppenAdmin && app.gruppe" class="panel">
        <h2>{{ $t('verwaltungtab.naechsterAbend') }}{{ app.gruppe ? ` – ${app.gruppe.name}` : '' }}</h2>
        <div class="row">
          <button class="small" @click="resetDabei">{{ $t('verwaltungtab.teilnahmeFuerDenNaechsten') }}</button>
        </div>
      </section>
      <template v-if="app.admin">
        <AdminBereich />

        <KiNutzung />

        <section class="panel">
          <h2>{{ $t('verwaltungtab.katalog') }}</h2>
          <p class="muted">
            {{ $t('verwaltungtab.movieCountFilmeDavon', { movie_count: app.status.movie_count, canon_count: app.status.canon_count }) }}
            <template v-if="app.status.last_sync">{{ $t('verwaltungtab.letzterAbgleichX', { x: vorWann(app.status.last_sync) }) }}</template>
          </p>
          <button v-if="app.status.tmdb" :disabled="busy" @click="sync">
            <Icon name="sync" :size="16" /> {{ busy ? $t('verwaltungtab.gleicheAb') : $t('verwaltungtab.mitTmdbAbgleichen') }}
          </button>
          <p v-else class="notice">{{ $t('verwaltungtab.ohne') }} <code>TMDB_API_KEY</code> {{ $t('verwaltungtab.laeuftScreenmatesAufDem') }}</p>
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
