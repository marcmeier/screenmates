<script setup>
import { useUi } from '../stores/ui'
const ui = useUi()
</script>

<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <button v-for="t in ui.toasts" :key="t.id" class="toast" :class="t.kind" @click="ui.dismiss(t.id)">
        {{ t.text }}
      </button>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toasts {
  position: fixed; right: 1.2rem; bottom: 1.2rem; z-index: 80;
  display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end;
  max-width: min(420px, calc(100vw - 2rem));
}
.toast {
  background: var(--bg-raised); border: 1px solid var(--line); border-left: 3px solid var(--muted);
  box-shadow: var(--shadow); padding: 0.7rem 1rem; text-align: left; font-size: 0.88rem;
}
.toast.ok { border-left-color: var(--ok); }
.toast.error { border-left-color: var(--accent); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(20px); }
.toast-enter-active, .toast-leave-active { transition: all 0.2s ease; }
@media (max-width: 860px) { .toasts { bottom: calc(5.2rem + env(safe-area-inset-bottom)); } }
</style>
