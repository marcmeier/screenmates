<script setup>
import { ref } from 'vue'
import { useApp } from '../stores/app'
import Icon from './Icon.vue'
import UeberInhalt from './UeberInhalt.vue'

// The front door: screenmates is invite-only. A link (#/einladung/<code>) opens it
// by itself; here you can also paste the link or code you got.
const app = useApp()
const eingabe = ref('')
const error = ref('')
const busy = ref(false)

function code(text) {
  const t = text.trim()
  const m = t.match(/einladung\/([A-Za-z0-9_-]+)/)
  return m ? m[1] : t
}

async function rein() {
  const token = code(eingabe.value)
  if (!token) return
  error.value = ''
  busy.value = true
  try {
    await app.einlassen(token)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
// Imprint and privacy notice: for everyone, also without an invitation.
const ueber = ref(location.hash.startsWith('#/ueber'))
</script>

<template>
  <main class="door">
    <div class="card panel">
      <div class="brand">screen<span>mates</span></div>
      <p class="lock"><Icon name="schloss" :size="15" /> Nur mit Einladung</p>
      <h1>Hier kommt man nur mit einem Einladungslink hinein.</h1>
      <p class="muted">Frag in deiner Filmgruppe nach dem Link. Hast du einen Link oder Code? Dann füg ihn hier ein.</p>
      <form class="row" @submit.prevent="rein">
        <input v-model="eingabe" placeholder="Einladungslink oder Code" aria-label="Einladungslink oder Code" />
        <button class="primary" :disabled="busy || !eingabe.trim()">Rein</button>
      </form>
      <p v-if="app.einladungFehler || error" class="error" role="alert">{{ error || app.einladungFehler }}</p>
    </div>
    <button class="ghost small rechtliches" :aria-expanded="ueber" @click="ueber = !ueber">Über · Impressum · Datenschutz</button>
    <UeberInhalt v-if="ueber" class="ueber" />
  </main>
</template>

<style scoped>
.door { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1rem; padding: 1.5rem; }
.rechtliches { color: var(--muted); }
.ueber { width: min(760px, 100%); text-align: left; }
.card { width: min(480px, 100%); padding: 2rem; text-align: center; }
.brand { font-weight: 800; font-size: 1.6rem; letter-spacing: -0.03em; }
.brand span { color: var(--accent); }
.lock { display: inline-flex; align-items: center; gap: 0.35rem; color: var(--muted); font-size: 0.8rem; margin: 0.4rem 0 1.4rem; }
h1 { font-size: 1.2rem; font-weight: 650; margin: 0 0 0.4rem; }
.card > .muted { margin: 0 0 1.2rem; font-size: 0.9rem; }
form input { flex: 1; }
.error { color: #ff6b6b; margin: 1rem 0 0; }
</style>
