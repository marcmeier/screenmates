<script>
// Open dialogs, innermost last: keys always go to the topmost one.
const offen = []
</script>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

// Accessible dialog: Escape closes, focus moves in and is restored afterwards,
// Tab stays inside, and the page behind doesn't scroll. Keys are handled on the
// window, not on the dialog: content that re-renders can drop the focus to
// <body>, and Escape must still close the dialog then.
const props = defineProps({
  label: { type: String, required: true },
  width: { type: String, default: '460px' },
  dismissable: { type: Boolean, default: true },
})
const emit = defineEmits(['close'])
const box = ref(null)
let previous = null
const ich = Symbol('modal')
const obenauf = () => offen.at(-1) === ich

const FOCUSABLE = 'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'

function onKey(e) {
  if (!obenauf() || !box.value) return
  if (e.key === 'Escape' && props.dismissable) {
    e.stopPropagation()
    emit('close')
  }
  if (e.key === 'Tab') {
    const els = [...box.value.querySelectorAll(FOCUSABLE)]
    if (!els.length) return
    const [first, last] = [els[0], els[els.length - 1]]
    if (!box.value.contains(document.activeElement)) {
      ;(e.shiftKey ? last : first).focus() // focus fell out (e.g. to <body>): bring it back
      e.preventDefault()
    } else if (e.shiftKey && document.activeElement === first) {
      last.focus()
      e.preventDefault()
    } else if (!e.shiftKey && document.activeElement === last) {
      first.focus()
      e.preventDefault()
    }
  }
}

onMounted(async () => {
  offen.push(ich)
  window.addEventListener('keydown', onKey)
  previous = document.activeElement
  document.body.style.overflow = 'hidden'
  await nextTick()
  const auto = box.value.querySelector('[autofocus]') || box.value.querySelector(FOCUSABLE)
  auto?.focus()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  offen.splice(offen.indexOf(ich), 1)
  if (!offen.length) document.body.style.overflow = ''
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
