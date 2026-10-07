<script setup>
import { t } from '../../i18n'
import { computed, ref } from 'vue'
import { useRoute } from '../../composables/useRoute'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import AdminBereich from '../AdminBereich.vue'
import Gefahrenzone from '../Gefahrenzone.vue'
import GruppenVerwaltung from '../GruppenVerwaltung.vue'
import Icon from '../Icon.vue'
import KiNutzung from '../KiNutzung.vue'

// For admins only: groups, people, the system (catalogue, AI) and the danger zone – one tab each,
// so nothing runs into the next. Group admins only see their groups.
const app = useApp()
const ui = useUi()
const route = useRoute()
const busy = ref(false)
const REITER = computed(() =>
  [
    { id: 'gruppen', icon: 'personen' },
    app.admin && { id: 'personen', icon: 'profil', zahl: app.antraege },
    app.admin && { id: 'system', icon: 'rad' },
    app.admin && { id: 'gefahr', icon: 'muell' },
  ].filter(Boolean),
)
const aktiv = computed(() => REITER.value.find((r) => r.id === route.value.sub)?.id ?? 'gruppen')

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

// Optional parts of screenmates, switched on or off for the whole server.
async function wuenscheSetzen(an) {
  await api.put('/api/admin/einstellungen', { wuensche: an })
  await app.refreshStatus()
  ui.toast(an ? t('verwaltungtab.wuenscheAn') : t('verwaltungtab.wuenscheAus'), 'ok')
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
      <nav v-if="REITER.length > 1" class="reiter" :aria-label="$t('nav.verwaltung')">
        <a
          v-for="r in REITER"
          :key="r.id"
          :href="`#/verwaltung/${r.id}`"
          :class="{ aktiv: aktiv === r.id, gefahr: r.id === 'gefahr' }"
          :aria-current="aktiv === r.id ? 'page' : undefined"
        >
          <Icon :name="r.icon" :size="15" /> {{ $t(`verwaltungtab.reiter.${r.id}`) }}
          <span v-if="r.zahl" class="zahl">{{ r.zahl }}</span>
        </a>
      </nav>

      <GruppenVerwaltung v-if="aktiv === 'gruppen'" @teilnahme="resetDabei" />

      <AdminBereich v-else-if="aktiv === 'personen'" />

      <template v-else-if="aktiv === 'system'">
        <section class="panel">
          <h2>{{ $t('verwaltungtab.funktionen') }}</h2>
          <label class="schalter">
            <input type="checkbox" :checked="app.status.wuensche" @change="wuenscheSetzen($event.target.checked)" />
            <span>
              <strong>{{ $t('nav.wuensche') }}</strong>
              <span class="muted">{{ $t('verwaltungtab.wuenscheText') }}</span>
            </span>
          </label>
        </section>

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
      </template>

      <Gefahrenzone v-else-if="aktiv === 'gefahr'" />
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 760px; display: flex; flex-direction: column; gap: 1.2rem; }
.page-head { margin-bottom: 0.2rem; }
section h2 { margin: 0 0 1rem; font-size: 1.1rem; }
section p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.small { font-size: 0.78rem; }
.schalter { display: flex; gap: 0.7rem; align-items: flex-start; cursor: pointer; font-size: 0.9rem; }
.schalter input { margin-top: 0.2rem; }
.schalter > span { display: flex; flex-direction: column; gap: 0.2rem; }

</style>
