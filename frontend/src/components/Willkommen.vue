<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApp } from '../stores/app'
import Icon from './Icon.vue'
import MeineAbos from './MeineAbos.vue'
import Modal from './Modal.vue'
import SprachWahl from './SprachWahl.vue'
import ThemeWahl from './ThemeWahl.vue'

// The first visit of someone new: first language and colours, then how a movie night
// works here in three cards – and their streaming services, so "Läuft bei uns" knows
// what you have from day one.
const app = useApp()
const { t } = useI18n()
const schritt = ref(0)
const KARTEN = [
  { emoji: '🙋', key: 'vorschlagen' },
  { emoji: '🎁', key: 'kiste' },
  { emoji: '🍿', key: 'schauen' },
]
// Steps: 0 = language & look, 1–3 = the cards, 4 = streaming services (only with TMDB).
const mitAbos = computed(() => app.status.tmdb)
const letzte = computed(() => (mitAbos.value ? KARTEN.length + 1 : KARTEN.length))
const karte = computed(() => KARTEN[schritt.value - 1])
const emit = defineEmits(['fertig'])
</script>

<template>
  <Modal :label="t('willkommen.dialog')" width="560px" :dismissable="false" @close="emit('fertig')">
    <div class="willkommen">
      <div class="punkte" aria-hidden="true">
        <span v-for="i in letzte + 1" :key="i" :class="{ an: i - 1 === schritt }"></span>
      </div>
      <template v-if="schritt === 0">
        <span class="emoji" aria-hidden="true">👋</span>
        <h2>{{ t('willkommen.hallo', { name: app.me?.name }) }}</h2>
        <p>{{ t('willkommen.einrichten') }}</p>
        <div class="wahl">
          <h3>{{ t('sprache.wahl') }}</h3>
          <SprachWahl class="mitte" />
          <h3>{{ t('darstellung.farbschema') }}</h3>
          <ThemeWahl />
          <p class="klein">{{ t('willkommen.spaeter') }}</p>
        </div>
      </template>
      <template v-else-if="karte">
        <span class="emoji" aria-hidden="true">{{ karte.emoji }}</span>
        <h2>{{ t(`willkommen.${karte.key}.titel`) }}</h2>
        <p>{{ t(`willkommen.${karte.key}.text`) }}</p>
      </template>
      <template v-else>
        <span class="emoji" aria-hidden="true">📺</span>
        <h2>{{ t('willkommen.dienste') }}</h2>
        <p>{{ t('willkommen.diensteText') }}</p>
        <MeineAbos class="abos" />
      </template>
      <div class="row">
        <button v-if="schritt > 0" class="ghost" @click="schritt--">{{ t('allg.zurueck') }}</button>
        <span class="spacer"></span>
        <button v-if="schritt < letzte" class="ghost small" @click="emit('fertig')">{{ t('willkommen.ueberspringen') }}</button>
        <button v-if="schritt < letzte" class="primary" @click="schritt++">{{ t('willkommen.weiter') }} <Icon name="pfeil" :size="14" class="weiter" /></button>
        <button v-else class="primary" @click="emit('fertig')">{{ t('willkommen.los') }}</button>
      </div>
    </div>
  </Modal>
</template>

<style scoped>
.willkommen { padding: 1.6rem 1.6rem 1.3rem; display: flex; flex-direction: column; gap: 0.7rem; text-align: center; }
.punkte { display: flex; justify-content: center; gap: 6px; }
.punkte span { width: 7px; height: 7px; border-radius: 50%; background: var(--line); transition: background 0.2s, width 0.2s; }
.punkte span.an { background: var(--accent); width: 20px; border-radius: 4px; }
.emoji { font-size: 3rem; line-height: 1; margin-top: 0.5rem; }
h2 { margin: 0; font-size: 1.35rem; }
h3 { margin: 0.6rem 0 0.1rem; font-size: 0.9rem; text-align: left; }
p { margin: 0; color: var(--muted); line-height: 1.55; }
.wahl { display: flex; flex-direction: column; gap: 0.45rem; text-align: left; }
.klein { font-size: 0.8rem; margin-top: 0.3rem; }
.abos { text-align: left; }
.abos :deep(h2) { display: none; }
.row { margin-top: 0.6rem; }
.weiter { transform: rotate(180deg); }
</style>
