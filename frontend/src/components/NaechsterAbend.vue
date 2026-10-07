<script setup>
import { t as tr } from '../i18n'
import { computed, ref, watch } from 'vue'
import { useApp } from '../stores/app'
import { terminText } from '../einladung'
import GastgeberLeiste from './GastgeberLeiste.vue'
import Icon from './Icon.vue'
import TerminUmfrage from './TerminUmfrage.vue'
import UserAvatar from './UserAvatar.vue'

// The next movie night in one line: when, who's in, your answer. The planning (date,
// poll, replies, host) folds away once nothing is waiting for you – and opens by
// itself when something is: no answer yet, a poll to vote on or to decide.
const props = defineProps({
  termin: { type: Object, default: null },
  umfrage: { type: Object, default: null },
})
const emit = defineEmits(['termin', 'einladen', 'umfrage', 'festgelegt'])
const app = useApp()

const t = computed(() => terminText(props.termin))
const vorschlaege = computed(() => props.umfrage?.vorschlaege ?? [])
const umfrageOffen = computed(() => vorschlaege.value.length > 0)
const tag = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin' })
const heute = computed(() => props.termin?.termin && tag.format(new Date(props.termin.termin)) === tag.format(new Date()))

const brauchtDich = computed(() => {
  if (!app.me) return false
  if (t.value && !app.me.rueckmeldung) return true
  // On the day itself the evening leads (AbendModus); a poll for later can wait folded.
  if (heute.value) return false
  return umfrageOffen.value && (vorschlaege.value.some((v) => !v.meine) || props.umfrage.darf_festlegen)
})
// Your own click wins until the plan changes (another date, another poll).
const manuell = ref(null)
const stand = computed(() => [props.termin?.termin, vorschlaege.value.map((v) => v.id).join()].join('|'))
watch(stand, () => (manuell.value = null))
const offen = computed(() => manuell.value ?? brauchtDich.value)

const ANTWORTEN = [
  { key: 'vielleicht', label: tr('naechsterabend.vielleicht'), icon: 'fragezeichen' },
  { key: 'nein', label: tr('naechsterabend.kannNicht'), icon: 'x' },
]
const antworten = (key) => app.antworten(app.me.rueckmeldung === key ? null : key)
const kalender = () => (window.location.href = '/api/termin.ics')
const namen = (us) => us.map((u) => u.name).join(', ')
const zusammenfassung = computed(() =>
  [
    // A few names say more than a number.
    app.dabei.length && tr('naechsterabend.sum.dabei', { wer: app.dabei.length <= 3 ? namen(app.dabei) : app.dabei.length }),
    app.vielleicht.length && tr('naechsterabend.sum.vielleicht', { n: app.vielleicht.length }),
    app.absagen.length && tr('naechsterabend.sum.absagen', { n: app.absagen.length }, app.absagen.length),
  ]
    .filter(Boolean)
    .join(' · '),
)
</script>

