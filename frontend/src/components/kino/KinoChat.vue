<script setup>
import { nextTick, ref, watch } from 'vue'
import { useApp } from '../../stores/app'
import { useKinoChat } from '../../stores/kinochat'
import UserAvatar from '../UserAvatar.vue'
import Icon from '../Icon.vue'

// Chat next to the screen. New messages scroll into view unless you scrolled up to read.
const app = useApp()
const chat = useKinoChat()
const text = ref('')
const liste = ref(null)
const sendet = ref(false)
const zeit = new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' })

function untenAngekommen() {
  const el = liste.value
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 60
}
watch(
  () => chat.nachrichten.length,
  async () => {
    const unten = untenAngekommen()
    await nextTick()
    if (unten && liste.value) liste.value.scrollTop = liste.value.scrollHeight
  },
)

async function senden() {
  const t = text.value.trim()
  if (!t || sendet.value) return
  sendet.value = true
  try {
    await chat.senden(t)
    text.value = ''
    await nextTick()
    if (liste.value) liste.value.scrollTop = liste.value.scrollHeight
  } finally {
    sendet.value = false
  }
}
const name = (id) => app.userById(id)?.name ?? 'Jemand'
const farbe = (id) => app.userById(id)?.color || 'var(--muted)'
</script>

<template>
  <section class="panel kinochat" aria-label="Kino-Chat">
    <header class="row">
      <Icon name="chat" :size="16" class="muted" />
      <h2>Chat</h2>
    </header>
    <ol ref="liste" class="nachrichten" aria-live="polite">
      <li v-if="!chat.nachrichten.length" class="leer muted">Noch still hier. Sag hallo – oder schick unten eine Reaktion ins Bild.</li>
      <li v-for="n in chat.nachrichten" :key="n.id" :class="{ meine: n.user_id === app.me?.id }">
        <UserAvatar :user-id="n.user_id" />
        <div class="blase">
          <span class="wer" :style="{ color: farbe(n.user_id) }">{{ name(n.user_id) }}</span>
          <time class="muted" :datetime="new Date(n.at).toISOString()">{{ zeit.format(n.at) }}</time>
          <p>{{ n.inhalt }}</p>
        </div>
      </li>
    </ol>
    <div class="reaktionen" role="group" aria-label="Reaktion ins Bild schicken">
      <button v-for="r in chat.reaktionen" :key="r" class="ghost" :aria-label="`Reaktion ${r}`" @click="chat.reagieren(r)">{{ r }}</button>
    </div>
    <form class="eingabe" @submit.prevent="senden">
      <input v-model="text" maxlength="300" placeholder="Nachricht an alle …" aria-label="Nachricht an alle" autocomplete="off" />
      <button class="primary small" :disabled="!text.trim() || sendet" aria-label="Senden"><Icon name="play" :size="14" /></button>
    </form>
  </section>
</template>

<style scoped>
.kinochat { display: flex; flex-direction: column; gap: 0.6rem; padding: 0.8rem; min-height: 0; }
header h2 { margin: 0; font-size: 0.95rem; }
.nachrichten {
  list-style: none; margin: 0; padding: 0 0.2rem 0 0; overflow-y: auto; flex: 1; min-height: 12rem; max-height: 26rem;
  display: flex; flex-direction: column; gap: 0.55rem;
}
.nachrichten li { display: flex; gap: 0.5rem; align-items: flex-start; }
.nachrichten .avatar { width: 26px; height: 26px; font-size: 0.6rem; flex: none; }
.blase { min-width: 0; font-size: 0.88rem; }
.blase p { margin: 0.1rem 0 0; overflow-wrap: anywhere; line-height: 1.35; }
.wer { font-weight: 700; font-size: 0.8rem; margin-right: 0.4rem; }
time { font-size: 0.7rem; }
.meine .blase p { color: #fff; }
.leer { font-size: 0.85rem; align-self: center; text-align: center; padding: 2rem 0.5rem; }
.reaktionen { display: flex; flex-wrap: wrap; gap: 2px; }
.reaktionen button { font-size: 1.2rem; padding: 0.2rem 0.4rem; line-height: 1; }
.reaktionen button:hover { transform: scale(1.15); }
.eingabe { display: flex; gap: 0.4rem; }
.eingabe input { flex: 1; min-width: 0; }
</style>