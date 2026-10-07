<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'
import Modal from './Modal.vue'

// Server admins only: clear out what testing left behind in the active group, area by area.
// What concerns the whole server is on the command line (python -m app.cli reset).
// The server backs up the database before it deletes anything.
const ui = useUi()
const stand = ref(null) // { gruppe: { id, name }, bereiche: [{ key, titel, text, anzahl }], bestaetigung, backups }
const gewaehlt = ref([])
const auftrag = ref(null) // { bereiche: [...], titel } while the confirmation is open
const wort = ref('')
const busy = ref(false)

const laden = async () => (stand.value = await api.get('/api/admin/reset'))
onMounted(laden)

const titel = (key) => stand.value.bereiche.find((b) => b.key === key)?.titel ?? key
function bestaetigen(bereiche) {
  wort.value = ''
  auftrag.value = { bereiche, liste: bereiche.map(titel) }
}
const passt = computed(() => wort.value.trim().toUpperCase() === stand.value?.bestaetigung)

async function ausfuehren() {
  busy.value = true
  try {
    const r = await api.post('/api/admin/reset', { bereiche: auftrag.value.bereiche, bestaetigung: wort.value })
    ui.toast(r.backup ? t('gefahrenzone.geloeschtMit', { datei: r.backup }) : t('gefahrenzone.geloescht'), 'ok', 6000)
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
    <h2 id="gefahr-titel"><Icon name="muell" :size="18" /> {{ $t('gefahrenzone.gefahrenzone') }}</h2>
    <template v-if="stand">
      <p class="muted">{{ $t('gefahrenzone.zumAufraeumen', { gruppe: stand.gruppe.name }) }}</p>
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
          <Icon name="muell" :size="15" /> {{ $t('gefahrenzone.ausgewaehltesLoeschen') }}
        </button>
      </div>

      <p class="muted klein">
        {{ $t('gefahrenzone.serverweit') }} <code>python -m app.cli reset</code>
      </p>

      <p v-if="stand.backups.length" class="muted klein">
        {{ $t('gefahrenzone.sicherungenImDatenordner') }} <code v-for="b in stand.backups" :key="b">{{ b }}</code>
      </p>
    </template>

    <Modal v-if="auftrag" :label="$t('gefahrenzone.wirklichLoeschen')" @close="auftrag = null">
      <form class="dialog" @submit.prevent="passt && ausfuehren()">
        <h2><Icon name="muell" /> {{ $t('gefahrenzone.wirklichLoeschen2') }}</h2>
        <p>{{ $t('gefahrenzone.geloeschtWirdIn', { gruppe: stand.gruppe.name }) }}</p>
        <ul>
          <li v-for="eintrag in auftrag.liste" :key="eintrag">{{ eintrag }}</li>
        </ul>
        <label>
          <span>{{ $t('gefahrenzone.bestaetigenMit', { wort: stand.bestaetigung }) }}</span>
          <input v-model="wort" autocomplete="off" autofocus :placeholder="stand.bestaetigung" :aria-label="$t('gefahrenzone.bestaetigung')" />
        </label>
        <div class="row">
          <span class="spacer"></span>
          <button type="button" @click="auftrag = null">{{ $t('gefahrenzone.abbrechen') }}</button>
          <button class="rot voll" :disabled="!passt || busy">{{ $t('gefahrenzone.endgueltigLoeschen') }}</button>
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
button.rot.voll { background: var(--accent); color: var(--on-accent); }
button.rot.voll:hover:not(:disabled) { background: var(--accent-hover); }

.klein { font-size: 0.75rem; margin: 1rem 0 0; }
.klein code { margin-right: 0.4rem; font-size: 0.72rem; }
.dialog { padding: 1.3rem 1.4rem; display: flex; flex-direction: column; gap: 0.8rem; }
.dialog h2 { margin: 0; }
.dialog p, .dialog ul { margin: 0; font-size: 0.9rem; }
.dialog ul { padding-left: 1.2rem; }
.dialog label { display: flex; flex-direction: column; gap: 0.35rem; font-size: 0.85rem; }
</style>