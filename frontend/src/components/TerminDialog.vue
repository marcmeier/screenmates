<script setup>
import { ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import Modal from './Modal.vue'

// When and where the next movie night is: set it (anyone with a name may), or let the
// group vote on a few dates (see TerminUmfrage.vue).
const props = defineProps({
  termin: { type: Object, default: null },
  modus: { type: String, default: 'fest' }, // 'fest' | 'umfrage'
})
const emit = defineEmits(['close', 'saved', 'umfrage'])
const ui = useUi()

// The date is German time on every device: someone abroad means 20:00 at home,
// not 20:00 where their phone happens to be. <input type="datetime-local"> has no
// zone, so it is filled with Berlin wall-clock time and sent without an offset,
// which the backend reads as German time.
const berlin = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
})
const wandzeit = (iso) => berlin.format(new Date(iso)).replace(' ', 'T') // "2026-10-09T20:00"
/** The next given weekday (0 = Sunday … 6 = Saturday) at 20:00, never today. */
function naechster(wochentag) {
  const heute = berlin.format(new Date()).slice(0, 10)
  const d = new Date(`${heute}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + ((wochentag - d.getUTCDay() + 7) % 7 || 7))
  return `${d.toISOString().slice(0, 10)}T20:00`
}
const art = ref(props.modus)
const wann = ref(props.termin?.termin ? wandzeit(props.termin.termin) : naechster(5))
const notiz = ref(props.termin?.notiz ?? '')
// For the poll: Friday and Saturday to start with.
const optionen = ref([naechster(5), naechster(6)])
const busy = ref(false)

async function speichern() {
  busy.value = true
  try {
    if (art.value === 'fest') {
      const t = await api.put('/api/termin', { termin: `${wann.value}:00`, notiz: notiz.value })
      ui.toast('Termin gespeichert', 'ok')
      ui.changed()
      emit('saved', t)
    } else {
      let u = null
      for (const o of [...new Set(optionen.value.filter(Boolean))]) {
        u = await api.post('/api/termin/umfrage', { termin: `${o}:00`, notiz: notiz.value })
      }
      ui.toast('Umfrage gestartet – jetzt können alle abstimmen', 'ok')
      ui.changed()
      emit('umfrage', u)
    }
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
      <div class="arten" role="radiogroup" aria-label="Wie finden wir den Termin?">
        <button type="button" role="radio" :aria-checked="art === 'fest'" :class="{ aktiv: art === 'fest' }" @click="art = 'fest'">
          <Icon name="kalender" :size="15" /> Fester Termin
        </button>
        <button type="button" role="radio" :aria-checked="art === 'umfrage'" :class="{ aktiv: art === 'umfrage' }" @click="art = 'umfrage'">
          <Icon name="umfrage" :size="15" /> Abstimmen lassen
        </button>
      </div>

      <label v-if="art === 'fest'">
        <span>Wann? <em class="muted">(deutsche Zeit)</em></span>
        <input v-model="wann" type="datetime-local" required />
      </label>
      <fieldset v-else class="optionen">
        <legend>Welche Termine stehen zur Wahl? <em class="muted">(deutsche Zeit)</em></legend>
        <div v-for="(o, i) in optionen" :key="i" class="option">
          <input v-model="optionen[i]" type="datetime-local" :aria-label="`Termin ${i + 1}`" required />
          <button v-if="optionen.length > 1" type="button" class="ghost small" :aria-label="`Termin ${i + 1} entfernen`" @click="optionen.splice(i, 1)">
            <Icon name="x" :size="14" />
          </button>
        </div>
        <button v-if="optionen.length < 8" type="button" class="small ghost mehr" @click="optionen.push(naechster(optionen.length % 2 ? 6 : 5))">
          <Icon name="plus" :size="14" /> Weiterer Termin
        </button>
        <p class="muted hinweis">Alle stimmen mit Ja, Vielleicht oder Nein ab. Wer festlegt, übernimmt die Antworten als Zusagen.</p>
      </fieldset>

      <label>
        <span>Wo? <em class="muted">(optional)</em></span>
        <input v-model="notiz" maxlength="80" placeholder="z. B. bei Marc oder online im Kino" />
      </label>
      <div class="row">
        <button v-if="art === 'fest' && termin?.termin" type="button" class="ghost danger" @click="entfernen">Termin entfernen</button>
        <span class="spacer"></span>
        <button type="button" @click="emit('close')">Abbrechen</button>
        <button class="primary" :disabled="busy || (art === 'fest' ? !wann : !optionen.some(Boolean))">
          {{ art === 'fest' ? 'Speichern' : 'Umfrage starten' }}
        </button>
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
.arten { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; padding: 3px; background: var(--bg); border: 1px solid var(--line); border-radius: 10px; }
.arten button { justify-content: center; border: none; background: none; color: var(--muted); font-size: 0.85rem; }
.arten button.aktiv { background: var(--bg-raised); color: var(--text); font-weight: 600; box-shadow: inset 0 -2px 0 var(--accent); }
.optionen { border: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.45rem; font-size: 0.85rem; }
.optionen legend { padding: 0; margin-bottom: 0.3rem; }
.option { display: flex; gap: 0.4rem; align-items: center; }
.option input { flex: 1; }
.mehr { align-self: flex-start; }
.hinweis { margin: 0.2rem 0 0; font-size: 0.78rem; }
</style>