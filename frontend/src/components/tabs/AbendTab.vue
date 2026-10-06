<script setup>
import { t as tr } from '../../i18n'
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
import { useMovieActions } from '../../composables/useMovieActions'
import { navigate } from '../../composables/useRoute'
import { dezimal } from '../../format'
import Erinnerungen from '../Erinnerungen.vue'
import Icon from '../Icon.vue'
import Poster from '../Poster.vue'
import KistenOeffnung from '../KistenOeffnung.vue'
import NaechsterAbend from '../NaechsterAbend.vue'
import ErsteSchritte from '../ErsteSchritte.vue'
import Erklaerung from '../Erklaerung.vue'
import AbendModus from '../AbendModus.vue'
import WieWars from '../WieWars.vue'
import { useKiste } from '../../stores/kiste'
import { seltenheitFuer } from '../../seltenheit'
import UserAvatar from '../UserAvatar.vue'

// Markdown rendering is only needed once there is info text; load it on demand.
const InfoCard = defineAsyncComponent(() => import('../InfoCard.vue'))
const Einladung = defineAsyncComponent(() => import('../Einladung.vue'))
const TerminDialog = defineAsyncComponent(() => import('../TerminDialog.vue'))

const app = useApp()
const kino = useKino()
const ui = useUi()
const kiste = useKiste()
const { alsGesehen } = useMovieActions()

const vorschlaege = ref([])
const pool = ref([])
const loading = ref(true)
// The film of the evening: the winner of the case opened for everyone.
const gewinner = computed(() => kiste.aktuell?.gewinner ?? null)
const termin = ref(null)
const erinnerungen = ref([])
const terminOffen = ref(null) // null | 'fest' | 'umfrage'
const einladungOffen = ref(false)
const umfrage = ref(null)
// December and January: the year in review is ready (see RueckblickView.vue).
const rueckblickJahr = ref(null)

async function load() {
  const [s, p, t, er, u] = await Promise.all([
    api.get('/api/suggestions'),
    api.get('/api/spin'),
    api.get('/api/termin'),
    api.get('/api/erinnerungen'),
    api.get('/api/termin/umfrage'),
  ])
  vorschlaege.value = s.suggestions
  pool.value = p.pool
  termin.value = t
  erinnerungen.value = er.erinnerungen
  umfrage.value = u
  loading.value = false
  extrasLaden()
}

// Per suggestion: what the group will think, and where it runs. Loaded after the list (TMDB, maths).
const prognosen = ref({})
const prognoseFuer = ref('gruppe')
const anbieter = ref({})
async function extrasLaden() {
  if (!vorschlaege.value.length) return
  api.get('/api/suggestions/prognose', { quiet: true }).then((r) => {
    prognosen.value = r.prognosen
    prognoseFuer.value = r.fuer
  }).catch(() => {})
  api.get('/api/suggestions/anbieter', { quiet: true }).then((r) => (anbieter.value = r.anbieter)).catch(() => {})
}
const prognoseTitel = (p) =>
  p.personen
    .map((x) => `${app.userById(x.user_id)?.name ?? '?'}: ${dezimal(x.sterne)} ★${x.echt ? ` (${tr('abendtab.bewertet')})` : ''}`)
    .join('\n')
const WEG_TEXT = { abo: '', kostenlos: tr('abendtab.kostenlos'), leihen: tr('abendtab.leihen'), kaufen: tr('abendtab.kaufen') }
function wegText(w) {
  const bei = w.bei.map((id) => app.userById(id)?.name).filter(Boolean)
  return `${WEG_TEXT[w.art]}${w.name}${bei.length ? ` · ${bei.join(', ')}` : ''}`
}
// The case's odds, right at the suggestion (vetoed films aren't in the case).
const poolGesamt = computed(() => pool.value.reduce((s, m) => s + m.gewicht, 0) || 1)
const chance = (m) => {
  const p = pool.value.find((x) => x.id === m.id)
  return p ? p.gewicht / poolGesamt.value : null
}

// On the day itself the page leads through the evening (see AbendModus.vue), and that card
// replaces the planning one – until the film is logged as watched. A start before midnight still
// counts after it; the server drops the date six hours after the start anyway.
const tagFmt = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin' })
const heuteAbend = computed(() => {
  const t = termin.value?.termin
  if (!t || termin.value.geschaut) return false
  return tagFmt.format(new Date(t)) === tagFmt.format(new Date()) || new Date(t) <= new Date()
})

