<script setup>
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { api } from '../../api'
import { useApp } from '../../stores/app'
import { useKino } from '../../stores/kino'
import { useUi } from '../../stores/ui'
import { useMovieActions } from '../../composables/useMovieActions'
import { navigate } from '../../composables/useRoute'
import { dezimal, vorWann } from '../../format'
import { terminText } from '../../einladung'
import Erinnerungen from '../Erinnerungen.vue'
import Icon from '../Icon.vue'
import Poster from '../Poster.vue'
import KistenOeffnung from '../KistenOeffnung.vue'
import GastgeberLeiste from '../GastgeberLeiste.vue'
import TerminUmfrage from '../TerminUmfrage.vue'
import { useKiste } from '../../stores/kiste'
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
const events = ref([])
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
  const [s, p, e, t, er, u] = await Promise.all([
    api.get('/api/suggestions'),
    api.get('/api/spin'),
    api.get('/api/events?limit=15'),
    api.get('/api/termin'),
    api.get('/api/erinnerungen'),
    api.get('/api/termin/umfrage'),
  ])
  vorschlaege.value = s.suggestions
  pool.value = p.pool
  events.value = e.events
  termin.value = t
  erinnerungen.value = er.erinnerungen
  umfrage.value = u
  loading.value = false
}
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

const ANTWORTEN = [
  { key: 'vielleicht', label: 'Vielleicht', icon: 'fragezeichen' },
  { key: 'nein', label: 'Kann nicht', icon: 'x' },
]
function antworten(key) {
  app.antworten(app.me.rueckmeldung === key ? null : key)
}
function kalender() {
  window.location.href = '/api/termin.ics'
}
const terminAnzeige = computed(() => terminText(termin.value))
// The invitation shows what's really up for the vote: no vetoed films.
const zurWahl = computed(() => vorschlaege.value.filter((m) => !m.veto_von.length))
onMounted(load)
watch(() => ui.changes, load)

const meinVorschlag = (m) => app.me && m.von.includes(app.me.id)
const meinVeto = (m) => app.me && m.veto_von.includes(app.me.id)
const vetoVerbraucht = computed(() => app.me && vorschlaege.value.some((m) => meinVeto(m)))
const namen = (ids) => ids.map((id) => app.userById(id)?.name ?? '?').join(', ')

// One veto per person: setting it on another film moves it there.
async function veto(m) {
  if (meinVeto(m)) {
    await api.del('/api/veto')
    ui.toast(`Veto gegen „${m.title}“ zurückgenommen`)
  } else {
    await api.post('/api/veto', { movie_id: m.id })
    ui.toast(`Veto gegen „${m.title}“ – er kommt nicht in die Kiste`, 'ok')
  }
  ui.changed()
}

async function toggle(m) {
  if (meinVorschlag(m)) await api.del(`/api/suggestions/${m.id}`)
  else await api.post('/api/suggestions', { movie_id: m.id })
  ui.changed()
}

async function allesLeeren() {
  if (!confirm('Alle Vorschläge löschen? Das betrifft alle.')) return
  await api.del('/api/suggestions/alle')
  ui.toast('Vorschläge geleert')
  ui.changed()
}

async function gewinnerGesehen() {
  await alsGesehen(gewinner.value)
  kiste.aktuell = null
}

