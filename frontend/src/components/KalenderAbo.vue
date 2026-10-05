<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// Your calendar app subscribes to the next movie nights of all your groups. The link
// carries a personal secret – calendar apps can't log in – so it can be renewed.
const ui = useUi()
const pfad = ref(undefined)

onMounted(async () => (pfad.value = (await api.get('/api/kalender')).pfad))
const https = computed(() => (pfad.value ? `${location.origin}${pfad.value}` : ''))
const webcal = computed(() => https.value.replace(/^https?:/, 'webcal:'))

async function erstellen(neu = false) {
  if (neu && !confirm('Neuen Link erstellen? Der alte hört sofort auf zu funktionieren.')) return
  pfad.value = (await api.post('/api/kalender')).pfad
}
async function abschalten() {
  if (!confirm('Kalender-Abo abschalten? Der Link hört sofort auf zu funktionieren.')) return
  pfad.value = (await api.del('/api/kalender')).pfad
}
async function kopieren() {
  try {
    await navigator.clipboard.writeText(https.value)
    ui.toast('Link kopiert', 'ok')
  } catch {
    ui.toast('Kopieren nicht erlaubt – markier den Link', 'error')
  }
}
</script>

<template>
  <section class="panel">
    <h2><Icon name="kalender" :size="18" /> Kalender-Abo</h2>
    <p class="muted">
      Die nächsten Filmabende all deiner Gruppen automatisch im Kalender – mit Ort, Filmen zur Wahl und Erinnerung.
      Ändert sich der Termin, zieht dein Kalender nach.
    </p>
    <template v-if="pfad">
      <div class="row link">
        <input :value="https" readonly aria-label="Kalender-Link" @focus="$event.target.select()" />
        <button class="small" @click="kopieren"><Icon name="kopieren" :size="14" /> Kopieren</button>
        <a class="button small" :href="webcal"><Icon name="extern" :size="14" /> Im Kalender öffnen</a>
      </div>
      <p class="muted klein">
        Google Kalender: „Weitere Kalender → Per URL“ und den Link einfügen. Apple und Outlook: „Im Kalender öffnen“.
        Der Link ist persönlich – wer ihn hat, sieht eure Termine.
      </p>
      <div class="row">
        <button class="small ghost" @click="erstellen(true)"><Icon name="sync" :size="14" /> Neuer Link</button>
        <button class="small ghost danger" @click="abschalten">Abschalten</button>
      </div>
    </template>
    <button v-else-if="pfad === null" class="small" @click="erstellen()"><Icon name="plus" :size="14" /> Kalender-Link erstellen</button>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.klein { font-size: 0.8rem; margin-top: 0.7rem; }
.link input { flex: 1; min-width: 14rem; font-size: 0.8rem; font-family: ui-monospace, monospace; }
a.button.small { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
</style>