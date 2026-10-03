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

// <input type="datetime-local"> speaks local time without an offset.
const lokal = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
function naechsterFreitag() {
  const d = new Date()
  d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7 || 7))
  d.setHours(20, 0, 0, 0)
  return d
}
const wann = ref(lokal(props.termin?.termin ? new Date(props.termin.termin) : naechsterFreitag()))
const notiz = ref(props.termin?.notiz ?? '')
const busy = ref(false)

async function speichern() {
  busy.value = true
  try {
    const t = await api.put('/api/termin', { termin: new Date(wann.value).toISOString(), notiz: notiz.value })
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
        <span>Wann?</span>
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
