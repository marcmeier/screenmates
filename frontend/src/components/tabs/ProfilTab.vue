<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { useRoute } from '../../composables/useRoute'
import UserAvatar from '../UserAvatar.vue'

// Your profile: your achievements and your own settings, in one place.
// Someone else's profile (#/profil/person/<id>) shows their achievements.
const ErfolgeTab = defineAsyncComponent(() => import('./ErfolgeTab.vue'))
const ProfilEinstellungen = defineAsyncComponent(() => import('../ProfilEinstellungen.vue'))

const app = useApp()
const ui = useUi()
const route = useRoute()
const fremd = computed(() => route.value.sub === 'person' && Number(route.value.id) !== app.me?.id)
const seite = computed(() => (route.value.sub === 'einstellungen' ? 'einstellungen' : 'erfolge'))
</script>

<template>
  <ErfolgeTab v-if="fremd" />
  <div v-else class="page">
    <div v-if="!app.me" class="empty">
      <strong>{{ $t('app.erstNamen') }}</strong>
      <button class="primary" style="margin-top: 0.8rem" @click="ui.loginOpen = true">{{ $t('namen.dialog') }}</button>
    </div>
    <template v-else>
      <header class="kopf">
        <UserAvatar :user="app.me" class="gross" />
        <div>
          <h1>{{ app.me.name }}</h1>
          <p class="muted">
            {{ $t('profiltab.levelX', { x: app.me.level || 1 }) }}<template v-if="app.admin"> {{ $t('profiltab.admin') }}</template><template v-if="app.gruppe"> · {{ app.gruppe.name }}</template>
          </p>
        </div>
      </header>
      <nav class="unter" :aria-label="$t('profiltab.profil')">
        <a href="#/profil" :class="{ active: seite === 'erfolge' }" :aria-current="seite === 'erfolge' ? 'page' : undefined">{{ $t('profiltab.erfolge') }}</a>
        <a href="#/profil/einstellungen" :class="{ active: seite === 'einstellungen' }" :aria-current="seite === 'einstellungen' ? 'page' : undefined">{{ $t('app.einstellungen') }}</a>
      </nav>
      <ProfilEinstellungen v-if="seite === 'einstellungen'" />
      <ErfolgeTab v-else eingebettet />
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 980px; display: flex; flex-direction: column; gap: 1.2rem; }
.kopf { display: flex; align-items: center; gap: 1.1rem; }
.kopf h1 { margin: 0; }
.kopf p { margin: 0.2rem 0 0; }
.gross { width: 64px; height: 64px; font-size: 1.3rem; }
.unter { display: flex; gap: 0.3rem; border-bottom: 1px solid var(--line); }
.unter a {
  padding: 0.55rem 0.9rem; text-decoration: none; color: var(--muted); font-weight: 600; font-size: 0.92rem;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
}
.unter a:hover { color: var(--text); }
.unter a.active { color: var(--text); border-bottom-color: var(--accent); }
</style>
