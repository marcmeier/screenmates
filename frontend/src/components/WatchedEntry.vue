<script setup>
import { computed, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { datum, dezimal } from '../format'
import Icon from './Icon.vue'
import Kommentar from './Kommentar.vue'
import Poster from './Poster.vue'
import StarRating from './StarRating.vue'
import UserAvatar from './UserAvatar.vue'

// `kompakt`: inside a film's detail sheet, where poster and title are already shown.
const props = defineProps({ entry: { type: Object, required: true }, kompakt: Boolean })
const emit = defineEmits(['update', 'removed'])
const app = useApp()
const ui = useUi()
const note = ref('')
const editDate = ref(false)

const m = computed(() => props.entry.movie)
const myRating = computed(() => props.entry.ratings.find((r) => r.user_id === app.me?.id)?.stars || 0)
const others = computed(() => props.entry.ratings.filter((r) => r.user_id !== app.me?.id))
const dateValue = computed(() => props.entry.watched_at.slice(0, 10))

// Update this card at once, and tell every other view showing the same evening
// (the chronicle behind an open detail sheet, the sheet itself) to refresh.
const update = (p) =>
  p.then((e) => {
    emit('update', e)
    ui.changed()
  })

function rate(stars) {
  update(api.post(`/api/watched/${props.entry.id}/rating`, { stars }))
}

function addNote(text, parent_id = null) {
  return update(api.post(`/api/watched/${props.entry.id}/notes`, { text, parent_id }))
}

async function send() {
  if (!note.value.trim()) return
  await addNote(note.value.trim())
  note.value = ''
}

async function heart(noteId) {
  await api.post('/api/watched/hearts', { note_id: noteId })
  ui.changed()
}

async function removeNote(noteId) {
  if (!confirm('Kommentar löschen?')) return
  await api.del(`/api/watched-notes/${noteId}`)
  ui.changed()
}

function setDate(e) {
  editDate.value = false
  if (!e.target.value) return
  update(api.patch(`/api/watched/${props.entry.id}`, { watched_at: `${e.target.value}T20:00:00Z` }))
}

async function toggleDabei(userId) {
  const ids = props.entry.participants.includes(userId)
    ? props.entry.participants.filter((id) => id !== userId)
    : [...props.entry.participants, userId]
  update(api.post(`/api/watched/${props.entry.id}/dabei`, { user_ids: ids }))
}

async function hide() {
  update(api.patch(`/api/watched/${props.entry.id}`, { hidden: !props.entry.hidden }))
}

async function remove() {
  if (!confirm(`„${m.value?.title}“ samt Bewertungen und Kommentaren löschen?`)) return
  await api.del(`/api/watched/${props.entry.id}`)
  emit('removed', props.entry.id)
}
</script>

<template>
  <article class="entry" :class="{ hidden: entry.hidden, kompakt }">
    <button v-if="!kompakt" class="cover" :aria-label="`${m?.title} – Details`" @click="m && ui.open(m)">
      <Poster v-if="m" :movie="m" />
    </button>

    <div class="body">
      <header class="head">
        <div>
          <h3 v-if="!kompakt">{{ m?.title }} <span class="muted year">{{ m?.year }}</span></h3>
          <div class="row sub">
            <span v-if="kompakt" class="muted">Geschaut am</span>
            <input v-if="editDate" type="date" :value="dateValue" autofocus aria-label="Datum" @change="setDate" @blur="editDate = false" />
            <button v-else class="ghost small date" :disabled="!app.me" title="Datum ändern" @click="editDate = true">
              {{ datum(entry.watched_at) }}
            </button>
            <span class="avatars">
              <UserAvatar v-for="id in entry.participants" :key="id" :user-id="id" />
            </span>
          </div>
        </div>
        <div v-if="entry.rating_avg" class="avg" :title="`${entry.ratings.length} Bewertungen`">
          <span class="num">{{ dezimal(entry.rating_avg) }}</span><span class="muted">/5</span>
        </div>
      </header>

      <div class="row rating">
        <template v-if="app.me">
          <span class="muted label">Deine Wertung</span>
          <StarRating :model-value="myRating" @update:model-value="rate" />
        </template>
        <span v-for="r in others" :key="r.id" class="chip">
          <UserAvatar :user-id="r.user_id" /> {{ '★'.repeat(r.stars) }}
        </span>
      </div>

      <details v-if="app.me" class="dabei">
        <summary class="muted">Wer war dabei?</summary>
        <div class="row">
          <button
            v-for="u in app.users"
            :key="u.id"
            class="chip"
            :class="{ on: entry.participants.includes(u.id) }"
            :aria-pressed="entry.participants.includes(u.id)"
            @click="toggleDabei(u.id)"
          >{{ u.name }}</button>
        </div>
      </details>

      <div class="notes">
        <Kommentar
          v-for="n in entry.notes"
          :key="n.id"
          :note="n"
          @reply="addNote($event.text, $event.parent)"
          @heart="heart"
          @remove="removeNote"
        />
        <form v-if="app.me" class="add" @submit.prevent="send">
          <input v-model="note" maxlength="2000" placeholder="Ins Gästebuch schreiben …" aria-label="Kommentar" />
          <button class="small" :disabled="!note.trim()">Senden</button>
        </form>
      </div>

      <footer v-if="app.admin" class="row host">
        <button class="ghost small" @click="hide">{{ entry.hidden ? 'Wieder anzeigen' : 'Ausblenden' }}</button>
        <button class="ghost small danger" @click="remove"><Icon name="muell" :size="14" /> Löschen</button>
      </footer>
    </div>
  </article>
</template>

<style scoped>
.entry { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 1.2rem; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 1rem; }
.entry.hidden { opacity: 0.55; }
.cover { padding: 0; aspect-ratio: 2/3; border-radius: 8px; overflow: hidden; background: var(--bg-raised); align-self: start; }
.head { display: flex; justify-content: space-between; gap: 1rem; }
h3 { margin: 0; font-size: 1.15rem; }
.year { font-weight: 400; font-size: 0.9rem; }
.sub { margin-top: 0.3rem; gap: 0.8rem; }
.sub input { width: auto; padding: 0.2rem 0.4rem; }
.date { padding: 0.15rem 0.4rem; margin-left: -0.4rem; font-size: 0.82rem; }
.avatars .avatar { width: 22px; height: 22px; font-size: 0.6rem; }
.avg { text-align: right; flex: none; }
.avg .num { font-size: 1.6rem; font-weight: 800; color: var(--gold); }
.rating { margin: 0.7rem 0 0.2rem; }
.label { font-size: 0.8rem; }
.chip .avatar { width: 18px; height: 18px; font-size: 0.5rem; }
.chip { color: var(--gold); }
.dabei { margin: 0.4rem 0; font-size: 0.85rem; }
.dabei summary { cursor: pointer; margin-bottom: 0.4rem; }
.dabei .chip { color: var(--muted); }
.dabei .chip.on { color: #fff; }
.notes { border-top: 1px solid var(--line); margin-top: 0.6rem; }
.add { display: flex; gap: 0.5rem; margin-top: 0.8rem; }
.host { margin-top: 0.8rem; justify-content: flex-end; }
@media (max-width: 600px) { .entry { grid-template-columns: 70px minmax(0, 1fr); } }
.entry.kompakt { grid-template-columns: minmax(0, 1fr); background: transparent; border: none; padding: 0; }
.entry.kompakt .sub { margin-top: 0; }
</style>
