<script setup>
import { t as tr } from '../i18n'
import { computed } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useKiste } from '../stores/kiste'
import { useGastgeber } from '../stores/gastgeber'
import { useKino } from '../stores/kino'
import { useUi } from '../stores/ui'
import { navigate } from '../composables/useRoute'
import { terminText } from '../einladung'
import Icon from './Icon.vue'
import { audioJetzt } from '../audio'
import Poster from './Poster.vue'
import UserAvatar from './UserAvatar.vue'

// The evening itself, as three steps on the day of the date: who's here → what we watch → film on.
// Everything here exists elsewhere on the page; this just puts it in order for tonight.
const props = defineProps({ termin: { type: Object, required: true }, pool: { type: Array, default: () => [] } })
const emit = defineEmits(['geschaut'])
const app = useApp()
const kiste = useKiste()
const kino = useKino()
const ui = useUi()
const g = useGastgeber()

// Not the host? Then say who is, and – if they aren't around (or nobody is) – take the baton
// and open the case in one go. With the host there, taking over goes to a short vote.
const hostName = computed(() => app.userById(g.gastgeber)?.name ?? '')
async function uebernehmenUndOeffnen() {
  audioJetzt()
  await g.nehmen()
  await kiste.oeffnen()
}

const t = computed(() => terminText(props.termin))
const gewinner = computed(() => kiste.aktuell?.gewinner ?? null)
const schritte = computed(() => [
  { key: 'da', titel: tr('abendmodus.werIstDa'), fertig: app.dabei.length >= 2 },
  { key: 'film', titel: tr('abendmodus.wasSchauenWir'), fertig: !!gewinner.value },
  { key: 'los', titel: tr('abendmodus.filmAb'), fertig: false },
])
const aktuell = computed(() => schritte.value.find((s) => !s.fertig)?.key ?? 'los')

async function eintragen() {
  const w = await api.post('/api/watched', { movie_id: gewinner.value.id })
  // Everyone who said yes was there – the chronicle can be corrected later.
  const leute = app.dabei.map((u) => u.id)
  if (leute.length) await api.post(`/api/watched/${w.id}/dabei`, { user_ids: [...new Set([app.me.id, ...leute])] })
  ui.toast(tr('abendmodus.titleEingetragenVielSpass', { title: gewinner.value.title }), 'ok')
  kiste.aktuell = null
  ui.changed()
  emit('geschaut')
}
</script>

