<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import GruppenEinladungen from './GruppenEinladungen.vue'
import UserAvatar from './UserAvatar.vue'

// Groups: server admins create and delete them; group admins (and server admins) run
// their members. Members of a group see only that group's movie nights.
const app = useApp()
const ui = useUi()
const gruppen = ref([])
const serverAdmin = ref(false)
const neueGruppe = ref('')
const umbenennen = ref(null)
const name = ref('')
const hinzu = ref({}) // group id -> user id picked for adding

async function laden() {
  // Names and groups may have changed elsewhere (another admin, another tab).
  const [r] = await Promise.all([api.get('/api/admin/gruppen'), app.refreshUsers(), app.refreshGruppen()])
  gruppen.value = r.gruppen
  for (const g of r.gruppen) hinzu.value[g.id] ??= '' // shows the "add member" prompt
  serverAdmin.value = r.server_admin
}
async function fertig(text) {
  await laden()
  ui.changed()
  if (text) ui.toast(text, 'ok')
}

const ohneGruppe = computed(() => {
  const drin = new Set(gruppen.value.flatMap((g) => g.mitglieder.map((m) => m.user_id)))
  return serverAdmin.value ? app.users.filter((u) => !drin.has(u.id)) : []
})
const nichtDrin = (g) => app.users.filter((u) => !g.mitglieder.some((m) => m.user_id === u.id))
const userName = (id) => app.userById(id)?.name || t('allg.jemand')

async function anlegen() {
  const n = neueGruppe.value.trim()
  if (!n) return
  await api.post('/api/admin/gruppen', { name: n })
  neueGruppe.value = ''
  await fertig(t('gruppenverwaltung.gruppeNAngelegtJetzt', { n }))
}
function starteUmbenennen(g) {
  umbenennen.value = g.id
  name.value = g.name
}
async function speichereName(g) {
  const n = name.value.trim()
  umbenennen.value = null
  if (n && n !== g.name) {
    await api.patch(`/api/admin/gruppen/${g.id}`, { name: n })
    await fertig(t('gruppenverwaltung.umbenanntInN', { n }))
  }
}
async function loeschen(g) {
  if (!confirm(t('gruppenverwaltung.gruppeNameLoeschenChronik', { name: g.name }))) return
  await api.del(`/api/admin/gruppen/${g.id}`)
  await fertig(t('gruppenverwaltung.gruppeNameGeloescht', { name: g.name }))
}
async function aufnehmen(g) {
  const uid = hinzu.value[g.id]
  if (!uid) return
  await api.put(`/api/admin/gruppen/${g.id}/mitglieder/${uid}`, { admin: false })
  hinzu.value[g.id] = ''
  await fertig(t('gruppenverwaltung.xIstJetztIn', { x: userName(uid), name: g.name }))
}
async function adminUmschalten(g, m) {
  await api.put(`/api/admin/gruppen/${g.id}/mitglieder/${m.user_id}`, { admin: !m.admin })
  await fertig(m.admin ? t('gruppenverwaltung.xIstKeinGruppen', { x: userName(m.user_id) }) : t('gruppenverwaltung.xIstJetztGruppen', { x: userName(m.user_id) }))
}
async function entfernen(g, m) {
  if (!confirm(t('gruppenverwaltung.xAusNameNehmen', { x: userName(m.user_id), name: g.name }))) return
  await api.del(`/api/admin/gruppen/${g.id}/mitglieder/${m.user_id}`)
  await fertig(t('gruppenverwaltung.xIstNichtMehr', { x: userName(m.user_id), name: g.name }))
}

onMounted(laden)
</script>

