<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

// A small ⓘ next to a term of ours (case, veto, host …): tap it for one or two sentences.
defineProps({ text: { type: String, required: true }, label: { type: String, required: true } })
const offen = ref(false)
const zu = () => (offen.value = false)
const taste = (e) => e.key === 'Escape' && zu()
onMounted(() => {
  document.addEventListener('click', zu)
  window.addEventListener('keydown', taste)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', zu)
  window.removeEventListener('keydown', taste)
})
</script>

<template>
  <span class="erklaerung" @click.stop>
    <button type="button" class="i" :aria-expanded="offen" :aria-label="$t('erklaerung.wasIst', { was: label })" @click="offen = !offen">i</button>
    <span v-if="offen" role="tooltip" class="blase">{{ text }}</span>
  </span>
</template>

<style scoped>
.erklaerung { position: relative; display: inline-flex; vertical-align: middle; margin-left: 0.3rem; text-transform: none; letter-spacing: normal; }
.i {
  width: 17px; height: 17px; padding: 0; border-radius: 50%; justify-content: center; font: italic 700 0.68rem/1 Georgia, serif;
  color: var(--muted); background: none; border: 1px solid var(--line);
}
.i:hover, .i[aria-expanded='true'] { color: var(--text); border-color: var(--accent); }
.blase {
  position: absolute; z-index: 60; top: calc(100% + 6px); left: -0.5rem; width: max-content; max-width: min(270px, 78vw);
  padding: 0.6rem 0.75rem; border-radius: 10px; background: var(--bg-raised); border: 1px solid var(--line);
  box-shadow: var(--shadow); color: var(--text); font-size: 0.82rem; font-weight: 400; line-height: 1.45; white-space: normal;
}
</style>