<template>
  <section class="abendmodus" :aria-label="$t('abendmodus.heuteAbend')">
    <header>
      <span class="heute">{{ $t('abendmodus.heuteAbend2') }}</span>
      <strong>{{ t.zeit }}</strong><span v-if="t.notiz" class="muted"> · {{ t.notiz }}</span>
    </header>
    <ol class="schritte">
      <li v-for="(s, i) in schritte" :key="s.key" :class="{ fertig: s.fertig, aktuell: aktuell === s.key }">
        <span class="nr" aria-hidden="true"><Icon v-if="s.fertig" name="gesehen" :size="14" /><template v-else>{{ i + 1 }}</template></span>
        <div class="inhalt">
          <h3>{{ s.titel }}</h3>

          <template v-if="s.key === 'da'">
            <div class="row">
              <span class="avatars"><UserAvatar v-for="u in app.dabei" :key="u.id" :user="u" /></span>
              <span class="muted klein">{{ app.dabei.length ? app.dabei.map((u) => u.name).join(', ') : $t('abendmodus.nochNiemand') }}</span>
            </div>
            <button v-if="app.me && !app.me.dabei" class="small primary" @click="app.toggleDabei()">{{ $t('abendmodus.ichBinDa') }}</button>
          </template>

          <template v-else-if="s.key === 'film'">
            <div v-if="gewinner" class="film">
              <span class="plakat"><Poster :movie="gewinner" :title="false" /></span>
              <span><strong>{{ gewinner.title }}</strong><small class="muted">{{ $t('abendmodus.ausDerKiste') }}</small></span>
            </div>
            <template v-else-if="pool.length">
              <button v-if="kiste.darfOeffnen" class="small primary" :disabled="!!kiste.buehne" @click="audioJetzt(), kiste.oeffnen()">
                <Icon name="kiste" :size="14" /> {{ $t('abendmodus.kisteFuerAlleOeffnen') }}
              </button>
              <template v-else-if="app.me && g.uebernehmen === 'sofort'">
                <p class="muted klein">
                  {{ g.gastgeber ? $t('abendmodus.gastgeberNichtDa', { name: hostName }) : $t('abendmodus.keinGastgeber') }}
                </p>
                <button class="small primary" :disabled="!!kiste.buehne" @click="uebernehmenUndOeffnen">
                  <Icon name="kiste" :size="14" /> {{ $t('abendmodus.uebernehmenUndOeffnen') }}
                </button>
              </template>
              <template v-else>
                <p class="muted klein">
                  {{ hostName ? $t('abendmodus.gastgeberOeffnetGleich', { name: hostName }) : $t('abendmodus.derGastgeberOeffnetGleich') }}
                </p>
                <button v-if="app.me && g.uebernehmen === 'abstimmung'" class="ghost small selbst" :title="$t('gastgeberleiste.dieAnwesendenStimmenAb')" @click="g.nehmen()">
                  {{ $t('abendmodus.selbstUebernehmen') }}
                </button>
              </template>
            </template>
            <template v-else>
              <p class="muted klein">{{ $t('abendmodus.nochNichtsVorgeschlagenSchnell') }}</p>
              <a href="#/finden" class="button small primary"><Icon name="suche" :size="14" /> {{ $t('abendtab.filmeFinden') }}</a>
            </template>
          </template>

          <template v-else>
            <template v-if="kino.live">
              <a href="#/kino" class="button small primary"><Icon name="kino" :size="14" /> {{ $t('abendmodus.zumKinoLaeuftSchon') }}</a>
            </template>
            <template v-else-if="gewinner">
              <div class="row">
                <button v-if="kino.enabled" class="small" @click="navigate('kino')"><Icon name="kino" :size="14" /> {{ $t('abendmodus.imKinoSchauen') }}</button>
                <button class="small" @click="eintragen"><Icon name="gesehen" :size="14" /> {{ $t('abendmodus.geschautEintragen') }}</button>
              </div>
            </template>
            <p v-else class="muted klein">{{ $t('abendmodus.sobaldDerFilmFeststeht') }}</p>
          </template>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.abendmodus {
  margin-bottom: 1rem; padding: 1rem 1.1rem; border-radius: 14px; border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--line));
  background: radial-gradient(120% 140% at 0% 0%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 60%), var(--bg-soft);
}
header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.9rem; font-size: 1.05rem; }
.heute { font-size: 0.7rem; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase; background: var(--accent); color: #fff; border-radius: 5px; padding: 3px 8px; }
.schritte { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.8rem; }
.schritte li { display: flex; gap: 0.7rem; padding: 0.8rem; border-radius: 10px; background: var(--bg); border: 1px solid var(--line); opacity: 0.6; transition: opacity 0.2s, border-color 0.2s; }
.schritte li.aktuell { opacity: 1; border-color: var(--accent); }
.schritte li.fertig { opacity: 0.9; }
.nr { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; font-weight: 800; font-size: 0.82rem; background: var(--bg-raised); border: 1px solid var(--line); }
.aktuell .nr { background: var(--accent); border-color: var(--accent); color: #fff; }
.fertig .nr { background: color-mix(in srgb, var(--ok) 25%, transparent); border-color: var(--ok); color: var(--ok); }
.inhalt { display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-start; min-width: 0; }
h3 { margin: 0.15rem 0 0; font-size: 0.95rem; }
.klein { font-size: 0.8rem; margin: 0; }
.avatars .avatar { width: 24px; height: 24px; font-size: 0.58rem; }
.film { display: flex; gap: 0.6rem; align-items: center; }
.film span:last-child { display: flex; flex-direction: column; font-size: 0.88rem; }
.plakat { width: 34px; height: 51px; border-radius: 4px; overflow: hidden; flex: none; background: var(--bg-raised); }
button.selbst { padding: 0.2rem 0; font-size: 0.78rem; color: var(--muted); }
button.selbst:hover { color: var(--text); }
a.button.small { padding: 0.3rem 0.6rem; font-size: 0.8rem; }
a.button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
@media (max-width: 800px) { .schritte { grid-template-columns: 1fr; } }
</style>