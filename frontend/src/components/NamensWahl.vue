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
// A requested name waits for an admin.
const beantragt = ref(null)

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

async function create() {
  const name = newName.value.trim()
  if (!name) return
  error.value = ''
  busy.value = true
  try {
    const u = await app.createUser(name)
    if (u.freigegeben) {
      ui.toast(`Hallo ${u.name}!`, 'ok')
      ui.changed()
      close()
    } else {
      beantragt.value = u
      newName.value = ''
    }
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Modal label="Namen wählen" @close="close">
    <div class="wrap">
      <div class="brand">screen<span>mates</span></div>

      <template v-if="beantragt">
        <h2>Antrag gestellt</h2>
        <p class="muted center">
          „{{ beantragt.name }}“ wartet jetzt auf die Freigabe durch einen Admin{{ app.zugang.einladung ? ` von „${app.zugang.einladung.gruppe}“` : '' }}.
          Danach findest du deinen Namen hier in der Liste und kannst ihn mit einem Klick wählen.
        </p>
        <div class="center"><button @click="close">Alles klar</button></div>
      </template>

      <template v-else-if="!guarded">
        <h2>Wer schaut mit?</h2>
        <p v-if="app.zugang.einladung" class="einladung center">
          Du bist eingeladen in <strong>„{{ app.zugang.einladung.gruppe }}“</strong>.
          {{ app.zugang.einladung.direkt ? 'Leg deinen Namen an, dann bist du direkt dabei.' : 'Leg deinen Namen an; ein Admin der Gruppe schaltet ihn frei.' }}
        </p>
        <div v-if="app.users.length" class="users">
          <button v-for="u in app.users" :key="u.id" class="user" :disabled="busy" @click="pick(u)">
            <UserAvatar :user="u" />
            <span>{{ u.name }}</span>
            <Icon v-if="u.hat_schutz" name="schloss" :size="14" class="lock" />
          </button>
        </div>
        <p v-else class="muted center">Noch niemand da – leg den ersten Namen an. Er wird Admin.</p>

        <p v-if="app.users.length && !app.zugang.einladung" class="muted center hint">Neu hier? Beantrag deinen Namen, ein Admin schaltet ihn frei.</p>
        <form class="create" @submit.prevent="create">
          <input v-model="newName" maxlength="30" placeholder="Neuer Name …" aria-label="Neuer Name" />
          <button class="primary" :disabled="busy || !newName.trim()">
            <Icon name="plus" :size="16" /> {{ !app.users.length || app.zugang.einladung?.direkt ? 'Anlegen' : 'Beantragen' }}
          </button>
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
.hint { font-size: 0.85rem; margin: 0 0 0.6rem; }
.einladung { font-size: 0.9rem; margin: -0.6rem 0 1.2rem; }
.users { display: flex; flex-wrap: wrap; gap: 0.6rem; justify-content: center; margin-bottom: 1.6rem; }
.user { padding: 0.45rem 0.9rem 0.45rem 0.45rem; border-radius: 999px; }
.lock { color: var(--muted); }
.create { display: flex; gap: 0.5rem; }
.create button { flex: none; }
.back { margin-bottom: 0.4rem; }
.error { color: #ff6b6b; text-align: center; margin: 1rem 0 0; }
</style>
