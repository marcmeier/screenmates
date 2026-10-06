<script setup>
import { useApp } from '../stores/app'
import { useRoute } from '../composables/useRoute'
import Icon from './Icon.vue'

// The way to "Neuigkeiten": the bell, with what's unread (the count comes with the live poll).
defineProps({ schmal: { type: Boolean, default: false } })
const app = useApp()
const route = useRoute()
</script>

<template>
  <a
    href="#/neuigkeiten"
    class="nav small glocke"
    :class="{ schmal, active: route.tab === 'neuigkeiten' }"
    :aria-label="app.glocke ? $t('glocke.neuigkeitenGlockeNeu', { glocke: app.glocke }) : $t('nav.neuigkeiten')"
    :title="schmal ? $t('nav.neuigkeiten') : undefined"
  >
    <Icon name="glocke" :size="16" />
    <span class="label">{{ $t('nav.neuigkeiten') }}</span>
    <span v-if="app.glocke" class="zahl">{{ app.glocke > 9 ? '9+' : app.glocke }}</span>
  </a>
</template>

<style scoped>
.glocke { position: relative; display: flex; align-items: center; gap: 0.7rem; height: 34px; padding: 0 0.8rem; border-radius: 9px; color: var(--muted); text-decoration: none; font-size: 0.85rem; }
.glocke:hover, .glocke.active { background: var(--bg-soft); color: var(--text); }
.zahl { margin-left: auto; font-size: 0.68rem; font-weight: 700; color: #fff; background: var(--accent); border-radius: 999px; padding: 0 6px; }
.schmal { justify-content: center; padding: 0; }
.schmal .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.schmal .zahl { position: absolute; top: 0; right: 10px; margin: 0; }
@media (max-width: 860px) {
  .glocke { height: auto; padding: 0.4rem; }
  .label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .zahl { position: absolute; top: -2px; right: -4px; }
}
</style>