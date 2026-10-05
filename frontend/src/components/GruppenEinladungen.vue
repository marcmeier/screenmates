<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { datum } from '../format'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'

// One group's invitation links and its open requests (new names and join requests).
const props = defineProps({ gruppe: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const app = useApp()
const ui = useUi()

const einladungen = ref([])
const anfragen = ref([])
const neu = ref({ direkt: false, tage: 7, max: '', notiz: '' })
const offen = ref(false)

async function laden() {
  const [e, a] = await Promise.all([
    api.get(`/api/admin/gruppen/${props.gruppe.id}/einladungen`),
    api.get(`/api/admin/gruppen/${props.gruppe.id}/anfragen`),
  ])
  einladungen.value = e.einladungen
  anfragen.value = a.anfragen
}

const url = (e) => `${location.origin}/#/einladung/${e.token}`

async function kopieren(e) {
  try {
    await navigator.clipboard.writeText(url(e))
    ui.toast('Link kopiert', 'ok')
  } catch {
    window.prompt('Link zum Kopieren:', url(e))
  }
}

async function teilen(e) {
  const text = `Komm in „${props.gruppe.name}“ auf screenmates: ${url(e)}`
  if (navigator.share) await navigator.share({ title: 'screenmates', text }).catch(() => {})
  else kopieren(e)
}

async function anlegen() {
  const n = neu.value
  const e = await api.post(`/api/admin/gruppen/${props.gruppe.id}/einladungen`, {
    direkt: n.direkt,
    tage: n.tage ? Number(n.tage) : null,
    max_nutzungen: n.max ? Number(n.max) : null,
    notiz: n.notiz,
  })
  neu.value = { direkt: false, tage: 7, max: '', notiz: '' }
  offen.value = false
  await laden()
  kopieren(e)
}

async function widerrufen(e) {
  if (!confirm('Diesen Link widerrufen? Wer damit schon drin ist, bleibt drin.')) return
  await api.del(`/api/admin/einladungen/${e.id}`)
  await laden()
  ui.toast('Link widerrufen')
}

async function entscheiden(a, annehmen) {
  const name = a.name || app.userById(a.user_id)?.name || 'Jemand'
  if (!annehmen && !confirm(a.neu ? `Antrag von „${name}“ ablehnen? Der Name wird gelöscht.` : `Beitrittsanfrage von ${name} ablehnen?`)) return
  await api.post(`/api/admin/gruppen/${props.gruppe.id}/anfragen/${a.user_id}`, { annehmen })
  await Promise.all([laden(), app.refreshUsers()])
  emit('changed')
  ui.toast(annehmen ? `${name} ist jetzt in „${props.gruppe.name}“` : 'Abgelehnt', annehmen ? 'ok' : 'info')
}

function beschreibung(e) {
  const teile = [e.direkt ? 'direkt aufnehmen' : 'mit Freigabe']
  teile.push(e.max_nutzungen ? `${e.nutzungen}/${e.max_nutzungen} genutzt` : `${e.nutzungen}× genutzt`)
  teile.push(e.gueltig_bis ? `bis ${datum(e.gueltig_bis)}` : 'ohne Ablauf')
  return teile.join(' · ')
}

onMounted(laden)
defineExpose({ laden })
</script>

<template>
  <div class="einladungen">
    <div v-if="anfragen.length" class="block">
      <h4>Anfragen <span class="count">{{ anfragen.length }}</span></h4>
      <ul>
        <li v-for="a in anfragen" :key="`${a.user_id}-${a.neu}`" class="row">
          <UserAvatar v-if="!a.neu" :user-id="a.user_id" />
          <strong>{{ a.name || app.userById(a.user_id)?.name }}</strong>
          <span class="muted small">{{ a.neu ? 'neuer Name' : 'möchte beitreten' }} · {{ datum(a.seit) }}</span>
          <span class="spacer"></span>
          <button class="small primary" @click="entscheiden(a, true)">Aufnehmen</button>
          <button class="ghost small danger" @click="entscheiden(a, false)">Ablehnen</button>
        </li>
      </ul>
    </div>

    <div class="block">
      <div class="row">
        <h4>Einladungslinks</h4>
        <span class="spacer"></span>
        <button class="small" @click="offen = !offen"><Icon name="plus" :size="13" /> Neuer Link</button>
      </div>
      <form v-if="offen" class="neu" @submit.prevent="anlegen">
        <label class="field">
          Wer den Link öffnet …
          <select v-model="neu.direkt">
            <option :value="false">… stellt einen Antrag, ein Admin der Gruppe gibt frei</option>
            <option :value="true">… ist direkt drin (für persönlich verschickte Links)</option>
          </select>
        </label>
        <div class="row">
          <label class="field">
            Gültig
            <select v-model="neu.tage">
              <option :value="1">1 Tag</option>
              <option :value="7">7 Tage</option>
              <option :value="30">30 Tage</option>
              <option :value="null">ohne Ablauf</option>
            </select>
          </label>
          <label class="field">
            Für
            <select v-model="neu.max">
              <option value="1">1 Person</option>
              <option value="5">5 Personen</option>
              <option value="20">20 Personen</option>
              <option value="">beliebig viele</option>
            </select>
          </label>
          <label class="field notiz">
            Notiz (nur für Admins)
            <input v-model="neu.notiz" maxlength="60" placeholder="z. B. Gruppenchat, für Tom" />
          </label>
        </div>
        <button class="primary small">Link erzeugen und kopieren</button>
      </form>
      <ul v-if="einladungen.length">
        <li v-for="e in einladungen" :key="e.id" class="row link" :class="{ abgelaufen: !e.gueltig }">
          <Icon name="teilen" :size="14" />
          <span class="was">
            <strong>{{ e.notiz || 'Einladung' }}</strong>
            <small class="muted">{{ e.gueltig ? beschreibung(e) : 'abgelaufen oder aufgebraucht' }}</small>
          </span>
          <span class="spacer"></span>
          <template v-if="e.gueltig">
            <button class="ghost small" @click="kopieren(e)"><Icon name="kopieren" :size="13" /> Kopieren</button>
            <button class="ghost small" @click="teilen(e)">Teilen</button>
          </template>
          <button class="ghost small danger" :aria-label="`Link ${e.notiz || ''} widerrufen`" @click="widerrufen(e)"><Icon name="x" :size="14" /></button>
        </li>
      </ul>
      <p v-else class="muted small">Noch keine Links. Ohne Link kommt niemand Neues in die Gruppe.</p>
    </div>
  </div>
</template>

<style scoped>
.einladungen { display: flex; flex-direction: column; gap: 0.6rem; margin-top: 0.6rem; }
.block { background: var(--bg-raised); border-radius: var(--radius); padding: 0.7rem 0.8rem; }
h4 { margin: 0; font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem; }
ul { list-style: none; padding: 0; margin: 0.5rem 0 0; }
li { padding: 0.3rem 0; }
.count { font-size: 0.7rem; background: var(--accent); color: #fff; border-radius: 999px; padding: 0 7px; }
.neu { display: flex; flex-direction: column; gap: 0.6rem; margin: 0.7rem 0; }
.neu .row { align-items: flex-end; }
.notiz { flex: 1; min-width: 12rem; }
.was { display: flex; flex-direction: column; min-width: 0; }
.was small { font-size: 0.74rem; }
.abgelaufen { opacity: 0.55; }
.small { font-size: 0.78rem; }
</style>