<template>
  <section class="panel">
    <h2>{{ $t('gruppenverwaltung.gruppen') }}</h2>
    <p class="muted">
      {{ $t('gruppenverwaltung.jedeGruppeHatIhren') }}
      <strong>{{ $t('gruppenverwaltung.einladungslink') }}</strong> {{ $t('gruppenverwaltung.hereinDenErzeugtEin') }}
    </p>
    <p v-if="ohneGruppe.length" class="notice warn">
      Noch in keiner Gruppe: {{ ohneGruppe.map((u) => u.name).join(', ') }}
    </p>

    <div v-for="g in gruppen" :key="g.id" class="gruppe">
      <div class="row kopf">
        <form v-if="umbenennen === g.id" class="rename" @submit.prevent="speichereName(g)">
          <input v-model="name" maxlength="40" :aria-label="$t('gruppenverwaltung.neuerNameFuerName', { name: g.name })" autofocus @keydown.esc="umbenennen = null" />
          <button class="small primary">OK</button>
        </form>
        <h3 v-else>{{ g.name }}</h3>
        <span class="muted small">{{ g.mitglieder.length }} {{ g.mitglieder.length === 1 ? $t('gruppenverwaltung.mitglied') : $t('gruppenverwaltung.mitglieder') }}</span>
        <span class="spacer"></span>
        <button class="ghost small" @click="starteUmbenennen(g)"><Icon name="stift" :size="13" /> {{ $t('gruppenverwaltung.umbenennen') }}</button>
        <button v-if="serverAdmin" class="ghost small danger" :aria-label="$t('gruppenverwaltung.gruppeNameLoeschen', { name: g.name })" @click="loeschen(g)">
          <Icon name="muell" :size="14" />
        </button>
      </div>
      <ul class="mitglieder">
        <li v-for="m in g.mitglieder" :key="m.user_id" class="row">
          <UserAvatar :user-id="m.user_id" />
          <span>{{ userName(m.user_id) }}</span>
          <span v-if="m.admin" class="chip admin">{{ $t('gruppenverwaltung.gruppenAdmin') }}</span>
          <span class="spacer"></span>
          <button class="ghost small" @click="adminUmschalten(g, m)">{{ m.admin ? $t('gruppenverwaltung.adminEntziehen') : $t('gruppenverwaltung.zumGruppenAdmin') }}</button>
          <button class="ghost small danger" :aria-label="$t('gruppenverwaltung.xAusNameNehmen2', { x: userName(m.user_id), name: g.name })" @click="entfernen(g, m)">
            <Icon name="x" :size="14" />
          </button>
        </li>
      </ul>
      <GruppenEinladungen :gruppe="g" @changed="laden" />
      <form v-if="nichtDrin(g).length" class="row hinzu" @submit.prevent="aufnehmen(g)">
        <select v-model="hinzu[g.id]" :aria-label="$t('gruppenverwaltung.mitgliedFuerNameWaehlen', { name: g.name })">
          <option value="">{{ $t('gruppenverwaltung.mitgliedHinzufuegen') }}</option>
          <option v-for="u in nichtDrin(g)" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
        <button class="small" :disabled="!hinzu[g.id]"><Icon name="plus" :size="14" /> {{ $t('gruppenverwaltung.aufnehmen') }}</button>
      </form>
    </div>

    <form v-if="serverAdmin" class="row neu" @submit.prevent="anlegen">
      <input v-model="neueGruppe" maxlength="40" :placeholder="$t('gruppenverwaltung.neueGruppe')" :aria-label="$t('gruppenverwaltung.neueGruppe2')" />
      <button :disabled="!neueGruppe.trim()"><Icon name="plus" :size="15" /> {{ $t('gruppenverwaltung.gruppeAnlegen') }}</button>
    </form>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 1rem; font-size: 1.1rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.notice.warn { color: var(--gold); }
.gruppe { border-top: 1px solid var(--line); padding: 0.8rem 0; }
.kopf h3 { margin: 0; font-size: 1rem; }
.mitglieder { list-style: none; padding: 0; margin: 0.5rem 0; }
.mitglieder li { padding: 0.25rem 0; }
.chip.admin { color: var(--accent); border-color: var(--accent); }
.hinzu select { flex: 1; max-width: 18rem; }
.hinzu { margin-top: 0.6rem; }
.neu { margin-top: 0.8rem; }
.neu input { flex: 1; }
.rename { display: flex; gap: 0.4rem; }
.small { font-size: 0.78rem; }
</style>
