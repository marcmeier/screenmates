<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

// Accessible dialog: Escape closes, focus moves in and is restored afterwards,
// Tab stays inside, and the page behind doesn't scroll.
const props = defineProps({
  label: { type: String, required: true },
  width: { type: String, default: '460px' },
  dismissable: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])
const box = ref(null)
let previous = null

const FOCUSABLE = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

function onKey(e) {
  if (e.key === 'Escape' && props.dismissable) {
    e.stopPropagation()
    emit('close')
  }
  if (e.key === 'Tab') {
    const els = [...box.value.querySelectorAll(FOCUSABLE)]
    if (!els.length) return
    const [first, last] = [els[0], els[els.length - 1]]
    if (e.shiftKey && document.activeElement === first) {
      last.focus()
      e.preventDefault()
    } else if (!e.shiftKey && document.activeElement === last) {
      first.focus()
      e.preventDefault()
    }
  }
}

onMounted(async () => {
  previous = document.activeElement
  document.body.style.overflow = 'hidden'
  await nextTick()
  const auto = box.value.querySelector('[autofocus]') || box.value.querySelector(FOCUSABLE)
  auto?.focus()
})
onBeforeUnmount(() => {
  document.body.style.overflow = ''
  previous?.focus?.()
})
</script>

<template>
  <Teleport to="body">
    <div class="backdrop" @mousedown.self="dismissable && emit('close')">
      <div
        ref="box"
        class="dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="label"
        :style="{ width: `min(${width}, 94vw)` }"
        @keydown="onKey"
      >
        <slot />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.backdrop {
  position: fixed; inset: 0; z-index: 60;
  background: rgba(4, 4, 7, 0.82); backdrop-filter: blur(3px);
  display: grid; place-items: center; padding: 1rem;
  animation: fade 0.15s ease-out;
}
.dialog {
  background: var(--bg-soft); border: 1px solid var(--line); border-radius: 14px;
  max-height: 92vh; overflow: auto; box-shadow: var(--shadow);
  animation: pop 0.18s ease-out;
}
@keyframes fade { from { opacity: 0; } }
@keyframes pop { from { opacity: 0; transform: translateY(8px) scale(0.98); } }
</style>
