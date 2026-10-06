<script setup>
import { computed, ref } from 'vue'
import { useApp } from '../stores/app'
import Icon from './Icon.vue'
import MeineAbos from './MeineAbos.vue'
import Modal from './Modal.vue'

// The first visit of someone new: how a movie night works here, in three cards –
// and their streaming services, so "Läuft bei uns" knows what you have from day one.
const app = useApp()
const schritt = ref(0)
const KARTEN = [
  { emoji: '🙋', titel: 'Vorschlagen', text: 'Unter „Finden“ stöberst du, fragst die KI oder suchst – und schlägst mit ✋ vor, was du sehen willst. Jede Person hat ein Veto.' },
  { emoji: '🎁', titel: 'Die Kiste entscheidet', text: 'Am Abend öffnet der Gastgeber die Filmabend-Kiste für alle. Je mehr Stimmen ein Film hat, desto größer seine Chance.' },
  { emoji: '🍿', titel: 'Gemeinsam schauen & bewerten', text: 'Auf dem Sofa oder im Kino von screenmates – danach vergibt jede Person Sterne und schreibt ins Gästebuch.' },
]
const mitAbos = computed(() => app.status.tmdb)
const letzte = computed(() => (mitAbos.value ? KARTEN.length : KARTEN.length - 1))
const emit = defineEmits(['fertig'])
</script>

<template>
  <Modal label="Willkommen bei screenmates" width="520px" :dismissable="false" @close="emit('fertig')">
    <div class="willkommen">
      <div class="punkte" aria-hidden="true">
        <span v-for="i in letzte + 1" :key="i" :class="{ an: i - 1 === schritt }"></span>
      </div>
      <template v-if="schritt < KARTEN.length">
        <span class="emoji" aria-hidden="true">{{ KARTEN[schritt].emoji }}</span>
        <h2>{{ schritt === 0 ? `Willkommen, ${app.me?.name}!` : KARTEN[schritt].titel }}</h2>
        <h3 v-if="schritt === 0">{{ KARTEN[0].titel }}</h3>
        <p>{{ KARTEN[schritt].text }}</p>
      </template>
      <template v-else>
        <span class="emoji" aria-hidden="true">📺</span>
        <h2>Deine Streamingdienste</h2>
        <p>Was du abonniert hast, füllt „Läuft bei uns“ und zeigt bei jedem Vorschlag, wo er läuft. Später änderbar unter Einstellungen.</p>
        <MeineAbos class="abos" />
      </template>
      <div class="row">
        <button v-if="schritt > 0" class="ghost" @click="schritt--">Zurück</button>
        <span class="spacer"></span>
        <button v-if="schritt < letzte" class="ghost small" @click="emit('fertig')">Überspringen</button>
        <button v-if="schritt < letzte" class="primary" @click="schritt++">Weiter <Icon name="pfeil" :size="14" class="weiter" /></button>
        <button v-else class="primary" @click="emit('fertig')">Los geht’s</button>
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
h3 { margin: 0; font-size: 1rem; color: var(--accent); }
p { margin: 0; color: var(--muted); line-height: 1.55; }
.abos { text-align: left; }
.abos :deep(h2) { display: none; }
.row { margin-top: 0.6rem; }
.weiter { transform: rotate(180deg); }
</style>