async function rueckblickPruefen() {
  const monat = new Date().getMonth() // 0 = January
  if (monat !== 11 && monat !== 0) return
  const jahr = new Date().getFullYear() - (monat === 0 ? 1 : 0)
  const r = await api.get('/api/rueckblick', { quiet: true }).catch(() => null)
  if (r?.jahre.includes(jahr)) rueckblickJahr.value = jahr
}
onMounted(rueckblickPruefen)
function umfrageGestartet(u) {
  umfrage.value = u
  terminOffen.value = null
}
function festgelegt(r) {
  termin.value = r.termin
  umfrage.value = r.umfrage
}

// The invitation shows what's really up for the vote: no vetoed films.
const zurWahl = computed(() => vorschlaege.value.filter((m) => !m.veto_von.length))
onMounted(load)
watch(() => ui.changes, load)

const meinVorschlag = (m) => app.me && m.von.includes(app.me.id)
const meinVeto = (m) => app.me && m.veto_von.includes(app.me.id)
const ichSchlageVor = computed(() => vorschlaege.value.some((m) => meinVorschlag(m)))
const vetoVerbraucht = computed(() => app.me && vorschlaege.value.some((m) => meinVeto(m)))
const namen = (ids) => ids.map((id) => app.userById(id)?.name ?? '?').join(', ')

// One veto per person: setting it on another film moves it there.
async function veto(m) {
  if (meinVeto(m)) {
    await api.del('/api/veto')
    ui.toast(tr('abendtab.vetoGegenTitleZurueckgenommen', { title: m.title }))
  } else {
    await api.post('/api/veto', { movie_id: m.id })
    ui.toast(tr('abendtab.vetoGegenTitleEr', { title: m.title }), 'ok')
  }
  ui.changed()
}

async function toggle(m) {
  if (meinVorschlag(m)) await api.del(`/api/suggestions/${m.id}`)
  else await api.post('/api/suggestions', { movie_id: m.id })
  ui.changed()
}

async function allesLeeren() {
  if (!confirm(tr('abendtab.alleVorschlaegeLoeschenDas'))) return
  await api.del('/api/suggestions/alle')
  ui.toast(tr('abendtab.vorschlaegeGeleert'))
  ui.changed()
}

async function gewinnerGesehen() {
  await alsGesehen(gewinner.value)
  kiste.aktuell = null
}

