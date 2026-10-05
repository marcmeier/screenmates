<script setup>
import { ref } from 'vue'
import { useApp } from '../stores/app'
import { vorWann } from '../format'
import Icon from './Icon.vue'
import UserAvatar from './UserAvatar.vue'

defineOptions({ name: 'Kommentar' })
const props = defineProps({ note: { type: Object, required: true }, depth: { type: Number, default: 0 } })
const emit = defineEmits(['reply', 'heart', 'remove'])
const app = useApp()
const replying = ref(false)
const text = ref('')

const mine = () => app.me && props.note.user_id === app.me.id
const hearted = () => app.me && props.note.hearts.includes(app.me.id)

function send() {
  if (!text.value.trim()) return
  emit('reply', { parent: props.note.id, text: text.value.trim() })
  text.value = ''
  replying.value = false
}
</script>

<template>
  <div class="note" :class="{ nested: depth > 0 }">
    <UserAvatar :user-id="note.user_id" />
    <div class="content">
      <div class="head">
        <strong>{{ app.userById(note.user_id)?.name || 'Gelöscht' }}</strong>
        <time class="muted" :datetime="note.created_at">{{ vorWann(note.created_at) }}</time>
      </div>
      <p>{{ note.text }}</p>
      <div class="tools">
        <button class="ghost small" :class="{ hearted: hearted() }" :disabled="!app.me" :aria-pressed="hearted()" @click="emit('heart', note.id)">
          <Icon name="herz" :size="14" /> {{ note.hearts.length || '' }}
        </button>
        <button v-if="app.me && depth < 3" class="ghost small" @click="replying = !replying"><Icon name="antwort" :size="14" /> Antworten</button>
        <button v-if="mine() || app.admin" class="ghost small" aria-label="Kommentar löschen" @click="emit('remove', note.id)"><Icon name="muell" :size="14" /></button>
      </div>
      <form v-if="replying" class="reply" @submit.prevent="send">
        <input v-model="text" maxlength="2000" placeholder="Antwort …" autofocus aria-label="Antwort" />
        <button class="small" :disabled="!text.trim()">Senden</button>
      </form>
      <Kommentar
        v-for="r in note.replies"
        :key="r.id"
        :note="r"
        :depth="depth + 1"
        @reply="emit('reply', $event)"
        @heart="emit('heart', $event)"
        @remove="emit('remove', $event)"
      />
    </div>
  </div>
</template>

<style scoped>
.note { display: flex; gap: 0.6rem; margin-top: 0.7rem; }
.note.nested { margin-top: 0.5rem; }
.content { flex: 1; min-width: 0; }
.head { display: flex; gap: 0.5rem; align-items: baseline; font-size: 0.85rem; }
.head time { font-size: 0.75rem; }
p { margin: 0.15rem 0 0; font-size: 0.9rem; white-space: pre-wrap; overflow-wrap: anywhere; }
.tools { display: flex; gap: 0.1rem; margin-left: -0.5rem; }
.tools button { padding: 0.15rem 0.5rem; font-size: 0.75rem; }
.hearted { color: var(--accent); }
.reply { display: flex; gap: 0.4rem; margin-top: 0.3rem; }
</style>
