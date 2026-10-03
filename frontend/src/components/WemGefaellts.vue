<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import { dezimal } from '../format'
import UserAvatar from './UserAvatar.vue'

// Who'll like this film, estimated from everyone's own stars (backend: app/prognose.py).
// Deliberately modest: shown from 8 ratings, labelled "erste Tendenz" until 25.
const props = defineProps({ movieId: { type: Number, required: true } })
const app = useApp()
const ui = useUi()
const daten = ref(null)

async function laden() {
  try {
    daten.value = await api.get(`/api/movies/${props.movieId}/prognose`, { quiet: true })
  } catch {
    daten.value = null
  }
}
watch(() => props.movieId, laden, { immediate: true })
watch(() => ui.changes, laden) // a new rating changes everyone's estimate

function urteil(sterne) {
  if (sterne >= 4) return 'wird’s mögen'
  if (sterne >= 3) return 'eher gut'
  if (sterne >= 2) return 'eher nicht'
  return 'lieber nicht'
}
const name = (id) => app.userById(id)?.name ?? '?'
const fehlend = computed(() => daten.value?.zu_wenig ?? [])
</script>

<template>
  <section v-if="daten && (daten.prognosen.length || fehlend.length)" class="wem">
    <h3 class="section-title">Wem gefällt’s?</h3>
    <ul v-if="daten.prognosen.length" class="liste">
      <li v-for="p in daten.prognosen" :key="p.user_id">
        <UserAvatar :user-id="p.user_id" />
        <span class="name">{{ name(p.user_id) }}</span>
        <span class="sterne" :aria-label="`etwa ${dezimal(p.sterne)} von 5 Sternen`">
          <span v-for="n in 5" :key="n" class="s" :class="{ voll: n <= p.sterne, halb: n - 0.5 === p.sterne }">★</span>
        </span>
        <span class="urteil" :class="{ gut: p.sterne >= 3.5, schlecht: p.sterne < 2.5 }">{{ urteil(p.sterne) }}</span>
        <span class="warum muted">
          <template v-if="p.weil">wie „{{ p.weil.titel }}“ (★ {{ dezimal(p.weil.sterne) }})</template>
          <template v-if="p.sicherheit === 'erste tendenz'"><template v-if="p.weil"> · </template>erste Tendenz</template>
        </span>
      </li>
    </ul>
    <p v-if="fehlend.length" class="muted hinweis">
      Ab {{ daten.min }} Bewertungen schätzt screenmates, wem ein Film gefällt. Noch zu wenig:
      {{ fehlend.map((z) => `${name(z.user_id)} (${z.bewertungen}/${daten.min})`).join(', ') }}.
    </p>
  </section>
</template>

<style scoped>
.liste { list-style: none; padding: 0; margin: 0 0 0.6rem; display: flex; flex-direction: column; gap: 0.45rem; }
.liste li { display: grid; grid-template-columns: 24px 6rem auto auto 1fr; align-items: center; gap: 0.6rem; font-size: 0.9rem; }
.liste .avatar { width: 24px; height: 24px; font-size: 0.62rem; }
.name { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sterne { letter-spacing: 1px; color: #3a3a46; }
.s.voll { color: var(--gold); }
.s.halb { background: linear-gradient(90deg, var(--gold) 50%, #3a3a46 50%); -webkit-background-clip: text; background-clip: text; color: transparent; }
.urteil { font-size: 0.8rem; }
.urteil.gut { color: var(--ok); }
.urteil.schlecht { color: var(--accent); }
.warum { font-size: 0.78rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hinweis { font-size: 0.8rem; margin: 0; }
@media (max-width: 600px) {
  .liste li { grid-template-columns: 24px 1fr auto; }
  .urteil { grid-column: 2; }
  .warum { grid-column: 2 / 4; white-space: normal; }
}
</style>
