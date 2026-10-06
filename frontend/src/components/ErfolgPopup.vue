<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useErfolge } from '../stores/erfolge'
import { navigate } from '../composables/useRoute'

// "Achievement unlocked" – one at a time, like on a console.
const erfolge = useErfolge()
const aktuell = computed(() => erfolge.popups[0] || null)
let timer = null

watch(
  aktuell,
  (e) => {
    clearTimeout(timer)
    if (e) timer = setTimeout(() => erfolge.weiter(), 5200)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(timer))

function oeffnen() {
  erfolge.weiter()
  navigate('profil')
}
</script>

<template>
  <Transition name="pop">
    <button v-if="aktuell" :key="aktuell.key" class="popup" :class="`stufe-${aktuell.stufe || 3}`" role="status" @click="oeffnen">
      <span class="medaille">{{ aktuell.zusammenfassung ? '🏆' : aktuell.emoji }}</span>
      <span class="text">
        <small>{{ aktuell.zusammenfassung ? $t('erfolgpopup.willkommenBeiDenErfolgen') : $t('erfolgpopup.erfolgFreigeschaltet') }}</small>
        <strong v-if="aktuell.zusammenfassung">{{ $t('erfolgpopup.zusammenfassungErfolgeFuerAlles', { zusammenfassung: aktuell.zusammenfassung }) }}</strong>
        <strong v-else>{{ aktuell.name }}</strong>
      </span>
      <span class="punkte">{{ aktuell.punkte }} P</span>
    </button>
  </Transition>
</template>

<style scoped>
.popup {
  position: fixed; left: 50%; bottom: 1.6rem; z-index: 60; transform: translateX(-50%);
  display: flex; align-items: center; gap: 0.9rem; padding: 0.6rem 1.1rem 0.6rem 0.6rem;
  min-width: min(380px, calc(100vw - 2rem)); max-width: calc(100vw - 2rem);
  background: linear-gradient(90deg, #15151b, #1d1d25); border: 1px solid var(--line); border-radius: 999px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.55); color: var(--text); text-align: left; cursor: pointer;
}
.medaille {
  width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center; font-size: 1.5rem; flex: none;
  background: var(--medaille); box-shadow: 0 0 0 3px var(--bg-soft), 0 0 18px var(--medaille);
  animation: glanz 1.2s ease-out;
}
.stufe-1 { --medaille: #b0703c; }
.stufe-2 { --medaille: #a9b3bd; }
.stufe-3 { --medaille: #e0a82e; }
.stufe-4 { --medaille: #7fd3e6; }
.text { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.text small { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
.text strong { font-size: 0.98rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.punkte { font-weight: 800; color: var(--gold); flex: none; }
@keyframes glanz { 0% { transform: scale(0.4) rotate(-30deg); } 60% { transform: scale(1.15) rotate(6deg); } 100% { transform: none; } }
.pop-enter-active, .pop-leave-active { transition: transform 0.35s cubic-bezier(0.2, 0.9, 0.3, 1.2), opacity 0.3s; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translate(-50%, 140%); }
@media (prefers-reduced-motion: reduce) {
  .medaille { animation: none; }
  .pop-enter-active, .pop-leave-active { transition: opacity 0.2s; }
  .pop-enter-from, .pop-leave-to { transform: translateX(-50%); }
}
</style>
