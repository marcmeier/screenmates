<script setup>
import { computed, onMounted, ref } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import Icon from '../Icon.vue'

const app = useApp()
const ui = useUi()
const text = ref('')
const updated = ref(null)
const draft = ref('')
const editing = ref(false)
const saving = ref(false)

onMounted(async () => {
  const r = await api.get('/api/info')
  text.value = r.text
  updated.value = r.updated_at
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
    const r = await api.put('/api/info', { text: draft.value })
    text.value = r.text
    updated.value = r.updated_at
    editing.value = false
    ui.toast('Info gespeichert', 'ok')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Info</h1>
        <p v-if="updated">Zuletzt geändert {{ vorWann(updated) }}</p>
      </div>
      <button v-if="app.host && !editing" @click="edit"><Icon name="stift" :size="16" /> Bearbeiten</button>
    </header>

    <div v-if="editing" class="editor">
      <label class="field">Markdown
        <textarea v-model="draft" rows="18" maxlength="20000" autofocus></textarea>
      </label>
      <div class="field">
        Vorschau
        <div class="panel prose preview" v-html="html"></div>
      </div>
      <div class="row">
        <button class="primary" :disabled="saving" @click="save">Speichern</button>
        <button class="ghost" @click="editing = false">Abbrechen</button>
      </div>
    </div>
    <div v-else-if="text" class="prose" v-html="html"></div>
    <div v-else class="empty">
      <strong>Noch keine Infos</strong>
      Hier kann der Host Regeln, Termine oder den Snack-Plan hinterlegen.
    </div>
  </div>
</template>

<style scoped>
.editor { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; }
.editor textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85rem; min-height: 380px; }
.preview { min-height: 380px; overflow: auto; color: var(--text); font-size: 0.92rem; }
.editor .row { grid-column: 1 / -1; }
@media (max-width: 900px) { .editor { grid-template-columns: 1fr; } }
</style>
