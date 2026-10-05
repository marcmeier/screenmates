<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { datum } from '../format'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'

// Admins: the access question, name requests and everyone's profile.
const app = useApp()
const ui = useUi()

const alle = ref([])
const antraege = computed(() => alle.value.filter((u) => !u.freigegeben))
const aktive = computed(() => alle.value.filter((u) => u.freigegeben))
// The last admin can't step down (the server refuses it too).
const einzigerAdmin = computed(() => aktive.value.filter((u) => u.admin).length <= 1)

async function laden() {
  alle.value = (await api.get('/api/admin/users')).users
}
async function fertig(text) {
  await Promise.all([laden(), app.refreshUsers()])
  ui.changed()
  if (text) ui.toast(text, 'ok')
}

// --- people ---
const neuerName = ref('')
const bearbeiten = ref(null) // id of the name being renamed
const name = ref('')

async function anlegen() {
  const n = neuerName.value.trim()
  if (!n) return
  await api.post('/api/admin/users', { name: n })
  neuerName.value = ''
  await fertig(`„${n}“ angelegt`)
}
async function aendern(u, felder, text) {
  await api.patch(`/api/admin/users/${u.id}`, felder)
  await fertig(text)
}
function umbenennen(u) {
  bearbeiten.value = u.id
  name.value = u.name
}
async function namenSpeichern(u) {
  const n = name.value.trim()
  bearbeiten.value = null
  if (n && n !== u.name) await aendern(u, { name: n }, `Umbenannt in „${n}“`)
}
async function ablehnen(u) {
  if (!confirm(`Antrag von „${u.name}“ ablehnen?`)) return
  await api.del(`/api/users/${u.id}`)
  await fertig('Antrag abgelehnt')
}
async function loeschen(u) {
  if (!confirm(`„${u.name}“ löschen? Bewertungen und Stimmen gehen verloren, Kommentare bleiben anonym erhalten.`)) return
  await api.del(`/api/users/${u.id}`)
  await fertig(`„${u.name}“ gelöscht`)
}
async function schutzWeg(u) {
  if (!confirm(`Film-Passwort von „${u.name}“ zurücksetzen? Danach kann jeder den Namen wählen, bis ${u.name} ein neues festlegt.`)) return
  await api.post(`/api/users/${u.id}/schutz`, { movie_id: null })
  await fertig(`Film-Passwort von ${u.name} zurückgesetzt`)
}
async function bildWeg(u) {
  if (!confirm(`Profilbild von „${u.name}“ entfernen?`)) return
  await api.del(`/api/users/${u.id}/bild`)
  await fertig(`Profilbild von ${u.name} entfernt`)
}
async function abmelden(u) {
  if (!confirm(`„${u.name}“ auf allen Geräten abmelden? Diese Geräte brauchen danach eine neue Einladung.`)) return
  const r = await api.post(`/api/admin/users/${u.id}/abmelden`)
  if (u.id === app.me?.id) return window.location.reload()
  await fertig(`${u.name}: ${r.beendet} ${r.beendet === 1 ? 'Gerät' : 'Geräte'} abgemeldet`)
}

onMounted(laden)
// New requests arrive while the page is open: follow the count in the navigation.
watch(() => app.antraege, laden)
</script>

<template>

  <section v-if="antraege.length" class="panel">
    <h2>Anträge <span class="count">{{ antraege.length }}</span></h2>
    <ul class="people">
      <li v-for="u in antraege" :key="u.id" class="row">
        <UserAvatar :user="u" />
        <strong>{{ u.name }}</strong>
        <span class="muted small">beantragt {{ datum(u.seit) }}</span>
        <span class="spacer"></span>
        <button class="small primary" @click="aendern(u, { freigegeben: true }, `„${u.name}“ freigegeben`)">Freigeben</button>
        <button class="ghost small danger" @click="ablehnen(u)">Ablehnen</button>
      </li>
    </ul>
  </section>

  <section class="panel">
    <h2>Benutzer</h2>
    <ul class="people">
      <li v-for="u in aktive" :key="u.id" class="person">
        <div class="row">
          <label class="farbe" :title="`Farbe von ${u.name}`">
            <UserAvatar :user="u" />
            <input type="color" :value="u.color || '#555555'" :aria-label="`Farbe von ${u.name}`" @change="aendern(u, { color: $event.target.value })" />
          </label>
          <form v-if="bearbeiten === u.id" class="rename" @submit.prevent="namenSpeichern(u)">
            <input v-model="name" maxlength="30" :aria-label="`Neuer Name für ${u.name}`" autofocus @keydown.esc="bearbeiten = null" />
            <button class="small primary">OK</button>
          </form>
          <strong v-else>{{ u.name }}</strong>
          <span v-if="u.admin" class="chip admin">Admin</span>
          <span v-if="u.hat_schutz" class="chip" title="Name mit Film-Passwort geschützt"><Icon name="schloss" :size="12" /></span>
          <span class="muted small">{{ u.sitzungen ? `${u.sitzungen} ${u.sitzungen === 1 ? 'Gerät' : 'Geräte'}` : 'nicht angemeldet' }} · seit {{ datum(u.seit) }}</span>
        </div>
        <div class="row tools">
          <button class="ghost small" @click="umbenennen(u)"><Icon name="stift" :size="13" /> Umbenennen</button>
          <button v-if="!(u.admin && einzigerAdmin)" class="ghost small" @click="aendern(u, { admin: !u.admin }, u.admin ? `${u.name} ist kein Admin mehr` : `${u.name} ist jetzt Admin`)">
            {{ u.admin ? 'Admin entziehen' : 'Zum Admin machen' }}
          </button>
          <button v-if="u.hat_schutz" class="ghost small" @click="schutzWeg(u)">Film-Passwort zurücksetzen</button>
          <button v-if="u.bild" class="ghost small" @click="bildWeg(u)">Bild entfernen</button>
          <button v-if="u.sitzungen" class="ghost small" @click="abmelden(u)"><Icon name="logout" :size="13" /> Überall abmelden</button>
          <button v-if="u.id !== app.me?.id" class="ghost small danger" :aria-label="`${u.name} löschen`" @click="loeschen(u)"><Icon name="muell" :size="14" /></button>
        </div>
      </li>
    </ul>
    <form class="row create" @submit.prevent="anlegen">
      <input v-model="neuerName" maxlength="30" placeholder="Namen direkt anlegen …" aria-label="Namen direkt anlegen" />
      <button :disabled="!neuerName.trim()"><Icon name="plus" :size="15" /> Anlegen</button>
    </form>
  </section>
</template>

<style scoped>
section h2 { margin: 0 0 1rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
section p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.count { font-size: 0.75rem; background: var(--accent); color: #fff; border-radius: 999px; padding: 1px 8px; }
.people { list-style: none; padding: 0; margin: 0 0 1rem; }
.people > li { padding: 0.6rem 0; border-top: 1px solid var(--line); }
.person .tools { margin: 0.35rem 0 0 2.6rem; gap: 0.2rem; }
.chip.admin { color: var(--accent); border-color: var(--accent); }
.farbe { position: relative; cursor: pointer; display: inline-flex; }
.farbe input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%; padding: 0; border: 0; }
.rename { display: flex; gap: 0.4rem; }
.rename input { width: 12rem; }
.create input { flex: 1; }
.small { font-size: 0.78rem; }
</style>
