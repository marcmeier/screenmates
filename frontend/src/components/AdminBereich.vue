<script setup>
import { t } from '../i18n'
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
  await fertig(t('adminbereich.nAngelegt', { n }))
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
  if (n && n !== u.name) await aendern(u, { name: n }, t('adminbereich.umbenanntInN', { n }))
}
async function ablehnen(u) {
  if (!confirm(t('adminbereich.antragVonNameAblehnen', { name: u.name }))) return
  await api.del(`/api/users/${u.id}`)
  await fertig(t('adminbereich.antragAbgelehnt'))
}
async function loeschen(u) {
  if (!confirm(t('adminbereich.nameLoeschenBewertungenUnd', { name: u.name }))) return
  await api.del(`/api/users/${u.id}`)
  await fertig(t('adminbereich.nameGeloescht', { name: u.name }))
}
async function schutzWeg(u) {
  if (!confirm(t('adminbereich.filmPasswortVonName', { name: u.name, name2: u.name }))) return
  await api.post(`/api/users/${u.id}/schutz`, { movie_id: null })
  await fertig(t('adminbereich.filmPasswortVonName2', { name: u.name }))
}
async function bildWeg(u) {
  if (!confirm(t('adminbereich.profilbildVonNameEntfernen', { name: u.name }))) return
  await api.del(`/api/users/${u.id}/bild`)
  await fertig(t('adminbereich.profilbildVonNameEntfernt', { name: u.name }))
}
async function abmelden(u) {
  if (!confirm(t('adminbereich.nameAufAllenGeraeten', { name: u.name }))) return
  const r = await api.post(`/api/admin/users/${u.id}/abmelden`)
  if (u.id === app.me?.id) return window.location.reload()
  await fertig(t('adminbereich.abgemeldet', { name: u.name, n: r.beendet }, r.beendet))
}

onMounted(laden)
// New requests arrive while the page is open: follow the count in the navigation.
watch(() => app.antraege, laden)
</script>

<template>

  <section v-if="antraege.length" class="panel">
    <h2>{{ $t('adminbereich.antraege') }} <span class="count">{{ antraege.length }}</span></h2>
    <ul class="people">
      <li v-for="u in antraege" :key="u.id" class="row">
        <UserAvatar :user="u" />
        <strong>{{ u.name }}</strong>
        <span class="muted small">{{ $t('adminbereich.beantragt', { am: datum(u.seit) }) }}</span>
        <span class="spacer"></span>
        <button class="small primary" @click="aendern(u, { freigegeben: true }, `„${u.name}“ freigegeben`)">{{ $t('adminbereich.freigeben') }}</button>
        <button class="ghost small danger" @click="ablehnen(u)">{{ $t('adminbereich.ablehnen') }}</button>
      </li>
    </ul>
  </section>

  <section class="panel">
    <h2>{{ $t('adminbereich.benutzer') }}</h2>
    <ul class="people">
      <li v-for="u in aktive" :key="u.id" class="person">
        <div class="row">
          <label class="farbe" :title="$t('adminbereich.farbeVonName', { name: u.name })">
            <UserAvatar :user="u" />
            <input type="color" :value="u.color || '#555555'" :aria-label="$t('adminbereich.farbeVonName2', { name: u.name })" @change="aendern(u, { color: $event.target.value })" />
          </label>
          <form v-if="bearbeiten === u.id" class="rename" @submit.prevent="namenSpeichern(u)">
            <input v-model="name" maxlength="30" :aria-label="$t('adminbereich.neuerNameFuerName', { name: u.name })" autofocus @keydown.esc="bearbeiten = null" />
            <button class="small primary">OK</button>
          </form>
          <strong v-else>{{ u.name }}</strong>
          <span v-if="u.admin" class="chip admin">{{ $t('adminbereich.admin') }}</span>
          <span v-if="u.hat_schutz" class="chip" :title="$t('adminbereich.nameMitFilmPasswort')"><Icon name="schloss" :size="12" /></span>
          <span class="muted small">{{ u.sitzungen ? $t('adminbereich.geraete', { n: u.sitzungen }, u.sitzungen) : $t('adminbereich.nichtAngemeldet') }} · {{ $t('adminbereich.seit', { am: datum(u.seit) }) }}</span>
        </div>
        <div class="row tools">
          <button class="ghost small" @click="umbenennen(u)"><Icon name="stift" :size="13" /> {{ $t('adminbereich.umbenennen') }}</button>
          <button v-if="!(u.admin && einzigerAdmin)" class="ghost small" @click="aendern(u, { admin: !u.admin }, u.admin ? $t('adminbereich.keinAdminMehr', { name: u.name }) : $t('adminbereich.jetztAdmin', { name: u.name }))">
            {{ u.admin ? $t('adminbereich.adminEntziehen') : $t('adminbereich.zumAdminMachen') }}
          </button>
          <button v-if="u.hat_schutz" class="ghost small" @click="schutzWeg(u)">{{ $t('adminbereich.filmPasswortZuruecksetzen') }}</button>
          <button v-if="u.bild" class="ghost small" @click="bildWeg(u)">{{ $t('adminbereich.bildEntfernen') }}</button>
          <button v-if="u.sitzungen" class="ghost small" @click="abmelden(u)"><Icon name="logout" :size="13" /> {{ $t('adminbereich.ueberallAbmelden') }}</button>
          <button v-if="u.id !== app.me?.id" class="ghost small danger" :aria-label="$t('adminbereich.nameLoeschen', { name: u.name })" @click="loeschen(u)"><Icon name="muell" :size="14" /></button>
        </div>
      </li>
    </ul>
    <form class="row create" @submit.prevent="anlegen">
      <input v-model="neuerName" maxlength="30" :placeholder="$t('adminbereich.namenDirektAnlegen')" :aria-label="$t('adminbereich.namenDirektAnlegen2')" />
      <button :disabled="!neuerName.trim()"><Icon name="plus" :size="15" /> {{ $t('adminbereich.anlegen') }}</button>
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
