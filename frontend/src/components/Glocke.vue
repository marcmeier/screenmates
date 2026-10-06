<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { vorWann } from '../format'
import Icon from './Icon.vue'

// The bell: what screenmates told you lately, also without push. The count comes with the live poll.
defineProps({ schmal: { type: Boolean, default: false } })
const app = useApp()
const offen = ref(false)
const eintraege = ref([])
const box = ref(null)

async function umschalten() {
  offen.value = !offen.value
  if (!offen.value) return
  const r = await api.get('/api/glocke')
  eintraege.value = r.eintraege
  if (r.ungelesen) {
    await api.post('/api/glocke/gelesen', undefined, { quiet: true }).catch(() => {})
    app.glocke = 0
  }
}
function oeffnen(e) {
  offen.value = false
  if (e.url) location.hash = new URL(e.url, location.origin).hash
}
const draussen = (e) => box.value && !box.value.contains(e.target) && (offen.value = false)
onMounted(() => document.addEventListener('click', draussen))
onBeforeUnmount(() => document.removeEventListener('click', draussen))
</script>

<template>
  <div ref="box" class="glocke" :class="{ schmal }">
    <button
      class="nav small knopf"
      :aria-expanded="offen"
      :aria-label="app.glocke ? `Benachrichtigungen, ${app.glocke} neu` : 'Benachrichtigungen'"
      :title="schmal ? 'Benachrichtigungen' : undefined"
      @click.stop="umschalten"
    >
      <Icon name="glocke" :size="16" />
      <span class="label">Benachrichtigungen</span>
      <span v-if="app.glocke" class="zahl">{{ app.glocke > 9 ? '9+' : app.glocke }}</span>
    </button>
    <div v-if="offen" class="liste panel" role="dialog" aria-label="Benachrichtigungen">
      <p v-if="!eintraege.length" class="muted leer">Noch nichts – hier landet, was screenmates dir mitteilt.</p>
      <button v-for="e in eintraege" :key="e.id" class="eintrag" :class="{ neu: e.neu }" @click="oeffnen(e)">
        <strong>{{ e.titel }}</strong>
        <span v-if="e.text" class="muted">{{ e.text }}</span>
        <time class="muted" :datetime="e.am">{{ vorWann(e.am) }}</time>
      </button>
    </div>
  </div>
</template>

<style scoped>
.glocke { position: relative; }
.knopf { width: 100%; border: none; background: none; text-align: left; font: inherit; cursor: pointer; }
.zahl { margin-left: auto; font-size: 0.68rem; font-weight: 700; color: #fff; background: var(--accent); border-radius: 999px; padding: 0 6px; }
.schmal .knopf { justify-content: center; }
.schmal .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.schmal .zahl { position: absolute; top: 0; right: 10px; margin: 0; }
/* Fixed, beside the sidebar: inside it the sidebar's own scrolling would cut it off. */
.liste {
  position: fixed; left: calc(var(--sidebar) + 0.6rem); bottom: 1rem; z-index: 40; width: 360px; max-height: 70vh; overflow-y: auto;
  padding: 0.4rem; display: flex; flex-direction: column; gap: 2px; box-shadow: var(--shadow);
}
.schmal .liste { left: calc(72px + 0.6rem); }
.leer { font-size: 0.85rem; padding: 0.8rem; margin: 0; }
.eintrag {
  display: flex; flex-direction: column; align-items: flex-start; gap: 0.15rem; padding: 0.6rem 0.7rem; border: none; border-radius: 8px;
  background: none; text-align: left; font-size: 0.85rem; position: relative;
}
.eintrag:hover { background: var(--bg-raised); }
.eintrag.neu::before { content: ''; position: absolute; left: 0; top: 0.9rem; width: 3px; height: 1rem; border-radius: 2px; background: var(--accent); }
.eintrag time { font-size: 0.72rem; }
@media (max-width: 860px) {
  .knopf { width: auto; padding: 0.4rem; height: auto; }
  .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .zahl { position: absolute; top: -2px; right: -4px; }
  .liste, .schmal .liste { left: auto; right: 0.6rem; bottom: auto; top: 3.6rem; width: min(360px, 94vw); }
}
</style>