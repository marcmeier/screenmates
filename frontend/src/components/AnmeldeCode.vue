<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { t } from '../i18n'
import { datumFmt } from '../format'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// A one-time login code for another device: as text to type, as a link and as a QR code.
// `url` makes the code (your own, or an admin's for someone else).
const props = defineProps({
  url: { type: String, required: true },
  label: { type: String, required: true },
  name: { type: String, default: '' }, // set when it's someone else's code: a warning to pass it on carefully
  sofort: { type: Boolean, default: false },
})
const ui = useUi()
const daten = ref(null)
const qr = ref('')
const busy = ref(false)

const link = () => location.origin + daten.value.path
const bis = () => datumFmt({ hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' }).format(new Date(daten.value.valid_until))

async function machen() {
  busy.value = true
  try {
    daten.value = await api.post(props.url)
    const { default: QRCode } = await import('qrcode')
    qr.value = await QRCode.toString(link(), { type: 'svg', margin: 2 })
  } finally {
    busy.value = false
  }
}
async function kopieren() {
  await navigator.clipboard.writeText(link())
  ui.toast(t('anmeldecode.kopiert'), 'ok')
}
onMounted(() => props.sofort && machen())
</script>

<template>
  <div class="anmeldecode">
    <button v-if="!daten" class="small" :disabled="busy" @click="machen"><Icon name="plus" :size="14" /> {{ label }}</button>
    <div v-else class="karte" role="group" :aria-label="$t('anmeldecode.code')">
      <!-- eslint-disable-next-line vue/no-v-html -- SVG drawn by the qrcode library from our own link -->
      <div class="qr" role="img" :aria-label="$t('anmeldecode.qr')" v-html="qr"></div>
      <div class="text">
        <span class="muted small">{{ $t('anmeldecode.code') }}</span>
        <output class="code">{{ daten.code }}</output>
        <p class="muted small">{{ $t('anmeldecode.text', { zeit: bis() }) }}</p>
        <p v-if="name" class="small warnung">{{ $t('anmeldecode.geheim', { name }) }}</p>
        <div class="row">
          <button class="small" @click="kopieren"><Icon name="kopieren" :size="13" /> {{ $t('anmeldecode.kopieren') }}</button>
          <button class="ghost small" :disabled="busy" @click="machen">{{ $t('anmeldecode.neu') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.karte { display: flex; gap: 1rem; align-items: flex-start; flex-wrap: wrap; margin-top: 0.4rem; }
.qr { width: 132px; height: 132px; background: #fff; border-radius: 8px; flex: none; }
.qr :deep(svg) { width: 100%; height: 100%; display: block; }
.text { flex: 1; min-width: 12rem; }
.code { display: block; font-family: 'JetBrains Mono Variable', ui-monospace, monospace; font-size: 1.6rem; font-weight: 700; letter-spacing: 0.08em; margin: 0.1rem 0 0.4rem; }
.text p { margin: 0 0 0.6rem; }
.warnung { color: var(--text); }
.small { font-size: 0.78rem; }
</style>
