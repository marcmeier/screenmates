<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// House rules, dates, snack plan: lives on the movie-night page where people
// look anyway. Everyone reads it, the host edits it in place.
const app = useApp()
const ui = useUi()
const text = ref('')
const draft = ref('')
const editing = ref(false)
const saving = ref(false)
const loaded = ref(false)

onMounted(async () => {
  text.value = (await api.get('/api/info')).text
  loaded.value = true
})

// Markdown is rendered, then sanitised: the info text is user content.
const html = computed(() => DOMPurify.sanitize(marked.parse(editing.value ? draft.value : text.value)))

function edit() {
  draft.value = text.value
  editing.value = true
}

async function save() {
  saving.value = true
  try {
    text.value = (await api.put('/api/info', { text: draft.value })).text
    editing.value = false
    ui.toast(t('infocard.infosGespeichert'), 'ok')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section v-if="loaded && (text || app.gruppenAdmin)" class="panel info">
    <div class="row head">
      <h2 class="section-title">{{ $t('infocard.titel') }}</h2>
      <span class="spacer"></span>
      <button v-if="app.gruppenAdmin && !editing" class="ghost small" :aria-label="text ? $t('infocard.infosBearbeiten') : $t('infocard.infosHinzufuegen')" @click="edit">
        <Icon :name="text ? 'stift' : 'plus'" :size="14" /> {{ text ? '' : $t('infocard.hinzufuegen') }}
      </button>
    </div>

    <template v-if="editing">
      <textarea v-model="draft" rows="10" maxlength="20000" autofocus :aria-label="$t('infocard.infosMarkdown')" placeholder="# Hausregeln&#10;- Handys in die Schale …"></textarea>
      <div v-if="draft" class="prose preview" v-html="html"></div>
      <div class="row actions">
        <button class="primary small" :disabled="saving" @click="save">{{ $t('infocard.speichern') }}</button>
        <button class="ghost small" @click="editing = false">{{ $t('infocard.abbrechen') }}</button>
      </div>
    </template>
    <div v-else-if="text" class="prose" v-html="html"></div>
    <p v-else class="muted">{{ $t('infocard.hierKoennenRegelnTermine') }}</p>
  </section>
</template>

<style scoped>
.info { margin-top: 1rem; }
.head .section-title { margin: 0; }
.head { margin-bottom: 0.4rem; }
.prose { font-size: 0.9rem; }
.prose :deep(h1) { font-size: 1.15rem; margin: 0.4em 0; }
.prose :deep(h2) { font-size: 1rem; }
.prose :deep(ul) { margin: 0.4em 0; }
textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; }
.preview { border-top: 1px solid var(--line); margin-top: 0.8rem; padding-top: 0.4rem; }
.actions { margin-top: 0.8rem; }
</style>
