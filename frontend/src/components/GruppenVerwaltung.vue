<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Erklaerung from './Erklaerung.vue'
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
const emit = defineEmits(['teilnahme'])
// One group on screen at a time (picked above it); "neu" shows the form for a new one.
const gewaehlt = ref(null)
const gruppe = computed(() => gruppen.value.find((g) => g.id === gewaehlt.value) ?? null)

async function laden() {
  // Names and groups may have changed elsewhere (another admin, another tab).
  const [r] = await Promise.all([api.get('/api/admin/gruppen'), app.refreshUsers(), app.refreshGruppen()])
  gruppen.value = r.gruppen
  if (gewaehlt.value !== 'neu' && !r.gruppen.some((g) => g.id === gewaehlt.value))
    gewaehlt.value = (r.gruppen.find((g) => g.id === app.gruppe?.id) ?? r.gruppen[0])?.id ?? (r.server_admin ? 'neu' : null)
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
  const g = await api.post('/api/admin/gruppen', { name: n })
  neueGruppe.value = ''
  if (g?.id) gewaehlt.value = g.id
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
  <div class="gruppen">
    <p class="muted intro">
      {{ $t('gruppenverwaltung.kurz') }}<Erklaerung :label="$t('gruppenverwaltung.gruppen')" :text="$t('erklaerung.gruppen')" />
    </p>
    <p v-if="ohneGruppe.length" class="notice warn">
      {{ $t('gruppenverwaltung.ohneGruppe', { namen: ohneGruppe.map((u) => u.name).join(', ') }) }}
    </p>

    <div v-if="gruppen.length > 1 || serverAdmin" class="wahl" role="tablist" :aria-label="$t('gruppenverwaltung.gruppen')">
      <button
        v-for="g in gruppen"
        :key="g.id"
        role="tab"
        :aria-selected="gewaehlt === g.id"
        :class="{ aktiv: gewaehlt === g.id }"
        @click="gewaehlt = g.id"
      >
        {{ g.name }} <span class="anzahl">{{ g.mitglieder.length }}</span>
      </button>
      <button v-if="serverAdmin" role="tab" class="neu-knopf" :aria-selected="gewaehlt === 'neu'" :class="{ aktiv: gewaehlt === 'neu' }" @click="gewaehlt = 'neu'">
        <Icon name="plus" :size="14" /> {{ $t('gruppenverwaltung.neueGruppe2') }}
      </button>
    </div>

    <form v-if="gewaehlt === 'neu'" class="karte neu" @submit.prevent="anlegen">
      <h3>{{ $t('gruppenverwaltung.neueGruppe2') }}</h3>
      <div class="row">
        <input v-model="neueGruppe" maxlength="40" :placeholder="$t('gruppenverwaltung.neueGruppe')" :aria-label="$t('gruppenverwaltung.neueGruppe2')" autofocus />
        <button class="primary" :disabled="!neueGruppe.trim()"><Icon name="plus" :size="15" /> {{ $t('gruppenverwaltung.gruppeAnlegen') }}</button>
      </div>
    </form>

    <article v-else-if="gruppe" class="karte" :aria-label="gruppe.name">
      <header class="kopf">
        <form v-if="umbenennen === gruppe.id" class="rename" @submit.prevent="speichereName(gruppe)">
          <input v-model="name" maxlength="40" :aria-label="$t('gruppenverwaltung.neuerNameFuerName', { name: gruppe.name })" autofocus @keydown.esc="umbenennen = null" />
          <button class="small primary">OK</button>
        </form>
        <template v-else>
          <Icon name="personen" :size="18" class="symbol" />
          <h3>{{ gruppe.name }}</h3>
          <span v-if="gruppe.id === app.gruppe?.id" class="chip klein">{{ $t('gruppenverwaltung.aktiv') }}</span>
        </template>
        <span class="spacer"></span>
        <button class="ghost small" @click="starteUmbenennen(gruppe)"><Icon name="stift" :size="13" /> {{ $t('gruppenverwaltung.umbenennen') }}</button>
        <button v-if="serverAdmin" class="ghost small danger" :aria-label="$t('gruppenverwaltung.gruppeNameLoeschen', { name: gruppe.name })" @click="loeschen(gruppe)">
          <Icon name="muell" :size="14" />
        </button>
      </header>

      <section class="abschnitt">
        <h4>{{ $t('gruppenverwaltung.mitglieder') }} <span class="count">{{ gruppe.mitglieder.length }}</span></h4>
        <ul class="mitglieder">
          <li v-for="m in gruppe.mitglieder" :key="m.user_id" class="row">
            <UserAvatar :user-id="m.user_id" />
            <span>{{ userName(m.user_id) }}</span>
            <span v-if="m.admin" class="chip admin">{{ $t('gruppenverwaltung.gruppenAdmin') }}</span>
            <span class="spacer"></span>
            <button class="ghost small" @click="adminUmschalten(gruppe, m)">{{ m.admin ? $t('gruppenverwaltung.adminEntziehen') : $t('gruppenverwaltung.zumGruppenAdmin') }}</button>
            <button class="ghost small danger" :aria-label="$t('gruppenverwaltung.xAusNameNehmen2', { x: userName(m.user_id), name: gruppe.name })" @click="entfernen(gruppe, m)">
              <Icon name="x" :size="14" />
            </button>
          </li>
        </ul>
        <form v-if="nichtDrin(gruppe).length" class="row hinzu" @submit.prevent="aufnehmen(gruppe)">
          <select v-model="hinzu[gruppe.id]" :aria-label="$t('gruppenverwaltung.mitgliedFuerNameWaehlen', { name: gruppe.name })">
            <option value="">{{ $t('gruppenverwaltung.mitgliedHinzufuegen') }}</option>
            <option v-for="u in nichtDrin(gruppe)" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
          <button class="small" :disabled="!hinzu[gruppe.id]"><Icon name="plus" :size="14" /> {{ $t('gruppenverwaltung.aufnehmen') }}</button>
        </form>
      </section>

      <section class="abschnitt">
        <GruppenEinladungen :gruppe="gruppe" @changed="laden" />
      </section>

      <section v-if="gruppe.id === app.gruppe?.id" class="abschnitt">
        <h4>{{ $t('verwaltungtab.naechsterAbend') }}</h4>
        <div class="row">
          <button class="small" @click="emit('teilnahme')">{{ $t('verwaltungtab.teilnahmeFuerDenNaechsten') }}</button>
        </div>
      </section>
    </article>
  </div>
</template>

<style scoped>
.gruppen { display: flex; flex-direction: column; gap: 0.9rem; }
.intro { margin: 0; font-size: 0.88rem; }
p { margin: 0; font-size: 0.9rem; }
.notice.warn { color: var(--gold); }
.wahl { display: flex; gap: 0.4rem; overflow-x: auto; scrollbar-width: none; padding-bottom: 2px; }
.wahl button { flex: none; gap: 0.45rem; border-radius: 999px; padding: 0.4rem 0.9rem; font-size: 0.88rem; }
.wahl button.aktiv { border-color: var(--accent); background: var(--accent-soft); color: var(--text); font-weight: 600; }
.wahl .anzahl { font-size: 0.72rem; color: var(--muted); }
.neu-knopf { border-style: dashed; color: var(--muted); }
/* One group = one card: framed and set off from everything around it. */
.karte {
  border: 1px solid color-mix(in srgb, var(--text) 22%, var(--line)); border-radius: 14px; overflow: hidden;
  background: var(--bg-soft);
}
.kopf {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; padding: 0.8rem 1rem;
  background: var(--bg-raised); border-bottom: 1px solid var(--line);
}
.kopf h3 { margin: 0; font-size: 1.05rem; }
.kopf .symbol { color: var(--muted); }
.chip.klein { font-size: 0.7rem; padding: 1px 8px; }
.abschnitt { padding: 0.9rem 1rem; }
.abschnitt + .abschnitt { border-top: 1px solid var(--line); }
.abschnitt h4, .abschnitt :deep(h4) {
  margin: 0 0 0.6rem; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted);
}
.count { margin-left: 0.3rem; color: var(--text); }
.mitglieder { list-style: none; padding: 0; margin: 0; }
.mitglieder li { padding: 0.3rem 0; }
.chip.admin { color: var(--text); border-color: color-mix(in srgb, var(--text) 35%, var(--line)); }
.hinzu { margin-top: 0.6rem; }
.hinzu select { flex: 1; max-width: 18rem; }
.neu { padding: 1rem; display: flex; flex-direction: column; gap: 0.7rem; }
.neu h3 { margin: 0; font-size: 1rem; }
.neu input { flex: 1; min-width: 0; }
.rename { display: flex; gap: 0.4rem; flex: 1; }
.rename input { flex: 1; min-width: 0; }
.small { font-size: 0.78rem; }
</style>
