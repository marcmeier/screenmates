<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import Icon from './Icon.vue'

// Back to the top of a long list: shows once you've scrolled about one and a half screens down.
const sichtbar = ref(false)
let rahmen = 0
function pruefen() {
  cancelAnimationFrame(rahmen)
  rahmen = requestAnimationFrame(() => (sichtbar.value = window.scrollY > window.innerHeight * 1.5))
}
function hoch() {
  const ruhig = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  window.scrollTo({ top: 0, behavior: ruhig ? 'auto' : 'smooth' })
}
onMounted(() => {
  window.addEventListener('scroll', pruefen, { passive: true })
  pruefen()
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', pruefen)
  cancelAnimationFrame(rahmen)
})
</script>

<template>
  <Transition name="hoch">
    <button v-if="sichtbar" class="nach-oben" :aria-label="$t('nachoben.nachOben')" :title="$t('nachoben.nachOben2')" @click="hoch">
      <Icon name="pfeil" :size="20" />
    </button>
  </Transition>
</template>

<style scoped>
.nach-oben {
  position: fixed; z-index: 40; right: max(1.2rem, env(safe-area-inset-right)); bottom: max(1.2rem, env(safe-area-inset-bottom));
  width: 46px; height: 46px; padding: 0; justify-content: center; border-radius: 50%;
  background: var(--bg-raised); border: 1px solid var(--line); color: var(--text); box-shadow: var(--shadow);
}
@media (max-width: 860px) { .nach-oben { bottom: calc(5.2rem + env(safe-area-inset-bottom)); } }
.nach-oben:hover { border-color: var(--accent); color: var(--accent); }
.nach-oben svg { transform: rotate(90deg); }
.hoch-enter-active, .hoch-leave-active { transition: opacity 0.2s, transform 0.2s; }
.hoch-enter-from, .hoch-leave-to { opacity: 0; transform: translateY(10px); }
@media (prefers-reduced-motion: reduce) { .hoch-enter-active, .hoch-leave-active { transition: none; } }
</style>