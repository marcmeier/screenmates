<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import { aboHier, ausschalten, einschalten, installiert, istIos, pushMoeglich } from '../push'
import Icon from './Icon.vue'

// Push notifications: switch them on per device, choose the kinds (for all your devices).
const ui = useUi()
const zustand = ref(null) // { schluessel, arten: [{ key, text, an }], geraete }
const hier = ref(false) // this device is subscribed
const busy = ref(false)
const moeglich = pushMoeglich()
const blockiert = ref(moeglich && Notification.permission === 'denied')
// iPhones and iPads only get web notifications in the app added to the home screen.
const iosOhneApp = istIos() && !installiert()

onMounted(async () => {
  zustand.value = await api.get('/api/push')
  hier.value = !!(await aboHier().catch(() => null))
})

async function an() {
  busy.value = true
  try {
    zustand.value = await einschalten(zustand.value.schluessel)
    hier.value = true
    ui.toast('Benachrichtigungen sind an', 'ok')
  } catch (e) {
    blockiert.value = Notification.permission === 'denied'
    if (e.status === undefined) ui.toast(e.message, 'error', 7000)
  } finally {
    busy.value = false
  }
}

async function aus() {
  busy.value = true
  try {
    zustand.value = (await ausschalten()) || zustand.value
    hier.value = false
    ui.toast('Auf diesem Gerät gibt es keine Benachrichtigungen mehr')
  } finally {
    busy.value = false
  }
}

async function waehlen(art, wert) {
  zustand.value = await api.put('/api/push/arten', { arten: { [art.key]: wert } })
}

async function testen() {
  const r = await api.post('/api/push/test')
  ui.toast(`Test an ${r.geraete} ${r.geraete === 1 ? 'Gerät' : 'Geräte'} geschickt`, 'ok')
}

const geraeteText = computed(() => {
  const n = zustand.value?.geraete ?? 0
  return n ? `An auf ${n} ${n === 1 ? 'Gerät' : 'Geräten'}` : 'Noch auf keinem Gerät an'
})
</script>

<template>
  <section class="panel">
    <h2><Icon name="glocke" :size="18" /> Benachrichtigungen</h2>
    <p class="muted">
      Erfahre auch bei geschlossener App, wenn ein Termin steht, die Kiste aufgeht oder das Kino live ist.
      Für Dinge, die gerade passieren, meldet sich screenmates nur, wenn du die App nicht offen hast.
    </p>

    <p v-if="!moeglich && iosOhneApp" class="notice">
      Auf dem iPhone und iPad: Öffne screenmates in Safari, tippe auf <strong>Teilen → Zum Home-Bildschirm</strong> und
      starte screenmates von dort. Dann kannst du Benachrichtigungen hier einschalten.
    </p>
    <p v-else-if="!moeglich" class="notice">Dieser Browser kann keine Benachrichtigungen empfangen.</p>
    <template v-else-if="zustand">
      <div class="row">
        <span class="chip" :class="{ ok: hier }"><Icon name="glocke" :size="13" /> {{ hier ? 'Auf diesem Gerät an' : 'Auf diesem Gerät aus' }}</span>
        <button v-if="!hier" class="primary small" :disabled="busy || blockiert" @click="an">Auf diesem Gerät einschalten</button>
        <button v-else class="small" :disabled="busy" @click="aus">Ausschalten</button>
        <button v-if="zustand.geraete" class="small ghost" @click="testen">Test schicken</button>
        <span class="spacer"></span>
        <span class="muted klein">{{ geraeteText }}</span>
      </div>
      <p v-if="blockiert" class="notice klein">
        Der Browser blockiert Benachrichtigungen für screenmates. Erlaube sie in den Website-Einstellungen (Schloss-Symbol
        neben der Adresse) und lade die Seite neu.
      </p>
    </template>

    <template v-if="zustand && moeglich">
      <h3>Worüber?</h3>
      <ul class="arten">
        <li v-for="a in zustand.arten" :key="a.key">
          <label>
            <input type="checkbox" :checked="a.an" @change="waehlen(a, $event.target.checked)" />
            <span>{{ a.text }}</span>
          </label>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
h3 { margin: 1.1rem 0 0.5rem; font-size: 0.95rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.klein { font-size: 0.8rem; }
.chip.ok { color: var(--ok); border-color: var(--ok); }
.notice.klein { margin-top: 0.8rem; }
.arten { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.35rem 1rem; }
.arten label { display: flex; align-items: center; gap: 0.55rem; font-size: 0.88rem; cursor: pointer; }
.arten input { width: 1.05rem; height: 1.05rem; accent-color: var(--accent); flex: none; }
</style>