<script setup>
import { ref, onMounted, computed } from 'vue'
import { api } from '../api'

const text = ref('')
const editing = ref(false)

async function load() { text.value = (await api.get('/api/info')).text || '' }
onMounted(load)

async function save() { await api.put('/api/info', { text: text.value }); editing.value = false }

// Minimal markdown: headings, bold, italics, line breaks.
const html = computed(() => text.value
  .replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/^### (.*)$/gm, '<h3>$1</h3>')
  .replace(/^## (.*)$/gm, '<h2>$1</h2>')
  .replace(/^# (.*)$/gm, '<h1>$1</h1>')
  .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
  .replace(/\*(.+?)\*/g, '<i>$1</i>')
  .replace(/\n/g, '<br/>'))
</script>

<template>
  <div>
    <div class="head">
      <h1>Info</h1>
      <button class="ghost" @click="editing = !editing">{{ editing ? 'Vorschau' : 'Bearbeiten' }}</button>
    </div>
    <textarea v-if="editing" v-model="text" rows="16" placeholder="Markdown …"></textarea>
    <div v-else class="rendered" v-html="html || '<p class=muted>Noch kein Info-Text.</p>'"></div>
    <button v-if="editing" class="primary" style="margin-top:1rem" @click="save">Speichern</button>
  </div>
</template>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
h1 { margin: 0; font-size: 1.5rem; }
.rendered { line-height: 1.6; max-width: 720px; }
textarea { max-width: 720px; }
</style>