const poolQuelle = computed(() => (vorschlaege.value.length ? 'vorschlaege' : 'merkliste'))
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>{{ $t('nav.abend') }}</h1>
        <p>{{ $t('abendtab.wannIstDerNaechste') }}</p>
      </div>
    </header>

    <a v-if="kino.live" href="#/kino" class="onair">
      <span class="badge"><span class="dot"></span>LIVE</span>
      <span>{{ $t('abendtab.jetztImKino') }} <strong>{{ kino.titel || $t('abendtab.uebertragungLaeuft') }}</strong></span>
      <span class="spacer"></span>
      <span class="go">{{ $t('abendtab.zuschauen') }} <Icon name="kino" :size="16" /></span>
    </a>

    <a v-if="rueckblickJahr" :href="`#/sammlung/rueckblick/${rueckblickJahr}`" class="rueckblick-teaser">
      <Icon name="funken" :size="20" />
      <span><strong>{{ $t('abendtab.euerFilmjahrRueckblickjahrIst', { rueckblickJahr }) }}</strong> {{ $t('abendtab.dieBestenFilmeDie') }}</span>
      <span class="spacer"></span>
      <span class="go">{{ $t('abendtab.rueckblickAnsehen') }}</span>
    </a>

    <WieWars v-if="app.me" />
    <ErsteSchritte v-if="app.me && !loading" :termin="termin" :vorgeschlagen="ichSchlageVor" />
    <AbendModus
      v-if="heuteAbend && app.me"
      :termin="termin"
      :pool="pool"
      @geschaut="load"
      @termin="(m) => (terminOffen = m)"
      @einladen="einladungOffen = true"
    />

    <NaechsterAbend
      v-else
      :termin="termin"
      :umfrage="umfrage"
      @termin="(m) => (terminOffen = m)"
      @einladen="einladungOffen = true"
      @umfrage="(u) => (umfrage = u)"
      @festgelegt="festgelegt"
    />
    <TerminDialog
      v-if="terminOffen"
      :termin="termin"
      :modus="terminOffen"
      @close="terminOffen = null"
      @saved="(t) => ((termin = t), (terminOffen = null))"
      @umfrage="umfrageGestartet"
    />
    <Einladung v-if="einladungOffen" :termin="termin" :filme="zurWahl" :dabei="app.dabei" @close="einladungOffen = false" />

    <section class="teil auswahl" aria-labelledby="auswahl-titel">
      <header class="teil-kopf">
        <h2 id="auswahl-titel">{{ $t('abendtab.wasSchauenWir') }}</h2>
        <p class="muted">{{ $t('abendtab.schlagtFilmeVorLegt') }}</p>
      </header>
      <div class="layout">
        <section>
          <div class="row unterkopf">
            <h3>{{ $t('abendtab.vorschlaege') }}<Erklaerung :label="$t('abendtab.vorschlaege')" :text="$t('erklaerung.vorschlaege')" /></h3>
            <span class="spacer"></span>
            <button v-if="app.gruppenAdmin && vorschlaege.length" class="ghost small danger" @click="allesLeeren">
              <Icon name="muell" :size="14" /> {{ $t('abendtab.alleLeeren') }}
            </button>
          </div>

          <p v-if="app.me && vorschlaege.length" class="muted small-text veto-hint">
            {{ $t('abendtab.jedePersonHatEin') }} <strong>{{ $t('abendtab.veto') }}</strong>{{ $t('abendtab.filmeMitVetoKommen') }}<Erklaerung :label="$t('abendtab.veto')" :text="$t('erklaerung.veto')" />
          </p>
          <div v-if="loading" class="list">
            <div v-for="i in 3" :key="i" class="skeleton" style="height: 86px"></div>
          </div>
          <div v-else-if="!vorschlaege.length" class="empty">
            <strong>{{ $t('abendtab.nochKeineVorschlaege') }}</strong>
            {{ $t('abendtab.beiJedemFilmGibt') }} <Icon name="hand" :size="14" />{{ $t('abendtab.knopf') }}
            <div style="margin-top: 0.8rem"><button class="small" @click="navigate('finden')">{{ $t('abendtab.filmeFinden') }}</button></div>
          </div>
          <ol v-else class="list">
            <li v-for="(m, i) in vorschlaege" :key="m.id" class="sugg" :class="{ vetoed: m.veto_von.length }">
              <span class="rank">{{ i + 1 }}</span>
              <button class="thumb" :aria-label="$t('abendtab.titleDetails', { title: m.title })" @click="ui.open(m)">
                <Poster :movie="m" :title="false" />
              </button>
              <div class="what">
                <button class="linklike" @click="ui.open(m)">{{ m.title }}</button>
                <!-- One quiet line of facts, then who suggested it and where it runs. -->
                <div class="muted meta">
                  {{ m.year }} · ★ {{ dezimal(m.vote_average) }}
                  <template v-if="chance(m) != null">
                    · <span class="chance-text" :style="{ '--farbe': seltenheitFuer(chance(m)).farbe }" :title="$t('abendtab.xSoWahrscheinlichZieht', { x: seltenheitFuer(chance(m)).name })"><Icon name="kiste" :size="12" /> {{ Math.round(chance(m) * 100) }} %</span>
                  </template>
                  <template v-if="prognosen[m.id]">
                    · <span class="prognose-text" :title="prognoseTitel(prognosen[m.id])">{{ $t(prognoseFuer === 'dabei' ? 'abendtab.prognoseHeute' : 'abendtab.prognose', { wert: dezimal(prognosen[m.id].wert) }) }}</span>
                  </template>
                </div>
                <div class="infos">
                  <span class="avatars"><UserAvatar v-for="id in m.von" :key="id" :user-id="id" /></span>
                  <span v-if="anbieter[m.id]" class="merkmal weg" :class="{ unser: anbieter[m.id].bei.length }">
                    <img v-if="anbieter[m.id].logo" :src="anbieter[m.id].logo" alt="" />{{ wegText(anbieter[m.id]) }}
                  </span>
                </div>
                <div v-if="m.veto_von.length" class="veto-info"><Icon name="veto" :size="13" /> {{ $t('abendtab.vetoVonX', { x: namen(m.veto_von) }) }}</div>
              </div>
              <div v-if="app.me" class="buttons">
                <button
                  class="small mit"
                  :class="{ on: meinVorschlag(m) }"
                  :aria-pressed="meinVorschlag(m)"
                  :title="meinVorschlag(m) ? $t('abendtab.zurueckziehen') : '+1'"
                  @click="toggle(m)"
                >
                  <Icon name="hand" :size="14" /> <span class="lbl">{{ meinVorschlag(m) ? $t('abendtab.zurueckziehen') : '+1' }}</span>
                </button>
                <button
                  class="small ghost veto"
                  :class="{ on: meinVeto(m) }"
                  :aria-pressed="meinVeto(m)"
                  :title="meinVeto(m) ? $t('abendtab.vetoZuruecknehmen') : vetoVerbraucht ? $t('abendtab.deinVetoHierherVerschieben') : $t('abendtab.nichtMitMirDer')"
                  @click="veto(m)"
                >
                  <Icon name="veto" :size="14" /> <span class="lbl">{{ meinVeto(m) ? $t('abendtab.vetoZurueck') : $t('abendtab.veto2') }}</span>
                </button>
              </div>
            </li>
          </ol>

        </section>
        <aside class="side">
          <div class="panel wheelbox">
            <h3>{{ $t('abendtab.filmabendKiste') }}<Erklaerung :label="$t('abendtab.filmabendKiste')" :text="$t('erklaerung.kiste')" /></h3>
            <template v-if="pool.length">
              <p class="muted small-text">
                {{ $t(`abendtab.poolAus.${poolQuelle}`, { n: pool.length }, pool.length) }}
                <template v-if="vorschlaege.length">{{ $t('abendtab.dieChancenStehenBei') }}</template>
                <template v-else>{{ $t('abendtab.jeSeltenerDieFarbe') }}</template>
              </p>
              <KistenOeffnung :pool="pool" :kompakt="vorschlaege.length > 0" />
            </template>
            <p v-else-if="vorschlaege.length" class="muted">{{ $t('abendtab.gegenAlleVorschlaegeGibt') }}</p>
            <p v-else class="muted">{{ $t('abendtab.sobaldEsVorschlaegeOder') }}</p>

            <div v-if="gewinner && !kiste.buehne" class="winner" role="status">
              <span class="muted small-text">{{ $t('abendtab.filmDesAbends') }}<template v-if="app.userById(kiste.aktuell.von)"> {{ $t('abendtab.ausDerKisteVon', { x: app.userById(kiste.aktuell.von).name }) }}</template></span>
              <strong>{{ gewinner.title }}</strong>
              <div class="row">
                <button class="small" @click="ui.open(gewinner)">{{ $t('abendtab.details') }}</button>
                <button v-if="app.me" class="small primary" @click="gewinnerGesehen"><Icon name="gesehen" :size="14" /> {{ $t('abendtab.geschaut') }}</button>
                <button v-if="kiste.darfOeffnen" class="ghost small" @click="kiste.zuruecknehmen()">{{ $t('abendtab.zuruecknehmen') }}</button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <footer class="fuss" :class="{ zwei: erinnerungen.length }">
      <InfoCard />
      <Erinnerungen v-if="erinnerungen.length" :erinnerungen="erinnerungen" />
    </footer>
  </div>
