<script setup>
import { computed } from 'vue'
import { datum } from '../format'

// One achievement: medal in its tier colour, locked ones dimmed with progress.
const props = defineProps({
  erfolg: { type: Object, required: true },
  am: { type: String, default: null }, // unlocked at
  wert: { type: Number, default: null }, // progress, own only
  vitrine: { type: Boolean, default: false }, // in the showcase
  waehlbar: { type: Boolean, default: false }, // can be put into the showcase
})
defineEmits(['vitrine'])
const offen = computed(() => !!props.am)
const prozent = computed(() => (props.wert == null ? null : Math.min(100, Math.round((100 * props.wert) / props.erfolg.ziel))))
</script>

<template>
  <div class="kachel" :class="[`stufe-${erfolg.stufe}`, { offen, geheim: erfolg.name === '???' }]">
    <span class="medaille" aria-hidden="true">{{ erfolg.emoji }}</span>
    <div class="info">
      <strong>{{ erfolg.name }}</strong>
      <span class="muted text">{{ erfolg.text }}</span>
      <div v-if="!offen && prozent !== null && erfolg.ziel > 1" class="fortschritt" :title="$t('erfolgkachel.vonZiel', { wert, ziel: erfolg.ziel })">
        <span class="balken"><span :style="{ width: `${prozent}%` }"></span></span>
        <small>{{ Math.min(wert, erfolg.ziel) }}/{{ erfolg.ziel }}</small>
      </div>
      <span class="meta muted">
        {{ erfolg.punkte }} P
        <template v-if="erfolg.selten != null"> {{ $t('erfolgkachel.seltenDerGruppe', { selten: erfolg.selten }) }}</template>
        <template v-if="am"> · {{ datum(am) }}</template>
      </span>
    </div>
    <button
      v-if="waehlbar"
      class="ghost stern"
      :class="{ an: vitrine }"
      :aria-pressed="vitrine"
      :aria-label="vitrine ? $t('erfolgkachel.nameAusDerVitrine', { name: erfolg.name }) : $t('erfolgkachel.nameInDieVitrine', { name: erfolg.name })"
      :title="vitrine ? $t('erfolgkachel.ausDerVitrineNehmen') : $t('erfolgkachel.inDieVitrineBis')"
      @click="$emit('vitrine', erfolg.key)"
    >★</button>
  </div>
</template>

<style scoped>
.kachel {
  display: flex; gap: 0.8rem; align-items: flex-start; padding: 0.8rem; border-radius: var(--radius);
  background: var(--bg-soft); border: 1px solid var(--line); position: relative;
}
.medaille {
  width: 46px; height: 46px; flex: none; border-radius: 50%; display: grid; place-items: center; font-size: 1.35rem;
  background: radial-gradient(circle at 35% 30%, color-mix(in srgb, var(--m) 70%, white), var(--m));
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.18);
}
.stufe-1 { --m: #b0703c; }
.stufe-2 { --m: #a9b3bd; }
.stufe-3 { --m: #e0a82e; }
.stufe-4 { --m: #7fd3e6; }
.kachel:not(.offen) .medaille { filter: grayscale(1) brightness(0.45); }
.kachel:not(.offen) strong { color: var(--muted); }
.geheim .medaille { filter: grayscale(1) brightness(0.35); }
.info { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; flex: 1; }
.info strong { font-size: 0.92rem; }
.text { font-size: 0.8rem; }
.meta { font-size: 0.72rem; }
.fortschritt { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
.balken { flex: 1; height: 6px; border-radius: 3px; background: var(--bg-raised); overflow: hidden; }
.balken span { display: block; height: 100%; background: var(--m); }
.fortschritt small { font-size: 0.7rem; color: var(--muted); font-variant-numeric: tabular-nums; }
.stern { position: absolute; top: 4px; right: 4px; font-size: 1rem; color: var(--muted); padding: 2px 6px; }
.stern.an { color: var(--gold); }
</style>
