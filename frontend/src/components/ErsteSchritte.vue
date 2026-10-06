<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { aboHier, istIos, pushMoeglich } from '../push'
import { useApp } from '../stores/app'
import { useUi } from '../stores/ui'
import Icon from './Icon.vue'

// New here? A short checklist on the movie-night page: answer for the next night, suggest a film,
// your streaming services, notifications. Each item leads where it's done and ticks itself;
// the card goes once everything is done or it's put away (remembered with the profile).
const props = defineProps({ termin: { type: Object, default: null }, vorgeschlagen: { type: Boolean, default: false } })
const app = useApp()
const ui = useUi()

const KEY = () => `screenmates.ersteSchritte.${app.me?.id}`
const gemerkt = ref({})
try {
  gemerkt.value = JSON.parse(localStorage.getItem(KEY())) || {}
} catch {
  /* private mode */
}
const pushAn = ref(false)
async function pushPruefen() {
  pushAn.value = !!(await aboHier().catch(() => null))
}
onMounted(pushPruefen)
watch(() => ui.changes, pushPruefen)

const neu = computed(() => !!app.me && Date.now() - new Date(app.me.created_at).getTime() < 30 * 864e5)
const schritte = computed(() =>
  [
    props.termin?.termin && { key: 'antwort', erledigt: !!(app.me.dabei || app.me.rueckmeldung) },
    { key: 'vorschlag', erledigt: props.vorgeschlagen, href: '#/finden' },
    app.status.tmdb && { key: 'abos', erledigt: !!app.me.abos?.length, href: '#/profil/einstellungen' },
    (pushMoeglich() || istIos()) && { key: 'push', erledigt: pushAn.value, href: '#/profil/einstellungen' },
  ]
    .filter(Boolean)
    .map((s) => ({ ...s, erledigt: s.erledigt || !!gemerkt.value[s.key] })),
)
// Once ticked stays ticked (a suggestion may be watched and gone later).
watch(
  schritte,
  (liste) => {
    const neuErledigt = liste.filter((s) => s.erledigt && !gemerkt.value[s.key])
    if (!neuErledigt.length) return
    gemerkt.value = { ...gemerkt.value, ...Object.fromEntries(neuErledigt.map((s) => [s.key, true])) }
    try {
      localStorage.setItem(KEY(), JSON.stringify(gemerkt.value))
    } catch {
      /* private mode */
    }
  },
  { immediate: true },
)
const fertig = computed(() => schritte.value.filter((s) => s.erledigt).length)
const sichtbar = computed(() => neu.value && !app.me.design?.schritte_aus && fertig.value < schritte.value.length)

async function ausblenden() {
  app.me.design = (await api.post('/api/users/me/erste-schritte')).design
}
</script>

<template>
  <section v-if="sichtbar" class="panel schritte" :aria-label="$t('ersteSchritte.titel')">
    <div class="kopf">
      <h2>{{ $t('ersteSchritte.titel') }}</h2>
      <span class="muted stand">{{ $t('ersteSchritte.stand', { fertig, alle: schritte.length }) }}</span>
      <span class="spacer"></span>
      <button class="ghost small" @click="ausblenden">{{ $t('ersteSchritte.ausblenden') }}</button>
    </div>
    <div class="balken" aria-hidden="true"><span :style="{ width: `${(100 * fertig) / schritte.length}%` }"></span></div>
    <ul>
      <li v-for="s in schritte" :key="s.key" :class="{ erledigt: s.erledigt }">
        <span class="haken" aria-hidden="true"><Icon v-if="s.erledigt" name="gesehen" :size="13" /></span>
        <span class="text">
          <strong>{{ $t(`ersteSchritte.${s.key}.titel`) }}</strong>
          <small class="muted">{{ $t(`ersteSchritte.${s.key}.text`) }}</small>
        </span>
        <template v-if="!s.erledigt">
          <span v-if="s.key === 'antwort'" class="row knoepfe">
            <button class="small primary" @click="app.antworten('ja')">{{ $t('ersteSchritte.antwort.ja') }}</button>
            <button class="small ghost" @click="app.antworten('nein')">{{ $t('ersteSchritte.antwort.nein') }}</button>
          </span>
          <a v-else :href="s.href" class="button small">{{ $t(`ersteSchritte.${s.key}.los`) }}</a>
        </template>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.schritte { margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.7rem; border-color: color-mix(in srgb, var(--accent) 35%, var(--line)); }
.kopf { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
h2 { margin: 0; font-size: 1.05rem; }
.stand { font-size: 0.82rem; }
.balken { height: 4px; border-radius: 2px; background: var(--line); overflow: hidden; }
.balken span { display: block; height: 100%; background: var(--accent); transition: width 0.3s; }
ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr)); gap: 0.6rem; }
li { display: flex; flex-direction: column; gap: 0.5rem; padding: 0.7rem 0.8rem; border-radius: 10px; background: var(--bg); border: 1px solid var(--line); position: relative; }
li.erledigt { opacity: 0.55; }
.haken { position: absolute; top: 0.65rem; right: 0.7rem; width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; border: 1px solid var(--line); }
.erledigt .haken { background: color-mix(in srgb, var(--ok) 25%, transparent); border-color: var(--ok); color: var(--ok); }
.text { display: flex; flex-direction: column; gap: 0.2rem; padding-right: 1.6rem; }
.text strong { font-size: 0.9rem; }
.text small { font-size: 0.78rem; line-height: 1.4; }
.knoepfe { gap: 0.3rem; }
a.button.small { align-self: flex-start; padding: 0.3rem 0.7rem; font-size: 0.8rem; }
@media (prefers-reduced-motion: reduce) { .balken span { transition: none; } }
</style>
