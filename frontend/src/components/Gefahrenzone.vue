<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import Modal from './Modal.vue'

// Server admins only: clear out what testing left behind – area by area, or everything
// back to a fresh start. The server backs up the database before it deletes anything.
const ui = useUi()
const stand = ref(null) // { bereiche: [{ key, titel, text, anzahl }], neustart, bestaetigung, backups }
const gewaehlt = ref([])
const auftrag = ref(null) // { bereiche: [...], titel } while the confirmation is open
const wort = ref('')
const busy = ref(false)

const laden = async () => (stand.value = await api.get('/api/admin/reset'))
onMounted(laden)

const titel = (key) => stand.value.bereiche.find((b) => b.key === key)?.titel ?? key
function bestaetigen(bereiche) {
  wort.value = ''
  auftrag.value = {
    bereiche,
    neustart: bereiche.includes('neustart'),
    liste: bereiche.includes('neustart') ? stand.value.bereiche.map((b) => b.titel) : bereiche.map(titel),
  }
}
const passt = computed(() => wort.value.trim().toUpperCase() === stand.value?.bestaetigung)

async function ausfuehren() {
  busy.value = true
  try {
    const r = await api.post('/api/admin/reset', { bereiche: auftrag.value.bereiche, bestaetigung: wort.value })
    ui.toast(`Gelöscht${r.backup ? ` – Sicherung: ${r.backup}` : ''}`, 'ok', 6000)
    auftrag.value = null
    gewaehlt.value = []
    // So much changed that the app starts afresh.
    setTimeout(() => window.location.reload(), 1200)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="panel gefahr" aria-labelledby="gefahr-titel">
    <h2 id="gefahr-titel"><Icon name="muell" :size="18" /> Gefahrenzone</h2>
    <p class="muted">
      Zum Aufräumen nach dem Testen, für alle Gruppen. Vor jedem Löschen sichert der Server die Datenbank
      (die letzten fünf bleiben liegen) – rückgängig machen geht nur über diese Sicherung.
    </p>

    <template v-if="stand">
      <ul class="bereiche">
        <li v-for="b in stand.bereiche" :key="b.key">
          <label>
            <input v-model="gewaehlt" type="checkbox" :value="b.key" :disabled="!b.anzahl" />
            <span>
              <strong>{{ b.titel }}</strong> <span class="zahl">{{ b.anzahl }}</span>
              <small class="muted">{{ b.text }}</small>
            </span>
          </label>
        </li>
      </ul>
      <div class="row">
        <button class="rot" :disabled="!gewaehlt.length" @click="bestaetigen(gewaehlt)">
          <Icon name="muell" :size="15" /> Ausgewähltes löschen
        </button>
      </div>

      <div class="neustart">
        <div>
          <strong>Alles neu</strong>
          <p class="muted">
            Leert alles oben und löscht zusätzlich alle anderen Namen ({{ stand.neustart }} Namen und Einladungen),
            mit ihren Bildern, Abos und Sitzungen. Es bleiben: du als Admin, die Gruppen, der Filmkatalog,
            die Über-Seite und die Einstellungen. Ideal, bevor du screenmates deinen Freunden zeigst.
          </p>
        </div>
        <button class="rot voll" @click="bestaetigen(['neustart'])"><Icon name="sync" :size="15" /> Alles neu starten</button>
      </div>

      <p v-if="stand.backups.length" class="muted klein">
        Sicherungen im Datenordner: <code v-for="b in stand.backups" :key="b">{{ b }}</code>
      </p>
    </template>

    <Modal v-if="auftrag" label="Wirklich löschen?" @close="auftrag = null">
      <form class="dialog" @submit.prevent="passt && ausfuehren()">
        <h2><Icon name="muell" /> Wirklich löschen?</h2>
        <p>Gelöscht wird für alle Gruppen:</p>
        <ul>
          <li v-for="t in auftrag.liste" :key="t">{{ t }}</li>
          <li v-if="auftrag.neustart"><strong>alle anderen Namen, Einladungen und Anträge</strong></li>
        </ul>
        <label>
          <span>Zum Bestätigen <strong>{{ stand.bestaetigung }}</strong> eintippen</span>
          <input v-model="wort" autocomplete="off" autofocus :placeholder="stand.bestaetigung" aria-label="Bestätigung" />
        </label>
        <div class="row">
          <span class="spacer"></span>
          <button type="button" @click="auftrag = null">Abbrechen</button>
          <button class="rot voll" :disabled="!passt || busy">Endgültig löschen</button>
        </div>
      </form>
    </Modal>
  </section>
</template>

<style scoped>
.gefahr { border-color: color-mix(in srgb, var(--accent) 55%, var(--line)); background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 7%, var(--bg-soft)), var(--bg-soft)); }
h2 { margin: 0 0 0.5rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; color: #ff6b6b; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.bereiche { list-style: none; margin: 0 0 0.9rem; padding: 0; display: flex; flex-direction: column; gap: 0.45rem; }
.bereiche label { display: flex; gap: 0.6rem; align-items: flex-start; cursor: pointer; font-size: 0.9rem; }
.bereiche input { width: 1.05rem; height: 1.05rem; margin-top: 0.15rem; accent-color: var(--accent); flex: none; }
.bereiche small { display: block; font-size: 0.78rem; }
.zahl { font-size: 0.72rem; font-weight: 700; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 0 6px; margin-left: 0.2rem; }
button.rot { border-color: var(--accent); color: #ff6b6b; background: transparent; }
button.rot:hover:not(:disabled) { background: var(--accent-soft); color: #fff; }
button.rot.voll { background: var(--accent); color: #fff; }
button.rot.voll:hover:not(:disabled) { background: var(--accent-hover); }
.neustart { display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-top: 1.2rem; padding-top: 1rem; border-top: 1px solid color-mix(in srgb, var(--accent) 35%, var(--line)); }
.neustart > div { flex: 1; min-width: 16rem; }
.neustart p { margin: 0.2rem 0 0; font-size: 0.84rem; }
.klein { font-size: 0.75rem; margin: 1rem 0 0; }
.klein code { margin-right: 0.4rem; font-size: 0.72rem; }
.dialog { padding: 1.3rem 1.4rem; display: flex; flex-direction: column; gap: 0.8rem; }
.dialog h2 { margin: 0; }
.dialog p, .dialog ul { margin: 0; font-size: 0.9rem; }
.dialog ul { padding-left: 1.2rem; }
.dialog label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.85rem; }
</style>