const poolQuelle = computed(() => (vorschlaege.value.length ? 'Vorschlägen' : 'der Merkliste'))
const EVENT_TEXT = {
  gesehen: (e) => `„${e.film}“ wurde geschaut`,
  vorschlag: (e) => `${e.wer ?? 'Jemand'} schlägt „${e.film}“ vor`,
  kommentar: (e) => `${e.wer ?? 'Jemand'}: „${e.text}“`,
  wunsch: (e) => `${e.wer ?? 'Jemand'} wünscht sich: ${e.text}`,
  veto: (e) => `${e.wer ?? 'Jemand'} legt ein Veto gegen „${e.film}“ ein`,
  erfolg: (e) => `${e.emoji} ${e.wer ?? 'Jemand'} hat ${e.name} freigeschaltet`,
  gastgeber: (e) =>
    e.art === 'uebergabe'
      ? `${e.von ?? 'Jemand'} gibt den Gastgeber-Stab an ${e.wer ?? 'jemanden'}`
      : e.art === 'abstimmung'
        ? `${e.wer ?? 'Jemand'} ist Gastgeber – per Abstimmung (${e.stand})`
        : `${e.wer ?? 'Jemand'} übernimmt den Gastgeber-Stab`,
  kiste: (e) => `${e.wer ?? 'Jemand'} öffnet die Kiste: „${e.film}“`,
  termin: (e) => {
    const t = terminText({ termin: e.termin })
    return `${e.wer ?? 'Jemand'} legt den Termin fest: ${t.tag}, ${t.zeit}`
  },
  umfrage: (e) => {
    const t = terminText({ termin: e.termin })
    return `${e.wer ?? 'Jemand'} schlägt einen Termin zur Abstimmung vor: ${t.tag}, ${t.zeit}`
  },
}
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>Nächster Filmabend</h1>
        <p>Wer ist dabei, was steht zur Wahl – und am Ende entscheidet die Kiste.</p>
      </div>
    </header>

    <a v-if="kino.live" href="#/kino" class="onair">
      <span class="badge"><span class="dot"></span>LIVE</span>
      <span>Jetzt im Kino: <strong>{{ kino.titel || 'Übertragung läuft' }}</strong></span>
      <span class="spacer"></span>
      <span class="go">Zuschauen <Icon name="kino" :size="16" /></span>
    </a>

    <a v-if="rueckblickJahr" :href="`#/sammlung/rueckblick/${rueckblickJahr}`" class="rueckblick-teaser">
      <Icon name="funken" :size="20" />
      <span><strong>Euer Filmjahr {{ rueckblickJahr }} ist da</strong> – die besten Filme, die strengste Kritik, eure Rekorde.</span>
      <span class="spacer"></span>
      <span class="go">Rückblick ansehen</span>
    </a>

    <section class="panel crew">
      <div class="row">
        <span class="muted">Dabei:</span>
        <template v-if="app.dabei.length">
          <span v-for="u in app.dabei" :key="u.id" class="chip who"><UserAvatar :user="u" link /> {{ u.name }}</span>
        </template>
        <span v-else class="muted">noch niemand</span>
        <span class="spacer"></span>
        <div v-if="app.me" class="rsvp" role="group" aria-label="Bist du dabei?">
          <button :class="app.me.dabei ? 'on' : 'primary'" :aria-pressed="app.me.dabei" @click="app.toggleDabei()">
            <Icon :name="app.me.dabei ? 'gesehen' : 'plus'" :size="16" />
            {{ app.me.dabei ? 'Ich bin dabei' : 'Ich bin dabei!' }}
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
      </div>
      <div v-if="app.vielleicht.length || app.absagen.length" class="row andere muted">
        <template v-if="app.vielleicht.length">
          <span>Vielleicht:</span>
          <span class="avatars" :title="app.vielleicht.map((u) => u.name).join(', ')"><UserAvatar v-for="u in app.vielleicht" :key="u.id" :user="u" link /></span>
          <span class="namen">{{ app.vielleicht.map((u) => u.name).join(', ') }}</span>
        </template>
        <template v-if="app.absagen.length">
          <span>Kann nicht:</span>
          <span class="namen">{{ app.absagen.map((u) => u.name).join(', ') }}</span>
        </template>
      </div>
      <div class="row termin">
        <Icon name="kalender" :size="16" class="muted" />
        <span v-if="terminAnzeige"><strong>{{ terminAnzeige.tag }}</strong>, {{ terminAnzeige.zeit }}<span v-if="terminAnzeige.notiz" class="muted"> · {{ terminAnzeige.notiz }}</span></span>
        <span v-else-if="umfrage?.vorschlaege.length" class="muted">Termin wird abgestimmt</span>
        <span v-else class="muted">Noch kein Termin</span>
        <button v-if="app.me" class="small ghost" @click="terminOffen = 'fest'">{{ terminAnzeige ? 'Ändern' : 'Termin festlegen' }}</button>
        <button v-if="app.me && !umfrage?.vorschlaege.length" class="small ghost" @click="terminOffen = 'umfrage'">
          <Icon name="umfrage" :size="14" /> Abstimmen
        </button>
        <button v-if="terminAnzeige" class="small ghost" title="Als Kalender-Eintrag herunterladen" @click="kalender">
          <Icon name="download" :size="14" /> Kalender
        </button>
        <span class="spacer"></span>
        <button class="small" @click="einladungOffen = true"><Icon name="teilen" :size="14" /> Einladen</button>
      </div>
      <TerminUmfrage v-if="app.me && umfrage?.vorschlaege.length" :umfrage="umfrage" @update="(u) => (umfrage = u)" @festgelegt="festgelegt" />
      <GastgeberLeiste />
    </section>
    <TerminDialog
      v-if="terminOffen"
      :termin="termin"
      :modus="terminOffen"
      @close="terminOffen = null"
      @saved="(t) => ((termin = t), (terminOffen = null))"
      @umfrage="umfrageGestartet"
    />
    <Einladung v-if="einladungOffen" :termin="termin" :filme="zurWahl" :dabei="app.dabei" @close="einladungOffen = false" />

    <div class="layout">
      <section>
        <div class="row">
          <h2 class="section-title">Vorschläge</h2>
          <span class="spacer"></span>
          <button v-if="app.gruppenAdmin && vorschlaege.length" class="ghost small danger" @click="allesLeeren">
            <Icon name="muell" :size="14" /> Alle leeren
          </button>
        </div>

        <p v-if="app.me && vorschlaege.length" class="muted small-text veto-hint">
          Jede Person hat ein <strong>Veto</strong>: Filme mit Veto kommen nicht in die Kiste.
        </p>
        <div v-if="loading" class="list">
          <div v-for="i in 3" :key="i" class="skeleton" style="height: 86px"></div>
        </div>
        <div v-else-if="!vorschlaege.length" class="empty">
          <strong>Noch keine Vorschläge</strong>
          Bei jedem Film gibt es den <Icon name="hand" :size="14" />-Knopf.
          <div style="margin-top: 0.8rem"><button class="small" @click="navigate('finden')">Filme finden</button></div>
        </div>
        <ol v-else class="list">
          <li v-for="(m, i) in vorschlaege" :key="m.id" class="sugg" :class="{ vetoed: m.veto_von.length }">
            <span class="rank">{{ i + 1 }}</span>
            <button class="thumb" :aria-label="`${m.title} – Details`" @click="ui.open(m)">
              <Poster :movie="m" :title="false" />
            </button>
            <div class="what">
              <button class="linklike" @click="ui.open(m)">{{ m.title }}</button>
              <div class="muted small-text">{{ m.year }} · ★ {{ dezimal(m.vote_average) }}</div>
              <div class="avatars"><UserAvatar v-for="id in m.von" :key="id" :user-id="id" /></div>
              <div v-if="m.veto_von.length" class="veto-info"><Icon name="veto" :size="13" /> Veto von {{ namen(m.veto_von) }}</div>
            </div>
            <div v-if="app.me" class="buttons">
              <button class="small" :class="{ on: meinVorschlag(m) }" @click="toggle(m)">
                <Icon name="hand" :size="14" /> {{ meinVorschlag(m) ? 'Zurückziehen' : '+1' }}
              </button>
              <button
                class="small ghost veto"
                :class="{ on: meinVeto(m) }"
                :aria-pressed="meinVeto(m)"
                :title="meinVeto(m) ? 'Veto zurücknehmen' : vetoVerbraucht ? 'Dein Veto hierher verschieben' : 'Nicht mit mir – der Film kommt nicht in die Kiste'"
                @click="veto(m)"
              >
                <Icon name="veto" :size="14" /> {{ meinVeto(m) ? 'Veto zurück' : 'Veto' }}
              </button>
            </div>
          </li>
        </ol>

        <h2 class="section-title">Aktivität</h2>
        <ul v-if="events.length" class="feed">
          <li v-for="(e, i) in events" :key="i">
            <span>{{ EVENT_TEXT[e.typ](e) }}</span>
            <time class="muted" :datetime="e.at">{{ vorWann(e.at) }}</time>
          </li>
        </ul>
        <p v-else class="muted">Hier passiert noch nichts.</p>
      </section>

      <aside class="side">
        <div class="panel wheelbox">
          <h2 class="section-title" style="margin-top: 0">Filmabend-Kiste</h2>
          <template v-if="pool.length">
            <p class="muted small-text">{{ pool.length }} {{ pool.length === 1 ? 'Film' : 'Filme' }} aus {{ poolQuelle }}. Je mehr Stimmen, desto größer die Chance – je seltener die Farbe, desto unwahrscheinlicher.</p>
            <KistenOeffnung :pool="pool" />
          </template>
          <p v-else-if="vorschlaege.length" class="muted">Gegen alle Vorschläge gibt es ein Veto – schlagt noch etwas vor.</p>
          <p v-else class="muted">Sobald es Vorschläge (oder Filme auf der Merkliste) gibt, kann die Kiste geöffnet werden.</p>

          <div v-if="gewinner && !kiste.buehne" class="winner" role="status">
            <span class="muted small-text">Film des Abends<template v-if="app.userById(kiste.aktuell.von)"> · aus der Kiste von {{ app.userById(kiste.aktuell.von).name }}</template></span>
            <strong>{{ gewinner.title }}</strong>
            <div class="row">
              <button class="small" @click="ui.open(gewinner)">Details</button>
              <button v-if="app.me" class="small primary" @click="gewinnerGesehen"><Icon name="gesehen" :size="14" /> Geschaut</button>
              <button v-if="kiste.darfOeffnen" class="ghost small" @click="kiste.zuruecknehmen()">Zurücknehmen</button>
            </div>
          </div>
        </div>
        <Erinnerungen v-if="erinnerungen.length" :erinnerungen="erinnerungen" />
        <InfoCard />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.crew { margin-bottom: 0.5rem; display: flex; flex-direction: column; gap: 0.6rem; }
