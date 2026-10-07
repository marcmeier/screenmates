<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from '../composables/useRoute'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { t } from '../i18n'
import AnmeldeCode from './AnmeldeCode.vue'
import Icon from './Icon.vue'
import Benachrichtigungen from './Benachrichtigungen.vue'
import Darstellung from './Darstellung.vue'
import KalenderAbo from './KalenderAbo.vue'
import MeineAbos from './MeineAbos.vue'
import ProfilBild from './ProfilBild.vue'

// Your own settings (profile picture, devices, subscriptions) – part of the profile page.
const app = useApp()
const ui = useUi()
// One topic at a time: #/profil/einstellungen/<reiter>.
const route = useRoute()
const REITER = computed(() =>
  [
    { id: 'profil', icon: 'profil' },
    { id: 'darstellung', icon: 'funken' },
    { id: 'benachrichtigungen', icon: 'glocke' },
    app.status.tmdb && { id: 'dienste', icon: 'kino' },
  ].filter(Boolean),
)
const aktiv = computed(() => REITER.value.find((r) => r.id === route.value.id)?.id ?? 'profil')

// On how many browsers your name is; signing out the others (a lost phone, a friend's laptop).
const geraete = ref(null)
async function geraeteLaden() {
  geraete.value = (await api.get('/api/login')).geraete
}
onMounted(geraeteLaden)
async function andereAbmelden() {
  if (!confirm(t('einst.andereAbmeldenFrage', { name: app.me.name }))) return
  const r = await api.post('/api/login/andere-abmelden')
  geraete.value = r.geraete
  ui.toast(t('einst.andereAbgemeldet', { n: r.abgemeldet }, r.abgemeldet), 'ok')
}
async function vergessen() {
  if (!confirm(t('einst.vergessenFrage', { name: app.me.name }))) return
  await app.vergessen(app.me.id)
  ui.loginOpen = true
}
// Your data: a file with everything about you, or your name deleted for good.
async function namenLoeschen() {
  const eingabe = prompt(t('einst.loeschenFrage', { name: app.me.name }))
  if (eingabe === null) return
  await api.del(`/api/users/me?name=${encodeURIComponent(eingabe)}`)
  window.location.reload() // without a name this browser is back at the door
}
</script>

<template>
  <div class="spalte">
    <nav class="reiter" :aria-label="$t('app.einstellungen')">
      <a
        v-for="r in REITER"
        :key="r.id"
        :href="`#/profil/einstellungen/${r.id}`"
        :class="{ aktiv: aktiv === r.id }"
        :aria-current="aktiv === r.id ? 'page' : undefined"
      >
        <Icon :name="r.icon" :size="15" /> {{ $t(`einst.reiter.${r.id}`) }}
      </a>
    </nav>

    <section v-if="aktiv === 'profil'" class="panel">
      <h2>{{ $t('einst.profil') }}</h2>
      <div class="row">
        <strong class="ich">{{ app.me.name }}</strong>
        <span class="spacer"></span>
        <button class="ghost small" @click="app.logout()"><Icon name="logout" :size="14" /> {{ $t('einst.abmelden') }}</button>
      </div>
      <ProfilBild :user="app.me" class="bild" />
      <p v-if="app.status.wuensche" class="ideas muted">
        {{ $t('einst.ideen') }} <a href="#/wuensche">{{ $t('nav.wuensche') }}</a>
      </p>

      <h3>{{ $t('einst.geraete') }}</h3>
      <p class="muted">{{ $t('einst.geraeteText') }}</p>
      <AnmeldeCode url="/api/login/code" :label="$t('einst.geraetVerbinden')" />
      <div class="row geraete">
        <span v-if="geraete" class="muted small">{{ $t('einst.geraeteAnzahl', { n: geraete }, geraete) }}</span>
        <span class="spacer"></span>
        <button v-if="geraete > 1" class="ghost small" @click="andereAbmelden">{{ $t('einst.andereAbmelden') }}</button>
        <button class="ghost small" @click="vergessen">{{ $t('einst.vergessen') }}</button>
      </div>

      <h3>{{ $t('einst.daten') }}</h3>
      <p class="muted">{{ $t('einst.datenText') }}</p>
      <div class="row">
        <a class="button small" href="/api/users/me/export" download><Icon name="download" :size="14" /> {{ $t('einst.datenHerunterladen') }}</a>
        <span class="spacer"></span>
        <button class="ghost small danger" @click="namenLoeschen"><Icon name="muell" :size="14" /> {{ $t('einst.loeschen') }}</button>
      </div>
    </section>

    <Darstellung v-else-if="aktiv === 'darstellung'" />

    <template v-else-if="aktiv === 'benachrichtigungen'">
      <Benachrichtigungen />
      <KalenderAbo />
    </template>

    <MeineAbos v-else-if="aktiv === 'dienste'" />
  </div>
</template>

<style scoped>
.spalte { max-width: 760px; display: flex; flex-direction: column; gap: 1.2rem; }
section h2 { margin: 0 0 1rem; font-size: 1.1rem; }
section h3 { margin: 1.4rem 0 0.3rem; font-size: 0.95rem; }
section p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.geraete { margin-top: 0.9rem; }
.ideas { margin: 1rem 0 0; }
.ich { font-size: 1.05rem; }
.bild { margin-top: 0.9rem; }
.ideas a { color: var(--text); }
.small { font-size: 0.78rem; }
</style>
