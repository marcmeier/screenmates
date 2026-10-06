<script setup>
import { t as tr } from '../i18n'
import { computed, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { terminText } from '../einladung'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'

// The group's date poll: everyone answers yes / maybe / no per date; whoever may
// picks one, which becomes the date (and everyone's answer their reply).
const props = defineProps({ umfrage: { type: Object, required: true } })
const emit = defineEmits(['update', 'festgelegt'])
const app = useApp()
const ui = useUi()
const neu = ref('')
const busy = ref(false)

const ANTWORTEN = [
  { key: 'ja', label: tr('terminumfrage.ja'), icon: 'gesehen' },
  { key: 'vielleicht', label: tr('terminumfrage.vielleicht'), icon: 'fragezeichen' },
  { key: 'nein', label: tr('terminumfrage.nein'), icon: 'x' },
]
const leute = (v, antwort) =>
  Object.entries(v.stimmen)
    .filter(([, a]) => a === antwort)
    .map(([id]) => Number(id))
const noch = computed(() => {
  // Members who haven't answered any date yet.
  const geantwortet = new Set(props.umfrage.vorschlaege.flatMap((v) => Object.keys(v.stimmen).map(Number)))
  return app.mitglieder.filter((u) => !geantwortet.has(u.id))
})

async function machen(fn) {
  busy.value = true
  try {
    emit('update', await fn())
    ui.changed()
  } finally {
    busy.value = false
  }
}
const stimmen = (v, antwort) =>
  machen(() => api.put(`/api/termin/umfrage/${v.id}/stimme`, { antwort: v.meine === antwort ? null : antwort }))
const loeschen = (v) => machen(() => api.del(`/api/termin/umfrage/${v.id}`))
async function beenden() {
  if (!confirm(tr('terminumfrage.dieUmfrageBeendenOhne'))) return
  await machen(() => api.del('/api/termin/umfrage'))
}
async function festlegen(v) {
  busy.value = true
  try {
    const r = await api.post(`/api/termin/umfrage/${v.id}/festlegen`)
    const t = terminText(r.termin)
    ui.toast(tr('terminumfrage.terminStehtTagZeit', { tag: t.tag, zeit: t.zeit }), 'ok', 5000)
    ui.changed()
    emit('festgelegt', r)
  } finally {
    busy.value = false
  }
}
async function vorschlagen() {
  if (!neu.value) return
  await machen(() => api.post('/api/termin/umfrage', { termin: `${neu.value}:00` }))
  neu.value = ''
}
</script>

<template>
  <div class="umfrage" :aria-label="$t('terminumfrage.terminumfrage')">
    <div class="kopf">
      <Icon name="umfrage" :size="16" class="muted" />
      <strong>{{ $t('terminumfrage.wannHabtIhrZeit') }}</strong>
      <span v-if="noch.length" class="muted klein">{{ $t('terminumfrage.nochOffen', { namen: noch.map((u) => u.name).join(', ') }) }}</span>
    </div>
    <ul>
      <li v-for="v in umfrage.vorschlaege" :key="v.id" class="option" :class="{ favorit: umfrage.favorit === v.id }">
        <div class="wann">
          <strong>{{ terminText(v).tag }}</strong>
          <span class="muted">{{ terminText(v).zeit }}<template v-if="v.notiz"> · {{ v.notiz }}</template></span>
          <span v-if="umfrage.favorit === v.id" class="badge">{{ $t('terminumfrage.favorit') }}</span>
        </div>
        <div class="avatars" :title="leute(v, 'ja').map((id) => app.userById(id)?.name).join(', ')">
          <UserAvatar v-for="id in leute(v, 'ja')" :key="id" :user-id="id" />
        </div>
        <div class="antworten" role="group" :aria-label="$t('terminumfrage.deineAntwortFuerX', { x: terminText(v).tag })">
          <button
            v-for="a in ANTWORTEN"
            :key="a.key"
            class="small"
            :class="[a.key, { on: v.meine === a.key }]"
            :aria-pressed="v.meine === a.key"
            :disabled="busy"
            :title="leute(v, a.key).map((id) => app.userById(id)?.name).join(', ') || a.label"
            @click="stimmen(v, a.key)"
          >
            <Icon :name="a.icon" :size="13" /> <span class="label">{{ a.label }}</span> <span class="n">{{ v[a.key] }}</span>
          </button>
        </div>
        <div class="aktionen">
          <button v-if="umfrage.darf_festlegen" class="small" :class="{ primary: umfrage.favorit === v.id }" :disabled="busy" @click="festlegen(v)">
            {{ $t('terminumfrage.festlegen') }}
          </button>
          <button v-if="v.darf_loeschen" class="small ghost" :disabled="busy" :aria-label="$t('terminumfrage.vorschlagXEntfernen', { x: terminText(v).tag })" @click="loeschen(v)">
            <Icon name="x" :size="13" />
          </button>
        </div>
      </li>
    </ul>
    <form v-if="umfrage.vorschlaege.length < umfrage.max" class="row neu" @submit.prevent="vorschlagen">
      <input v-model="neu" type="datetime-local" :aria-label="$t('terminumfrage.weiterenTerminVorschlagen')" />
      <button class="small" :disabled="!neu || busy"><Icon name="plus" :size="13" /> {{ $t('terminumfrage.vorschlagen') }}</button>
      <span class="spacer"></span>
      <button v-if="umfrage.darf_festlegen" type="button" class="small ghost" :disabled="busy" @click="beenden">{{ $t('terminumfrage.umfrageBeenden') }}</button>
    </form>
  </div>
</template>

<style scoped>
.umfrage { border-top: 1px solid var(--line); padding-top: 0.7rem; display: flex; flex-direction: column; gap: 0.6rem; }
.kopf { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; font-size: 0.92rem; }
.klein { font-size: 0.78rem; }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.option {
  display: grid; grid-template-columns: minmax(10rem, 1fr) auto auto auto; align-items: center; gap: 0.7rem;
  padding: 0.5rem 0.7rem; border-radius: 9px; background: var(--bg); border: 1px solid var(--line);
}
.option.favorit { border-color: color-mix(in srgb, var(--accent) 55%, var(--line)); }
.wann { display: flex; flex-direction: column; gap: 1px; min-width: 0; font-size: 0.88rem; }
.wann .muted { font-size: 0.8rem; }
.badge { align-self: flex-start; font-size: 0.66rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--accent); }
.avatars .avatar { width: 22px; height: 22px; font-size: 0.58rem; }
.antworten { display: flex; gap: 3px; }
.antworten button { gap: 0.3rem; }
.antworten .n { font-weight: 700; font-variant-numeric: tabular-nums; }
.antworten .ja.on { border-color: var(--ok); background: color-mix(in srgb, var(--ok) 16%, transparent); }
.antworten .vielleicht.on { border-color: var(--gold); background: color-mix(in srgb, var(--gold) 16%, transparent); }
.antworten .nein.on { border-color: var(--accent); background: var(--accent-soft); }
.aktionen { display: flex; gap: 3px; justify-content: flex-end; }
.neu input { width: auto; color-scheme: dark; padding: 0.3rem 0.5rem; font-size: 0.82rem; }
@media (max-width: 700px) {
  .option { grid-template-columns: 1fr auto; }
  .antworten { grid-column: 1 / -1; }
  .antworten button { flex: 1; justify-content: center; }
  .aktionen { grid-column: 2; grid-row: 1; }
  .avatars { display: none; }
}
@media (max-width: 420px) { .antworten .label { display: none; } }
</style>