.rsvp { display: flex; gap: 0.3rem; flex-wrap: wrap; }
.rsvp .ghost { font-size: 0.85rem; }
.rsvp .vielleicht.on { color: var(--text); border-color: var(--gold); background: color-mix(in srgb, var(--gold) 14%, transparent); }
.rsvp .nein.on { color: var(--text); border-color: var(--accent); background: var(--accent-soft); }
.andere { font-size: 0.82rem; gap: 0.45rem; margin-top: -0.2rem; }
.andere .avatars .avatar { width: 20px; height: 20px; font-size: 0.55rem; }
.andere .namen { margin-right: 0.8rem; }
.rueckblick-teaser {
  display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem; padding: 0.85rem 1rem; text-decoration: none;
  border-radius: var(--radius); border: 1px solid color-mix(in srgb, var(--gold) 45%, transparent);
  background: linear-gradient(100deg, color-mix(in srgb, var(--gold) 20%, transparent), color-mix(in srgb, var(--accent) 12%, transparent));
}
.rueckblick-teaser svg { color: var(--gold); flex: none; }
.rueckblick-teaser .go { font-weight: 600; white-space: nowrap; }
.rueckblick-teaser:hover { border-color: var(--gold); }
@media (max-width: 600px) {
  .rsvp { width: 100%; }
  .rsvp button { flex: 1; justify-content: center; }
  .rueckblick-teaser .go { display: none; }
}
.termin { border-top: 1px solid var(--line); padding-top: 0.6rem; font-size: 0.9rem; }
.onair {
  display: flex; align-items: center; gap: 0.8rem; margin-bottom: 1rem; padding: 0.8rem 1rem; text-decoration: none;
  border-radius: var(--radius); background: linear-gradient(90deg, color-mix(in srgb, var(--accent) 22%, transparent), color-mix(in srgb, var(--accent) 6%, transparent)); border: 1px solid rgba(229, 9, 20, 0.45);
}
.onair:hover { border-color: var(--accent); }
.onair .badge { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.08em; padding: 3px 8px; border-radius: 5px; }
.onair .dot { width: 7px; height: 7px; border-radius: 50%; background: #fff; animation: blink 1.4s ease-in-out infinite; }
@keyframes blink { 50% { opacity: 0.3; } }
.onair .go { display: inline-flex; align-items: center; gap: 0.4rem; font-weight: 600; }
.who { padding: 2px 10px 2px 2px; color: var(--text); }
.who .avatar { width: 22px; height: 22px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 380px; gap: 2rem; align-items: start; }
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.6rem; }
.veto-hint { margin: -0.4rem 0 0.8rem; }
.sugg.vetoed { opacity: 0.55; }
.sugg.vetoed .linklike { text-decoration: line-through; }
.veto-info { display: inline-flex; align-items: center; gap: 4px; font-size: 0.78rem; color: var(--accent); }
.buttons { display: flex; flex-direction: column; gap: 0.3rem; align-items: stretch; }
.veto.on { color: #fff; }
.sugg { display: flex; align-items: center; gap: 0.9rem; background: var(--bg-soft); border: 1px solid var(--line); border-radius: var(--radius); padding: 0.6rem 0.9rem 0.6rem 0.6rem; }
.rank { width: 1.6rem; text-align: center; font-weight: 800; color: var(--muted); font-size: 1.1rem; }
.sugg:first-child .rank { color: var(--accent); }
.thumb { padding: 0; width: 46px; height: 69px; border-radius: 6px; overflow: hidden; flex: none; background: var(--bg-raised); }
.what { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.linklike { padding: 0; border: none; background: none; font-weight: 600; font-size: 0.98rem; text-align: left; }
.linklike:hover { background: none; text-decoration: underline; }
.small-text { font-size: 0.8rem; }
.avatars .avatar { width: 22px; height: 22px; font-size: 0.6rem; }
.side { min-width: 0; }
.winner { margin-top: 1.2rem; border-top: 1px solid var(--line); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.4rem; text-align: center; align-items: center; }
.winner strong { font-size: 1.3rem; }
.feed { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; }
.feed li { display: flex; gap: 1rem; justify-content: space-between; padding: 0.55rem 0; border-bottom: 1px solid var(--line); font-size: 0.88rem; }
.feed time { flex: none; font-size: 0.78rem; }
@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .side { order: -1; }
}
</style>
