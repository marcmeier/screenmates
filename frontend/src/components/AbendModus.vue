<script setup>
import { t as tr } from '../i18n'
import { computed, onBeforeUnmount, ref } from 'vue'
import { api } from '../api'
import { useApp } from '../stores/app'
import { useKiste } from '../stores/kiste'
import { useGastgeber } from '../stores/gastgeber'
import { useKino } from '../stores/kino'
import { useUi } from '../stores/ui'
import { navigate } from '../composables/useRoute'
import { terminText } from '../einladung'
import { vorWann } from '../format'
import GastgeberLeiste from './GastgeberLeiste.vue'
import Icon from './Icon.vue'
import { audioJetzt } from '../audio'
import Poster from './Poster.vue'
import UserAvatar from './UserAvatar.vue'

// The evening itself, as three steps on the day of the date: who's here → what we watch → film on.
// On that day it is the only card for the evening: the replies sit in step one, inviting and
// the planning (change the date, calendar, the host's baton) behind "⋯" in the header.
const props = defineProps({ termin: { type: Object, required: true }, pool: { type: Array, default: () => [] } })
const emit = defineEmits(['geschaut', 'termin', 'einladen'])
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
// The header follows the clock: "tonight 20:00 · in 2 hours", then "running since 20:00".
const jetzt = ref(Date.now())
const uhr = setInterval(() => (jetzt.value = Date.now()), 30_000)
onBeforeUnmount(() => clearInterval(uhr))
const laeuft = computed(() => new Date(props.termin.termin).getTime() <= jetzt.value)
const bis = computed(() => (jetzt.value, vorWann(props.termin.termin)))
const mehr = ref(false)
const kalender = () => (window.location.href = '/api/termin.ics')
const andere = computed(() =>
  [
    app.vielleicht.length && tr('naechsterabend.sum.vielleicht', { n: app.vielleicht.length }),
    app.absagen.length && tr('naechsterabend.sum.absagen', { n: app.absagen.length }, app.absagen.length),
  ]
    .filter(Boolean)
    .join(' · '),
)
const kannNicht = () => app.antworten(app.me.rueckmeldung === 'nein' ? null : 'nein')
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
      <span v-if="laeuft" class="heute live"><span class="punkt" aria-hidden="true"></span>{{ $t('abendmodus.laeuftSeit', { zeit: t.zeit }) }}</span>
      <template v-else>
        <span class="heute">{{ $t('abendmodus.heuteAbend2') }}</span>
        <strong>{{ t.zeit }}</strong>
        <span class="muted bis">· {{ bis }}</span>
      </template>
      <span v-if="t.notiz" class="muted notiz">· {{ t.notiz }}</span>
      <span class="spacer"></span>
      <button class="small ghost" @click="emit('einladen')"><Icon name="teilen" :size="14" /> {{ $t('naechsterabend.einladen') }}</button>
      <button class="small ghost mehr" :aria-expanded="mehr" aria-controls="abend-mehr" :title="$t('naechsterabend.planung')" :aria-label="$t('naechsterabend.planung')" @click="mehr = !mehr">⋯</button>
    </header>
    <div v-if="mehr" id="abend-mehr" class="mehr-panel">
      <div class="row">
        <button class="small ghost" @click="emit('termin', 'fest')"><Icon name="kalender" :size="14" /> {{ $t('naechsterabend.aendern') }}</button>
        <button class="small ghost" :title="$t('naechsterabend.alsKalenderEintragHerunterladen')" @click="kalender"><Icon name="download" :size="14" /> {{ $t('naechsterabend.kalender') }}</button>
      </div>
      <GastgeberLeiste />
    </div>
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
            <p v-if="andere" class="muted klein">{{ andere }}</p>
            <div v-if="app.me" class="row antwort" role="group" :aria-label="$t('naechsterabend.bistDuDabei')">
              <button :class="app.me.dabei ? 'small on' : 'small primary'" :aria-pressed="app.me.dabei" @click="app.toggleDabei()">
                <Icon v-if="app.me.dabei" name="gesehen" :size="13" /> {{ app.me.dabei ? $t('abendmodus.duBistDa') : $t('abendmodus.ichBinDa') }}
              </button>
              <button class="small ghost nein" :class="{ on: app.me.rueckmeldung === 'nein' }" :aria-pressed="app.me.rueckmeldung === 'nein'" @click="kannNicht">
                {{ $t('naechsterabend.kannNicht') }}
              </button>
            </div>
          </template>

          <template v-else-if="s.key === 'film'">
            <div v-if="gewinner" class="film">
              <span class="plakat"><Poster :movie="gewinner" :title="false" /></span>
              <span><strong>{{ gewinner.title }}</strong><small class="muted">{{ $t('abendmodus.ausDerKiste') }}</small></span>
            </div>
            <template v-else-if="pool.length">
              <button v-if="kiste.darfOeffnen" class="kiste-knopf gross" :disabled="!!kiste.buehne" @click="audioJetzt(), kiste.oeffnen()">
                <Icon name="kiste" :size="18" /> {{ $t('abendmodus.kisteFuerAlleOeffnen') }}
              </button>
              <template v-else-if="app.me && g.uebernehmen === 'sofort'">
                <p class="muted klein">
                  {{ g.gastgeber ? $t('abendmodus.gastgeberNichtDa', { name: hostName }) : $t('abendmodus.keinGastgeber') }}
                </p>
                <button class="kiste-knopf gross" :disabled="!!kiste.buehne" @click="uebernehmenUndOeffnen">
                  <Icon name="kiste" :size="18" /> {{ $t('abendmodus.uebernehmenUndOeffnen') }}
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
header { display: flex; align-items: center; flex-wrap: wrap; gap: 0.4rem 0.6rem; margin-bottom: 0.9rem; font-size: 1.05rem; }
header .bis, header .notiz { font-size: 0.95rem; }
header button { font-size: 0.8rem; }
header .mehr { font-size: 1.1rem; line-height: 1; padding: 0.25rem 0.55rem; }
.live { display: inline-flex; align-items: center; gap: 0.4rem; }
.punkt { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: puls 1.6s ease-in-out infinite; }
@keyframes puls { 50% { opacity: 0.3; } }
.mehr-panel { display: flex; flex-direction: column; gap: 0.6rem; margin: -0.3rem 0 0.9rem; padding: 0.7rem 0.8rem; border-radius: 10px; background: var(--bg); border: 1px solid var(--line); }
.antwort { gap: 0.3rem; }
.antwort .on { border-color: var(--ok); color: var(--text); }
.antwort .nein.on { border-color: var(--accent); background: var(--accent-soft); }
@media (prefers-reduced-motion: reduce) { .punkt { animation: none; } }
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
@media (max-width: 800px) { .schritte { grid-template-columns: minmax(0, 1fr); } }
.kiste-knopf.gross { width: 100%; padding: 0.7rem 0.9rem; font-size: 0.95rem; border-radius: 10px; }
/* A step you can act on now is never dimmed – the case button must not look switched off. */
.schritte li:has(.kiste-knopf) { opacity: 1; }
</style>