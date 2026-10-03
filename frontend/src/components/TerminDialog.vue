<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import Modal from './Modal.vue'

// When and where the next movie night is. Anyone with a name may set it.
const props = defineProps({ termin: { type: Object, default: null } })
const emit = defineEmits(['close', 'saved'])
const ui = useUi()

// The date is German time on every device: someone abroad means 20:00 at home,
// not 20:00 where their phone happens to be. <input type="datetime-local"> has no
// zone, so it is filled with Berlin wall-clock time and sent without an offset,
// which the backend reads as German time.
const berlin = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
})
const wandzeit = (iso) => berlin.format(new Date(iso)).replace(' ', 'T') // "2026-10-09T20:00"
function naechsterFreitag() {
  const heute = berlin.format(new Date()).slice(0, 10)
  const d = new Date(`${heute}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + ((5 - d.getUTCDay() + 7) % 7 || 7))
  return `${d.toISOString().slice(0, 10)}T20:00`
}
const wann = ref(props.termin?.termin ? wandzeit(props.termin.termin) : naechsterFreitag())
const notiz = ref(props.termin?.notiz ?? '')
const busy = ref(false)

async function speichern() {
  busy.value = true
  try {
    const t = await api.put('/api/termin', { termin: `${wann.value}:00`, notiz: notiz.value })
    ui.toast('Termin gespeichert', 'ok')
    ui.changed()
    emit('saved', t)
  } finally {
    busy.value = false
  }
}

async function entfernen() {
  const t = await api.del('/api/termin')
  ui.changed()
  emit('saved', t)
}
</script>

<template>
  <Modal label="Termin für den Filmabend" @close="emit('close')">
    <form class="termin" @submit.prevent="speichern">
      <h2><Icon name="kalender" /> Termin</h2>
      <label>
        <span>Wann? <em class="muted">(deutsche Zeit)</em></span>
        <input v-model="wann" type="datetime-local" required />
      </label>
      <label>
        <span>Wo? <em class="muted">(optional)</em></span>
        <input v-model="notiz" maxlength="80" placeholder="z. B. bei Marc oder online im Kino" />
      </label>
      <div class="row">
        <button v-if="termin?.termin" type="button" class="ghost danger" @click="entfernen">Termin entfernen</button>
        <span class="spacer"></span>
        <button type="button" @click="emit('close')">Abbrechen</button>
        <button class="primary" :disabled="busy || !wann">Speichern</button>
      </div>
    </form>
  </Modal>
</template>

<style scoped>
.termin { padding: 1.3rem 1.4rem; display: flex; flex-direction: column; gap: 0.9rem; }
h2 { margin: 0; font-size: 1.15rem; display: flex; align-items: center; gap: 0.5rem; }
label { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.85rem; }
em { font-style: normal; }
input { color-scheme: dark; }
</style>
