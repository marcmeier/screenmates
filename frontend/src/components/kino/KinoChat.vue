<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useApp } from '../../stores/app'
import { useKinoChat } from '../../stores/kinochat'
import UserAvatar from '../UserAvatar.vue'
import Icon from '../Icon.vue'

// Chat next to the screen, a fixed height that scrolls. New messages scroll into view
// unless you scrolled up to read; older ones load on demand (they age out after 30 days).
const app = useApp()
const chat = useKinoChat()
const text = ref('')
const liste = ref(null)
const sendet = ref(false)
const laedt = ref(false)
const zeit = new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' })
const datum = new Intl.DateTimeFormat('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })

function tagText(ms) {
  const tag = new Date(ms).toDateString()
  if (tag === new Date().toDateString()) return 'Heute'
  if (tag === new Date(Date.now() - 864e5).toDateString()) return 'Gestern'
  return datum.format(ms)
}
// Messages with a day line wherever the day changes.
const zeilen = computed(() => {
  let vorher = null
  return chat.nachrichten.map((n) => {
    const tag = new Date(n.at).toDateString()
    const trenner = tag !== vorher ? tagText(n.at) : null
    vorher = tag
    return { ...n, trenner }
  })
})

function untenAngekommen() {
  const el = liste.value
  return !el || el.scrollHeight - el.scrollTop - el.clientHeight < 60
}
const nachUnten = () => liste.value && (liste.value.scrollTop = liste.value.scrollHeight)
watch(
  () => chat.nachrichten.at(-1)?.id,
  async () => {
    const unten = untenAngekommen()
    await nextTick()
    if (unten) nachUnten()
  },
)

async function aelter() {
  const el = liste.value
  const abstand = el.scrollHeight - el.scrollTop
  laedt.value = true
  try {
    await chat.aelterLaden()
    await nextTick()
    el.scrollTop = el.scrollHeight - abstand // keep reading where you were
  } finally {
    laedt.value = false
  }
}

async function senden() {
  const t = text.value.trim()
  if (!t || sendet.value) return
  sendet.value = true
  try {
    await chat.senden(t)
    text.value = ''
    await nextTick()
    nachUnten()
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
      <span class="spacer"></span>
      <small class="muted" :title="`Nachrichten verschwinden nach ${chat.tage} Tagen`">{{ chat.tage }} Tage</small>
    </header>
    <ol ref="liste" class="nachrichten" aria-live="polite">
      <li v-if="chat.mehr" class="mehr">
        <button class="ghost small" :disabled="laedt" @click="aelter">Ältere Nachrichten</button>
      </li>
      <li v-if="!chat.nachrichten.length" class="leer muted">Noch still hier. Sag hallo – oder schick unten eine Reaktion ins Bild.</li>
      <template v-for="n in zeilen" :key="n.id">
        <li v-if="n.trenner" class="trenner"><span>{{ n.trenner }}</span></li>
        <li class="nachricht" :class="{ meine: n.user_id === app.me?.id }">
          <UserAvatar :user-id="n.user_id" />
          <div class="blase">
            <span class="wer" :style="{ color: farbe(n.user_id) }">{{ name(n.user_id) }}</span>
            <time class="muted" :datetime="new Date(n.at).toISOString()">{{ zeit.format(n.at) }}</time>
            <p>{{ n.inhalt }}</p>
          </div>
        </li>
      </template>
    </ol>
    <div class="reaktionen" role="group" aria-label="Reaktion ins Bild schicken">
      <button v-for="r in chat.reaktionen" :key="r" class="ghost" :aria-label="`Reaktion ${r}`" @click="chat.reagieren(r)">{{ r }}</button>
    </div>
    <button class="ghost small moment" @click="chat.moment()">✋ Moment, bin gleich da</button>
    <form class="eingabe" @submit.prevent="senden">
      <input v-model="text" maxlength="300" placeholder="Nachricht an alle …" aria-label="Nachricht an alle" autocomplete="off" />
      <button class="primary small" :disabled="!text.trim() || sendet" aria-label="Senden"><Icon name="play" :size="14" /></button>
    </form>
  </section>
</template>

<style scoped>
.kinochat { display: flex; flex-direction: column; gap: 0.6rem; padding: 0.8rem; min-height: 0; height: var(--chat-hoehe, 34rem); }
header h2 { margin: 0; font-size: 0.95rem; }
header small { font-size: 0.72rem; }
.nachrichten {
  list-style: none; margin: 0; padding: 0 0.2rem 0 0; overflow-y: auto; flex: 1; min-height: 0;
  display: flex; flex-direction: column; gap: 0.55rem; overscroll-behavior: contain;
}
.nachricht { display: flex; gap: 0.5rem; align-items: flex-start; }
.nachricht .avatar { width: 26px; height: 26px; font-size: 0.6rem; flex: none; }
.blase { min-width: 0; font-size: 0.88rem; }
.blase p { margin: 0.1rem 0 0; overflow-wrap: anywhere; line-height: 1.35; }
.wer { font-weight: 700; font-size: 0.8rem; margin-right: 0.4rem; }
time { font-size: 0.7rem; }
.meine .blase p { color: #fff; }
.leer { font-size: 0.85rem; align-self: center; text-align: center; padding: 2rem 0.5rem; margin: auto 0; }
.mehr { align-self: center; }
.trenner { display: flex; align-items: center; gap: 0.6rem; font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }
.trenner::before, .trenner::after { content: ''; flex: 1; height: 1px; background: var(--line); }
.reaktionen { display: flex; flex-wrap: wrap; gap: 0; justify-content: space-between; }
.reaktionen button { font-size: 1.15rem; padding: 0.2rem 0.25rem; line-height: 1; }
.reaktionen button:hover { transform: scale(1.15); }
.moment { align-self: flex-start; font-size: 0.78rem; }
.eingabe { display: flex; gap: 0.4rem; }
.eingabe input { flex: 1; min-width: 0; }
</style>