<script setup>
import { computed, ref } from 'vue'
import { useRoute } from '../composables/useRoute'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { t } from '../i18n'
import FilmPicker from './FilmPicker.vue'
import Icon from './Icon.vue'
import Benachrichtigungen from './Benachrichtigungen.vue'
import Darstellung from './Darstellung.vue'
import KalenderAbo from './KalenderAbo.vue'
import MeineAbos from './MeineAbos.vue'
import ProfilBild from './ProfilBild.vue'

// Your own settings (profile picture, film password, subscriptions) – part of the profile page.
const app = useApp()
const ui = useUi()
const pickSchutz = ref(false)
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

async function setSchutz(movie) {
  await api.post(`/api/users/${app.me.id}/schutz`, { movie_id: movie?.id ?? null })
  pickSchutz.value = false
  await app.refreshUsers()
  ui.toast(movie ? t('einst.geschuetztDurch', { film: movie.title }) : t('einst.schutzEntfernt'), 'ok')
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
      <p class="ideas muted">
        {{ $t('einst.ideen') }} <a href="#/wuensche">{{ $t('nav.wuensche') }}</a>
      </p>

      <h3>{{ $t('einst.schutz') }}</h3>
      <p class="muted">
        {{ $t('einst.schutzText', { name: app.me.name }) }}
      </p>
      <div class="row">
        <span class="chip" :class="{ ok: app.me.hat_schutz }">
          <Icon name="schloss" :size="13" /> {{ app.me.hat_schutz ? $t('einst.geschuetzt') : $t('einst.ungeschuetzt') }}
        </span>
        <button class="small" @click="pickSchutz = !pickSchutz">{{ app.me.hat_schutz ? $t('einst.filmAendern') : $t('einst.schutzEinrichten') }}</button>
        <button v-if="app.me.hat_schutz" class="ghost small" @click="setSchutz(null)">{{ $t('einst.entfernen') }}</button>
      </div>
      <div v-if="pickSchutz" class="picker"><FilmPicker :placeholder="$t('einst.passwortFilm')" @pick="setSchutz" /></div>
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
.chip.ok { color: var(--ok); border-color: var(--ok); }
.picker { margin-top: 0.9rem; }
.ideas { margin: 1rem 0 0; }
.ich { font-size: 1.05rem; }
.bild { margin-top: 0.9rem; }
.ideas a { color: var(--text); }
.small { font-size: 0.78rem; }
</style>
