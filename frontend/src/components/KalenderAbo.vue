<script setup>
import { t } from '../i18n'
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// Your calendar app subscribes to the next movie nights of all your groups. The link
// carries a personal secret – calendar apps can't log in – so it can be renewed.
const ui = useUi()
const pfad = ref(undefined)

onMounted(async () => (pfad.value = (await api.get('/api/kalender')).pfad))
const https = computed(() => (pfad.value ? `${location.origin}${pfad.value}` : ''))
const webcal = computed(() => https.value.replace(/^https?:/, 'webcal:'))

async function erstellen(neu = false) {
  if (neu && !confirm(t('kalenderabo.neuenLinkErstellenDer'))) return
  pfad.value = (await api.post('/api/kalender')).pfad
}
async function abschalten() {
  if (!confirm(t('kalenderabo.kalenderAboAbschaltenDer'))) return
  pfad.value = (await api.del('/api/kalender')).pfad
}
async function kopieren() {
  try {
    await navigator.clipboard.writeText(https.value)
    ui.toast(t('kalenderabo.linkKopiert'), 'ok')
  } catch {
    ui.toast(t('kalenderabo.kopierenNichtErlaubtMarkier'), 'error')
  }
}
</script>

<template>
  <section class="panel">
    <h2><Icon name="kalender" :size="18" /> {{ $t('kalenderabo.kalenderAbo') }}</h2>
    <p class="muted">
      {{ $t('kalenderabo.dieNaechstenFilmabendeAll') }}
    </p>
    <template v-if="pfad">
      <div class="row link">
        <input :value="https" readonly :aria-label="$t('kalenderabo.kalenderLink')" @focus="$event.target.select()" />
        <button class="small" @click="kopieren"><Icon name="kopieren" :size="14" /> {{ $t('kalenderabo.kopieren') }}</button>
        <a class="button small" :href="webcal"><Icon name="extern" :size="14" /> {{ $t('kalenderabo.imKalenderOeffnen') }}</a>
      </div>
      <p class="muted klein">
        {{ $t('kalenderabo.googleKalenderWeitereKalender') }}
      </p>
      <div class="row">
        <button class="small ghost" @click="erstellen(true)"><Icon name="sync" :size="14" /> {{ $t('kalenderabo.neuerLink') }}</button>
        <button class="small ghost danger" @click="abschalten">{{ $t('kalenderabo.abschalten') }}</button>
      </div>
    </template>
    <button v-else-if="pfad === null" class="small" @click="erstellen()"><Icon name="plus" :size="14" /> {{ $t('kalenderabo.kalenderLinkErstellen') }}</button>
  </section>
</template>

<style scoped>
h2 { margin: 0 0 0.4rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem; }
p { margin: 0 0 0.8rem; font-size: 0.9rem; }
.klein { font-size: 0.8rem; margin-top: 0.7rem; }
.link input { flex: 1; min-width: 14rem; font-size: 0.8rem; font-family: ui-monospace, monospace; }
a.button.small { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
</style>