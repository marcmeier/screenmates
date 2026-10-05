<script setup>
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, ref, watch } from 'vue'
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
const konto = ref({ kofi: '', paypal: '' }) // account names while editing the donation section
const qr = ref({}) // key -> SVG of the account link, drawn here in the browser
const TITEL = { spenden: 'Unterstützen', impressum: 'Impressum', datenschutz: 'Datenschutz' }
const HINWEIS = {
  spenden: 'Wofür das Geld gedacht ist (Server, Domain …).',
  impressum: 'Name und ladungsfähige Anschrift, Kontakt (E-Mail). Leer lassen, wenn keins nötig ist.',
  datenschutz: 'Welche Daten screenmates speichert, wer sie sieht, wie man sie löschen lässt.',
}
const KONTO = { kofi: 'Ko-fi-Name', paypal: 'PayPal.me-Name' }

async function laden() {
  daten.value = await api.get('/api/ueber')
}
onMounted(laden)
const html = (md) => DOMPurify.sanitize(marked.parse(md || ''))
const konten = computed(() => Object.entries(daten.value?.konten || {}))
const gefuellt = (k) => daten.value.texte[k] || (k === 'spenden' && konten.value.length)
const sichtbar = computed(() => Object.keys(TITEL).filter((k) => gefuellt(k) || app.admin))

// The QR code library is only loaded when there is something to draw.
watch(konten, async (liste) => {
  if (!liste.length) return
  const { default: QRCode } = await import('qrcode')
  const svgs = {}
  for (const [k, { url }] of liste) svgs[k] = await QRCode.toString(url, { type: 'svg', margin: 2 })
  qr.value = svgs
})

function start(k) {
  bearbeiten.value = k
  entwurf.value = daten.value.texte[k]
  konto.value = { kofi: daten.value.konten.kofi?.name || '', paypal: daten.value.konten.paypal?.name || '' }
}
async function speichern() {
  await api.put(`/api/admin/seiten/${bearbeiten.value}`, { text: entwurf.value })
  if (bearbeiten.value === 'spenden') {
    for (const k of Object.keys(KONTO)) await api.put(`/api/admin/seiten/${k}`, { text: konto.value[k] })
  }
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
        <div v-if="k === 'spenden'" class="row konto-felder">
          <label v-for="(label, key) in KONTO" :key="key" class="field">
            {{ label }}
            <input v-model="konto[key]" placeholder="Name oder Link, leer = aus" />
          </label>
        </div>
        <div class="row">
          <button class="primary small">Speichern</button>
          <button type="button" class="ghost small" @click="bearbeiten = null">Abbrechen</button>
        </div>
      </form>
      <template v-else-if="gefuellt(k)">
        <!-- eslint-disable-next-line vue/no-v-html -- sanitised with DOMPurify -->
        <div v-if="daten.texte[k]" class="md" v-html="html(daten.texte[k])"></div>
        <div v-if="k === 'spenden' && konten.length" class="konten">
          <div v-for="[key, c] in konten" :key="key" class="konto">
            <!-- eslint-disable-next-line vue/no-v-html -- SVG drawn by the qrcode library from our own link -->
            <div v-if="qr[key]" class="qr" role="img" :aria-label="`QR-Code für ${c.label}`" v-html="qr[key]"></div>
            <a :href="c.url" target="_blank" rel="noopener" class="button small"><Icon name="herz" :size="14" /> {{ c.label }}</a>
            <small class="muted">{{ c.url.replace('https://', '') }}</small>
          </div>
        </div>
      </template>
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
.konto-felder { margin-bottom: 0.8rem; }
.konto-felder .field { flex: 1; }
.md :deep(h1), .md :deep(h2), .md :deep(h3) { font-size: 1rem; margin: 1rem 0 0.4rem; }
.md :deep(p), .md :deep(li) { font-size: 0.9rem; }
.md :deep(a) { color: var(--accent); }
.konten { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.8rem; }
.konto { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.konto small { font-size: 0.75rem; }
/* white quiet zone so every phone camera reads it, whatever the colour scheme */
.qr { width: 140px; height: 140px; background: #fff; border-radius: 8px; }
.qr :deep(svg) { display: block; width: 100%; height: 100%; }
/* on a phone there is nothing to scan with: the button is enough */
@media (max-width: 640px) {
  .qr { display: none; }
  .konto { flex-direction: row; }
  .konto small { display: none; }
}
</style>
