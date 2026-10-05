<script setup>
import { computed, ref } from 'vue'
import { useApp } from '../stores/app'
import { useGastgeber } from '../stores/gastgeber'
import UserAvatar from './UserAvatar.vue'

// Who runs the evening, and how the baton changes hands. On the evening page and in the Kino.
const app = useApp()
const g = useGastgeber()
const waehlen = ref(false)
const an = ref('')
const ich = computed(() => g.gastgeber != null && g.gastgeber === app.me?.id)
const name = computed(() => app.userById(g.gastgeber)?.name)
const andere = computed(() => app.mitglieder.filter((u) => u.id !== g.gastgeber))

async function geben() {
  await g.uebergeben(Number(an.value))
  waehlen.value = false
  an.value = ''
}
</script>

<template>
  <div v-if="app.me" class="gastgeber row" aria-label="Gastgeber des Abends">
    <span class="stab" aria-hidden="true">🎬</span>
    <template v-if="g.gastgeber">
      <UserAvatar :user-id="g.gastgeber" link />
      <span>
        <strong>{{ ich ? 'Du bist' : name }}</strong> {{ ich ? 'Gastgeber' : 'ist Gastgeber' }}
        <small v-if="!ich" class="muted" :class="{ weg: !g.da }">· {{ g.da ? 'gerade da' : 'gerade nicht da' }}</small>
      </span>
    </template>
    <span v-else class="muted">Niemand hat den Gastgeber-Stab</span>
    <span class="spacer"></span>

    <template v-if="g.darfUebergeben && andere.length">
      <form v-if="waehlen" class="row" @submit.prevent="geben">
        <select v-model="an" aria-label="Stab weitergeben an" required>
          <option value="" disabled>An wen?</option>
          <option v-for="u in andere" :key="u.id" :value="u.id">{{ u.name }}</option>
        </select>
        <button class="small primary" :disabled="!an">Anbieten</button>
        <button type="button" class="small ghost" @click="waehlen = false">Abbrechen</button>
      </form>
      <button v-else class="small" @click="waehlen = true">Stab weitergeben</button>
    </template>
    <button v-if="g.uebernehmen === 'sofort'" class="small" @click="g.nehmen()">Stab übernehmen</button>
    <button v-else-if="g.uebernehmen === 'abstimmung'" class="small" title="Die Anwesenden stimmen ab – 60 Sekunden" @click="g.nehmen()">
      Übernehmen? Abstimmen lassen
    </button>
  </div>
</template>

<style scoped>
.gastgeber { gap: 0.55rem; font-size: 0.88rem; flex-wrap: wrap; }
.stab { font-size: 1.1rem; }
.weg { color: var(--gold); }
select { font-size: 0.82rem; }
</style>
