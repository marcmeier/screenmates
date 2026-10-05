<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// About screenmates: version, source, donations, imprint and privacy notice.
// Reachable without an invitation; admins write the texts right here.
const app = useApp()
const ui = useUi()
const daten = ref(null)
const bearbeiten = ref(null) // key being edited
const entwurf = ref('')
const TITEL = { spenden: 'Unterstützen', impressum: 'Impressum', datenschutz: 'Datenschutz' }
const HINWEIS = {
  spenden: 'Zum Beispiel Links zu PayPal, Ko-fi oder GitHub Sponsors – und wofür das Geld gedacht ist (Server, Domain …).',
  impressum: 'Name und ladungsfähige Anschrift, Kontakt (E-Mail). Leer lassen, wenn keins nötig ist.',
  datenschutz: 'Welche Daten screenmates speichert, wer sie sieht, wie man sie löschen lässt.',
}

async function laden() {
  daten.value = await api.get('/api/ueber')
}
onMounted(laden)
const html = (md) => DOMPurify.sanitize(marked.parse(md || ''))
const sichtbar = computed(() => Object.keys(TITEL).filter((k) => daten.value?.texte[k] || app.admin))

function start(k) {
  bearbeiten.value = k
  entwurf.value = daten.value.texte[k]
}
async function speichern() {
  await api.put(`/api/admin/seiten/${bearbeiten.value}`, { text: entwurf.value })
  bearbeiten.value = null
  await laden()
  ui.toast('Gespeichert', 'ok')
}
</script>

<template>
  <div v-if="daten" class="ueber">
    <section class="panel">
      <h2>screen<span class="akzent">mates</span> <small class="muted">Version {{ daten.version }}</small></h2>
      <p>Filmabende mit Freunden planen, gemeinsam schauen und darüber reden. Freie Software – der Quellcode liegt offen.</p>
      <a :href="daten.repo" target="_blank" rel="noopener" class="button small"><Icon name="extern" :size="14" /> Quellcode auf GitHub</a>
    </section>
    <section v-for="k in sichtbar" :id="k" :key="k" class="panel">
      <div class="kopf">
        <h2>{{ TITEL[k] }}</h2>
        <button v-if="app.admin && bearbeiten !== k" class="ghost small" @click="start(k)"><Icon name="stift" :size="14" /> Bearbeiten</button>
      </div>
      <form v-if="bearbeiten === k" @submit.prevent="speichern">
        <p class="muted">{{ HINWEIS[k] }} Markdown geht.</p>
        <textarea v-model="entwurf" rows="10" :aria-label="`${TITEL[k]} (Markdown)`"></textarea>
        <div class="row">
          <button class="primary small">Speichern</button>
          <button type="button" class="ghost small" @click="bearbeiten = null">Abbrechen</button>
        </div>
      </form>
      <!-- eslint-disable-next-line vue/no-v-html -- sanitised with DOMPurify -->
      <div v-else-if="daten.texte[k]" class="md" v-html="html(daten.texte[k])"></div>
      <p v-else class="muted">Noch leer – nur Admins sehen diesen Abschnitt.</p>
    </section>
  </div>
</template>

<style scoped>
.ueber { display: flex; flex-direction: column; gap: 1.2rem; }
h2 { margin: 0 0 0.6rem; font-size: 1.1rem; }
h2 small { font-weight: 400; font-size: 0.8rem; margin-left: 0.4rem; }
.akzent { color: var(--accent); }
p { font-size: 0.9rem; }
.kopf { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; }
textarea { width: 100%; font: inherit; font-size: 0.85rem; margin-bottom: 0.6rem; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) { font-size: 1rem; margin: 1rem 0 0.4rem; }
.md :deep(p), .md :deep(li) { font-size: 0.9rem; }
.md :deep(a) { color: var(--accent); }
</style>
