<script setup>
import { t } from '../i18n'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useUi } from '../stores/ui'
import { einladungsBild, einladungsText } from '../einladung'
import Icon from './Icon.vue'
import Modal from './Modal.vue'

// Invitation for the group chat: preview of the card, then share / save / copy.
const props = defineProps({
  termin: { type: Object, default: null },
  filme: { type: Array, default: () => [] },
  dabei: { type: Array, default: () => [] },
})
const emit = defineEmits(['close'])
const ui = useUi()

const text = einladungsText(props)
const blob = ref(null)
const vorschau = ref('')
const datei = () => new File([blob.value], 'filmabend.png', { type: 'image/png' })
const kannTeilen = typeof navigator.share === 'function'

onMounted(async () => {
  blob.value = await einladungsBild(props)
  if (blob.value) vorschau.value = URL.createObjectURL(blob.value)
})
onBeforeUnmount(() => vorschau.value && URL.revokeObjectURL(vorschau.value))

async function teilen() {
  try {
    // Phones: picture and text straight into WhatsApp, Signal & co.
    if (blob.value && navigator.canShare?.({ files: [datei()] })) await navigator.share({ files: [datei()], text })
    else await navigator.share({ text })
  } catch (e) {
    if (e.name !== 'AbortError') ui.toast(t('einladung.teilenHatNichtGeklappt'), 'error')
  }
}

async function kopieren() {
  try {
    await navigator.clipboard.writeText(text)
    ui.toast(t('einladung.einladungKopiert'), 'ok')
  } catch {
    ui.toast(t('einladung.kopierenNichtErlaubtMarkier'), 'error')
  }
}
</script>

<template>
  <Modal :label="$t('einladung.zumFilmabendEinladen')" width="560px" @close="emit('close')">
    <div class="einladung">
      <header class="row">
        <h2>{{ $t('einladung.einladen') }}</h2>
        <span class="spacer"></span>
        <button class="ghost" :aria-label="$t('einladung.schliessen')" @click="emit('close')"><Icon name="x" /></button>
      </header>

      <div class="karte">
        <img v-if="vorschau" :src="vorschau" :alt="$t('einladung.einladungskarte')" />
        <div v-else class="skeleton"></div>
      </div>
      <pre class="text">{{ text }}</pre>

      <div class="aktionen">
        <button v-if="kannTeilen" class="primary" :disabled="!blob" @click="teilen"><Icon name="teilen" :size="16" /> {{ $t('einladung.teilen') }}</button>
        <a class="button" :class="{ disabled: !vorschau }" :href="vorschau || undefined" download="filmabend.png">
          <Icon name="download" :size="16" /> {{ $t('einladung.bildSpeichern') }}
        </a>
        <button @click="kopieren"><Icon name="kopieren" :size="16" /> {{ $t('einladung.textKopieren') }}</button>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.einladung { padding: 1.2rem 1.4rem 1.4rem; display: flex; flex-direction: column; gap: 0.9rem; }
h2 { margin: 0; font-size: 1.15rem; }
.karte { display: grid; place-items: center; }
.karte img, .karte .skeleton { width: min(300px, 70vw); aspect-ratio: 4 / 5; border-radius: 12px; box-shadow: var(--shadow); }
.text { margin: 0; white-space: pre-wrap; font: inherit; font-size: 0.82rem; color: var(--muted); background: var(--bg-raised); border-radius: 8px; padding: 0.7rem 0.9rem; user-select: all; }
.aktionen { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
.aktionen .button { display: inline-flex; align-items: center; gap: 0.4rem; }
.aktionen .disabled { pointer-events: none; opacity: 0.5; }
</style>
