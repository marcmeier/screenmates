<script setup>
import { t } from '../../i18n'
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useUi } from '../../stores/ui'
import { vorWann } from '../../format'
import Icon from '../Icon.vue'
import UserAvatar from '../UserAvatar.vue'

const app = useApp()
const ui = useUi()
const features = ref([])
const loading = ref(true)
const draft = ref('')
const open = ref(null)
const editing = ref(null)
const noteDraft = ref('')

async function load() {
  try {
    features.value = (await api.get('/api/features')).features
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => [ui.changes, app.me?.id], load)

function replace(f) {
  const i = features.value.findIndex((x) => x.id === f.id)
  if (i >= 0) features.value[i] = f
}

async function add() {
  const text = draft.value.trim()
  if (!text) return
  features.value.unshift(await api.post('/api/features', { text }))
  draft.value = ''
}
const vote = async (f) => replace(await api.post(`/api/features/${f.id}/vote`))
const done = async (f) => replace(await api.patch(`/api/features/${f.id}/done`, { done: !f.done }))

async function save(f, text) {
  editing.value = null
  if (text.trim() && text.trim() !== f.text) replace(await api.patch(`/api/features/${f.id}`, { text: text.trim() }))
}

async function remove(f) {
  if (!confirm(t('wuenschetab.diesenWunschLoeschen'))) return
  await api.del(`/api/features/${f.id}`)
  features.value = features.value.filter((x) => x.id !== f.id)
}

async function addNote(f) {
  if (!noteDraft.value.trim()) return
  replace(await api.post(`/api/features/${f.id}/notes`, { text: noteDraft.value.trim() }))
  noteDraft.value = ''
}

async function removeNote(f, n) {
  await api.del(`/api/feature-notes/${n.id}`)
  replace({ ...f, notes: f.notes.filter((x) => x.id !== n.id) })
}

const mine = (o) => app.me && o.user_id === app.me.id
const offen = computed(() => features.value.filter((f) => !f.done))
const erledigt = computed(() => features.value.filter((f) => f.done))
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1>{{ $t('wuenschetab.wuensche') }}</h1>
        <p>{{ $t('wuenschetab.ideenFuerScreenmatesAbstimmen') }}</p>
      </div>
    </header>

    <form v-if="app.me" class="add" @submit.prevent="add">
      <input v-model="draft" maxlength="500" :placeholder="$t('wuenschetab.wasSollScreenmatesNoch')" :aria-label="$t('wuenschetab.neuerWunsch')" />
      <button class="primary" :disabled="!draft.trim()"><Icon name="plus" :size="16" /> {{ $t('wuenschetab.wuenschen') }}</button>
    </form>

    <div v-if="loading" class="list"><div v-for="i in 3" :key="i" class="skeleton" style="height: 64px"></div></div>
    <div v-else-if="!features.length" class="empty"><strong>{{ $t('wuenschetab.nochKeineWuensche') }}</strong>{{ $t('wuenschetab.derErsteWunschIst') }}</div>

    <template v-for="[title, list] in [['Offen', offen], ['Erledigt', erledigt]]" :key="title">
      <h2 v-if="list.length" class="section-title">{{ title }} · {{ list.length }}</h2>
      <ul class="list">
        <li v-for="f in list" :key="f.id" class="wish" :class="{ done: f.done }">
          <button
            class="vote"
            :class="{ on: f.voted }"
            :disabled="!app.me"
            :aria-pressed="f.voted"
            :aria-label="$t('wuenschetab.abstimmenVotesStimmen', { votes: f.votes })"
            @click="vote(f)"
          >▲<span>{{ f.votes }}</span></button>

          <div class="main">
            <input
              v-if="editing === f.id"
              :value="f.text"
              maxlength="500"
              autofocus
              :aria-label="$t('wuenschetab.wunschBearbeiten')"
              @keydown.enter="save(f, $event.target.value)"
              @keydown.escape="editing = null"
              @blur="save(f, $event.target.value)"
            />
            <p v-else class="text">{{ f.text }}</p>
            <div class="row meta">
              <UserAvatar v-if="f.user_id" :user-id="f.user_id" />
              <span>{{ vorWann(f.created_at) }}</span>
              <button class="ghost small" @click="open = open === f.id ? null : f.id">
                {{ f.notes.length ? `${f.notes.length} Anmerkung${f.notes.length > 1 ? 'en' : ''}` : $t('wuenschetab.anmerken') }}
              </button>
            </div>

            <div v-if="open === f.id" class="notes">
              <div v-for="n in f.notes" :key="n.id" class="note">
                <UserAvatar :user-id="n.user_id" />
                <span>{{ n.text }}</span>
                <button v-if="mine(n) || app.admin" class="ghost small" :aria-label="$t('wuenschetab.anmerkungLoeschen')" @click="removeNote(f, n)">
                  <Icon name="x" :size="12" />
                </button>
              </div>
              <form v-if="app.me" class="add small-add" @submit.prevent="addNote(f)">
                <input v-model="noteDraft" maxlength="1000" :placeholder="$t('wuenschetab.anmerkung')" :aria-label="$t('wuenschetab.anmerkung2')" />
                <button class="small" :disabled="!noteDraft.trim()">{{ $t('wuenschetab.senden') }}</button>
              </form>
            </div>
          </div>

          <div class="actions">
            <button v-if="app.admin" class="ghost small" :title="f.done ? $t('wuenschetab.wiederOeffnen') : $t('wuenschetab.alsErledigtMarkieren')" @click="done(f)">
              <Icon :name="f.done ? 'antwort' : 'gesehen'" :size="15" />
            </button>
            <button v-if="mine(f) || app.admin" class="ghost small" :aria-label="$t('wuenschetab.bearbeiten')" @click="editing = f.id"><Icon name="stift" :size="15" /></button>
            <button v-if="mine(f) || app.admin" class="ghost small danger" :aria-label="$t('wuenschetab.loeschen')" @click="remove(f)"><Icon name="muell" :size="15" /></button>
          </div>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 820px; }
.add { display: flex; gap: 0.6rem; margin-bottom: 1rem; }
.add button { flex: none; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.6rem; }
.wish { display: flex; gap: 0.9rem; align-items: flex-start; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.8rem 0.9rem; }
.wish.done .text { text-decoration: line-through; color: var(--muted); }
.vote { flex-direction: column; gap: 0; min-width: 48px; padding: 0.35rem; line-height: 1.1; font-size: 0.8rem; }
.vote span { font-weight: 800; font-size: 0.95rem; }
.vote.on { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.main { flex: 1; min-width: 0; }
.text { margin: 0.1rem 0 0.3rem; overflow-wrap: anywhere; }
.meta { font-size: 0.78rem; color: var(--muted); gap: 0.4rem; }
.meta .avatar, .note .avatar { width: 20px; height: 20px; font-size: 0.55rem; }
.notes { margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px solid var(--line); }
.note { display: flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; padding: 0.25rem 0; }
.small-add { margin: 0.5rem 0 0; }
.actions { display: flex; gap: 0.1rem; }
</style>
