<script setup>
import { ref } from 'vue'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import FilmPicker from './FilmPicker.vue'
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import UserAvatar from './UserAvatar.vue'

const app = useApp()
const ui = useUi()
const newName = ref('')
const error = ref('')
const busy = ref(false)
// Film-as-PIN: a guarded name is unlocked by clicking the right film.
const guarded = ref(null)

function close() {
  ui.loginOpen = false
}

async function attempt(fn) {
  error.value = ''
  busy.value = true
  try {
    await fn()
    ui.toast(`Hallo ${app.me.name}!`, 'ok')
    ui.changed()
    close()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function pick(u) {
  if (u.hat_schutz) {
    error.value = ''
    guarded.value = u
  } else {
    attempt(() => app.choose(u.id))
  }
}

const unlock = (movie) => attempt(() => app.choose(guarded.value.id, movie.id))

function create() {
  const name = newName.value.trim()
  if (name) attempt(() => app.createUser(name))
}
</script>

<template>
  <Modal label="Namen wählen" @close="close">
    <div class="wrap">
      <div class="brand">screen<span>mates</span></div>

      <template v-if="!guarded">
        <h2>Wer schaut mit?</h2>
        <div v-if="app.users.length" class="users">
          <button v-for="u in app.users" :key="u.id" class="user" :disabled="busy" @click="pick(u)">
            <UserAvatar :user="u" />
            <span>{{ u.name }}</span>
            <Icon v-if="u.hat_schutz" name="schloss" :size="14" class="lock" />
          </button>
        </div>
        <p v-else class="muted center">Noch niemand da – leg den ersten Namen an.</p>

        <form class="create" @submit.prevent="create">
          <input v-model="newName" maxlength="30" placeholder="Neuer Name …" aria-label="Neuer Name" />
          <button class="primary" :disabled="busy || !newName.trim()"><Icon name="plus" :size="16" /> Anlegen</button>
        </form>
      </template>

      <template v-else>
        <button class="ghost small back" @click="guarded = null"><Icon name="pfeil" :size="14" /> Zurück</button>
        <h2>Film-Passwort für {{ guarded.name }}</h2>
        <p class="muted center">Such den Film, den {{ guarded.name }} als Passwort gewählt hat, und klick ihn an.</p>
        <FilmPicker :busy="busy" @pick="unlock" />
      </template>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
    </div>
  </Modal>
</template>

<style scoped>
.wrap { padding: 2rem; }
.brand { text-align: center; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.02em; }
.brand span { color: var(--accent); }
h2 { text-align: center; font-weight: 600; font-size: 1.25rem; margin: 0.6rem 0 1.4rem; }
.center { text-align: center; }
.users { display: flex; flex-wrap: wrap; gap: 0.6rem; justify-content: center; margin-bottom: 1.6rem; }
.user { padding: 0.45rem 0.9rem 0.45rem 0.45rem; border-radius: 999px; }
.lock { color: var(--muted); }
.create { display: flex; gap: 0.5rem; }
.create button { flex: none; }
.back { margin-bottom: 0.4rem; }
.error { color: #ff6b6b; text-align: center; margin: 1rem 0 0; }
</style>