<template>
  <section class="panel crew" :class="{ offen, heute }" :aria-label="$t('naechsterabend.naechsterFilmabend')">
    <div class="zeile">
      <div class="wann">
        <span v-if="heute" class="heute-badge">{{ $t('naechsterabend.heute') }}</span>
        <Icon v-else name="kalender" :size="17" class="muted" />
        <span v-if="t" class="termin"><strong>{{ t.tag }}</strong>, {{ t.zeit }}<span v-if="t.notiz" class="muted"><span class="trenner"> · </span>{{ t.notiz }}</span></span>
        <span v-else-if="umfrageOffen" class="muted">{{ $t('naechsterabend.terminWirdAbgestimmt') }}</span>
        <span v-else class="muted">{{ $t('naechsterabend.nochNichtsGeplant') }}</span>
        <span v-if="t && umfrageOffen" class="chip klein">{{ $t('naechsterabend.umfrageLaeuft') }}</span>
      </div>
      <span v-if="zusammenfassung" class="wer" :title="namen(app.dabei)">
        <span class="avatars"><UserAvatar v-for="u in app.dabei.slice(0, 6)" :key="u.id" :user="u" /></span>
        <span class="muted">{{ zusammenfassung }}</span>
      </span>
      <span class="spacer"></span>
      <div v-if="app.me" class="rsvp" role="group" :aria-label="$t('naechsterabend.bistDuDabei')">
        <button :class="app.me.dabei ? 'on' : 'primary'" :aria-pressed="app.me.dabei" @click="app.toggleDabei()">
          <Icon :name="app.me.dabei ? 'gesehen' : 'plus'" :size="16" />
          {{ app.me.dabei ? $t('naechsterabend.ichBinDabei') : $t('naechsterabend.ichBinDabei2') }}
        </button>
        <button
          v-for="a in ANTWORTEN"
          :key="a.key"
          class="ghost"
          :class="[a.key, { on: app.me.rueckmeldung === a.key }]"
          :aria-pressed="app.me.rueckmeldung === a.key"
          @click="antworten(a.key)"
        >
          <Icon :name="a.icon" :size="15" /> {{ a.label }}
        </button>
      </div>
      <div class="aktionen">
        <button class="small" :title="$t('naechsterabend.einladen')" @click="emit('einladen')"><Icon name="teilen" :size="14" /> <span class="lbl">{{ $t('naechsterabend.einladen') }}</span></button>
        <button v-if="app.me" class="small ghost auf" :aria-expanded="offen" aria-controls="planung" @click="manuell = !offen">
          <span class="lbl">{{ $t('naechsterabend.planung') }}</span><span class="mehr-punkte" aria-hidden="true">⋯</span> <Icon name="pfeil" :size="14" class="pfeil" />
        </button>
      </div>
    </div>

    <div v-if="app.me && !t && !umfrageOffen && !offen" class="row leer">
      <button class="small" @click="emit('termin', 'fest')"><Icon name="kalender" :size="14" /> {{ $t('naechsterabend.terminFestlegen') }}</button>
      <button class="small ghost" @click="emit('termin', 'umfrage')"><Icon name="umfrage" :size="14" /> {{ $t('naechsterabend.abstimmen') }}</button>
    </div>

    <div v-if="offen" id="planung" class="details">
      <div class="row">
        <span class="muted">{{ $t('naechsterabend.dabei') }}</span>
        <template v-if="app.dabei.length">
          <span v-for="u in app.dabei" :key="u.id" class="chip who"><UserAvatar :user="u" link /> {{ u.name }}</span>
        </template>
        <span v-else class="muted">{{ $t('naechsterabend.nochNiemand') }}</span>
      </div>
      <div v-if="app.vielleicht.length || app.absagen.length" class="row andere muted">
        <template v-if="app.vielleicht.length">
          <span>{{ $t('naechsterabend.vielleicht2') }}</span>
          <span class="namen">{{ namen(app.vielleicht) }}</span>
        </template>
        <template v-if="app.absagen.length">
          <span>{{ $t('naechsterabend.kannNicht2') }}</span>
          <span class="namen">{{ namen(app.absagen) }}</span>
        </template>
      </div>
      <div class="row knoepfe">
        <button class="small ghost" @click="emit('termin', 'fest')"><Icon name="kalender" :size="14" /> {{ t ? $t('naechsterabend.aendern') : $t('naechsterabend.terminFestlegen') }}</button>
        <button v-if="!umfrageOffen" class="small ghost" @click="emit('termin', 'umfrage')"><Icon name="umfrage" :size="14" /> {{ $t('naechsterabend.abstimmen') }}</button>
        <button v-if="t" class="small ghost" :title="$t('naechsterabend.alsKalenderEintragHerunterladen')" @click="kalender"><Icon name="download" :size="14" /> {{ $t('naechsterabend.kalender') }}</button>
      </div>
      <TerminUmfrage v-if="umfrageOffen" :umfrage="umfrage" @update="(u) => emit('umfrage', u)" @festgelegt="(r) => emit('festgelegt', r)" />
      <GastgeberLeiste />
    </div>
  </section>
