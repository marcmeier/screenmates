<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
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
const userName = (id) => app.userById(id)?.name || 'Jemand'

async function anlegen() {
  const n = neueGruppe.value.trim()
  if (!n) return
  await api.post('/api/admin/gruppen', { name: n })
  neueGruppe.value = ''
  await fertig(`Gruppe „${n}“ angelegt – jetzt Mitglieder hinzufügen`)
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
    await fertig(`Umbenannt in „${n}“`)
  }
}
async function loeschen(g) {
  if (!confirm(`Gruppe „${g.name}“ löschen? Chronik, Bewertungen, Gästebuch, Merkliste, Vorschläge und Termin dieser Gruppe gehen verloren. Die Mitglieder und ihre Erfolge bleiben.`)) return
  await api.del(`/api/admin/gruppen/${g.id}`)
  await fertig(`Gruppe „${g.name}“ gelöscht`)
}
async function aufnehmen(g) {
  const uid = hinzu.value[g.id]
  if (!uid) return
  await api.put(`/api/admin/gruppen/${g.id}/mitglieder/${uid}`, { admin: false })
  hinzu.value[g.id] = ''
  await fertig(`${userName(uid)} ist jetzt in „${g.name}“`)
}
async function adminUmschalten(g, m) {
  await api.put(`/api/admin/gruppen/${g.id}/mitglieder/${m.user_id}`, { admin: !m.admin })
  await fertig(m.admin ? `${userName(m.user_id)} ist kein Gruppen-Admin mehr` : `${userName(m.user_id)} ist jetzt Gruppen-Admin`)
}
async function entfernen(g, m) {
  if (!confirm(`${userName(m.user_id)} aus „${g.name}“ nehmen? Bewertungen und Kommentare dort bleiben erhalten.`)) return
  await api.del(`/api/admin/gruppen/${g.id}/mitglieder/${m.user_id}`)
  await fertig(`${userName(m.user_id)} ist nicht mehr in „${g.name}“`)
}

onMounted(laden)
</script>

<template>
  <section class="panel">
    <h2>Gruppen</h2>
    <p class="muted">
      Jede Gruppe hat ihren eigenen Filmabend, ihre Chronik, Merkliste, Vorschläge, ihren Termin und ihr Kino – sichtbar nur
      für ihre Mitglieder. Namen, Level und Erfolge gelten für den ganzen Server.
    </p>
    <p v-if="ohneGruppe.length" class="notice warn">
      Noch in keiner Gruppe: {{ ohneGruppe.map((u) => u.name).join(', ') }}
    </p>

    <div v-for="g in gruppen" :key="g.id" class="gruppe">
      <div class="row kopf">
        <form v-if="umbenennen === g.id" class="rename" @submit.prevent="speichereName(g)">
          <input v-model="name" maxlength="40" :aria-label="`Neuer Name für ${g.name}`" autofocus @keydown.esc="umbenennen = null" />
          <button class="small primary">OK</button>
        </form>
        <h3 v-else>{{ g.name }}</h3>
        <span class="muted small">{{ g.mitglieder.length }} {{ g.mitglieder.length === 1 ? 'Mitglied' : 'Mitglieder' }}</span>
        <span class="spacer"></span>
        <button class="ghost small" @click="starteUmbenennen(g)"><Icon name="stift" :size="13" /> Umbenennen</button>
        <button v-if="serverAdmin" class="ghost small danger" :aria-label="`Gruppe ${g.name} löschen`" @click="loeschen(g)">
          <Icon name="muell" :size="14" />
        </button>
      </div>
      <ul class="mitglieder">
        <li v-for="m in g.mitglieder" :key="m.user_id" class="row">
          <UserAvatar :user-id="m.user_id" />
          <span>{{ userName(m.user_id) }}</span>
          <span v-if="m.admin" class="chip admin">Gruppen-Admin</span>
          <span class="spacer"></span>
          <button class="ghost small" @click="adminUmschalten(g, m)">{{ m.admin ? 'Admin entziehen' : 'Zum Gruppen-Admin' }}</button>
          <button class="ghost small danger" :aria-label="`${userName(m.user_id)} aus ${g.name} nehmen`" @click="entfernen(g, m)">
            <Icon name="x" :size="14" />
          </button>
        </li>
      </ul>
      <form v-if="nichtDrin(g).length" class="row hinzu" @submit.prevent="aufnehmen(g)">
        <select v-model="hinzu[g.id]" :aria-label="`Mitglied für ${g.name} wählen`">
          <option value="">Mitglied hinzufügen …</option>
          <option v-for="u in nichtDrin(g)" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
        <button class="small" :disabled="!hinzu[g.id]"><Icon name="plus" :size="14" /> Aufnehmen</button>
      </form>
    </div>

    <form v-if="serverAdmin" class="row neu" @submit.prevent="anlegen">
      <input v-model="neueGruppe" maxlength="40" placeholder="Neue Gruppe …" aria-label="Neue Gruppe" />
      <button :disabled="!neueGruppe.trim()"><Icon name="plus" :size="15" /> Gruppe anlegen</button>
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
.neu { margin-top: 0.8rem; }
.neu input { flex: 1; }
.rename { display: flex; gap: 0.4rem; }
.small { font-size: 0.78rem; }
</style>