</template>

<style scoped>
.rueckblick-teaser {
  display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem; padding: 0.85rem 1rem; text-decoration: none;
  border-radius: var(--radius); border: 1px solid color-mix(in srgb, var(--gold) 45%, transparent);
  background: linear-gradient(100deg, color-mix(in srgb, var(--gold) 20%, transparent), color-mix(in srgb, var(--accent) 12%, transparent));
}
.rueckblick-teaser svg { color: var(--gold); flex: none; }
.rueckblick-teaser .go { font-weight: 600; white-space: nowrap; }
.rueckblick-teaser:hover { border-color: var(--gold); }
@media (max-width: 600px) {
  .rueckblick-teaser .go { display: none; }
}
.onair {
  display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem; padding: 0.8rem 1rem; text-decoration: none;
  border-radius: var(--radius); background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 22%, transparent), color-mix(in srgb, var(--accent) 6%, transparent)); border: 1px solid rgba(229, 9, 20, 0.45);
}
.onair:hover { border-color: var(--accent); }
.onair .badge { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; padding: 3px 8px; border-radius: 5px; }
.onair .dot { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: blink 1.4s ease-in-out infinite; }
@keyframes blink { 50% { opacity: 0.3; } }
.onair .go { display: inline-flex; align-items: center; gap: 0.4rem; font-weight: 600; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 2rem; align-items: start; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.6rem; }
.veto-hint { margin: -0.4rem 0 0.8rem; }
.sugg.vetoed { opacity: 0.55; }
.sugg.vetoed .linklike { text-decoration: line-through; }
.veto-info { display: inline-flex; align-items: center; gap: 4px; font-size: 0.78rem; color: var(--accent); }
.infos { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 2px; }
.merkmal {
  display: inline-flex; align-items: center; gap: 4px; font-size: 0.72rem; padding: 1px 7px; border-radius: 999px;
  border: 1px solid var(--line); color: var(--muted); white-space: nowrap;
}
.merkmal img { width: 14px; height: 14px; border-radius: 3px; }
/* Long ones (a service with names) end in … instead of widening the page. */
.merkmal { max-width: 100%; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.merkmal.chance { color: var(--text); border-color: color-mix(in srgb, var(--farbe) 60%, transparent); background: color-mix(in srgb, var(--farbe) 16%, transparent); }
.merkmal.prognose { color: var(--gold); border-color: color-mix(in srgb, var(--gold) 45%, transparent); }
.merkmal.weg.unser { color: var(--ok); border-color: color-mix(in srgb, var(--ok) 45%, transparent); }
.sugg.vetoed .infos { display: none; }
.buttons { display: flex; flex-direction: column; gap: 0.3rem; align-items: stretch; }
.veto.on { color: #fff; }
.sugg { display: flex; align-items: center; gap: 0.9rem; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.6rem 0.9rem 0.6rem 0.6rem; }
.rank { width: 1.6rem; text-align: center; font-weight: 800; color: var(--muted); font-size: 1.1rem; }
.sugg:first-child .rank { color: var(--text); }
.thumb { padding: 0; width: 46px; height: 69px; border-radius: 6px; overflow: hidden; flex: none; background: var(--bg-raised); }
.what { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.linklike {
  padding: 0; border: none; background: none; font-weight: 600; font-size: 0.98rem; text-align: left; line-height: 1.3;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.meta { font-size: 0.82rem; display: flex; flex-wrap: wrap; align-items: center; gap: 0 0.3rem; }
.chance-text { display: inline-flex; align-items: center; gap: 3px; color: color-mix(in srgb, var(--farbe) 55%, var(--text)); font-weight: 600; }
.prognose-text { color: var(--gold); }
.infos .avatars { display: inline-flex; margin-right: 0.2rem; }
/* Suggested by me: a calm green tick-state – red is kept for what matters most. */
.buttons .mit.on { border-color: color-mix(in srgb, var(--ok) 55%, var(--line)); background: color-mix(in srgb, var(--ok) 12%, transparent); color: var(--text); }
@media (max-width: 600px) {
  .sugg { gap: 0.6rem; padding: 0.55rem 0.6rem 0.55rem 0.4rem; }
  .rank { width: 1.1rem; font-size: 0.95rem; }
  .thumb { width: 40px; height: 60px; }
  .buttons .lbl { display: none; }
  .buttons button { width: 40px; height: 36px; padding: 0; justify-content: center; }
}
.linklike:hover { background: none; text-decoration: underline; }
.small-text { font-size: 0.8rem; }
.avatars .avatar { width: 22px; height: 22px; font-size: 0.6rem; }
.side { min-width: 0; }
/* The page in three parts: the next evening, what we watch, and the extras at the foot. */
.teil { margin-top: 2.2rem; }
.teil-kopf { display: flex; align-items: baseline; gap: 0.4rem 1rem; flex-wrap: wrap; margin-bottom: 1rem; padding-bottom: 0.7rem; border-bottom: 1px solid var(--line); }
.teil-kopf h2 { margin: 0; font-size: 1.3rem; letter-spacing: -0.01em; }
.teil-kopf p { margin: 0; font-size: 0.9rem; }
h3 { margin: 0 0 0.6rem; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 600; }
.unterkopf h3 { margin: 0; }
.unterkopf { margin-bottom: 0.6rem; }
.fuss { margin-top: 2.6rem; padding-top: 1.2rem; border-top: 1px solid var(--line); display: grid; gap: 1.2rem; }
.fuss.zwei { grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); align-items: start; }
.fuss :deep(.info) { margin-top: 0; }
@media (max-width: 900px) { .fuss.zwei { grid-template-columns: minmax(0, 1fr); } }
.winner { margin-top: 1.2rem; border-top: 1px solid var(--line); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.4rem; text-align: center; align-items: center; }
.winner strong { font-size: 1.3rem; }
@media (max-width: 1100px) {
  .layout { grid-template-columns: minmax(0, 1fr); }
  .side { order: -1; }
}
</style>