</template>

<style scoped>
.crew { margin-bottom: 0.5rem; display: flex; flex-direction: column; gap: 0.6rem; padding: 0.75rem 1rem; }
.crew.heute { border-color: color-mix(in srgb, var(--accent) 50%, var(--line)); }
.zeile { display: flex; align-items: center; gap: 0.6rem 1rem; flex-wrap: wrap; }
.wann { display: flex; align-items: center; gap: 0.5rem; font-size: 0.95rem; min-width: 0; }
.heute-badge {
  font-size: 0.68rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #fff;
  background: var(--accent); border-radius: 5px; padding: 2px 7px;
}
.chip.klein { font-size: 0.72rem; padding: 1px 8px; }
.wer { display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.82rem; }
.wer .avatars .avatar { width: 22px; height: 22px; font-size: 0.55rem; }
.rsvp { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.rsvp button { padding: 0.4rem 0.75rem; font-size: 0.85rem; }
.rsvp .vielleicht.on { color: var(--text); border-color: var(--gold); background: color-mix(in srgb, var(--gold) 14%, transparent); }
.rsvp .nein.on { color: var(--text); border-color: var(--accent); background: var(--accent-soft); }
.aktionen { display: flex; gap: 0.3rem; margin-left: auto; }
.pfeil { transform: rotate(-90deg); transition: transform 0.2s; }
.offen .pfeil { transform: rotate(90deg); }
.leer { gap: 0.4rem; }
.details { display: flex; flex-direction: column; gap: 0.6rem; border-top: 1px solid var(--line); padding-top: 0.7rem; animation: auf 0.18s ease-out; }
@keyframes auf { from { opacity: 0; transform: translateY(-4px); } }
.who { padding: 2px 10px 2px 2px; color: var(--text); }
.who .avatar { width: 22px; height: 22px; }
.andere { font-size: 0.82rem; gap: 0.45rem; }
.andere .namen { margin-right: 0.8rem; }
.knoepfe { gap: 0.3rem; }
/* Phones: one tidy block – when (with invite/planning as icons beside it), who's in,
   and the answer as one segmented bar instead of loose buttons. */
.mehr-punkte { display: none; }
@media (max-width: 600px) {
  .crew { padding: 0.75rem 0.8rem; gap: 0.55rem; }
  .zeile { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 0.5rem; align-items: center; }
  .wann { grid-column: 1; grid-row: 1; font-size: 0.9rem; min-width: 0; }
  .wann > svg { display: none; }
  .termin { min-width: 0; }
  /* the place/note gets its own short line instead of wrapping into the date */
  .termin .trenner { display: none; }
  .termin .muted { display: block; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .aktionen { grid-column: 2; grid-row: 1; margin: 0; gap: 0.2rem; }
  .aktionen .lbl, .aktionen .pfeil { display: none; }
  .aktionen button { width: 36px; height: 34px; padding: 0; justify-content: center; }
  .mehr-punkte { display: inline; font-size: 1.1rem; line-height: 1; }
  .wer { grid-column: 1 / -1; grid-row: 2; }
  .zeile > .spacer { display: none; }
  .rsvp {
    grid-column: 1 / -1; grid-row: 3; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0;
    border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }
  .rsvp button { border: none; border-radius: 0; justify-content: center; padding: 0.55rem 0.3rem; font-size: 0.82rem; white-space: nowrap; gap: 0.3rem; }
  .rsvp button + button { border-left: 1px solid var(--line); }
  .leer { display: grid; grid-template-columns: 1fr 1fr; }
  .leer button { justify-content: center; }
}
@media (prefers-reduced-motion: reduce) { .details { animation: none; } .pfeil { transition: none; } }
</style>